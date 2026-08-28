from __future__ import annotations

import html
import json
from pathlib import Path

from ..models import AnalysisResult


def to_json(result: AnalysisResult, destination: str | Path | None = None) -> str:
    text = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    if destination:
        Path(destination).write_text(text, encoding="utf-8")
    return text


def to_dot(result: AnalysisResult, destination: str | Path | None = None) -> str:
    lines = ["digraph PyInspect {", "  rankdir=LR;"]
    for edge in result.edges:
        lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{edge.type.value}"];')
    lines.append("}")
    text = "\n".join(lines) + "\n"
    if destination:
        Path(destination).write_text(text, encoding="utf-8")
    return text


def to_html(result: AnalysisResult, destination: str | Path | None = None) -> str:
    title = html.escape(Path(result.root).name)
    data = json.dumps(result.to_dict(), ensure_ascii=False).replace("</", "<\\/")
    page = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PyInspect - {title}</title><style>
:root{{font-family:Inter,system-ui,sans-serif;color:#172033;background:#f6f8fb}}body{{margin:0}}header{{background:#172033;color:white;padding:1.4rem 2rem}}main{{max-width:1300px;margin:1.5rem auto;padding:0 1rem}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.8rem}}.card,section{{background:white;border:1px solid #e1e6ef;border-radius:10px;padding:1rem;box-shadow:0 2px 8px #1720330d}}.card strong{{display:block;font-size:1.8rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}input,select{{padding:.65rem;border:1px solid #ccd4df;border-radius:6px;margin:.2rem}}pre{{background:#101827;color:#d9e2f0;padding:1rem;border-radius:7px;overflow:auto;max-height:480px}}li{{margin:.35rem 0}}.pill{{display:inline-block;padding:.15rem .4rem;border-radius:5px;background:#e7eefb;font-size:.8rem;margin-left:.3rem}}
</style></head><body><header><h1>PyInspect</h1><p>Entenda seu código Python sem ler cada linha.</p><small>{html.escape(result.root)}</small></header><main><div class="cards"><div class="card">Arquivos<strong>{len(result.files)}</strong></div><div class="card">Classes<strong>{len(result.classes)}</strong></div><div class="card">Funções<strong>{len(result.functions)}</strong></div><div class="card">Problemas<strong>{len(result.issues)}</strong></div></div><div class="grid"><section><h2>Explorador do projeto</h2><input id="search" placeholder="Pesquisar arquivos, funções ou classes"><ul id="explorer"></ul></section><section><h2>Grafo de relações</h2><select id="relation"><option value="ALL">Todas as relações</option><option>IMPORTS</option><option>CALLS</option><option>INHERITS</option><option>DEFINES</option></select><pre id="graph"></pre></section></div><section style="margin-top:1rem"><h2>Possíveis problemas</h2><ul id="issues"></ul></section><section style="margin-top:1rem"><h2>Resultado estruturado</h2><details><summary>Mostrar JSON</summary><pre id="json"></pre></details></section></main><script>
const result={data};const explorer=document.querySelector('#explorer'),issues=document.querySelector('#issues'),graph=document.querySelector('#graph'),search=document.querySelector('#search'),relation=document.querySelector('#relation');
function renderExplorer(){{const q=search.value.toLowerCase();const items=[...result.files.map(x=>x.path),...result.functions.map(x=>x.qualified_name),...result.classes.map(x=>x.qualified_name)].filter(x=>x.toLowerCase().includes(q));explorer.innerHTML=items.map(x=>`<li>${{x}}</li>`).join('')||'<li>Nenhum resultado</li>'}}
function renderGraph(){{const kind=relation.value;graph.textContent=result.edges.filter(e=>kind==='ALL'||e.type===kind).map(e=>`${{e.source}} --[${{e.type}}]--> ${{e.target}}`).join('\\n')||'Nenhuma relação'}}
issues.innerHTML=result.issues.map(i=>`<li>${{i.message}} <span class="pill">${{i.kind}}</span></li>`).join('')||'<li>Nenhum possível problema detectado</li>';document.querySelector('#json').textContent=JSON.stringify(result,null,2);search.oninput=renderExplorer;relation.onchange=renderGraph;renderExplorer();renderGraph();</script></body></html>'''
    if destination:
        Path(destination).write_text(page, encoding="utf-8")
    return page
