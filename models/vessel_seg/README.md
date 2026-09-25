# models/vessel_seg — NOT USED (ONNX contract removed 2026-09-26)

Vessel segmentation now loads **natively** from:

    C:\Users\PIYUSH KUMAR\netra-dr-models\FR-UNet\pretrained_weights\DRIVE\checkpoint-epoch40.pth

via `pipeline/structure.py::run_vessel_segmentation()` using `models.fr_unet.FR_UNet`.

No ONNX file or metadata.json should be placed here.
