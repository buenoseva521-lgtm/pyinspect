import json
from pathlib import Path

from pyinspect.cli import main
from pyinspect.deep_analysis import build_deep_analysis
from pyinspect.project import Project


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_relatorio_profundo_contem_todas_as_secoes():
    project = Project(FIXTURE)
    project.scan()
    relatorio = build_deep_analysis(project)
    assert relatorio["resumo"]["linhas_de_codigo"] > 0
    assert relatorio["resumo"]["funcoes"] >= 3
    assert "media" in relatorio["complexidade"]
    assert relatorio["complexidade"]["funcoes"]
    assert "internos" in relatorio["dependencias"]
    assert "externos" in relatorio["dependencias"]
    assert "funcoes_possivelmente_nao_utilizadas" in relatorio["codigo_possivelmente_nao_utilizado"]
    assert relatorio["estrutura"]["maiores_arquivos"]
    assert "funcoes_muito_grandes" in relatorio["qualidade"]
    assert relatorio["grafo"]["modulos"] >= 2
    assert all(item["modulo"] in {arquivo.module for arquivo in project.files} for item in relatorio["grafo"]["modulos_mais_conectados"])
    assert isinstance(relatorio["entry_points"], list)


def test_analyze_exibe_relatorio_profundo_em_portugues(capsys):
    assert main(["analyze", str(FIXTURE)]) == 0
    saida = capsys.readouterr().out
    for titulo in ["RESUMO GERAL", "COMPLEXIDADE", "DEPENDÊNCIAS", "CÓDIGO POSSIVELMENTE NÃO UTILIZADO", "ESTRUTURA", "QUALIDADE", "GRAFO", "POSSÍVEIS PONTOS DE ENTRADA"]:
        assert titulo in saida
    assert "Linhas de código" in saida
    assert "Complexidade média" in saida
    assert "Módulos mais conectados" in saida


def test_dist_pimcord_e_ignorado_por_padrao(tmp_path):
    (tmp_path / "main.py").write_text("import app\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    dist = tmp_path / "dist_pimcord"
    dist.mkdir()
    (dist / "gerado.py").write_text("def deve_ser_ignorado():\n    return 99\n", encoding="utf-8")
    projeto = Project(tmp_path)
    projeto.scan()
    assert all("dist_pimcord" not in arquivo.path for arquivo in projeto.files)
    assert not any(fn.name == "deve_ser_ignorado" for fn in projeto.functions)


def test_configuracao_ignora_diretorio_customizado(tmp_path):
    (tmp_path / ".pyinspect.json").write_text(json.dumps({"ignore": ["gerado"]}), encoding="utf-8")
    (tmp_path / "main.py").write_text("pass\n", encoding="utf-8")
    custom = tmp_path / "gerado"
    custom.mkdir()
    (custom / "arquivo.py").write_text("def falsa():\n    pass\n", encoding="utf-8")
    assert all("gerado" not in arquivo.path for arquivo in Project(tmp_path).scan().files)
