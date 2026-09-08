# Dicionario de Dados - Camada Silver

**Adição de 08/09/2026:** contextos `contexto_ibge_municipio` e
`contexto_censo_municipio_rede`, alunos de 2025 em
`alunos_alfabetizacao_oficial` e registros sem chave em
`quarentena_alfabetizacao`. [Definições](enriquecimento_ibge_censo.md).

Atualização de 07/09/2026: `dim_escola` preserva a edição da avaliação,
com coluna `ano`, chave `ano + id_escola` e 79.273 vínculos no lake local.
O fato deve se relacionar por essa chave. A referência antiga a 42.811
escolas únicas entre anos não representa uma identidade longitudinal
comprovada. Consulte [a auditoria](analise_prontidao_fase3.md).

**Camada:** Silver  
**Origem fisica:** `data/silver/`  
**Data de referencia dos arquivos:** `execution_date=2026-07-04`  
**Total de tabelas:** 17

## Visao Geral

A camada Silver contem dados tratados, padronizados e organizados para consumo analitico. As tabelas seguem dois padroes principais:

- `dim_*`: dimensoes de referencia, como municipio, UF e escola.
- `fato_*`: fatos analiticos com medidas, indicadores, metas e flags de qualidade.

## Tabelas

| Tabela | Linhas | Colunas | Descricao |
|---|---:|---:|---|
| `silver.dim_escola` | 42.811 | 4 | Cadastro de escolas observadas, vinculadas ao municipio. |
| `silver.dim_municipio` | 5.550 | 3 | Cadastro de municipios. |
| `silver.dim_uf` | 25 | 4 | Cadastro de Unidades Federativas. |
| `silver.dominio_regiao_uf` | 27 | 3 | Dominio de regiao brasileira por UF. |
| `silver.fato_aluno_alfabetizacao` | 3.867.999 | 20 | Fato granular por aluno, escola, municipio, rede e ano. |
| `silver.fato_bolsa_familia_municipio` | 11.140 | 8 | Beneficiarios e valores pagos do Bolsa Familia por municipio. |
| `silver.fato_distribuicao_nivel_municipio` | 112.032 | 8 | Distribuicao dos alunos por nivel de alfabetizacao no municipio. |
| `silver.fato_distribuicao_nivel_uf` | 675 | 8 | Distribuicao dos alunos por nivel de alfabetizacao na UF. |
| `silver.fato_fundeb` | 54 | 13 | Valores do FUNDEB por UF e ano. |
| `silver.fato_meta_anual_brasil` | 21 | 7 | Metas anuais de alfabetizacao para Brasil. |
| `silver.fato_meta_anual_municipio` | 74.688 | 8 | Metas anuais de alfabetizacao por municipio. |
| `silver.fato_meta_anual_uf` | 545 | 8 | Metas anuais de alfabetizacao por UF. |
| `silver.fato_resultado_brasil` | 3 | 8 | Resultado observado de alfabetizacao para Brasil. |
| `silver.fato_resultado_meta_municipio` | 10.584 | 10 | Resultado de meta por municipio e nivel de alfabetizacao. |
| `silver.fato_resultado_meta_uf` | 77 | 9 | Resultado de meta por UF. |
| `silver.fato_resultado_municipio` | 23.995 | 8 | Resultado observado de alfabetizacao por municipio. |
| `silver.fato_resultado_uf` | 145 | 8 | Resultado observado de alfabetizacao por UF. |

## Campos Recorrentes

| Coluna | Descricao |
|---|---|
| `ano` | Ano de referencia do dado observado. |
| `ano_competencia` | Ano de competencia do beneficio ou pagamento. |
| `ano_meta` | Ano da meta projetada. |
| `id_municipio` | Codigo IBGE do municipio. |
| `id_municipio_nome` | Nome do municipio. |
| `sigla_uf` | Sigla da Unidade Federativa. |
| `sigla_uf_nome` | Nome da Unidade Federativa. |
| `rede` | Rede de ensino ou nivel administrativo. |
| `serie` | Serie escolar analisada. |
| `taxa_alfabetizacao` | Percentual de alunos alfabetizados ou taxa consolidada. |
| `media_portugues` | Media de proficiencia em Lingua Portuguesa. |
| `meta_alfabetizacao` | Meta percentual de alfabetizacao. |
| `percentual_participacao` | Percentual de participacao no indicador. |
| `nivel_agregacao` | Nivel territorial do indicador: Brasil, UF ou Municipio. |
| `nivel_alfabetizacao` | Nivel de alfabetizacao usado na distribuicao dos alunos. |
| `data_processamento_silver` | Data em que a tabela foi processada na camada Silver. |
| `flag_*` | Indicador booleano de validacao ou qualidade do campo relacionado. |

