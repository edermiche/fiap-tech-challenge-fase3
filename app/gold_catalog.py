from pathlib import Path
from html import escape
from unicodedata import normalize

import pandas as pd
from flask import Flask, render_template_string, request, url_for

try:
    from app import mapa_brasil_metas as mapa
except ImportError:
    import mapa_brasil_metas as mapa


app = Flask(__name__)

BASE_PATH = Path(__file__).resolve().parents[1]
GOLD_PATH = BASE_PATH / "data" / "gold"


DESCRICOES_TABELAS = {
    "base_modelagem_aluno_enriquecida": {
        "nome": "Base de modelagem com IBGE e Censo Escolar - Fase 3",
        "descricao": (
            "Avaliacoes de 2023, 2024 e 2025 com populacao municipal e contexto "
            "do Censo Escolar por municipio/rede. Doze novos preditores. "
            "Consulte docs/enriquecimento_ibge_censo.md para cobertura e limites."
        ),
    },
    "base_modelagem_aluno": {
        "nome": "Base de modelagem por aluno - Fase 3",
        "descricao": (
            "Uma observacao por avaliacao: alvo binario, elegibilidade, territorio, "
            "historico municipal e pagamentos Bolsa Familia do ano anterior. "
            "Metas sao contexto; consulte docs/base_modelagem_aluno.md antes de treinar."
        ),
    },
    "metricas_qualidade": {
        "nome": "Metricas de qualidade por execucao",
        "descricao": (
            "Historico das regras de qualidade avaliadas a cada execucao do "
            "pipeline: camada, tabela, regra, registros violando, limite e "
            "status. E a tabela que responde se a qualidade piorou desde a "
            "safra anterior (ver docs/adr/ADR-002)."
        ),
    },
    "evolucao_meta_resultado_brasil": {
        "nome": "Evolucao metas x resultados Brasil",
        "descricao": (
            "Tabela unica de meta x resultado no nivel Brasil: comparacao com a "
            "meta e variacao anual na mesma serie (ver docs/adr/ADR-003)."
        ),
    },
    "evolucao_alfabetizacao": {
        "nome": "Evolucao da alfabetizacao",
        "descricao": (
            "Serie temporal consolidada com taxa media de alfabetizacao, "
            "percentual de participacao e variacoes anuais."
        ),
    },
    "evolucao_meta_resultado_municipio": {
        "nome": "Evolucao metas x resultados municipio",
        "descricao": (
            "Dashboard temporal para acompanhar resultado observado, meta, "
            "distancia da meta e variacao anual por municipio."
        ),
    },
    "evolucao_meta_resultado_uf": {
        "nome": "Evolucao metas x resultados UF",
        "descricao": (
            "Dashboard temporal para acompanhar resultado observado, meta, "
            "distancia da meta e variacao anual por estado."
        ),
    },
    "desigualdade_territorial_uf": {
        "nome": "Desigualdade territorial por UF",
        "descricao": (
            "Mede a dispersao dos resultados municipais dentro de cada UF, "
            "incluindo amplitude, desvio padrao e percentual abaixo da meta."
        ),
    },
    "indicador_meta_regiao": {
        "nome": "Indicador de meta por regiao",
        "descricao": (
            "Agrega resultado, meta e status por regiao brasileira para comparar "
            "desempenho territorial."
        ),
    },
    "indicador_meta_brasil": {
        "nome": "Indicador de meta Brasil",
        "descricao": (
            "Compara resultado observado e meta de alfabetizacao no nivel Brasil, "
            "calculando distancia da meta e status de cumprimento."
        ),
    },
    "indicador_alfabetizacao_municipio": {
        "nome": "Indicador de alfabetizacao por municipio",
        "descricao": (
            "Visao analitica municipal com resultado de alfabetizacao, meta, "
            "status de cumprimento, UF, nome do municipio, Bolsa Familia e "
            "rankings de prioridade."
        ),
    },
    "indicador_meta_municipio": {
        "nome": "Indicador de meta municipio",
        "descricao": (
            "Compara resultado observado e meta de alfabetizacao por municipio, "
            "calculando distancia da meta e status de cumprimento."
        ),
    },
    "indicador_meta_uf": {
        "nome": "Indicador de meta UF",
        "descricao": (
            "Compara resultado observado e meta de alfabetizacao por UF, "
            "calculando distancia da meta e status de cumprimento."
        ),
    },
    "indicador_presenca_avaliacao": {
        "nome": "Indicador de presenca na avaliacao",
        "descricao": (
            "Resumo de presenca e ausencia por municipio, UF, rede e serie, "
            "separando participacao de desempenho."
        ),
    },
    "indicador_desempenho_aluno": {
        "nome": "Indicadores de desempenho dos alunos",
        "descricao": (
            "Agrega proficiencia, alfabetizacao e presenca dos alunos por "
            "municipio, UF, rede e serie."
        ),
    },
    "meta_uf_bolsa_familia": {
        "nome": "Meta por UF x Bolsa Familia",
        "descricao": (
            "Cruza meta de alfabetizacao por estado com total de beneficiarios "
            "e valor pago pelo Bolsa Familia."
        ),
    },
    "meta_uf_fundeb": {
        "nome": "Meta por UF x FUNDEB",
        "descricao": (
            "Cruza meta de alfabetizacao por estado com valores recebidos do "
            "FUNDEB e ranking anual de verba."
        ),
    },
    "mapa_calor_territorial": {
        "nome": "Mapa de calor territorial",
        "descricao": (
            "Classifica municipios por risco territorial conforme distancia em "
            "pontos percentuais ate a meta."
        ),
    },
    "perfil_aluno_alfabetizacao": {
        "nome": "Perfil aluno alfabetizacao",
        "descricao": (
            "Distribui os alunos por ano, serie, rede, presenca e status de "
            "alfabetizacao, com media de proficiencia."
        ),
    },
    "distribuicao_desempenho_aluno": {
        "nome": "Distribuicao de desempenho dos alunos",
        "descricao": (
            "Distribui alunos por faixas de proficiencia, alfabetizacao, UF, "
            "rede e serie."
        ),
    },
    "ranking_municipio_prioritario": {
        "nome": "Ranking de municipios prioritarios",
        "descricao": (
            "Lista municipios abaixo da meta, ordenados pela maior distancia "
            "negativa em relacao ao objetivo."
        ),
    },
    "ranking_uf_prioritaria": {
        "nome": "Ranking de UFs prioritarias",
        "descricao": (
            "Lista UFs abaixo da meta, ordenadas pela maior distancia negativa "
            "em relacao ao objetivo."
        ),
    },
    "ranking_escolas_prioritarias": {
        "nome": "Ranking de escolas prioritarias",
        "descricao": (
            "Ordena escolas por maior percentual de alunos nao alfabetizados, "
            "com rankings nacional, por UF e por municipio."
        ),
    },
    "ranking_territorial_prioridade": {
        "nome": "Ranking territorial de prioridade",
        "descricao": (
            "Ranking de municipios abaixo da meta com posicoes no Brasil, na "
            "regiao e dentro da UF."
        ),
    },
    "resumo_status_meta": {
        "nome": "Resumo de status das metas",
        "descricao": (
            "Agregado por ano, nivel territorial e status da meta, usado para "
            "visao executiva de cumprimento das metas."
        ),
    },
}


