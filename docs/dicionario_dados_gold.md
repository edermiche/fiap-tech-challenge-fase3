# Dicionário de Dados - Camada Gold

**Adição de 08/09/2026:** `base_modelagem_aluno_enriquecida`, com 52 colunas
físicas, partição anual e 21 preditores explícitos. O
[dicionário dos novos atributos](enriquecimento_ibge_censo.md) também
documenta referências, denominadores e cobertura de 2023–2025.

**Gerado em:** 2026-07-02 18:15:40

**Atualização 07/09/2026:** adicionada `base_modelagem_aluno`, documentada no
[contrato da Fase 3](base_modelagem_aluno.md). O lake local contém 22 tabelas
analíticas e `metricas_qualidade`; `meta_uf_fundeb` é opcional e está ausente.
Os caminhos e volumetrias detalhados abaixo são históricos; para a execução
atual consulte a [auditoria](analise_prontidao_fase3.md).

## Visão geral

A camada Gold contém tabelas analíticas finais derivadas da camada Silver, criadas para responder às perguntas de negócio relacionadas à alfabetização no Brasil.

**Total de tabelas Gold identificadas:** 22 analíticas + 1 de observabilidade
(`metricas_qualidade`).

As antigas `comparacao_meta_resultado_brasil` / `_uf` / `_municipio` foram
consolidadas nas tabelas `evolucao_meta_resultado_*` do mesmo grão, que já
continham todas as colunas delas mais as variações anuais — ver
[ADR-003](adr/ADR-003-governanca-camada-gold.md).

## Notas de cobertura dos dados

As junções foram corrigidas para preservar resultados sem meta. Ainda há
lacunas da fonte; presença de linha territorial não significa resultado
preenchido. A auditoria distingue as duas situações.

| Tabela | O que esperar | Por quê |
|---|---|---|
| `indicador_meta_uf` e derivadas | 27 linhas por ano (2023–2025) | Junção à esquerda; em 2024 há 3 UFs sem meta e 1 sem resultado. |
| `indicador_meta_municipio` e derivadas | 5232 linhas em 2023; 5352 em 2024 | Em 2024, os 120 municípios sem meta são preservados. |
| `evolucao_meta_resultado_municipio` | Variação do resultado disponível onde existem duas safras | 2023 foi preservado; não há meta de 2023 para calcular variação anual da meta em 2024. |
| `meta_uf_bolsa_familia` | Colunas de Bolsa Família nulas em 2025 | A fonte do Bolsa Família cobre 2023–2024. O `left join` preserva a linha da meta 2025 com o enriquecimento vazio, em vez de descartá-la |
| `perfil_aluno_alfabetizacao` | Rede "Privada" com dezenas de alunos em 2024 | A avaliação é censitária na rede pública; a participação privada é residual e não sustenta leitura comparativa |

A diferença de rótulo de rede entre grãos (`Pública` em Brasil/UF, `Municipal`
em município) também vem da fonte e é preservada sem normalização.

## Tabelas identificadas

