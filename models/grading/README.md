# models/grading — NOT USED (ONNX contract removed 2026-09-26)

DR grading now loads drdetect EfficientNet-B0 from:

    ~/.cache/huggingface/hub/models--adarshcod30--drdetect-dr-screening/
    snapshots/f1ad9f790312cec657782f097f499e9bda5755fa/best.ckpt

via `pipeline/grading.py::run_grading()` using GradingModule.load_from_checkpoint().

NOTE: sakshamkr1/ResNet50-APTOS-DR returns 404 on HuggingFace — that repo does not exist.
The drdetect EfficientNet-B0 is the only available trained grader.

No ONNX file or metadata.json should be placed here.
