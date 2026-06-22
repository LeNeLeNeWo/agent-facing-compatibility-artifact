# Anonymization Report

Generated: 2026-06-22T08:52:30+00:00

## Copied Directories

- `afc_gate`
- `code`
- `data`
- `docs`
- `figures`
- `results`
- `scripts`
- `tables`

## Excluded Files

- Total excluded candidates: 51
- Excluded categories: `.env`, git history, virtual environments, caches, raw provider logs, raw trajectory dumps, provider-debug logs, WYZ/Grok smoke/debug material, and local IDE metadata.

## Redacted Patterns

- local Windows project roots
- local WSL home paths
- known author/affiliation placeholders
- obvious secret value patterns

## Remaining Warnings

- The package includes environment-variable names such as DEEPSEEK_API_KEY for optional live reruns; these are not secret values.
- License terms are provisional for anonymous review and require author confirmation before public release.

## Confirmation

No obvious secret values are intentionally included. Run `python scripts/scan_for_secrets.py --root .` from the artifact root to regenerate the scan report.