| Tabela | Arquivo mais recente |
|---|---|
| `gold.desigualdade_territorial_uf` | `../data/gold/desigualdade_territorial_uf/execution_date=2026-07-05/` |
| `gold.distribuicao_desempenho_aluno` | `../data/gold/distribuicao_desempenho_aluno/execution_date=2026-07-05/` |
| `gold.evolucao_alfabetizacao` | `../data/gold/evolucao_alfabetizacao/execution_date=2026-07-02/evolucao_alfabetizacao.parquet` |
| `gold.evolucao_meta_resultado_brasil` | `../data/gold/evolucao_meta_resultado_brasil/execution_date=2026-09-02/` |
| `gold.evolucao_meta_resultado_municipio` | `../data/gold/evolucao_meta_resultado_municipio/execution_date=2026-07-05/` |
| `gold.evolucao_meta_resultado_uf` | `../data/gold/evolucao_meta_resultado_uf/execution_date=2026-07-05/` |
| `gold.indicador_alfabetizacao_municipio` | `../data/gold/indicador_alfabetizacao_municipio/execution_date=2026-07-05/ano=2024/indicador_alfabetizacao_municipio.parquet` |
| `gold.indicador_desempenho_aluno` | `../data/gold/indicador_desempenho_aluno/execution_date=2026-07-05/` |
| `gold.indicador_meta_brasil` | `../data/gold/indicador_meta_brasil/execution_date=2026-07-02/indicador_meta_brasil.parquet` |
| `gold.indicador_meta_municipio` | `../data/gold/indicador_meta_municipio/execution_date=2026-07-02/indicador_meta_municipio.parquet` |
| `gold.indicador_meta_regiao` | `../data/gold/indicador_meta_regiao/execution_date=2026-07-05/` |
| `gold.indicador_meta_uf` | `../data/gold/indicador_meta_uf/execution_date=2026-07-02/indicador_meta_uf.parquet` |
| `gold.indicador_presenca_avaliacao` | `../data/gold/indicador_presenca_avaliacao/execution_date=2026-07-05/` |
| `gold.mapa_calor_territorial` | `../data/gold/mapa_calor_territorial/execution_date=2026-07-05/` |
| `gold.meta_uf_bolsa_familia` | `../data/gold/meta_uf_bolsa_familia/execution_date=2026-07-05/` |
| `gold.metricas_qualidade` | `../data/gold/metricas_qualidade/execution_date=2026-09-02/metricas_qualidade.parquet` |
| `gold.meta_uf_fundeb` | `../data/gold/meta_uf_fundeb/execution_date=2026-07-05/` |
| `gold.perfil_aluno_alfabetizacao` | `../data/gold/perfil_aluno_alfabetizacao/execution_date=2026-07-05/` |
| `gold.ranking_escolas_prioritarias` | `../data/gold/ranking_escolas_prioritarias/execution_date=2026-07-05/` |
| `gold.ranking_municipio_prioritario` | `../data/gold/ranking_municipio_prioritario/execution_date=2026-07-02/ranking_municipio_prioritario.parquet` |
| `gold.ranking_territorial_prioridade` | `../data/gold/ranking_territorial_prioridade/execution_date=2026-07-05/` |
| `gold.ranking_uf_prioritaria` | `../data/gold/ranking_uf_prioritaria/execution_date=2026-07-02/ranking_uf_prioritaria.parquet` |
| `gold.resumo_status_meta` | `../data/gold/resumo_status_meta/execution_date=2026-07-02/resumo_status_meta.parquet` |

---

## gold.evolucao_meta_resultado_brasil

**Descricao:** Serie temporal de resultado observado, meta, distancia da meta e variacao anual no nivel Brasil. Consolida a antiga `comparacao_meta_resultado_brasil` (ADR-003).

**Chave sugerida:** `ano`, `ano_meta`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia do resultado observado. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `rede` | `object` | Rede de ensino. |
| `nivel_agregacao` | `object` | Nivel territorial da analise. |
| `resultado_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista para o ano. |
| `distancia_meta` | `float64` | Diferenca entre resultado observado e meta. |
| `variacao_resultado_ano_anterior` | `float64` | Variacao do resultado observado em relacao ao ano anterior da mesma rede. |
| `variacao_meta_ano_anterior` | `float64` | Variacao da meta em relacao ao ano anterior da mesma rede. |
| `flag_meta_atingida` | `bool` | Indica se a meta foi atingida. |
| `status_meta` | `object` | Classificacao textual do atingimento da meta. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.evolucao_meta_resultado_uf

**Descricao:** Serie temporal de resultado observado, meta, distancia da meta e variacao anual por UF.

**Chave sugerida:** `ano`, `ano_meta`, `sigla_uf`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia do resultado observado. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `rede` | `object` | Rede de ensino. |
| `nivel_agregacao` | `object` | Nivel territorial da analise. |
| `resultado_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista para o ano. |
| `distancia_meta` | `float64` | Diferenca entre resultado observado e meta. |
| `variacao_resultado_ano_anterior` | `float64` | Variacao do resultado observado em relacao ao ano anterior da mesma UF e rede. |
| `variacao_meta_ano_anterior` | `float64` | Variacao da meta em relacao ao ano anterior da mesma UF e rede. |
| `flag_meta_atingida` | `bool` | Indica se a meta foi atingida. |
| `status_meta` | `object` | Classificacao textual do atingimento da meta. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.evolucao_meta_resultado_municipio

**Descricao:** Serie temporal de resultado observado, meta, distancia da meta e variacao anual por municipio.

