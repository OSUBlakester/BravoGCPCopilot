#!/usr/bin/env python3

import json
import os
import re
from typing import Any, Dict, List, Optional, Set

import google.genai as genai
import google.genai.types as genai_types

STANDARD_LOCALES: List[str] = [
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "ja",
    "zh",
    "ar",
    "ko",
]

LOCALE_LABELS: Dict[str, str] = {
    "en-US": "English (US)",
    "es": "Spanish",
    "es-US": "Spanish (US)",
    "fr": "French",
    "fr-FR": "French (France)",
    "de": "German",
    "de-DE": "German (Germany)",
    "it": "Italian",
    "it-IT": "Italian (Italy)",
    "pt": "Portuguese",
    "pt-BR": "Portuguese (Brazil)",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "ar-XA": "Arabic",
    "ko": "Korean",
}


def locale_base(locale: Optional[str]) -> str:
    normalized = normalize_locale_tag(locale or "")
    if not normalized:
        return ""
    return normalized.split("-")[0].lower()


def parse_locale_list(raw: Optional[str]) -> List[str]:
    locales: List[str] = []
    for token in str(raw or "").split(","):
        normalized = normalize_locale_tag(token)
        if normalized and normalized not in locales:
            locales.append(normalized)
    return locales


def locale_bases_set(locales: List[str]) -> Set[str]:
    out: Set[str] = set()
    for loc in locales:
        base = locale_base(loc)
        if base:
            out.add(base)
    return out


def normalize_locale_tag(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().replace("_", "-")
    if not cleaned:
        return None

    label_to_locale = {
        "english (us)": "en-US",
        "spanish": "es",
        "spanish (us)": "es-US",
        "french": "fr",
        "french (france)": "fr-FR",
        "german": "de",
        "german (germany)": "de-DE",
        "italian": "it",
        "italian (italy)": "it-IT",
        "portuguese": "pt",
        "portuguese (brazil)": "pt-BR",
        "russian": "ru",
        "japanese": "ja",
        "chinese": "zh",
        "chinese (simplified)": "zh",
        "korean": "ko",
        "arabic": "ar",
        "arabic (experimental)": "ar-XA",
    }

    mapped = label_to_locale.get(cleaned.lower())
    if mapped:
        return mapped

    parts = cleaned.split("-")
    if len(parts) == 1:
        lang = parts[0].lower()
        if len(lang) != 2:
            return None
        return lang

    lang = parts[0].lower()
    region = parts[1].upper()
    if len(lang) != 2 or len(region) < 2:
        return None
    return f"{lang}-{region}"


def sanitize_translated_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r'^[\s"“”‘’`]+', "", text)
    text = re.sub(r'[\s"“”‘’`]+$', "", text)
    text = text.rstrip(",")
    return text.strip()


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        cleaned = sanitize_translated_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _extract_json_array(raw_text: str, expected_count: int) -> List[str]:
    candidate_payloads: List[str] = []
    stripped = (raw_text or "").strip()
    if not stripped:
        raise ValueError("Empty model response")

    candidate_payloads.append(stripped)

    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if fence_match:
        candidate_payloads.append(fence_match.group(1).strip())

    array_match = re.search(r"\[.*\]", stripped, re.DOTALL)
    if array_match:
        candidate_payloads.append(array_match.group(0).strip())

    for payload_text in candidate_payloads:
        try:
            parsed = json.loads(payload_text)
        except Exception:
            continue

        if isinstance(parsed, list):
            lines = [sanitize_translated_text(item) for item in parsed]
            if len(lines) == expected_count:
                return lines

    fallback_lines = [
        sanitize_translated_text(re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line))
        for line in stripped.splitlines()
        if line.strip()
    ]
    if len(fallback_lines) == expected_count:
        return fallback_lines

    raise ValueError("Unable to parse model response as JSON array of expected length")


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    stripped = (raw_text or "").strip()
    if not stripped:
        raise ValueError("Empty model response")

    candidate_payloads: List[str] = [stripped]

    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if fence_match:
        candidate_payloads.append(fence_match.group(1).strip())

    obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if obj_match:
        candidate_payloads.append(obj_match.group(0).strip())

    for payload_text in candidate_payloads:
        try:
            parsed = json.loads(payload_text)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Unable to parse model response as JSON object")


