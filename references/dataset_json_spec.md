# nnUNet v2 dataset.json Field Reference

## Required Fields

### `channel_names` (dict, required)
Maps channel index string → modality name string.
```json
"channel_names": {
  "0": "CT"
}
```
```json
"channel_names": {
  "0": "T1",
  "1": "T1Gd",
  "2": "T2",
  "3": "FLAIR"
}
```
**Critical**: The string value controls normalization:
- `"CT"` → global foreground normalization (CT Hounsfield units)
- Anything else → per-channel z-score normalization (appropriate for MRI)

### `labels` (dict, required)
Maps label name → integer value. **name:int** (NOT int:name like nnUNet v1).
```json
"labels": {
  "background": 0,
  "liver": 1,
  "tumor": 2
}
```
Rules:
- `background` must map to `0`
- Values must be consecutive integers: 0, 1, 2, 3, ...
- No gaps allowed

### `numTraining` (int, required)
Number of training cases (i.e., number of entries in `imagesTr` / number of unique case IDs, NOT number of files).

### `file_ending` (string, required)
File extension used for ALL images and segmentations.
- `.nii.gz` — recommended, widely supported
- `.nii` — uncompressed NIfTI
- `.mha` — MetaImage format
- Must be identical for images and labels

---

## Optional Fields

### `name` (string)
Human-readable dataset name. Not used by nnUNet but useful for documentation.
```json
"name": "Dataset042_LiverSeg"
```

### `description` (string)
Free text description. Not used by nnUNet.

### `reference` (string)
Citation or URL for the dataset. Not used by nnUNet.

### `licence` (string)
Data license. Not used by nnUNet.

### `overwrite_image_reader_writer` (string)
Force a specific IO backend. Usually not needed — nnUNet auto-detects.
- `"SimpleITKIO"` — use for `.mha`, `.nrrd`, or when nibabel fails
- `"NibabelIO"` — use for NIfTI when SimpleITK causes issues
- `"NibabelIOWithReorient"` — like NibabelIO but also reorients to RAS

### `classification_labels` (dict)
Case-level classification labels. Maps a task name → {class_int: class_name}.
Must be paired with a `cls_data.csv` file at the dataset root.
```json
"classification_labels": {
  "ISUP_grade": {
    "0": "Benign/Indolent (ISUP 0-1)",
    "1": "ISUP 1",
    "2": "ISUP 2",
    "3": "ISUP 3",
    "4": "ISUP 4",
    "5": "ISUP 5"
  }
}
```
The `cls_data.csv` format:
```csv
identifier,label
case_001,0
case_002,3
```
Where `identifier` matches the case ID in imagesTr/labelsTr (no channel suffix, no extension),
and `label` is the integer class. For multi-label tasks, use list format: `"[1, 0]"`.

### `regions_class_order` (list, only for region-based training)
Only needed if using hierarchical/overlapping labels. Leave out for standard segmentation.

---

## Full Example — Single-Modality CT
```json
{
  "name": "Dataset042_LiverSeg",
  "description": "Liver segmentation from abdominal CT",
  "reference": "https://example.com/dataset",
  "licence": "CC-BY 4.0",
  "channel_names": {
    "0": "CT"
  },
  "labels": {
    "background": 0,
    "liver": 1,
    "tumor": 2
  },
  "numTraining": 131,
  "file_ending": ".nii.gz"
}
```

## Full Example — Multi-Modal MRI
```json
{
  "name": "Dataset043_BrainTumour",
  "description": "Glioma segmentation from multi-modal MRI",
  "channel_names": {
    "0": "T1",
    "1": "T1Gd",
    "2": "T2",
    "3": "FLAIR"
  },
  "labels": {
    "background": 0,
    "enhancing_tumor": 1,
    "necrotic_core": 2,
    "edema": 3
  },
  "numTraining": 484,
  "file_ending": ".nii.gz",
  "overwrite_image_reader_writer": "SimpleITKIO"
}
```

## Full Example — MHA Input
```json
{
  "name": "Dataset050_Prostate",
  "channel_names": {
    "0": "T2"
  },
  "labels": {
    "background": 0,
    "prostate": 1
  },
  "numTraining": 32,
  "file_ending": ".mha",
  "overwrite_image_reader_writer": "SimpleITKIO"
}
```