DESCRICOES_COLUNAS = {
    "ano": "Ano de referencia do dado observado.",
    "rede": "Rede de ensino ou nivel administrativo.",
    "taxa_alfabetizacao": "Taxa observada de alfabetizacao.",
    "resultado_alfabetizacao": "Resultado observado de alfabetizacao.",
    "percentual_participacao": "Percentual de participacao no indicador.",
    "variacao_taxa": "Variacao da taxa de alfabetizacao em relacao ao ano anterior.",
    "variacao_percentual": "Variacao do percentual de participacao em relacao ao ano anterior.",
    "variacao_resultado_ano_anterior": "Variacao do resultado observado em relacao ao ano anterior.",
    "variacao_meta_ano_anterior": "Variacao da meta em relacao ao ano anterior.",
    "flag_taxa_alfabetizacao_valido": "Flag de qualidade da taxa de alfabetizacao.",
    "flag_percentual_participacao_valido": "Flag de qualidade do percentual de participacao.",
    "nivel_agregacao": "Nivel territorial do indicador.",
    "nivel_agregacao_resultado": "Nivel territorial do resultado observado.",
    "nivel_agregacao_meta": "Nivel territorial da meta.",
    "data_processamento_silver_resultado": "Data de processamento Silver do resultado.",
    "data_processamento_silver_meta": "Data de processamento Silver da meta.",
    "ano_meta": "Ano alvo da meta de alfabetizacao.",
    "meta_alfabetizacao": "Meta percentual de alfabetizacao.",
    "flag_meta_alfabetizacao_valido": "Flag de qualidade da meta de alfabetizacao.",
    "distancia_meta": "Diferenca entre taxa observada e meta de alfabetizacao.",
    "flag_meta_atingida": "Indica se a meta foi atingida.",
    "status_meta": "Classificacao do cumprimento da meta.",
    "id_municipio": "Codigo IBGE do municipio.",
    "id_municipio_nome": "Nome do municipio.",
    "serie": "Serie escolar analisada.",
    "nivel_alfabetizacao": "Nivel de alfabetizacao observado.",
    "media_portugues": "Media de proficiencia em Lingua Portuguesa.",
    "sigla_uf": "Sigla da Unidade Federativa.",
    "sigla_uf_nome": "Nome da Unidade Federativa.",
    "ranking": "Posicao no ranking de prioridade.",
    "ranking_prioridade_uf": "Posicao de prioridade do municipio dentro da UF.",
    "ranking_prioridade_brasil": "Posicao de prioridade do municipio no Brasil.",
    "total_beneficiarios_bolsa_familia": "Total anual de beneficiarios do Bolsa Familia no municipio.",
    "valor_total_bolsa_familia": "Valor anual pago pelo Bolsa Familia no municipio.",
    "total_fundeb": "Valor total do FUNDEB recebido pela UF.",
    "total_estado_df": "Parcela do FUNDEB referente ao estado ou Distrito Federal.",
    "total_municipios": "Parcela do FUNDEB referente aos municipios da UF.",
    "percentual_brasil": "Participacao da UF no total Brasil do FUNDEB.",
    "ranking_fundeb_ano": "Posicao da UF no ranking anual de valor do FUNDEB.",
    "ranking_meta_ano": "Posicao da UF no ranking anual de meta de alfabetizacao.",
    "total_beneficiarios_bolsa_familia": "Total anual de beneficiarios do Bolsa Familia.",
    "valor_total_bolsa_familia": "Valor anual pago pelo Bolsa Familia.",
    "total_municipios_com_bolsa_familia": "Quantidade de municipios da UF com dados do Bolsa Familia.",
    "ranking_beneficiarios_ano": "Posicao da UF no ranking anual de beneficiarios do Bolsa Familia.",
    "data_processamento_gold": "Data de processamento da camada Gold.",
    "quantidade": "Quantidade de registros agregados no grupo.",
    "nivel": "Nivel territorial do resumo.",
    "regiao_brasil": "Regiao brasileira.",
    "resultado_alfabetizacao_medio": "Media regional do resultado de alfabetizacao.",
    "meta_alfabetizacao_media": "Media regional da meta de alfabetizacao.",
    "distancia_media_meta": "Media da distancia entre resultado e meta.",
    "total_ufs": "Quantidade de UFs consideradas.",
    "total_meta_atingida": "Quantidade de territorios com meta atingida.",
    "total_abaixo_meta": "Quantidade de territorios abaixo da meta.",
    "total_sem_informacao": "Quantidade de territorios sem informacao de meta.",
    "percentual_meta_atingida": "Percentual de territorios com meta atingida.",
    "status_regiao": "Status consolidado da regiao.",
    "ranking_nacional": "Posicao no ranking nacional de prioridade.",
    "ranking_regiao": "Posicao no ranking regional de prioridade.",
    "ranking_uf": "Posicao no ranking de prioridade dentro da UF.",
    "resultado_medio_uf": "Media do resultado municipal dentro da UF.",
    "menor_resultado_municipal": "Menor resultado municipal observado na UF.",
    "maior_resultado_municipal": "Maior resultado municipal observado na UF.",
    "amplitude_resultado": "Diferenca entre maior e menor resultado municipal.",
    "desvio_padrao_resultado": "Desvio padrao dos resultados municipais da UF.",
    "meta_media_uf": "Media das metas municipais da UF.",
    "qtd_municipios": "Quantidade de municipios considerados.",
    "qtd_municipios_abaixo_meta": "Quantidade de municipios abaixo da meta.",
    "qtd_municipios_meta_atingida": "Quantidade de municipios com meta atingida.",
    "percentual_municipios_abaixo_meta": "Percentual de municipios abaixo da meta.",
    "classe_risco": "Classe de risco territorial conforme distancia da meta.",
    "cor_mapa": "Cor sugerida para visualizacao cartografica.",
    "presenca": "Indicador de presenca do aluno na avaliacao.",
    "alfabetizado": "Indica se o aluno foi classificado como alfabetizado.",
    "total_alunos": "Quantidade total de alunos.",
    "media_proficiencia": "Media de proficiencia dos alunos.",
    "percentual_alunos": "Percentual de alunos dentro do agrupamento.",
    "total_presentes": "Quantidade de alunos presentes.",
    "total_ausentes": "Quantidade de alunos ausentes.",
    "percentual_presentes": "Percentual de alunos presentes no agrupamento.",
    "percentual_presenca": "Percentual de presenca na avaliacao.",
    "percentual_ausencia": "Percentual de ausencia na avaliacao.",
    "media_proficiencia_presentes": "Media de proficiencia dos alunos presentes.",
    "id_escola": "Codigo identificador da escola.",
    "total_alfabetizados": "Quantidade de alunos alfabetizados.",
    "total_nao_alfabetizados": "Quantidade de alunos nao alfabetizados.",
    "percentual_nao_alfabetizado": "Percentual de alunos nao alfabetizados.",
    "ranking_municipio": "Posicao da escola no ranking do municipio.",
    "mediana_proficiencia": "Mediana de proficiencia dos alunos.",
    "menor_proficiencia": "Menor proficiencia observada.",
    "maior_proficiencia": "Maior proficiencia observada.",
    "desvio_padrao_proficiencia": "Desvio padrao da proficiencia dos alunos.",
    "percentual_alfabetizado": "Percentual de alunos alfabetizados.",
    "faixa_proficiencia": "Faixa de proficiencia do aluno.",
    "data_execucao": "Data da execucao do pipeline que gerou a metrica.",
    "camada": "Camada avaliada pela regra de qualidade.",
    "tabela": "Tabela avaliada pela regra de qualidade.",
    "regra": "Regra de qualidade aplicada.",
    "escopo": "Recorte avaliado pela regra, quando existe (ex.: ano=2024).",
    "registros_avaliados": "Total de registros avaliados pela regra.",
    "registros_violando": "Registros que violaram a regra.",
    "percentual_violacao": "Percentual de registros em violacao.",
    "limite_bloqueio": "Percentual a partir do qual a regra barra a execucao.",
    "severidade": "Severidade da regra: bloqueante ou alerta.",
    "status": "Resultado da avaliacao: ok, alerta ou bloqueio.",
}


