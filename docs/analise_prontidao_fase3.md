# Análise local da Fase 2 e preparação para a Fase 3

Análise de 07/09/2026. Fontes: PDFs das fases 2 e 3, código dos dois projetos,
sete extrações Bronze de 08/07/2026 e tabelas reprocessadas.

**Há volume suficiente para iniciar classificação supervisionada, mas a base
não é completa em cobertura territorial, temporal e variáveis.** O bloqueio
estrutural foi corrigido: agora existe `gold.base_modelagem_aluno`, com uma
observação por avaliação e alvo validado. Os arquivos brutos foram preservados.

## Requisitos dos PDFs

Fase 2, páginas 4–6: seis entidades educacionais, batch e streaming,
Bronze/Silver/Gold, qualidade e preparação para ML; integração externa opcional.
Cloud continua sendo exigência da fase; esta auditoria valida a execução local,
não revalida a implantação AWS.

Fase 3, páginas 2–5: **classificação de aluno alfabetizado ou não alfabetizado
com dados provenientes da Gold**, contexto educacional, territorial e
socioeconômico, EDA, tratamento de vazamento, pipeline de pré-processamento/modelo,
validação e interpretabilidade. Também menciona informações populacionais e
educacionais complementares. Não fixa mínimo de linhas, não exige todas as
fontes externas citadas como exemplos e não exige eliminar todas as ausências.

O projeto da Fase 3 existente foi inspecionado, mas não foi modificado nem
retreinado. Ele ainda lê Silver e precisa migrar para o
[contrato da nova Gold](base_modelagem_aluno.md).

## Dados efetivamente encontrados

| Medida | 2023 | 2024 |
|---|---:|---:|
| Registros de avaliação | 1.747.439 | 2.120.560 |
| Municípios nos microdados | 4.873 | 5.519 |
| Códigos escolares dentro da edição | 36.776 | 42.497 |
| UFs nos microdados | 23 | 26 |
| Ausentes | 244.381 | 267.772 |
| Presentes sem proficiência | 249 | 936 |
| Avaliações com alvo válido | 1.502.809 | 1.851.852 |
| Alvo válido: alfabetizado | 877.427 | 1.107.119 |
| Alvo válido: não alfabetizado | 625.382 | 744.733 |

Total: **3.867.999 registros**, dos quais **3.354.661** têm avaliação válida.
Nenhuma duplicata na chave composta da nova base. São registros de avaliação,
não uma contagem longitudinal de crianças únicas entre anos.

Em 2023 faltam AC, RR, SP e DF nos microdados; em 2024 falta RR. Não completar
com linhas artificiais. Metas/resultados agregados Brasil/UF incluem 2025, mas
isso não cria alunos de 2025. Metas até 2030 não são resultados observados.

O histórico municipal cobre **1.423.733 avaliações elegíveis de 2024 (76,882%)**.
Pagamentos Bolsa Família de 2023 cobrem **100%** das avaliações elegíveis de 2024.
Metas contextuais cobrem 95,330% no nível municipal, 98,253% em UF e 100% em
Brasil. Em 2023 não existe ano anterior local para essas features. Ausência
deve ser tratada por imputação aprendida no treino e relato de cobertura;
não significa zero.

## Problemas encontrados e correções

1. **Gold sem aluno individual.** Criada `base_modelagem_aluno`: alvo,
   elegibilidade, território, histórico municipal e Bolsa Família defasados,
   metas contextuais e anos de referência. Ausentes e presentes sem medição
   permanecem para auditoria, com alvo nulo.
2. **Resultados excluídos por falta de metas.** A junção preserva o resultado.
   Gold municipal: antes 5.232 linhas somente em 2024; agora 5.232 em 2023 e
   5.352 em 2024. Os 120 sem meta em 2024 continuam sinalizados. Em 2023 não
   existe meta para aquele ano. Gold UF preserva 27 linhas por ano, mas RR/2024
   continua sem resultado: contagem de linhas não prova cobertura da medição.
3. **Código escolar tratado como estável.** Dos 36.462 códigos comuns aos dois
   anos, **35.597 mudam de município**. O histórico escolar calculado pela
   Fase 3 anterior pode conectar escolas sem relação comprovada. Foi retirado
   da nova base. A dimensão escolar e sua junção Gold passaram a usar o ano,
   mantendo 79.273 vínculos escola/edição em vez de deduplicar anos juntos.
4. **Bolsa Família com nome enganoso.** O SQL faz `COUNT(1)` dos registros de
   pagamento. Na nova base, o campo se chama `total_pagamentos`, e o quociente
   monetário é valor médio por pagamento. Colunas legadas de dashboards/Silver
   ainda usam `beneficiarios` por compatibilidade; não interpretar como pessoas
   ou famílias únicas. Essa contagem não pode ser recuperada da soma agregada.
5. **Informações contemporâneas na previsão.** A nova base usa apenas o ano
   anterior para desempenho e Bolsa Família. A soma de pagamentos de todo 2024
   não existia no início de 2024. Metas ficam fora da lista padrão de features
   até comprovar a publicação antes do instante da previsão.
6. **Snapshots Bronze somados.** O leitor seleciona a extração batch completa
   mais recente, evitando misturar versões. Cada snapshot deve conter todo
   o histórico; não publicar coleta parcial como snapshot completo.

