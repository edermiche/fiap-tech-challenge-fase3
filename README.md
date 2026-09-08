# Tech Challenge FIAP — Fase 2

## Pipeline Híbrido para Análise da Alfabetização no Brasil

**Evolução local de 08/09/2026:** IBGE, Censo Escolar e AEEB 2025 foram
incorporados em `gold.base_modelagem_aluno_enriquecida`, com 12 novos
preditores e 1.966.095 avaliações elegíveis de 2025. Veja os
[dados, cobertura e comandos de reprodução](docs/enriquecimento_ibge_censo.md).
Esta etapa adiciona uma tabela Gold e quatro conjuntos Silver ao inventário
de 07/09 abaixo; dados e modelos continuam fora do Git.

**Revisão local de 07/09/2026:** a Gold agora inclui
`base_modelagem_aluno`, própria para a classificação pedida na Fase 3.
Consulte a [análise de cobertura e lacunas](docs/analise_prontidao_fase3.md)
e o [contrato de consumo](docs/base_modelagem_aluno.md). A revisão também
preserva resultados sem metas e corrige a dimensão escolar para a chave
`ano + id_escola`; códigos escolares não devem ser cruzados entre anos sem
correspondência validada. No lake local: 7 entidades batch, 16 tabelas Silver
e 23 Gold (22 analíticas + qualidade); FUNDEB está ausente. Os números da
auditoria substituem as contagens históricas nas seções abaixo.

