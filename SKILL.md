---
name: nnunet-converter
description: >
  Convert medical imaging datasets into nnUNet v2 format. Supports all nnUNet-native
  formats: NIfTI (.nii.gz), MHA (.mha), NRRD (.nrrd), PNG (.png), BMP (.bmp), TIFF (.tif).
  Use this skill whenever the user mentions nnUNet, nnU-Net, dataset conversion for
  segmentation training, preparing data for nnUNet, organizing imagesTr/labelsTr folders,
  generating dataset.json, or structuring medical images for nnUNet preprocessing.
  Trigger even if the user just says "convert my dataset to nnUNet" or "prepare my
  segmentation data for nnUNet training". Also handles classification labels (cls_data.csv)
  and classification_labels in dataset.json.
---

# nnUNet v2 Dataset Converter Skill

Convert datasets into nnUNet v2 format with minimal unnecessary conversion.
nnUNet v2 natively supports many file formats — **avoid format conversion whenever possible**.

## Core Principle: Minimize Conversion

nnUNet v2 supports multiple file formats natively via its ReaderWriter abstraction.
**Do NOT convert files to a different format unless strictly necessary.** Specifically:
- If data is already `.nii.gz` → keep as `.nii.gz`
- If data is already `.mha` → keep as `.mha` (do NOT convert to `.nii.gz`)
- If data is already `.nrrd` → keep as `.nrrd`
- If data is 2D `.png` or `.bmp` → keep as `.png` (do NOT wrap in NIfTI)
- If data is `.tif`/`.tiff` → keep as `.tif`
- If data is `.jpg`/`.jpeg` → convert to `.png` (JPEG is lossy, nnUNet requires lossless)

The only valid reasons to convert format are:
1. Input uses lossy compression (`.jpg`) — convert to `.png`
2. Mixing formats within a dataset (nnUNet requires one `file_ending` per dataset)
3. Input format is not supported by any nnUNet ReaderWriter

## Supported File Formats (from official nnUNet docs)

| ReaderWriter | Extensions | Notes |
|---|---|---|
| **NaturalImage2DIO** | `.png`, `.bmp`, `.tif` | 2D natural images. RGB stored in single file (no channel split needed) |
| **NibabelIO** | `.nii.gz`, `.nrrd`, `.mha` | Standard 3D medical imaging |
| **NibabelIOWithReorient** | `.nii.gz`, `.nrrd`, `.mha` | Same as NibabelIO but reorients to RAS |
| **SimpleITKIO** | `.nii.gz`, `.nrrd`, `.mha` | Alternative 3D reader |
| **Tiff3DIO** | `.tif`, `.tiff` | 3D TIFF stacks. Requires companion `.json` with spacing info |

**IMPORTANT**: nnUNet requires **lossless** (or no) compression. No `.jpg`!

## nnUNet v2 Format at a Glance

```
nnUNet_raw/
└── Dataset{ID}_{Name}/        # e.g. Dataset042_LiverSeg
    ├── dataset.json
    ├── imagesTr/
    │   ├── case_0001_0000.nii.gz   # channel 0 of case 0001
    │   ├── case_0001_0001.nii.gz   # channel 1 (multi-modal only)
    │   └── ...
    ├── labelsTr/
    │   ├── case_0001.nii.gz        # segmentation mask (NO channel suffix)
    │   └── ...
    └── imagesTs/               # optional test images (no labels needed)
        └── ...
```

