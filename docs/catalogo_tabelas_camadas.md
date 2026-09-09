# Catalogo de Tabelas por Camada

**Adição de 08/09/2026:** `gold.base_modelagem_aluno_enriquecida`, com
IBGE/Censo Escolar e avaliações de 2025. Na Silver: `contexto_ibge_municipio`,
`contexto_censo_municipio_rede`, `alunos_alfabetizacao_oficial` e
`quarentena_alfabetizacao`. A Bronze guarda os arquivos oficiais em
`enriquecimento_oficial`. [Contrato e reprodução](enriquecimento_ibge_censo.md).

Este documento descreve o nome e a finalidade das tabelas materializadas nas camadas Bronze, Silver e Gold do pipeline.

Revisão de 07/09/2026: o lake local contém 7 entidades batch, 16 tabelas
Silver e 23 Gold (22 analíticas + qualidade). `base_modelagem_aluno` é a
nova tabela de consumo da Fase 3, com contrato em
[base_modelagem_aluno.md](base_modelagem_aluno.md). FUNDEB listado abaixo
é legado/opcional e não existe na execução local. `dim_escola` agora é
particionada por ano, com chave `ano + id_escola`. Consulte a
[auditoria atual](analise_prontidao_fase3.md) para cobertura e limitações.

## Visao Geral

| Camada | Total de tabelas | Papel no pipeline |
|---|---:|---|
| Bronze | 8 | Dados brutos ingeridos e padronizados com metadados tecnicos. |
| Silver | 17 | Dados tratados, tipados, deduplicados, com regras de qualidade e modelados em dimensoes e fatos. |
| Gold | 24 | Indicadores analiticos finais para dashboard, rankings, microdados educacionais, dados territoriais, verificacoes externas e acompanhamento de metas. |

---

## Bronze

A camada Bronze preserva as entidades de origem com baixa transformacao, acrescentando rastreabilidade de ingestao.

| Tabela | Nome descritivo | Descricao |
|---|---|---|
| `bronze.alunos` | Microdados de alunos | Base bruta de alunos avaliados, com identificadores, escola, municipio, rede, presenca, proficiencia e classificacao de alfabetizacao. |
| `bronze.bolsa_familia_municipio` | Bolsa Familia por municipio | Base agregada do Bolsa Familia por municipio, ano de competencia, UF, total de beneficiarios e valor pago. |
| `bronze.fundeb` | FUNDEB por UF | Base bruta de valores do FUNDEB por ano, estado, UF e totais financeiros. |
| `bronze.meta_alfabetizacao_brasil` | Metas nacionais de alfabetizacao | Metas e resultados de alfabetizacao no nivel Brasil, por ano e rede. |
| `bronze.meta_alfabetizacao_municipio` | Metas municipais de alfabetizacao | Metas e resultados de alfabetizacao no nivel municipio, por ano, rede e nivel de alfabetizacao. |
| `bronze.meta_alfabetizacao_uf` | Metas estaduais de alfabetizacao | Metas e resultados de alfabetizacao no nivel UF, por ano e rede. |
| `bronze.municipio` | Resultados por municipio | Resultados observados de alfabetizacao e proficiencia agregados por municipio, ano, serie e rede. |
| `bronze.uf` | Resultados por UF | Resultados observados de alfabetizacao e proficiencia agregados por UF, ano, serie e rede. |

---

## Silver

A camada Silver organiza os dados em dimensoes e fatos. Nesta camada tambem sao aplicadas regras de qualidade: padronizacao de nomes, tipagem, remocao de duplicidades e remocao de nulos em campos criticos.

| Tabela | Nome descritivo | Descricao |
|---|---|---|
| `silver.dim_escola` | Dimensao escola | Cadastro deduplicado de escolas observadas nos microdados, vinculadas ao municipio. |
| `silver.dim_municipio` | Dimensao municipio | Cadastro deduplicado de municipios usados nas analises. |
| `silver.dim_uf` | Dimensao UF | Cadastro deduplicado de Unidades Federativas, com nome e regiao brasileira. |
| `silver.dominio_regiao_uf` | Dominio de regiao por UF | Tabela auxiliar que relaciona cada UF a uma regiao brasileira. |
| `silver.fato_aluno_alfabetizacao` | Fato de alfabetizacao por aluno | Fato granular por aluno, escola, municipio, ano, serie e rede, com proficiencia, peso, status de presenca e flags de qualidade. |
| `silver.fato_bolsa_familia_municipio` | Fato Bolsa Familia municipal | Indicadores agregados do Bolsa Familia por municipio e ano de competencia. |
| `silver.fato_distribuicao_nivel_municipio` | Distribuicao de niveis por municipio | Proporcao de alunos por nivel de alfabetizacao em cada municipio, ano, serie e rede. |
| `silver.fato_distribuicao_nivel_uf` | Distribuicao de niveis por UF | Proporcao de alunos por nivel de alfabetizacao em cada UF, ano, serie e rede. |
| `silver.fato_fundeb` | Fato FUNDEB por UF | Valores do FUNDEB por ano e UF, com totais financeiros, ranking anual e flags de validacao. |
| `silver.fato_meta_anual_brasil` | Metas anuais Brasil | Metas de alfabetizacao transformadas para formato longitudinal no nivel Brasil. |
| `silver.fato_meta_anual_municipio` | Metas anuais municipio | Metas de alfabetizacao transformadas para formato longitudinal no nivel municipio. |
| `silver.fato_meta_anual_uf` | Metas anuais UF | Metas de alfabetizacao transformadas para formato longitudinal no nivel UF. |
| `silver.fato_resultado_brasil` | Resultado Brasil | Resultado observado de alfabetizacao no nivel Brasil, por ano e rede. |
| `silver.fato_resultado_meta_municipio` | Resultado de meta municipal | Resultado observado de alfabetizacao por municipio, rede e nivel de alfabetizacao. |
| `silver.fato_resultado_meta_uf` | Resultado de meta estadual | Resultado observado de alfabetizacao por UF e rede. |
| `silver.fato_resultado_municipio` | Resultado municipal | Resultado observado de alfabetizacao e media de portugues por municipio, ano, serie e rede. |
| `silver.fato_resultado_uf` | Resultado estadual | Resultado observado de alfabetizacao e media de portugues por UF, ano, serie e rede. |

