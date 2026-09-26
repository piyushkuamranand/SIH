"""
tests/test_web_app.py — End-to-End Tests for the NETRA-DR Web Prototype

Tests:
1. GET /: renders upload interface and demo quick-actions.
2. POST / (demo good sample): runs the full pipeline, GOOD quality passes the gate.
3. POST / (demo reject sample): runs Phase 1 only; REJECT halts downstream phases.
4. POST / (invalid file): input validation rejects non-image or corrupted files.
5. POST /api/grade: programmatic JSON API runs the full pipeline.
6. GET /api/status: returns per-model readiness and operational status.

Phase 2–4 model artifacts may not be delivered yet (see models/*/metadata.json);
these tests only assert on Phase 1 (which has a working rule-based baseline) and
on graceful "unavailable" behaviour for the not-yet-trained phases — never a crash.
"""

from __future__ import annotations

import io
from pathlib import Path
import pytest

from app.app import app

ROOT = Path(__file__).resolve().parent.parent
GOOD_SAMPLE = ROOT / "data" / "demo" / "good_sample.jpg"
REJECT_SAMPLE = ROOT / "data" / "demo" / "reject_sample.jpg"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_get_upload_page(client):
    """GET / should render successfully with upload options."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "NETRA-DR" in html
    assert "Image Intake" in html
    assert "Good Sample" in html
    assert "Reject Sample" in html


def test_post_demo_good_image(client):
    """POST / with demo_image=good should pass the Phase 1 quality gate."""
    res = client.post("/", data={"demo_image": "good"})
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Phase 1" in html
    assert "GOOD" in html
    assert "Quality Gate Passed" in html
    assert "PROCEED" in html


def test_post_demo_reject_image(client):
    """POST / with demo_image=reject should evaluate to REJECT and halt at Phase 1."""
    res = client.post("/", data={"demo_image": "reject"})
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "REJECT" in html
    assert "Recapture Advised" in html
    assert "HALT" in html


def test_post_file_upload_good(client):
    """POST / with genuine good fundus image file upload."""
    with open(GOOD_SAMPLE, "rb") as f:
        file_bytes = io.BytesIO(f.read())

    res = client.post(
        "/",
        data={"image": (file_bytes, "test_good.jpg")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "GOOD" in html
    assert "Quality Gate Passed" in html


def test_post_invalid_file_rejected(client):
    """POST / with text file instead of image should fail validation."""
    fake_file = io.BytesIO(b"This is not a real image file.")
    res = client.post(
        "/",
        data={"image": (fake_file, "fake.jpg")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Invalid image file" in html


def test_api_grade_endpoint_json(client):
    """POST /api/grade with image_path JSON payload runs the full pipeline."""
    res = client.post(
        "/api/grade",
        json={"image_path": str(GOOD_SAMPLE)},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["quality"]["label"] == "GOOD"
    assert "grading" in data
    assert "explainability" in data


def test_api_grade_endpoint_reject(client):
    """POST /api/grade with a reject-quality image halts at Phase 1."""
    res = client.post(
        "/api/grade",
        json={"image_path": str(REJECT_SAMPLE)},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["quality"]["label"] == "REJECT"
    assert data["stopped_at_phase1"] is True


def test_api_status_endpoint(client):
    """GET /api/status returns operational status and per-model readiness."""
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "operational"
    assert "startup_report" in data
    assert "items" in data["startup_report"]
