"""
Unit tests for pipeline/structure.py -- TASK-008 (MA detector).

Test coverage:
1. Missing metadata.json -> clear model artifact missing FileNotFoundError.
2. Incomplete metadata.json (missing required ma_detector field) -> ModelContractError.
3. Complete metadata.json but missing FP-reducer ONNX file -> ModelArtifactNotFoundError.
4. Unsupported candidate_extraction_method -> ValueError naming the method.
5. Non-3-D preprocessed_image -> ValueError (or ModelArtifactNotFoundError fires first).
6. Return-schema: function has return type hint and docstring with all output keys.
7. Two-stage architecture: source reads candidate_extraction_method from contract;
   Stage A classical extraction runs before Stage B CNN.
8. Classical extractors: basic sanity checks without ONNX model.
9. MA overlay helper: shape/dtype without ONNX model.
10. (Integration, requires real ONNX model) -- skipped when artifact absent.
    Verifies: ma_count is a non-negative int; ma_overlay is HWC uint8 BGR.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline.contract import ModelArtifactNotFoundError, ModelContractError
from pipeline.structure import run_ma_detection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_complete_ma_metadata(
    fp_reducer_file: str = "ma_fp_reducer.onnx",
    candidate_method: str = "top_hat",
) -> dict:
    """Return a fully-populated metadata.json dict for the MA detector contract."""
    return {
        "model_name":                   "ma_detector_test",
        "model_version":                "0.0.0",
        "input_size":                   [512, 512],
        "channels":                     3,
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std":  [0.229, 0.224, 0.225],
        },
        "model_file":                   fp_reducer_file,
        "framework":                    "onnx",
        "training_dataset":             "e-ophtha-MA",
        "preprocessing":                "FOV crop, resize, CLAHE, normalize",
        "eval_metrics":                 {"froc": 0.0},
        # MA-detector-type required fields
        "candidate_extraction_method":  candidate_method,
        "fp_reducer_model_file":        fp_reducer_file,
        "output_format":                "softmax",
        # Optional fields consumed by run_ma_detection
        "patch_size":                   32,
        "ma_positive_class_index":      1,
        "tophat_disk_radius":           6,
        "tophat_threshold_factor":      2.0,
        "matched_filter_sigma":         1.0,
        "matched_filter_threshold_factor": 2.0,
    }


def _make_dummy_preprocessed_image(h: int = 224, w: int = 224) -> np.ndarray:
    """Return a random HWC float32 array simulating a preprocessed fundus image."""
    rng = np.random.default_rng(42)
    return rng.random((h, w, 3)).astype(np.float32)


# ---------------------------------------------------------------------------
# Missing-artifact error paths (no real model needed)
# ---------------------------------------------------------------------------

class TestMADetectionMissingArtifacts(unittest.TestCase):
    """Verify that missing-artifact situations fail loudly and specifically."""

    def test_missing_metadata_json_raises_file_not_found(self):
        """run_ma_detection with an empty model_dir raises a clear FileNotFoundError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with self.assertRaises(FileNotFoundError) as ctx:
                run_ma_detection(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("model artifact missing", error_msg.lower())
            self.assertIn("Phase 2", error_msg)
            self.assertIn("MA detection", error_msg)

    def test_incomplete_metadata_missing_candidate_method_raises_contract_error(self):
        """Metadata missing candidate_extraction_method -> ModelContractError naming the field."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            incomplete = _make_complete_ma_metadata()
            incomplete.pop("candidate_extraction_method")
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(incomplete), encoding="utf-8"
            )
            with self.assertRaises(ModelContractError) as ctx:
                run_ma_detection(preprocessed_image=image, model_dir=tmpdir_path)
            self.assertIn("candidate_extraction_method", str(ctx.exception))

    def test_incomplete_metadata_missing_fp_reducer_raises_contract_error(self):
        """Metadata missing fp_reducer_model_file -> ModelContractError naming the field."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            incomplete = _make_complete_ma_metadata()
            incomplete.pop("fp_reducer_model_file")
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(incomplete), encoding="utf-8"
            )
            with self.assertRaises(ModelContractError) as ctx:
                run_ma_detection(preprocessed_image=image, model_dir=tmpdir_path)
            self.assertIn("fp_reducer_model_file", str(ctx.exception))

    def test_complete_metadata_but_missing_onnx_raises_artifact_error(self):
        """Complete metadata.json but no FP-reducer ONNX -> ModelArtifactNotFoundError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_ma_metadata(fp_reducer_file="ma_fp_reducer.onnx")
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            # Deliberately do NOT create ma_fp_reducer.onnx
            with self.assertRaises(ModelArtifactNotFoundError) as ctx:
                run_ma_detection(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("model artifact missing", error_msg.lower())
            self.assertIn("Phase 2", error_msg)
            self.assertIn("ma_fp_reducer.onnx", error_msg)

    def test_unsupported_candidate_method_raises_value_error(self):
        """An unrecognised candidate_extraction_method raises ValueError naming the method."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_ma_metadata(candidate_method="neural_magic")
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            # Create a dummy ONNX placeholder so the file-existence check passes
            (tmpdir_path / "ma_fp_reducer.onnx").write_bytes(b"\x00" * 4)
            with self.assertRaises(ValueError) as ctx:
                run_ma_detection(preprocessed_image=image, model_dir=tmpdir_path)
            self.assertIn("neural_magic", str(ctx.exception))

    def test_non_3d_image_raises_value_error_or_artifact_error(self):
        """A 2-D preprocessed_image raises ValueError (or artifact error fires first)."""
        bad_image = np.zeros((224, 224), dtype=np.float32)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_ma_metadata()
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            with self.assertRaises((ValueError, ModelArtifactNotFoundError)):
                run_ma_detection(preprocessed_image=bad_image, model_dir=tmpdir_path)


