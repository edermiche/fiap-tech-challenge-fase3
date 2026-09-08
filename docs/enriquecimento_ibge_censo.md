# Gold com IBGE, Censo Escolar e AEEB 2025

Execução local: **2026-09-08**. Origem do lake anterior: **2026-09-07**.
A tabela de consumo evoluída é **`gold.base_modelagem_aluno_enriquecida`**.
A tabela inicial `base_modelagem_aluno` permanece como referência reproduzível.

## Fontes e integração

| Avaliação | População IBGE | Censo Escolar | Histórico educacional / Bolsa Família |
|---|---|---|---|
| 2023 | Estimativa 2021 | 2022 | Indisponível na base local anterior |
| 2024 | Censo Demográfico 2022 | 2023 | 2023 |
| 2025 | Estimativa 2024 | 2024 | 2024 |

População é ligada pelo código IBGE de sete dígitos. Censo é agregado por
município e dependência administrativa, incluindo somente escolas em atividade
com matrículas nos anos iniciais do Ensino Fundamental. Não há ligação entre
ID escolar da AEEB e código INEP do Censo: o dicionário da AEEB 2025 define
`ID_ESCOLA` como máscara fictícia.

Arquivos originais ficam na Bronze, com URL, SHA-256, tamanho, data de obtenção
e cabeçalhos HTTP. Dados normalizados/agregados ficam na Silver. A Gold resulta
das junções validadas como muitos-para-um; a Fase 3 lê somente a Gold.

Os downloads complementares são diretos das fontes oficiais. A extração
BigQuery das fontes anteriores continua disponível. O servidor de arquivos
do Inep respondeu em HTTP e encerrou conexões HTTPS neste ambiente; essa
origem está explícita no manifesto. O hash registra os bytes baixados, mas
não substitui assinatura/autenticação do conteúdo pelo publicador.

## Novas colunas preditoras

| Coluna | Definição |
|---|---|
| `populacao_municipio_ibge` | População residente municipal; ano/tipo acompanham a medida |
| `escolas_anos_iniciais_censo` | Escolas ativas com matrículas nos anos iniciais |
| `matriculas_anos_iniciais_censo` | Soma de matrículas dessas escolas |
| `vinculos_docentes_anos_iniciais_censo` | Soma de docentes por escola; não é contagem de pessoas únicas |
| `turmas_anos_iniciais_censo` | Soma de turmas dessas escolas |
| `pct_escolas_rurais_censo` | Percentual de escolas selecionadas em localização rural |
| `pct_escolas_internet_censo` | Percentual com internet entre respostas válidas |
| `pct_escolas_agua_potavel_censo` | Percentual com água potável entre respostas válidas |
| `pct_escolas_biblioteca_censo` | Percentual com biblioteca entre respostas válidas |
| `pct_escolas_lab_informatica_censo` | Percentual com laboratório de informática entre respostas válidas |
| `matriculas_por_vinculo_docente_censo` | Matrículas / vínculos docentes; denominador positivo |
| `matriculas_por_turma_censo` | Matrículas / turmas; denominador positivo |

São 12 novos preditores, além dos nove anteriores. A Gold contém **52 colunas
físicas** e `ano` como partição; `execution_date` também vem do caminho.

Colunas adicionais de auditoria: `ano_referencia_ibge`, `tipo_populacao_ibge`,
`ano_referencia_censo`, `tem_populacao_ibge`, `tem_censo_escolar` e quatro
contagens `escolas_resposta_in_*`, que registram denominadores dos indicadores
de infraestrutura. Nenhuma dessas colunas de auditoria entra automaticamente
no modelo.

## Qualidade e cobertura

| Ano | Registros Gold | Elegíveis | UFs | Cobertura IBGE | Cobertura Censo |
|---|---:|---:|---:|---:|---:|
| 2023 | 1.747.439 | 1.502.809 | 23 | 100,0000% | 99,9950% |
| 2024 | 2.120.560 | 1.851.852 | 26 | 100,0000% | 100,0000% |
| 2025 | 2.222.164 | 1.966.095 | 27 | 99,9944% | 99,9938% |

Coberturas são calculadas nas avaliações elegíveis. As razões por docente
e por turma podem ter ausências adicionais quando o denominador é zero.
Contagens incompletas não são apresentadas como totais parciais; percentuais
não tratam resposta ausente como “não”. Símbolos SIDRA de ausência permanecem
nulos, sem inventar população zero.

A fonte AEEB 2025 contém 2.222.792 registros. **628 estão sem município,
escola e rede**: são preservados em `silver.quarentena_alfabetizacao`, fora
da Gold com chave válida. Dos demais, 252.753 são ausentes e 3.316 presentes
sem proficiência válida; não entram no modelo. Não houve rótulos elegíveis
inconsistentes com o corte de 743 na execução materializada.

Roraima passou a estar presente na edição de 2025. Não foi preenchida
artificialmente sua ausência em 2023/2024.

## Limites temporais

Ano de referência anterior não comprova que a versão atual do arquivo estava
publicada antes de determinada avaliação. A obtenção e os hashes são
registrados agora; o manifesto mantém `vintage_historico_comprovado=false`.
O teste 2024 → 2025 é retrospectivo e não autoriza previsão operacional de
metas futuras sem verificar a disponibilidade histórica de todas as fontes.

O Censo Demográfico de 2022 e a estimativa de 2024 têm métodos distintos.
Sua diferença não deve ser usada diretamente como crescimento populacional.
Os novos atributos descrevem contexto municipal/rede, não características
familiares ou infraestrutura da escola individual do aluno.

## Reprodução local

Na raiz da Fase 2, com a Gold inicial e a Silver de 2026-09-07 disponíveis:

```powershell
python -m pip install -r requirements.txt
python -m src.bronze.download_enriquecimento --execution-date 2026-09-08
python -m src.gold.enriquecer_modelagem --execution-date 2026-09-08 --origem-execution-date 2026-09-07
python -m pytest tests/ -q
```

O comando adicional materializa as tabelas complementares Silver e Gold;
o `main.py` original continua reproduzindo as tabelas anteriores. A integração
com execução AWS/Glue não foi implementada neste ciclo local.

Na Fase 3:

```powershell
python main.py temporal --execution-date 2026-09-08 --ano-treino 2024 --ano-teste 2025
```

Manifesto: `data/gold/base_modelagem_aluno_enriquecida/execution_date=2026-09-08/manifesto_enriquecimento.json`.
Dados e quarentena permanecem locais, fora do Git.

## Referências oficiais

- [IBGE: estimativas populacionais](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html).
- [IBGE: Censo Demográfico 2022](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html?t=resultados).
- [SIDRA: tabela 4714](https://sidra.ibge.gov.br/tabela/4714) e [tabela 6579](https://sidra.ibge.gov.br/tabela/6579).
- [Inep: microdados do Censo Escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar).
- [Inep: resultados AEEB 2025](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/avaliacao-da-alfabetizacao/resultados/2025).
- Dicionários de escolas e AEEB incluídos nos ZIP oficiais, consultados para
  conferir códigos de dependência, presença, infraestrutura e definição do alvo.
