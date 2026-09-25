"""
Unit and integration tests for pipeline/preprocessing.py.

Validates:
1. End-to-end preprocessing on sample fundus image matches config target_size and normalization range.
2. Clear errors on corrupted, unreadable, or missing image files.
3. Individual steps: crop_fov, resize, apply_clahe, normalize.
4. Visual before/after artifact generation in tests/fixtures/output/.
"""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from pipeline.preprocessing import (
    apply_clahe,
    crop_fov,
    load_config,
    load_image,
    normalize,
    preprocess,
    resize,
)


class TestPreprocessing(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = Path("tests/fixtures")
        self.output_dir = self.fixtures_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_image_path = self.fixtures_dir / "sample_fundus.jpg"
        self.config_path = Path("configs/preprocessing.json")

    def test_load_config_valid(self):
        config = load_config(self.config_path)
        self.assertIn("target_size", config)
        self.assertIn("fov_crop", config)
        self.assertIn("clahe", config)
        self.assertIn("normalization", config)
        self.assertEqual(len(config["target_size"]), 2)

    def test_load_config_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_config("configs/non_existent_config.json")

    def test_load_config_corrupted_file(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            f.write("{ invalid json content ...")
            bad_path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                load_config(bad_path)
            self.assertIn("Corrupted or invalid JSON", str(ctx.exception))
        finally:
            Path(bad_path).unlink(missing_ok=True)

    def test_load_image_valid_path(self):
        self.assertTrue(self.sample_image_path.exists(), "Sample fundus image fixture missing.")
        img = load_image(self.sample_image_path)
        self.assertIsInstance(img, np.ndarray)
        self.assertEqual(img.ndim, 3)
        self.assertEqual(img.shape[2], 3)
        self.assertEqual(img.dtype, np.uint8)

    def test_load_image_numpy_inputs(self):
        # 2D grayscale
        gray = np.full((100, 100), 128, dtype=np.uint8)
        loaded = load_image(gray)
        self.assertEqual(loaded.shape, (100, 100, 3))

        # 3D RGBA
        rgba = np.full((100, 100, 4), 200, dtype=np.uint8)
        loaded_rgb = load_image(rgba)
        self.assertEqual(loaded_rgb.shape, (100, 100, 3))

        # Float array in [0, 1]
        float_img = np.full((100, 100, 3), 0.5, dtype=np.float32)
        loaded_float = load_image(float_img)
        self.assertEqual(loaded_float.dtype, np.uint8)
        self.assertEqual(loaded_float[0, 0, 0], 128)

    def test_load_image_pil_input(self):
        pil_img = Image.new("RGB", (64, 64), color=(255, 128, 64))
        loaded = load_image(pil_img)
        self.assertEqual(loaded.shape, (64, 64, 3))
        self.assertEqual(loaded.dtype, np.uint8)

    def test_load_image_missing_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            load_image("data/does_not_exist.jpg")

    def test_load_image_corrupted_file_raises_clear_error(self):
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".jpg") as f:
            f.write(b"NOT_A_REAL_IMAGE_FILE_RANDOM_BYTES_1234567890")
            corrupt_path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                load_image(corrupt_path)
            self.assertIn("Corrupted, invalid, or unsupported image file", str(ctx.exception))
        finally:
            Path(corrupt_path).unlink(missing_ok=True)

    def test_load_image_invalid_type_raises_error(self):
        with self.assertRaises(TypeError):
            load_image(12345)

    def test_crop_fov(self):
        # Create a mock image with wide black borders and a bright center region
        mock_img = np.zeros((200, 200, 3), dtype=np.uint8)
        mock_img[50:150, 60:160] = 180

        cropped = crop_fov(mock_img, threshold=10, margin=0)
        self.assertEqual(cropped.shape, (100, 100, 3))
        self.assertTrue(np.all(cropped == 180))

    def test_crop_fov_all_black_raises_error(self):
        black_img = np.zeros((100, 100, 3), dtype=np.uint8)
        with self.assertRaises(ValueError) as ctx:
            crop_fov(black_img, threshold=10)
        self.assertIn("no detectable fundus field of view", str(ctx.exception))

    def test_resize(self):
        img = np.zeros((100, 150, 3), dtype=np.uint8)
        resized = resize(img, (256, 512))
        self.assertEqual(resized.shape, (256, 512, 3))

    def test_apply_clahe(self):
        img = np.full((100, 100, 3), 100, dtype=np.uint8)
        # Create some gradient
        img[:, :, 0] = np.linspace(50, 150, 100, dtype=np.uint8)
        enhanced = apply_clahe(img, clip_limit=2.0, tile_grid_size=(8, 8))
        self.assertEqual(enhanced.shape, (100, 100, 3))
        self.assertEqual(enhanced.dtype, np.uint8)

    def test_normalize(self):
        img = np.array([[[0, 127, 255]]], dtype=np.uint8)
        norm = normalize(img, range_min=0.0, range_max=1.0, dtype="float32")
        self.assertEqual(norm.dtype, np.float32)
        self.assertAlmostEqual(float(norm[0, 0, 0]), 0.0, places=2)
        self.assertAlmostEqual(float(norm[0, 0, 1]), 127.0 / 255.0, places=2)
        self.assertAlmostEqual(float(norm[0, 0, 2]), 1.0, places=2)

    def test_preprocess_end_to_end_on_fixture(self):
        """End-to-end preprocessing on real sample image matches config target_size and bounds."""
        config = load_config(self.config_path)
        expected_size = tuple(config["target_size"])

        # Execute preprocessing
        processed = preprocess(self.sample_image_path, self.config_path)

        # 1. Output shape matches target_size (height, width, 3)
        self.assertEqual(processed.shape, (expected_size[0], expected_size[1], 3))

        # 2. Output is float32 and values are within [0.0, 1.0]
        self.assertEqual(processed.dtype, np.float32)
        self.assertGreaterEqual(float(processed.min()), 0.0)
        self.assertLessEqual(float(processed.max()), 1.0)

        # 3. Save before/after inspection files to tests/fixtures/output/
        raw_img = load_image(self.sample_image_path)
        raw_out_path = self.output_dir / "sample_fundus_raw.jpg"
        Image.fromarray(raw_img).save(raw_out_path)

        # Convert normalized float [0, 1] back to [0, 255] uint8 for visual inspection saving
        vis_processed = (processed * 255.0).clip(0, 255).astype(np.uint8)
        processed_out_path = self.output_dir / "sample_fundus_preprocessed.png"
        Image.fromarray(vis_processed).save(processed_out_path)

        self.assertTrue(raw_out_path.exists())
        self.assertTrue(processed_out_path.exists())

    def test_preprocess_custom_config(self):
        """Ensure preprocessing is strictly parameter-driven without hardcoded sizes."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            json.dump({
                "target_size": [224, 224],
                "fov_crop": {"threshold": 10, "margin": 0},
                "clahe": {"clip_limit": 3.0, "tile_grid_size": [4, 4], "channel": "L"},
                "normalization": {"range": [-1.0, 1.0], "dtype": "float32"}
            }, f)
            custom_cfg_path = f.name

        try:
            processed = preprocess(self.sample_image_path, custom_cfg_path)
            self.assertEqual(processed.shape, (224, 224, 3))
            self.assertGreaterEqual(float(processed.min()), -1.0)
            self.assertLessEqual(float(processed.max()), 1.0)
        finally:
            Path(custom_cfg_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
