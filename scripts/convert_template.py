#!/usr/bin/env python3
"""
nnUNet v2 Dataset Conversion Template
======================================
Adapt this script to your specific input layout.
Run: python convert_to_nnunet.py

Dependencies: pip install SimpleITK nibabel numpy
"""

import os
import shutil
import json
import re
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# USER CONFIGURATION — edit these for your dataset
# ============================================================

INPUT_DIR = Path("/path/to/your/input/dataset")
OUTPUT_DIR = Path("/path/to/nnUNet_raw")

DATASET_ID = 42                        # 3-digit ID, avoid 001-010 (MSD reserved)
DATASET_NAME = "MyDataset"             # CamelCase, no spaces

# Channel definitions: channel_index -> (modality_name, glob_pattern_in_case_folder)
# For single modality: just one entry with index 0
# For multi-modal: add entries for each modality IN ORDER
CHANNELS: Dict[int, Tuple[str, str]] = {
    0: ("CT", "image.nii.gz"),         # (nnunet_name, filename_pattern)
    # 1: ("T2", "t2.nii.gz"),          # uncomment for multi-modal
}

LABEL_FILENAME = "label.nii.gz"        # filename of the segmentation mask in each case folder

# Label mapping: {label_name: integer_value}
# 0 must always be background; values must be consecutive!
LABELS: Dict[str, int] = {
    "background": 0,
    "structure": 1,                    # rename to your actual structure
}

FILE_ENDING = ".nii.gz"               # output file extension: .nii.gz or .mha

# Train/test split — set TEST_RATIO = 0 to put everything in imagesTr
TEST_RATIO = 0.0                       # e.g. 0.2 means 20% go to imagesTs
RANDOM_SEED = 42

# Optional: force SimpleITK reader (recommended for .mha inputs)
USE_SIMPLEITK_IO = False

# ============================================================
# HELPERS
# ============================================================

def read_image(path: Path):
    """Read NIfTI or MHA image. Returns (array, affine_or_None, sitk_image)."""
    suffix = "".join(path.suffixes)
    if suffix in (".mha", ".nrrd", ".nii", ".nii.gz"):
        try:
            import SimpleITK as sitk
            sitk_img = sitk.ReadImage(str(path))
            return sitk_img
        except Exception as e:
            raise RuntimeError(f"Could not read {path}: {e}")
    raise ValueError(f"Unsupported format: {path}")


def write_image(sitk_img, output_path: Path):
    """Write SimpleITK image to output path."""
    import SimpleITK as sitk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(sitk_img, str(output_path))


def validate_labels(label_path: Path, expected_labels: Dict[str, int]) -> List[str]:
    """Check that label values are consecutive and match expectations. Returns warnings."""
    import SimpleITK as sitk
    import numpy as np

    warnings = []
    img = sitk.ReadImage(str(label_path))
    arr = sitk.GetArrayFromImage(img)
    unique_vals = sorted(np.unique(arr).astype(int).tolist())

    expected_vals = sorted(expected_labels.values())
    if unique_vals != expected_vals:
        warnings.append(
            f"  WARNING: {label_path.name} has labels {unique_vals}, "
            f"expected {expected_vals}"
        )

    # Check consecutive
    for i, v in enumerate(unique_vals):
        if v != i:
            warnings.append(
                f"  WARNING: Labels are not consecutive in {label_path.name}. "
                f"Found {unique_vals}. Remap before using nnUNet!"
            )
            break

    return warnings


def remap_labels(label_path: Path, mapping: Dict[int, int], output_path: Path):
    """Remap label integer values using a {old: new} mapping dict."""
    import SimpleITK as sitk
    import numpy as np

    img = sitk.ReadImage(str(label_path))
    arr = sitk.GetArrayFromImage(img).astype(np.int32)
    remapped = np.zeros_like(arr)
    for old_val, new_val in mapping.items():
        remapped[arr == old_val] = new_val

    out_img = sitk.GetImageFromArray(remapped)
    out_img.CopyInformation(img)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out_img, str(output_path))


# ============================================================
# LAYOUT DETECTION — adapt get_cases() for your input layout
# ============================================================

def get_cases() -> List[Path]:
    """
    Return list of case paths.

    LAYOUT A — per-subject subfolders (default):
        input/
          patient001/
            image.nii.gz
            label.nii.gz
          patient002/
            ...

    LAYOUT B — flat folders: edit to return list of case IDs
    instead, and adapt the copy logic in main() accordingly.
    """
    cases = sorted([p for p in INPUT_DIR.iterdir() if p.is_dir()])
    if not cases:
        raise RuntimeError(f"No subdirectories found in {INPUT_DIR}. "
                           "Edit get_cases() for your layout.")
    return cases