class AacGeminiTranslator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY before running translation scripts.")
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def translate_lines(
        self,
        lines: List[str],
        target_locale: str,
        source_locale: str = "en-US",
    ) -> List[str]:
        clean_lines = [sanitize_translated_text(line) for line in lines]
        if not any(clean_lines):
            return clean_lines

        source_instruction = LOCALE_LABELS.get(source_locale, source_locale)
        target_instruction = LOCALE_LABELS.get(target_locale, target_locale)

        prompt = (
            "You are a translation engine for AAC communication. "
            f"Translate each line from {source_instruction} to {target_instruction}. "
            "If a line is already in the target language, keep it as-is. "
            "Return ONLY valid JSON as an array of strings with exactly the same number of items and same order. "
            "Do not add explanations. Preserve punctuation and intent.\n\n"
            f"LINES_JSON:\n{json.dumps(clean_lines, ensure_ascii=False)}"
        )

        strict_cfg = genai_types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        )

        response_text = ""
        try:
            response = self._client.models.generate_content(
                model=self._model_name, contents=prompt, config=strict_cfg
            )
            response_text = (response.text or "").strip()
            translated = _extract_json_array(response_text, len(clean_lines))
            return [line if line else fallback for line, fallback in zip(translated, clean_lines)]
        except Exception:
            response = self._client.models.generate_content(
                model=self._model_name, contents=prompt
            )
            response_text = (response.text or "").strip()
            translated = _extract_json_array(response_text, len(clean_lines))
            return [line if line else fallback for line, fallback in zip(translated, clean_lines)]

    def expand_terms_with_inflections(
        self,
        terms: List[str],
        locale: str,
        max_forms_per_term: int = 8,
    ) -> Dict[str, List[str]]:
        clean_terms = dedupe_preserve_order([sanitize_translated_text(term) for term in terms])
        if not clean_terms:
            return {}

        locale_norm = normalize_locale_tag(locale) or locale
        locale_instruction = LOCALE_LABELS.get(locale_norm, locale_norm)

        prompt = (
            "You are an AAC linguistic helper. "
            f"For each term, provide common inflected forms in {locale_instruction} that users may type/select. "
            "Include person/number conjugations for verbs when applicable. "
            "Do not translate into other words; only inflectional variants of the same lemma/term. "
            "Return ONLY valid JSON object: {\"term\": [\"variant1\", ...]}. "
            "Each variant should be short, natural, and de-duplicated. "
            f"Limit each list to at most {max_forms_per_term} items.\n\n"
            f"TERMS_JSON:\n{json.dumps(clean_terms, ensure_ascii=False)}"
        )

        response = self._client.models.generate_content(
            model=self._model_name, contents=prompt
        )
        response_text = (response.text or "").strip()
        parsed = _extract_json_object(response_text)

        output: Dict[str, List[str]] = {}
        for term in clean_terms:
            raw_values = parsed.get(term)
            if not isinstance(raw_values, list):
                output[term] = [term]
                continue

            normalized = dedupe_preserve_order([
                sanitize_translated_text(item) for item in raw_values
            ])
            if term not in normalized:
                normalized = dedupe_preserve_order([term, *normalized])

            output[term] = normalized[:max_forms_per_term]

        return output


def expand_locale_tags_with_inflections(
    translator: AacGeminiTranslator,
    locale: str,
    tags: List[str],
    enabled_locale_bases: Set[str],
    max_forms_per_term: int = 8,
) -> List[str]:
    base = locale_base(locale)
    if not base or base not in enabled_locale_bases:
        return dedupe_preserve_order(tags)

    clean_tags = dedupe_preserve_order([sanitize_translated_text(tag) for tag in tags])
    if not clean_tags:
        return clean_tags

    try:
        expanded_map = translator.expand_terms_with_inflections(
            terms=clean_tags,
            locale=locale,
            max_forms_per_term=max_forms_per_term,
        )
        flattened: List[str] = []
        for tag in clean_tags:
            flattened.extend(expanded_map.get(tag, [tag]))
        return dedupe_preserve_order(flattened)
    except Exception:
        # Safe fallback: retain original tags if inflection generation fails.
        return clean_tags