**Chave sugerida:** `ano`, `ano_meta`, `id_municipio`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia do resultado observado. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `rede` | `object` | Rede de ensino. |
| `nivel_agregacao` | `object` | Nivel territorial da analise. |
| `resultado_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista para o ano. |
| `distancia_meta` | `float64` | Diferenca entre resultado observado e meta. |
| `variacao_resultado_ano_anterior` | `float64` | Variacao do resultado observado em relacao ao ano anterior do mesmo municipio e rede. |
| `variacao_meta_ano_anterior` | `float64` | Variacao da meta em relacao ao ano anterior do mesmo municipio e rede. |
| `flag_meta_atingida` | `bool` | Indica se a meta foi atingida. |
| `status_meta` | `object` | Classificacao textual do atingimento da meta. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.indicador_meta_regiao

**Descricao:** Indicador territorial agregado por regiao brasileira, com resultado medio, meta media e status regional.

**Chave sugerida:** `ano`, `ano_meta`, `regiao_brasil`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `rede` | `object` | Rede de ensino. |
| `resultado_alfabetizacao_medio` | `float64` | Media regional do resultado observado. |
| `meta_alfabetizacao_media` | `float64` | Media regional da meta de alfabetizacao. |
| `distancia_media_meta` | `float64` | Media da distancia entre resultado e meta. |
| `total_ufs` | `int64` | Quantidade de UFs consideradas na regiao. |
| `total_meta_atingida` | `int64` | Quantidade de UFs com meta atingida. |
| `total_abaixo_meta` | `int64` | Quantidade de UFs abaixo da meta. |
| `percentual_meta_atingida` | `float64` | Percentual de UFs com meta atingida. |
| `status_regiao` | `object` | Status consolidado da regiao. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.perfil_aluno_alfabetizacao

**Descricao:** Perfil agregado dos microdados por serie, rede, presenca e status de alfabetizacao.

**Chave sugerida:** `ano`, `serie`, `rede`, `presenca`, `alfabetizado`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `serie` | `object` | Serie escolar. |
| `rede` | `object` | Rede de ensino. |
| `presenca` | `object` | Indicador de presenca do aluno. |
| `alfabetizado` | `object` | Classificacao de alfabetizacao. |
| `total_alunos` | `int64` | Quantidade de alunos no grupo. |
| `media_proficiencia` | `float64` | Media de proficiencia no grupo. |
| `percentual_alunos` | `float64` | Percentual do grupo dentro da serie/rede/ano. |
| `total_presentes` | `int64` | Total de alunos presentes. |
| `total_ausentes` | `int64` | Total de alunos ausentes. |
| `percentual_presentes` | `float64` | Percentual de presentes no grupo. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.indicador_presenca_avaliacao

**Descricao:** Indicadores de presenca e ausencia na avaliacao por municipio, UF, rede e serie.

**Chave sugerida:** `ano`, `id_municipio`, `rede`, `serie`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `rede` | `object` | Rede de ensino. |
| `serie` | `object` | Serie escolar. |
| `total_alunos` | `int64` | Total de alunos avaliados/cadastrados no grupo. |
| `total_presentes` | `int64` | Total de alunos presentes. |
| `total_ausentes` | `int64` | Total de alunos ausentes. |
| `media_proficiencia_presentes` | `float64` | Media de proficiencia dos alunos presentes. |
| `percentual_presenca` | `float64` | Percentual de presenca. |
| `percentual_ausencia` | `float64` | Percentual de ausencia. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.indicador_desempenho_aluno

**Descricao:** Indicadores agregados de desempenho dos alunos por municipio, UF, rede e serie.

**Chave sugerida:** `ano`, `id_municipio`, `rede`, `serie`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `rede` | `object` | Rede de ensino. |
| `serie` | `object` | Serie escolar. |
| `total_alunos` | `int64` | Total de alunos no grupo. |
| `total_presentes` | `int64` | Total de alunos presentes. |
| `total_alfabetizados` | `int64` | Total de alunos alfabetizados. |
| `total_nao_alfabetizados` | `int64` | Total de alunos nao alfabetizados. |
| `media_proficiencia` | `float64` | Media de proficiencia. |
| `mediana_proficiencia` | `float64` | Mediana de proficiencia. |
| `menor_proficiencia` | `float64` | Menor proficiencia observada. |
| `maior_proficiencia` | `float64` | Maior proficiencia observada. |
| `desvio_padrao_proficiencia` | `float64` | Desvio padrao da proficiencia. |
| `percentual_presenca` | `float64` | Percentual de presenca. |
| `percentual_alfabetizado` | `float64` | Percentual de alunos alfabetizados. |
| `percentual_nao_alfabetizado` | `float64` | Percentual de alunos nao alfabetizados. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.distribuicao_desempenho_aluno

**Descricao:** Distribuicao dos alunos por faixa de proficiencia e status de alfabetizacao.

**Chave sugerida:** `ano`, `sigla_uf`, `rede`, `serie`, `faixa_proficiencia`, `alfabetizado`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `rede` | `object` | Rede de ensino. |
| `serie` | `object` | Serie escolar. |
| `faixa_proficiencia` | `object` | Faixa de proficiencia. |
| `alfabetizado` | `object` | Classificacao de alfabetizacao. |
| `total_alunos` | `int64` | Total de alunos na faixa. |
| `media_proficiencia` | `float64` | Media de proficiencia na faixa. |
| `percentual_alunos` | `float64` | Percentual de alunos na faixa dentro do grupo. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.ranking_escolas_prioritarias

**Descricao:** Ranking de escolas prioritarias por percentual de alunos nao alfabetizados.

**Chave sugerida:** `ano`, `id_escola`, `rede`, `serie`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `id_escola` | `object` | Codigo identificador da escola. |
| `rede` | `object` | Rede de ensino. |
| `serie` | `object` | Serie escolar. |
| `total_alunos` | `int64` | Total de alunos da escola no grupo. |
| `total_presentes` | `int64` | Total de alunos presentes. |
| `total_alfabetizados` | `int64` | Total de alunos alfabetizados. |
| `total_nao_alfabetizados` | `int64` | Total de alunos nao alfabetizados. |
| `percentual_nao_alfabetizado` | `float64` | Percentual de alunos nao alfabetizados. |
| `percentual_presenca` | `float64` | Percentual de presenca. |
| `media_proficiencia` | `float64` | Media de proficiencia da escola. |
| `ranking_nacional` | `int64` | Posicao no ranking nacional. |
| `ranking_uf` | `int64` | Posicao no ranking da UF. |
| `ranking_municipio` | `int64` | Posicao no ranking do municipio. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.ranking_territorial_prioridade

**Descricao:** Ranking de municipios abaixo da meta, com posicoes no Brasil, na regiao e dentro da UF.

**Chave sugerida:** `ano`, `ano_meta`, `id_municipio`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `taxa_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista. |
| `distancia_meta` | `float64` | Distancia entre resultado e meta. |
| `ranking_nacional` | `int64` | Posicao no ranking nacional de prioridade. |
| `ranking_regiao` | `int64` | Posicao no ranking regional de prioridade. |
| `ranking_uf` | `int64` | Posicao no ranking da UF. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.desigualdade_territorial_uf

