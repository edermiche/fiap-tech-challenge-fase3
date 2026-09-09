# Contrato Gold para a Fase 3

Tabela: `gold.base_modelagem_aluno`. Papel: **serving para modelagem**.
Acrescenta grão individual, rótulo validado e atributos defasados; atende ao
critério de criação da ADR-003. Gerada automaticamente por `python main.py`.

O arquivo é particionado em `data/gold/base_modelagem_aluno/execution_date=YYYY-MM-DD/ano=YYYY/`.
Leia uma única execução completa; concatenar várias execuções duplica alunos.

| Campos | Uso e definição |
|---|---|
| `ano`, `id_municipio`, `id_escola`, `id_aluno`, `serie`, `rede` | Chave da observação de avaliação, validada sem nulos ou duplicatas. Não representa acompanhamento longitudinal da mesma criança. |
| `id_municipio_nome`, `sigla_uf`, `regiao_brasil` | Território. Código IBGE e nomes vêm do lake; não se inferem características familiares. |
| `alfabetizado_binario` | Alvo: 1 = Sim, 0 = Não. Nulo para quem não tem avaliação válida. |
| `elegivel_modelagem` | Presente, proficiência preenchida e não negativa, rótulo conhecido e coerente com o corte de 743. |
| `motivo_exclusao_modelagem` | Elegível, ausente, sem proficiência válida ou rótulo inconsistente. Uso de auditoria, nunca feature. |
| `taxa_alfabetizacao_municipio_anterior` | Percentual **não ponderado** entre avaliações válidas do ano anterior; não substitui o indicador oficial ponderado. |
| `alunos_avaliados_municipio_anterior` | Quantidade de avaliações válidas do ano anterior. Não é população municipal nem matrícula total do Censo Escolar. |
| `taxa_presenca_municipio_anterior` | Percentual de registros com presença na avaliação anterior; não é frequência escolar durante o ano letivo. |
| `total_pagamentos_bolsa_familia_anterior` | `COUNT(1)` anual da consulta de origem. Conta registros de pagamentos, não famílias ou beneficiários únicos. |
| `valor_total_bolsa_familia_anterior` | Soma em reais dos pagamentos da competência do ano anterior. |
| `valor_medio_pagamento_bolsa_familia_anterior` | Valor total dividido pelo número de pagamentos; nulo quando o denominador não é positivo. |
| `ano_referencia_historico_*`, `ano_referencia_bolsa_familia` | Ano de origem das medidas; sempre menor que o ano da avaliação. |
| `meta_alfabetizacao_{municipio,uf,brasil}` | Meta para o ano da observação, selecionada da versão com ano-base anterior mais recente. Uso contextual condicionado à comprovação da publicação. |
| `ano_base_meta_*`, `rede_meta_*` | Versão e abrangência: meta municipal refere-se à rede Municipal; estadual/nacional à Pública, mesmo que o aluno pertença à rede Estadual. |
| `tem_historico`, `tem_bolsa_familia_anterior` | Cobertura da junção. Ausência não é preenchida com zero. |
| `data_processamento_gold` | Data da execução. Não é data de publicação da fonte. |

## Consumo na Fase 3

Exemplo executado a partir da raiz da **Fase 2**:

```python
from pathlib import Path
from src.common.particionamento import ler_tabela_mais_recente
from src.gold.base_modelagem import FEATURES

base = ler_tabela_mais_recente(Path("data/gold/base_modelagem_aluno"))
treinavel = base.loc[base.elegivel_modelagem & base.ano.eq(2024)].copy()
X = treinavel[FEATURES]
y = treinavel["alfabetizado_binario"].astype("int8")
grupos = treinavel["id_escola"]
```

No repositório reconstruído `fiap-tech-challenge-fase3`, o comando
`python main.py tudo` lê esta Gold pelo módulo `src/preprocessing/base.py`.
O experimento inicial foi executado sobre 2024. A evolução com IBGE, Censo
Escolar e teste de 2025 usa uma tabela adicional, documentada em
[enriquecimento_ibge_censo.md](enriquecimento_ibge_censo.md).

Use a lista explícita `FEATURES` de `src/gold/base_modelagem.py`, nunca todas
as colunas exceto o alvo. Identificadores, motivos de exclusão e datas são apoio.
A Gold não fornece proficiência ou resultado contemporâneo agregado como preditores.
As metas ficam fora dessa lista até confirmar sua publicação antes do instante
de previsão. Há revisões posteriores documentadas pelo INEP.

Separe treino/validação/teste por escola; aprenda imputação e encoding apenas
no treino, dentro do pipeline sklearn. Uma divisão aleatória por aluno pode
colocar o mesmo contexto escolar dos dois lados. Avalie também por UF e rede.

O deslocamento anual evita usar medidas da mesma safra, mas **não prova a
disponibilidade em uma data exata**: as extrações atuais não preservam datas
históricas de publicação nem todas as revisões. Para simular uma decisão real,
defina uma data de corte e confira quando cada fonte foi divulgada. Não descreva
automaticamente esse experimento como previsão no primeiro dia de 2024.

As lacunas de 2023 são mantidas porque não há 2022 nessas fontes locais.
Em 2024, municípios que não participaram em 2023 terão histórico ausente.
Mais linhas do mesmo contexto não criam novas variáveis individuais.

**Não há histórico por escola nesta base.** Dos 36.462 códigos escolares nos
dois anos, 35.597 aparecem em municípios diferentes. Mesmo a coincidência de
código e município não comprova identidade longitudinal. A chave de
`silver.dim_escola` agora é `ano + id_escola`. Não cruze esse identificador
com o código INEP do Censo Escolar sem correspondência oficial validada.

## Verificação

```powershell
python -m pytest tests/ -q
python -m src.qualidade.auditar_lake --saida docs/auditoria_lake.json
```

Os testes cobrem ausência sem alvo, presente sem medição, limite de 743,
isolamento do resultado contemporâneo, defasagem de pagamentos, rejeição de
junções duplicadas, versão da meta e preservação de resultados sem metas.
