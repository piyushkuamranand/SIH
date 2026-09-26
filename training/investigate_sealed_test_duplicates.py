import csv
from pathlib import Path
import numpy as np
from PIL import Image
import hashlib

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

def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()

pool_rows = []
for split_file in ["grading_train.csv", "grading_val.csv"]:
    for row in csv.DictReader(open(PROJECT_ROOT / "data" / "splits" / split_file, encoding="utf-8")):
        pool_rows.append(row)

print(f"hashing {len(pool_rows)} pool images once...")
pool_hashes = []
for i, row in enumerate(pool_rows):
    pool_hashes.append(average_hash(RAW / row["image_path"]))
    if (i+1) % 1000 == 0:
        print(f"  {i+1}/{len(pool_rows)}")

test_img_dir = RAW / "idrid" / "B_grading" / "B. Disease Grading" / "1. Original Images" / "b. Testing Set"

for test_id in ["IDRiD_003", "IDRiD_006", "IDRiD_007", "IDRiD_005"]:
    test_path = test_img_dir / f"{test_id}.jpg"
    test_hash = average_hash(test_path)
    best_idx, best_dist = None, 999
    for i, h in enumerate(pool_hashes):
        d = hamming(test_hash, h)
        if d < best_dist:
            best_dist = d
            best_idx = i
    best = pool_rows[best_idx]
    pool_path = RAW / best["image_path"]
    print(f"\n{test_id} (test) closest match: dataset={best['dataset']} id={best['id_code']} distance={best_dist}")
    print(f"  test file:  {test_path}  size={test_path.stat().st_size}  md5={md5(test_path)}")
    print(f"  pool file:  {pool_path}  size={pool_path.stat().st_size}  md5={md5(pool_path)}")
    with Image.open(test_path) as im1, Image.open(pool_path) as im2:
        print(f"  test dims={im1.size}  pool dims={im2.size}")
        g1 = np.asarray(im1.convert("L").resize((64,64)), dtype=np.float32)
        g2 = np.asarray(im2.convert("L").resize((64,64)), dtype=np.float32)
        corr = np.corrcoef(g1.flatten(), g2.flatten())[0,1]
        print(f"  64x64 grayscale pixel correlation: {corr:.4f}")
