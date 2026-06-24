from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import json


@dataclass
class ProjectMeta:
    name: str = "Untitled Project"
    client: str = ""
    location: str = ""
    code_basis: str = "IPC / ASHRAE / Local AHJ"
    prepared_by: str = ""
    revision: str = "P01"


@dataclass
class FluxelProject:
    meta: ProjectMeta = field(default_factory=ProjectMeta)
    modules: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FluxelProject":
        meta = ProjectMeta(**data.get("meta", {}))
        return cls(meta=meta, modules=data.get("modules", {}))
