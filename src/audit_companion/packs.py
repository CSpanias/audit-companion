"""Load the built-in assessment content."""

from importlib.resources import as_file, files
from pathlib import Path
from typing import Literal

import yaml
from pydantic import ValidationError

from audit_companion.models import AssessmentPack

BuiltinPack = Literal["mdm", "remote-access", "voip"]


class PackLoadError(ValueError):
    """Raised when built-in assessment content cannot be loaded."""


def load_builtin_pack(pack_id: BuiltinPack) -> AssessmentPack:
    resource = files("audit_companion").joinpath(
        "data",
        "packs",
        f"{pack_id}.yaml",
    )
    with as_file(resource) as pack_path:
        return _load_pack_file(pack_path)


def _load_pack_file(pack_path: Path) -> AssessmentPack:
    try:
        with pack_path.open(encoding="utf-8") as pack_file:
            data = yaml.safe_load(pack_file)
    except OSError as error:
        raise PackLoadError(
            f"Unable to read built-in assessment {pack_path}: {error}"
        ) from error
    except yaml.YAMLError as error:
        raise PackLoadError(
            f"Invalid YAML for built-in assessment {pack_path}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise PackLoadError(f"Built-in assessment {pack_path} must contain a YAML mapping")

    try:
        return AssessmentPack.model_validate(data)
    except ValidationError as error:
        raise PackLoadError(f"Invalid built-in assessment {pack_path}:\n{error}") from error
