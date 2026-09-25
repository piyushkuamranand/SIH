# models/lesion_seg — NOT USED (ONNX contract removed 2026-09-26)

Lesion segmentation now calls:

    fundus_lesions_toolkit.models.segment()

which auto-downloads weights from HuggingFace on first call.
No ONNX file or metadata.json should be placed here.

Source: C:\Users\PIYUSH KUMAR\netra-dr-models\fundus-lesions-toolkit\
