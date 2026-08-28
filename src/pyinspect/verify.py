from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path
from typing import Any


EXTENSIONS = {
    ".py": "Python", ".pyi": "Python stub", ".toml": "TOML", ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java",
    ".c": "C", ".h": "C Header", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".hpp": "C++ Header", ".rs": "Rust", ".go": "Go", ".php": "PHP", ".rb": "Ruby",
    ".sh": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
}
IGNORED = {".git", "__pycache__", ".pytest_cache", "node_modules", "venv", ".venv", "dist", "build"}
SECRET_RE = re.compile(r"(?i)(token|api[_-]?key|password|passwd|secret|credential)[\s'\"]*[:=][\s'\"]*['\"]([^'\"]{4,})['\"]")


def language_for(path: Path) -> str:
    return EXTENSIONS.get(path.suffix.lower(), "desconhecida")


def _name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""


def _value(node: ast.AST | None, mask_secrets: bool = True) -> str:
    if node is None:
        return "nenhum valor"
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            value = node.value
            if mask_secrets and len(value) >= 4 and any(x in value.lower() for x in ("token", "secret", "password", "apikey")):
                return '"********"'
            return repr(value[:100])
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _name(node)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return f"coleção com {len(node.elts)} item(ns)"
    if isinstance(node, ast.Dict):
        return f"dicionário com {len(node.keys)} item(ns)"
    if isinstance(node, ast.Call):
        return f"resultado de {_name(node.func) or 'uma chamada'}"
    return "expressão"


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, str(exc)


