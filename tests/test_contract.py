"""
tests/test_contract.py — Unit tests for pipeline/contract.py

Validates:
- Successful contract loading for classifier, segmentation, and ma_detector models.
- Missing required core and type-specific fields fail with clear error naming the field.
- Non-existent metadata.json and corrupted JSON fail with clear errors.
- resolve_model_path succeeds when artifact is present, fails with clear 'model artifact not found' when missing.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.contract import (
    CORE_MANDATORY_FIELDS,
    TYPE_SPECIFIC_FIELDS,
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)


def make_valid_contract_data(model_type: str = "classifier") -> dict:
    """Helper to generate a complete valid contract dictionary."""
    base = {
        "model_name": "test_model",
        "model_version": "1.0.0",
        "input_size": [224, 224],
        "channels": 3,
        "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        "model_file": "model.onnx",
        "framework": "onnx",
        "training_dataset": "DDR",
        "preprocessing": ["fov_crop", "resize", "clahe", "normalize"],
        "eval_metrics": {"accuracy": 0.95},
    }
    if model_type == "classifier":
        base.update({
            "class_labels": ["Accept", "Reject"],
            "output_format": "softmax_probs",
            "threshold": 0.5,
        })
    elif model_type == "segmentation":
        base.update({
            "mask_labels": ["vessel"],
            "output_format": "binary_mask",
            "mask_resolution": [512, 512],
        })
    elif model_type == "ma_detector":
        base.update({
            "candidate_extraction_method": "morphological_tophat",
            "fp_reducer_model_file": "ma_fp_reducer.onnx",
            "output_format": "candidate_list_with_scores",
        })
    return base


class TestModelContract(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def write_metadata(self, data: dict, filename: str = "metadata.json") -> Path:
        path = Path(self.test_dir) / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_load_valid_classifier_contract(self):
        contract_data = make_valid_contract_data("classifier")
        self.write_metadata(contract_data)

        loaded = load_contract(self.test_dir, "classifier")
        self.assertIsInstance(loaded, dict)
        self.assertEqual(loaded["model_name"], "test_model")
        self.assertEqual(loaded["class_labels"], ["Accept", "Reject"])
        self.assertEqual(loaded["threshold"], 0.5)

    def test_load_classifier_missing_field_raises_error_with_field_name(self):
        contract_data = make_valid_contract_data("classifier")
        del contract_data["threshold"]
        self.write_metadata(contract_data)

        with self.assertRaises(ModelContractError) as ctx:
            load_contract(self.test_dir, "classifier")
        self.assertIn("threshold", str(ctx.exception))

    def test_load_valid_segmentation_contract(self):
        contract_data = make_valid_contract_data("segmentation")
        self.write_metadata(contract_data)

        loaded = load_contract(self.test_dir, "segmentation")
        self.assertEqual(loaded["mask_labels"], ["vessel"])
        self.assertEqual(loaded["mask_resolution"], [512, 512])

    def test_load_segmentation_missing_field_raises_error(self):
        contract_data = make_valid_contract_data("segmentation")
        del contract_data["mask_resolution"]
        self.write_metadata(contract_data)

        with self.assertRaises(ModelContractError) as ctx:
            load_contract(self.test_dir, "segmentation")
        self.assertIn("mask_resolution", str(ctx.exception))

    def test_load_valid_ma_detector_contract(self):
        contract_data = make_valid_contract_data("ma_detector")
        self.write_metadata(contract_data)

        loaded = load_contract(self.test_dir, "ma_detector")
        self.assertEqual(loaded["candidate_extraction_method"], "morphological_tophat")

    def test_load_ma_detector_missing_field_raises_error(self):
        contract_data = make_valid_contract_data("ma_detector")
        del contract_data["fp_reducer_model_file"]
        self.write_metadata(contract_data)

        with self.assertRaises(ModelContractError) as ctx:
            load_contract(self.test_dir, "ma_detector")
        self.assertIn("fp_reducer_model_file", str(ctx.exception))

    def test_load_missing_core_field_raises_error(self):
        contract_data = make_valid_contract_data("classifier")
        del contract_data["normalization"]
        self.write_metadata(contract_data)

        with self.assertRaises(ModelContractError) as ctx:
            load_contract(self.test_dir, "classifier")
        self.assertIn("normalization", str(ctx.exception))

    def test_missing_metadata_file_raises_file_not_found(self):
        empty_dir = Path(self.test_dir) / "empty_model"
        empty_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            load_contract(empty_dir, "classifier")

    def test_corrupted_json_raises_model_contract_error(self):
        path = Path(self.test_dir) / "metadata.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: 123")

        with self.assertRaises(ModelContractError) as ctx:
            load_contract(self.test_dir, "classifier")
        self.assertIn("Corrupted or invalid JSON", str(ctx.exception))

    def test_unsupported_model_type_raises_error(self):
        contract_data = make_valid_contract_data("classifier")
        self.write_metadata(contract_data)

        with self.assertRaises(ModelContractError) as ctx:
            load_contract(self.test_dir, "unsupported_type")
        self.assertIn("Unsupported model type", str(ctx.exception))

    def test_resolve_model_path_success(self):
        contract_data = make_valid_contract_data("classifier")
        artifact_file = Path(self.test_dir) / "model.onnx"
        artifact_file.write_text("dummy onnx content")

        resolved = resolve_model_path(self.test_dir, contract_data)
        self.assertTrue(Path(resolved).is_file())
        self.assertEqual(Path(resolved), artifact_file)

    def test_resolve_model_path_missing_artifact_raises_clear_error(self):
        contract_data = make_valid_contract_data("classifier")
        # Artifact 'model.onnx' is intentionally not created

        with self.assertRaises(ModelArtifactNotFoundError) as ctx:
            resolve_model_path(self.test_dir, contract_data)
        self.assertIn("model artifact not found", str(ctx.exception).lower())

    def test_resolve_model_path_missing_model_file_key(self):
        contract_data = make_valid_contract_data("classifier")
        del contract_data["model_file"]

        with self.assertRaises(ModelContractError) as ctx:
            resolve_model_path(self.test_dir, contract_data)
        self.assertIn("model_file", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
