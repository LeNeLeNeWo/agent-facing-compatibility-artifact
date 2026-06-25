# Phase 12L Final Consistency Audit

- Status: pass
- Paper directory: `<HOME>/ICSE 2027/schema_mutation_paper_package_20260612_194214/IEEE_Conference_Template`
- Page count: 10
- Phase 12K integrated Address Element: True
- Blocking issues: 0

## Replay Count Consistency

```json
{
  "abstract_says_three": true,
  "abstract_says_two": false,
  "conclusion_says_three": true,
  "consistent": true,
  "fig1_caption_illustrative_only": false,
  "fig1_caption_replayed": true,
  "finding4_says_three": true,
  "finding4_says_two": false,
  "phase12k_integrated": true,
  "section2_illustrative_only": false,
  "section2_replayed": true
}
```

## Table II Check

```json
{
  "expected_rows": {
    "baseline_old_api": {
      "hidden": 0,
      "hidden_den": 36,
      "success": 36,
      "success_den": 36
    },
    "evolved_o0_silent": {
      "hidden": 29,
      "hidden_den": 35,
      "success": 6,
      "success_den": 35
    },
    "evolved_visible_feedback": {
      "hidden": 0,
      "hidden_den": 35,
      "success": 34,
      "success_den": 35
    }
  },
  "matches_expected": true,
  "note_has_106_ok_108_terminal": true,
  "note_has_286_ok_control": true,
  "parsed_rows": {
    "baseline_old_api": {
      "hidden": 0,
      "hidden_den": 36,
      "success": 36,
      "success_den": 36
    },
    "evolved_o0_silent": {
      "hidden": 29,
      "hidden_den": 35,
      "success": 6,
      "success_den": 35
    },
    "evolved_visible_feedback": {
      "hidden": 0,
      "hidden_den": 35,
      "success": 34,
      "success_den": 35
    }
  }
}
```

## Address Element Formal

```json
{
  "by_condition": {
    "baseline_old_api": {
      "hidden": 0,
      "ok": 12,
      "success": 12
    },
    "evolved_o0_silent": {
      "hidden": 6,
      "ok": 12,
      "success": 6
    },
    "evolved_visible_feedback": {
      "hidden": 0,
      "ok": 12,
      "success": 12
    }
  },
  "deterministic_oracle_worked": true,
  "planned_cells": 36,
  "real_third_party_api_call_rows": [],
  "rule_leakage_rows": [],
  "run_cells": 36,
  "status_counts": {
    "ok": 36
  }
}
```

## Forbidden Claims

```json
{
  "cohens_kappa": {
    "allowed_negative_context_present": false,
    "blocking": false,
    "matches": 0
  },
  "human_validated_oracle_precision": {
    "allowed_negative_context_present": false,
    "blocking": false,
    "matches": 0
  },
  "live_stripe_experiment": {
    "allowed_negative_context_present": false,
    "blocking": false,
    "matches": 0
  },
  "production_frequency_estimate": {
    "allowed_negative_context_present": true,
    "blocking": false,
    "matches": 0
  },
  "production_incident": {
    "allowed_negative_context_present": true,
    "blocking": false,
    "matches": 2
  }
}
```

## Citation, Artifact Link, Security

```json
{
  "author_identity_patterns": {
    "email": false,
    "local_home_path_flag": false,
    "institution_keyword_flag": false,
    "local_account_flag": false
  },
  "four_open_link_present": true,
  "placeholder_patterns": false,
  "provider_debug_patterns": {
    "grok": false,
    "winerror": false,
    "wyz": false
  },
  "real_github_url_present": false,
  "secret_patterns": {
    "api_key": false,
    "bearer": false,
    "github_pat": false,
    "sk": false
  },
  "stripe2026addressstateformat_defined": true,
  "stripe2026addressstateformat_used": true
}
```

## Readability and Paths

```json
{
  "fig1_inset_readable_manual_preview": "checked_in_phase12l",
  "fig4_lower_is_better": true,
  "included_paths": {
    "figures": {
      "figures/c_semantic_generalization_v2.pdf": true,
      "figures/combined_observability_main_v2.pdf": true,
      "figures/exposure_aware_paired_protocol.drawio.pdf": true,
      "figures/exposure_control_contrast_v2.pdf": true,
      "figures/fig1_compliant_semantic_failure.pdf": true
    },
    "tables": {
      "tables/grounding_controls_auto": true,
      "tables/taxonomy": true,
      "tables/trace_case_box_auto": true
    }
  },
  "missing_figures": [],
  "missing_tables": [],
  "table_ii_note_present": true
}
```

## Blocking Issues

- None.
