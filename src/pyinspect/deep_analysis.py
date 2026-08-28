from __future__ import annotations

import ast
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from .models import RelationType
from .project import Project


def _source_nodes(project: Project) -> list[tuple[str, ast.AST]]:
    nodes: list[tuple[str, ast.AST]] = []
    for file_info in project.files:
        path = project.root / file_info.path
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes.append((file_info.path, node))
    return nodes


def _complexity(project: Project) -> dict[str, Any]:
    functions = sorted(project.functions, key=lambda x: (-x.complexity, x.qualified_name))
    by_file: dict[str, list[int]] = defaultdict(list)
    for fn in project.functions:
        by_file[fn.file].append(fn.complexity)
    files = sorted(((path, sum(values), len(values), mean(values)) for path, values in by_file.items()), key=lambda x: (-x[1], x[0]))
    values = [fn.complexity for fn in project.functions]
    return {
        "media": round(mean(values), 2) if values else 0.0,
        "funcoes": [{"nome": fn.qualified_name, "arquivo": fn.file, "complexidade": fn.complexity, "aninhamento": fn.nesting, "status": "alta" if fn.complexity >= 10 else "moderada" if fn.complexity >= 5 else "baixa"} for fn in functions],
        "arquivos": [{"arquivo": path, "complexidade_total": total, "funcoes": count, "media": round(avg, 2)} for path, total, count, avg in files],
        "altas": [fn.qualified_name for fn in functions if fn.complexity >= 10],
    }


def _dependencies(project: Project) -> dict[str, Any]:
    local_modules = {f.module for f in project.files}
    import_counter = Counter(imp.split(".")[0] for f in project.files for imp in f.imports)
    internal: list[dict[str, str]] = []
    external: list[str] = []
    for file_info in project.files:
        for imp in file_info.imports:
            is_internal = any(imp == mod or imp.startswith(mod + ".") or mod.startswith(imp + ".") for mod in local_modules)
            if is_internal:
                internal.append({"origem": file_info.module, "destino": imp})
            else:
                external.append(imp.split(".")[0])
    return {
        "modulos_mais_importados": [{"modulo": name, "quantidade": count} for name, count in import_counter.most_common()],
        "externos": sorted(set(external)),
        "internos": internal,
        "relacoes": [{"origem": e.source, "destino": e.target, "tipo": e.type.value} for e in project.graph if e.type == RelationType.IMPORTS],
        "ciclos": [issue.details.get("cycle", []) for issue in project.result.issues if issue.kind == "circular_import"],
    }


