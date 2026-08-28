from pathlib import Path

from pyinspect.cli import main
from pyinspect.verify import verify_file


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project" / "main.py"


def test_verify_explicita_o_que_o_arquivo_faz():
    texto = verify_file(FIXTURE)
    assert "VERIFICAÇÃO DE ARQUIVO" in texto
    assert "O QUE ESTE ARQUIVO PARECE FAZER" in texto
    assert "DEPENDÊNCIAS IMPORTADAS" in texto
    assert "FUNÇÕES E MÉTODOS" in texto
    assert "FLUXO E SINAIS OBSERVADOS" in texto
    assert "LIMITAÇÕES" in texto
    assert "service" in texto
    assert "main" in texto


def test_verify_funciona_pela_cli(capsys):
    assert main(["verify", str(FIXTURE)]) == 0
    saida = capsys.readouterr().out
    assert "Explicação baseada em análise estática AST" in saida
    assert "não executa o arquivo" in saida


def test_verify_reconstroi_comportamento_de_arquivo_generico(tmp_path):
    arquivo = tmp_path / "processador.py"
    arquivo.write_text("""import json\n\ndef processar(entrada, limite=3):\n    dados = json.loads(entrada)\n    if len(dados) > limite:\n        return dados[:limite]\n    return dados\n""", encoding="utf-8")
    texto = verify_file(arquivo)
    assert "depende de" in texto
    assert "define 1 função(ões)" in texto
    assert "avalia uma condição if" in texto
    assert "processar" in texto
    assert "retorna" in texto


def test_verify_arquivo_inexistente(capsys, tmp_path):
    caminho = tmp_path / "ausente.py"
    assert main(["verify", str(caminho)]) == 2
    saida = capsys.readouterr().out
    assert "O arquivo não existe" in saida
