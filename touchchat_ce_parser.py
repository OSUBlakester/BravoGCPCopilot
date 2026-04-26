"""Utilities for parsing TouchChat .ce exports into Bravo-friendly board/button structures."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class TouchChatExtraction:
    parsed_data: Dict[str, Any]
    temp_dir: str
    c4v_path: str
    c4s_path: Optional[str]


def _int_color_to_hex(value: Any, default_hex: str) -> str:
    try:
        if value is None:
            return default_hex
        num = int(value)
        # TouchChat colors are stored as packed 24-bit RGB integers.
        return f"#{num & 0xFFFFFF:06X}"
    except Exception:
        return default_hex


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_helper_button_text(value: Any) -> str:
    return " ".join(_safe_text(value).lower().split())


def _normalize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    return base if base else "touchchat_export.ce.zip"


def _find_first_file_with_suffix(root: str, suffix: str) -> Optional[str]:
    for current_root, _dirs, files in os.walk(root):
        for name in files:
            if name.lower().endswith(suffix.lower()):
                return os.path.join(current_root, name)
    return None


def _load_embedded_symbol_rids(c4s_path: Optional[str]) -> set[str]:
    """Load all symbol RIDs physically embedded in Images.c4s."""
    if not c4s_path:
        return set()

    conn = sqlite3.connect(c4s_path)
    try:
        cur = conn.execute("SELECT rid FROM symbols")
        return {str(rid).strip() for (rid,) in cur.fetchall() if rid}
    except Exception:
        return set()
    finally:
        conn.close()


def _load_page_resources(conn: sqlite3.Connection) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    page_by_id: Dict[int, Dict[str, Any]] = {}
    page_by_rid: Dict[str, Dict[str, Any]] = {}

    cur = conn.execute(
        """
        SELECT p.id, r.id AS resource_id, r.rid, r.name
        FROM pages p
        JOIN resources r ON r.id = p.resource_id
        ORDER BY p.id
        """
    )
    for page_id, resource_id, rid, name in cur.fetchall():
        item = {
            "page_id": int(page_id),
            "resource_id": int(resource_id),
            "rid": str(rid),
            "name": _safe_text(name) or f"Page {page_id}",
        }
        page_by_id[item["page_id"]] = item
        page_by_rid[item["rid"]] = item

    return page_by_id, page_by_rid


def _load_navigation_targets(
    conn: sqlite3.Connection,
    page_by_id: Dict[int, Dict[str, Any]],
    page_by_rid: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[int, str], set[int]]:
    """Map button resource_id -> target page rid and identify temporary (navigate-and-return) actions."""
    targets: Dict[int, str] = {}
    temporary_navigation_resources: set[int] = set()
    page_rids = set(page_by_rid.keys())
    page_resource_id_to_rid = {
        int(page.get("resource_id") or 0): str(page.get("rid") or "")
        for page in page_by_id.values()
        if int(page.get("resource_id") or 0) > 0 and str(page.get("rid") or "")
    }

    cur = conn.execute(
        """
        SELECT a.resource_id, a.code, ad.value
        FROM actions a
        JOIN action_data ad ON ad.action_id = a.id
        WHERE a.code IN (8, 9, 73)
          AND ad.key = 0
        """
    )

    for resource_id, action_code, value in cur.fetchall():
        rid_value = _safe_text(value)
        target_rid: Optional[str] = None

        if rid_value and rid_value in page_rids:
            target_rid = rid_value
        elif rid_value:
            try:
                numeric_value = int(rid_value)
            except Exception:
                numeric_value = None

            # Some exports encode target as pages.id.
            if numeric_value is not None and numeric_value in page_by_id:
                target_rid = str(page_by_id[numeric_value].get("rid") or "") or None

            # Others encode target as pages.resource_id (resources.id).
            if numeric_value is not None and not target_rid:
                mapped_rid = page_resource_id_to_rid.get(numeric_value)
                target_rid = mapped_rid if mapped_rid else None

        if target_rid:
            targets[int(resource_id)] = target_rid
            if int(action_code or 0) == 73:
                temporary_navigation_resources.add(int(resource_id))

    return targets, temporary_navigation_resources


def _load_special_function_buttons(conn: sqlite3.Connection) -> set[int]:
    """Identify clear/period function buttons to skip during import.

    Any resource that has BOTH action code 28 (clear) and code 60 (display
    manipulation) but lacks a navigation code (8, 9, 73) is a special-function
    button (clear, period, backspace variants) that Bravo already provides.
    This catches all encoding variants: (28,60), (28,60,71), (28,53,60,71), etc.
    """
    skip_buttons: set[int] = set()

    cur = conn.execute(
        """
        WITH action_codes AS (
            SELECT a.resource_id,
                   SUM(CASE WHEN a.code = 28  THEN 1 ELSE 0 END) AS has_28,
                   SUM(CASE WHEN a.code = 60  THEN 1 ELSE 0 END) AS has_60,
                   SUM(CASE WHEN a.code IN (8, 9, 73) THEN 1 ELSE 0 END) AS has_nav
            FROM actions a
            GROUP BY a.resource_id
        )
        SELECT resource_id FROM action_codes
        WHERE has_28 > 0 AND has_60 > 0 AND has_nav = 0
        """
    )

    for (resource_id,) in cur.fetchall():
        skip_buttons.add(int(resource_id))

    return skip_buttons


def _load_named_helper_buttons(conn: sqlite3.Connection) -> set[int]:
    """Identify helper/function buttons already provided elsewhere in Bravo, to skip during import.

    Covers:
    - Navigation helpers: home, find a word, mode switcher
    - Period/punctuation buttons (label ".")
    - Delete-word buttons (various spellings of "delete wd")
    """
    helper_buttons: set[int] = set()
    helper_names = {
        # Navigation / UI helpers already present in Bravo
        "find a word",
        "home",
        "wordpower60_basic ss  [one finger swipe down]",
        # Punctuation — Bravo's Speak Display adds punctuation automatically
        ".",
        # Delete-word — Bravo has its own backspace-word action
        "delete wd",
        "delete word",
        "delete wprd",  # known TouchChat typo variant
    }

    placeholders = ",".join("?" * len(helper_names))
    cur = conn.execute(
        f"SELECT DISTINCT id FROM resources WHERE LOWER(TRIM(name)) IN ({placeholders})",
        tuple(sorted(helper_names)),
    )

    for (resource_id,) in cur.fetchall():
        helper_buttons.add(int(resource_id))

    return helper_buttons


HELPER_BUTTON_TEXT_EXCLUSIONS = {
    "find a word",
    "home",
    "wordpower60_basic ss [one finger swipe down]",
    ".",
    "delete wd",
    "delete word",
    "delete wprd",
}


def _load_modifier_triggers(conn: sqlite3.Connection) -> Dict[int, int]:
    """Map TouchChat button resource IDs to the modifier state they trigger."""
    triggers: Dict[int, int] = {}
    cur = conn.execute(
        """
        SELECT a.resource_id, ad.value
        FROM actions a
        JOIN action_data ad ON ad.action_id = a.id
        WHERE a.code = 71 AND ad.key = 0
        """
    )

    for resource_id, value in cur.fetchall():
        try:
            triggers[int(resource_id)] = int(str(value).strip())
        except Exception:
            continue

    return triggers


def _load_button_set_modifier_variants(conn: sqlite3.Connection) -> Dict[int, Dict[int, Dict[str, Any]]]:
    """Map cell resource IDs to their alternate button-set modifier states."""
    variants_by_cell: Dict[int, Dict[int, Dict[str, Any]]] = {}
    cur = conn.execute(
        """
        SELECT
            bs.resource_id AS cell_resource_id,
            bsm.modifier,
            btn.resource_id AS button_resource_id,
            br.rid AS button_resource_rid,
            btn.label,
            btn.message,
            btn.visible,
            style.body_color,
            style.font_color
        FROM button_sets bs
        JOIN button_set_modifiers bsm ON bsm.button_set_id = bs.id
        JOIN buttons btn ON btn.id = bsm.button_id
        LEFT JOIN resources br ON br.id = btn.resource_id
        LEFT JOIN button_styles style ON style.id = btn.button_style_id
        WHERE bsm.modifier <> 0
        ORDER BY bs.resource_id, bsm.modifier
        """
    )

    for row in cur.fetchall():
        (
            cell_resource_id,
            modifier_id,
            button_resource_id,
            button_resource_rid,
            label,
            message,
            visible,
            body_color,
            font_color,
        ) = row

        try:
            cell_id = int(cell_resource_id or 0)
            modifier_key = int(modifier_id or 0)
        except Exception:
            continue
        if cell_id <= 0 or modifier_key <= 0:
            continue

        variants_for_cell = variants_by_cell.setdefault(cell_id, {})
        variants_for_cell[modifier_key] = {
            "button_resource_id": int(button_resource_id or 0),
            "button_resource_rid": _safe_text(button_resource_rid),
            "label": _safe_text(label),
            "speech_text": _safe_text(message) or None,
            "visible": bool(1 if visible is None else visible),
            "background_color": _int_color_to_hex(body_color, "#FFFFFF"),
            "text_color": _int_color_to_hex(font_color, "#000000"),
        }

    return variants_by_cell


def _load_board_cells(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT
            p.id AS page_id,
            pr.rid AS page_rid,
            pr.name AS page_name,
            bb.layout_x,
            bb.layout_y,
            c.location,
            c.span_x,
            c.span_y,
            c.resource_id AS cell_resource_id,
            cr.rid AS cell_resource_rid,
            cr.name AS cell_resource_name,
            bset_btn.resource_id AS set_default_button_resource_id,
            bset_btn.label AS set_default_label,
            bset_btn.message AS set_default_message,
            br.id AS button_resource_id,
            br.rid AS button_resource_rid,
            br.name AS button_resource_name,
            b.id AS button_id,
            b.label AS label,
            b.message AS message,
            b.visible AS visible,
            bs.body_color AS body_color,
            bs.font_color AS font_color,
            sl.rid AS symbol_rid,
            sl.feature AS symbol_feature
        FROM pages p
        JOIN resources pr ON pr.id = p.resource_id
        LEFT JOIN button_box_instances bi ON bi.page_id = p.id
        LEFT JOIN button_boxes bb ON bb.id = bi.button_box_id
        LEFT JOIN button_box_cells c ON c.button_box_id = bb.id
        LEFT JOIN resources cr ON cr.id = c.resource_id
        LEFT JOIN button_sets bset ON bset.resource_id = c.resource_id
        LEFT JOIN button_set_modifiers bsm_default ON bsm_default.button_set_id = bset.id AND bsm_default.modifier = 0
        LEFT JOIN buttons bset_btn ON bset_btn.id = bsm_default.button_id
        LEFT JOIN buttons b ON b.resource_id = c.resource_id
        LEFT JOIN resources br ON br.id = b.resource_id
        LEFT JOIN button_styles bs ON bs.id = b.button_style_id
        LEFT JOIN symbol_links sl ON sl.id = b.symbol_link_id
        WHERE c.id IS NOT NULL
        ORDER BY p.id, c.location
        """
    )

    rows: List[Dict[str, Any]] = []
    for row in cur.fetchall():
        (
            page_id,
            page_rid,
            page_name,
            layout_x,
            layout_y,
            location,
            span_x,
            span_y,
            cell_resource_id,
            cell_resource_rid,
            cell_resource_name,
            set_default_button_resource_id,
            set_default_label,
            set_default_message,
            button_resource_id,
            button_resource_rid,
            button_resource_name,
            button_id,
            label,
            message,
            visible,
            body_color,
            font_color,
            symbol_rid,
            symbol_feature,
        ) = row

        rows.append(
            {
                "page_id": int(page_id),
                "page_rid": _safe_text(page_rid),
                "page_name": _safe_text(page_name),
                "layout_x": int(layout_x or 10),
                "layout_y": int(layout_y or 6),
                "location": int(location or 0),
                "span_x": int(span_x or 1),
                "span_y": int(span_y or 1),
                "cell_resource_id": int(cell_resource_id or 0),
                "cell_resource_rid": _safe_text(cell_resource_rid),
                "cell_resource_name": _safe_text(cell_resource_name),
                "set_default_button_resource_id": int(set_default_button_resource_id or 0),
                "set_default_label": _safe_text(set_default_label),
                "set_default_message": _safe_text(set_default_message),
                "button_resource_id": int(button_resource_id or 0),
                "button_resource_rid": _safe_text(button_resource_rid),
                "button_resource_name": _safe_text(button_resource_name),
                "button_id": int(button_id or 0),
                "label": _safe_text(label),
                "message": _safe_text(message),
                "visible": int(1 if visible is None else visible),
                "body_color": body_color,
                "font_color": font_color,
                "symbol_rid": _safe_text(symbol_rid),
                "symbol_feature": int(symbol_feature) if symbol_feature is not None else None,
            }
        )

    return rows