def _unused(project: Project) -> dict[str, Any]:
    call_targets = {e.target for e in project.graph if e.type == RelationType.CALLS}
    inheritance_targets = {e.target for e in project.graph if e.type == RelationType.INHERITS}
    functions = [fn.qualified_name for fn in project.functions if fn.qualified_name not in call_targets and fn.name not in {"main", "__init__"}]
    classes = [cls.qualified_name for cls in project.classes if cls.qualified_name not in inheritance_targets]
    imports: list[str] = []
    for file_info in project.files:
        try:
            tree = ast.parse((project.root / file_info.path).read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    if local not in names:
                        imports.append(f"{file_info.path}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    local = alias.asname or alias.name
                    if alias.name != "*" and local not in names:
                        imports.append(f"{file_info.path}: {alias.name}")
    defined_modules = {f.module for f in project.files}
    imported_modules = {imp for f in project.files for imp in f.imports}
    files = [f.path for f in project.files if f.module not in imported_modules and Path(f.path).name not in {"main.py", "__main__.py", "cli.py", "app.py"}]
    return {"funcoes_possivelmente_nao_utilizadas": functions, "classes_possivelmente_nao_utilizadas": classes, "imports_possivelmente_nao_utilizados": imports, "arquivos_possivelmente_nao_utilizados": files, "observacao": "Possivelmente não utilizado; a análise estática não prova que o código esteja morto."}


def _structure(project: Project) -> dict[str, Any]:
    files = sorted(((f.path, f.lines) for f in project.files), key=lambda x: (-x[1], x[0]))
    classes = sorted(((f.path, f.classes) for f in project.files), key=lambda x: (-x[1], x[0]))
    functions = sorted(((f.path, f.functions) for f in project.files), key=lambda x: (-x[1], x[0]))
    tree: list[str] = []
    for file_info in project.files:
        tree.append(file_info.path)
    return {"arvore": tree, "maiores_arquivos": [{"arquivo": p, "linhas": n} for p, n in files[:10]], "modulos_com_mais_classes": [{"arquivo": p, "classes": n} for p, n in classes[:10] if n], "modulos_com_mais_funcoes": [{"arquivo": p, "funcoes": n} for p, n in functions[:10] if n]}


def _quality(project: Project) -> dict[str, Any]:
    large_functions = [{"nome": fn.qualified_name, "arquivo": fn.file, "linhas": fn.line_end - fn.line_start + 1} for fn in project.functions if fn.line_end - fn.line_start + 1 >= 50]
    large_classes = [{"nome": cls.qualified_name, "arquivo": cls.file, "linhas": cls.line_end - cls.line_start + 1} for cls in project.classes if cls.line_end - cls.line_start + 1 >= 100]
    many_args = [{"nome": fn.qualified_name, "quantidade": len(fn.parameters)} for fn in project.functions if len(fn.parameters) > 5]
    fingerprints: Counter[str] = Counter()
    locations: dict[str, list[str]] = defaultdict(list)
    for file_path, node in _source_nodes(project):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            fingerprint = hashlib.sha1(ast.dump(node, include_attributes=False).encode()).hexdigest()
            fingerprints[fingerprint] += 1
            locations[fingerprint].append(f"{file_path}:{getattr(node, 'lineno', 0)}")
    duplicates = [{"ocorrencias": count, "locais": locations[key]} for key, count in fingerprints.items() if count > 1]
    suspicious_imports = [f"{f.path}: import amplo ou dinâmico" for f in project.files if any(imp.endswith(".*") for imp in f.imports)]
    return {"funcoes_muito_grandes": large_functions, "classes_muito_grandes": large_classes, "excesso_de_argumentos": many_args, "duplicacao_estatica": duplicates, "imports_suspeitos": suspicious_imports, "observacao": "Os limites são heurísticas transparentes: 50 linhas por função, 100 por classe e 5 argumentos."}


def build_deep_analysis(project: Project) -> dict[str, Any]:
    total_lines = sum(f.lines for f in project.files)
    modules = {f.module for f in project.files}
    connected = Counter()
    module_names = {f.module for f in project.files}
    for edge in project.graph:
        if edge.source in module_names:
            connected[edge.source] += 1
        if edge.target in module_names:
            connected[edge.target] += 1
    entry_points = [f.path for f in project.files if Path(f.path).name in {"main.py", "__main__.py", "cli.py", "app.py", "manage.py"}]
    entry_points += [f.path for f in project.files if any(fn.name == "main" and fn.file == f.path for fn in project.functions) and f.path not in entry_points]
    return {
        "resumo": {"arquivos": len(project.files), "linhas_de_codigo": total_lines, "classes": len(project.classes), "funcoes": len(project.functions), "funcoes_async": sum(fn.is_async for fn in project.functions), "imports": sum(len(f.imports) for f in project.files), "pacotes_externos": len(project.result.external_imports)},
        "complexidade": _complexity(project),
        "dependencias": _dependencies(project),
        "codigo_possivelmente_nao_utilizado": _unused(project),
        "estrutura": _structure(project),
        "qualidade": _quality(project),
        "grafo": {"modulos": len(modules), "relacoes": len(project.graph), "ciclos": len(_dependencies(project)["ciclos"]), "modulos_mais_conectados": [{"modulo": name, "relacoes": count} for name, count in connected.most_common(10)]},
        "entry_points": sorted(set(entry_points)),
    }
