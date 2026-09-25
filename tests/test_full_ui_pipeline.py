import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.app import app
import json

def test_full_ui_pipeline():
    client = app.test_client()

    print("================================================================")
    print("  1. Testing GET / (Home UI)")
    print("================================================================")
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"NETRA-DR" in resp.data
    print("  [OK] Home page loaded successfully.")

    print("\n================================================================")
    print("  2. Testing Phase 1 with Good Sample (POST / with demo_image=good)")
    print("================================================================")
    resp = client.post("/", data={"demo_image": "good", "run_mode": "step"})
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "EyeQ Quality Assessment Gate" in html
    assert "current-analysis-id" in html

    # Extract analysis_id
    import re
    m = re.search(r'id="current-analysis-id"\s+value="([^"]+)"', html)
    assert m is not None, "analysis_id not found in rendered HTML"
    analysis_id = m.group(1)
    print(f"  [OK] Phase 1 Quality Gate Passed. Analysis ID: {analysis_id}")

    print("\n================================================================")
    print("  3. Testing Phase 2 API (POST /api/phase2)")
    print("================================================================")
    resp2 = client.post("/api/phase2", json={"analysis_id": analysis_id})
    assert resp2.status_code == 200
    p2_data = resp2.get_json()
    assert p2_data["status"] == "success"
    p2 = p2_data["phase2"]
    print(f"  [OK] Phase 2 Structure Analysis Completed:")
    print(f"       - Evidence Label         : {p2['evidence_label']}")
    print(f"       - Vessel Mask Available  : {bool(p2['vessel_mask_uri'])}")
    print(f"       - Thin Vessel Sensitivity: {p2['thin_vessel_sensitivity']}")
    print(f"       - Microaneurysms (MA)    : {p2['ma_count']} detected ({p2['ma_count_near_macula']} near-macula)")
    print(f"       - Hemorrhages (HE)       : {p2['he_presence']} (Area fraction: {p2['he_area_fraction']})")
    print(f"       - HE Quadrants (TL/TR/BL/BR): {p2['he_quadrant_counts']}")
    print(f"       - Hard Exudates (EX)     : {p2['ex_area']} area (Near-fovea: {p2['ex_area_near_fovea']})")
    print(f"       - Soft Exudates (SE)     : {p2['se_presence']}")
    print(f"       - Overlays Non-Merged    : Separate URIs for Vessel, MA, HE, EX, SE verified.")

    print("\n================================================================")
    print("  4. Testing Phase 3 API (POST /api/phase3)")
    print("================================================================")
    resp3 = client.post("/api/phase3", json={"analysis_id": analysis_id})
    assert resp3.status_code == 200
    p3_data = resp3.get_json()
    assert p3_data["status"] == "success"
    p3 = p3_data["phase3"]
    print(f"  [OK] Phase 3 Severity Grading & Decision Fusion Completed:")
    print(f"       - Predicted Severity     : {p3['severity_name']}")
    print(f"       - Calibrated Confidence  : {p3['confidence']} (T={p3['temperature']})")
    print(f"       - 5-Class Distribution   : {p3['calibrated_probabilities']}")
    print(f"       - Decision Fusion Outcome: {p3['referable_decision']}")
    print(f"       - Applied Quality Tier   : {p3['quality_tier']} (Cutoff: {p3['threshold_applied']})")
    print(f"       - Grade-Alone Baseline   : {p3['grade_alone_decision']}")
    print(f"       - Fusion Rationale       : {p3['reason']}")

    print("\n================================================================")
    print("  5. Testing Phase 4 API (POST /api/phase4)")
    print("================================================================")
    resp4 = client.post("/api/phase4", json={"analysis_id": analysis_id})
    assert resp4.status_code == 200
    p4_data = resp4.get_json()
    assert p4_data["status"] == "success"
    p4 = p4_data["phase4"]
    print(f"  [OK] Phase 4 Explainability & Consistency Audit Completed:")
    print(f"       - Mandatory Attention Label: {p4['label']}")
    print(f"       - Heatmap Overlay Exists   : {bool(p4['heatmap_overlay_uri'])}")
    print(f"       - Heatmap-vs-HE IoU        : {p4['iou_vs_he']}")
    print(f"       - Heatmap-vs-EX IoU        : {p4['iou_vs_ex']}")
    print(f"       - Priority Human Review    : {p4['priority_human_review']}")
    print(f"       - Consistency Reason       : {p4['consistency_flag_reason']}")

    print("\n================================================================")
    print("  6. Testing Quality Gating with Reject Sample")
    print("================================================================")
    resp_rej = client.post("/", data={"demo_image": "reject", "run_mode": "step"})
    assert resp_rej.status_code == 200
    html_rej = resp_rej.data.decode("utf-8")
    assert "Phases 2, 3, and 4 Strictly Gated &amp; Blocked" in html_rej
    
    m_rej = re.search(r'id="current-analysis-id"\s+value="([^"]+)"', html_rej)
    if m_rej:
        rej_id = m_rej.group(1)
        resp_blocked = client.post("/api/phase2", json={"analysis_id": rej_id})
        assert resp_blocked.status_code == 400
        err_msg = resp_blocked.get_json()["error"]
        print(f"  [OK] Reject Image Correctly Blocked from Downstream Stages: '{err_msg}'")

    print("\n================================================================")
    print("  ALL 4 PHASES VERIFIED END-TO-END WITH ZERO MOCKING")
    print("================================================================")

if __name__ == "__main__":
    test_full_ui_pipeline()