FILTROS_POR_TABELA = {
    "evolucao_meta_resultado_brasil": ["ano", "ano_meta", "rede", "status_meta"],
    "metricas_qualidade": [
        "data_execucao",
        "camada",
        "tabela",
        "regra",
        "escopo",
        "status",
    ],
    "evolucao_meta_resultado_municipio": [
        "ano",
        "ano_meta",
        "sigla_uf",
        "rede",
        "status_meta",
        "id_municipio_nome",
        "id_municipio",
    ],
    "evolucao_meta_resultado_uf": [
        "ano",
        "ano_meta",
        "sigla_uf",
        "rede",
        "status_meta",
    ],
    "desigualdade_territorial_uf": [
        "ano",
        "ano_meta",
        "regiao_brasil",
        "sigla_uf",
        "rede",
    ],
    "indicador_meta_regiao": [
        "ano",
        "ano_meta",
        "regiao_brasil",
        "rede",
        "status_regiao",
    ],
    "indicador_alfabetizacao_municipio": [
        "ano",
        "ano_meta",
        "sigla_uf",
        "rede",
        "status_meta",
        "id_municipio_nome",
        "id_municipio",
    ],
    "indicador_meta_municipio": [
        "ano",
        "ano_meta",
        "rede",
        "status_meta",
        "id_municipio_nome",
        "id_municipio",
    ],
    "indicador_meta_uf": ["ano", "ano_meta", "sigla_uf", "rede", "status_meta"],
    "indicador_meta_brasil": ["ano", "ano_meta", "rede", "status_meta"],
    "indicador_presenca_avaliacao": [
        "ano",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "serie",
        "id_municipio_nome",
        "id_municipio",
    ],
    "indicador_desempenho_aluno": [
        "ano",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "serie",
        "id_municipio_nome",
        "id_municipio",
    ],
    "meta_uf_bolsa_familia": [
        "ano",
        "ano_meta",
        "sigla_uf",
        "rede",
        "status_meta",
    ],
    "meta_uf_fundeb": [
        "ano",
        "ano_meta",
        "sigla_uf",
        "rede",
        "status_meta",
    ],
    "mapa_calor_territorial": [
        "ano",
        "ano_meta",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "status_meta",
        "classe_risco",
        "id_municipio_nome",
        "id_municipio",
    ],
    "perfil_aluno_alfabetizacao": [
        "ano",
        "serie",
        "rede",
        "presenca",
        "alfabetizado",
    ],
    "distribuicao_desempenho_aluno": [
        "ano",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "serie",
        "faixa_proficiencia",
        "alfabetizado",
    ],
    "ranking_municipio_prioritario": ["ano", "id_municipio_nome", "id_municipio"],
    "ranking_escolas_prioritarias": [
        "ano",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "serie",
        "id_municipio_nome",
        "id_municipio",
        "id_escola",
    ],
    "ranking_uf_prioritaria": ["ano", "sigla_uf"],
    "ranking_territorial_prioridade": [
        "ano",
        "ano_meta",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "id_municipio_nome",
        "id_municipio",
    ],
    "resumo_status_meta": ["ano", "nivel", "nivel_agregacao", "rede", "status_meta"],
    "evolucao_alfabetizacao": ["ano", "rede", "nivel_agregacao"],
}


ROTULOS_FILTROS = {
    "ano": "Ano",
    "data_execucao": "Execucao",
    "camada": "Camada",
    "tabela": "Tabela",
    "regra": "Regra",
    "escopo": "Escopo",
    "status": "Status",
    "ano_meta": "Ano meta",
    "sigla_uf": "UF",
    "rede": "Rede",
    "status_meta": "Status",
    "nivel": "Nivel",
    "nivel_agregacao": "Agregacao",
    "id_municipio": "Codigo municipio",
    "id_municipio_nome": "Municipio",
}


COLUNAS_SEM_FILTRO_AUTOMATICO = {
    "taxa_alfabetizacao",
    "resultado_alfabetizacao",
    "percentual_participacao",
    "variacao_taxa",
    "variacao_percentual",
    "variacao_resultado_ano_anterior",
    "variacao_meta_ano_anterior",
    "meta_alfabetizacao",
    "distancia_meta",
    "media_portugues",
    "total_beneficiarios_bolsa_familia",
    "valor_total_bolsa_familia",
    "total_fundeb",
    "total_estado_df",
    "total_municipios",
    "percentual_brasil",
    "ranking_fundeb_ano",
    "ranking_meta_ano",
    "total_municipios_com_bolsa_familia",
    "ranking_beneficiarios_ano",
    "quantidade",
    "total_registros",
    "percentual_registros",
    "resultado_alfabetizacao_medio",
    "meta_alfabetizacao_media",
    "distancia_media_meta",
    "total_ufs",
    "total_meta_atingida",
    "total_abaixo_meta",
    "total_sem_informacao",
    "percentual_meta_atingida",
    "ranking_nacional",
    "ranking_regiao",
    "ranking_uf",
    "resultado_medio_uf",
    "menor_resultado_municipal",
    "maior_resultado_municipal",
    "amplitude_resultado",
    "desvio_padrao_resultado",
    "meta_media_uf",
    "qtd_municipios",
    "qtd_municipios_abaixo_meta",
    "qtd_municipios_meta_atingida",
    "percentual_municipios_abaixo_meta",
    "cor_mapa",
    "total_alunos",
    "media_proficiencia",
    "percentual_alunos",
    "total_presentes",
    "total_ausentes",
    "percentual_presentes",
    "percentual_presenca",
    "percentual_ausencia",
    "media_proficiencia_presentes",
    "total_alfabetizados",
    "total_nao_alfabetizados",
    "percentual_nao_alfabetizado",
    "percentual_alfabetizado",
    "mediana_proficiencia",
    "menor_proficiencia",
    "maior_proficiencia",
    "desvio_padrao_proficiencia",
    "ranking_municipio",
    "flag_taxa_alfabetizacao_valido",
    "flag_percentual_participacao_valido",
    "flag_meta_alfabetizacao_valido",
    "flag_meta_atingida",
    "data_processamento_silver",
    "data_processamento_silver_resultado",
    "data_processamento_silver_meta",
    "data_processamento_gold",
}


# As tabelas evolucao_* consolidaram as antigas comparacao_* (ADR-003):
# a mesma tabela alimenta o grafico de comparacao com a meta e o de serie
# temporal, porque as colunas de variacao anual sao um acrescimo, nao uma
# tabela nova.
TABELAS_COM_GRAFICO_COMPARACAO = {
    "evolucao_meta_resultado_brasil",
    "evolucao_meta_resultado_municipio",
    "evolucao_meta_resultado_uf",
}


TABELAS_COM_GRAFICO_EVOLUCAO = {
    "evolucao_meta_resultado_municipio",
    "evolucao_meta_resultado_uf",
}


TABELAS_COM_GRAFICO_EXTERNO = {
    "meta_uf_bolsa_familia": {
        "metrica": "total_beneficiarios_bolsa_familia",
        "rotulo": "Beneficiarios",
    },
    "meta_uf_fundeb": {
        "metrica": "total_fundeb",
        "rotulo": "FUNDEB",
    },
}


TABELAS_VERIFICACAO_GOLD = {
    "meta_uf_bolsa_familia",
    "meta_uf_fundeb",
}


TABELAS_DADOS_TERRITORIAIS = {
    "desigualdade_territorial_uf",
    "indicador_meta_regiao",
    "mapa_calor_territorial",
    "ranking_territorial_prioridade",
}


TABELAS_MICRODADOS_EDUCACIONAIS = {
    "distribuicao_desempenho_aluno",
    "indicador_desempenho_aluno",
    "indicador_presenca_avaliacao",
    "perfil_aluno_alfabetizacao",
    "ranking_escolas_prioritarias",
}


def localizar_parquet_mais_recente(caminho_tabela: Path) -> Path | None:
    arquivos = list(caminho_tabela.rglob("*.parquet"))

    if not arquivos:
        return None

    return max(arquivos, key=lambda arquivo: arquivo.stat().st_mtime)