**Descricao:** Medidas de desigualdade dos resultados municipais dentro de cada UF.

**Chave sugerida:** `ano`, `ano_meta`, `sigla_uf`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `resultado_medio_uf` | `float64` | Media dos resultados municipais da UF. |
| `menor_resultado_municipal` | `float64` | Menor resultado municipal da UF. |
| `maior_resultado_municipal` | `float64` | Maior resultado municipal da UF. |
| `amplitude_resultado` | `float64` | Diferenca entre maior e menor resultado municipal. |
| `desvio_padrao_resultado` | `float64` | Dispersao dos resultados municipais. |
| `qtd_municipios` | `int64` | Quantidade de municipios considerados. |
| `qtd_municipios_abaixo_meta` | `int64` | Quantidade de municipios abaixo da meta. |
| `percentual_municipios_abaixo_meta` | `float64` | Percentual de municipios abaixo da meta. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.mapa_calor_territorial

**Descricao:** Base municipal classificada por faixa de risco territorial conforme distancia ate a meta.

**Chave sugerida:** `ano`, `ano_meta`, `id_municipio`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `regiao_brasil` | `object` | Regiao brasileira. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `taxa_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista. |
| `distancia_meta` | `float64` | Distancia entre resultado e meta. |
| `status_meta` | `object` | Status de cumprimento da meta. |
| `classe_risco` | `object` | Faixa de risco territorial. |
| `cor_mapa` | `object` | Cor sugerida para mapa de calor. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.indicador_alfabetizacao_municipio

**Descricao:** Tabela analitica municipal enriquecida para acompanhar alfabetizacao, meta, status, nome do municipio, UF, indicadores do Bolsa Familia e rankings de prioridade.

**Arquivo fisico:** `../data/gold/indicador_alfabetizacao_municipio/execution_date=2026-07-05/ano=2024/indicador_alfabetizacao_municipio.parquet`

**Quantidade de linhas:** 5232

**Quantidade de colunas:** 19

**Chave sugerida:** `ano`, `id_municipio`, `rede`, `ano_meta`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia do resultado observado. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `rede` | `object` | Rede de ensino. |
| `nivel_agregacao` | `object` | Nivel territorial da analise. |
| `taxa_alfabetizacao` | `float64` | Taxa de alfabetizacao observada. |
| `nivel_alfabetizacao` | `Int64` | Nivel de alfabetizacao observado. |
| `percentual_participacao` | `float64` | Percentual de participacao na avaliacao. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista para o ano. |
| `distancia_meta` | `float64` | Diferenca entre taxa observada e meta de alfabetizacao. |
| `flag_meta_atingida` | `bool` | Indica se a meta foi atingida. |
| `status_meta` | `object` | Classificacao textual do atingimento da meta. |
| `total_beneficiarios_bolsa_familia` | `Int64` | Total anual de beneficiarios do Bolsa Familia no municipio. |
| `valor_total_bolsa_familia` | `float64` | Valor anual pago pelo Bolsa Familia no municipio. |
| `ranking_prioridade_uf` | `Int64` | Posicao de prioridade do municipio dentro da UF, quando esta abaixo da meta. |
| `ranking_prioridade_brasil` | `Int64` | Posicao de prioridade do municipio no Brasil, quando esta abaixo da meta. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.meta_uf_fundeb

**Descricao:** Verificacao estadual que cruza meta de alfabetizacao com valores recebidos do FUNDEB.

**Chave sugerida:** `ano`, `ano_meta`, `sigla_uf`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia do resultado observado e do repasse FUNDEB. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `sigla_uf_nome` | `object` | Nome da Unidade Federativa. |
| `rede` | `object` | Rede de ensino. |
| `nivel_agregacao` | `object` | Nivel territorial da analise. |
| `resultado_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista para o ano. |
| `distancia_meta` | `float64` | Diferenca entre resultado observado e meta. |
| `status_meta` | `object` | Classificacao textual do atingimento da meta. |
| `total_fundeb` | `float64` | Valor total do FUNDEB recebido pela UF. |
| `total_estado_df` | `float64` | Parcela do FUNDEB referente ao estado ou Distrito Federal. |
| `total_municipios` | `float64` | Parcela do FUNDEB referente aos municipios da UF. |
| `percentual_brasil` | `float64` | Participacao da UF no total Brasil do FUNDEB. |
| `ranking_fundeb_ano` | `Int64` | Ranking anual da UF por valor total do FUNDEB. |
| `ranking_meta_ano` | `Int64` | Ranking anual da UF por meta de alfabetizacao. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.meta_uf_bolsa_familia

