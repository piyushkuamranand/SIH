"""
tests/test_phase1_prototype.py — End-to-End Tests for Phase 1 EyeQ Prototype

Tests:
1. GET /: renders upload interface and demo quick-actions.
2. POST / (demo good sample): runs EyeQ, outputs GOOD quality label, passes quality gate.
3. POST / (demo reject sample): runs EyeQ, outputs REJECT quality label, halts downstream pipeline.
4. POST / (invalid file): input validation rejects non-image or corrupted files.
5. POST /api/quality: programmatic JSON API evaluates image quality.
6. GET /api/status: returns model readiness and operational status.
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
    assert "Phase 1: EyeQ Quality Assessment" in html
    assert "Upload Fundus Image" in html
    assert "Good Sample" in html
    assert "Reject Sample" in html


def test_post_demo_good_image(client):
    """POST / with demo_image=good should evaluate to GOOD."""
    res = client.post("/", data={"demo_image": "good"})
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Phase 1 — EyeQ Quality Assessment Result" in html
    assert "GOOD" in html
    assert "Quality Gate Passed" in html
    assert "PROCEED" in html


def test_post_demo_reject_image(client):
    """POST / with demo_image=reject should evaluate to REJECT and halt."""
    res = client.post("/", data={"demo_image": "reject"})
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Phase 1 — EyeQ Quality Assessment Result" in html
    assert "REJECT" in html
    assert "Recapture Advised" in html
    assert "HALT" in html
    assert "Phases 2–4 Halted" in html


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


def test_api_quality_endpoint_json(client):
    """POST /api/quality with image_path JSON payload."""
    res = client.post(
        "/api/quality",
        json={"image_path": str(GOOD_SAMPLE)},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["quality_label"] == "GOOD"
    assert data["quality_score"] > 0.95
    assert data["action"] == "PROCEED"
    assert "probabilities" in data
    assert "good" in data["probabilities"]


def test_api_quality_endpoint_reject(client):
    """POST /api/quality with reject image."""
    res = client.post(
        "/api/quality",
        json={"image_path": str(REJECT_SAMPLE)},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["quality_label"] == "REJECT"
    assert data["action"] == "HALT"


def test_api_status_endpoint(client):
    """GET /api/status returns operational status and EyeQ readiness."""
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "operational"
    assert data["phase1_eyeq"]["available"] is True
