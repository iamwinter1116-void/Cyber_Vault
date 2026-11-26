"""Dump FastAPI OpenAPI schema to contracts/openapi.yaml for `make openapi`."""

from __future__ import annotations

from pathlib import Path

import yaml

from services.api.main import create_app


def dump_openapi(out_path: Path) -> None:
    """Serialize the implemented FastAPI OpenAPI document as YAML."""
    doc = create_app().openapi()
    out_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    dump_openapi(Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml")