## Regras de Qualidade Aplicadas

A etapa de qualidade da Silver e executada em `src/silver/qualidade.py`, apos a transformacao e antes da gravacao dos arquivos Parquet.

| Regra | Aplicacao |
|---|---|
| Padronizacao de nomes | Colunas sao normalizadas para `snake_case`, sem acentos, sem espacos e sem caracteres especiais. |
| Remocao de duplicidades | Cada tabela usa a chave primaria sugerida como subconjunto de deduplicacao. Quando nao houver regra explicita, a linha completa e usada. |
| Remocao de nulos criticos | Registros com nulos ou strings vazias nas chaves e campos obrigatorios da tabela sao descartados. |
| Ajuste de tipagem | Colunas temporais e identificadores recebem tipos consistentes; medidas numericas sao convertidas com `pd.to_numeric`; flags sao convertidas para booleano nullable. |
| Rastreabilidade | O pipeline imprime a volumetria antes e depois da qualidade para cada tabela Silver. |

## Chaves e Relacionamentos

As chaves abaixo sao definicoes conceituais para documentacao, validacao e consumo analitico. Como a camada Silver esta materializada em arquivos Parquet, essas restricoes nao sao aplicadas fisicamente como em um banco relacional tradicional.

### Chaves Primarias Sugeridas

| Tabela | Chave primaria sugerida | Observacao |
|---|---|---|
| `silver.dim_uf` | `sigla_uf` | Identifica uma Unidade Federativa. |
| `silver.dominio_regiao_uf` | `sigla_uf` | Relaciona cada UF a uma regiao brasileira. |
| `silver.dim_municipio` | `id_municipio` | Identifica um municipio pelo codigo IBGE. |
| `silver.dim_escola` | `id_escola` | Identifica uma escola. |
| `silver.fato_resultado_uf` | `ano`, `sigla_uf`, `serie`, `rede` | Resultado anual por UF, serie e rede. |
| `silver.fato_resultado_municipio` | `ano`, `id_municipio`, `serie`, `rede` | Resultado anual por municipio, serie e rede. |
| `silver.fato_resultado_brasil` | `ano`, `rede`, `nivel_agregacao` | Resultado anual consolidado no Brasil. |
| `silver.fato_meta_anual_uf` | `ano`, `sigla_uf`, `rede`, `ano_meta` | Meta anual por UF e ano alvo. |
| `silver.fato_meta_anual_municipio` | `ano`, `id_municipio`, `rede`, `ano_meta` | Meta anual por municipio e ano alvo. |
| `silver.fato_meta_anual_brasil` | `ano`, `rede`, `ano_meta`, `nivel_agregacao` | Meta anual consolidada no Brasil. |
| `silver.fato_aluno_alfabetizacao` | `ano`, `id_aluno`, `id_escola` | Registro do aluno em uma escola e ano. |
| `silver.fato_distribuicao_nivel_uf` | `ano`, `sigla_uf`, `serie`, `rede`, `nivel_alfabetizacao` | Distribuicao por nivel de alfabetizacao na UF. |
| `silver.fato_distribuicao_nivel_municipio` | `ano`, `id_municipio`, `serie`, `rede`, `nivel_alfabetizacao` | Distribuicao por nivel de alfabetizacao no municipio. |
| `silver.fato_resultado_meta_uf` | `ano`, `sigla_uf`, `rede`, `nivel_agregacao` | Resultado de meta agregado por UF. |
| `silver.fato_resultado_meta_municipio` | `ano`, `id_municipio`, `rede`, `nivel_alfabetizacao` | Resultado de meta por municipio e nivel. |
| `silver.fato_bolsa_familia_municipio` | `ano_competencia`, `id_municipio` | Agregado anual do Bolsa Familia por municipio. |
| `silver.fato_fundeb` | `ano`, `sigla_uf` | Valores do FUNDEB por UF e ano. |

