# PyInspect

> Analise projetos Python e entenda sua estrutura, componentes e possíveis sinais de atenção sem precisar ler cada linha de código.

**PyInspect** é uma ferramenta open source de análise estática para projetos Python. Ela percorre o código sem executá-lo e produz uma visão estruturada de módulos, funções, classes, imports, chamadas, heranças, relações entre arquivos, ciclos de importação, complexidade e possíveis pontos de atenção.

O nome do pacote publicado no PyPI é **`pyinspect-code`**; o nome deste projeto e do repositório no GitHub é **PyInspect**.

## Por que usar

Projetos Python crescem rapidamente e nem sempre há tempo para ler cada arquivo em detalhe. O PyInspect ajuda a formar uma primeira compreensão do sistema, localizar componentes importantes e levantar hipóteses para investigação, mantendo a análise offline e sem executar o código analisado por padrão.

## Principais funcionalidades

- Varredura de projetos e descoberta de arquivos Python e stub (`.py` e `.pyi`).
- Extração de módulos, funções, classes, métodos, imports, chamadas e heranças por meio de AST.
- Grafo de relações entre módulos, incluindo candidatos a ciclos de importação.
- Indicadores heurísticos de complexidade e possíveis funções ou classes não utilizadas.
- Comando `verify` para explicar o comportamento provável de um arquivo ou projeto sem executá-lo.
- Exportação dos resultados para JSON, DOT e HTML.
- Relatório HTML local servido pelo próprio comando `serve`.
- Configuração opcional de diretórios ignorados em `.pyinspect.json`.
- Interface de linha de comando em português do Brasil, preservando nomes técnicos de comandos e opções em inglês.

## Instalação

A instalação recomendada para usuários é feita pelo PyPI:

```bash
pip install pyinspect-code
```

A versão recomendada atualmente é **0.2.1**. A versão 0.2.0 foi considerada quebrada e não deve ser tratada como versão recomendada.

## Uso rápido

Analise um projeto com o comando principal de verificação:

```bash
pyinspect verify /caminho/do/projeto
```

Outros comandos disponíveis incluem:

```bash
pyinspect /caminho/do/projeto             # equivale a analyze
pyinspect scan /caminho/do/projeto
pyinspect analyze /caminho/do/projeto
pyinspect tree /caminho/do/projeto
pyinspect graph /caminho/do/projeto
pyinspect dead-code /caminho/do/projeto
pyinspect export /caminho/do/projeto --format json --output report.json
pyinspect export /caminho/do/projeto --format dot --output graph.dot
pyinspect export /caminho/do/projeto --format html --output report.html
pyinspect serve /caminho/do/projeto
```

A pesquisa de entidades pode ser feita por nome:

```bash
pyinspect function /caminho/do/projeto process_payment
pyinspect class /caminho/do/projeto PaymentService
```

### Exemplo de saída

A saída varia conforme o projeto analisado. Um resumo típico contém seções como estas:

```text
PYINSPECT — RESUMO DA ANÁLISE
Arquivos: 8 | Linhas: 412 | Funções: 23 | Classes: 6
Imports internos: 14 | Imports externos: 9

POSSÍVEIS PONTOS DE ATENÇÃO
- Função possivelmente não utilizada: package.helpers.unused_helper
- Complexidade elevada: package.service.process_payment

GRAFO
Módulos: 8 | Relações: 17 | Ciclos: 0
```

Os nomes e quantidades do exemplo são ilustrativos; o programa calcula os valores a partir do projeto fornecido.

## O que é analisado

Arquivos Python e Python stub são analisados com a árvore sintática abstrata (AST). O PyInspect identifica estrutura de módulos, definições, imports, chamadas, heranças, relações internas, complexidade aproximada, sinais de código possivelmente não utilizado e alguns pontos de entrada. O comando `verify` também resume propósito provável, fluxo, entradas, saídas, efeitos observáveis, chamadas importantes e limitações.

Arquivos estruturados como `.toml`, `.json`, `.yaml` e `.yml` recebem análise apropriada ao formato. Outros formatos de código podem receber análise textual ou estrutural quando não há um parser semântico específico. Possíveis tokens, senhas e chaves são tratados como sinais e mascarados, sem exibição integral.

## Configuração

Opcionalmente, crie `.pyinspect.json` na raiz do projeto analisado para ignorar diretórios adicionais:

```json
{"ignore": ["generated", "vendor"]}
```

Diretórios de build e distribuição, incluindo variantes `dist_*`, são ignorados por padrão.

## Limitações

A análise é estática e deliberadamente conservadora. Imports dinâmicos, reflexão, `getattr`, decorators, plugins e convenções específicas de frameworks podem impedir que o uso real de uma função ou classe seja determinado. Complexidade, código não utilizado, pontos de entrada e ciclos são sinais heurísticos, não provas definitivas. O relatório não substitui testes, revisão de código, análise de segurança nem a execução controlada da aplicação.

## Status atual

A versão **0.2.1** está preparada para uso como ferramenta de análise offline, biblioteca Python e CLI. O núcleo atual cobre AST, descoberta de projeto, grafo, exportação, análise aprofundada, verificação explicativa e relatório web local.

## Roadmap

As próximas evoluções possíveis incluem tracing opcional em runtime, comparação entre versões, integração com Git, sistema de plugins e integrações opcionais com ferramentas externas. Essas ideias ainda não fazem parte da funcionalidade garantida da versão 0.2.1.

## Desenvolvimento

Clone o repositório, instale-o em modo editável e execute os testes:

```bash
git clone https://github.com/buenoseva521-lgtm/pyinspect.git
cd pyinspect
python -m pip install -e .
python -m unittest discover -s tests -v
```

Contribuições são bem-vindas. Para mudanças maiores, abra primeiro uma issue descrevendo o problema ou a proposta. Pull requests devem incluir testes quando aplicável, manter a compatibilidade da CLI e explicar claramente qualquer alteração de comportamento.

## Como reportar bugs

Abra uma [issue no GitHub](https://github.com/buenoseva521-lgtm/pyinspect/issues) com a versão do PyInspect, versão do Python, sistema operacional, comando executado, saída obtida e um exemplo mínimo reproduzível. Remova tokens, senhas, dados proprietários e outros segredos antes de compartilhar logs ou projetos.

## Links

- [Código-fonte e issues no GitHub](https://github.com/buenoseva521-lgtm/pyinspect)
- [Pacote `pyinspect-code` no PyPI](https://pypi.org/project/pyinspect-code/)

## Licença

Distribuído sob a [licença MIT](LICENSE).