# ---------------------------------------------------------------------------
# Return schema (no model needed)
# ---------------------------------------------------------------------------

class TestMADetectionReturnSchema(unittest.TestCase):
    """Verify function signature, type hints, and docstring without running inference."""

    def test_function_has_return_type_hint(self):
        hints = run_ma_detection.__annotations__
        self.assertIn("return", hints, "run_ma_detection missing return type annotation.")

    def test_function_docstring_describes_all_output_keys(self):
        doc = run_ma_detection.__doc__ or ""
        for key in ("ma_count", "ma_overlay"):
            self.assertIn(key, doc, f"Docstring does not mention output key {key!r}.")

    def test_function_docstring_describes_error_cases(self):
        doc = run_ma_detection.__doc__ or ""
        self.assertIn("ModelArtifactNotFoundError", doc)
        self.assertIn("ModelContractError", doc)

    def test_function_docstring_describes_both_stages(self):
        doc = run_ma_detection.__doc__ or ""
        self.assertIn("Stage A", doc, "Docstring must describe Stage A classical extraction.")
        self.assertIn("Stage B", doc, "Docstring must describe Stage B CNN FP-reducer.")

    def test_function_docstring_mentions_candidate_extraction_method(self):
        doc = run_ma_detection.__doc__ or ""
        self.assertIn("candidate_extraction_method", doc)

    def test_implementation_reads_method_from_contract(self):
        import inspect
        src = inspect.getsource(run_ma_detection)
        self.assertIn("candidate_extraction_method", src)

    def test_implementation_calls_classical_extractor_stage_a(self):
        """Implementation must call at least one classical extractor helper."""
        import inspect
        src = inspect.getsource(run_ma_detection)
        calls_tophat  = "_extract_candidates_tophat" in src
        calls_matched = "_extract_candidates_matched_filter" in src
        self.assertTrue(
            calls_tophat or calls_matched,
            "run_ma_detection must invoke a classical candidate extractor for Stage A.",
        )


# ---------------------------------------------------------------------------
# Classical extractor unit tests (run without any ONNX model)
# ---------------------------------------------------------------------------

class TestClassicalCandidateExtractors(unittest.TestCase):
    """Sanity checks for the two classical Stage-A extraction functions."""

    def test_tophat_returns_list_of_row_col_tuples(self):
        from pipeline.structure import _extract_candidates_tophat
        image = _make_dummy_preprocessed_image(h=128, w=128)
        candidates = _extract_candidates_tophat(image, disk_radius=4, threshold_factor=2.0)
        self.assertIsInstance(candidates, list)
        for c in candidates:
            self.assertEqual(len(c), 2, "Each candidate must be a (row, col) pair.")
            self.assertIsInstance(c[0], int)
            self.assertIsInstance(c[1], int)

    def test_matched_filter_returns_list_of_row_col_tuples(self):
        from pipeline.structure import _extract_candidates_matched_filter
        image = _make_dummy_preprocessed_image(h=128, w=128)
        candidates = _extract_candidates_matched_filter(image, sigma=1.0, threshold_factor=2.0)
        self.assertIsInstance(candidates, list)
        for c in candidates:
            self.assertEqual(len(c), 2)
            self.assertIsInstance(c[0], int)
            self.assertIsInstance(c[1], int)

    def test_tophat_handles_uint8_input(self):
        from pipeline.structure import _extract_candidates_tophat
        image = (np.random.default_rng(1).random((64, 64, 3)) * 255).astype(np.uint8)
        result = _extract_candidates_tophat(image)
        self.assertIsInstance(result, list)

    def test_matched_filter_handles_uint8_input(self):
        from pipeline.structure import _extract_candidates_matched_filter
        image = (np.random.default_rng(2).random((64, 64, 3)) * 255).astype(np.uint8)
        result = _extract_candidates_matched_filter(image)
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# MA overlay helper tests (run without any ONNX model)
# ---------------------------------------------------------------------------

