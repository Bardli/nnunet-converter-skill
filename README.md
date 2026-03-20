# nnUNet Converter Skill for Claude Code

A [Claude Code](https://claude.com/claude-code) custom skill that converts medical imaging datasets (NIfTI `.nii`/`.nii.gz`, MetaImage `.mha`) into [nnUNet v2](https://github.com/MIC-DKFZ/nnUNet) format.

## What it does

When you mention nnUNet dataset conversion in a Claude Code conversation, this skill automatically activates and guides the conversion process:

- Organizes images into `imagesTr/labelsTr/imagesTs` folder structure
- Handles file renaming with proper channel suffixes (`_0000`, `_0001`, ...)
- Generates `dataset.json` with correct channel names, labels, and metadata
- Supports single-modality and multi-modal datasets (e.g., T1+T2+FLAIR MRI, multi-sequence prostate MRI)
- Handles spatial resampling for multi-modal data with different resolutions
- Supports classification labels (`cls_data.csv` + `classification_labels` in `dataset.json`)
- Converts between `.mha` and `.nii.gz` formats

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
git clone https://github.com/ChingYuanYu/nnunet-converter-skill.git .claude/skills/nnunet-converter
```

## Usage

Once installed, simply ask Claude Code to convert your dataset:

```
> convert my brain tumor dataset to nnUNet format
> prepare the prostate MRI data for nnUNet training
> create nnUNet dataset from the liver CT scans in /data/liver/
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

The generated conversion scripts use:
- Python 3.8+
- `nibabel` (for NIfTI I/O)
- `SimpleITK` (for `.mha` I/O and spatial resampling)
- `numpy`

## License

MIT
