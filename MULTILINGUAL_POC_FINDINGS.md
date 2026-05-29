# Multilingual POC Findings and Plan

Date: 2026-05-07
Scope: Read-only architecture review of current Bravo app to prepare a safe multilingual proof of concept (POC).

## Executive Summary

A multilingual rollout is feasible, but current runtime behavior is tightly coupled to American English in key speech and prompt pathways. The safest path is a separate POC project (or long-lived POC branch) that introduces language controls without destabilizing production.

Primary recommendation: Split language behavior into three independent channels per user.

- Listening language: speech recognition and wake-word detection locale
- Generation language: LLM option/prompt language
- Output language: spoken TTS announcement language

This enables your target scenario:

- User-facing options/prompts in Spanish
- Wake word and audible announcements in English

## Confirmed Findings (Current Codebase)

1. Speech recognition locale is hard-coded to English US.
- `questionRecognitionInstance.lang = 'en-US'`

2. TTS synthesis uses a hard-coded English US language code.
- `VoiceSelectionParams(language_code="en-US", name=voice_name)`

3. Available TTS voices endpoint is filtered to English US only.
- `list_voices(language_code="en-US")`

4. Wake-word defaults are English-centric.
- Interjection/name defaults are effectively "Hey" + "Friend" and client fallback values are "hey" and "friend/bravo".

5. LLM prompts and follow-up prompt templates are heavily English-authored and assume English output behavior.

6. Settings schema does not currently separate recognition locale, generation locale, and output locale.

## Why This Is High-Risk Without a POC

- Replacing English assumptions in-place can regress wake-word reliability and scanning flows.
- LLM output language can drift without strict prompt constraints and post-validation.
- Voice inventory and pronunciation quality vary by locale and voice family.
- Translation inserted inline may increase latency and impair fast-turn AAC interactions.

## Recommended POC Architecture

## 1) Add Language Profile Settings

Create explicit per-user language controls:

- `recognition_locale` (example: `en-US`)
- `generation_locale` (example: `es-ES`)
- `announcement_locale` (example: `en-US`)
- `wakeword_locale` (optional; defaults to recognition locale)
- `translation_mode` (`off`, `source_to_target`, `dual`)
- `translation_target_locale` (optional, used when mode requires)

Optional but useful:

- `strict_generation_language` (bool)
- `fallback_generation_locale` (example: `en-US`)

## 2) Make STT/TTS Locale-Aware

- Speech recognition:
  - Set recognition language from `recognition_locale`.
  - Keep fallback to `en-US` if unset.

- TTS synthesis:
  - Derive TTS `language_code` from selected voice metadata or `announcement_locale`.
  - Avoid hard-coded `en-US`.

- Voice listing:
  - Return voices for requested locale (or grouped by locale) instead of only `en-US`.

## 3) Make LLM Output Locale-Aware

- Inject explicit generation policy into prompt construction:
  - Required output language
  - No language mixing
  - Keep AAC style constraints intact

- Add response validation:
  - Detect wrong-language drift and retry once with stricter constraints.

## 4) Externalize System Strings

Move hard-coded UI and announcement strings into locale bundles.

Suggested structure:

- `i18n/en-US.json`
- `i18n/es-ES.json`

Initial scope should include:

- Scanning prompts
- Error announcements
- Listening confirmations
- Email flow system announcements

## 5) Add Translation Path

Support translation for selected text and/or generated options:

- `off`: no translation
- `source_to_target`: translate source text to target locale
- `dual`: preserve source and translated form (for caregiver/context use)

For AAC UX, default to low-friction behavior:

- Generate directly in `generation_locale` whenever possible
- Translate only where cross-language communication is needed

## POC Feature Slice (Minimal, High-Value)

Implement one vertical path first:

1. Grid flow only (not Tap + Grid at once)
2. Spanish generation (`generation_locale=es-ES`)
3. English wake word + announcements (`recognition_locale=en-US`, `announcement_locale=en-US`)
4. Translation endpoint for selected phrase (Spanish -> English) before final spoken announcement, toggle-controlled

Success criteria:

- Wake word still activates reliably in English
- User sees LLM options in Spanish consistently
- Announcements remain English when configured
- End-to-end latency remains acceptable for AAC turn-taking

## Validation Matrix for POC

Core test cases:

1. Monolingual baseline (all en-US)
2. Bilingual target (es-ES generation, en-US wake/announce)
3. Missing locale fallback behavior
4. Unsupported voice fallback behavior
5. LLM wrong-language retry behavior
6. Translation on/off/double-output modes

Accessibility and UX checks:

- No extra taps required for standard flow
- Scan timing unchanged or configurable
- Error messages remain understandable in configured UI language

## Suggested Implementation Sequence

1. Introduce language settings model and defaults.
2. Thread locale settings into STT setup and `/play-audio` path.
3. Update voice catalog endpoint to locale-aware behavior.
4. Add generation locale policy to `/llm` prompt assembly.
5. Add lightweight language validation/retry.
6. Externalize highest-frequency system announcements to i18n files.
7. Add translation mode endpoint/path for selected phrases.
8. Run focused latency and usability tests.

## Non-Goals for First POC

- Full localization of every admin screen
- Full parity across both Grid and Tap flows on day one
- Automatic language detection for every utterance
- Bulk migration of existing board text into multilingual variants

## Open Decisions

1. Should wake-word language always match recognition locale, or be separately configurable?
2. Should translated output replace original text or be optional dual output?
3. Should caregiver/admin UI remain English-only in POC?
4. Do we enforce one generation locale per session or allow per-board override?

## Practical Recommendation

Create the POC as a separate project copy, keep production unchanged, and prove one bilingual end-to-end path before broad rollout. This minimizes risk while giving fast evidence on quality, latency, and usability.
