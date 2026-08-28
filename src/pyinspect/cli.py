from __future__ import annotations

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .deep_analysis import build_deep_analysis
from .exporters import to_dot, to_html, to_json
from .project import Project
from .verify import verify_file, verify_project


class PortugueseArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        text = super().format_help()
        replacements = {
            "usage:": "uso:",
            "positional arguments:": "argumentos posicionais:",
            "options:": "opções:",
            "show this help message and exit": "mostra esta mensagem de ajuda e encerra",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text


def summary(project: Project) -> str:
    r = project.result
    async_count = sum(f.is_async for f in r.functions)
    lines = [
        "╭────────────────────────────────────╮",
        "│             PyInspect              │",
        "│     Entenda seu código Python      │",
        "╰────────────────────────────────────╯",
        "",
        f"Projeto: {Path(r.root).name}",
        "",
        f"Arquivos              {len(r.files)}",
        f"Classes               {len(r.classes)}",
        f"Funções               {len(r.functions)}",
        f"Funções assíncronas   {async_count}",
        f"Imports               {sum(len(f.imports) for f in r.files)}",
        f"Pacotes externos      {len(r.external_imports)}",
        "",
        "Possíveis problemas",
    ]
    lines += [f"⚠ {i.message} [{i.subject}]" for i in r.issues[:20]] or ["Nenhum detectado"]
    lines += ["", "Pontos de entrada"]
    entries = [f.path for f in r.files if Path(f.path).name in {"main.py", "cli.py", "app.py", "__main__.py"}]
    lines += [f"• {x}" for x in entries] or ["• A análise estática não conseguiu determinar os pontos de entrada"]
    return "\n".join(lines)


def deep_summary(project: Project) -> str:
    a = build_deep_analysis(project)
    r = a["resumo"]
    c = a["complexidade"]
    d = a["dependencias"]
    u = a["codigo_possivelmente_nao_utilizado"]
    s = a["estrutura"]
    q = a["qualidade"]
    g = a["grafo"]
    lines = [
        "╭──────────────────────────────────────────────╮",
        "│          PyInspect — Análise profunda          │",
        "│   Entenda a arquitetura sem ler cada linha   │",
        "╰──────────────────────────────────────────────╯",
        "",
        "RESUMO GERAL",
        f"Arquivos: {r['arquivos']} | Linhas de código: {r['linhas_de_codigo']}",
        f"Classes: {r['classes']} | Funções: {r['funcoes']} | Funções assíncronas: {r['funcoes_async']}",
        f"Imports: {r['imports']} | Pacotes externos: {r['pacotes_externos']}",
        "",
        "COMPLEXIDADE",
        f"Complexidade média: {c['media']}",
        f"Funções com complexidade alta: {len(c['altas'])}",
    ]
    for item in c["funcoes"][:10]:
        lines.append(f"  • {item['nome']} — {item['complexidade']} ({item['status']}) [{item['arquivo']}]")
    lines += ["", "DEPENDÊNCIAS", f"Módulos importados: {len(d['modulos_mais_importados'])}", f"Imports internos: {len(d['internos'])}", f"Imports externos: {len(d['externos'])}", f"Possíveis ciclos: {len(d['ciclos'])}"]
    for item in d["modulos_mais_importados"][:10]:
        lines.append(f"  • {item['modulo']}: {item['quantidade']} importações")
    lines += ["", "CÓDIGO POSSIVELMENTE NÃO UTILIZADO", f"Funções: {len(u['funcoes_possivelmente_nao_utilizadas'])}", f"Classes: {len(u['classes_possivelmente_nao_utilizadas'])}", f"Imports: {len(u['imports_possivelmente_nao_utilizados'])}", f"Arquivos: {len(u['arquivos_possivelmente_nao_utilizados'])}", f"  Observação: {u['observacao']}"]
    lines += ["", "ESTRUTURA", "Árvore resumida:"] + [f"  └── {path}" for path in s["arvore"][:30]]
    lines += ["Maiores arquivos:"] + [f"  • {x['arquivo']}: {x['linhas']} linhas" for x in s["maiores_arquivos"][:5]]
    lines += ["Módulos com mais classes:"] + [f"  • {x['arquivo']}: {x['classes']} classes" for x in s["modulos_com_mais_classes"][:5]]
    lines += ["Módulos com mais funções:"] + [f"  • {x['arquivo']}: {x['funcoes']} funções" for x in s["modulos_com_mais_funcoes"][:5]]
    lines += ["", "QUALIDADE", f"Funções muito grandes: {len(q['funcoes_muito_grandes'])}", f"Classes muito grandes: {len(q['classes_muito_grandes'])}", f"Excesso de argumentos: {len(q['excesso_de_argumentos'])}", f"Duplicações detectadas: {len(q['duplicacao_estatica'])}", f"Imports suspeitos: {len(q['imports_suspeitos'])}", f"  Observação: {q['observacao']}"]
    lines += ["", "GRAFO", f"Módulos: {g['modulos']} | Relações: {g['relacoes']} | Ciclos: {g['ciclos']}", "Módulos mais conectados:"] + [f"  • {x['modulo']}: {x['relacoes']} relações" for x in g["modulos_mais_conectados"]]
    lines += ["", "POSSÍVEIS PONTOS DE ENTRADA"] + ([f"  • {x}" for x in a["entry_points"]] or ["  • A análise estática não conseguiu determinar pontos de entrada"])
    return "\n".join(lines)


def build_parser():
    p = PortugueseArgumentParser(prog="pyinspect", description="Entenda seu código Python sem ler cada linha.")
    sub = p.add_subparsers(dest="command", title="comandos")
    for cmd in ["scan", "analyze", "tree", "graph", "dead-code"]:
        s = sub.add_parser(cmd, help={"scan": "Analisa o projeto", "analyze": "Exibe o resumo da análise", "tree": "Exibe a árvore de arquivos", "graph": "Exibe o grafo de relações", "dead-code": "Exibe possíveis trechos não utilizados"}[cmd])
        s.add_argument("path", help="Caminho do projeto Python")
    for cmd in ["function", "class"]:
        s = sub.add_parser(cmd, help="Pesquisa uma função" if cmd == "function" else "Pesquisa uma classe")
        s.add_argument("path", help="Caminho do projeto Python")
        s.add_argument("name", help="Nome a pesquisar")
    s = sub.add_parser("export", help="Exporta o resultado da análise")
    s.add_argument("path", help="Caminho do projeto Python")
    s.add_argument("--format", choices=["json", "dot", "html"], required=True, help="Formato: json, dot ou html")
    s.add_argument("--output", help="Arquivo de saída")
    s = sub.add_parser("serve", help="Inicia o relatório web local")
    s.add_argument("path", help="Caminho do projeto Python")
    s.add_argument("--port", type=int, default=8000, help="Porta do servidor (padrão: 8000)")
    s = sub.add_parser("verify", help="Explica o que um arquivo ou projeto parece fazer", description="Explica o comportamento provável de um arquivo ou projeto sem executar o código.", epilog="Exemplos:\n  pyinspect verify bot.py\n  pyinspect verify ./meu_projeto\n  pyinspect verify pyproject.toml\n\nPython usa análise AST; outros formatos usam parser estruturado ou heurísticas. O código analisado nunca é executado.")
    s.add_argument("path", help="Caminho de um arquivo ou diretório")
    return p


def main(argv=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    commands = {"scan", "analyze", "tree", "graph", "dead-code", "function", "class", "export", "serve", "verify"}
    if raw and raw[0] not in commands and not raw[0].startswith("-"):
        raw.insert(0, "analyze")
    args = build_parser().parse_args(raw)
    command = args.command
    if command == "verify":
        target = Path(args.path)
        if target.is_dir():
            print(verify_project(target))
            return 0
        print(verify_file(target))
        return 0 if target.is_file() else 2
    if not command:
        build_parser().print_help()
        return 0
    path = args.path
    try:
        project = Project(path)
        project.scan()
    except FileNotFoundError as exc:
        print(f"Erro: o diretório do projeto não existe: {exc}", file=sys.stderr)
        return 2
    if command == "scan":
        print(summary(project))
    elif command == "analyze":
        print(deep_summary(project))
    elif command == "tree":
        for f in project.files:
            print(f.path)
    elif command == "graph":
        for e in project.graph:
            print(f"{e.source} --{e.type.value}--> {e.target}")
    elif command == "dead-code":
        for i in project.result.issues:
            if "unused" in i.kind:
                print(f"{i.kind}: {i.subject} — {i.message}")
    elif command == "function":
        print(json.dumps([f.__dict__ for f in project.find_function(args.name)], indent=2, ensure_ascii=False, default=lambda x: x.__dict__))
    elif command == "class":
        print(json.dumps([c.__dict__ for c in project.find_class(args.name)], indent=2, ensure_ascii=False))
    elif command == "export":
        fn = {"json": to_json, "dot": to_dot, "html": to_html}[args.format]
        output = args.output or f"pyinspect-report.{args.format}"
        fn(project.result, output)
        print(f"Exportado para {output}")
    elif command == "serve":
        report = Path(project.root) / ".pyinspect-report.html"
        to_html(project.result, report)
        print(f"Servidor iniciado para {report} em http://127.0.0.1:{args.port}", flush=True)
        import os
        os.chdir(project.root)
        ThreadingHTTPServer(("127.0.0.1", args.port), SimpleHTTPRequestHandler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
