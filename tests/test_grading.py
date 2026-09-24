"""
tests/test_grading.py — Unit and integration tests for pipeline/grading.py (TASK-010).

Test coverage:
1. Missing metadata.json -> clear "model artifact missing" FileNotFoundError.
2. Incomplete metadata.json (missing required classifier field) -> ModelContractError.
3. Complete metadata.json but missing ONNX file -> clear ModelArtifactNotFoundError.
4. Invalid image inputs (wrong ndim, channels, types) -> ValueError.
5. Missing image file path -> FileNotFoundError.
6. Mocked ONNX inference tests:
   - Output probabilities sum to 1.0
   - severity_class is int and matches argmax(probabilities)
   - Contract class_labels length matches output dimension
   - ResNet-50 and backup EfficientNet-B0 backbones correctly reflected in metadata
   - Both float32 and uint8 preprocessed images accepted
7. Return schema and signature verification (type hints, docstring).
8. Real ONNX integration test (runs if real artifact present, skipped otherwise).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from pipeline.contract import ModelArtifactNotFoundError, ModelContractError
from pipeline.grading import run_grading


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_complete_grading_metadata(
    model_file: str = "dr_grading.onnx",
    model_name: str = "resnet50_dr_grading",
    output_format: str = "softmax",
) -> dict:
    """Return a fully-populated metadata.json dict for the grading model classifier contract."""
    return {
        "model_name": model_name,
        "model_version": "1.0.0",
        "input_size": [224, 224],
        "channels": 3,
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std":  [0.229, 0.224, 0.225],
        },
        "model_file": model_file,
        "framework": "onnx",
        "training_dataset": "APTOS+DDR",
        "preprocessing": "FOV crop, resize, CLAHE, normalize",
        "eval_metrics": {"accuracy": 0.88, "kappa": 0.85},
        "class_labels": ["0", "1", "2", "3", "4"],
        "output_format": output_format,
        "threshold": 0.5,
    }


def _make_dummy_preprocessed_image(h: int = 224, w: int = 224, dtype=np.float32) -> np.ndarray:
    """Return a random HWC array simulating a preprocessed fundus image."""
    rng = np.random.default_rng(42)
    if dtype == np.float32:
        return rng.random((h, w, 3)).astype(np.float32)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# 1. Missing artifact error paths
# ---------------------------------------------------------------------------

class TestGradingMissingArtifacts(unittest.TestCase):
    """Verify that missing or invalid artifacts fail loudly and specifically."""

    def test_missing_metadata_json_raises_file_not_found(self):
        """run_grading with an empty model_dir raises a clear FileNotFoundError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with self.assertRaises(FileNotFoundError) as ctx:
                run_grading(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("model artifact missing", error_msg.lower())
            self.assertIn("Phase 3", error_msg)

    def test_incomplete_metadata_json_raises_contract_error(self):
        """Metadata missing required classifier fields raises ModelContractError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            incomplete = _make_complete_grading_metadata()
            incomplete.pop("class_labels")  # Missing mandatory classifier field
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(incomplete), encoding="utf-8"
            )
            with self.assertRaises(ModelContractError) as ctx:
                run_grading(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("class_labels", error_msg)

    def test_complete_metadata_but_missing_onnx_raises_artifact_error(self):
        """Complete metadata.json but no ONNX file raises ModelArtifactNotFoundError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata(model_file="dr_grading.onnx")
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            with self.assertRaises(ModelArtifactNotFoundError) as ctx:
                run_grading(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("model artifact missing", error_msg.lower())
            self.assertIn("dr_grading.onnx", error_msg)
            self.assertIn("Phase 3", error_msg)


# ---------------------------------------------------------------------------
# 2. Input validation
# ---------------------------------------------------------------------------

class TestGradingInputValidation(unittest.TestCase):
    """Verify input dimension and format validation."""

    def test_invalid_image_shape_raises_value_error(self):
        """2D or 4D image array raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata()
            (tmpdir_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (tmpdir_path / "dr_grading.onnx").write_text("fake onnx", encoding="utf-8")

            # 2D array
            with self.assertRaises(ValueError):
                run_grading(preprocessed_image=np.zeros((224, 224)), model_dir=tmpdir_path)

            # 4D array
            with self.assertRaises(ValueError):
                run_grading(preprocessed_image=np.zeros((1, 224, 224, 3)), model_dir=tmpdir_path)

            # 3D with 1 channel
            with self.assertRaises(ValueError):
                run_grading(preprocessed_image=np.zeros((224, 224, 1)), model_dir=tmpdir_path)

    def test_invalid_image_type_raises_value_error(self):
        """Passing non-array / non-path raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata()
            (tmpdir_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (tmpdir_path / "dr_grading.onnx").write_text("fake onnx", encoding="utf-8")

            with self.assertRaises(ValueError):
                run_grading(preprocessed_image=12345, model_dir=tmpdir_path)

    def test_nonexistent_image_path_raises_file_not_found(self):
        """Passing nonexistent path raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata()
            (tmpdir_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (tmpdir_path / "dr_grading.onnx").write_text("fake onnx", encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                run_grading(preprocessed_image="nonexistent_image_path_12345.jpg", model_dir=tmpdir_path)


# ---------------------------------------------------------------------------
# 3. Mocked inference tests
# ---------------------------------------------------------------------------

class TestGradingMockedInference(unittest.TestCase):
    """Verify inference pipeline mechanics using mocked ONNX runtime session."""

    def _setup_mock_session(self, raw_output: np.ndarray):
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_session.get_inputs.return_value = [mock_input]
        mock_session.run.return_value = [raw_output]
        return mock_session

    @patch("onnxruntime.InferenceSession")
    def test_inference_returns_valid_probabilities_and_argmax(self, mock_ort):
        """Mocked inference produces probabilities summing to 1.0 and correct severity_class."""
        # Mock output with class 2 having the highest score
        mock_output = np.array([[0.05, 0.10, 0.70, 0.10, 0.05]], dtype=np.float32)
        mock_ort.return_value = self._setup_mock_session(mock_output)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata(model_name="resnet50_dr_grading")
            (tmpdir_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (tmpdir_path / "dr_grading.onnx").write_text("dummy", encoding="utf-8")

            img = _make_dummy_preprocessed_image(224, 224, dtype=np.float32)
            result = run_grading(preprocessed_image=img, model_dir=tmpdir_path)

            self.assertIn("severity_class", result)
            self.assertIn("probabilities", result)
            self.assertIn("model_name", result)
            self.assertIn("metadata", result)

            self.assertEqual(result["severity_class"], 2)
            self.assertEqual(len(result["probabilities"]), 5)
            self.assertAlmostEqual(sum(result["probabilities"]), 1.0, places=5)
            self.assertEqual(result["model_name"], "resnet50_dr_grading")
            self.assertEqual(result["metadata"]["backbone"], "resnet50_dr_grading")

    @patch("onnxruntime.InferenceSession")
    def test_efficientnet_backup_backbone_exposed_in_metadata(self, mock_ort):
        """Backup EfficientNet-B0 backbone must be visible in metadata output."""
        mock_output = np.array([[0.80, 0.10, 0.05, 0.03, 0.02]], dtype=np.float32)
        mock_ort.return_value = self._setup_mock_session(mock_output)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata(
                model_name="efficientnet_b0_dr_grading",
                model_file="efficientnet_b0.onnx",
            )
            (tmpdir_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (tmpdir_path / "efficientnet_b0.onnx").write_text("dummy", encoding="utf-8")

            img = _make_dummy_preprocessed_image(224, 224, dtype=np.uint8)
            result = run_grading(preprocessed_image=img, model_dir=tmpdir_path)

            self.assertEqual(result["severity_class"], 0)
            self.assertEqual(result["model_name"], "efficientnet_b0_dr_grading")
            self.assertEqual(result["metadata"]["backbone"], "efficientnet_b0_dr_grading")

    @patch("onnxruntime.InferenceSession")
    def test_logits_output_format_converted_with_softmax(self, mock_ort):
        """Unnormalized logits are converted to valid softmax probabilities."""
        mock_logits = np.array([[-2.0, 1.0, 4.0, 0.5, -1.0]], dtype=np.float32)
        mock_ort.return_value = self._setup_mock_session(mock_logits)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_grading_metadata(output_format="logits")
            (tmpdir_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (tmpdir_path / "dr_grading.onnx").write_text("dummy", encoding="utf-8")

            img = _make_dummy_preprocessed_image(224, 224)
            result = run_grading(preprocessed_image=img, model_dir=tmpdir_path)

            self.assertEqual(result["severity_class"], 2)
            self.assertAlmostEqual(sum(result["probabilities"]), 1.0, places=5)
            for p in result["probabilities"]:
                self.assertGreaterEqual(p, 0.0)
                self.assertLessEqual(p, 1.0)


# ---------------------------------------------------------------------------
# 4. Return schema and type hints
# ---------------------------------------------------------------------------

class TestGradingReturnSchema(unittest.TestCase):
    """Verify function signature, annotations, and docstrings."""

    def test_function_has_return_type_hint(self):
        """run_grading has return type annotation."""
        hints = run_grading.__annotations__
        self.assertIn("return", hints)

    def test_function_docstring_describes_keys(self):
        """Docstring contains required output keys."""
        doc = run_grading.__doc__ or ""
        for key in ("severity_class", "probabilities", "model_name", "class_labels"):
            self.assertIn(key, doc)


# ---------------------------------------------------------------------------
# 5. Integration tests (Real ONNX artifact)
# ---------------------------------------------------------------------------

class TestGradingIntegration(unittest.TestCase):
    """Integration tests running with real models/grading artifacts if present."""

    REAL_MODEL_DIR = Path("models/grading")

    @unittest.skipUnless(
        Path("models/grading/metadata.json").is_file()
        and any(Path("models/grading").glob("*.onnx")),
        "Skipped: grading model artifact not yet available (MATLAB export pending).",
    )
    def test_real_model_inference_on_fixture(self):
        """Inference on fixture image produces valid class in 0..4 and normalized probabilities."""
        fixture_path = Path("tests/fixtures/sample_fundus.jpg")
        self.assertTrue(fixture_path.is_file(), "Fixture image missing.")

        result = run_grading(preprocessed_image=fixture_path, model_dir=self.REAL_MODEL_DIR)

        self.assertIn("severity_class", result)
        self.assertIn("probabilities", result)
        self.assertIsInstance(result["severity_class"], int)
        self.assertIn(result["severity_class"], [0, 1, 2, 3, 4])
        self.assertEqual(len(result["probabilities"]), 5)
        self.assertAlmostEqual(sum(result["probabilities"]), 1.0, places=4)
        self.assertEqual(result["severity_class"], int(np.argmax(result["probabilities"])))


if __name__ == "__main__":
    unittest.main()