---

## Gold

A camada Gold consolida os indicadores finais usados em analises e visualizacoes.

Cada tabela tem um papel declarado — **base** (juncao canonica de um grao),
**serving** (recorte pronto para uma pergunta) ou **observabilidade** (metrica
sobre a propria pipeline). O criterio para criar uma tabela nova e o
[ADR-003](adr/ADR-003-governanca-camada-gold.md): so entra no catalogo o que
acrescenta coluna calculada, muda o grao ou integra outra fonte.

| Tabela | Nome descritivo | Descricao |
|---|---|---|
| `gold.desigualdade_territorial_uf` | Desigualdade territorial por UF | Mede dispersao dos resultados municipais dentro de cada UF, com amplitude, desvio padrao e percentual abaixo da meta. |
| `gold.evolucao_alfabetizacao` | Evolucao da alfabetizacao | Serie temporal consolidada com taxa media de alfabetizacao, participacao e variacoes anuais. |
| `gold.evolucao_meta_resultado_brasil` | Evolucao metas x resultados Brasil | Serie temporal de resultado, meta, distancia da meta e variacao anual no nivel Brasil (serving; consolidou a antiga `comparacao_meta_resultado_brasil`). |
| `gold.evolucao_meta_resultado_municipio` | Evolucao metas x resultados municipio | Serie temporal de resultado, meta, distancia da meta e variacao anual por municipio (serving; consolidou a antiga `comparacao_meta_resultado_municipio`). |
| `gold.evolucao_meta_resultado_uf` | Evolucao metas x resultados UF | Serie temporal de resultado, meta, distancia da meta e variacao anual por UF (serving; consolidou a antiga `comparacao_meta_resultado_uf`). |
| `gold.distribuicao_desempenho_aluno` | Distribuicao de desempenho dos alunos | Distribui alunos por faixa de proficiencia, alfabetizacao, UF, rede e serie. |
| `gold.indicador_alfabetizacao_municipio` | Indicador de alfabetizacao por municipio | Visao municipal enriquecida com resultado, meta, status, nome do municipio, UF, Bolsa Familia e rankings de prioridade. |
| `gold.indicador_desempenho_aluno` | Indicadores de desempenho dos alunos | Agrega proficiencia, alfabetizacao e presenca por municipio, UF, rede e serie. |
| `gold.indicador_meta_brasil` | Indicador de meta Brasil | Compara resultado observado e meta de alfabetizacao no nivel Brasil, calculando distancia da meta e status. |
| `gold.indicador_meta_municipio` | Indicador de meta municipio | Compara resultado observado e meta de alfabetizacao por municipio, calculando distancia da meta e status. |
| `gold.indicador_meta_regiao` | Indicador de meta por regiao | Consolida resultado, meta, distancia e status por regiao brasileira. |
| `gold.indicador_meta_uf` | Indicador de meta UF | Compara resultado observado e meta de alfabetizacao por UF, calculando distancia da meta e status. |
| `gold.indicador_presenca_avaliacao` | Indicador de presenca na avaliacao | Resume presenca e ausencia por municipio, UF, rede e serie. |
| `gold.mapa_calor_territorial` | Mapa de calor territorial | Classifica municipios por faixa de risco conforme distancia ate a meta. |
| `gold.meta_uf_bolsa_familia` | Meta por UF x Bolsa Familia | Cruza meta estadual de alfabetizacao com total de beneficiarios e valor pago pelo Bolsa Familia. |
| `gold.meta_uf_fundeb` | Meta por UF x FUNDEB | Cruza meta estadual de alfabetizacao com valor recebido do FUNDEB e ranking anual de verba. |
| `gold.metricas_qualidade` | Metricas de qualidade por execucao | Observabilidade: historico das regras de qualidade avaliadas a cada execucao (camada, tabela, regra, violacoes, limite e status). |
| `gold.perfil_aluno_alfabetizacao` | Perfil aluno alfabetizacao | Distribui alunos por presenca, status de alfabetizacao, serie e rede. |
| `gold.ranking_escolas_prioritarias` | Ranking de escolas prioritarias | Ordena escolas por maior percentual de alunos nao alfabetizados. |
| `gold.ranking_municipio_prioritario` | Ranking de municipios prioritarios | Lista municipios abaixo da meta, ordenados pela maior distancia negativa em relacao ao objetivo. |
| `gold.ranking_territorial_prioridade` | Ranking territorial de prioridade | Ordena municipios abaixo da meta com rankings nacional, regional e por UF. |
| `gold.ranking_uf_prioritaria` | Ranking de UFs prioritarias | Lista UFs abaixo da meta, ordenadas pela maior distancia negativa em relacao ao objetivo. |
| `gold.resumo_status_meta` | Resumo de status das metas | Agregado por ano, nivel territorial e status da meta, usado para visao executiva de cumprimento das metas. |

## Relacao com os Dicionarios de Dados

Para detalhes de colunas, tipos, chaves e regras de qualidade, consulte:

- [`docs/dicionario_dados_bronze.md`](dicionario_dados_bronze.md)
- [`docs/dicionario_dados_silver.md`](dicionario_dados_silver.md)
- [`docs/dicionario_dados_gold.md`](dicionario_dados_gold.md)