**Descricao:** Verificacao estadual que cruza meta de alfabetizacao com total de beneficiarios e valores pagos pelo Bolsa Familia.

**Chave sugerida:** `ano`, `ano_meta`, `sigla_uf`, `rede`

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia do resultado observado e do Bolsa Familia. |
| `ano_meta` | `Int64` | Ano da meta comparada. |
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `rede` | `object` | Rede de ensino. |
| `nivel_agregacao` | `object` | Nivel territorial da analise. |
| `resultado_alfabetizacao` | `float64` | Resultado observado de alfabetizacao. |
| `meta_alfabetizacao` | `float64` | Meta de alfabetizacao prevista para o ano. |
| `distancia_meta` | `float64` | Diferenca entre resultado observado e meta. |
| `status_meta` | `object` | Classificacao textual do atingimento da meta. |
| `total_beneficiarios_bolsa_familia` | `Int64` | Total anual de beneficiarios do Bolsa Familia na UF. |
| `valor_total_bolsa_familia` | `float64` | Valor anual pago pelo Bolsa Familia na UF. |
| `total_municipios_com_bolsa_familia` | `Int64` | Quantidade de municipios da UF com dados do Bolsa Familia. |
| `ranking_beneficiarios_ano` | `Int64` | Ranking anual da UF por total de beneficiarios. |
| `ranking_meta_ano` | `Int64` | Ranking anual da UF por meta de alfabetizacao. |
| `data_processamento_gold` | `object` | Data de processamento da camada Gold. |

## gold.evolucao_alfabetizacao

**Descrição:** Tabela analítica consolidada para acompanhar a evolução da alfabetização por nível de agregação.

**Arquivo físico:** `../data/gold/evolucao_alfabetizacao/execution_date=2026-07-02/evolucao_alfabetizacao.parquet`

**Quantidade de linhas:** 5

