"""
pipeline/contract.py — NETRA-DR Model Contract Loader & Validator

Loads and validates metadata.json for exported models across all pipeline phases.
Ensures zero hardcoding of image sizes, normalization parameters, class orders,
or thresholds in downstream inference code.
"""

from pathlib import Path
from typing import Any, Dict, Set, Union
import json
import os

# Mandatory fields across all model types (from docs/HANDOFF.md)
CORE_MANDATORY_FIELDS: Set[str] = {
    "model_name",
    "model_version",
    "input_size",
    "channels",
    "normalization",
    "model_file",
    "framework",
    "training_dataset",
    "preprocessing",
    "eval_metrics",
}

# Per-model-type additional mandatory fields
TYPE_SPECIFIC_FIELDS: Dict[str, Set[str]] = {
    "classifier": {
        "class_labels",
        "output_format",
        "threshold",
    },
    "segmentation": {
        "mask_labels",
        "output_format",
        "mask_resolution",
    },
    "ma_detector": {
        "candidate_extraction_method",
        "fp_reducer_model_file",
        "output_format",
    },
}

SUPPORTED_MODEL_TYPES: Set[str] = set(TYPE_SPECIFIC_FIELDS.keys())


class ModelContractError(ValueError):
    """Raised when a model contract or metadata.json is invalid, missing, or incomplete."""
    pass


class ModelArtifactNotFoundError(FileNotFoundError):
    """Raised when the model artifact specified in metadata.json cannot be found."""
    pass


def get_required_fields(model_type: str) -> Set[str]:
    """
    Returns the complete set of required fields for a given model type.
    """
    normalized_type = model_type.strip().lower()
    if normalized_type not in TYPE_SPECIFIC_FIELDS:
        supported = ", ".join(sorted(SUPPORTED_MODEL_TYPES))
        raise ModelContractError(
            f"Unsupported model type '{model_type}'. Supported types are: {supported}"
        )
    return CORE_MANDATORY_FIELDS | TYPE_SPECIFIC_FIELDS[normalized_type]


def load_contract(model_dir: Union[str, Path], model_type: str) -> Dict[str, Any]:
    """
    Reads and validates metadata.json from model_dir against the model contract schema.

    Args:
        model_dir: Directory containing metadata.json (e.g. models/quality/)
        model_type: One of 'classifier', 'segmentation', 'ma_detector'

    Returns:
        dict: Parsed and validated contract dictionary

    Raises:
        FileNotFoundError: If metadata.json does not exist in model_dir
        ModelContractError: If JSON is invalid, model_type is unsupported,
                            or required fields are missing.
    """
    dir_path = Path(model_dir)
    metadata_path = dir_path / "metadata.json"

    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"Model contract metadata file not found at: {metadata_path}"
        )

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            contract = json.load(f)
    except json.JSONDecodeError as e:
        raise ModelContractError(
            f"Corrupted or invalid JSON in model contract at '{metadata_path}': {e}"
        ) from e

    if not isinstance(contract, dict):
        raise ModelContractError(
            f"Invalid model contract format at '{metadata_path}': expected JSON object, got {type(contract).__name__}"
        )

    required_fields = get_required_fields(model_type)
    missing_fields = sorted(list(required_fields - set(contract.keys())))

    if missing_fields:
        missing_str = ", ".join(f"'{field}'" for field in missing_fields)
        raise ModelContractError(
            f"Model contract at '{metadata_path}' is missing required field(s) for type '{model_type}': {missing_str}"
        )

    return contract


def resolve_model_path(model_dir: Union[str, Path], contract: Dict[str, Any]) -> str:
    """
    Resolves the model artifact path from model_dir and contract['model_file'],
    verifying that the artifact exists on disk.

    Args:
        model_dir: Directory containing the model artifact
        contract: Validated contract dictionary containing 'model_file'

    Returns:
        str: Absolute or project-relative path to existing model file

    Raises:
        ModelContractError: If contract does not contain 'model_file'
        ModelArtifactNotFoundError: If the model artifact file does not exist on disk
    """
    if "model_file" not in contract:
        raise ModelContractError(
            "Model contract does not specify 'model_file'."
        )

    model_file = contract["model_file"]
    dir_path = Path(model_dir)

    target_path = Path(model_file) if Path(model_file).is_absolute() else dir_path / model_file

    if not target_path.is_file():
        raise ModelArtifactNotFoundError(
            f"Model artifact not found: '{target_path}' (expected from contract 'model_file': '{model_file}')"
        )

    return str(target_path)