### Chaves Estrangeiras Sugeridas

| Tabela origem | Coluna origem | Tabela destino | Coluna destino | Relacionamento |
|---|---|---|---|---|
| `silver.dim_escola` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Escola pertence a um municipio. |
| `silver.dim_uf` | `sigla_uf` | `silver.dominio_regiao_uf` | `sigla_uf` | UF pertence a uma regiao brasileira. |
| `silver.fato_aluno_alfabetizacao` | `id_escola` | `silver.dim_escola` | `id_escola` | Aluno esta vinculado a uma escola. |
| `silver.fato_aluno_alfabetizacao` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Aluno esta vinculado a um municipio. |
| `silver.fato_resultado_municipio` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Resultado observado por municipio. |
| `silver.fato_meta_anual_municipio` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Meta anual por municipio. |
| `silver.fato_resultado_meta_municipio` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Resultado de meta por municipio. |
| `silver.fato_distribuicao_nivel_municipio` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Distribuicao de niveis por municipio. |
| `silver.fato_bolsa_familia_municipio` | `id_municipio` | `silver.dim_municipio` | `id_municipio` | Beneficios agregados por municipio. |
| `silver.fato_resultado_uf` | `sigla_uf` | `silver.dim_uf` | `sigla_uf` | Resultado observado por UF. |
| `silver.fato_meta_anual_uf` | `sigla_uf` | `silver.dim_uf` | `sigla_uf` | Meta anual por UF. |
| `silver.fato_resultado_meta_uf` | `sigla_uf` | `silver.dim_uf` | `sigla_uf` | Resultado de meta por UF. |
| `silver.fato_distribuicao_nivel_uf` | `sigla_uf` | `silver.dim_uf` | `sigla_uf` | Distribuicao de niveis por UF. |
| `silver.fato_fundeb` | `sigla_uf` | `silver.dim_uf` | `sigla_uf` | Valor do FUNDEB por UF. |
| `silver.fato_bolsa_familia_municipio` | `sigla_uf` | `silver.dim_uf` | `sigla_uf` | Beneficios agregados por UF. |

---

## `silver.dim_escola`

Cadastro de escolas observadas na base de alunos, vinculadas ao municipio.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id_escola` | `object` | Codigo identificador da escola. |
| `id_municipio` | `object` | Codigo IBGE do municipio da escola. |
| `id_municipio_nome` | `object` | Nome do municipio da escola. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.dim_municipio`

Cadastro de municipios usados nas analises.

| Coluna | Tipo | Descricao |
|---|---|---|
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `id_municipio_nome` | `object` | Nome do municipio. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.dim_uf`

Cadastro de Unidades Federativas.

| Coluna | Tipo | Descricao |
|---|---|---|
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `sigla_uf_nome` | `object` | Nome da Unidade Federativa. |
| `regiao_brasil` | `object` | Regiao brasileira da UF. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.dominio_regiao_uf`

Dominio auxiliar de regiao brasileira por UF.