class FileVerification:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.text = ""
        self.tree: ast.Module | None = None
        self.language = language_for(self.path)
        self.error: str | None = None
        self.imports: list[str] = []
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.assignments: list[str] = []
        self.flow: list[str] = []
        self.inputs: list[str] = []
        self.outputs: list[str] = []
        self.effects: list[str] = []
        self.attention: list[str] = []
        self.docstring = ""

    def parse(self) -> "FileVerification":
        if not self.path.is_file():
            self.error = f"arquivo não encontrado: {self.path}"
            return self
        self.text, error = _read_text(self.path)
        if error:
            self.error = error
            return self
        assert self.text is not None
        if self.language in {"Python", "Python stub"}:
            try:
                self.tree = ast.parse(self.text, filename=str(self.path))
            except SyntaxError as exc:
                self.error = f"erro de sintaxe na linha {exc.lineno}: {exc.msg}"
                return self
            self._parse_python()
        else:
            self._parse_structured_or_text()
        return self

    def _parse_python(self) -> None:
        assert self.tree is not None
        self.docstring = ast.get_docstring(self.tree) or ""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                self.imports.extend(a.name for a in node.names if a.name not in self.imports)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                for a in node.names:
                    item = base + (f".{a.name}" if base else a.name)
                    if item not in self.imports:
                        self.imports.append(item)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.append(self._function(node))
            elif isinstance(node, ast.ClassDef):
                self.classes.append(self._class(node))
            elif isinstance(node, ast.Call):
                self._call(node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                self.assignments.extend(_name(t) for t in targets if _name(t))
            elif isinstance(node, ast.If):
                self.flow.append(f"avalia uma condição if na linha {node.lineno}")
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                self.flow.append(f"repete operações em um laço na linha {node.lineno}")
            elif isinstance(node, ast.Try):
                self.flow.append(f"trata exceções com try/except na linha {node.lineno}")
            elif isinstance(node, ast.With):
                self.flow.append(f"usa um contexto protegido com with na linha {node.lineno}")
            elif isinstance(node, ast.AsyncFunctionDef):
                self.flow.append(f"define uma operação assíncrona na linha {node.lineno}")
            elif isinstance(node, ast.Await):
                self.flow.append(f"aguarda uma operação assíncrona na linha {node.lineno}")
            elif isinstance(node, (ast.Yield, ast.YieldFrom)):
                self.flow.append(f"produz valores progressivamente na linha {node.lineno}")
            elif isinstance(node, ast.Raise):
                self.attention.append(f"pode lançar uma exceção explicitamente na linha {node.lineno}")
        self._detect_attention()

    def _parse_structured_or_text(self) -> None:
        if self.path.suffix.lower() == ".toml":
            try:
                data = tomllib.loads(self.text)
                self.assignments = list(data.keys())
                self.flow.append("define metadados e configuração no formato TOML")
            except tomllib.TOMLDecodeError as exc:
                self.error = f"não foi possível analisar TOML: {exc}"
        elif self.path.suffix.lower() == ".json":
            try:
                data = json.loads(self.text)
                self.assignments = list(data.keys()) if isinstance(data, dict) else []
                self.flow.append("define dados estruturados no formato JSON")
            except json.JSONDecodeError as exc:
                self.error = f"não foi possível analisar JSON: {exc}"
        elif self.path.suffix.lower() in {".yaml", ".yml"}:
            self.flow.append("define configuração ou dados estruturados no formato YAML")
            self.assignments = [line.split(":", 1)[0].strip() for line in self.text.splitlines() if ":" in line and not line.lstrip().startswith("#")]
        else:
            self._parse_text_patterns()

    def _parse_text_patterns(self) -> None:
        lines = self.text.splitlines()
        nonempty = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith(("#", "//", "/*", "--"))]
        if self.language == "Shell":
            self.flow.append("parece executar comandos de shell em sequência")
        elif self.language in {"HTML", "CSS"}:
            self.flow.append("define estrutura ou apresentação de uma página web")
        elif self.language == "SQL":
            self.flow.append("define ou executa operações sobre dados em um banco SQL")
        else:
            self.flow.append(f"contém {len(nonempty)} linha(s) de código no formato {self.language}")
        for line in lines:
            low = line.lower()
            if any(x in low for x in ("http://", "https://", "fetch(", "curl ")):
                self.effects.append("contém uma URL ou possível operação de rede")
            if any(x in low for x in ("password", "secret", "token", "api_key")):
                self.attention.append("contém um identificador que pode representar segredo; valores não são exibidos")

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
        args = [a.arg for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
        returns = [_value(n.value) for n in ast.walk(node) if isinstance(n, ast.Return)]
        calls = [_name(n.func) for n in ast.walk(node) if isinstance(n, ast.Call) and _name(n.func)]
        return {"nome": node.name, "linha": node.lineno, "final": getattr(node, "end_lineno", node.lineno), "argumentos": args, "async": isinstance(node, ast.AsyncFunctionDef), "retornos": returns, "chamadas": list(dict.fromkeys(calls))}

    def _class(self, node: ast.ClassDef) -> dict[str, Any]:
        methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        bases = [_name(n) or "base não identificada" for n in node.bases]
        return {"nome": node.name, "linha": node.lineno, "bases": bases, "métodos": methods}

    def _call(self, node: ast.Call) -> None:
        name = _name(node.func) or "chamada dinâmica"
        args = [_value(a) for a in node.args[:3]]
        lower = name.lower()
        if lower in {"print", "builtins.print"}:
            description = f"exibe {', '.join(args) if args else 'informação'} no terminal"
            self.outputs.append(f"imprime {', '.join(args) if args else 'informação'} na saída padrão")
            self.effects.append("escreve texto na saída padrão")
        elif lower in {"input", "builtins.input"}:
            description = "solicita uma informação digitada pelo usuário"
            self.inputs.append("recebe informação digitada pelo usuário")
        elif lower in {"open", "io.open"}:
            description = f"abre um arquivo{(' com ' + ', '.join(args)) if args else ''}"
            self.effects.append("acessa um arquivo")
        elif lower.endswith((".read", ".readline", ".readlines")):
            description = "lê dados de um arquivo ou fluxo"
            self.inputs.append("lê dados de um arquivo ou fluxo")
        elif lower.endswith((".write", ".writelines")):
            description = "escreve dados em um arquivo ou fluxo"
            self.outputs.append("grava dados em um arquivo ou fluxo")
            self.effects.append("escreve dados em um arquivo")
        elif any(x in lower for x in ("requests.", "httpx.", "urllib", "aiohttp", "socket")):
            description = "faz uma operação de rede"
            self.effects.append("realiza uma operação de rede")
        elif lower.endswith((".send", ".send_message", ".reply", ".respond")):
            description = "envia uma mensagem ou resposta"
            self.outputs.append("envia uma mensagem ou resposta")
        elif lower in {"eval", "exec", "os.system", "subprocess.run", "subprocess.call", "subprocess.Popen"}:
            description = "executa código ou comando externo"
            self.attention.append(f"foi detectado uso de {name}; o código parece executar algo dinamicamente ou externamente")
        else:
            description = f"chama {name}"
        self.calls.append({"nome": name, "linha": node.lineno, "descrição": description})

    def _detect_attention(self) -> None:
        low = self.text.lower()
        for pattern, message in (("subprocess", "foi detectado uso de subprocess"), ("os.system", "foi detectado uso de os.system"), ("eval(", "foi detectada avaliação dinâmica com eval"), ("exec(", "foi detectada execução dinâmica com exec"), ("os.environ", "foi detectado acesso a variável de ambiente"), ("socket", "foi detectada possível comunicação por socket")):
            if pattern in low and message not in self.attention:
                self.attention.append(message)
        if "discord" in low:
            self.effects.append("os imports e chamadas são compatíveis com um bot ou integração Discord")
        if "database" in low or any(x in low for x in ("sqlite", "sqlalchemy", "psycopg", "mysql")):
            self.effects.append("o código parece interagir com banco de dados")
        if SECRET_RE.search(self.text) or re.search(r"(?i)(token|api[_-]?key|password|secret)\s*=\s*['\"]", self.text):
            self.attention.append("foi detectado um possível segredo hardcoded; o valor foi mascarado")
        for url in re.findall(r"https?://[^\s'\"]+", self.text):
            self.attention.append(f"foi detectada uma URL externa: {url[:80]}")

    def report(self) -> str:
        if self.error:
            detalhe = self.error
            prefixo = "O arquivo não existe" if "arquivo não encontrado" in detalhe else "Não foi possível analisar o arquivo"
            return f"{prefixo}.\n\nErro: {detalhe}\n\nDica: verifique o caminho e tente novamente."
        if self.language not in {"Python", "Python stub"}:
            return self._report_non_python()
        functions = self.functions
        classes = self.classes
        calls = self.calls
        purpose: list[str] = []
        if self.docstring:
            purpose.append(f"a documentação declara: {self.docstring.splitlines()[0]}")
        if functions:
            purpose.append(f"define {len(functions)} função(ões) para executar operações ou transformar dados")
        if classes:
            purpose.append(f"define {len(classes)} classe(s) para organizar estado e comportamento")
        if self.imports:
            purpose.append(f"depende de {len(self.imports)} módulo(s) ou símbolo(s) importado(s)")
        if not purpose:
            purpose.append("executa ou declara operações no nível do módulo; o propósito completo depende do contexto de uso")
        lines = self._header()
        lines += ["O QUE ESTE ARQUIVO PARECE FAZER"]
        lines += [f"  • {x}." for x in purpose]
        lines += ["", "DEPENDÊNCIAS", "DEPENDÊNCIAS IMPORTADAS"]
        if self.imports:
            lines += [f"  • {x}" for x in self.imports]
        else:
            lines.append("  • Nenhuma detectada")
        lines += ["", "ENTRADAS"] + ([f"  • {x}" for x in dict.fromkeys(self.inputs)] or ["  • Nenhuma detectada"])
        lines += ["", "SAÍDAS"] + ([f"  • {x}" for x in dict.fromkeys(self.outputs)] or ["  • Nenhuma detectada"])
        lines += ["", "EFEITOS OBSERVÁVEIS"] + ([f"  • {x}" for x in dict.fromkeys(self.effects)] or ["  • Nenhum efeito específico detectado"])
        lines += ["", "COMPONENTES", f"  • {len(functions)} função(ões)", f"  • {len(classes)} classe(s)", f"  • {len(self.imports)} import(s)", f"  • {len(calls)} chamada(s)"]
        lines += ["", "FLUXO PROVÁVEL", "FLUXO E SINAIS OBSERVADOS"] + ([f"  {i}. {x}" for i, x in enumerate(dict.fromkeys(self.flow + [c['descrição'] for c in calls[:10]]), 1)] or ["  • Não foi possível reconstruir o fluxo com segurança"])
        lines += ["", "FUNÇÕES", "FUNÇÕES E MÉTODOS"] + ([f"  • {f['nome']} — {len(f['argumentos'])} argumento(s), {'assíncrona' if f['async'] else 'síncrona'}; retorna {', '.join(f['retornos']) if f['retornos'] else 'sem retorno explícito'}" for f in functions] or ["  • Nenhuma detectada"])
        lines += ["", "CLASSES"] + ([f"  • {c['nome']} — métodos: {', '.join(c['métodos']) or 'nenhum'}; bases: {', '.join(c['bases']) or 'nenhuma'}" for c in classes] or ["  • Nenhuma detectada"])
        lines += ["", "CHAMADAS IMPORTANTES"] + ([f"  • Linha {c['linha']}: {c['descrição']} ({c['nome']})" for c in calls[:20]] or ["  • Nenhuma detectada"])
        lines += ["", "SINAIS DE ATENÇÃO"] + ([f"  • {x}" for x in dict.fromkeys(self.attention)] or ["  • Nenhum sinal específico detectado"])
        if any("segredo" in x.lower() for x in self.attention):
            lines.append("  • valores não são exibidos; informações sensíveis são mascaradas no relatório.")
        lines += ["", "LIMITAÇÕES", "  • A explicação é uma inferência estática baseada no AST. O PyInspect não executa o arquivo; o arquivo não é executado durante a análise. Comportamento dependente de dados externos, reflexão, configuração, plugins ou caminhos dinâmicos pode não ser confirmado."]
        return "\n".join(lines)

    def _header(self) -> list[str]:
        return [            "╭────────────────────────────────────────────╮", "│       PyInspect — VERIFICAÇÃO DE ARQUIVO   │", "│  Explicação baseada em análise estática AST  │", "╰────────────────────────────────────────────╯", "", f"Arquivo: {self.path}", f"Linguagem: {self.language}", f"Linhas: {len(self.text.splitlines())}", ""]

    def _report_non_python(self) -> str:
        lines = self._header()
        lines += ["O QUE ESTE ARQUIVO PARECE FAZER"]
        if self.path.suffix.lower() == ".toml":
            lines.append("  • Define metadados ou configuração no formato TOML.")
        elif self.path.suffix.lower() == ".json":
            lines.append("  • Define dados estruturados no formato JSON.")
        elif self.path.suffix.lower() in {".yaml", ".yml"}:
            lines.append("  • Define configuração ou dados estruturados no formato YAML.")
        else:
            lines.append(f"  • Contém código ou estrutura no formato {self.language}; a interpretação usa heurísticas textuais.")
        lines += ["", "ESTRUTURA"] + ([f"  • Campo ou chave: {x}" for x in self.assignments[:30]] or ["  • Não foi possível identificar campos estruturados"])
        lines += ["", "SINAIS DE ATENÇÃO"] + ([f"  • {x}" for x in self.attention] or ["  • Nenhum sinal específico detectado"])
        lines += ["", "LIMITAÇÕES", "  • Não há analisador semântico completo para esta linguagem/formato nesta versão; a explicação é baseada na extensão, parser disponível e padrões textuais."]
        return "\n".join(lines)


def verify_file(path: str | Path) -> str:
    return FileVerification(path).parse().report()


def verify_project(path: str | Path) -> str:
    root = Path(path)
    if not root.is_dir():
        return f"Não foi possível analisar o projeto.\n\nErro: diretório não encontrado: {root}\n\nDica: informe um diretório ou use verify com um arquivo existente."
    files = [p for p in root.rglob("*") if p.is_file() and not any(part in IGNORED or part.startswith("dist_") or part.startswith(".dist_") for part in p.relative_to(root).parts)]
    by_language: dict[str, int] = {}
    reports: list[FileVerification] = []
    for path in files:
        lang = language_for(path)
        by_language[lang] = by_language.get(lang, 0) + 1
        if lang in {"Python", "Python stub"}:
            reports.append(FileVerification(path).parse())
    python_files = [r for r in reports if not r.error]
    graph_edges = []
    cycles = []
    connected: dict[str, int] = {}
    if python_files:
        try:
            from .project import Project
            project = Project(root)
            result = project.scan(use_cache=False)
            graph_edges = list(result.edges)
            cycles = [issue for issue in result.issues if issue.kind == "circular_import"]
            for edge in graph_edges:
                connected[edge.source] = connected.get(edge.source, 0) + 1
                connected[edge.target] = connected.get(edge.target, 0) + 1
        except Exception:
            graph_edges = []
    functions = sum(len(r.functions) for r in python_files)
    classes = sum(len(r.classes) for r in python_files)
    imports = sum(len(r.imports) for r in python_files)
    attention = [a for r in python_files for a in r.attention]
    effects = [e for r in python_files for e in r.effects]
    likely = []
    joined = " ".join(" ".join(r.imports) + " " + " ".join(effects) for r in python_files).lower()
    if "discord" in joined:
        likely.append("o projeto parece ser um bot ou integração Discord")
    if any(x in joined for x in ("sql", "sqlite", "sqlalchemy", "database")):
        likely.append("o projeto parece interagir com banco de dados")
    if not likely:
        likely.append("o propósito geral depende da composição dos módulos; foram reunidas evidências estáticas dos arquivos Python")
    lines = ["╭────────────────────────────────────────────╮", "│       PyInspect — VERIFICAÇÃO DE PROJETO    │", "╰────────────────────────────────────────────╯", "", f"Projeto: {root}", "", "VISÃO GERAL DO PROJETO", f"  • Arquivos: {len(files)}", f"  • Arquivos Python: {by_language.get('Python', 0)}", f"  • Módulos Python: {len(python_files)}", f"  • Classes: {classes}", f"  • Funções: {functions}", f"  • Imports: {imports}", "", "O QUE O PROJETO PARECE FAZER"]
    lines += [f"  • {x}." for x in likely]
    lines += ["", "LINGUAGENS E FORMATOS"] + [f"  • {k}: {v} arquivo(s)" for k, v in sorted(by_language.items())]
    lines += ["", "COMPONENTES PRINCIPAIS"] + [f"  • {x}" for x in sorted(set(effects))[:15]]
    lines += ["", "RELAÇÕES ENTRE MÓDULOS", f"  • Módulos: {len(python_files)}", f"  • Relações detectadas: {len(graph_edges)}", f"  • Ciclos possíveis: {len(cycles)}"]
    if connected:
        lines += ["  • Módulos mais conectados: " + ", ".join(f"{name} ({count})" for name, count in sorted(connected.items(), key=lambda item: item[1], reverse=True)[:5])]
    if cycles:
        lines += [f"  • {issue.message}" for issue in cycles[:10]]
    lines += ["", "SINAIS DE ATENÇÃO"] + ([f"  • {x}" for x in dict.fromkeys(attention)] or ["  • Nenhum sinal específico detectado"])
    lines += ["", "LIMITAÇÕES", "  • A visão do projeto é estática e usa principalmente os módulos Python analisados; não executa nenhum arquivo e não confirma fluxos dependentes de configuração ou serviços externos."]
    return "\n".join(lines)
