# NETRA-DR

NETRA-DR is an explainable AI diabetic retinopathy screening prototype developed for SIH26038 (MathWorks) that processes fundus retinal photographs through a four-phase screening pipeline: quality gate verification, retinal structure analysis, diabetic retinopathy grading and referral decision, and model attention explainability. For project architecture, pipeline design, model contract specifications, and engineering conventions, refer to [docs/HANDOFF.md](docs/HANDOFF.md) as the primary entry point for contributors.

## Quick Start — One Command Launch

### Windows
```bat
run_demo.bat
```

### Linux / macOS / Git Bash on Windows
```bash
bash run_demo.sh
```

Both scripts install dependencies from `requirements.txt` and start the Flask server at **http://127.0.0.1:5000**.

### Manual launch
```bash
pip install -r requirements.txt
python app/app.py
```

## Requirements

- Python 3.10 or later
- ONNX model artifacts in `models/` (see `docs/HANDOFF.md` — model artifacts are exported from MATLAB; missing models show as "unavailable" in the web UI rather than crashing)

## Project Structure

```
netra-dr/
├── pipeline/           Core pipeline modules (Phase 1–4 + report + startup check)
├── app/                Flask web app (app.py + templates/ + static/)
├── models/             Model directories (ONNX artifacts placed here after MATLAB export)
├── configs/            Configuration JSONs (preprocessing, calibration, decision rule)
├── data/demo/          Demo fundus images for the live presentation
├── tests/              pytest test suite
├── docs/               HANDOFF.md, IMPLEMENTATION_SCHEMA.md, TASKS.md, checkpoints/
├── matlab/             MATLAB training scripts and Simulink workflow model
├── run_demo.bat        Windows one-command launcher
└── run_demo.sh         Unix one-command launcher
```
