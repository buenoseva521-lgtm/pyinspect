from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RelationType(str, Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    DEFINES = "DEFINES"
    USES = "USES"


@dataclass
class ParameterInfo:
    name: str
    annotation: str | None = None
    default: str | None = None


@dataclass
class FunctionInfo:
    name: str
    qualified_name: str
    file: str
    line_start: int
    line_end: int
    parameters: list[ParameterInfo] = field(default_factory=list)
    return_annotation: str | None = None
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    calls: list[str] = field(default_factory=list)
    complexity: int = 1
    nesting: int = 0


@dataclass
class ClassInfo:
    name: str
    qualified_name: str
    file: str
    line_start: int
    line_end: int
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)


@dataclass
class FileInfo:
    path: str
    module: str
    lines: int
    classes: int = 0
    functions: int = 0
    imports: list[str] = field(default_factory=list)
    parse_error: str | None = None


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: RelationType


@dataclass
class Issue:
    kind: str
    message: str
    subject: str
    severity: str = "warning"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    root: str
    files: list[FileInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    external_imports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "root": self.root,
            "files": [asdict(x) for x in self.files],
            "functions": [asdict(x) for x in self.functions],
            "classes": [asdict(x) for x in self.classes],
            "edges": [{"source": e.source, "target": e.target, "type": e.type.value} for e in self.edges],
            "issues": [asdict(x) for x in self.issues],
            "external_imports": self.external_imports,
        }