**Quantidade de colunas:** 12

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano de referência do resultado observado. |
| `rede` | `object` | 0 | 0.0% | 2 | `Pública` | Rede de ensino. |
| `nivel_agregacao` | `object` | 0 | 0.0% | 3 | `Brasil` | Nível territorial da análise. |
| `taxa_alfabetizacao_media` | `float64` | 0 | 0.0% | 5 | `59.2` | Média da taxa de alfabetização observada no agrupamento. |
| `meta_alfabetizacao_media` | `float64` | 0 | 0.0% | 5 | `59.9` | Média da meta de alfabetização no agrupamento. |
| `distancia_media_meta` | `float64` | 0 | 0.0% | 5 | `-0.6999999999999957` | Média da distância entre taxa observada e meta de alfabetização. |
| `percentual_participacao_medio` | `float64` | 0 | 0.0% | 5 | `87.37` | Média do percentual de participação no agrupamento. |
| `total_registros` | `int64` | 0 | 0.0% | 3 | `1` | Quantidade de registros considerados no agrupamento. |
| `total_meta_atingida` | `int64` | 0 | 0.0% | 5 | `0` | Quantidade de registros com meta atingida. |
| `total_abaixo_meta` | `int64` | 0 | 0.0% | 5 | `1` | Quantidade de registros abaixo da meta. |
| `percentual_meta_atingida` | `float64` | 0 | 0.0% | 5 | `0.0` | Percentual de registros com meta atingida. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

## gold.indicador_meta_brasil

**Descrição:** Tabela analítica nacional que compara taxa de alfabetização observada com a meta do mesmo ano.

**Arquivo físico:** `../data/gold/indicador_meta_brasil/execution_date=2026-07-02/indicador_meta_brasil.parquet`

**Quantidade de linhas:** 2

**Quantidade de colunas:** 11

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano de referência do resultado observado. |
| `rede` | `object` | 0 | 0.0% | 1 | `Pública` | Rede de ensino. |
| `nivel_agregacao` | `object` | 0 | 0.0% | 1 | `Brasil` | Nível territorial da análise. |
| `taxa_alfabetizacao` | `float64` | 0 | 0.0% | 2 | `59.2` | Taxa de alfabetização observada. |
| `percentual_participacao` | `float64` | 0 | 0.0% | 2 | `87.37` | Percentual de participação na avaliação. |
| `ano_meta` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano da meta comparada. |
| `meta_alfabetizacao` | `float64` | 0 | 0.0% | 2 | `59.9` | Meta de alfabetização prevista para o ano. |
| `distancia_meta` | `float64` | 0 | 0.0% | 2 | `-0.6999999999999957` | Diferença entre taxa observada e meta de alfabetização. |
| `flag_meta_atingida` | `bool` | 0 | 0.0% | 2 | `False` | Indica se a meta foi atingida. |
| `status_meta` | `object` | 0 | 0.0% | 2 | `Abaixo da meta` | Classificação textual do atingimento da meta. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

## gold.indicador_meta_municipio

**Descrição:** Tabela analítica por município que compara taxa de alfabetização observada com a meta do mesmo ano.

**Arquivo físico:** `../data/gold/indicador_meta_municipio/execution_date=2026-07-02/indicador_meta_municipio.parquet`

**Quantidade de linhas:** 5352

**Quantidade de colunas:** 13

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 1 | `2024` | Ano de referência do resultado observado. |
| `id_municipio` | `object` | 0 | 0.0% | 5352 | `1100015` | Código identificador do município. |
| `id_municipio_nome` | `object` | 0 | 0.0% | 5096 | `Alta Floresta D'Oeste` | Nome do município. |
| `rede` | `object` | 0 | 0.0% | 1 | `Municipal` | Rede de ensino. |
| `nivel_agregacao` | `object` | 0 | 0.0% | 1 | `Município` | Nível territorial da análise. |
| `taxa_alfabetizacao` | `float64` | 0 | 0.0% | 3512 | `67.79` | Taxa de alfabetização observada. |
| `percentual_participacao` | `float64` | 0 | 0.0% | 1670 | `89.87` | Percentual de participação na avaliação. |
| `ano_meta` | `Int64` | 0 | 0.0% | 1 | `2024` | Ano da meta comparada. |
| `meta_alfabetizacao` | `float64` | 120 | 2.24% | 2745 | `67.08` | Meta de alfabetização prevista para o ano. |
| `distancia_meta` | `float64` | 120 | 2.24% | 4077 | `0.710000000000008` | Diferença entre taxa observada e meta de alfabetização. |
| `flag_meta_atingida` | `object` | 120 | 2.24% | 2 | `True` | Indica se a meta foi atingida. |
| `status_meta` | `object` | 0 | 0.0% | 3 | `Meta atingida` | Classificação textual do atingimento da meta. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