# ============================================================
# MAIN CONVERSION LOGIC
# ============================================================

def main():
    import random
    import SimpleITK as sitk  # noqa: imported here to give clear error if missing

    dataset_folder_name = f"Dataset{DATASET_ID:03d}_{DATASET_NAME}"
    dataset_root = OUTPUT_DIR / dataset_folder_name
    images_tr = dataset_root / "imagesTr"
    labels_tr = dataset_root / "labelsTr"
    images_ts = dataset_root / "imagesTs"

    images_tr.mkdir(parents=True, exist_ok=True)
    labels_tr.mkdir(parents=True, exist_ok=True)

    cases = get_cases()
    print(f"Found {len(cases)} cases in {INPUT_DIR}")

    # Train/test split
    random.seed(RANDOM_SEED)
    shuffled = cases[:]
    random.shuffle(shuffled)
    n_test = int(len(shuffled) * TEST_RATIO)
    test_cases = set(c.name for c in shuffled[:n_test])
    train_cases = [c for c in cases if c.name not in test_cases]

    if n_test > 0:
        images_ts.mkdir(parents=True, exist_ok=True)

    all_warnings = []
    n_train = 0

    for case_dir in cases:
        case_id = case_dir.name
        is_test = case_id in test_cases

        # --- Copy / convert each channel ---
        for ch_idx, (modality_name, ch_filename) in CHANNELS.items():
            src = case_dir / ch_filename
            if not src.exists():
                print(f"  SKIP: {src} not found")
                continue

            dst_name = f"{case_id}_{ch_idx:04d}{FILE_ENDING}"
            dst_dir = images_ts if is_test else images_tr
            dst = dst_dir / dst_name

            if src.suffix == FILE_ENDING or "".join(src.suffixes) == FILE_ENDING:
                shutil.copy2(src, dst)
            else:
                # Format conversion needed (e.g. .mha → .nii.gz)
                img = sitk.ReadImage(str(src))
                sitk.WriteImage(img, str(dst))
                print(f"  Converted: {src.name} → {dst.name}")

        # --- Copy label (train only) ---
        if not is_test:
            label_src = case_dir / LABEL_FILENAME
            if label_src.exists():
                label_dst = labels_tr / f"{case_id}{FILE_ENDING}"

                # Validate labels
                warnings = validate_labels(label_src, LABELS)
                all_warnings.extend(warnings)

                if label_src.suffix == FILE_ENDING or "".join(label_src.suffixes) == FILE_ENDING:
                    shutil.copy2(label_src, label_dst)
                else:
                    img = sitk.ReadImage(str(label_src))
                    sitk.WriteImage(img, str(label_dst))
            else:
                print(f"  WARNING: No label found for {case_id}")
            n_train += 1

    # --- Generate dataset.json ---
    channel_names = {str(idx): name for idx, (name, _) in CHANNELS.items()}

    dataset_json = {
        "name": dataset_folder_name,
        "description": f"Converted by nnunet-converter skill",
        "channel_names": channel_names,
        "labels": LABELS,
        "numTraining": n_train,
        "file_ending": FILE_ENDING,
    }
    if USE_SIMPLEITK_IO:
        dataset_json["overwrite_image_reader_writer"] = "SimpleITKIO"

    json_path = dataset_root / "dataset.json"
    with open(json_path, "w") as f:
        json.dump(dataset_json, f, indent=4)

    # --- Summary ---
    print("\n" + "=" * 60)
    print(f"Conversion complete → {dataset_root}")
    print(f"  Training cases : {n_train}")
    print(f"  Test cases     : {n_test}")
    print(f"  Channels       : {len(CHANNELS)}")
    print(f"  dataset.json   : {json_path}")

    if all_warnings:
        print("\nWarnings (review before running nnUNet):")
        for w in all_warnings:
            print(w)
    else:
        print("\nNo label validation warnings.")

    print("\nNext steps:")
    print(f"  export nnUNet_raw={OUTPUT_DIR}")
    print(f"  nnUNetv2_plan_and_preprocess -d {DATASET_ID:03d} --verify_dataset_integrity")


if __name__ == "__main__":
    main()
