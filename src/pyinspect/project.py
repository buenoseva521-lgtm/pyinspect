from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import load_ignored
from .models import AnalysisResult, Edge, Issue, RelationType
from .parser import ModuleParser

DEFAULT_IGNORED = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", "dist", "build"}


class Project:
    def __init__(self, root: str | Path, ignored: set[str] | None = None):
        self.root = Path(root).resolve()
        self.ignored = load_ignored(self.root) | (ignored or set())
        self.result = AnalysisResult(str(self.root))
        self._cache_path = self.root / ".pyinspect-cache.json"

    @property
    def files(self): return self.result.files
    @property
    def functions(self): return self.result.functions
    @property
    def classes(self): return self.result.classes
    @property
    def graph(self): return self.result.edges

    def _paths(self) -> list[Path]:
        def ignorado(path: Path) -> bool:
            return any(part in self.ignored or part.startswith(".dist_") or part.startswith("dist_") for part in path.relative_to(self.root).parts)
        return sorted(p for p in self.root.rglob("*.py") if not ignorado(p))

    def scan(self, use_cache: bool = True) -> AnalysisResult:
        self.result = AnalysisResult(str(self.root))
        if not self.root.is_dir():
            raise FileNotFoundError(f"O diretório do projeto não existe: {self.root}")
        parser = ModuleParser()
        for path in self._paths():
            info, functions, classes, edges = parser.parse(path, self.root)
            self.result.files.append(info)
            self.result.functions.extend(functions)
            self.result.classes.extend(classes)
            self.result.edges.extend(edges)
            if info.parse_error:
                self.result.issues.append(Issue("parse_error", f"Não foi possível analisar {info.path}: {info.parse_error}", info.path, "error"))
        self._analyze()
        if use_cache:
            self._write_cache()
        return self.result

    def _analyze(self) -> None:
        local_modules = {f.module for f in self.files}
        external: set[str] = set()
        for f in self.files:
            for imp in f.imports:
                root = imp.split(".")[0]
                if not any(imp == m or imp.startswith(m + ".") or m.startswith(imp + ".") for m in local_modules):
                    external.add(root)
        self.result.external_imports = sorted(external)
        self._cycles(local_modules)
        referenced = {e.target for e in self.graph if e.type == RelationType.CALLS}
        referenced |= {e.target for e in self.graph if e.type == RelationType.INHERITS}
        for fn in self.functions:
            if fn.qualified_name not in referenced and fn.name not in {"main", "__init__"}:
                self.result.issues.append(Issue("unused_function", "Função possivelmente não utilizada; a análise estática não conseguiu determinar seu uso.", fn.qualified_name))
        for cls in self.classes:
            if cls.qualified_name not in referenced:
                self.result.issues.append(Issue("unused_class", "Classe possivelmente não utilizada; a análise estática não conseguiu determinar seu uso.", cls.qualified_name))
        for fn in self.functions:
            if fn.complexity >= 10:
                self.result.issues.append(Issue("complexity", f"A complexidade da função é {fn.complexity}, com aninhamento {fn.nesting}.", fn.qualified_name, details={"complexity": fn.complexity, "nesting": fn.nesting}))

    def _cycles(self, modules: set[str]) -> None:
        adjacency: dict[str, list[str]] = {m: [] for m in modules}
        for edge in self.graph:
            if edge.type == RelationType.IMPORTS:
                target = next((m for m in modules if edge.target == m or edge.target.startswith(m + ".") or m.startswith(edge.target + ".")), None)
                if target:
                    adjacency.setdefault(edge.source, []).append(target)
        visiting: set[str] = set(); visited: set[str] = set()
        def dfs(node: str, stack: list[str]):
            if node in visiting:
                cycle = stack[stack.index(node):] + [node]
                self.result.issues.append(Issue("circular_import", "Circular import candidate: " + " → ".join(cycle), node, details={"cycle": cycle}))
                return
            if node in visited: return
            visiting.add(node)
            for nxt in adjacency.get(node, []): dfs(nxt, stack + [node])
            visiting.remove(node); visited.add(node)
        for node in adjacency: dfs(node, [])

    def find_function(self, name: str):
        return [f for f in self.functions if f.name == name or f.qualified_name == name]
    def find_class(self, name: str):
        return [c for c in self.classes if c.name == name or c.qualified_name == name]
    def callers(self, name: str): return [e.source for e in self.graph if e.type == RelationType.CALLS and (e.target == name or e.target.endswith("." + name))]
    def callees(self, name: str): return [e.target for e in self.graph if e.type == RelationType.CALLS and (e.source == name or e.source.endswith("." + name))]
    def import_graph(self): return [e for e in self.graph if e.type == RelationType.IMPORTS]

    def _write_cache(self):
        payload = {"version": 1, "files": {f.path: hashlib.sha256((self.root / f.path).read_bytes()).hexdigest() for f in self.files}}
        self._cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