## gold.indicador_meta_uf

**Descrição:** Tabela analítica por UF que compara taxa de alfabetização observada com a meta do mesmo ano.

**Arquivo físico:** `../data/gold/indicador_meta_uf/execution_date=2026-07-02/indicador_meta_uf.parquet`

**Quantidade de linhas:** 54

**Quantidade de colunas:** 13

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano de referência do resultado observado. |
| `sigla_uf` | `object` | 0 | 0.0% | 27 | `AC` | Sigla da Unidade Federativa. |
| `sigla_uf_nome` | `object` | 4 | 7.41% | 25 | `Acre` | Nome da Unidade Federativa. |
| `rede` | `object` | 0 | 0.0% | 1 | `Pública` | Rede de ensino. |
| `nivel_agregacao` | `object` | 0 | 0.0% | 1 | `UF` | Nível territorial da análise. |
| `taxa_alfabetizacao` | `float64` | 1 | 1.85% | 46 | `51.38` | Taxa de alfabetização observada. |
| `percentual_participacao` | `float64` | 1 | 1.85% | 38 | `80.87` | Percentual de participação na avaliação. |
| `ano_meta` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano da meta comparada. |
| `meta_alfabetizacao` | `float64` | 4 | 7.41% | 43 | `49.7` | Meta de alfabetização prevista para o ano. |
| `distancia_meta` | `float64` | 4 | 7.41% | 40 | `-1.0700000000000003` | Diferença entre taxa observada e meta de alfabetização. |
| `flag_meta_atingida` | `object` | 4 | 7.41% | 2 | `False` | Indica se a meta foi atingida. |
| `status_meta` | `object` | 0 | 0.0% | 3 | `Sem informação` | Classificação textual do atingimento da meta. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

## gold.ranking_municipio_prioritario

**Descrição:** Ranking de municípios priorizados conforme distância em relação à meta de alfabetização.

**Arquivo físico:** `../data/gold/ranking_municipio_prioritario/execution_date=2026-07-02/ranking_municipio_prioritario.parquet`

**Quantidade de linhas:** 2444

**Quantidade de colunas:** 11

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 1 | `2024` | Ano de referência do resultado observado. |
| `posicao_prioridade` | `int64` | 0 | 0.0% | 2444 | `1` | Posição no ranking de priorização. |
| `id_municipio` | `object` | 0 | 0.0% | 2444 | `4320453` | Código identificador do município. |
| `id_municipio_nome` | `object` | 0 | 0.0% | 2379 | `Sério` | Nome do município. |
| `rede` | `object` | 0 | 0.0% | 1 | `Municipal` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | 0 | 0.0% | 1830 | `11.1` | Taxa de alfabetização observada. |
| `meta_alfabetizacao` | `float64` | 0 | 0.0% | 1590 | `80.0` | Meta de alfabetização prevista para o ano. |
| `distancia_meta` | `float64` | 0 | 0.0% | 1938 | `-68.9` | Diferença entre taxa observada e meta de alfabetização. |
| `percentual_participacao` | `float64` | 0 | 0.0% | 1175 | `100.0` | Percentual de participação na avaliação. |
| `status_meta` | `object` | 0 | 0.0% | 1 | `Abaixo da meta` | Classificação textual do atingimento da meta. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

## gold.ranking_uf_prioritaria

**Descrição:** Ranking de UFs priorizadas conforme distância em relação à meta de alfabetização.

**Arquivo físico:** `../data/gold/ranking_uf_prioritaria/execution_date=2026-07-02/ranking_uf_prioritaria.parquet`

**Quantidade de linhas:** 19