**File naming rule:** `{CASE_ID}_{XXXX}.{FILE_ENDING}` for images, `{CASE_ID}.{FILE_ENDING}` for labels.
- CASE_ID: any string, e.g. `liver_001`, `BRATS_042`
- XXXX: 4-digit zero-padded channel identifier (`_0000`, `_0001`, ...)
- Single modality: only `_0000` exists
- Labels: **no** channel suffix
- **RGB exception**: For `.png` RGB natural images, all 3 color channels are stored in a single file with suffix `_0000` (nnUNet's `NaturalImage2DIO` reads the 3 channels automatically). Do NOT split RGB into separate files.

## Workflow

### Step 1 — Understand the Input Dataset

Ask the user (or infer from context) these things before writing any code:

1. **Source layout**: How is the input organized? Common patterns:
   - Flat: all images in one folder, labels in another
   - Per-subject: one folder per patient/case containing image(s) + mask
   - Mixed: images and labels interleaved with a naming convention

2. **Modalities / channels**: How many input channels?
   - Single (CT, T1 MRI, etc.) → one file per case, suffix `_0000`
   - Multi-modal (T1+T2+FLAIR+T1Gd) → one file per channel per case
   - RGB natural images (endoscopy, dermoscopy, etc.) → **single** `.png` file with suffix `_0000`

3. **File format**: What format is the input data?
   - Already in a supported format (`.nii.gz`, `.mha`, `.nrrd`, `.png`, `.bmp`, `.tif`) → **keep it, no conversion needed**
   - Lossy format (`.jpg`, `.jpeg`) → must convert to `.png`
   - Multi-frame TIFF (3D stacks) → keep as `.tif`, use Tiff3DIO with companion `.json` for spacing
   - Unsupported format → convert to nearest supported format
   - `file_ending` must be **consistent** across the dataset. If mixing formats, pick one and convert.

4. **Label values**: What integer values appear in the masks? Must be **consecutive** starting from 0. 0 = background always (if no background, do not use 0 for something else). Ask the user what each label value represents (e.g. 1=liver, 2=tumor).

5. **Train/test split**: Does the user have a pre-defined split, or should the script put everything in `imagesTr`?

6. **Dataset ID and name**: nnUNet needs a 3-digit ID (e.g. 042) and a CamelCase name (e.g. LiverSeg). Ask if not obvious. IDs 001–010 are reserved for Medical Segmentation Decathlon.

7. **Channel names**: What is each modality called? This controls nnUNet normalization:
   - `"CT"` → CT-specific global normalization (clip to 0.5/99.5 percentile, then z-score on foreground)
   - `"noNorm"` → no normalization at all
   - `"rescale_to_0_1"` → rescale intensities to [0, 1]
   - `"rgb_to_0_1"` → assumes uint8, divides by 255 (use for RGB natural images)
   - `"zscore"` or anything else → per-image z-score normalization (default for MRI)
   - The exact string matters for normalization scheme selection!

8. **Classification labels**: Does the dataset have case-level classification labels?
   - If yes, determine the label source (CSV, metadata, folder names, etc.)
   - Determine label semantics: binary (0/1), multi-class (0,1,2,...), or multi-label ([0,1], [1,0], ...)
   - Classification labels go in BOTH `cls_data.csv` AND `classification_labels` in `dataset.json`

9. **Spatial alignment**: For multi-modal data, check if all modalities share the same geometry (size, spacing, origin, direction). If not, resample non-reference modalities to the reference image space.

### Step 2 — Write the Conversion Script

Write a Python script. Dependencies depend on the input format:
- For `.nii.gz`/`.mha`/`.nrrd`: use `SimpleITK` or `nibabel`
- For `.png`/`.jpg`/`.bmp`: use `PIL/Pillow`
- For `.tif`/`.tiff`: use `PIL/Pillow` (2D) or `tifffile` (3D stacks)

See `scripts/convert_template.py` for a reusable template.

Key rules to enforce in the script:
- **Avoid format conversion** — if input is already in a supported format, just copy/rename
- Output file extension must match `file_ending` in dataset.json
- All images **must** use the same `file_ending` across the dataset
- For 2D RGB images (`.png`): store as a single RGB file per case with `_0000` suffix. Do NOT split channels.
- For grayscale 2D: store as single-channel `.png` with `_0000` suffix
- Labels must not have a channel suffix
- Case identifiers must be consistent between imagesTr and labelsTr
- Validate that label values are consecutive integers starting at 0
- For `.jpg`/`.jpeg` inputs: convert to `.png` (lossless) since nnUNet forbids lossy formats

### Step 3 — Generate dataset.json

Generate dataset.json automatically by scanning the output `imagesTr` folder.
Read the reference: `references/dataset_json_spec.md`

Minimal required fields:
```json
{
  "channel_names": {"0": "CT"},
  "labels": {"background": 0, "liver": 1},
  "numTraining": 51,
  "file_ending": ".nii.gz"
}
```

Optional but recommended:
```json
{
  "name": "Dataset042_LiverSeg",
  "description": "Liver segmentation from CT",
  "reference": "",
  "licence": "",
  "overwrite_image_reader_writer": "SimpleITKIO"
}
```

> **Note on `overwrite_image_reader_writer`**: This is **optional** — nnUNet auto-detects the correct ReaderWriter based on file extension. Only set it if auto-detection fails or you need a specific reader (e.g., `NibabelIOWithReorient` to force RAS reorientation).

### Step 4 — Validate

After running the conversion script, verify:
```bash
# Count files match
ls imagesTr/ | wc -l   # should be numTraining * num_channels
ls labelsTr/ | wc -l   # should be numTraining

# Spot-check naming
ls imagesTr/ | head -5
ls labelsTr/ | head -5

# If nnUNet is installed, run integrity check:
nnUNetv2_plan_and_preprocess -d {ID} --verify_dataset_integrity
```

### Step 5 — Update Conversion Notes

After every successful conversion, append an entry to `conversion_notes.md` in the `nnUNet_raw/` directory. This file serves as a human-readable log of all conversions — what was converted, how, and what decisions were made.

If the file does not exist, create it with a `# nnUNet Dataset Conversion Notes` header.

Each entry must include these sections:

```markdown
## Dataset{ID}_{Name}

**Source:** `/path/to/source/data/`
**Task:** brief description of the segmentation task
**Cases:** number of cases
**Dataset size:** total size on disk after conversion (e.g. 348 MB)
**Raw data format:** original format before conversion (e.g. DICOM, NIfTI, PNG, TIFF)
**Output format:** nnUNet file_ending (e.g. .nii.gz, .png, .tif)
**Conversion date:** YYYY-MM-DD
**Licence:** dataset licence if known (e.g. CC BY 4.0, TCIA Data Usage Policy)
**Paper:** citation or DOI of the related publication
**Webpage:** URL of the dataset page

### Format decision
- What format was the input? Was conversion needed? What tool/method was used?

### Label handling
- How were labels extracted/mapped? What are the integer values?
- Any special handling (remapping, combining, missing labels)?

### Dropped files
- What files from the source were NOT included and why?

### dataset.json
```json
channel_names: ...
labels: ...
file_ending: ...
```

### Notes
- Any gotchas, warnings, or non-obvious decisions made during conversion.
```

This step is **mandatory** — do not skip it. The conversion notes are the only record of how each dataset was prepared and what was intentionally excluded.

---

## 2D Image Datasets (PNG/BMP/TIFF)

nnUNet v2 natively supports 2D images via `NaturalImage2DIO`. **Do NOT wrap 2D images in NIfTI containers.**

### RGB natural images (endoscopy, dermoscopy, surgical, etc.)
RGB images are stored as a **single** `.png` file per case. nnUNet reads the 3 channels automatically.
```python
from PIL import Image

# RGB: save as single PNG — do NOT split into 3 separate channel files
img = Image.open("input.jpg").convert("RGB")
img.save("imagesTr/case_001_0000.png")  # single file, _0000 suffix

# Mask: save as single-channel PNG with integer label values
mask = Image.open("mask.png")
mask.save("labelsTr/case_001.png")  # no channel suffix
```

dataset.json for RGB:
```json
{
  "channel_names": {"0": "R", "1": "G", "2": "B"},
  "labels": {"background": 0, "tumor": 1},
  "numTraining": 500,
  "file_ending": ".png"
}
```

Note: Even though `channel_names` lists 3 channels, the image is stored as a single RGB `.png` file with only the `_0000` suffix. This is the sole exception to the one-file-per-channel rule.

### Grayscale 2D images (ultrasound, X-ray, etc.)
```python
from PIL import Image

img = Image.open("input.png").convert("L")
img.save("imagesTr/case_001_0000.png")
```

dataset.json for grayscale:
```json
{
  "channel_names": {"0": "Ultrasound"},
  "labels": {"background": 0, "lesion": 1},
  "numTraining": 200,
  "file_ending": ".png"
}
```

---

## 3D TIFF Datasets

For 3D TIFF stacks (e.g., microscopy, OCT), nnUNet uses `Tiff3DIO`. This includes **multi-frame TIFFs** (e.g., ImageJ stacks) — they are 3D volumes and Tiff3DIO handles them natively. Do NOT convert multi-frame TIFFs to `.nii.gz`.

Each `.tif` file must have a companion `.json` file (same name, without channel suffix) with spacing information:

```json
{
    "spacing": [7.6, 7.6, 80.0]
}
```

If the data has no real-world spacing (e.g., OCT), use `[1.0, 1.0, 1.0]` as placeholder.

Folder structure:
```
Dataset123_Foo/
├── dataset.json
├── imagesTr/
│   ├── cell6_0000.tif
│   └── cell6.json         # spacing info for cell6
└── labelsTr/
    ├── cell6.tif
    └── cell6.json          # spacing info for cell6
```

Set `"overwrite_image_reader_writer": "Tiff3DIO"` in dataset.json to ensure nnUNet uses the correct reader.

### How to handle 3D TIFF datasets
```python
import shutil
import json
import tifffile
import numpy as np

spacing = [1.0, 1.0, 1.0]  # replace with real spacing if known

# Images: copy .tif as-is, add companion .json
shutil.copy2("input/OCT001.tif", "imagesTr/OCT001_0000.tif")
with open("imagesTr/OCT001.json", "w") as f:
    json.dump({"spacing": spacing}, f)

# Masks: remap values if needed, write as .tif, add companion .json
mask = tifffile.imread("input/OCT001_mask.tif").astype(np.uint8)
mask[mask == 255] = 1  # remap to consecutive labels
tifffile.imwrite("labelsTr/OCT001.tif", mask)
with open("labelsTr/OCT001.json", "w") as f:
    json.dump({"spacing": spacing}, f)
```

### dataset.json for 3D TIFF
```json
{
  "channel_names": {"0": "OCT"},
  "labels": {"background": 0, "lesion": 1},
  "numTraining": 100,
  "file_ending": ".tif",
  "overwrite_image_reader_writer": "Tiff3DIO"
}
```

---

## Classification Labels (cls_data.csv + dataset.json)

Many datasets have case-level classification labels in addition to segmentation masks. These are stored in two places:

### cls_data.csv
A CSV file at the dataset root with format:
```csv
identifier,label
case_001,0
case_002,1
case_003,2
```

- `identifier`: matches the case ID used in imagesTr/labelsTr filenames (WITHOUT channel suffix or file extension)
- `label`: integer class label. Can also be a list for multi-label tasks: `"[1, 0]"`

### classification_labels in dataset.json
Add a `classification_labels` field to dataset.json that maps label names to their integer values:
```json
{
  "classification_labels": {
    "ISUP_grade": {
      "0": "Benign/Indolent (ISUP 0-1)",
      "1": "ISUP 1",
      "2": "ISUP 2",
      "3": "ISUP 3"
    }
  }
}
```

For multi-label classification (e.g., primary tumor origin with multiple classes):
```json
{
  "classification_labels": {
    "primary_tumor_origin": {
      "0": "NSCLC",
      "1": "Breast carcinoma",
      "2": "SCLC"
    }
  }
}
```

### Classification Label Sources
Classification labels can come from:
- Clinical metadata CSV/spreadsheet (e.g., ISUP grade, IDH mutation status, tumor type)
- Derived from segmentation masks (e.g., presence/absence of tumor = binary classification)
- Folder structure or filename patterns

**Important**: Classification labels and segmentation labels serve different purposes:
- Segmentation = voxel-level (WHERE is the lesion)
- Classification = case-level (WHAT type/grade is it)
- They should ideally capture different information — if classification can be trivially derived from the segmentation mask (e.g., "has any tumor voxel"), consider using a richer classification target instead (e.g., tumor grade, molecular subtype)

### Existing Examples in /mnt/pool/datasets/CY/nnUNet_raw/:
- `Dataset219_BrainMets`: `primary_tumor_origin` (NSCLC/Breast/SCLC) — multi-class
- `Dataset227_MU_Glioma_Post`: `primary_diagnosis` (GBM/Astrocytoma/Others) — multi-class
- `Dataset306_JSC_UCSD_PTGB`: `idh_mutation_status` (IDH Wild-Type/IDH Mutant) — binary with -1 for unknown
- `Dataset211_BMLMPS_FLAIR`: multi-label format `"[1, 0]"`
- `Dataset320_PICAI`: `ISUP_grade` (0-5) — ordinal grading scale

---

## Spatial Resampling for Multi-Modal Data

When combining modalities with **different spatial resolutions** (common in MRI), all channels must be resampled to a common reference space before nnUNet can use them.

### When to resample
- Check size, spacing, origin, and direction of each modality
- If any differ, resample the non-reference modalities to match the reference

### How to resample
```python
import SimpleITK as sitk

def resample_to_reference(moving_img, reference_img, interpolator=sitk.sitkLinear):
    """Resample moving image to match reference image geometry."""
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference_img)
    resampler.SetInterpolator(interpolator)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving_img)
```

### Interpolation choice
- **Images**: `sitk.sitkLinear` (smooth, preserves intensity gradients)
- **Labels/masks**: `sitk.sitkNearestNeighbor` (preserves integer label values)

### Example: PICAI dataset
- T2W: 384x384x19 @ 0.5mm spacing (high-res reference)
- ADC: 84x128x19 @ 2.0mm spacing → resample to T2W space
- HBV: 84x128x19 @ 2.0mm spacing → resample to T2W space
- Labels: already at T2W resolution

---

## Handling Common Input Layouts

### Layout A: Two flat folders (images/ and labels/)
```
input/
├── images/
│   ├── patient001.nii.gz
│   └── patient002.nii.gz
└── labels/
    ├── patient001.nii.gz
    └── patient002.nii.gz
```
→ Sort both folders, pair by sorted index or matching filename stem.

### Layout B: Per-subject folders
```
input/
├── patient001/
│   ├── T1.nii.gz
│   ├── T2.nii.gz
│   └── seg.nii.gz
└── patient002/
    ├── T1.nii.gz
    ├── T2.nii.gz
    └── seg.nii.gz
```
→ Walk subdirectories; use folder name as case ID; detect channels by known filenames.

### Layout C: Single folder, mixed files
```
input/
├── patient001_image.nii.gz
├── patient001_label.nii.gz
├── patient002_image.nii.gz
└── patient002_label.nii.gz
```
→ Use regex/glob patterns to separate images from labels by suffix.

### Layout D: 2D images with class folders
```
input/
├── train/
│   ├── ClassA/
│   │   ├── img001.png
│   │   └── img002.png
│   └── ClassB/
│       ├── img003.png
│       └── img004.png
└── masks/
    ├── img001.png
    └── img002.png
```
→ Walk class folders for images; derive classification labels from folder names.

---

## Multi-Modal Handling

For multi-modal MRI (e.g. T1, T2, FLAIR):
- Each modality becomes a separate file with incrementing channel index
- Channel order must be **identical** for all cases
- `channel_names` in dataset.json maps `"0"` → `"T1"`, `"1"` → `"T2"`, etc.

Example output for 4-channel BraTS-style data:
```
imagesTr/
├── BraTS_001_0000.nii.gz   # T1
├── BraTS_001_0001.nii.gz   # T1Gd
├── BraTS_001_0002.nii.gz   # T2
├── BraTS_001_0003.nii.gz   # FLAIR
└── ...
```

---

## Label Validation

nnUNet requires:
- Label 0 = background (always). If there is no background, do not use 0 for something else.
- Consecutive integers: 0, 1, 2, 3, ...
- No gaps (e.g. 0, 1, 4 is INVALID)
- Not all labels need to be present in every training case

Check and remap if needed:
```python
import numpy as np
import nibabel as nib

img = nib.load("label.nii.gz")
data = img.get_fdata().astype(int)
unique_vals = sorted(np.unique(data))
# Remap to consecutive if needed
mapping = {old: new for new, old in enumerate(unique_vals)}
```

---

## Ignore Label (Sparse Annotations)

nnUNet supports an `ignore` label for datasets with incomplete annotations (scribbles, partial slices, coarse masks). Regions marked with the ignore label are excluded from loss computation during training, but nnUNet still predicts dense segmentations at inference.

### Rules
- The ignore label **must** be the highest integer value in the segmentation
- It **must** be named `"ignore"` in dataset.json
- It is NOT predicted — do not include it in `regions_class_order`

### Example
```json
"labels": {
    "background": 0,
    "edema": 1,
    "necrosis": 2,
    "enhancing_tumor": 3,
    "ignore": 4
}
```

Use cases:
- Scribble supervision (save annotation time)
- Dense annotation of only a subset of slices
- Masking out faulty regions in reference segmentations

---

## Region-Based Training (Overlapping/Hierarchical Labels)

For tasks where evaluation targets are overlapping regions rather than individual labels (e.g., BraTS: whole tumor, tumor core, enhancing tumor), nnUNet supports region-based training.

### How it works
- Labels in dataset.json are declared as **lists of integers** representing which raw label values belong to that region
- An additional `regions_class_order` field tells nnUNet how to convert regions back to an integer segmentation map
- nnU-Net trains on regions and evaluates on regions

### Example (BraTS-style)
Standard label-based:
```json
"labels": {
    "background": 0,
    "edema": 1,
    "non_enhancing_and_necrosis": 2,
    "enhancing_tumor": 3
}
```

Region-based equivalent:
```json
"labels": {
    "background": 0,
    "whole_tumor": [1, 2, 3],
    "tumor_core": [2, 3],
    "enhancing_tumor": 3
},
"regions_class_order": [1, 2, 3]
```

### Critical rules
- `regions_class_order` length must equal the number of regions (excluding background)
- Order matters: encompassing regions first, substructures later (later entries overwrite earlier ones)
- **IMPORTANT**: When writing dataset.json, use `sort_keys=False` in `json.dump()` to preserve label declaration order!
- Compatible with the ignore label (just don't include ignore in `regions_class_order`)

---

## Environment Variables

nnUNet requires three environment variables to be set before running any commands:

```bash
export nnUNet_raw="/path/to/nnUNet_raw"
export nnUNet_preprocessed="/path/to/nnUNet_preprocessed"   # should be on fast storage (SSD)
export nnUNet_results="/path/to/nnUNet_results"
```

The conversion script outputs data to `nnUNet_raw`. After conversion, the user must set these variables before running `nnUNetv2_plan_and_preprocess`.

---

## Inference Data Format

The data format for inference **must match training exactly**:
- Same `file_ending` as specified in dataset.json
- Same channel order and naming convention (`{CASE_ID}_{XXXX}.{FILE_ENDING}`)
- All input channels must be present for every case
- You cannot train on `.png` and run inference on `.jpg`

---

## Migrating Existing Datasets

### From Medical Segmentation Decathlon (MSD)
```bash
nnUNetv2_convert_MSD_dataset -i /path/to/TaskXXX_Name -o DatasetXXX_Name
```

### From nnU-Net v1
```bash
nnUNetv2_convert_old_nnUNet_dataset /path/to/old/TaskXXX_Name DatasetXXX_Name
```

Key differences from v1:
- "modality" is now `channel_names`
- Labels are `name: int` (not `int: name`)
- Datasets are `DatasetXXX_Name` (not `TaskXXX`)
- `file_ending` field is new (supports multiple formats)

---

## Custom Data Splits

By default nnUNet uses 5-fold cross-validation with random splits. To use custom splits:

1. Create a `splits_final.json` in `nnUNet_preprocessed/DatasetXXX_NAME/`
2. Format: list of 5 dicts, each with `"train"` and `"val"` keys containing lists of case identifiers

```json
[
    {"train": ["case_001", "case_002", ...], "val": ["case_010", "case_011", ...]},
    {"train": ["case_003", "case_004", ...], "val": ["case_001", "case_002", ...]},
    ...
]
```

---

## Reference Files

- `references/dataset_json_spec.md` — Full dataset.json field reference
- `scripts/convert_template.py` — Reusable Python conversion script template
