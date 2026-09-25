# NETRA-DR Model Contract Specification

This document defines the model contract specification as described in [docs/HANDOFF.md](HANDOFF.md).
Every MATLAB-trained model ships as two files within its stage directory:

```text
models/<stage_name>/
    <model_artifact>          (e.g. quality_model.onnx)
    metadata.json
```

The inference code reads `metadata.json` via `pipeline.contract.load_contract` and derives preprocessing/postprocessing parameters from it. Downstream inference code must never hardcode image size, normalization parameters, class orders, or thresholds.

## Mandatory Core Fields (All Models)

All models regardless of type must specify the following 10 core fields in `metadata.json`:

| Field | Description | Example |
|---|---|---|
| `model_name` | Name or architecture identifier | `"quality_mobilenetv2"` |
| `model_version` | Model export version / iteration | `"1.0.0"` |
| `input_size` | Expected input dimensions `[height, width]` | `[224, 224]` |
| `channels` | Number of image channels | `3` |
| `normalization` | Normalization parameters (mean, std, scale range) | `{"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}` |
| `model_file` | Filename of the model artifact | `"quality_model.onnx"` |
| `framework` | Export framework / runtime | `"onnx"` |
| `training_dataset` | Dataset(s) used during training in MATLAB | `"DDR"` |
| `preprocessing` | Ordered preprocessing operations | `["fov_crop", "resize", "clahe", "normalize"]` |
| `eval_metrics` | Evaluation metrics achieved during validation | `{"accuracy": 0.94, "auc": 0.97}` |

## Additional Mandatory Fields by Model Type

| Model Type | Extra Mandatory Fields | Field Descriptions / Examples |
|---|---|---|
| `classifier` (quality, grading) | `class_labels`<br>`output_format`<br>`threshold` | List of class label strings: `["Accept", "Reject"]`<br>Format string: `"softmax_probs"`<br>Decision threshold float or dict: `0.5` |
| `segmentation` (vessel, HE/EX/SE) | `mask_labels`<br>`output_format`<br>`mask_resolution` | Label string(s) for segmented structures: `["vessel"]`<br>Format string: `"binary_mask"` or `"multi_channel_mask"`<br>Output mask dimensions: `[512, 512]` |
| `ma_detector` (hybrid) | `candidate_extraction_method`<br>`fp_reducer_model_file`<br>`output_format` | Extraction method description: `"morphological_tophat"`<br>Artifact file for false positive reduction: `"ma_fp_reducer.onnx"`<br>Format string: `"candidate_list_with_scores"` |

## Implementation Reference

The contract validation is implemented in [pipeline/contract.py](../pipeline/contract.py):
- `load_contract(model_dir, model_type)`: Loads and checks all mandatory fields for the specified type.
- `resolve_model_path(model_dir, contract)`: Resolves and verifies that the model artifact file exists on disk.