| Coluna | Tipo | Descricao |
|---|---|---|
| `sigla_uf` | `object` | Sigla da Unidade Federativa. |
| `regiao_brasil` | `object` | Regiao brasileira da UF. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_aluno_alfabetizacao`

Fato granular com informacoes de alfabetizacao por aluno.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `id_aluno` | `object` | Identificador do aluno. |
| `id_escola` | `object` | Identificador da escola. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `serie` | `object` | Serie escolar. |
| `rede` | `object` | Rede de ensino. |
| `caderno` | `object` | Tipo ou identificador do caderno aplicado. |
| `presenca` | `object` | Indicador de presenca do aluno. |
| `preenchimento_caderno` | `object` | Situacao de preenchimento do caderno. |
| `alfabetizado` | `object` | Classificacao de alfabetizacao do aluno. |
| `proficiencia` | `float64` | Proficiencia do aluno. |
| `peso_aluno` | `float64` | Peso amostral ou peso do aluno no indicador. |
| `flag_id_aluno_valido` | `bool` | Indica se o identificador do aluno e valido. |
| `flag_id_escola_valido` | `bool` | Indica se o identificador da escola e valido. |
| `flag_id_municipio_valido` | `bool` | Indica se o identificador do municipio e valido. |
| `flag_proficiencia_valida` | `bool` | Indica se a proficiencia e valida. |
| `flag_peso_aluno_valido` | `bool` | Indica se o peso do aluno e valido. |
| `flag_presenca_preenchida` | `bool` | Indica se a presenca foi preenchida. |
| `flag_alfabetizado_preenchido` | `bool` | Indica se a classificacao de alfabetizacao foi preenchida. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_bolsa_familia_municipio`

Fato com dados agregados do Bolsa Familia por municipio.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano_competencia` | `Int64` | Ano de competencia do beneficio. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `sigla_uf` | `object` | Sigla da UF do municipio. |
| `total_beneficiarios` | `Int64` | Total de beneficiarios no municipio. |
| `valor_total_pago` | `float64` | Valor total pago no municipio. |
| `flag_total_beneficiarios_valido` | `boolean` | Indica se o total de beneficiarios e valido. |
| `flag_valor_total_pago_valido` | `bool` | Indica se o valor total pago e valido. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_distribuicao_nivel_municipio`

Distribuicao de alunos por nivel de alfabetizacao no municipio.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `serie` | `object` | Serie escolar. |
| `rede` | `object` | Rede de ensino. |
| `nivel_alfabetizacao` | `Int64` | Nivel de alfabetizacao. |
| `proporcao_alunos` | `float64` | Proporcao de alunos no nivel. |
| `flag_proporcao_alunos_valido` | `bool` | Indica se a proporcao esta entre 0 e 100 ou nula. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_distribuicao_nivel_uf`

Distribuicao de alunos por nivel de alfabetizacao na UF.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `sigla_uf` | `object` | Sigla da UF. |
| `serie` | `object` | Serie escolar. |
| `rede` | `object` | Rede de ensino. |
| `nivel_alfabetizacao` | `Int64` | Nivel de alfabetizacao. |
| `proporcao_alunos` | `float64` | Proporcao de alunos no nivel. |
| `flag_proporcao_alunos_valido` | `bool` | Indica se a proporcao esta entre 0 e 100 ou nula. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_fundeb`

Fato com dados do FUNDEB por UF e ano.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `ranking_ano` | `Int64` | Posicao da UF no ranking anual. |
| `estado` | `object` | Nome do estado. |
| `sigla_uf` | `object` | Sigla da UF. |
| `total_estado_df` | `float64` | Total associado ao estado ou Distrito Federal. |
| `total_municipios` | `float64` | Total associado aos municipios. |
| `total_fundeb` | `float64` | Total do FUNDEB. |
| `percentual_brasil` | `float64` | Participacao percentual da UF no total Brasil. |
| `flag_total_estado_df_valido` | `bool` | Indica se o total do estado/DF e valido. |
| `flag_total_municipios_valido` | `bool` | Indica se o total dos municipios e valido. |
| `flag_total_fundeb_valido` | `bool` | Indica se o total do FUNDEB e valido. |
| `flag_percentual_brasil_valido` | `bool` | Indica se o percentual Brasil esta entre 0 e 100 ou nulo. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_meta_anual_brasil`

Metas anuais de alfabetizacao em nivel Brasil.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano base da medicao. |
| `rede` | `object` | Rede de ensino. |
| `ano_meta` | `Int64` | Ano alvo da meta. |
| `meta_alfabetizacao` | `float64` | Meta percentual de alfabetizacao. |
| `flag_meta_alfabetizacao_valido` | `bool` | Indica se a meta esta entre 0 e 100 ou nula. |
| `nivel_agregacao` | `object` | Nivel territorial da meta. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_meta_anual_municipio`

