from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_required_files_exist():
    required = [
        "README.md",
        "ARTIFACT_EVALUATION.md",
        "DATASET_CARD.md",
        "REPRODUCTION_GUIDE.md",
        "requirements.txt",
        "code/schema_mutation/runner.py",
        "afc_gate/README.md",
        "results/main_results/phase5_summary.json",
        "results/phase10_nonobviousness/nonobviousness_analysis_report.json",
        "results/phase10_real_case_replay/real_case_formal_summary.json",
        "tables/generated_tex/nonobviousness_control_auto.tex",
        "tables/generated_tex/real_case_replay_auto.tex",
        "figures/pdf/real_case_replay.pdf",
    ]
    missing = [rel for rel in required if not (ROOT / rel).exists()]
    assert not missing


def test_headline_numbers():
    h = load_json("docs/reproduction_headlines.json")
    assert h["strict_schema_client"] == {"agent_breaking": 44, "n": 130, "rate": 0.338}
    assert h["relaxed_schema_client_yp"]["agent_breaking"] == 49
    assert h["phase8_exposure_control"]["exposed_o0_n"] == 363
    assert h["phase8_exposure_control"]["unused_control_n"] == 363
    assert h["phase5_formal_cells"] == {"airline": 1290, "retail": 525, "total": 1815}
    assert h["phase10_real_api_corpus"]["entries"] == 151
    assert h["phase10_real_api_corpus"]["c_class_candidates"] == 61
    assert h["phase10_real_replay"]["baseline_success"] == "24/24"
    assert h["phase10_real_replay"]["o0_silent_success"] == "0/23"
    assert h["phase10_real_replay"]["visible_feedback_success"] == "22/23"
    assert h["phase10_nonobviousness"]["o0_more_reasoning_success"] == "3/96"
    assert h["phase10_nonobviousness"]["o0_reflection_success"] == "6/95"
    assert h["phase10_nonobviousness"]["rule_visible_success"] == "71/95"


def test_phase10_summary_values():
    replay = load_json("results/phase10_real_case_replay/real_case_formal_summary.json")
    assert replay["status_counts"] == {"failed": 2, "ok": 70}
    assert replay["by_condition"]["baseline_old_api"]["success_n"] == 24
    assert replay["by_condition"]["evolved_o0_silent"]["hidden_violation_n"] == 23
    assert replay["by_condition"]["evolved_visible_feedback"]["success_n"] == 22
    nonobv = load_json("results/phase10_nonobviousness/nonobviousness_analysis_report.json")
    by_cond = nonobv.get("condition_summary") or nonobv.get("condition_results")
    assert by_cond["O0_increased_reasoning_budget"]["success_n"] == 3
    assert by_cond["O0_reflection_scaffold"]["success_n"] == 6
    assert by_cond["rule_in_tool_preamble_upper_bound"]["success_n"] == 71
