from __future__ import annotations

import ast
from pathlib import Path

from .models import ClassInfo, Edge, FileInfo, FunctionInfo, ParameterInfo, RelationType


def _text(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _decorators(nodes: list[ast.expr]) -> list[str]:
    return [_text(n) or "<decorator>" for n in nodes]


def _parameters(args: ast.arguments) -> list[ParameterInfo]:
    values = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
    defaults = [None] * (len(values) - len(args.defaults) - len(args.kwonlyargs))
    defaults += [None] * len(args.kwonlyargs)
    positional_defaults = [None] * (len(args.posonlyargs) + len(args.args) - len(args.defaults)) + [_text(x) for x in args.defaults]
    result: list[ParameterInfo] = []
    for i, arg in enumerate(values):
        default = positional_defaults[i] if i < len(positional_defaults) else None
        result.append(ParameterInfo(arg.arg, _text(arg.annotation), default))
    if args.vararg:
        result.append(ParameterInfo("*" + args.vararg.arg, _text(args.vararg.annotation)))
    if args.kwarg:
        result.append(ParameterInfo("**" + args.kwarg.arg, _text(args.kwarg.annotation)))
    return result


class _FunctionVisitor(ast.NodeVisitor):
    def __init__(self, function: FunctionInfo):
        self.function = function
        self.depth = 0

    def visit_Call(self, node: ast.Call) -> None:
        name = _text(node.func)
        if name:
            self.function.calls.append(name)
        self.generic_visit(node)

    def _branch(self, node: ast.AST) -> None:
        self.function.complexity += 1
        self.depth += 1
        self.function.nesting = max(self.function.nesting, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    visit_If = _branch
    visit_For = _branch
    visit_AsyncFor = _branch
    visit_While = _branch
    visit_Try = _branch
    visit_Match = _branch

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.function.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)


class ModuleParser:
    def parse(self, path: Path, root: Path) -> tuple[FileInfo, list[FunctionInfo], list[ClassInfo], list[Edge]]:
        rel = path.relative_to(root).as_posix()
        module = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel.replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        text = path.read_text(encoding="utf-8", errors="replace")
        info = FileInfo(rel, module, len(text.splitlines()))
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            info.parse_error = f"{exc.msg} at line {exc.lineno}"
            return info, [], [], []
        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        edges: list[Edge] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                info.imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = (node.module or "")
                info.imports.extend(base + (f".{alias.name}" if base else alias.name) for alias in node.names)
        for node in ast.iter_child_nodes(tree):
            self._visit_definition(node, module, rel, functions, classes, edges, None)
        info.classes = len(classes)
        info.functions = len(functions)
        for imported in info.imports:
            edges.append(Edge(module, imported, RelationType.IMPORTS))
        return info, functions, classes, edges

    def _visit_definition(self, node: ast.AST, module: str, rel: str, functions: list[FunctionInfo], classes: list[ClassInfo], edges: list[Edge], parent: str | None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qname = f"{module}.{parent + '.' if parent else ''}{node.name}"
            fn = FunctionInfo(node.name, qname, rel, node.lineno, getattr(node, "end_lineno", node.lineno), _parameters(node.args), _text(node.returns), _decorators(node.decorator_list), isinstance(node, ast.AsyncFunctionDef))
            _FunctionVisitor(fn).visit(node)
            functions.append(fn)
            edges.append(Edge(parent or module, qname, RelationType.DEFINES))
            for call in fn.calls:
                edges.append(Edge(qname, call, RelationType.CALLS))
            return
        if isinstance(node, ast.ClassDef):
            qname = f"{module}.{parent + '.' if parent else ''}{node.name}"
            cls = ClassInfo(node.name, qname, rel, node.lineno, getattr(node, "end_lineno", node.lineno), [_text(x) or "<base>" for x in node.bases], [], _decorators(node.decorator_list))
            classes.append(cls)
            edges.append(Edge(parent or module, qname, RelationType.DEFINES))
            for base in cls.bases:
                edges.append(Edge(qname, base, RelationType.INHERITS))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cls.methods.append(child.name)
                self._visit_definition(child, module, rel, functions, classes, edges, node.name)
            return
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
            for child in ast.iter_child_nodes(node):
                self._visit_definition(child, module, rel, functions, classes, edges, parent)
