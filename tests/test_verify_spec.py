from pathlib import Path

from pyinspect.verify import verify_file, verify_project


def test_print_e_explicado_sem_executar(tmp_path):
    path = tmp_path / "hello.py"
    path.write_text('print("Hello World")\n', encoding="utf-8")
    report = verify_file(path)
    assert 'exibe \'Hello World\' no terminal' in report
    assert "escreve texto na saída padrão" in report
    assert "1 chamada(s)" in report


def test_toml_nao_e_tratado_como_python(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "teste"\nversion = "1.0.0"\n', encoding="utf-8")
    report = verify_file(path)
    assert "Linguagem: TOML" in report
    assert "metadados ou configuração no formato TOML" in report
    assert "erro de sintaxe Python" not in report


def test_json_yaml_e_linguagem_generica(tmp_path):
    json_path = tmp_path / "config.json"
    json_path.write_text('{"nome": "teste"}', encoding="utf-8")
    yaml_path = tmp_path / "config.yml"
    yaml_path.write_text("nome: teste\nporta: 8080\n", encoding="utf-8")
    assert "formato JSON" in verify_file(json_path)
    assert "formato YAML" in verify_file(yaml_path)


def test_riscos_e_segredos_sao_detectados_sem_expor_valor(tmp_path):
    path = tmp_path / "perigoso.py"
    path.write_text('import os\nimport subprocess\nTOKEN = "abcd123456789"\nos.system("echo oi")\n', encoding="utf-8")
    report = verify_file(path)
    assert "subprocess" in report
    assert "os.system" in report
    assert "possível segredo hardcoded" in report
    assert "abcd123456789" not in report
    assert "********" in report or "valores não são exibidos" in report


def test_verify_projeto_ignora_build_e_resume_python(tmp_path):
    (tmp_path / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    dist = tmp_path / "dist_pimcord"
    dist.mkdir()
    (dist / "gerado.py").write_text("print('não deve entrar')\n", encoding="utf-8")
    report = verify_project(tmp_path)
    assert "main.py" not in report or "Arquivos Python: 1" in report
    assert "Arquivos Python: 1" in report
    assert "gerado.py" not in report