**Quantidade de colunas:** 11

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano de referência do resultado observado. |
| `posicao_prioridade` | `int64` | 0 | 0.0% | 13 | `1` | Posição no ranking de priorização. |
| `sigla_uf` | `object` | 0 | 0.0% | 13 | `RS` | Sigla da Unidade Federativa. |
| `sigla_uf_nome` | `object` | 0 | 0.0% | 13 | `Rio Grande do Sul` | Nome da Unidade Federativa. |
| `rede` | `object` | 0 | 0.0% | 1 | `Pública` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | 0 | 0.0% | 19 | `44.67` | Taxa de alfabetização observada. |
| `meta_alfabetizacao` | `float64` | 0 | 0.0% | 18 | `66.2` | Meta de alfabetização prevista para o ano. |
| `distancia_meta` | `float64` | 0 | 0.0% | 18 | `-21.53` | Diferença entre taxa observada e meta de alfabetização. |
| `percentual_participacao` | `float64` | 0 | 0.0% | 17 | `82.86` | Percentual de participação na avaliação. |
| `status_meta` | `object` | 0 | 0.0% | 1 | `Abaixo da meta` | Classificação textual do atingimento da meta. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

## gold.resumo_status_meta

**Descrição:** Tabela consolidada com a quantidade e percentual de registros por status da meta, ano e nível de agregação.

**Arquivo físico:** `../data/gold/resumo_status_meta/execution_date=2026-07-02/resumo_status_meta.parquet`

**Quantidade de linhas:** 11

**Quantidade de colunas:** 8

| Coluna | Tipo | Nulos | % Nulos | Valores distintos | Exemplo | Descrição |
|---|---|---:|---:|---:|---|---|
| `ano` | `Int64` | 0 | 0.0% | 2 | `2024` | Ano de referência do resultado observado. |
| `rede` | `object` | 0 | 0.0% | 2 | `Pública` | Rede de ensino. |
| `nivel_agregacao` | `object` | 0 | 0.0% | 3 | `Brasil` | Nível territorial da análise. |
| `status_meta` | `object` | 0 | 0.0% | 3 | `Abaixo da meta` | Classificação textual do atingimento da meta. |
| `quantidade` | `int64` | 0 | 0.0% | 9 | `1` | Quantidade de registros no agrupamento. |
| `total_registros` | `int64` | 0 | 0.0% | 3 | `1` | Quantidade de registros considerados no agrupamento. |
| `percentual_registros` | `float64` | 0 | 0.0% | 10 | `100.0` | Percentual de registros no agrupamento. |
| `data_processamento_gold` | `object` | 0 | 0.0% | 1 | `2026-07-02` | Data de processamento da camada Gold. |

---

## gold.metricas_qualidade

**Descricao:** Historico das metricas de qualidade do pipeline. Uma linha por execucao, camada, tabela e regra avaliada. Gravada pela Silver (regras de conteudo) e complementada pela Gold (volumetria publicada) na mesma particao de execucao. E a tabela que permite responder se a qualidade piorou desde a safra anterior — ver [ADR-002](adr/ADR-002-gate-de-qualidade.md).

**Particionamento:** `execution_date=<data>/metricas_qualidade.parquet` (sem particao por ano: e um log de execucoes, nao um fato anual).

**Chave sugerida:** `data_execucao`, `camada`, `tabela`, `regra`, `coluna`, `escopo`

| Coluna | Tipo | Descricao |
|---|---|---|
| `data_execucao` | `object` | Data da execucao do pipeline que gerou a metrica (ISO-8601). |
| `camada` | `object` | Camada avaliada: `silver` ou `gold`. |
| `tabela` | `object` | Tabela avaliada. |
| `regra` | `object` | Regra aplicada (ver `src/qualidade/regras.py`). |
| `coluna` | `object` | Coluna avaliada, quando a regra e por coluna; vazio quando e por tabela. |
| `escopo` | `object` | Recorte adicional da avaliacao, quando existe (ex.: `ano=2024` nas regras de cobertura); vazio nas demais. |
| `registros_avaliados` | `int64` | Total de registros considerados pela regra. |
| `registros_violando` | `int64` | Registros que violaram a regra. |
| `percentual_violacao` | `float64` | Percentual de violacao. Na regra `aumento_ausencia_safra_anterior`, e a variacao em pontos percentuais contra a execucao anterior. |
| `limite_bloqueio` | `float64` | Percentual a partir do qual a regra barra a execucao; nulo nas regras de alerta. |
| `severidade` | `object` | `bloqueante` ou `alerta`. |
| `status` | `object` | `ok`, `alerta` ou `bloqueio`. |

As regras `cobertura_territorial` (entidades ausentes contra o universo
esperado, por ano) e `queda_cobertura_safra_anterior` (entidades que existiam
na execucao anterior e sumiram) sao o que torna as lacunas da secao
"Notas de cobertura dos dados" visiveis e comparaveis entre safras.