Pipeline de engenharia de dados em Arquitetura Medalhão (Bronze → Silver → Gold) com ingestão híbrida (batch + streaming), construído sobre dados públicos do INEP disponibilizados pela [Base dos Dados](https://basedosdados.org/), para acompanhar o **Indicador Criança Alfabetizada** no Brasil.

**Repositório**: https://github.com/edermiche/fiap-tech-challenge-fase2
---

## 1. Contexto do Problema

A alfabetização na infância é um dos pilares do desenvolvimento educacional, social e econômico de um país. O **Compromisso Nacional Criança Alfabetizada** é a política pública que mobiliza União, estados, Distrito Federal e municípios com o objetivo de garantir que todas as crianças brasileiras estejam alfabetizadas até o final do 2º ano do Ensino Fundamental.

Para dar base objetiva a essa política, o INEP realizou em 2023 a **Pesquisa Alfabetiza Brasil**, que definiu o ponto de corte de **743 pontos na escala de proficiência do Saeb** como o nível a partir do qual uma criança é considerada alfabetizada. Desse parâmetro nasceu o **Indicador Criança Alfabetizada**: o percentual de estudantes que atingem esse patamar. A meta nacional é que, até **2030**, 100% das crianças estejam alfabetizadas ao final do 2º ano.

O desafio analítico: acompanhar esse indicador exige integrar fontes heterogêneas — metas nacionais, estaduais e municipais, dados territoriais e microdados de avaliação por aluno — com qualidade, escalabilidade e custo controlado. Este projeto simula o trabalho de um time de engenharia de dados de uma organização pública de análise educacional que constrói exatamente essa fundação.

### Perguntas de negócio que a pipeline responde

- Qual a taxa de alfabetização observada por Brasil, UF e município, e como ela se compara com as metas oficiais de cada ano?
- Quais UFs e municípios estão mais distantes das metas e deveriam ser priorizados por políticas públicas?
- Como o indicador evolui no tempo, em cada nível de agregação?

---

## 2. Arquitetura da Solução

### Visão geral

![Arquitetura do projeto — pipeline híbrido local e AWS](docs/arquitetura_projeto.png)

Fonte editável do diagrama: [docs/diagrama_arquitetura.drawio](docs/diagrama_arquitetura.drawio)

### Fluxo de dados

1. **Extração batch**: `src/bronze/download_bigquery.py` consulta a Base dos Dados no BigQuery (com dry run de custo antes de cada execução) e grava as 7 entidades em parquet, particionadas por `execution_date`.
2. **Ingestão streaming**: `src/streaming/producer.py` reemite medições de alunos como eventos em micro-lotes — para a fila local (modo padrão, sem AWS) ou para o Kinesis Data Streams (`--destino kinesis`). O consumo é feito pelo `consumer.py` (local) ou pelo Lambda `consumer_lambda.py` (nuvem), que adicionam metadados de ingestão e gravam na Bronze em `alunos_streaming/ano=YYYY/`.
3. **Consolidação Bronze**: `src/bronze/processar_bronze.py` unifica os arquivos brutos de cada entidade com metadados técnicos (`entidade_origem`, `modo_ingestao`, `data_ingestao_bronze`).
4. **Transformação Silver**: `src/silver/processar_silver.py` une os alunos ingeridos por batch e por streaming em uma única base (deduplicação pela chave natural do registro; a coluna `modo_ingestao` preserva a origem), limpa, padroniza tipos, remove duplicidades, normaliza chaves, cria flags de qualidade e modela dimensões e fatos. Antes de publicar, mede a qualidade, grava as métricas em `gold.metricas_qualidade` e **aplica o gate**: safra reprovada não é gravada nem chega à Gold (ver [ADR-002](docs/adr/ADR-002-gate-de-qualidade.md)).
5. **Camada Gold**: `src/gold/processar_gold.py` integra resultados e metas e materializa datasets prontos para consumo analítico.

`main.py` executa as três etapas acima em sequência (bronze → silver → gold) com um único comando.

### Implementação em nuvem (AWS)

A pipeline de streaming e o data lake estão **implementados e testados na AWS** (região `sa-east-1` — dados públicos brasileiros em região brasileira):

| Componente local (simulação) | Implementação AWS | Status |
|---|---|---|
| `data/` (parquet em camadas) | S3 — prefixos `bronze/`, `silver/`, `gold/` no bucket do lake | ✅ implantado (63+ arquivos) |
| `data/streaming/fila/` (micro-lotes JSON) | Kinesis Data Streams (1 shard provisionado) | ✅ implantado |
| `src/streaming/consumer.py` | Lambda `consumer_lambda.py` com trigger no Kinesis + layer AWSSDKPandas | ✅ implantado |
| Prints/logs de execução | CloudWatch Logs (lotes processados por invocação) | ✅ ativo |
| `src/bronze/download_bigquery.py` | Glue Job Python Shell `bronze-ingestao` (BigQuery → S3, service account no Secrets Manager) dentro do Glue Workflow, disparado por EventBridge Scheduler | ✅ implantado |
| `src/silver` e `src/gold` | Glue Jobs `silver-transformacoes` e `gold-analitica` no mesmo workflow (encadeamento condicional bronze → silver → gold, reaproveitando os módulos locais via pacote `src/` no S3) | ✅ implantado |
| — | Alertas de falha de job: EventBridge rule → SNS (e-mail) | ✅ implantado |

O desenho local e o da nuvem são deliberadamente espelhados: o handler do Lambda (`src/streaming/consumer_lambda.py`) reimplementa o mesmo fluxo do consumer local, e o producer alterna entre os destinos com uma flag (`--destino kinesis` usa `put_records` via boto3). Isso permite que qualquer avaliador execute a simulação completa sem conta AWS, e que a versão em nuvem seja reproduzida com um comando via Terraform (`infra/` — ver [infra/README.md](infra/README.md)), incluindo o import dos recursos pré-existentes para o state.

Teste de ponta a ponta realizado: 500 eventos reais de alunos enviados pelo producer → Kinesis → Lambda (5 lotes de 100) → parquet particionado por ano no S3. Evidências (prints do console S3, métricas do Kinesis e logs do CloudWatch) em [docs/evidencias/](docs/evidencias/).

---

## 3. Ingestão Híbrida — por que cada fonte é batch ou streaming

| Fonte | Modo | Justificativa |
|---|---|---|
| Metas Brasil / UF / Município | **Batch** | Publicadas em ciclos oficiais anuais; não há ganho em processá-las continuamente |
| Município, UF (agregados) | **Batch** | Dados territoriais e agregados consolidados por ano de avaliação |
| Medições de alunos | **Streaming (simulado)** | Representa o cenário real de resultados de avaliação chegando incrementalmente de escolas/sistemas aplicadores. Não existe fonte pública de streaming para esses dados, então o producer simula esse comportamento em micro-lotes — o que basta para demonstrar o padrão arquitetural |

A decisão segue o princípio de usar streaming apenas onde a semântica do dado é de evento incremental — e não "porque foi pedido". O custo operacional de um stream só se justifica para a fonte que de fato se comportaria assim em produção.

---

## 4. Arquitetura Medalhão

### Particionamento

Nas três camadas, as tabelas com uma coluna de ano são gravadas como `execution_date=<data>/ano=<ano>/arquivo.parquet` (implementado em `src/common/particionamento.py`, compartilhado por bronze/silver/gold):

- **`execution_date`**: preserva o histórico de execuções do pipeline (reprocessamento/versão).
- **`ano`**: permite leitura seletiva por ano — em motores com partition pruning (Athena/BigQuery), reduz os bytes escaneados por consulta (ver seção de FinOps).

Tabelas sem uma coluna de ano — dimensões e domínios (`dim_uf`, `dim_municipio`, `dim_escola`, `dominio_regiao_uf`) — não recebem a subpartição por ano: são cadastros, não fatos, e fatiar por ano não traria ganho de performance nem faria sentido semântico.

### 🥉 Bronze — dados brutos

- 7 entidades: `alunos` (3,87 mi de linhas), `municipio`, `uf`, `meta_alfabetizacao_brasil`, `meta_alfabetizacao_uf`, `meta_alfabetizacao_municipio`, `bolsa_familia_municipio`
- Ingestão bruta (BigQuery → parquet) particionada por `execution_date=YYYY-MM-DD`; consolidação processada em `<entidade>/processado/ano=YYYY/`, particionada por ano
- Eventos de streaming gravados em `alunos_streaming/ano=YYYY/` — unidos à entidade `alunos` (batch) na transformação Silver, com deduplicação pela chave natural (batch prevalece) e rastreabilidade pela coluna `modo_ingestao`
- Metadados técnicos de rastreabilidade em todas as entidades

**Volume de dados**: o projeto trabalha com todo o histórico disponível do Indicador Criança Alfabetizada (avaliação SAEB de 2023 e 2024 em todas as granularidades; Brasil e UF já têm um ciclo de acompanhamento adicional para 2025; metas projetadas até 2030). Indicador exige série histórica para comparação — descartar anos inviabilizaria a análise de evolução temporal.

### 🥈 Silver — dados tratados

17 tabelas modeladas em dimensões e fatos ([dicionário completo](docs/dicionario_dados_silver.md), [catálogo por camada](docs/catalogo_tabelas_camadas.md)):

- **Dimensões**: `dim_uf`, `dim_municipio`, `dim_escola`
- **Fatos de resultado**: `fato_resultado_brasil`, `fato_resultado_uf`, `fato_resultado_municipio`, `fato_resultado_meta_uf`, `fato_resultado_meta_municipio`
- **Fatos de metas** (colunas → linhas): `fato_meta_anual_brasil`, `fato_meta_anual_uf`, `fato_meta_anual_municipio`
- **Distribuição por nível**: `fato_distribuicao_nivel_uf`, `fato_distribuicao_nivel_municipio`
- **Granularidade aluno**: `fato_aluno_alfabetizacao` (3,87 mi de linhas com flags de qualidade)
- **Enriquecimento externo**: `fato_bolsa_familia_municipio` (total de beneficiários e valor pago por município/ano, consumida na Gold em `meta_uf_bolsa_familia` e `indicador_alfabetizacao_municipio`)

Transformações aplicadas: padronização de textos e códigos identificadores, conversão de tipos, remoção de duplicidades exatas, normalização de chaves, unpivot de metas anuais e níveis de proficiência, flags de validação (percentuais em [0,100], chaves preenchidas, valores não negativos) — registros inválidos são sinalizados, não descartados, preservando rastreabilidade.

### 🥇 Gold — camada analítica

22 datasets analíticos prontos para consumo, mais a tabela de observabilidade `metricas_qualidade` ([dicionário completo](docs/dicionario_dados_gold.md)):

| Tabela | Pergunta que responde |
|---|---|
| `evolucao_meta_resultado_brasil` / `_uf` / `_municipio` | Comparação entre resultado observado e meta **e** evolução temporal da distância da meta — uma tabela de consumo por grão (ver [ADR-003](docs/adr/ADR-003-governanca-camada-gold.md)) |
| `indicador_meta_regiao` / `desigualdade_territorial_uf` | Dados territoriais por região e UF, incluindo desigualdade interna entre municípios |
| `indicador_meta_brasil` / `_uf` / `_municipio` | Resultado observado vs. meta do mesmo ano, com status de atingimento |
| `indicador_alfabetizacao_municipio` | Visao municipal enriquecida com nome do municipio, UF, Bolsa Familia e rankings de prioridade |
| `perfil_aluno_alfabetizacao` / `indicador_presenca_avaliacao` / `ranking_escolas_prioritarias` | Microdados educacionais agregados: perfil, presença e priorização escolar |
| `indicador_desempenho_aluno` / `distribuicao_desempenho_aluno` | Indicadores de proficiência, alfabetização e faixas de desempenho dos alunos |
| `ranking_territorial_prioridade` / `mapa_calor_territorial` | Priorização e classificação de risco territorial para municípios |
| `meta_uf_fundeb` / `meta_uf_bolsa_familia` | Verificações externas: verba FUNDEB ou beneficiários do Bolsa Família x meta estadual |
| `evolucao_alfabetizacao` | Evolução temporal do indicador por nível de agregação |
| `ranking_uf_prioritaria` / `ranking_municipio_prioritario` | Priorização por distância à meta — insumo direto para política pública |
| `resumo_status_meta` | Consolidação de atingimento por ano e agregação |
| `metricas_qualidade` | Observabilidade: a qualidade piorou desde a safra anterior? |

Cada tabela tem um papel declarado — base, serving ou observabilidade — e o
critério para criar a próxima está no [ADR-003](docs/adr/ADR-003-governanca-camada-gold.md).
Foi ele que consolidou as antigas `comparacao_meta_resultado_*` nas
`evolucao_meta_resultado_*` do mesmo grão, que já continham todas as colunas
delas.

---

## 5. Qualidade de Dados

Mecanismos implementados ao longo das camadas:

- **Duplicidade**: análise de chaves candidatas na Bronze ([insumos de modelagem](docs/insumos_modelagem_bronze.md)) e `drop_duplicates` sistemático na Silver
- **Valores ausentes**: perfil de nulos por coluna documentado nos dicionários; nulos legítimos (ex.: proficiência de alunos ausentes) preservados e sinalizados
- **Chaves de relacionamento**: validação de integridade referencial entre tabelas (cobertura de `id_municipio`, `sigla_uf`, `ano` entre origens — documentada nos insumos de modelagem)
- **Consistência**: flags de validação de intervalo em todos os campos percentuais; notebooks de quality checks (`03_quality_checks.ipynb`)

### O gate: a validação barra, não só sinaliza

Sinalizar sem interromper deixaria a Gold ser construída sobre uma extração
corrompida — flags registradas, dashboards com número errado e aparência de
normalidade. Por isso as regras têm severidade ([ADR-002](docs/adr/ADR-002-gate-de-qualidade.md)):

- **Bloqueantes** — tabela vazia, chave primária duplicada, campo obrigatório
  nulo, percentual fora de `[0,100]` acima de 5%, descarte de linha por chave
  inválida acima de 5%: `QualidadeInsuficienteError` interrompe a execução
  **antes** de a Silver ser publicada. Na AWS, o job Glue falha e dispara o
  alerta SNS já implantado.
- **De alerta** — ausência de métrica vinda da fonte, deduplicação de dimensão
  derivada de fato, aumento de ausência entre safras, cobertura territorial
  incompleta: ficam registradas e não interrompem, porque não são erro do
  pipeline. A regra `cobertura_territorial` é a que torna visível, por exemplo,
  que a Gold traz 24 das 27 UFs em 2024 (AC e DF só têm meta a partir de 2025;
  RR não tem resultado até 2024) — lacunas listadas em
  [notas de cobertura](docs/dicionario_dados_gold.md#notas-de-cobertura-dos-dados).

O catálogo de regras e limites está em `src/qualidade/regras.py`;
`QUALIDADE_MODO=alertar` permite investigar sem interromper.

### O histórico: `gold.metricas_qualidade`

Métrica que só existe no stdout não responde a pergunta que qualidade de dados
existe para responder, que é comparativa. Toda execução grava uma linha por
camada/tabela/regra em `gold/metricas_qualidade/execution_date=<data>/`, com
registros avaliados, violações, limite e status — e compara com a execução
anterior na regra `aumento_ausencia_safra_anterior`. A tabela é navegável no
catálogo Gold (`app/gold_catalog.py`).

### Testes

```bash
pytest tests/
```

`tests/test_qualidade.py` cobre os três comportamentos que sustentam a
decisão: percentual fora do intervalo barra; deduplicação de dimensão não
barra; o histórico é gravado e a safra seguinte se compara com a anterior.

### Validadores visuais das camadas (`app/`)

Aplicações Flask para inspecionar os arquivos parquet gerados em cada camada pelo navegador — úteis para conferência rápida de qualidade sem abrir notebooks:

- `app/medallion_validator.py`: navegação entre Bronze, Silver e Gold em uma única interface (lista tabelas, resume linhas/colunas, agrupa por eixo e métrica, gera gráfico de barras, consulta a distribuição de `status_meta` e mostra amostras)
- `app/dashboard_alfabetizacao.py`: dashboard analítico da Gold (Brasil/UF/Município) com filtros de ano, rede e UF
- `app/mapa_brasil_metas.py`: mapa do Brasil (SVG) colorido por status da meta, com drill-down por estado e por município
- `app/dashboard_simulacao_2030.py`: dashboard de cenários municipais até 2030, com filtros por ano simulado, UF, risco e município

```bash
python app/medallion_validator.py       # http://127.0.0.1:5000
python app/dashboard_alfabetizacao.py   # http://127.0.0.1:5003
python app/mapa_brasil_metas.py         # http://127.0.0.1:5004
python app/dashboard_simulacao_2030.py  # http://127.0.0.1:5005
```

---

## 6. Decisões Arquiteturais (trade-offs)

As decisões cujo trade-off não é óbvio no código estão registradas como ADRs
em [docs/adr/](docs/adr/README.md) — o que foi decidido, por quê e o que a
decisão custa:

| ADR | Decisão |
|---|---|
| [ADR-001](docs/adr/ADR-001-fonte-bigquery-vs-download.md) | Extrair via BigQuery em vez de baixar o dataset — e o que a arquitetura multi-cloud cobra por isso |
| [ADR-002](docs/adr/ADR-002-gate-de-qualidade.md) | Validação estrutural barra a execução; métricas persistidas com histórico |
| [ADR-003](docs/adr/ADR-003-governanca-camada-gold.md) | Papel declarado por tabela Gold e consolidação das sobreposições |
| [ADR-004](docs/adr/ADR-004-ciclo-de-vida-armazenamento.md) | Lifecycle Policy do S3 declarada no `s3.tf` |

**Fonte de dados: BigQuery (multi-cloud) vs. download direto** — a Base dos Dados oferece as duas formas. Escolhemos o BigQuery porque as consultas filtram e denormalizam na origem (a de alunos resolve seis junções com dicionários), o que evita hospedar arquivo grande e mantém a extração auditável em SQL. O preço é consciente: dependência de uma conta GCP com billing próprio e tráfego entre nuvens (GCP → S3) a cada carga, recorrente e proporcional à frequência de execução. O download direto tornaria a arquitetura single-cloud e eliminaria esse egress, ao custo de baixar o dataset inteiro e refazer as junções em pandas. Detalhes, números e os gatilhos para revisitar: [ADR-001](docs/adr/ADR-001-fonte-bigquery-vs-download.md).

**Batch vs. Streaming** — Kafka foi considerado e descartado: para o volume do projeto (milhares de eventos, não milhões/dia), operar um cluster Kafka é over-engineering. A simulação local com fila de micro-lotes demonstra o padrão e migra naturalmente para Kinesis Data Streams (gerenciado, 1 shard, custo próximo de zero no nosso volume), mantendo a semântica de producer/consumer.

**Data Lake vs. Data Warehouse** — optamos por data lake em parquet: os dados são públicos, o consumo é analítico e exploratório, e parquet colunar + particionamento entrega performance de leitura sem o custo fixo de um warehouse provisionado. Se o consumo evoluir para BI corporativo de alta concorrência, a Gold pode ser publicada em um warehouse (Athena/Redshift Spectrum leem o mesmo parquet no S3 sem migração).

**Custo vs. Performance** — o pipeline prioriza custo: processamento em micro-lotes em vez de streaming contínuo provisionado, transformações em pandas (suficiente para 3,9 mi de linhas; Spark seria justificável apenas acima de dezenas de milhões), armazenamento colunar comprimido. A performance de consulta é garantida pelo particionamento, não por computação cara.

---

## 7. Monitoramento e FinOps

### Monitoramento

- **Local**: logs estruturados de execução em todas as etapas (entidade processada, volumetria, arquivos gerados), contagem de lotes/eventos no streaming, validações com relatório de aprovação/reprovação
- **Nuvem (ativo)**: CloudWatch Logs registra cada invocação do Lambda consumer (eventos processados, arquivos gravados); as métricas do Kinesis (`IncomingRecords`, `GetRecords.IteratorAgeMilliseconds`) medem volume e latência do stream; o trigger expõe `LastProcessingResult` para diagnóstico de falhas de ingestão
- Evolução: alarmes CloudWatch + SNS para notificação ativa de falhas

### FinOps

Decisões que reduzem custo operacional:

- **Parquet + particionamento** (`execution_date` + `ano`, nas três camadas — ver seção 4): leitura seletiva de partições reduz bytes escaneados — em Athena/BigQuery, custo é proporcional a bytes lidos
- **Dry run obrigatório antes da extração**: `download_bigquery.py` estima os bytes de cada consulta antes de executar e impõe `maximum_bytes_billed` como trava de custo (a extração completa processa ~260 MB, dentro do free tier de 1 TB/mês do BigQuery — custo real: R$ 0)
- **Cache de resultados**: re-execuções não repetem consultas (arquivos existentes são pulados)
- **Serverless por padrão**: Lambda e Kinesis cobram por uso; não há cluster ocioso. A janela de batching de 5s no trigger agrupa eventos e reduz invocações do Lambda
- **Ciclo de vida do armazenamento** (`infra/s3.tf`): a Bronze acumula uma partição por execução e nada expirava sozinho — com o agendamento semanal ligado, são ~52 cargas/ano crescendo de forma monotônica. A Lifecycle Policy move a Bronze para Standard-IA aos 30 dias, Glacier Instant Retrieval aos 90 e expira aos 730; a Silver esfria aos 90 dias; uploads multipart interrompidos são abortados em 7 dias. A Gold fica quente (é o que os dashboards leem). Prazos parametrizados em `infra/variables.tf`; racional em [ADR-004](docs/adr/ADR-004-ciclo-de-vida-armazenamento.md)
- **Custo real medido da arquitetura AWS no nosso volume**: S3 (~150 MB) + Kinesis (1 shard provisionado, ~US$ 0,02/h) + Lambda (invocações esporádicas no free tier) ≈ **menos de US$ 5/mês** — e o Terraform permite subir a infra só quando necessário e derrubar depois (`terraform destroy`, ou destroy direcionado do Kinesis, o único custo fixo relevante), zerando o custo ocioso. Os jobs Glue rodam em Python Shell (1 DPU), a fração de centavo por execução

---

## 8. Aplicação em IA

A camada Gold foi desenhada para alimentar diretamente casos de uso de inteligência artificial:

- **Modelos de predição de alfabetização**: `fato_aluno_alfabetizacao` (Silver) fornece 3,87 mi de observações com proficiência, presença, rede e território — base para prever risco de não-alfabetização por município/escola. Enriquecida com fontes externas (Censo Escolar, indicadores socioeconômicos do IBGE), suporta modelos de regressão/classificação com features contextuais
- **Análise de desigualdade educacional**: as distribuições por nível de proficiência (`fato_distribuicao_nivel_*`) permitem medir dispersão intra-UF e clusters de vulnerabilidade educacional (ex.: k-means sobre distância à meta + nível socioeconômico)
- **Políticas públicas baseadas em dados**: os rankings de priorização da Gold são o insumo direto para alocação de recursos do Compromisso Nacional — a evolução temporal permite avaliar efeito de intervenções (diferença-em-diferenças entre municípios priorizados e não priorizados)
- **Simulação de cenários até 2030**: `src/ml/simular_cenarios_2030.py` gera a tabela `gold.simulacao_alfabetizacao_2030`, cruzando o resultado municipal observado mais recente com as metas oficiais anuais. A saída compara cenários conservador, base e acelerado, calcula gap para a meta, probabilidade indicativa de atingimento e classe de risco territorial. Como a série observada ainda é curta, o uso recomendado é análise de cenários explicável, não previsão temporal definitiva.

```bash
python -m src.ml.simular_cenarios_2030
```

---

## 9. Tecnologias Utilizadas

| Tecnologia | Uso | Justificativa |
|---|---|---|
| Python 3.12 + pandas + pyarrow | Todo o pipeline | Stack padrão de dados; volume do projeto não justifica engine distribuída |
| Parquet | Armazenamento em todas as camadas | Colunar, comprimido, schema embutido; leitura seletiva de colunas/partições |
| BigQuery (Base dos Dados) | Fonte dos dados públicos | Dados INEP já estruturados e versionados; SQL padrão; free tier cobre o projeto |
| Jupyter Notebooks | Exploração e entendimento dos dados | Documentação executável — código, resultado e decisão no mesmo artefato; transformações Silver/Gold em produção rodam via `src/silver` e `src/gold` |
| Flask | Validadores visuais das camadas (`app/`) | Inspeção rápida dos parquets pelo navegador, sem depender de notebook |
| Git + GitHub (branches + PRs) | Versionamento e colaboração | Evolução rastreável do pipeline por feature branches e Pull Requests |
| AWS (S3, Kinesis, Lambda, Glue, EventBridge, SNS) | Data lake, streaming e pipeline batch em nuvem | Serverless, pay-per-use, aderente ao volume do projeto (ver seção FinOps) |
| Terraform | IaC de toda a infra AWS (`infra/`) | Infraestrutura reproduzível com um comando; recursos pré-existentes importados via `import` blocks |

---

## 10. Estrutura do Repositório

```text
.
├── app/                           # validadores/dashboards Flask (inspeção via navegador)
├── data/                          # data lake local (não versionado)
│   ├── bronze/                    #   brutos por entidade + partições execution_date
│   ├── silver/                    #   tabelas tratadas particionadas
│   ├── gold/                      #   datasets analíticos
│   └── streaming/                 #   fila de micro-lotes (simulação do stream)
├── docs/
│   ├── adr/                       # decisões arquiteturais registradas (ADR-001..004)
│   ├── crisp_dm.md                # abordagem CRISP-DM do projeto
│   ├── roteiro_video.md           # roteiro cronometrado do vídeo executivo
│   ├── catalogo_tabelas_camadas.md# descrição das tabelas Bronze, Silver e Gold
│   ├── dicionario_dados_bronze.md # perfil técnico das tabelas Bronze
│   ├── dicionario_dados_silver.md # dicionário das tabelas Silver
│   ├── dicionario_dados_gold.md   # dicionário das tabelas Gold
│   ├── evidencias/                # prints da execução em nuvem (S3, Kinesis, Lambda)
│   └── insumos_modelagem_bronze.md# chaves, relacionamentos e backlog
├── infra/                         # IaC Terraform de toda a infra AWS
│   ├── *.tf                       #   S3, Kinesis, Lambda, Glue, Scheduler, SNS
│   └── README.md                  #   apply, secret GCP, como plugar silver/gold
├── notebooks/
│   ├── 01_download_bronze_bigquery.ipynb    # espelha src/bronze/download_bigquery.py
│   ├── 01_entendimento_dados_bronze.ipynb
│   ├── 02_silver_transformacoes.ipynb       # exploração; a Silver "de verdade" roda via src/silver
│   ├── 03_quality_checks.ipynb
│   └── 04_gold_analitica.ipynb              # exploração; a Gold "de verdade" roda via src/gold
├── queries/bronze/                # SQL de extração (Base dos Dados)
├── src/
│   ├── aws/                       # upload do data lake para o S3
│   ├── bronze/                    # ingestão batch (leitura, gravação, download BigQuery)
│   ├── silver/                    # transformações Bronze -> Silver (dims, fatos, flags de qualidade)
│   ├── gold/                      # agregações Silver -> Gold (indicadores, rankings, evolução)
│   ├── qualidade/                 # regras, gate e histórico em gold.metricas_qualidade
│   ├── glue/                      # scripts dos jobs Glue (ingestão bronze na nuvem)
│   └── streaming/                 # producer, consumer local e consumer Lambda
├── tests/                         # testes do gate de qualidade (pytest)
├── main.py                        # pipeline completo: bronze -> silver -> gold
├── requirements.txt
└── .env.example
```

---

## 11. Como Executar

### Pré-requisitos

- Python 3.12+
- Conta Google Cloud com um projeto criado (só para a extração; free tier suficiente)

### Setup

```bash
# 1. Ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows | source .venv/bin/activate (Linux/Mac)

# 2. Dependências
pip install -r requirements.txt

# 3. Variáveis de ambiente
copy .env.example .env            # e preencha GCP_PROJECT_ID
```

### Pipeline batch

```bash
# 4. Extração da Base dos Dados (abre o navegador para login Google)
python -m src.bronze.download_bigquery              # use --somente-dry-run para só estimar custo

# 5. Pipeline completo: Bronze -> Silver -> Gold
python main.py
```

O gate de qualidade roda dentro do `main.py`: se uma regra bloqueante for
violada, a execução para com `QualidadeInsuficienteError` antes de publicar a
Silver, e as métricas ficam gravadas em `gold.metricas_qualidade` para
auditoria. Para investigar sem interromper, use `QUALIDADE_MODO=alertar`.

```bash
# Testes do gate e do histórico de qualidade
pytest tests/
```

Os notebooks `02_silver_transformacoes.ipynb` e `04_gold_analitica.ipynb` continuam no repositório para exploração/depuração passo a passo, mas não são mais o caminho de execução — `main.py` já roda as três camadas via `src/silver` e `src/gold`.

### Pipeline streaming — simulação local (dois terminais, sem AWS)

```bash
# Terminal 1 — consumer (inicie primeiro)
python -m src.streaming.consumer

# Terminal 2 — producer
python -m src.streaming.producer --total-eventos 1000 --tamanho-lote 100
```

O consumer encerra sozinho após ciclos consecutivos de fila vazia (configurável via `--max-ciclos-vazios`).

### Pipeline streaming — AWS

Com a infra provisionada (ver [infra/README.md](infra/README.md)) e `AWS_REGION`/`KINESIS_STREAM_NAME` no `.env`:

```bash
# Envia eventos reais ao Kinesis; o Lambda consome e grava no S3 automaticamente
python -m src.streaming.producer --destino kinesis --total-eventos 500

# Acompanhar o processamento
aws logs tail /aws/lambda/fiap-alfabetizacao-consumer --follow
```

### Upload do data lake para o S3

```bash
python -m src.aws.upload_s3 --dry-run    # lista o que seria enviado
python -m src.aws.upload_s3              # sobe bronze, silver e gold
```

### Pipeline batch — AWS (Glue Workflow)

Com o secret da service account GCP carregado (ver [infra/README.md](infra/README.md)):

```bash
# Dispara a ingestão bronze na nuvem (BigQuery -> S3); silver e gold
# entram no mesmo workflow quando as transformações forem plugadas
aws glue start-workflow-run --name fiap-alfabetizacao-pipeline
```

---

## 12. Metodologia

O projeto segue a abordagem **CRISP-DM** (entendimento do negócio → entendimento dos dados → preparação → modelagem → avaliação → implantação), documentada em [docs/crisp_dm.md](docs/crisp_dm.md). Os artefatos de entendimento e qualidade de cada etapa estão em `docs/`.

---

## 13. Próximos Passos

- [x] Provisionamento AWS via IaC (Terraform: S3 + Kinesis + Lambda + Glue + EventBridge + SNS) com evidências de execução
- [x] Monitoramento com CloudWatch (logs e métricas do stream/Lambda/Glue)
- [x] Alertas de falha de job Glue via EventBridge + SNS (e-mail)
- [x] Ingestão batch na nuvem (Glue Job `bronze-ingestao` + Glue Workflow + Scheduler)
- [x] Carregar a service account GCP no Secrets Manager e habilitar o agendamento
- [x] Plugar Silver (`src/silver`) e Gold (`src/gold`) 
- [x] Atualização do notebook de quality checks para a estrutura atual da Silver
- [x] Enriquecimento com fontes externas (Censo Escolar, IBGE) para os casos de uso de IA
- [x] Gate de qualidade bloqueante e histórico em `gold.metricas_qualidade` (ADR-002)
- [x] Governança da camada Gold: papel por tabela e consolidação das sobreposições (ADR-003)
- [x] Lifecycle Policy do S3 declarada no `s3.tf` (ADR-004) — falta `terraform apply`
- [x] Decisão multi-cloud (BigQuery x download direto) documentada com consequências (ADR-001)
- [x] Vídeo executivo (até 5 min) — roteiro cronometrado em [docs/roteiro_video.md](docs/roteiro_video.md)
