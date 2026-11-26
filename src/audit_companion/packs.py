"""Assessment pack loading and validation."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from audit_companion.models import AssessmentPack


class PackLoadError(ValueError):
    """Raised when an assessment pack cannot be read or validated."""


def load_pack(path: str | Path) -> AssessmentPack:
    pack_path = Path(path)
    try:
        with pack_path.open(encoding="utf-8") as pack_file:
            data = yaml.safe_load(pack_file)
    except OSError as error:
        raise PackLoadError(f"Unable to read assessment pack {pack_path}: {error}") from error
    except yaml.YAMLError as error:
        raise PackLoadError(f"Invalid YAML in assessment pack {pack_path}: {error}") from error

    if not isinstance(data, dict):
        raise PackLoadError(f"Assessment pack {pack_path} must contain a YAML mapping")

    try:
        return AssessmentPack.model_validate(data)
    except ValidationError as error:
        raise PackLoadError(f"Invalid assessment pack {pack_path}:\n{error}") from error