def parse_touchchat_ce_upload(file_bytes: bytes, filename: str) -> TouchChatExtraction:
    """Extract and parse a TouchChat CE archive into normalized board/button data."""
    temp_dir = tempfile.mkdtemp(prefix="touchchat_migration_")
    archive_name = _normalize_filename(filename)
    archive_path = os.path.join(temp_dir, archive_name)

    with open(archive_path, "wb") as f:
        f.write(file_bytes)

    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(temp_dir)

    c4v_path = _find_first_file_with_suffix(temp_dir, ".c4v")
    if not c4v_path:
        raise ValueError("TouchChat export does not include a .c4v vocabulary database")

    c4s_path = _find_first_file_with_suffix(temp_dir, ".c4s")

    conn = sqlite3.connect(c4v_path)
    try:
        embedded_symbol_rids = _load_embedded_symbol_rids(c4s_path)

        page_by_id, page_by_rid = _load_page_resources(conn)
        nav_targets_by_resource, temporary_navigation_resources = _load_navigation_targets(conn, page_by_id, page_by_rid)
        special_function_buttons_to_skip = _load_special_function_buttons(conn)
        named_helper_buttons_to_skip = _load_named_helper_buttons(conn)
        modifier_triggers_by_resource = _load_modifier_triggers(conn)
        modifier_variants_by_cell_resource = _load_button_set_modifier_variants(conn)
        cell_rows = _load_board_cells(conn)

        boards: Dict[str, Dict[str, Any]] = {}
        total_buttons = 0

        for page in page_by_id.values():
            boards[str(page["page_id"])] = {
                "page_id": str(page["page_id"]),
                "page_rid": page["rid"],
                "name": page["name"],
                "layout_cols": 10,
                "layout_rows": 6,
                "button_count": 0,
                "buttons": [],
            }

        for row in cell_rows:
            board_key = str(row["page_id"])
            board = boards.get(board_key)
            if not board:
                continue

            cols = max(1, int(row["layout_x"] or 10))
            rows = max(1, int(row["layout_y"] or 6))
            board["layout_cols"] = cols
            board["layout_rows"] = rows

            label = str(row["label"] or row["set_default_label"] or "").strip()
            speech_text = str(row["message"] or row["set_default_message"] or "").strip() or None
            action_resource_id = (
                int(row["button_resource_id"] or 0)
                or int(row["set_default_button_resource_id"] or 0)
                or int(row["cell_resource_id"] or 0)
            )
            has_payload = bool(label or speech_text or row["symbol_rid"] or action_resource_id)
            if not has_payload:
                continue

            # Skip TouchChat helper controls already handled elsewhere in Bravo.
            if int(action_resource_id or 0) in special_function_buttons_to_skip or int(action_resource_id or 0) in named_helper_buttons_to_skip:
                continue
            if (
                _normalize_helper_button_text(label) in HELPER_BUTTON_TEXT_EXCLUSIONS
                or _normalize_helper_button_text(speech_text) in HELPER_BUTTON_TEXT_EXCLUSIONS
            ):
                continue

            location = int(row["location"])
            parsed_button = {
                "index": len(board["buttons"]),
                "button_id": row["button_id"],
                "button_resource_id": action_resource_id,
                "button_resource_rid": row["button_resource_rid"] or row["cell_resource_rid"],
                "label": label,
                "speech_text": speech_text,
                "modifier_trigger_id": modifier_triggers_by_resource.get(int(action_resource_id or 0)),
                "modifier_variants": {},
                "row": int(location // cols),
                "col": int(location % cols),
                "location": location,
                "span_x": row["span_x"],
                "span_y": row["span_y"],
                "background_color": _int_color_to_hex(row["body_color"], "#FFFFFF"),
                "text_color": _int_color_to_hex(row["font_color"], "#000000"),
                # Only retain symbol_rid when it is physically embedded in Images.c4s.
                "symbol_rid": (
                    row["symbol_rid"]
                    if row["symbol_rid"] and row["symbol_rid"] in embedded_symbol_rids
                    else None
                ),
                "symbol_feature": row["symbol_feature"],
                "navigation_target_page_rid": None,
                "navigation_target_page_name": None,
                "temporary_navigation": False,
                "visible": bool(row["visible"]),
            }

            target_page_rid = nav_targets_by_resource.get(action_resource_id)
            if target_page_rid:
                parsed_button["navigation_target_page_rid"] = target_page_rid
                target_page = page_by_rid.get(target_page_rid)
                if target_page:
                    parsed_button["navigation_target_page_name"] = target_page["name"]
                if int(action_resource_id or 0) in temporary_navigation_resources:
                    parsed_button["temporary_navigation"] = True

            raw_modifier_variants = modifier_variants_by_cell_resource.get(int(row["cell_resource_id"] or 0), {})
            if raw_modifier_variants:
                parsed_variants: Dict[str, Dict[str, Any]] = {}
                for modifier_id, variant in raw_modifier_variants.items():
                    variant_action_resource_id = int(variant.get("button_resource_id") or 0)
                    if variant_action_resource_id in special_function_buttons_to_skip or variant_action_resource_id in named_helper_buttons_to_skip:
                        continue
                    if (
                        _normalize_helper_button_text(variant.get("label")) in HELPER_BUTTON_TEXT_EXCLUSIONS
                        or _normalize_helper_button_text(variant.get("speech_text")) in HELPER_BUTTON_TEXT_EXCLUSIONS
                    ):
                        continue

                    variant_target_page_rid = nav_targets_by_resource.get(variant_action_resource_id)
                    variant_target_page_name = None
                    if variant_target_page_rid:
                        variant_target_page = page_by_rid.get(variant_target_page_rid)
                        if variant_target_page:
                            variant_target_page_name = variant_target_page.get("name")

                    parsed_variants[str(modifier_id)] = {
                        "label": str(variant.get("label") or "").strip(),
                        "speech_text": variant.get("speech_text"),
                        "button_resource_id": variant_action_resource_id,
                        "button_resource_rid": variant.get("button_resource_rid"),
                        "modifier_trigger_id": modifier_triggers_by_resource.get(variant_action_resource_id),
                        "navigation_target_page_rid": variant_target_page_rid,
                        "navigation_target_page_name": variant_target_page_name,
                        "temporary_navigation": bool(variant_action_resource_id in temporary_navigation_resources),
                        "background_color": variant.get("background_color") or parsed_button["background_color"],
                        "text_color": variant.get("text_color") or parsed_button["text_color"],
                    }

                parsed_button["modifier_variants"] = parsed_variants

            board["buttons"].append(parsed_button)
            total_buttons += 1

        for board in boards.values():
            board["buttons"].sort(key=lambda b: (int(b.get("row", 0)), int(b.get("col", 0)), int(b.get("location", 0))))
            for idx, button in enumerate(board["buttons"]):
                button["index"] = idx
            board["button_count"] = len(board["buttons"])

        parsed_data: Dict[str, Any] = {
            "file": archive_name,
            "format": "touchchat_ce",
            "total_boards": len(boards),
            "total_buttons": total_buttons,
            "boards": boards,
        }

        return TouchChatExtraction(
            parsed_data=parsed_data,
            temp_dir=temp_dir,
            c4v_path=c4v_path,
            c4s_path=c4s_path,
        )
    except Exception:
        # Caller owns temp cleanup on success; on parse failure clean here.
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        raise
    finally:
        conn.close()


def load_symbol_png_bytes(c4s_path: Optional[str], symbol_rid: Optional[str]) -> Optional[bytes]:
    """Return raw PNG bytes for a symbol RID if available and directly PNG-encoded."""
    if not c4s_path or not symbol_rid:
        return None

    conn = sqlite3.connect(c4s_path)
    try:
        cur = conn.execute(
            "SELECT data FROM symbols WHERE rid = ? LIMIT 1",
            (str(symbol_rid).strip(),),
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return None

        blob = bytes(row[0])
        if blob.startswith(PNG_SIGNATURE):
            return blob
        return None
    finally:
        conn.close()
