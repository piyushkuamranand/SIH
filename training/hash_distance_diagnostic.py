import csv, sys
from pathlib import Path
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"

def average_hash(image_path, hash_size=16):
    with Image.open(image_path) as img:
        gray = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
        arr = np.asarray(gray, dtype=np.float32)
    mean = arr.mean()
    bits = (arr > mean).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return h

def hamming(a, b):
    return bin(a ^ b).count("1")

pool_paths = []
for split_file in ["grading_train.csv", "grading_val.csv"]:
    for row in csv.DictReader(open(PROJECT_ROOT / "data" / "splits" / split_file, encoding="utf-8")):
        pool_paths.append(RAW / row["image_path"])

print(f"hashing {len(pool_paths)} pool images...")
pool_hashes = [average_hash(p) for p in pool_paths]

test_img_dir = RAW / "idrid" / "B_grading" / "B. Disease Grading" / "1. Original Images" / "b. Testing Set"
test_paths = sorted(test_img_dir.glob("*.jpg"))[:15]  # sample 15 for speed

print("id, min_distance, 2nd_min_distance")
for p in test_paths:
    h = average_hash(p)
    dists = sorted(hamming(h, ph) for ph in pool_hashes)
    print(f"{p.stem}, {dists[0]}, {dists[1]}")