def localizar_execucao_mais_recente(caminho_tabela: Path) -> Path | None:
    if not caminho_tabela.exists():
        return None

    execucoes = [
        caminho
        for caminho in caminho_tabela.iterdir()
        if caminho.is_dir() and caminho.name.startswith("execution_date=")
    ]

    if not execucoes:
        return None

    return max(execucoes, key=lambda caminho: caminho.name)


def listar_parquets_execucao(caminho_execucao: Path) -> list[Path]:
    arquivos_particionados = sorted(
        arquivo
        for pasta_ano in caminho_execucao.glob("ano=*")
        if pasta_ano.is_dir()
        for arquivo in pasta_ano.glob("*.parquet")
    )

    return arquivos_particionados or sorted(caminho_execucao.glob("*.parquet"))


def listar_tabelas_gold() -> list[str]:
    if not GOLD_PATH.exists():
        return []

    tabelas = []
    for caminho in sorted(GOLD_PATH.iterdir()):
        if caminho.is_dir() and localizar_parquet_mais_recente(caminho):
            tabelas.append(caminho.name)

    return tabelas


def carregar_gold(nome_tabela: str) -> tuple[pd.DataFrame, Path]:
    execucao = localizar_execucao_mais_recente(GOLD_PATH / nome_tabela)

    if execucao is None:
        raise FileNotFoundError(f"Nenhuma execucao encontrada para gold.{nome_tabela}")

    arquivos = listar_parquets_execucao(execucao)
    if not arquivos:
        raise FileNotFoundError(f"Nenhum parquet encontrado para gold.{nome_tabela}")

    df = pd.concat([pd.read_parquet(arquivo) for arquivo in arquivos], ignore_index=True)

    return df, execucao


def formatar_valor(valor):
    if pd.isna(valor):
        return "-"

    if isinstance(valor, float):
        return round(valor, 4)

    return valor


def normalizar_busca(valor: str) -> str:
    texto = normalize("NFKD", str(valor))
    texto = "".join(caractere for caractere in texto if not caractere.encode("ascii", "ignore") == b"")
    return texto.casefold()