class TestDrawMAOverlay(unittest.TestCase):
    """Sanity checks for the _draw_ma_overlay helper."""

    def test_overlay_is_uint8_hwc_with_correct_spatial_size(self):
        from pipeline.structure import _draw_ma_overlay
        image = _make_dummy_preprocessed_image(h=128, w=128)
        overlay = _draw_ma_overlay(image, ma_locations=[(32, 64), (80, 10)])
        self.assertIsInstance(overlay, np.ndarray)
        self.assertEqual(overlay.ndim, 3)
        self.assertEqual(overlay.shape[0], 128)
        self.assertEqual(overlay.shape[1], 128)
        self.assertEqual(overlay.shape[2], 3)
        self.assertEqual(overlay.dtype, np.uint8)

    def test_overlay_with_no_locations_returns_image_shaped_array(self):
        from pipeline.structure import _draw_ma_overlay
        image = _make_dummy_preprocessed_image(h=64, w=64)
        overlay = _draw_ma_overlay(image, ma_locations=[])
        self.assertEqual(overlay.shape, (64, 64, 3))
        self.assertEqual(overlay.dtype, np.uint8)


# ---------------------------------------------------------------------------
# Integration test (skipped when model artifact is absent)
# ---------------------------------------------------------------------------

REAL_MODEL_DIR = Path("models/ma_detector")
_metadata_present = (REAL_MODEL_DIR / "metadata.json").is_file()
_onnx_present = any(REAL_MODEL_DIR.glob("*.onnx")) if REAL_MODEL_DIR.is_dir() else False


@unittest.skipUnless(
    _metadata_present and _onnx_present,
    "Skipped: ma_detector model artifact not yet available (MATLAB export pending).",
)
class TestMADetectionIntegration(unittest.TestCase):
    """
    Integration tests that run when the real ONNX model is present.
    Validates ma_count type and ma_overlay shape/dtype.
    """

    FIXTURE_DIR = Path("tests/fixtures")
    OUTPUT_DIR  = Path("tests/fixtures/output")

    @classmethod
    def setUpClass(cls) -> None:
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _load_preprocessed_image(self) -> np.ndarray:
        from pipeline.preprocessing import preprocess
        fixture = self.FIXTURE_DIR / "sample_fundus.jpg"
        if not fixture.is_file():
            self.skipTest(f"Fixture image not found: {fixture}")
        return preprocess(fixture)

    def test_inference_returns_expected_keys(self):
        img = self._load_preprocessed_image()
        result = run_ma_detection(preprocessed_image=img)
        for key in ("ma_count", "ma_overlay"):
            self.assertIn(key, result, f"Missing key {key!r} in result.")

    def test_ma_count_is_non_negative_integer(self):
        img = self._load_preprocessed_image()
        result = run_ma_detection(preprocessed_image=img)
        count = result["ma_count"]
        self.assertIsInstance(count, int, f"ma_count must be int, got {type(count).__name__}")
        self.assertGreaterEqual(count, 0, "ma_count must be >= 0.")

    def test_ma_overlay_shape_and_dtype(self):
        img = self._load_preprocessed_image()
        result = run_ma_detection(preprocessed_image=img)
        overlay = result["ma_overlay"]
        self.assertIsInstance(overlay, np.ndarray)
        self.assertEqual(overlay.ndim, 3)
        self.assertEqual(overlay.shape[2], 3)
        self.assertEqual(overlay.dtype, np.uint8)

    def test_overlay_same_spatial_size_as_input(self):
        img = self._load_preprocessed_image()
        result = run_ma_detection(preprocessed_image=img)
        overlay = result["ma_overlay"]
        self.assertEqual(overlay.shape[0], img.shape[0])
        self.assertEqual(overlay.shape[1], img.shape[1])

    def test_overlay_saved_for_visual_inspection(self):
        import cv2
        img = self._load_preprocessed_image()
        result = run_ma_detection(preprocessed_image=img)
        out_path = self.OUTPUT_DIR / "ma_overlay.png"
        cv2.imwrite(str(out_path), result["ma_overlay"])
        self.assertTrue(out_path.is_file(), f"Failed to save overlay to {out_path}")


if __name__ == "__main__":
    unittest.main()
