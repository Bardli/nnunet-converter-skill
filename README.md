# nnUNet Converter Skill for Claude Code

A [Claude Code](https://claude.com/claude-code) custom skill that converts medical imaging datasets into [nnUNet v2](https://github.com/MIC-DKFZ/nnUNet) format.

Supports all nnUNet-native file formats: NIfTI (`.nii.gz`), MHA (`.mha`), NRRD (`.nrrd`), PNG (`.png`), BMP (`.bmp`), TIFF (`.tif`).

## Core Principle

**Avoid unnecessary format conversion.** nnUNet v2 natively supports many file formats. If your data is already in a supported format, the skill will copy/rename files without converting them. For example:
- 2D PNG images stay as PNG (not wrapped in NIfTI)
- MHA files stay as MHA (not converted to .nii.gz)
- RGB images are stored as a single file (not split into 3 channel files)

## What it does

When you mention nnUNet dataset conversion in a Claude Code conversation, this skill automatically activates and guides the conversion process:

- Organizes images into `imagesTr/labelsTr/imagesTs` folder structure
- Handles file renaming with proper channel suffixes (`_0000`, `_0001`, ...)
- Generates `dataset.json` with correct channel names, labels, and metadata
- Supports single-modality and multi-modal datasets
- Handles spatial resampling for multi-modal data with different resolutions
- Supports classification labels (`cls_data.csv` + `classification_labels` in `dataset.json`)
- Supports 2D natural images (PNG/BMP), 3D volumes (NIfTI/MHA/NRRD), and 3D TIFF stacks

## Installation

Copy the skill into your project's `.claude/skills/` directory:

```bash
# From your project root
mkdir -p .claude/skills
cp -r nnunet-converter .claude/skills/nnunet-converter
```

Or clone directly:

```bash
mkdir -p .claude/skills
git clone https://github.com/Bardli/nnunet-converter-skill.git .claude/skills/nnunet-converter
```

## Usage

Once installed, simply ask Claude Code to convert your dataset:

```
> convert my brain tumor dataset to nnUNet format
> prepare the prostate MRI data for nnUNet training
> create nnUNet dataset from the endoscopy images in /data/endo/
```

The skill will ask clarifying questions about your dataset (modalities, label values, dataset ID, etc.) and then generate a conversion script tailored to your data.

## Structure

```
nnunet-converter/
├── SKILL.md                          # Skill definition and workflow
├── references/
│   └── dataset_json_spec.md          # dataset.json field reference
├── scripts/
│   └── convert_template.py           # Reusable conversion script template
└── README.md
```

## Requirements

The generated conversion scripts use (install only what your data format needs):
- Python 3.8+
- `Pillow` (for 2D images: PNG, BMP, TIFF, JPG→PNG conversion)
- `nibabel` (for NIfTI I/O)
- `SimpleITK` (for `.mha`/`.nrrd` I/O and spatial resampling)
- `numpy`

## License

MIT