Reprocessamento não é coleta nova: foram reutilizadas extrações de 08/07/2026,
sem consulta BigQuery nem atualização remota dos microdados. As execuções
antigas permanecem para comparação. Leia a partição mais recente.

## O que acrescentar

| Prioridade | Enriquecimento | Integração e benefício |
|---|---|---|
| Alta | Censo Escolar: infraestrutura, urbano/rural, matrículas, docentes, turmas, tempo integral | Agregar por município/rede/ano e unir por código IBGE. Usar escola individual somente com correspondência validada dos identificadores. Acrescenta contexto educacional independente da prova. |
| Alta | IBGE: população municipal e população em idade escolar quando disponível | Município + ano de referência + publicação. Permite porte populacional real e indicadores por habitante. Alunos avaliados não são população. |
| Alta | Outra safra de microdados de alfabetização | Validar disponibilidade, esquema e comparabilidade. O portal oficial já lista resultados de 2025; o arquivo de microdados de 2025 não foi validado nesta análise. Permite teste temporal com histórico comparável. |
| Média | INSE e formação docente | Edição histórica publicada antes da previsão; grão municipal/rede enquanto não houver correspondência escolar. Acrescenta contexto socioeconômico e educacional. |
| Média | Bolsa Família/Cadastro Único mensal | Município + competência + unidade de contagem; contagem distinta na origem quando possível. Diferencia famílias, pessoas, pagamentos e meses cobertos. |
| Média | FUNDEB por rede e matrícula | Município/UF + ano anterior, natureza do recurso e denominador explícitos. A tabela `fato_fundeb` não existe neste lake, embora conste em documentação antiga. |
| Posterior | Renda, saneamento, escolaridade adulta, IDHM | Preservar ano censitário e grão. Não transformar indicador antigo em observações anuais novas. |

Fontes oficiais consultadas em 07/09/2026:

- [INEP: Censo Escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar).
- [IBGE: população para o TCU](https://www.ibge.gov.br/estatisticas/sociais/populacao/37734-relacao-da-populacao-dos-municipios-para-publicacao-no-tcu.html).
- [INEP: resultados de alfabetização](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/avaliacao-da-alfabetizacao/resultados).
- [INEP: resultados de 2024 e revisão das metas municipais em 23/09/2025](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/avaliacao-da-alfabetizacao/resultados/2024).

Esses enriquecimentos são recomendações; não foram baixados ou fabricados.
O lake atual não contém população, infraestrutura, renda individual, histórico
familiar ou atributos individuais adicionais.

## Limites da modelagem

A base permite iniciar uma **análise retrospectiva supervisionada**. Para
alegar previsão operacional em uma data real, é necessário reconstruir
disponibilidade e revisões das fontes naquela data. Ano anterior não garante
publicação anterior. Taxas históricas da nova base são não ponderadas;
comparações oficiais precisam respeitar pesos e população avaliada.

Não interpretar contexto como causa da alfabetização individual. Vários alunos
compartilham o mesmo vetor de atributos. Avaliar baseline, precisão/recall das
classes, F1 macro, ROC AUC e calibração, com separação por escola dentro da
edição e resultados desagregados por UF/rede.

Os resultados antigos da Fase 3 precisam ser recalculados após migração:
mudam elegibilidade, variáveis e junções. Não reutilizar métricas do README
antigo como evidência desta nova base.

## Execução local e evidências

Na raiz de `fiap-tech-challenge-fase2`:

```powershell
python -m pytest tests/ -q
python main.py
python -m src.qualidade.auditar_lake --saida docs/auditoria_lake.json
python app/gold_catalog.py
```

`main.py` reprocessa arquivos existentes. A coleta é separada:
`python -m src.bronze.download_bigquery`, com autenticação e projeto configurado.
Não apagar a única cópia Bronze antes de confirmar disponibilidade da coleta.

Streaming local exercitado com 500 eventos reais reemitidos em cinco lotes,
deduplicados contra batch; não representam 500 crianças adicionais.

Os testes cobrem vazamento contemporâneo, junções duplicadas, histórico
municipal, versão de metas, resultado sem meta, contagem regional e escola
por edição. O catálogo Flask respondeu HTTP 200 e mostrou a nova tabela.

Evidências: `docs/evidencias/logs/pipeline_local_2026-09-07.log`,
`docs/evidencias/logs/auditoria_local_2026-09-07.log`,
`docs/auditoria_antes.json` e `docs/auditoria_lake.json`
(JSONs locais ignorados pelo Git).

A aprovação do gate estrutural não significa dados completos. Permanecem
alertas da Silver de ausência e descarte na origem, além das lacunas acima.

Validação final: **20 testes passaram**, pipeline completo concluído e
191 métricas de qualidade persistidas. A Gold tem 3.867.999 linhas, sem
duplicatas na chave e sem ano de referência contemporâneo/futuro nas features
defasadas. A Silver registra quatro alertas: 120 registros municipais de 2023
sem chave/nível obrigatório, 22 metas UF sem campos obrigatórios e ausência
de medidas de distribuição por nível em aproximadamente 48% das linhas UF
e municipais. As flags e o log preservam essas limitações.