def montar_dicionario_colunas(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for coluna in df.columns:
        serie = df[coluna]
        exemplo = "-"
        valores_validos = serie.dropna()
        if not valores_validos.empty:
            exemplo = formatar_valor(valores_validos.iloc[0])

        linhas.append(
            {
                "coluna": coluna,
                "tipo": str(serie.dtype),
                "nulos": int(serie.isna().sum()),
                "% nulos": round((serie.isna().mean() * 100), 2),
                "distintos": int(serie.nunique(dropna=True)),
                "exemplo": exemplo,
                "descricao": DESCRICOES_COLUNAS.get(coluna, "Campo analitico da tabela Gold."),
            }
        )

    return pd.DataFrame(linhas)


def montar_filtros(tabela: str, df: pd.DataFrame) -> list[dict]:
    filtros = []
    colunas_filtro = [
        coluna
        for coluna in FILTROS_POR_TABELA.get(tabela, [])
        if coluna in df.columns
    ]

    for coluna in df.columns:
        if coluna in colunas_filtro or coluna in COLUNAS_SEM_FILTRO_AUTOMATICO:
            continue

        qtd_distintos = df[coluna].nunique(dropna=True)
        if qtd_distintos <= 80:
            colunas_filtro.append(coluna)

    for coluna in colunas_filtro:
        valor_atual = request.args.get(f"f_{coluna}", "").strip()
        valores = (
            df[coluna]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        tipo = "select"
        if coluna in {"id_municipio", "id_municipio_nome"} or len(valores) > 80:
            tipo = "text"
            valores = []

        filtros.append(
            {
                "coluna": coluna,
                "nome": f"f_{coluna}",
                "rotulo": ROTULOS_FILTROS.get(coluna, coluna),
                "tipo": tipo,
                "valor": valor_atual,
                "valores": valores,
                "placeholder": "Digite para buscar",
            }
        )

    return filtros


def aplicar_filtros(df: pd.DataFrame, filtros: list[dict]) -> pd.DataFrame:
    df_filtrado = df.copy()

    for filtro in filtros:
        valor = filtro["valor"]
        coluna = filtro["coluna"]

        if not valor:
            continue

        serie = df_filtrado[coluna].astype(str)
        if filtro["tipo"] == "text":
            busca = normalizar_busca(valor)
            serie_normalizada = serie.map(normalizar_busca)
            df_filtrado = df_filtrado[serie_normalizada.str.contains(busca, na=False)]
        else:
            df_filtrado = df_filtrado[serie == valor]

    return df_filtrado


def preparar_tabela_html(df: pd.DataFrame, limite: int) -> str:
    df_preview = df.head(limite).map(formatar_valor)
    return df_preview.to_html(index=False, classes="data-table")


def montar_rotulo_grafico(linha: pd.Series) -> str:
    partes = []

    for coluna in ["id_municipio_nome", "sigla_uf", "nivel_agregacao", "rede"]:
        if coluna in linha.index and pd.notna(linha[coluna]):
            valor = str(linha[coluna])
            if valor and valor not in partes:
                partes.append(valor)

    if "ano" in linha.index and pd.notna(linha["ano"]):
        partes.append(str(linha["ano"]))

    return " - ".join(partes) or "Registro"


def montar_grafico_comparacao(df: pd.DataFrame, limite: int) -> str:
    colunas_necessarias = {"resultado_alfabetizacao", "meta_alfabetizacao"}
    if df.empty or not colunas_necessarias.issubset(df.columns):
        return ""

    df_grafico = df.head(limite).copy()
    maximo = max(
        df_grafico["resultado_alfabetizacao"].max(skipna=True),
        df_grafico["meta_alfabetizacao"].max(skipna=True),
        100,
    )

    linhas = []
    for _, linha in df_grafico.iterrows():
        resultado = linha.get("resultado_alfabetizacao")
        meta = linha.get("meta_alfabetizacao")
        resultado_num = 0 if pd.isna(resultado) else float(resultado)
        meta_num = 0 if pd.isna(meta) else float(meta)
        resultado_largura = min(max((resultado_num / maximo) * 100, 0), 100)
        meta_largura = min(max((meta_num / maximo) * 100, 0), 100)
        status = str(linha.get("status_meta", ""))

        linhas.append(
            f"""
            <div class="chart-row">
                <div class="chart-label">
                    <strong>{escape(montar_rotulo_grafico(linha))}</strong>
                    <span>{escape(status)}</span>
                </div>
                <div class="chart-bars">
                    <div class="bar-line">
                        <span>Resultado</span>
                        <div class="bar-track">
                            <div class="bar-fill result" style="width: {resultado_largura:.2f}%"></div>
                        </div>
                        <strong>{resultado_num:.2f}</strong>
                    </div>
                    <div class="bar-line">
                        <span>Meta</span>
                        <div class="bar-track">
                            <div class="bar-fill target" style="width: {meta_largura:.2f}%"></div>
                        </div>
                        <strong>{meta_num:.2f}</strong>
                    </div>
                </div>
            </div>
            """
        )

    return "\n".join(linhas)


def montar_grafico_evolucao(df: pd.DataFrame, limite: int) -> str:
    colunas_necessarias = {"ano", "resultado_alfabetizacao", "meta_alfabetizacao"}
    if df.empty or not colunas_necessarias.issubset(df.columns):
        return ""

    ordenar = [
        coluna
        for coluna in ["sigla_uf", "id_municipio_nome", "id_municipio", "rede", "ano"]
        if coluna in df.columns
    ]
    df_grafico = df.sort_values(ordenar).head(limite).copy() if ordenar else df.head(limite).copy()
    maximo = max(
        df_grafico["resultado_alfabetizacao"].max(skipna=True),
        df_grafico["meta_alfabetizacao"].max(skipna=True),
        100,
    )

    linhas = []
    for _, linha in df_grafico.iterrows():
        resultado = linha.get("resultado_alfabetizacao")
        meta = linha.get("meta_alfabetizacao")
        resultado_num = 0 if pd.isna(resultado) else float(resultado)
        meta_num = 0 if pd.isna(meta) else float(meta)
        resultado_largura = min(max((resultado_num / maximo) * 100, 0), 100)
        meta_largura = min(max((meta_num / maximo) * 100, 0), 100)
        variacao_resultado = linha.get("variacao_resultado_ano_anterior")
        variacao_meta = linha.get("variacao_meta_ano_anterior")
        status = str(linha.get("status_meta", ""))
        detalhes = []

        if pd.notna(variacao_resultado):
            detalhes.append(f"Var. resultado: {float(variacao_resultado):+.2f}")
        if pd.notna(variacao_meta):
            detalhes.append(f"Var. meta: {float(variacao_meta):+.2f}")
        if status:
            detalhes.append(status)

        linhas.append(
            f"""
            <div class="chart-row">
                <div class="chart-label">
                    <strong>{escape(montar_rotulo_grafico(linha))}</strong>
                    <span>{escape(' | '.join(detalhes))}</span>
                </div>
                <div class="chart-bars">
                    <div class="bar-line">
                        <span>Resultado</span>
                        <div class="bar-track">
                            <div class="bar-fill result" style="width: {resultado_largura:.2f}%"></div>
                        </div>
                        <strong>{resultado_num:.2f}</strong>
                    </div>
                    <div class="bar-line">
                        <span>Meta</span>
                        <div class="bar-track">
                            <div class="bar-fill target" style="width: {meta_largura:.2f}%"></div>
                        </div>
                        <strong>{meta_num:.2f}</strong>
                    </div>
                </div>
            </div>
            """
        )

    return "\n".join(linhas)


def montar_grafico_externo(df: pd.DataFrame, limite: int, metrica: str, rotulo: str) -> str:
    colunas_necessarias = {metrica, "meta_alfabetizacao"}
    if df.empty or not colunas_necessarias.issubset(df.columns):
        return ""

    ordenar = []
    if "ano" in df.columns:
        ordenar.append("ano")
    if metrica in df.columns:
        ordenar.append(metrica)

    df_grafico = df.sort_values(ordenar, ascending=[True, False][:len(ordenar)]).head(limite).copy()
    max_metrica = max(df_grafico[metrica].max(skipna=True), 1)
    max_meta = max(df_grafico["meta_alfabetizacao"].max(skipna=True), 100)

    linhas = []
    for _, linha in df_grafico.iterrows():
        valor_metrica = linha.get(metrica)
        meta = linha.get("meta_alfabetizacao")
        valor_metrica_num = 0 if pd.isna(valor_metrica) else float(valor_metrica)
        meta_num = 0 if pd.isna(meta) else float(meta)
        metrica_largura = min(max((valor_metrica_num / max_metrica) * 100, 0), 100)
        meta_largura = min(max((meta_num / max_meta) * 100, 0), 100)
        status = str(linha.get("status_meta", ""))
        ranking = linha.get("ranking_fundeb_ano", linha.get("ranking_beneficiarios_ano", ""))
        detalhe = status
        if pd.notna(ranking) and ranking != "":
            detalhe = f"{status} | Ranking: {ranking}"

        linhas.append(
            f"""
            <div class="chart-row">
                <div class="chart-label">
                    <strong>{escape(montar_rotulo_grafico(linha))}</strong>
                    <span>{escape(detalhe)}</span>
                </div>
                <div class="chart-bars">
                    <div class="bar-line">
                        <span>{escape(rotulo)}</span>
                        <div class="bar-track">
                            <div class="bar-fill external" style="width: {metrica_largura:.2f}%"></div>
                        </div>
                        <strong>{valor_metrica_num:,.0f}</strong>
                    </div>
                    <div class="bar-line">
                        <span>Meta</span>
                        <div class="bar-track">
                            <div class="bar-fill target" style="width: {meta_largura:.2f}%"></div>
                        </div>
                        <strong>{meta_num:.2f}</strong>
                    </div>
                </div>
            </div>
            """
        )

    return "\n".join(linhas)


def montar_grafico_territorial(tabela: str, df: pd.DataFrame, limite: int) -> str:
    if df.empty:
        return ""

    if tabela == "mapa_calor_territorial" and "classe_risco" in df.columns:
        df_grafico = (
            df.groupby("classe_risco", as_index=False)
            .size()
            .rename(columns={"size": "quantidade"})
            .sort_values("quantidade", ascending=False)
        )
        metrica = "quantidade"
        rotulo = "Municipios"
        label_col = "classe_risco"
    elif tabela == "desigualdade_territorial_uf" and "amplitude_resultado" in df.columns:
        df_grafico = df.sort_values("amplitude_resultado", ascending=False).head(limite)
        metrica = "amplitude_resultado"
        rotulo = "Amplitude"
        label_col = "sigla_uf"
    elif tabela == "ranking_territorial_prioridade" and "distancia_meta" in df.columns:
        df_grafico = df.sort_values("ranking_nacional").head(limite).copy()
        df_grafico["distancia_abs"] = df_grafico["distancia_meta"].abs()
        metrica = "distancia_abs"
        rotulo = "Distancia"
        label_col = "id_municipio_nome"
    elif tabela == "indicador_meta_regiao" and "distancia_media_meta" in df.columns:
        df_grafico = df.sort_values("distancia_media_meta").head(limite).copy()
        df_grafico["distancia_abs"] = df_grafico["distancia_media_meta"].abs()
        metrica = "distancia_abs"
        rotulo = "Distancia media"
        label_col = "regiao_brasil"
    else:
        return ""

    maximo = max(df_grafico[metrica].max(skipna=True), 1)
    linhas = []

    for _, linha in df_grafico.iterrows():
        valor = linha.get(metrica)
        valor_num = 0 if pd.isna(valor) else float(valor)
        largura = min(max((valor_num / maximo) * 100, 0), 100)
        label = str(linha.get(label_col, "Territorio"))
        detalhe = []
        for coluna in ["ano", "regiao_brasil", "sigla_uf", "status_meta", "status_regiao"]:
            if coluna in linha.index and pd.notna(linha[coluna]):
                detalhe.append(str(linha[coluna]))

        linhas.append(
            f"""
            <div class="chart-row">
                <div class="chart-label">
                    <strong>{escape(label)}</strong>
                    <span>{escape(' | '.join(detalhe))}</span>
                </div>
                <div class="chart-bars">
                    <div class="bar-line">
                        <span>{escape(rotulo)}</span>
                        <div class="bar-track">
                            <div class="bar-fill territorial" style="width: {largura:.2f}%"></div>
                        </div>
                        <strong>{valor_num:,.2f}</strong>
                    </div>
                </div>
            </div>
            """
        )

    return "\n".join(linhas)


def montar_grafico_microdados(tabela: str, df: pd.DataFrame, limite: int) -> str:
    if df.empty:
        return ""

    if tabela == "perfil_aluno_alfabetizacao":
        df_grafico = df.sort_values("total_alunos", ascending=False).head(limite)
        metrica = "total_alunos"
        rotulo = "Alunos"
        label_cols = ["rede", "presenca", "alfabetizado"]
    elif tabela == "indicador_presenca_avaliacao":
        df_grafico = df.sort_values("percentual_ausencia", ascending=False).head(limite)
        metrica = "percentual_ausencia"
        rotulo = "Ausencia"
        label_cols = ["id_municipio_nome", "sigla_uf", "rede"]
    elif tabela == "ranking_escolas_prioritarias":
        df_grafico = df.sort_values("ranking_nacional").head(limite)
        metrica = "percentual_nao_alfabetizado"
        rotulo = "Nao alfabet."
        label_cols = ["id_escola", "id_municipio_nome", "sigla_uf"]
    elif tabela == "indicador_desempenho_aluno":
        df_grafico = df.sort_values("media_proficiencia", ascending=False).head(limite)
        metrica = "media_proficiencia"
        rotulo = "Proficiencia"
        label_cols = ["id_municipio_nome", "sigla_uf", "rede"]
    elif tabela == "distribuicao_desempenho_aluno":
        df_grafico = df.sort_values("total_alunos", ascending=False).head(limite)
        metrica = "total_alunos"
        rotulo = "Alunos"
        label_cols = ["faixa_proficiencia", "alfabetizado", "sigla_uf"]
    else:
        return ""

    maximo = max(df_grafico[metrica].max(skipna=True), 1)
    linhas = []

    for _, linha in df_grafico.iterrows():
        valor = linha.get(metrica)
        valor_num = 0 if pd.isna(valor) else float(valor)
        largura = min(max((valor_num / maximo) * 100, 0), 100)
        label = " - ".join(
            str(linha[coluna])
            for coluna in label_cols
            if coluna in linha.index and pd.notna(linha[coluna])
        )
        detalhe = []
        for coluna in ["ano", "serie", "ranking_nacional", "total_alunos"]:
            if coluna in linha.index and pd.notna(linha[coluna]):
                detalhe.append(f"{coluna}: {linha[coluna]}")

        linhas.append(
            f"""
            <div class="chart-row">
                <div class="chart-label">
                    <strong>{escape(label or 'Microdados')}</strong>
                    <span>{escape(' | '.join(detalhe))}</span>
                </div>
                <div class="chart-bars">
                    <div class="bar-line">
                        <span>{escape(rotulo)}</span>
                        <div class="bar-track">
                            <div class="bar-fill microdata" style="width: {largura:.2f}%"></div>
                        </div>
                        <strong>{valor_num:,.2f}</strong>
                    </div>
                </div>
            </div>
            """
        )

    return "\n".join(linhas)


HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catalogo Gold</title>
    <style>
        :root {
            --bg: #f5f7fa;
            --panel: #ffffff;
            --text: #1f2933;
            --muted: #607080;
            --line: #d8dee6;
            --accent: #176b87;
            --accent-soft: #e7f2f5;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: Arial, Helvetica, sans-serif;
        }

        .layout {
            display: grid;
            grid-template-columns: 300px minmax(0, 1fr);
            min-height: 100vh;
        }

        aside {
            border-right: 1px solid var(--line);
            background: var(--panel);
            padding: 20px 16px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow: auto;
        }

        main {
            padding: 24px;
            min-width: 0;
        }

        h1,
        h2,
        h3 {
            margin: 0;
        }

        .brand {
            margin-bottom: 18px;
        }

        .brand h1 {
            font-size: 22px;
            margin-bottom: 4px;
        }

        .brand p,
        .subtitle,
        .muted {
            color: var(--muted);
            margin: 0;
            line-height: 1.45;
        }

        .menu {
            display: grid;
            gap: 8px;
        }

        .menu-section {
            margin: 18px 0 8px;
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .menu a {
            display: block;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px 12px;
            color: var(--text);
            text-decoration: none;
            background: #fff;
        }

        .menu a.active {
            border-color: var(--accent);
            background: var(--accent-soft);
            font-weight: 700;
        }

        .menu a.dashboard-link {
            border-color: var(--accent);
            background: var(--accent);
            color: #fff;
        }

        .menu a.dashboard-link .table-name {
            color: rgba(255, 255, 255, .82);
        }

        .table-name {
            display: block;
            color: var(--muted);
            font-size: 12px;
            font-weight: 400;
            margin-top: 2px;
            word-break: break-word;
        }

        .header {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: start;
            margin-bottom: 18px;
        }

        .actions {
            display: flex;
            gap: 8px;
            align-items: end;
        }

        label {
            display: grid;
            gap: 6px;
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }

        input,
        select,
        button {
            min-height: 38px;
            border-radius: 6px;
            border: 1px solid var(--line);
            background: #fff;
            color: var(--text);
            padding: 8px 10px;
            font-size: 14px;
        }

        select {
            min-width: 150px;
        }

        button {
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
            font-weight: 700;
            cursor: pointer;
        }

        .filters {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 16px;
        }

        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px;
            align-items: end;
        }

        .filter-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .secondary-link {
            min-height: 38px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 8px 10px;
            color: var(--text);
            text-decoration: none;
            background: #fff;
            font-size: 14px;
            font-weight: 700;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
            overflow: hidden;
            margin-bottom: 16px;
        }

        .metric {
            padding: 14px;
            border-right: 1px solid var(--line);
            min-width: 0;
        }

        .metric:last-child {
            border-right: 0;
        }

        .metric span {
            display: block;
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .metric strong {
            display: block;
            min-width: 0;
            overflow-wrap: anywhere;
            word-break: break-word;
            font-size: 24px;
            line-height: 1.15;
        }

        .metric .file-name {
            font-size: 18px;
        }

        .section {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            margin-bottom: 16px;
            overflow: hidden;
        }

        .section-head {
            padding: 14px 16px;
            border-bottom: 1px solid var(--line);
        }

        .section-body {
            padding: 16px;
        }

        .comparison-chart {
            display: grid;
            gap: 14px;
        }

        .chart-row {
            display: grid;
            grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
            gap: 16px;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--line);
        }

        .chart-row:last-child {
            border-bottom: 0;
            padding-bottom: 0;
        }

        .chart-label {
            min-width: 0;
        }

        .chart-label strong,
        .chart-label span {
            display: block;
            overflow-wrap: anywhere;
        }

        .chart-label span {
            color: var(--muted);
            font-size: 12px;
            margin-top: 4px;
        }

        .chart-bars {
            display: grid;
            gap: 8px;
            min-width: 0;
        }

        .bar-line {
            display: grid;
            grid-template-columns: 78px minmax(0, 1fr) 64px;
            gap: 10px;
            align-items: center;
            font-size: 13px;
        }

        .bar-line > span {
            color: var(--muted);
            font-weight: 700;
        }

        .bar-line > strong {
            text-align: right;
        }

        .bar-track {
            height: 14px;
            border-radius: 999px;
            background: #edf1f5;
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            border-radius: 999px;
        }

        .bar-fill.result {
            background: #2f8f5b;
        }

        .bar-fill.target {
            background: #d9862c;
        }

        .bar-fill.external {
            background: #176b87;
        }

        .bar-fill.territorial {
            background: #6b6f2a;
        }

        .bar-fill.microdata {
            background: #7b4f9f;
        }

        .table-wrap {
            overflow: auto;
            max-height: 560px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th,
        td {
            border-bottom: 1px solid var(--line);
            padding: 8px 10px;
            text-align: left;
            white-space: nowrap;
        }

        th {
            background: var(--accent-soft);
            position: sticky;
            top: 0;
            z-index: 1;
        }

        .erro {
            padding: 16px;
            border: 1px solid #efc6bd;
            border-radius: 8px;
            background: #fff4f1;
            color: #8a2d1c;
        }

        @media (max-width: 900px) {
            .layout {
                grid-template-columns: 1fr;
            }

            aside {
                position: relative;
                height: auto;
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }

            .cards,
            .header,
            .chart-row {
                display: grid;
                grid-template-columns: 1fr;
            }

            .metric {
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }
        }
    </style>
</head>
<body>
<div class="layout">
    <aside>
        <div class="brand">
            <h1>Catalogo Gold</h1>
            <p>{{ total_tabelas }} tabelas disponiveis em data/gold.</p>
        </div>

        <nav class="menu" aria-label="Tabelas Gold">
            <a class="dashboard-link" href="{{ url_for('mapa_index') }}">
                Mapa Brasil Metas
                <span class="table-name">Dashboard geografico</span>
            </a>

            {% if menu_verificacoes %}
                <div class="menu-section">Verificacoes Gold</div>

                {% for item in menu_verificacoes %}
                    <a href="{{ url_for('index', tabela=item.tabela, limite=limite) }}"
                       class="{% if item.tabela == tabela_selecionada %}active{% endif %}">
                        {{ item.nome }}
                        <span class="table-name">gold.{{ item.tabela }}</span>
                    </a>
                {% endfor %}
            {% endif %}

            {% if menu_territoriais %}
                <div class="menu-section">Dados Territoriais</div>

                {% for item in menu_territoriais %}
                    <a href="{{ url_for('index', tabela=item.tabela, limite=limite) }}"
                       class="{% if item.tabela == tabela_selecionada %}active{% endif %}">
                        {{ item.nome }}
                        <span class="table-name">gold.{{ item.tabela }}</span>
                    </a>
                {% endfor %}
            {% endif %}

            {% if menu_microdados %}
                <div class="menu-section">Microdados Educacionais</div>

                {% for item in menu_microdados %}
                    <a href="{{ url_for('index', tabela=item.tabela, limite=limite) }}"
                       class="{% if item.tabela == tabela_selecionada %}active{% endif %}">
                        {{ item.nome }}
                        <span class="table-name">gold.{{ item.tabela }}</span>
                    </a>
                {% endfor %}
            {% endif %}

            <div class="menu-section">Tabelas Gold</div>

            {% for item in menu_tabelas %}
                <a href="{{ url_for('index', tabela=item.tabela, limite=limite) }}"
                   class="{% if item.tabela == tabela_selecionada %}active{% endif %}">
                    {{ item.nome }}
                    <span class="table-name">gold.{{ item.tabela }}</span>
                </a>
            {% endfor %}
        </nav>
    </aside>

    <main>
        {% if erro %}
            <section class="erro">{{ erro }}</section>
        {% else %}
            <header class="header">
                <div>
                    <h1>{{ descricao.nome }}</h1>
                    <p class="subtitle">gold.{{ tabela_selecionada }}</p>
                    <p class="subtitle">{{ descricao.descricao }}</p>
                </div>
                <form class="actions" method="get">
                    <input type="hidden" name="tabela" value="{{ tabela_selecionada }}">
                    <label>
                        Linhas
                        <input type="number" name="limite" min="5" max="500" step="5" value="{{ limite }}">
                    </label>
                    <button type="submit">Atualizar</button>
                </form>
            </header>

            <section class="cards" aria-label="Resumo da tabela">
                <div class="metric"><span>Linhas</span><strong>{{ linhas }}</strong></div>
                <div class="metric"><span>Colunas</span><strong>{{ colunas }}</strong></div>
                <div class="metric"><span>Execucao</span><strong class="file-name">{{ arquivo_nome }}</strong></div>
                <div class="metric"><span>Amostra</span><strong>{{ limite }}</strong></div>
            </section>

            {% if filtros %}
                <form class="filters" method="get">
                    <input type="hidden" name="tabela" value="{{ tabela_selecionada }}">
                    <input type="hidden" name="limite" value="{{ limite }}">
                    <div class="filter-grid">
                        {% for filtro in filtros %}
                            <label>
                                {{ filtro.rotulo }}
                                {% if filtro.tipo == "select" %}
                                    <select name="{{ filtro.nome }}">
                                        <option value="">Todos</option>
                                        {% for valor in filtro.valores %}
                                            <option value="{{ valor }}" {% if valor == filtro.valor %}selected{% endif %}>
                                                {{ valor }}
                                            </option>
                                        {% endfor %}
                                    </select>
                                {% else %}
                                    <input
                                        type="search"
                                        name="{{ filtro.nome }}"
                                        value="{{ filtro.valor }}"
                                        placeholder="{{ filtro.placeholder }}"
                                    >
                                {% endif %}
                            </label>
                        {% endfor %}
                        <div class="filter-actions">
                            <button type="submit">Filtrar</button>
                            <a class="secondary-link" href="{{ url_for('index', tabela=tabela_selecionada, limite=limite) }}">
                                Limpar
                            </a>
                        </div>
                    </div>
                </form>
            {% endif %}

            {% if grafico_comparacao %}
                <section class="section">
                    <div class="section-head">
                        <h2>Grafico de comparacao</h2>
                        <p class="muted">Resultado observado x meta de alfabetizacao para a selecao atual.</p>
                    </div>
                    <div class="section-body comparison-chart">
                        {{ grafico_comparacao | safe }}
                    </div>
                </section>
            {% endif %}

            {% if grafico_evolucao %}
                <section class="section">
                    <div class="section-head">
                        <h2>Grafico temporal</h2>
                        <p class="muted">Evolucao de resultado observado x meta para a selecao atual.</p>
                    </div>
                    <div class="section-body comparison-chart">
                        {{ grafico_evolucao | safe }}
                    </div>
                </section>
            {% endif %}

            {% if grafico_externo %}
                <section class="section">
                    <div class="section-head">
                        <h2>Grafico de verificacao</h2>
                        <p class="muted">Indicador externo x meta de alfabetizacao para a selecao atual.</p>
                    </div>
                    <div class="section-body comparison-chart">
                        {{ grafico_externo | safe }}
                    </div>
                </section>
            {% endif %}

            {% if grafico_territorial %}
                <section class="section">
                    <div class="section-head">
                        <h2>Grafico territorial</h2>
                        <p class="muted">Resumo visual da selecao territorial atual.</p>
                    </div>
                    <div class="section-body comparison-chart">
                        {{ grafico_territorial | safe }}
                    </div>
                </section>
            {% endif %}

            {% if grafico_microdados %}
                <section class="section">
                    <div class="section-head">
                        <h2>Grafico de microdados</h2>
                        <p class="muted">Resumo visual da selecao atual dos microdados educacionais.</p>
                    </div>
                    <div class="section-body comparison-chart">
                        {{ grafico_microdados | safe }}
                    </div>
                </section>
            {% endif %}

            <section class="section">
                <div class="section-head">
                    <h2>Dicionario da tabela</h2>
                </div>
                <div class="section-body table-wrap">
                    {{ dicionario | safe }}
                </div>
            </section>

            {% if mostrar_listagem %}
                <section class="section">
                    <div class="section-head">
                        <h2>Listagem</h2>
                        <p class="muted">Exibindo ate {{ limite }} linhas da selecao atual.</p>
                    </div>
                    <div class="section-body table-wrap">
                        {{ listagem | safe }}
                    </div>
                </section>
            {% endif %}
        {% endif %}
    </main>
</div>
</body>
</html>
"""


@app.route("/")
def index():
    tabelas = listar_tabelas_gold()
    menu = [
        {
            "tabela": tabela,
            "nome": DESCRICOES_TABELAS.get(tabela, {}).get("nome", tabela),
        }
        for tabela in tabelas
    ]
    menu_verificacoes = [
        item for item in menu if item["tabela"] in TABELAS_VERIFICACAO_GOLD
    ]
    menu_territoriais = [
        item for item in menu if item["tabela"] in TABELAS_DADOS_TERRITORIAIS
    ]
    menu_microdados = [
        item for item in menu if item["tabela"] in TABELAS_MICRODADOS_EDUCACIONAIS
    ]
    menu_tabelas = [
        item
        for item in menu
        if item["tabela"] not in TABELAS_VERIFICACAO_GOLD
        and item["tabela"] not in TABELAS_DADOS_TERRITORIAIS
        and item["tabela"] not in TABELAS_MICRODADOS_EDUCACIONAIS
    ]

    if not tabelas:
        return render_template_string(
            HTML,
            total_tabelas=0,
            menu=[],
            menu_verificacoes=[],
            menu_territoriais=[],
            menu_microdados=[],
            menu_tabelas=[],
            tabela_selecionada=None,
            limite=50,
            erro="Nenhuma tabela Gold encontrada em data/gold.",
        )

    tabela_selecionada = request.args.get("tabela", tabelas[0])
    if tabela_selecionada not in tabelas:
        tabela_selecionada = tabelas[0]

    try:
        limite = int(request.args.get("limite", "50"))
    except ValueError:
        limite = 50
    limite = min(max(limite, 5), 500)

    try:
        df, arquivo = carregar_gold(tabela_selecionada)
        descricao = DESCRICOES_TABELAS.get(
            tabela_selecionada,
            {
                "nome": tabela_selecionada,
                "descricao": "Tabela analitica da camada Gold.",
            },
        )

        filtros = montar_filtros(tabela_selecionada, df)
        df_filtrado = aplicar_filtros(df, filtros)
        grafico_comparacao = ""
        if tabela_selecionada in TABELAS_COM_GRAFICO_COMPARACAO:
            grafico_comparacao = montar_grafico_comparacao(df_filtrado, limite)
        grafico_evolucao = ""
        mostrar_listagem = tabela_selecionada not in TABELAS_COM_GRAFICO_EVOLUCAO
        if tabela_selecionada in TABELAS_COM_GRAFICO_EVOLUCAO:
            grafico_evolucao = montar_grafico_evolucao(df_filtrado, limite)
        grafico_externo = ""
        if tabela_selecionada in TABELAS_COM_GRAFICO_EXTERNO:
            config_grafico = TABELAS_COM_GRAFICO_EXTERNO[tabela_selecionada]
            grafico_externo = montar_grafico_externo(
                df_filtrado,
                limite,
                config_grafico["metrica"],
                config_grafico["rotulo"],
            )
        grafico_territorial = ""
        if tabela_selecionada in TABELAS_DADOS_TERRITORIAIS:
            grafico_territorial = montar_grafico_territorial(
                tabela_selecionada,
                df_filtrado,
                limite,
            )
        grafico_microdados = ""
        if tabela_selecionada in TABELAS_MICRODADOS_EDUCACIONAIS:
            grafico_microdados = montar_grafico_microdados(
                tabela_selecionada,
                df_filtrado,
                limite,
            )

        dicionario = montar_dicionario_colunas(df).to_html(index=False, classes="data-table")
        listagem = preparar_tabela_html(df_filtrado, limite) if mostrar_listagem else ""

        return render_template_string(
            HTML,
            total_tabelas=len(tabelas),
            menu=menu,
            menu_verificacoes=menu_verificacoes,
            menu_territoriais=menu_territoriais,
            menu_microdados=menu_microdados,
            menu_tabelas=menu_tabelas,
            tabela_selecionada=tabela_selecionada,
            limite=limite,
            erro=None,
            descricao=descricao,
            filtros=filtros,
            linhas=f"{len(df_filtrado):,}".replace(",", "."),
            colunas=len(df.columns),
            arquivo_nome=arquivo.name,
            grafico_comparacao=grafico_comparacao,
            grafico_evolucao=grafico_evolucao,
            grafico_externo=grafico_externo,
            grafico_territorial=grafico_territorial,
            grafico_microdados=grafico_microdados,
            mostrar_listagem=mostrar_listagem,
            dicionario=dicionario,
            listagem=listagem,
        )
    except Exception as erro:
        return render_template_string(
            HTML,
            total_tabelas=len(tabelas),
            menu=menu,
            menu_verificacoes=menu_verificacoes,
            menu_territoriais=menu_territoriais,
            menu_microdados=menu_microdados,
            menu_tabelas=menu_tabelas,
            tabela_selecionada=tabela_selecionada,
            limite=limite,
            filtros=[],
            grafico_comparacao="",
            grafico_evolucao="",
            grafico_externo="",
            grafico_territorial="",
            grafico_microdados="",
            mostrar_listagem=True,
            erro=str(erro),
        )


def ajustar_links_mapa(html: str) -> str:
    return (
        html
        .replace('href="/estado/', 'href="/mapa/estado/')
        .replace('href="/cidade/', 'href="/mapa/cidade/')
        .replace('href="/?ano=', 'href="/mapa?ano=')
        .replace('`/cidade/${cidadeSelect.value}', '`/mapa/cidade/${cidadeSelect.value}')
    )


@app.route("/mapa")
def mapa_index():
    try:
        df = mapa.carregar_indicador_uf()
        opcoes = mapa.montar_opcoes(df)
        ano = request.args.get("ano", opcoes["anos"][0] if opcoes["anos"] else "todos")
        rede = request.args.get("rede", "todas")
        dados = mapa.filtrar_dados(df, ano, rede)

        return render_template_string(
            ajustar_links_mapa(mapa.HTML),
            opcoes=opcoes,
            ano=ano,
            rede=rede,
            estados=mapa.montar_estados(dados),
            metricas=mapa.montar_metricas(dados),
            erro=None,
        )
    except Exception as erro:
        return render_template_string(
            ajustar_links_mapa(mapa.HTML),
            opcoes={"anos": [], "redes": []},
            ano="",
            rede="todas",
            estados=[],
            metricas={},
            erro=str(erro),
        )


@app.route("/mapa/estado/<sigla_uf>")
def mapa_estado(sigla_uf: str):
    sigla_uf = sigla_uf.upper()

    if sigla_uf not in mapa.CODIGO_UF_POR_SIGLA:
        return render_template_string(
            ajustar_links_mapa(mapa.HTML_ESTADO),
            sigla_uf=sigla_uf,
            opcoes={"anos": [], "redes": []},
            ano="",
            rede="todas",
            cidades=[],
            municipios=[],
            metricas={},
            erro=f"UF invalida: {sigla_uf}",
        )

    try:
        df = mapa.carregar_indicador_municipio()
        opcoes = mapa.montar_opcoes(df)
        ano = request.args.get("ano", opcoes["anos"][0] if opcoes["anos"] else "todos")
        rede = request.args.get("rede", "todas")
        opcoes = mapa.incluir_opcao_atual(opcoes, ano, rede)
        dados = mapa.filtrar_dados_municipio(df, sigla_uf, ano, rede)

        return render_template_string(
            ajustar_links_mapa(mapa.HTML_ESTADO),
            sigla_uf=sigla_uf,
            opcoes=opcoes,
            ano=ano,
            rede=rede,
            cidades=mapa.montar_opcoes_cidade(df, sigla_uf),
            municipios=mapa.montar_municipios(dados, sigla_uf),
            metricas=mapa.montar_metricas(dados),
            erro=None,
        )
    except Exception as erro:
        return render_template_string(
            ajustar_links_mapa(mapa.HTML_ESTADO),
            sigla_uf=sigla_uf,
            opcoes={"anos": [], "redes": []},
            ano="",
            rede="todas",
            cidades=[],
            municipios=[],
            metricas={},
            erro=str(erro),
        )


@app.route("/mapa/cidade/<id_municipio>")
def mapa_cidade(id_municipio: str):
    ano = request.args.get("ano", "todos")
    rede = request.args.get("rede", "todas")
    sigla_uf = request.args.get("uf", "")

    try:
        df_municipio = mapa.carregar_indicador_municipio()
        registro = df_municipio[
            df_municipio["id_municipio"].astype(str) == str(id_municipio)
        ]

        if registro.empty:
            raise FileNotFoundError(f"Municipio nao encontrado na Gold: {id_municipio}")

        if not sigla_uf:
            sigla_uf = str(registro.iloc[0].get("sigla_uf") or "")

        return render_template_string(
            ajustar_links_mapa(mapa.HTML_CIDADE),
            id_municipio=id_municipio,
            nome_cidade=mapa.obter_nome_cidade(df_municipio, id_municipio),
            sigla_uf=sigla_uf,
            ano=ano,
            rede=rede,
            secoes=mapa.montar_secoes_cidade(id_municipio, sigla_uf, ano, rede),
            erro=None,
        )
    except Exception as erro:
        return render_template_string(
            ajustar_links_mapa(mapa.HTML_CIDADE),
            id_municipio=id_municipio,
            nome_cidade=str(id_municipio),
            sigla_uf=sigla_uf,
            ano=ano,
            rede=rede,
            secoes=[],
            erro=str(erro),
        )


if __name__ == "__main__":
    app.run(debug=False, port=5006, use_reloader=False)
