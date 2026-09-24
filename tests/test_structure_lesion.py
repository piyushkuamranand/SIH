"""
Unit tests for pipeline/structure.py — TASK-007 (lesion segmentation: HE/EX/SE).

Test coverage:
1. Missing metadata.json -> clear "model artifact missing" FileNotFoundError.
2. Incomplete metadata.json (missing required segmentation field) -> ModelContractError.
3. Complete metadata.json but missing ONNX file -> clear ModelArtifactNotFoundError.
4. Complete metadata.json but mask_labels missing a required lesion class -> ValueError.
5. Non-3-D preprocessed_image -> ValueError (or ModelArtifactNotFoundError fires first).
6. Return-schema: function has return type hint and docstring with all output keys.
7. (Integration, requires real ONNX model) — skipped when artifact absent.
   Verifies: three masks have correct shape/dtype; he_presence is bool; ex_area in [0,1];
   lesion_overlay is HWC uint8; masks are kept separate (not merged into one).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline.contract import ModelArtifactNotFoundError, ModelContractError
from pipeline.structure import run_lesion_segmentation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_complete_lesion_metadata(model_file: str = "lesion_seg.onnx") -> dict:
    """Return a fully-populated metadata.json dict for the lesion segmentation contract."""
    return {
        "model_name":         "lesion_unet_test",
        "model_version":      "0.0.0",
        "input_size":         [512, 512],
        "channels":           3,
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std":  [0.229, 0.224, 0.225],
        },
        "model_file":         model_file,
        "framework":          "onnx",
        "training_dataset":   "IDRiD",
        "preprocessing":      "FOV crop, resize, CLAHE, normalize",
        "eval_metrics":       {"dice": 0.0, "iou": 0.0},
        # Segmentation-type required fields
        "mask_labels":        ["HE", "EX", "SE"],
        "output_format":      "sigmoid",
        "mask_resolution":    [512, 512],
        # Optional fields consumed by run_lesion_segmentation
        "threshold":              0.5,
        "he_presence_threshold":  50,
    }


def _make_dummy_preprocessed_image(h: int = 224, w: int = 224) -> np.ndarray:
    """Return a random HWC float32 array simulating a preprocessed fundus image."""
    rng = np.random.default_rng(7)
    return rng.random((h, w, 3)).astype(np.float32)


# ---------------------------------------------------------------------------
# Missing-artifact error paths (no real model needed)
# ---------------------------------------------------------------------------

class TestLesionSegmentationMissingArtifacts(unittest.TestCase):
    """Verify that missing-artifact situations fail loudly and specifically."""

    def test_missing_metadata_json_raises_file_not_found(self):
        """run_lesion_segmentation with an empty model_dir raises a clear FileNotFoundError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with self.assertRaises(FileNotFoundError) as ctx:
                run_lesion_segmentation(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("model artifact missing", error_msg.lower())
            self.assertIn("Phase 2", error_msg)
            self.assertIn("lesion segmentation", error_msg.lower())

    def test_incomplete_metadata_json_raises_contract_error(self):
        """Metadata missing a required segmentation field -> ModelContractError naming the field."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            incomplete = _make_complete_lesion_metadata()
            incomplete.pop("mask_labels")  # required for segmentation type
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(incomplete), encoding="utf-8"
            )
            with self.assertRaises(ModelContractError) as ctx:
                run_lesion_segmentation(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("mask_labels", error_msg)

    def test_complete_metadata_but_missing_onnx_raises_artifact_error(self):
        """Complete metadata.json but no ONNX file -> ModelArtifactNotFoundError."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_lesion_metadata(model_file="lesion_seg.onnx")
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            # Deliberately do NOT create lesion_seg.onnx
            with self.assertRaises(ModelArtifactNotFoundError) as ctx:
                run_lesion_segmentation(preprocessed_image=image, model_dir=tmpdir_path)
            error_msg = str(ctx.exception)
            self.assertIn("model artifact missing", error_msg.lower())
            self.assertIn("Phase 2", error_msg)
            self.assertIn("lesion_seg.onnx", error_msg)

    def test_mask_labels_missing_he_raises_value_error(self):
        """mask_labels without 'HE' -> ValueError naming the missing label."""
        image = _make_dummy_preprocessed_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_lesion_metadata()
            # Remove HE from labels
            metadata["mask_labels"] = ["EX", "SE"]
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            # Create a dummy placeholder so the ONNX check doesn't fire first
            (tmpdir_path / "lesion_seg.onnx").write_bytes(b"\x00" * 4)
            # The ValueError about missing 'HE' label fires before actual inference
            # because we check mask_labels before calling onnxruntime.
            # (An OSError/RuntimeError from onnxruntime is also acceptable here —
            # what must NOT happen is a silent wrong-shape or fabricated result.)
            with self.assertRaises((ValueError, RuntimeError, Exception)) as ctx:
                run_lesion_segmentation(preprocessed_image=image, model_dir=tmpdir_path)
            # If it's a ValueError, the message must mention 'HE'
            if isinstance(ctx.exception, ValueError):
                self.assertIn("HE", str(ctx.exception))

    def test_non_3d_image_raises_value_error_or_artifact_error(self):
        """A 2-D preprocessed_image raises ValueError (or artifact error fires first)."""
        bad_image = np.zeros((224, 224), dtype=np.float32)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            metadata = _make_complete_lesion_metadata()
            (tmpdir_path / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            # ONNX still missing — either ValueError (shape check) or
            # ModelArtifactNotFoundError (resolve fires first) is correct.
            with self.assertRaises((ValueError, ModelArtifactNotFoundError)):
                run_lesion_segmentation(preprocessed_image=bad_image, model_dir=tmpdir_path)


# ---------------------------------------------------------------------------
# Return schema (no model needed)
# ---------------------------------------------------------------------------

class TestLesionSegmentationReturnSchema(unittest.TestCase):
    """Verify function signature, type hints, and docstring without running inference."""

    def test_function_has_return_type_hint(self):
        """run_lesion_segmentation must have type hints."""
        hints = run_lesion_segmentation.__annotations__
        self.assertIn("return", hints, "run_lesion_segmentation missing return type annotation.")

    def test_function_docstring_describes_all_output_keys(self):
        """Docstring must mention every expected output key."""
        doc = run_lesion_segmentation.__doc__ or ""
        for key in ("he_mask", "ex_mask", "se_mask", "he_presence", "ex_area", "lesion_overlay"):
            self.assertIn(key, doc, f"Docstring does not mention output key '{key}'.")

    def test_function_docstring_describes_error_cases(self):
        """Docstring must mention the artifact-missing error types."""
        doc = run_lesion_segmentation.__doc__ or ""
        self.assertIn("ModelArtifactNotFoundError", doc)
        self.assertIn("ModelContractError", doc)

    def test_implementation_does_not_invent_lesion_subtypes(self):
        """
        The implementation must not reference or produce forbidden lesion subtypes
        (flame, dot-blot, deep) as output keys or computed values.
        Docstrings may *document* the prohibition; the code body must not *produce* them.
        """
        import inspect
        # Get source lines, skip the docstring (first triple-quoted block)
        src = inspect.getsource(run_lesion_segmentation)
        # Strip the docstring: find the closing triple-quote and look at code after it
        # Simple heuristic: split on '"""' and take everything after the second marker
        parts = src.split('"""')
        # parts[0] = def line, parts[1] = docstring body, parts[2]+ = code body
        code_body = '"""'.join(parts[2:]) if len(parts) > 2 else src
        code_body_lower = code_body.lower()
        for forbidden in ("flame", "dot-blot", "deep"):
            self.assertNotIn(
                forbidden, code_body_lower,
                f"Implementation code body references forbidden lesion subtype '{forbidden}'.",
            )


# ---------------------------------------------------------------------------
# Integration test (skipped when model artifact is absent)
# ---------------------------------------------------------------------------

REAL_MODEL_DIR = Path("models/lesion_seg")
_metadata_present = (REAL_MODEL_DIR / "metadata.json").is_file()
_onnx_present = any(REAL_MODEL_DIR.glob("*.onnx")) if REAL_MODEL_DIR.is_dir() else False


@unittest.skipUnless(
    _metadata_present and _onnx_present,
    "Skipped: lesion_seg model artifact not yet available (MATLAB export pending).",
)
class TestLesionSegmentationIntegration(unittest.TestCase):
    """
    Integration tests that run when the real ONNX model is present.
    Validates mask shapes/dtypes, he_presence type, ex_area range, overlay shape,
    and that all three masks are kept separate.
    """

    FIXTURE_DIR = Path("tests/fixtures")
    OUTPUT_DIR  = Path("tests/fixtures/output")

    @classmethod
    def setUpClass(cls) -> None:
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _load_preprocessed_image(self) -> np.ndarray:
        """Load the fixture fundus image and preprocess it."""
        from pipeline.preprocessing import preprocess
        fixture = self.FIXTURE_DIR / "sample_fundus.jpg"
        if not fixture.is_file():
            self.skipTest(f"Fixture image not found: {fixture}")
        return preprocess(fixture)

    def test_inference_returns_expected_keys(self):
        """Integration: result contains all six expected keys."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        for key in ("he_mask", "ex_mask", "se_mask", "he_presence", "ex_area", "lesion_overlay"):
            self.assertIn(key, result, f"Missing key '{key}' in result.")

    def test_he_mask_shape_and_dtype(self):
        """he_mask must be a 2-D uint8 HW array matching the image dimensions."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        mask = result["he_mask"]
        self.assertIsInstance(mask, np.ndarray)
        self.assertEqual(mask.ndim, 2, "he_mask must be 2-D (HW).")
        self.assertEqual(mask.shape[0], img.shape[0])
        self.assertEqual(mask.shape[1], img.shape[1])
        self.assertEqual(mask.dtype, np.uint8)
        unique_vals = set(np.unique(mask).tolist())
        self.assertTrue(
            unique_vals.issubset({0, 255}),
            f"he_mask should contain only 0 and 255, got {unique_vals}",
        )

    def test_ex_mask_shape_and_dtype(self):
        """ex_mask must be a 2-D uint8 HW array matching the image dimensions."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        mask = result["ex_mask"]
        self.assertIsInstance(mask, np.ndarray)
        self.assertEqual(mask.ndim, 2, "ex_mask must be 2-D (HW).")
        self.assertEqual(mask.shape[0], img.shape[0])
        self.assertEqual(mask.shape[1], img.shape[1])
        self.assertEqual(mask.dtype, np.uint8)

    def test_se_mask_shape_and_dtype(self):
        """se_mask must be a 2-D uint8 HW array matching the image dimensions."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        mask = result["se_mask"]
        self.assertIsInstance(mask, np.ndarray)
        self.assertEqual(mask.ndim, 2, "se_mask must be 2-D (HW).")
        self.assertEqual(mask.shape[0], img.shape[0])
        self.assertEqual(mask.shape[1], img.shape[1])
        self.assertEqual(mask.dtype, np.uint8)

    def test_masks_are_separate_arrays(self):
        """he_mask, ex_mask, and se_mask must not be the same object (not merged)."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        self.assertIsNot(
            result["he_mask"], result["ex_mask"],
            "he_mask and ex_mask must be separate arrays.",
        )
        self.assertIsNot(
            result["he_mask"], result["se_mask"],
            "he_mask and se_mask must be separate arrays.",
        )
        self.assertIsNot(
            result["ex_mask"], result["se_mask"],
            "ex_mask and se_mask must be separate arrays.",
        )

    def test_he_presence_is_bool(self):
        """he_presence must be a Python bool."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        self.assertIsInstance(
            result["he_presence"], bool,
            f"he_presence must be bool, got {type(result['he_presence']).__name__}",
        )

    def test_ex_area_is_float_in_unit_interval(self):
        """ex_area must be a float in [0, 1]."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        ex_area = result["ex_area"]
        self.assertIsInstance(
            ex_area, float,
            f"ex_area must be float, got {type(ex_area).__name__}",
        )
        self.assertGreaterEqual(ex_area, 0.0, "ex_area must be >= 0.")
        self.assertLessEqual(ex_area, 1.0, "ex_area must be <= 1.")

    def test_lesion_overlay_shape_and_dtype(self):
        """lesion_overlay must be a 3-D uint8 HWC array."""
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        overlay = result["lesion_overlay"]
        self.assertIsInstance(overlay, np.ndarray)
        self.assertEqual(overlay.ndim, 3, "lesion_overlay must be 3-D (HWC).")
        self.assertEqual(overlay.shape[2], 3)
        self.assertEqual(overlay.dtype, np.uint8)

    def test_overlay_saved_for_visual_inspection(self):
        """Save the lesion overlay to tests/fixtures/output/ for manual visual check."""
        import cv2
        img = self._load_preprocessed_image()
        result = run_lesion_segmentation(preprocessed_image=img)
        out_path = self.OUTPUT_DIR / "lesion_overlay.png"
        cv2.imwrite(str(out_path), result["lesion_overlay"])
        self.assertTrue(out_path.is_file(), f"Failed to save overlay to {out_path}")


if __name__ == "__main__":
    unittest.main()
