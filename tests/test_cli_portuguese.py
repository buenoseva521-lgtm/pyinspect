from pathlib import Path

from pyinspect.cli import main, summary
from pyinspect.exporters import to_html
from pyinspect.project import Project


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_resumo_da_cli_em_portugues(capsys):
    project = Project(FIXTURE)
    project.scan()
    texto = summary(project)
    assert "Projeto:" in texto
    assert "Arquivos" in texto
    assert "Funções" in texto
    assert "Funções assíncronas" in texto
    assert "Pacotes externos" in texto
    assert "Possíveis problemas" in texto
    assert "Pontos de entrada" in texto


def test_ajuda_da_cli_em_portugues(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    saida = capsys.readouterr().out
    assert "Entenda seu código Python sem ler cada linha." in saida
    assert "Analisa o projeto" in saida
    assert "Exibe o grafo de relações" in saida


def test_erro_amigavel_em_portugues(capsys):
    assert main(["scan", "/caminho/que-nao-existe"]) == 2
    erro = capsys.readouterr().err
    assert "Erro: o diretório do projeto não existe" in erro


def test_relatorio_html_em_portugues():
    pagina = to_html(Project(FIXTURE).scan())
    assert 'lang="pt-BR"' in pagina
    assert "Explorador do projeto" in pagina
    assert "Possíveis problemas" in pagina
    assert "Todas as relações" in pagina
