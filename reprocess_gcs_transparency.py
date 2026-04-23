#!/usr/bin/env python3
"""
Safely detect and reprocess PNG images in GCS that appear to have non-transparent white backgrounds.

Key safety features:
- Dry-run mode (default behavior)
- Backup-before-write for reprocess mode
- Generation precondition on overwrite to avoid race-condition clobbers
- Machine-readable JSON report for audit + restore

Example usage:
  # 1) Dry-run on known URLs (recommended first step)
  python3 reprocess_gcs_transparency.py \
    --mode dry-run \
    --use-sample-urls

  # 2) Backup only suspected images from dry-run target set
  python3 reprocess_gcs_transparency.py \
    --mode backup \
    --use-sample-urls \
    --suspected-only

  # 3) Reprocess (backup + overwrite) suspected images only
  python3 reprocess_gcs_transparency.py \
    --mode reprocess \
    --use-sample-urls \
    --suspected-only \
    --confirm-write

  # 4) Restore from a previous report if needed
  python3 reprocess_gcs_transparency.py \
    --mode restore \
    --from-report reports/transparency_reprocess_20260415_120000.json \
    --confirm-write
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from google.cloud import storage
from PIL import Image


SAMPLE_URLS = [
    "https://storage.googleapis.com/bravo-prod-465323-aac-images/bravo_images/Categories_from_20260124_202634.png",
    "https://storage.googleapis.com/bravo-prod-465323-aac-images/bravo_images/Categories_same_20260124_200857.png",
    "https://storage.googleapis.com/bravo-prod-465323-aac-images/bravo_images/Categories_conversation_20260124_204117.png",
    "https://storage.googleapis.com/bravo-prod-465323-aac-images/bravo_images/Categories_answer_20260124_204737.png",
]


@dataclass
class ImageTarget:
    bucket: str
    object_name: str
    source: str


@dataclass
class ProcessingResult:
    bucket: str
    object_name: str
    source: str
    mode: str
    status: str
    message: str
    generation: Optional[int] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    suspected_white_background: Optional[bool] = None
    metrics_before: Optional[Dict[str, Any]] = None
    metrics_after: Optional[Dict[str, Any]] = None
    backup_object_name: Optional[str] = None


class TransparencyReprocessor:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        if args.credentials_file:
            self.client = storage.Client.from_service_account_json(
                args.credentials_file,
                project=args.project,
            )
        else:
            self.client = storage.Client(project=args.project) if args.project else storage.Client()
        self.logger = logging.getLogger("transparency_reprocessor")

    @staticmethod
    def parse_gcs_url(url: str) -> ImageTarget:
        parsed = urlparse(url)

        if parsed.scheme == "gs":
            bucket = parsed.netloc
            object_name = parsed.path.lstrip("/")
            if not bucket or not object_name:
                raise ValueError(f"Invalid gs:// URL: {url}")
            return ImageTarget(bucket=bucket, object_name=object_name, source=url)

        if parsed.scheme in {"http", "https"} and parsed.netloc == "storage.googleapis.com":
            path = parsed.path.lstrip("/")
            parts = path.split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid GCS HTTPS URL: {url}")
            return ImageTarget(bucket=parts[0], object_name=parts[1], source=url)

        raise ValueError(f"Unsupported GCS URL format: {url}")

    @staticmethod
    def _is_near_white(r: int, g: int, b: int, tolerance: int) -> bool:
        threshold = 255 - tolerance
        return r >= threshold and g >= threshold and b >= threshold

    def compute_white_metrics(self, image: Image.Image, tolerance: int) -> Dict[str, Any]:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        pixels = rgba.getdata()

        total_pixels = width * height
        opaque_pixels = 0
        white_opaque_pixels = 0

        border_opaque_pixels = 0
        border_white_opaque_pixels = 0

        for idx, (r, g, b, a) in enumerate(pixels):
            x = idx % width
            y = idx // width
            is_border = (x == 0 or x == width - 1 or y == 0 or y == height - 1)

            if a > 10:
                opaque_pixels += 1
                if self._is_near_white(r, g, b, tolerance):
                    white_opaque_pixels += 1

            if is_border and a > 10:
                border_opaque_pixels += 1
                if self._is_near_white(r, g, b, tolerance):
                    border_white_opaque_pixels += 1

        white_ratio = (white_opaque_pixels / opaque_pixels) if opaque_pixels else 0.0
        border_white_ratio = (
            border_white_opaque_pixels / border_opaque_pixels if border_opaque_pixels else 0.0
        )

        return {
            "width": width,
            "height": height,
            "total_pixels": total_pixels,
            "opaque_pixels": opaque_pixels,
            "white_opaque_pixels": white_opaque_pixels,
            "white_opaque_ratio": round(white_ratio, 6),
            "border_opaque_pixels": border_opaque_pixels,
            "border_white_opaque_pixels": border_white_opaque_pixels,
            "border_white_opaque_ratio": round(border_white_ratio, 6),
        }

    def is_suspected_white_background(self, metrics: Dict[str, Any]) -> bool:
        # Conservative detection: strong white border plus notable white opaque area.
        return (
            metrics["border_white_opaque_ratio"] >= self.args.border_white_threshold
            and metrics["white_opaque_ratio"] >= self.args.white_ratio_threshold
        )

    def convert_white_to_transparent(self, image: Image.Image, tolerance: int) -> Image.Image:
        rgba = image.convert("RGBA")
        data = rgba.getdata()
        new_data = []

        for (r, g, b, a) in data:
            if a > 0 and self._is_near_white(r, g, b, tolerance):
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append((r, g, b, a))

        rgba.putdata(new_data)
        return rgba

    @staticmethod
    def build_backup_name(prefix: str, object_name: str) -> str:
        safe_prefix = prefix.strip("/")
        return f"{safe_prefix}/{object_name}" if safe_prefix else object_name

    def resolve_targets(self) -> List[ImageTarget]:
        targets: List[ImageTarget] = []

        for url in self.args.urls:
            targets.append(self.parse_gcs_url(url))

        if self.args.use_sample_urls:
            for url in SAMPLE_URLS:
                targets.append(self.parse_gcs_url(url))

        if self.args.url_file:
            path = Path(self.args.url_file)
            if not path.exists():
                raise FileNotFoundError(f"URL file not found: {path}")
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                targets.append(self.parse_gcs_url(line))

        if self.args.bucket and self.args.prefix:
            bucket = self.client.bucket(self.args.bucket)
            for blob in self.client.list_blobs(bucket, prefix=self.args.prefix):
                if not blob.name.lower().endswith(".png"):
                    continue
                targets.append(
                    ImageTarget(
                        bucket=self.args.bucket,
                        object_name=blob.name,
                        source=f"gs://{self.args.bucket}/{blob.name}",
                    )
                )

        dedup = {}
        for target in targets:
            dedup[(target.bucket, target.object_name)] = target

        resolved = sorted(dedup.values(), key=lambda t: (t.bucket, t.object_name))
        if not resolved:
            raise ValueError(
                "No targets resolved. Provide --url/--url-file/--use-sample-urls or --bucket + --prefix."
            )
        return resolved

    def process_target(self, target: ImageTarget) -> ProcessingResult:
        bucket = self.client.bucket(target.bucket)
        blob = bucket.blob(target.object_name)

        if not blob.exists():
            return ProcessingResult(
                bucket=target.bucket,
                object_name=target.object_name,
                source=target.source,
                mode=self.args.mode,
                status="missing",
                message="Object not found",
            )

        blob.reload()
        generation = int(blob.generation) if blob.generation else None
        size = blob.size
        content_type = blob.content_type or ""

        if not target.object_name.lower().endswith(".png"):
            return ProcessingResult(
                bucket=target.bucket,
                object_name=target.object_name,
                source=target.source,
                mode=self.args.mode,
                status="skipped",
                message="Non-PNG object skipped",
                generation=generation,
                size=size,
                content_type=content_type,
            )

        data = blob.download_as_bytes()
        image = Image.open(io.BytesIO(data))
        before_metrics = self.compute_white_metrics(image, self.args.tolerance)
        suspected = self.is_suspected_white_background(before_metrics)

        if self.args.suspected_only and not suspected:
            return ProcessingResult(
                bucket=target.bucket,
                object_name=target.object_name,
                source=target.source,
                mode=self.args.mode,
                status="skipped",
                message="Not suspected based on thresholds",
                generation=generation,
                size=size,
                content_type=content_type,
                suspected_white_background=suspected,
                metrics_before=before_metrics,
            )

        if self.args.mode in {"dry-run", "verify"}:
            return ProcessingResult(
                bucket=target.bucket,
                object_name=target.object_name,
                source=target.source,
                mode=self.args.mode,
                status="analyzed",
                message="Analysis complete",
                generation=generation,
                size=size,
                content_type=content_type,
                suspected_white_background=suspected,
                metrics_before=before_metrics,
            )

        backup_name = self.build_backup_name(self.args.backup_prefix, target.object_name)

        if self.args.mode in {"backup", "reprocess"}:
            backup_blob = bucket.blob(backup_name)
            if backup_blob.exists() and not self.args.overwrite_existing_backup:
                return ProcessingResult(
                    bucket=target.bucket,
                    object_name=target.object_name,
                    source=target.source,
                    mode=self.args.mode,
                    status="skipped",
                    message=(
                        "Backup already exists; use --overwrite-existing-backup to replace it"
                    ),
                    generation=generation,
                    size=size,
                    content_type=content_type,
                    suspected_white_background=suspected,
                    metrics_before=before_metrics,
                    backup_object_name=backup_name,
                )

            # Copy exact object bytes into backup prefix.
            bucket.copy_blob(blob, bucket, new_name=backup_name)

            if self.args.mode == "backup":
                return ProcessingResult(
                    bucket=target.bucket,
                    object_name=target.object_name,
                    source=target.source,
                    mode=self.args.mode,
                    status="backed_up",
                    message="Backup created",
                    generation=generation,
                    size=size,
                    content_type=content_type,
                    suspected_white_background=suspected,
                    metrics_before=before_metrics,
                    backup_object_name=backup_name,
                )

        # mode == reprocess
        processed = self.convert_white_to_transparent(image, self.args.tolerance)
        out_buffer = io.BytesIO()
        processed.save(out_buffer, format="PNG", optimize=True)
        out_bytes = out_buffer.getvalue()

        after_image = Image.open(io.BytesIO(out_bytes))
        after_metrics = self.compute_white_metrics(after_image, self.args.tolerance)

        blob.upload_from_string(
            out_bytes,
            content_type="image/png",
            if_generation_match=generation,
        )

        return ProcessingResult(
            bucket=target.bucket,
            object_name=target.object_name,
            source=target.source,
            mode=self.args.mode,
            status="reprocessed",
            message="Backup created and object overwritten safely",
            generation=generation,
            size=size,
            content_type=content_type,
            suspected_white_background=suspected,
            metrics_before=before_metrics,
            metrics_after=after_metrics,
            backup_object_name=backup_name,
        )

    def restore_from_report(self, report_path: Path) -> List[ProcessingResult]:
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")

        payload = json.loads(report_path.read_text(encoding="utf-8"))
        raw_results = payload.get("results", [])

        results: List[ProcessingResult] = []
        for row in raw_results:
            backup_name = row.get("backup_object_name")
            object_name = row.get("object_name")
            bucket_name = row.get("bucket")

            if not backup_name or not object_name or not bucket_name:
                continue

            bucket = self.client.bucket(bucket_name)
            source_backup_blob = bucket.blob(backup_name)
            target_blob = bucket.blob(object_name)

            if not source_backup_blob.exists():
                results.append(
                    ProcessingResult(
                        bucket=bucket_name,
                        object_name=object_name,
                        source=f"gs://{bucket_name}/{object_name}",
                        mode="restore",
                        status="missing_backup",
                        message="Backup object not found",
                        backup_object_name=backup_name,
                    )
                )
                continue

            if not target_blob.exists() and not self.args.allow_restore_create:
                results.append(
                    ProcessingResult(
                        bucket=bucket_name,
                        object_name=object_name,
                        source=f"gs://{bucket_name}/{object_name}",
                        mode="restore",
                        status="skipped",
                        message="Target object missing (use --allow-restore-create to recreate)",
                        backup_object_name=backup_name,
                    )
                )
                continue

            bucket.copy_blob(source_backup_blob, bucket, new_name=object_name)
            results.append(
                ProcessingResult(
                    bucket=bucket_name,
                    object_name=object_name,
                    source=f"gs://{bucket_name}/{object_name}",
                    mode="restore",
                    status="restored",
                    message="Restored original object from backup",
                    backup_object_name=backup_name,
                )
            )

        return results

    def write_report(self, targets: Sequence[ImageTarget], results: Sequence[ProcessingResult]) -> Path:
        report_dir = Path(self.args.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"transparency_reprocess_{timestamp}.json"

        payload = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": self.args.mode,
            "project": self.args.project,
            "args": {
                "suspected_only": self.args.suspected_only,
                "tolerance": self.args.tolerance,
                "white_ratio_threshold": self.args.white_ratio_threshold,
                "border_white_threshold": self.args.border_white_threshold,
                "backup_prefix": self.args.backup_prefix,
            },
            "target_count": len(targets),
            "result_count": len(results),
            "status_summary": self._status_summary(results),
            "targets": [asdict(t) for t in targets],
            "results": [asdict(r) for r in results],
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return report_path

    @staticmethod
    def _status_summary(results: Sequence[ProcessingResult]) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for row in results:
            summary[row.status] = summary.get(row.status, 0) + 1
        return summary

    def run(self) -> int:
        if self.args.mode in {"backup", "reprocess", "restore"} and not self.args.confirm_write:
            raise ValueError(
                f"Mode '{self.args.mode}' performs writes. Re-run with --confirm-write."
            )

        if self.args.mode == "restore":
            if not self.args.from_report:
                raise ValueError("Restore mode requires --from-report <report.json>")
            restore_results = self.restore_from_report(Path(self.args.from_report))
            report_path = self.write_report([], restore_results)
            self.logger.info("Restore complete. Report: %s", report_path)
            self.logger.info("Status summary: %s", self._status_summary(restore_results))
            return 0

        targets = self.resolve_targets()
        results: List[ProcessingResult] = []

        self.logger.info("Resolved %d targets", len(targets))
        for idx, target in enumerate(targets, start=1):
            self.logger.info("[%d/%d] Processing %s", idx, len(targets), target.source)
            try:
                result = self.process_target(target)
            except Exception as exc:
                self.logger.exception("Failed processing %s", target.source)
                result = ProcessingResult(
                    bucket=target.bucket,
                    object_name=target.object_name,
                    source=target.source,
                    mode=self.args.mode,
                    status="error",
                    message=str(exc),
                )
            results.append(result)

        report_path = self.write_report(targets, results)
        self.logger.info("Completed mode=%s. Report: %s", self.args.mode, report_path)
        self.logger.info("Status summary: %s", self._status_summary(results))
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely detect and reprocess white-background PNGs in GCS"
    )

    parser.add_argument(
        "--mode",
        choices=["dry-run", "verify", "backup", "reprocess", "restore"],
        default="dry-run",
        help="Operation mode (default: dry-run)",
    )
    parser.add_argument("--project", help="GCP project override for storage client")
    parser.add_argument(
        "--credentials-file",
        help="Path to a service-account JSON key for non-interactive GCS access",
    )

    parser.add_argument(
        "--url",
        dest="urls",
        action="append",
        default=[],
        help="Target image URL (https://storage.googleapis.com/... or gs://...)",
    )
    parser.add_argument("--url-file", help="Text file with one GCS URL per line")
    parser.add_argument(
        "--use-sample-urls",
        action="store_true",
        help="Include built-in sample URLs from investigation",
    )

    parser.add_argument("--bucket", help="Optional bucket for prefix-based scan")
    parser.add_argument("--prefix", help="Optional prefix for bucket scan (requires --bucket)")

    parser.add_argument(
        "--suspected-only",
        action="store_true",
        help="Only back up/reprocess items that meet white-background suspicion thresholds",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=30,
        help="Near-white tolerance (0-255, default: 30)",
    )
    parser.add_argument(
        "--white-ratio-threshold",
        type=float,
        default=0.20,
        help="Min overall white opaque ratio for suspicion (default: 0.20)",
    )
    parser.add_argument(
        "--border-white-threshold",
        type=float,
        default=0.85,
        help="Min border white opaque ratio for suspicion (default: 0.85)",
    )

    parser.add_argument(
        "--backup-prefix",
        default=f"backups/transparency_fix_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        help="Backup object prefix for backup/reprocess modes",
    )
    parser.add_argument(
        "--overwrite-existing-backup",
        action="store_true",
        help="Allow replacing existing backup object(s)",
    )

    parser.add_argument(
        "--from-report",
        help="Report JSON file used by restore mode",
    )
    parser.add_argument(
        "--allow-restore-create",
        action="store_true",
        help="Allow restore to recreate missing target objects",
    )

    parser.add_argument(
        "--report-dir",
        default="reports",
        help="Directory for generated JSON reports",
    )

    parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Required for modes that write to GCS (backup/reprocess/restore)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        runner = TransparencyReprocessor(args)
        return runner.run()
    except Exception as exc:
        logging.error("Fatal error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