Metas anuais de alfabetizacao por municipio.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano base da medicao. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `rede` | `object` | Rede de ensino. |
| `ano_meta` | `Int64` | Ano alvo da meta. |
| `meta_alfabetizacao` | `float64` | Meta percentual de alfabetizacao. |
| `flag_meta_alfabetizacao_valido` | `bool` | Indica se a meta esta entre 0 e 100 ou nula. |
| `nivel_agregacao` | `object` | Nivel territorial da meta. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_meta_anual_uf`

Metas anuais de alfabetizacao por UF.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano base da medicao. |
| `sigla_uf` | `object` | Sigla da UF. |
| `rede` | `object` | Rede de ensino. |
| `ano_meta` | `Int64` | Ano alvo da meta. |
| `meta_alfabetizacao` | `float64` | Meta percentual de alfabetizacao. |
| `flag_meta_alfabetizacao_valido` | `bool` | Indica se a meta esta entre 0 e 100 ou nula. |
| `nivel_agregacao` | `object` | Nivel territorial da meta. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_resultado_brasil`

Resultado observado de alfabetizacao em nivel Brasil.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `rede` | `object` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | Taxa de alfabetizacao observada. |
| `percentual_participacao` | `float64` | Percentual de participacao. |
| `flag_taxa_alfabetizacao_valido` | `bool` | Indica se a taxa esta entre 0 e 100 ou nula. |
| `flag_percentual_participacao_valido` | `bool` | Indica se a participacao esta entre 0 e 100 ou nula. |
| `nivel_agregacao` | `object` | Nivel territorial do resultado. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_resultado_meta_municipio`

Resultado observado por municipio, rede e nivel de alfabetizacao.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `rede` | `object` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | Taxa de alfabetizacao observada. |
| `nivel_alfabetizacao` | `Int64` | Nivel de alfabetizacao. |
| `percentual_participacao` | `float64` | Percentual de participacao. |
| `flag_taxa_alfabetizacao_valido` | `bool` | Indica se a taxa esta entre 0 e 100 ou nula. |
| `flag_percentual_participacao_valido` | `bool` | Indica se a participacao esta entre 0 e 100 ou nula. |
| `nivel_agregacao` | `object` | Nivel territorial do resultado. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_resultado_meta_uf`

Resultado observado por UF e rede.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `sigla_uf` | `object` | Sigla da UF. |
| `rede` | `object` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | Taxa de alfabetizacao observada. |
| `percentual_participacao` | `float64` | Percentual de participacao. |
| `flag_taxa_alfabetizacao_valido` | `bool` | Indica se a taxa esta entre 0 e 100 ou nula. |
| `flag_percentual_participacao_valido` | `bool` | Indica se a participacao esta entre 0 e 100 ou nula. |
| `nivel_agregacao` | `object` | Nivel territorial do resultado. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_resultado_municipio`

Resultado observado de alfabetizacao por municipio.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `id_municipio` | `object` | Codigo IBGE do municipio. |
| `serie` | `object` | Serie escolar. |
| `rede` | `object` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | Taxa de alfabetizacao observada. |
| `media_portugues` | `float64` | Media de proficiencia em Lingua Portuguesa. |
| `flag_taxa_alfabetizacao_valido` | `bool` | Indica se a taxa esta entre 0 e 100 ou nula. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |

## `silver.fato_resultado_uf`

Resultado observado de alfabetizacao por UF.

| Coluna | Tipo | Descricao |
|---|---|---|
| `ano` | `Int64` | Ano de referencia. |
| `sigla_uf` | `object` | Sigla da UF. |
| `serie` | `object` | Serie escolar. |
| `rede` | `object` | Rede de ensino. |
| `taxa_alfabetizacao` | `float64` | Taxa de alfabetizacao observada. |
| `media_portugues` | `float64` | Media de proficiencia em Lingua Portuguesa. |
| `flag_taxa_alfabetizacao_valido` | `bool` | Indica se a taxa esta entre 0 e 100 ou nula. |
| `data_processamento_silver` | `object` | Data de processamento na camada Silver. |
