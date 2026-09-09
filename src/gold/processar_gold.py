"""
Processador da camada Gold - Análises finais de alfabetização.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

from src.gold.base_modelagem import construir_base_modelagem_aluno

from src.common.particionamento import salvar_particionado_por_ano, ler_tabela_mais_recente
from src.qualidade.armazenamento import (
    ler_metricas_safra_anterior,
    salvar_metricas_qualidade,
)
from src.qualidade.metricas import (
    avaliar_gates,
    coletar_metricas_cobertura,
    coletar_metricas_gold,
    comparar_cobertura_com_safra_anterior,
    imprimir_resumo,
)


SILVER_PATH = Path("data/silver")
GOLD_PATH = Path("data/gold")

# Partição de destino da execução corrente. É module-level porque as ~20
# funções de materialização a usam para carimbar data_processamento_gold;
# processar_camada_gold a redefine quando recebe uma data, para que Silver e
# Gold caiam sempre na mesma partição (inclusive num reprocessamento de data
# passada, ou numa execução que atravesse a meia-noite).
EXECUTION_DATE = date.today().isoformat()

# Volumetria publicada por tabela na execução corrente, alimentada por
# salvar_gold e registrada em gold.metricas_qualidade no fim da camada.
VOLUMETRIA_GOLD: dict[str, int] = {}

# Universo territorial esperado: 26 estados + Distrito Federal.
TOTAL_UF_BRASIL = 27


CODIGO_UF_POR_PREFIXO = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}


def carregar_silver(nome_tabela: str, colunas: list[str] | None = None) -> pd.DataFrame:
    """
    Carrega a execução mais recente de uma tabela Silver pelo nome.
    Com LAKE_S3_BUCKET definido (jobs Glue), lê direto do S3.
    """
    bucket = os.getenv("LAKE_S3_BUCKET")

    if bucket:
        from src.common import lake_s3

        df = lake_s3.ler_tabela_mais_recente(
            bucket, f"silver/{nome_tabela}", colunas=colunas
        )
    else:
        df = ler_tabela_mais_recente(SILVER_PATH / nome_tabela, colunas=colunas)

    print(f"[OK] silver.{nome_tabela} carregada: {len(df)} linhas")

    return df


def carregar_silver_opcional(
    nome_tabela: str,
    colunas: list[str] | None = None,
) -> pd.DataFrame | None:
    """
    Carrega uma tabela Silver que pode não existir — a integração FUNDEB
    foi removida da Bronze, então fato_fundeb só existe em lakes antigos.
    Retorna None quando ausente, e as tabelas Gold dependentes são puladas.
    """
    try:
        return carregar_silver(nome_tabela, colunas=colunas)
    except FileNotFoundError:
        print(f"[AVISO] silver.{nome_tabela} indisponível; tabelas dependentes serão puladas")

        return None


def salvar_gold(df: pd.DataFrame, nome_tabela: str) -> Path | str:
    """
    Salva uma tabela Gold particionada por execution_date e por ano.
    Com LAKE_S3_BUCKET definido (jobs Glue), grava direto no S3.
    """
    bucket = os.getenv("LAKE_S3_BUCKET")

    if bucket:
        from src.common import lake_s3

        prefixo_execucao = f"gold/{nome_tabela}/execution_date={EXECUTION_DATE}"
        lake_s3.salvar_particionado_por_ano(
            df, bucket, prefixo_execucao, f"{nome_tabela}.parquet"
        )
        destino = f"s3://{bucket}/{prefixo_execucao}"
    else:
        destino = GOLD_PATH / nome_tabela / f"execution_date={EXECUTION_DATE}"
        salvar_particionado_por_ano(df, destino, f"{nome_tabela}.parquet")

    VOLUMETRIA_GOLD[nome_tabela] = len(df)

    print(f"[OK] gold.{nome_tabela} salva: {len(df)} linhas")

    return destino


def medir_cobertura(
    df: pd.DataFrame,
    coluna_entidade: str,
    total_esperado: int,
) -> dict[int, tuple[int, int]]:
    """Conta entidades territoriais distintas por ano, contra o universo esperado."""
    return {
        int(ano): (grupo[coluna_entidade].nunique(), total_esperado)
        for ano, grupo in df.groupby("ano")
    }


def registrar_qualidade_gold(
    coberturas: dict[str, dict[int, tuple[int, int]]] | None = None,
) -> pd.DataFrame:
    """
    Grava a volumetria publicada e a cobertura territorial da Gold em
    gold.metricas_qualidade, na mesma partição de execução usada pela Silver.
    """
    df_metricas = coletar_metricas_gold(VOLUMETRIA_GOLD, EXECUTION_DATE)

    if coberturas:
        df_metricas = pd.concat(
            [df_metricas, coletar_metricas_cobertura(coberturas, EXECUTION_DATE)],
            ignore_index=True,
        )
        df_metricas = comparar_cobertura_com_safra_anterior(
            df_metricas,
            ler_metricas_safra_anterior(EXECUTION_DATE),
        )

    salvar_metricas_qualidade(df_metricas, EXECUTION_DATE)
    imprimir_resumo(df_metricas)
    avaliar_gates(df_metricas)

    return df_metricas


def aplicar_status_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula status de cumprimento de meta."""
    df = df.copy()
    
    df["distancia_meta"] = df["taxa_alfabetizacao"] - df["meta_alfabetizacao"]
    df["flag_meta_atingida"] = pd.NA
    df.loc[
        ~(df["taxa_alfabetizacao"].isna() | df["meta_alfabetizacao"].isna()),
        "flag_meta_atingida"
    ] = df.loc[
        ~(df["taxa_alfabetizacao"].isna() | df["meta_alfabetizacao"].isna()),
        "distancia_meta"
    ] >= 0
    
    df["status_meta"] = "Sem informação"
    df.loc[df["flag_meta_atingida"] == True, "status_meta"] = "Meta atingida"
    df.loc[df["flag_meta_atingida"] == False, "status_meta"] = "Abaixo da meta"
    
    return df


def enriquecer_nome_municipio(
    df: pd.DataFrame,
    df_dim_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Adiciona nome do municipio a tabelas com id_municipio."""
    if "id_municipio" not in df.columns:
        return df.copy()

    df_enriquecido = df.copy()
    df_enriquecido["id_municipio"] = df_enriquecido["id_municipio"].astype(str)

    dim_municipio = (
        df_dim_municipio[["id_municipio", "id_municipio_nome"]]
        .drop_duplicates("id_municipio")
        .copy()
    )
    dim_municipio["id_municipio"] = dim_municipio["id_municipio"].astype(str)

    if "id_municipio_nome" in df_enriquecido.columns:
        df_enriquecido = df_enriquecido.drop(columns=["id_municipio_nome"])

    df_enriquecido = df_enriquecido.merge(dim_municipio, on="id_municipio", how="left")

    colunas = list(df_enriquecido.columns)
    colunas.remove("id_municipio_nome")
    indice_id = colunas.index("id_municipio") + 1
    colunas.insert(indice_id, "id_municipio_nome")

    return df_enriquecido[colunas]


def enriquecer_regiao_uf(
    df: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Adiciona regiao brasileira a tabelas com sigla_uf."""
    if "sigla_uf" not in df.columns:
        return df.copy()

    dominio = (
        df_dominio_regiao_uf[["sigla_uf", "regiao_brasil"]]
        .drop_duplicates("sigla_uf")
        .copy()
    )

    df_enriquecido = df.copy()
    if "regiao_brasil" in df_enriquecido.columns:
        df_enriquecido = df_enriquecido.drop(columns=["regiao_brasil"])

    return df_enriquecido.merge(dominio, on="sigla_uf", how="left")


def enriquecer_regiao_municipio(
    df: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Deriva UF do municipio e adiciona regiao brasileira."""
    df_enriquecido = df.copy()
    if "id_municipio" in df_enriquecido.columns and "sigla_uf" not in df_enriquecido.columns:
        df_enriquecido["sigla_uf"] = (
            df_enriquecido["id_municipio"].astype(str).str[:2].map(CODIGO_UF_POR_PREFIXO)
        )

    return enriquecer_regiao_uf(df_enriquecido, df_dominio_regiao_uf)


def processar_indicador_meta_brasil(
    df_fato_resultado_brasil: pd.DataFrame,
    df_fato_meta_anual_brasil: pd.DataFrame,
) -> pd.DataFrame:
    """Processa indicador de meta Brasil."""
    df = (
        df_fato_resultado_brasil
        .merge(
            df_fato_meta_anual_brasil.loc[
                df_fato_meta_anual_brasil["ano"].eq(df_fato_meta_anual_brasil["ano_meta"])
            ],
            on=["ano", "rede", "nivel_agregacao"],
            how="left",
            validate="one_to_one",
            suffixes=("_resultado", "_meta")
        )
    )

    # Compara o resultado observado no ano apenas com a meta do mesmo ano;
    # sem esse filtro, cada linha de resultado se multiplica por uma linha
    # por ano_meta (2024..2030), comparando o mesmo resultado contra metas
    # de anos diferentes.
    # Ausência de meta não elimina o resultado observado.
    df["ano_meta"] = df["ano"]

    df = aplicar_status_meta(df)

    return (
        df
        .sort_values(["ano", "rede"])
        .reset_index(drop=True)
    )


def processar_indicador_meta_uf(
    df_fato_resultado_meta_uf: pd.DataFrame,
    df_fato_meta_anual_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Processa indicador de meta por UF."""
    df = (
        df_fato_resultado_meta_uf
        .merge(
            df_fato_meta_anual_uf.loc[
                df_fato_meta_anual_uf["ano"].eq(df_fato_meta_anual_uf["ano_meta"])
            ],
            on=["ano", "sigla_uf", "rede", "nivel_agregacao"],
            how="left",
            validate="one_to_one",
            suffixes=("_resultado", "_meta")
        )
    )

    # Preserva UFs sem meta para tornar a lacuna visível.
    df["ano_meta"] = df["ano"]

    df = aplicar_status_meta(df)

    return (
        df
        .sort_values(["ano", "sigla_uf", "rede"])
        .reset_index(drop=True)
    )


def processar_ranking_uf_prioritaria(
    df_indicador_meta_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Processa ranking de UFs prioritárias."""
    df = (
        df_indicador_meta_uf[df_indicador_meta_uf["status_meta"] == "Abaixo da meta"]
        .groupby(["ano", "sigla_uf"])
        .agg({
            "distancia_meta": "mean",
            "taxa_alfabetizacao": "mean",
        })
        .reset_index()
        .sort_values(["ano", "distancia_meta"])
        .reset_index(drop=True)
    )
    
    df["ranking"] = df.groupby("ano").cumcount() + 1
    
    return df[df["ranking"] <= 10].reset_index(drop=True)


def processar_indicador_meta_municipio(
    df_fato_resultado_meta_municipio: pd.DataFrame,
    df_fato_meta_anual_municipio: pd.DataFrame,
    df_dim_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Processa indicador de meta por município."""
    df = (
        df_fato_resultado_meta_municipio
        .merge(
            df_fato_meta_anual_municipio.loc[
                df_fato_meta_anual_municipio["ano"].eq(df_fato_meta_anual_municipio["ano_meta"])
            ],
            on=["ano", "id_municipio", "rede", "nivel_agregacao"],
            how="left",
            validate="one_to_one",
            suffixes=("_resultado", "_meta")
        )
    )

    # Preserva municípios sem meta, inclusive o ano-base 2023.
    df["ano_meta"] = df["ano"]

    df = aplicar_status_meta(df)
    df = enriquecer_nome_municipio(df, df_dim_municipio)

    return (
        df
        .sort_values(["ano", "id_municipio_nome", "id_municipio", "rede"])
        .reset_index(drop=True)
    )


def processar_ranking_municipio_prioritario(
    df_indicador_meta_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Processa ranking de municípios prioritários."""
    df = (
        df_indicador_meta_municipio[
            df_indicador_meta_municipio["status_meta"] == "Abaixo da meta"
        ]
        .groupby(["ano", "id_municipio"])
        .agg({
            "distancia_meta": "mean",
            "taxa_alfabetizacao": "mean",
        })
        .reset_index()
        .sort_values(["ano", "distancia_meta"])
        .reset_index(drop=True)
    )

    if "id_municipio_nome" in df_indicador_meta_municipio.columns:
        nomes = (
            df_indicador_meta_municipio[["id_municipio", "id_municipio_nome"]]
            .drop_duplicates("id_municipio")
        )
        df = df.merge(nomes, on="id_municipio", how="left")
    
    df["ranking"] = df.groupby("ano").cumcount() + 1
    
    colunas = ["ano", "id_municipio", "id_municipio_nome", "distancia_meta", "taxa_alfabetizacao", "ranking"]

    return (
        df[df["ranking"] <= 20][[coluna for coluna in colunas if coluna in df.columns]]
        .reset_index(drop=True)
    )


def processar_evolucao_meta_resultado(
    df_indicador: pd.DataFrame,
    grupo: list[str],
    colunas_territorio: list[str],
    ordenacao: list[str],
) -> pd.DataFrame:
    """
    Serie temporal de meta x resultado em um grao territorial.

    Tabela unica de consumo do par meta/resultado: consolida o que antes
    eram duas tabelas Gold por grao (comparacao_* e evolucao_*), já que a
    comparacao era a projecao desta mesma tabela sem as colunas de
    variacao anual. Ver docs/adr/ADR-003-governanca-camada-gold.md.
    """
    df = df_indicador.rename(
        columns={"taxa_alfabetizacao": "resultado_alfabetizacao"}
    ).copy()
    df = df.sort_values([*grupo, "ano"]).reset_index(drop=True)

    df["variacao_resultado_ano_anterior"] = (
        df.groupby(grupo)["resultado_alfabetizacao"].diff()
    )
    df["variacao_meta_ano_anterior"] = (
        df.groupby(grupo)["meta_alfabetizacao"].diff()
    )
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "ano_meta",
        *colunas_territorio,
        "rede",
        "nivel_agregacao",
        "resultado_alfabetizacao",
        "meta_alfabetizacao",
        "distancia_meta",
        "variacao_resultado_ano_anterior",
        "variacao_meta_ano_anterior",
        "flag_meta_atingida",
        "status_meta",
        "data_processamento_gold",
    ]

    return (
        df[[coluna for coluna in colunas if coluna in df.columns]]
        .sort_values([coluna for coluna in ordenacao if coluna in df.columns])
        .reset_index(drop=True)
    )


def processar_evolucao_meta_resultado_brasil(
    df_indicador_meta_brasil: pd.DataFrame,
) -> pd.DataFrame:
    """Serie temporal de meta e resultado no nivel Brasil."""
    return processar_evolucao_meta_resultado(
        df_indicador_meta_brasil,
        grupo=["rede"],
        colunas_territorio=[],
        ordenacao=["rede", "ano"],
    )


def processar_evolucao_meta_resultado_uf(
    df_indicador_meta_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Serie temporal de meta e resultado por UF."""
    return processar_evolucao_meta_resultado(
        df_indicador_meta_uf,
        grupo=["sigla_uf", "rede"],
        colunas_territorio=["sigla_uf"],
        ordenacao=["sigla_uf", "rede", "ano"],
    )


def processar_evolucao_meta_resultado_municipio(
    df_indicador_meta_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Serie temporal de meta e resultado por municipio."""
    df = df_indicador_meta_municipio.copy()

    # indicador_meta_municipio nao carrega a UF (a origem e o fato municipal):
    # deriva do prefixo IBGE do codigo, para que o recorte por estado funcione
    # nesta tabela de consumo.
    if "sigla_uf" not in df.columns:
        df["sigla_uf"] = (
            df["id_municipio"].astype(str).str[:2].map(CODIGO_UF_POR_PREFIXO)
        )

    return processar_evolucao_meta_resultado(
        df,
        grupo=["id_municipio", "rede"],
        colunas_territorio=["id_municipio", "id_municipio_nome", "sigla_uf"],
        ordenacao=["sigla_uf", "id_municipio_nome", "id_municipio", "rede", "ano"],
    )


def processar_meta_uf_fundeb(
    df_indicador_meta_uf: pd.DataFrame,
    df_fato_fundeb: pd.DataFrame,
) -> pd.DataFrame:
    """Cruza metas por UF com valores do FUNDEB."""
    fundeb = df_fato_fundeb.rename(
        columns={
            "estado": "sigla_uf_nome",
            "ranking_ano": "ranking_fundeb_ano",
        }
    ).copy()
    fundeb = fundeb[
        [
            "ano",
            "sigla_uf",
            "sigla_uf_nome",
            "ranking_fundeb_ano",
            "total_estado_df",
            "total_municipios",
            "total_fundeb",
            "percentual_brasil",
        ]
    ].drop_duplicates(["ano", "sigla_uf"])

    df = df_indicador_meta_uf.rename(
        columns={"taxa_alfabetizacao": "resultado_alfabetizacao"}
    ).copy()
    df = df.merge(fundeb, on=["ano", "sigla_uf"], how="left")
    df["ranking_meta_ano"] = df.groupby("ano")["meta_alfabetizacao"].rank(
        ascending=False,
        method="dense",
    ).astype("Int64")
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "ano_meta",
        "sigla_uf",
        "sigla_uf_nome",
        "rede",
        "nivel_agregacao",
        "resultado_alfabetizacao",
        "meta_alfabetizacao",
        "distancia_meta",
        "status_meta",
        "total_fundeb",
        "total_estado_df",
        "total_municipios",
        "percentual_brasil",
        "ranking_fundeb_ano",
        "ranking_meta_ano",
        "data_processamento_gold",
    ]

    return (
        df[[coluna for coluna in colunas if coluna in df.columns]]
        .sort_values(["ano", "ranking_fundeb_ano", "sigla_uf"])
        .reset_index(drop=True)
    )


def processar_meta_uf_bolsa_familia(
    df_indicador_meta_uf: pd.DataFrame,
    df_fato_bolsa_familia_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Cruza metas por UF com beneficiarios e valores do Bolsa Familia."""
    bolsa = df_fato_bolsa_familia_municipio.rename(
        columns={
            "ano_competencia": "ano",
            "total_beneficiarios": "total_beneficiarios_bolsa_familia",
            "valor_total_pago": "valor_total_bolsa_familia",
        }
    ).copy()
    bolsa = (
        bolsa
        .groupby(["ano", "sigla_uf"], as_index=False)
        .agg(
            total_beneficiarios_bolsa_familia=("total_beneficiarios_bolsa_familia", "sum"),
            valor_total_bolsa_familia=("valor_total_bolsa_familia", "sum"),
            total_municipios_com_bolsa_familia=("id_municipio", "nunique"),
        )
    )
    bolsa["ranking_beneficiarios_ano"] = (
        bolsa.groupby("ano")["total_beneficiarios_bolsa_familia"]
        .rank(ascending=False, method="dense")
        .astype("Int64")
    )

    df = df_indicador_meta_uf.rename(
        columns={"taxa_alfabetizacao": "resultado_alfabetizacao"}
    ).copy()
    df = df.merge(bolsa, on=["ano", "sigla_uf"], how="left")
    df["ranking_meta_ano"] = df.groupby("ano")["meta_alfabetizacao"].rank(
        ascending=False,
        method="dense",
    ).astype("Int64")
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "ano_meta",
        "sigla_uf",
        "rede",
        "nivel_agregacao",
        "resultado_alfabetizacao",
        "meta_alfabetizacao",
        "distancia_meta",
        "status_meta",
        "total_beneficiarios_bolsa_familia",
        "valor_total_bolsa_familia",
        "total_municipios_com_bolsa_familia",
        "ranking_beneficiarios_ano",
        "ranking_meta_ano",
        "data_processamento_gold",
    ]

    return (
        df[[coluna for coluna in colunas if coluna in df.columns]]
        .sort_values(["ano", "ranking_beneficiarios_ano", "sigla_uf"])
        .reset_index(drop=True)
    )


def processar_indicador_meta_regiao(
    df_indicador_meta_uf: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega cumprimento de metas por regiao brasileira."""
    df = enriquecer_regiao_uf(df_indicador_meta_uf, df_dominio_regiao_uf)
    df = (
        df
        .groupby(["ano", "ano_meta", "regiao_brasil", "rede"], dropna=False)
        .agg(
            resultado_alfabetizacao_medio=("taxa_alfabetizacao", "mean"),
            meta_alfabetizacao_media=("meta_alfabetizacao", "mean"),
            distancia_media_meta=("distancia_meta", "mean"),
            total_ufs=("sigla_uf", "nunique"),
            total_meta_atingida=("status_meta", lambda serie: int((serie == "Meta atingida").sum())),
            total_abaixo_meta=("status_meta", lambda serie: int((serie == "Abaixo da meta").sum())),
            total_sem_informacao=("status_meta", lambda serie: int((serie == "Sem informação").sum())),
        )
        .reset_index()
    )
    df["percentual_meta_atingida"] = (
        df["total_meta_atingida"] / df["total_ufs"].replace(0, pd.NA) * 100
    )
    df["status_regiao"] = "Sem informacao"
    df.loc[df["distancia_media_meta"] >= 0, "status_regiao"] = "Meta atingida"
    df.loc[df["distancia_media_meta"] < 0, "status_regiao"] = "Abaixo da meta"
    df["data_processamento_gold"] = EXECUTION_DATE

    return (
        df
        .sort_values(["ano", "regiao_brasil", "rede"])
        .reset_index(drop=True)
    )


def processar_ranking_territorial_prioridade(
    df_indicador_meta_municipio: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Cria ranking de municipios prioritarios por Brasil, regiao e UF."""
    df = enriquecer_regiao_municipio(df_indicador_meta_municipio, df_dominio_regiao_uf)
    df = df[
        df["status_meta"].eq("Abaixo da meta") & df["distancia_meta"].notna()
    ].copy()
    df = df.sort_values(["ano", "ano_meta", "distancia_meta", "id_municipio"])
    df["ranking_nacional"] = df.groupby(["ano", "ano_meta"]).cumcount() + 1
    df["ranking_regiao"] = df.groupby(["ano", "ano_meta", "regiao_brasil"]).cumcount() + 1
    df["ranking_uf"] = df.groupby(["ano", "ano_meta", "sigla_uf"]).cumcount() + 1
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "ano_meta",
        "regiao_brasil",
        "sigla_uf",
        "id_municipio",
        "id_municipio_nome",
        "rede",
        "taxa_alfabetizacao",
        "meta_alfabetizacao",
        "distancia_meta",
        "status_meta",
        "ranking_nacional",
        "ranking_regiao",
        "ranking_uf",
        "data_processamento_gold",
    ]

    return (
        df[[coluna for coluna in colunas if coluna in df.columns]]
        .reset_index(drop=True)
    )


def processar_desigualdade_territorial_uf(
    df_indicador_meta_municipio: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula desigualdade de resultados municipais dentro de cada UF."""
    df = enriquecer_regiao_municipio(df_indicador_meta_municipio, df_dominio_regiao_uf)
    df = (
        df
        .groupby(["ano", "ano_meta", "regiao_brasil", "sigla_uf", "rede"], dropna=False)
        .agg(
            resultado_medio_uf=("taxa_alfabetizacao", "mean"),
            menor_resultado_municipal=("taxa_alfabetizacao", "min"),
            maior_resultado_municipal=("taxa_alfabetizacao", "max"),
            desvio_padrao_resultado=("taxa_alfabetizacao", "std"),
            meta_media_uf=("meta_alfabetizacao", "mean"),
            distancia_media_meta=("distancia_meta", "mean"),
            qtd_municipios=("id_municipio", "nunique"),
            qtd_municipios_abaixo_meta=("status_meta", lambda serie: int((serie == "Abaixo da meta").sum())),
            qtd_municipios_meta_atingida=("status_meta", lambda serie: int((serie == "Meta atingida").sum())),
        )
        .reset_index()
    )
    df["amplitude_resultado"] = (
        df["maior_resultado_municipal"] - df["menor_resultado_municipal"]
    )
    df["percentual_municipios_abaixo_meta"] = (
        df["qtd_municipios_abaixo_meta"] / df["qtd_municipios"].replace(0, pd.NA) * 100
    )
    df["data_processamento_gold"] = EXECUTION_DATE

    return (
        df
        .sort_values(["ano", "amplitude_resultado"], ascending=[True, False])
        .reset_index(drop=True)
    )


def classificar_risco_territorial(distancia_meta) -> str:
    if pd.isna(distancia_meta):
        return "Sem informacao"
    if distancia_meta >= 0:
        return "Meta atingida"
    if distancia_meta >= -5:
        return "Ate 5 p.p. abaixo"
    if distancia_meta >= -10:
        return "Entre 5 e 10 p.p. abaixo"
    return "Mais de 10 p.p. abaixo"


def cor_risco_territorial(classe_risco: str) -> str:
    cores = {
        "Meta atingida": "#2f8f5b",
        "Ate 5 p.p. abaixo": "#f0c44d",
        "Entre 5 e 10 p.p. abaixo": "#d9862c",
        "Mais de 10 p.p. abaixo": "#c84b3a",
        "Sem informacao": "#cbd5df",
    }
    return cores.get(classe_risco, "#cbd5df")


def processar_mapa_calor_territorial(
    df_indicador_meta_municipio: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Cria base territorial para mapa de calor por municipio."""
    df = enriquecer_regiao_municipio(df_indicador_meta_municipio, df_dominio_regiao_uf)
    df["classe_risco"] = df["distancia_meta"].apply(classificar_risco_territorial)
    df["cor_mapa"] = df["classe_risco"].apply(cor_risco_territorial)
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "ano_meta",
        "regiao_brasil",
        "sigla_uf",
        "id_municipio",
        "id_municipio_nome",
        "rede",
        "taxa_alfabetizacao",
        "meta_alfabetizacao",
        "distancia_meta",
        "status_meta",
        "classe_risco",
        "cor_mapa",
        "data_processamento_gold",
    ]

    return (
        df[[coluna for coluna in colunas if coluna in df.columns]]
        .sort_values(["ano", "regiao_brasil", "sigla_uf", "id_municipio_nome"])
        .reset_index(drop=True)
    )


def preparar_alunos_enriquecidos(
    df_fato_aluno_alfabetizacao: pd.DataFrame,
    df_dim_escola: pd.DataFrame,
    df_dim_municipio: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
) -> pd.DataFrame:
    """Enriquece microdados educacionais com municipio, UF e regiao."""
    df = df_fato_aluno_alfabetizacao.copy()
    df["id_municipio"] = df["id_municipio"].astype(str)
    df["id_escola"] = df["id_escola"].astype(str)

    escolas = (
        df_dim_escola[["ano", "id_escola", "id_municipio", "id_municipio_nome"]]
        .drop_duplicates(["ano", "id_escola"])
        .copy()
    )
    escolas["id_escola"] = escolas["id_escola"].astype(str)
    escolas["id_municipio"] = escolas["id_municipio"].astype(str)

    if "id_municipio_nome" in df.columns:
        df = df.drop(columns=["id_municipio_nome"])

    df = df.merge(escolas, on=["ano", "id_escola", "id_municipio"], how="left", validate="many_to_one")
    municipios = (
        df_dim_municipio[["id_municipio", "id_municipio_nome"]]
        .drop_duplicates("id_municipio")
        .rename(columns={"id_municipio_nome": "id_municipio_nome_dim"})
        .copy()
    )
    municipios["id_municipio"] = municipios["id_municipio"].astype(str)
    df = df.merge(municipios, on="id_municipio", how="left")
    df["id_municipio_nome"] = df["id_municipio_nome"].fillna(df["id_municipio_nome_dim"])
    df["id_municipio_nome"] = df["id_municipio_nome"].fillna(df["id_municipio"])
    df = df.drop(columns=["id_municipio_nome_dim"])
    df["sigla_uf"] = df["id_municipio"].str[:2].map(CODIGO_UF_POR_PREFIXO)
    df = enriquecer_regiao_uf(df, df_dominio_regiao_uf)

    return df


def processar_perfil_aluno_alfabetizacao(
    df_alunos_enriquecidos: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega perfil dos alunos por presenca, alfabetizacao, serie e rede."""
    total_grupo = (
        df_alunos_enriquecidos
        .groupby(["ano", "serie", "rede"], dropna=False)
        .size()
        .reset_index(name="total_alunos_grupo")
    )
    df = (
        df_alunos_enriquecidos
        .groupby(["ano", "serie", "rede", "presenca", "alfabetizado"], dropna=False)
        .agg(
            total_alunos=("id_aluno", "count"),
            media_proficiencia=("proficiencia", "mean"),
            total_presentes=("presenca", lambda serie: int((serie == "Presente").sum())),
            total_ausentes=("presenca", lambda serie: int((serie == "Ausente").sum())),
        )
        .reset_index()
        .merge(total_grupo, on=["ano", "serie", "rede"], how="left")
    )
    df["percentual_alunos"] = (
        df["total_alunos"] / df["total_alunos_grupo"].replace(0, pd.NA) * 100
    )
    df["percentual_presentes"] = (
        df["total_presentes"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "serie",
        "rede",
        "presenca",
        "alfabetizado",
        "total_alunos",
        "media_proficiencia",
        "percentual_alunos",
        "total_presentes",
        "total_ausentes",
        "percentual_presentes",
        "data_processamento_gold",
    ]

    return (
        df[colunas]
        .sort_values(["ano", "serie", "rede", "presenca", "alfabetizado"])
        .reset_index(drop=True)
    )


def processar_indicador_presenca_avaliacao(
    df_alunos_enriquecidos: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega indicadores de presenca/ausencia na avaliacao."""
    df = (
        df_alunos_enriquecidos
        .groupby(
            ["ano", "regiao_brasil", "sigla_uf", "id_municipio", "id_municipio_nome", "rede", "serie"],
            dropna=False,
        )
        .agg(
            total_alunos=("id_aluno", "count"),
            total_presentes=("presenca", lambda serie: int((serie == "Presente").sum())),
            total_ausentes=("presenca", lambda serie: int((serie == "Ausente").sum())),
            media_proficiencia_presentes=(
                "proficiencia",
                "mean",
            ),
        )
        .reset_index()
    )
    df["percentual_presenca"] = (
        df["total_presentes"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["percentual_ausencia"] = (
        df["total_ausentes"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["data_processamento_gold"] = EXECUTION_DATE

    return (
        df
        .sort_values(["ano", "regiao_brasil", "sigla_uf", "id_municipio", "rede", "serie"])
        .reset_index(drop=True)
    )


def processar_ranking_escolas_prioritarias(
    df_alunos_enriquecidos: pd.DataFrame,
) -> pd.DataFrame:
    """Gera ranking de escolas com maior concentracao de alunos nao alfabetizados."""
    df = (
        df_alunos_enriquecidos
        .groupby(
            ["ano", "regiao_brasil", "sigla_uf", "id_municipio", "id_municipio_nome", "id_escola", "rede", "serie"],
            dropna=False,
        )
        .agg(
            total_alunos=("id_aluno", "count"),
            total_presentes=("presenca", lambda serie: int((serie == "Presente").sum())),
            total_nao_alfabetizados=("alfabetizado", lambda serie: int((serie == "Não").sum())),
            total_alfabetizados=("alfabetizado", lambda serie: int((serie == "Sim").sum())),
            media_proficiencia=("proficiencia", "mean"),
        )
        .reset_index()
    )
    df["percentual_nao_alfabetizado"] = (
        df["total_nao_alfabetizados"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["percentual_presenca"] = (
        df["total_presentes"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df = df.sort_values(
        ["ano", "percentual_nao_alfabetizado", "media_proficiencia"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    df["ranking_nacional"] = df.groupby("ano").cumcount() + 1
    df["ranking_uf"] = df.groupby(["ano", "sigla_uf"]).cumcount() + 1
    df["ranking_municipio"] = df.groupby(["ano", "id_municipio"]).cumcount() + 1
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "regiao_brasil",
        "sigla_uf",
        "id_municipio",
        "id_municipio_nome",
        "id_escola",
        "rede",
        "serie",
        "total_alunos",
        "total_presentes",
        "total_alfabetizados",
        "total_nao_alfabetizados",
        "percentual_nao_alfabetizado",
        "percentual_presenca",
        "media_proficiencia",
        "ranking_nacional",
        "ranking_uf",
        "ranking_municipio",
        "data_processamento_gold",
    ]

    return df[colunas].reset_index(drop=True)


def classificar_faixa_proficiencia(proficiencia) -> str:
    if pd.isna(proficiencia):
        return "Sem proficiencia"
    if proficiencia < 650:
        return "Abaixo de 650"
    if proficiencia < 700:
        return "650 a 699"
    if proficiencia < 750:
        return "700 a 749"
    if proficiencia < 800:
        return "750 a 799"
    return "800 ou mais"


def processar_indicador_desempenho_aluno(
    df_alunos_enriquecidos: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega indicadores de desempenho dos alunos por territorio e rede."""
    df = (
        df_alunos_enriquecidos
        .groupby(
            ["ano", "regiao_brasil", "sigla_uf", "id_municipio", "id_municipio_nome", "rede", "serie"],
            dropna=False,
        )
        .agg(
            total_alunos=("id_aluno", "count"),
            total_presentes=("presenca", lambda serie: int((serie == "Presente").sum())),
            total_alfabetizados=("alfabetizado", lambda serie: int((serie == "Sim").sum())),
            total_nao_alfabetizados=("alfabetizado", lambda serie: int((serie != "Sim").sum())),
            media_proficiencia=("proficiencia", "mean"),
            mediana_proficiencia=("proficiencia", "median"),
            menor_proficiencia=("proficiencia", "min"),
            maior_proficiencia=("proficiencia", "max"),
            desvio_padrao_proficiencia=("proficiencia", "std"),
        )
        .reset_index()
    )
    df["percentual_presenca"] = (
        df["total_presentes"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["percentual_alfabetizado"] = (
        df["total_alfabetizados"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["percentual_nao_alfabetizado"] = (
        df["total_nao_alfabetizados"] / df["total_alunos"].replace(0, pd.NA) * 100
    )
    df["data_processamento_gold"] = EXECUTION_DATE

    return (
        df
        .sort_values(["ano", "regiao_brasil", "sigla_uf", "id_municipio", "rede", "serie"])
        .reset_index(drop=True)
    )


def processar_distribuicao_desempenho_aluno(
    df_alunos_enriquecidos: pd.DataFrame,
) -> pd.DataFrame:
    """Distribui alunos por faixas de proficiencia e alfabetizacao."""
    df_base = df_alunos_enriquecidos.copy()
    df_base["faixa_proficiencia"] = df_base["proficiencia"].apply(classificar_faixa_proficiencia)

    total_grupo = (
        df_base
        .groupby(["ano", "regiao_brasil", "sigla_uf", "rede", "serie"], dropna=False)
        .size()
        .reset_index(name="total_alunos_grupo")
    )
    df = (
        df_base
        .groupby(
            ["ano", "regiao_brasil", "sigla_uf", "rede", "serie", "faixa_proficiencia", "alfabetizado"],
            dropna=False,
        )
        .agg(
            total_alunos=("id_aluno", "count"),
            media_proficiencia=("proficiencia", "mean"),
        )
        .reset_index()
        .merge(total_grupo, on=["ano", "regiao_brasil", "sigla_uf", "rede", "serie"], how="left")
    )
    df["percentual_alunos"] = (
        df["total_alunos"] / df["total_alunos_grupo"].replace(0, pd.NA) * 100
    )
    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "regiao_brasil",
        "sigla_uf",
        "rede",
        "serie",
        "faixa_proficiencia",
        "alfabetizado",
        "total_alunos",
        "media_proficiencia",
        "percentual_alunos",
        "data_processamento_gold",
    ]

    return (
        df[colunas]
        .sort_values(["ano", "regiao_brasil", "sigla_uf", "rede", "serie", "faixa_proficiencia"])
        .reset_index(drop=True)
    )


def processar_indicador_alfabetizacao_municipio(
    df_indicador_meta_municipio: pd.DataFrame,
    df_dim_municipio: pd.DataFrame,
    df_fato_bolsa_familia_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Monta indicador analitico por municipio enriquecido para consumo no catalogo."""
    df = df_indicador_meta_municipio.copy()
    df["id_municipio"] = df["id_municipio"].astype(str)
    df = enriquecer_nome_municipio(df, df_dim_municipio)
    df["sigla_uf"] = df["id_municipio"].str[:2].map(CODIGO_UF_POR_PREFIXO)

    bolsa = df_fato_bolsa_familia_municipio.copy()
    if not bolsa.empty:
        bolsa["id_municipio"] = bolsa["id_municipio"].astype(str)
        bolsa = bolsa.rename(
            columns={
                "ano_competencia": "ano",
                "total_beneficiarios": "total_beneficiarios_bolsa_familia",
                "valor_total_pago": "valor_total_bolsa_familia",
            }
        )
        bolsa = bolsa[
            [
                "ano",
                "id_municipio",
                "total_beneficiarios_bolsa_familia",
                "valor_total_bolsa_familia",
            ]
        ].drop_duplicates(["ano", "id_municipio"])
        df = df.merge(bolsa, on=["ano", "id_municipio"], how="left")
    else:
        df["total_beneficiarios_bolsa_familia"] = pd.NA
        df["valor_total_bolsa_familia"] = pd.NA

    df["ranking_prioridade_uf"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
    df["ranking_prioridade_brasil"] = pd.Series(pd.NA, index=df.index, dtype="Int64")

    filtro_prioridade = df["status_meta"].eq("Abaixo da meta") & df["distancia_meta"].notna()
    prioridade_uf = df.loc[filtro_prioridade].sort_values(
        ["ano", "ano_meta", "sigla_uf", "distancia_meta", "id_municipio"]
    )

    if not prioridade_uf.empty:
        ranking_uf = prioridade_uf.groupby(["ano", "ano_meta", "sigla_uf"]).cumcount() + 1

        df.loc[prioridade_uf.index, "ranking_prioridade_uf"] = pd.Series(
            ranking_uf.values,
            index=prioridade_uf.index,
            dtype="Int64",
        )

    prioridade_brasil = df.loc[filtro_prioridade].sort_values(
        ["ano", "ano_meta", "distancia_meta", "id_municipio"]
    )

    if not prioridade_brasil.empty:
        ranking_brasil = prioridade_brasil.groupby(["ano", "ano_meta"]).cumcount() + 1

        df.loc[prioridade_brasil.index, "ranking_prioridade_brasil"] = pd.Series(
            ranking_brasil.values,
            index=prioridade_brasil.index,
            dtype="Int64",
        )

    df["data_processamento_gold"] = EXECUTION_DATE

    colunas = [
        "ano",
        "id_municipio",
        "id_municipio_nome",
        "sigla_uf",
        "rede",
        "nivel_agregacao",
        "taxa_alfabetizacao",
        "nivel_alfabetizacao",
        "percentual_participacao",
        "ano_meta",
        "meta_alfabetizacao",
        "distancia_meta",
        "flag_meta_atingida",
        "status_meta",
        "total_beneficiarios_bolsa_familia",
        "valor_total_bolsa_familia",
        "ranking_prioridade_uf",
        "ranking_prioridade_brasil",
        "data_processamento_gold",
    ]

    return (
        df[[coluna for coluna in colunas if coluna in df.columns]]
        .sort_values(["ano", "sigla_uf", "id_municipio", "rede"])
        .reset_index(drop=True)
    )


def processar_evolucao_alfabetizacao(
    df_fato_resultado_brasil: pd.DataFrame,
) -> pd.DataFrame:
    """Processa série histórica de evolução."""
    df = (
        df_fato_resultado_brasil
        .groupby("ano")
        .agg({
            "taxa_alfabetizacao": "mean",
            "percentual_participacao": "sum",
        })
        .reset_index()
        .sort_values("ano")
    )
    
    df["variacao_taxa"] = df["taxa_alfabetizacao"].diff()
    df["variacao_percentual"] = df["percentual_participacao"].diff()
    
    return df.reset_index(drop=True)


def processar_resumo_status_meta(
    df_indicador_meta_brasil: pd.DataFrame,
    df_indicador_meta_uf: pd.DataFrame,
    df_indicador_meta_municipio: pd.DataFrame,
) -> pd.DataFrame:
    """Processa resumo de cumprimento de metas."""
    df_brasil = (
        df_indicador_meta_brasil
        .groupby(["ano", "status_meta"])
        .size()
        .reset_index(name="quantidade")
    )
    df_brasil["nivel"] = "Brasil"
    
    df_uf = (
        df_indicador_meta_uf
        .groupby(["ano", "status_meta"])
        .size()
        .reset_index(name="quantidade")
    )
    df_uf["nivel"] = "UF"
    
    df_municipio = (
        df_indicador_meta_municipio
        .groupby(["ano", "status_meta"])
        .size()
        .reset_index(name="quantidade")
    )
    df_municipio["nivel"] = "Município"
    
    df = pd.concat(
        [df_brasil, df_uf, df_municipio],
        ignore_index=True
    )
    
    return (
        df
        .sort_values(["ano", "nivel", "status_meta"])
        .reset_index(drop=True)
    )


def processar_camada_gold(data_processamento: date | None = None) -> None:
    """
    Processa todas as análises da camada Gold.

    `data_processamento` define a partição execution_date de destino;
    por padrão, a data corrente.
    """
    global EXECUTION_DATE

    if data_processamento is not None:
        EXECUTION_DATE = data_processamento.isoformat()

    VOLUMETRIA_GOLD.clear()

    print("Iniciando processamento da camada Gold")
    print("=" * 80)
    
    # Carregar Silver
    print("\n[CARREGAMENTO] Lendo tabelas Silver...")
    df_fato_resultado_brasil = carregar_silver("fato_resultado_brasil")
    df_fato_aluno_alfabetizacao = carregar_silver("fato_aluno_alfabetizacao")
    df_fato_resultado_meta_uf = carregar_silver("fato_resultado_meta_uf")
    df_fato_resultado_meta_municipio = carregar_silver("fato_resultado_meta_municipio")
    df_fato_meta_anual_brasil = carregar_silver("fato_meta_anual_brasil")
    df_fato_meta_anual_uf = carregar_silver("fato_meta_anual_uf")
    df_fato_meta_anual_municipio = carregar_silver("fato_meta_anual_municipio")
    df_dim_escola = carregar_silver("dim_escola")
    df_dim_municipio = carregar_silver("dim_municipio")
    df_dominio_regiao_uf = carregar_silver("dominio_regiao_uf")
    df_fato_fundeb = carregar_silver_opcional("fato_fundeb")
    df_fato_bolsa_familia_municipio = carregar_silver("fato_bolsa_familia_municipio")
    
    # Processar indicadores
    print("\n[PROCESSAMENTO] Gerando indicadores Gold...")

    df_alunos_enriquecidos = preparar_alunos_enriquecidos(
        df_fato_aluno_alfabetizacao,
        df_dim_escola,
        df_dim_municipio,
        df_dominio_regiao_uf,
    )

    df_base_modelagem = construir_base_modelagem_aluno(
        df_alunos_enriquecidos,
        df_fato_bolsa_familia_municipio,
        {
            "municipio": df_fato_meta_anual_municipio,
            "uf": df_fato_meta_anual_uf,
            "brasil": df_fato_meta_anual_brasil,
        },
    )
    df_base_modelagem["data_processamento_gold"] = EXECUTION_DATE
    salvar_gold(df_base_modelagem, "base_modelagem_aluno")
    del df_base_modelagem

    df_perfil_aluno_alfabetizacao = processar_perfil_aluno_alfabetizacao(
        df_alunos_enriquecidos,
    )
    salvar_gold(df_perfil_aluno_alfabetizacao, "perfil_aluno_alfabetizacao")

    df_indicador_presenca_avaliacao = processar_indicador_presenca_avaliacao(
        df_alunos_enriquecidos,
    )
    salvar_gold(df_indicador_presenca_avaliacao, "indicador_presenca_avaliacao")

    df_ranking_escolas_prioritarias = processar_ranking_escolas_prioritarias(
        df_alunos_enriquecidos,
    )
    salvar_gold(df_ranking_escolas_prioritarias, "ranking_escolas_prioritarias")

    df_indicador_desempenho_aluno = processar_indicador_desempenho_aluno(
        df_alunos_enriquecidos,
    )
    salvar_gold(df_indicador_desempenho_aluno, "indicador_desempenho_aluno")

    df_distribuicao_desempenho_aluno = processar_distribuicao_desempenho_aluno(
        df_alunos_enriquecidos,
    )
    salvar_gold(df_distribuicao_desempenho_aluno, "distribuicao_desempenho_aluno")

    df_indicador_meta_brasil = processar_indicador_meta_brasil(
        df_fato_resultado_brasil,
        df_fato_meta_anual_brasil,
    )
    salvar_gold(df_indicador_meta_brasil, "indicador_meta_brasil")

    df_evolucao_meta_resultado_brasil = processar_evolucao_meta_resultado_brasil(
        df_indicador_meta_brasil,
    )
    salvar_gold(
        df_evolucao_meta_resultado_brasil,
        "evolucao_meta_resultado_brasil",
    )

    df_indicador_meta_uf = processar_indicador_meta_uf(
        df_fato_resultado_meta_uf,
        df_fato_meta_anual_uf,
    )
    salvar_gold(df_indicador_meta_uf, "indicador_meta_uf")

    df_evolucao_meta_resultado_uf = processar_evolucao_meta_resultado_uf(
        df_indicador_meta_uf,
    )
    salvar_gold(
        df_evolucao_meta_resultado_uf,
        "evolucao_meta_resultado_uf",
    )

    if df_fato_fundeb is not None:
        df_meta_uf_fundeb = processar_meta_uf_fundeb(
            df_indicador_meta_uf,
            df_fato_fundeb,
        )
        salvar_gold(df_meta_uf_fundeb, "meta_uf_fundeb")

    df_meta_uf_bolsa_familia = processar_meta_uf_bolsa_familia(
        df_indicador_meta_uf,
        df_fato_bolsa_familia_municipio,
    )
    salvar_gold(df_meta_uf_bolsa_familia, "meta_uf_bolsa_familia")

    df_indicador_meta_regiao = processar_indicador_meta_regiao(
        df_indicador_meta_uf,
        df_dominio_regiao_uf,
    )
    salvar_gold(df_indicador_meta_regiao, "indicador_meta_regiao")
    
    df_ranking_uf_prioritaria = processar_ranking_uf_prioritaria(
        df_indicador_meta_uf,
    )
    salvar_gold(df_ranking_uf_prioritaria, "ranking_uf_prioritaria")
    
    df_indicador_meta_municipio = processar_indicador_meta_municipio(
        df_fato_resultado_meta_municipio,
        df_fato_meta_anual_municipio,
        df_dim_municipio,
    )
    salvar_gold(df_indicador_meta_municipio, "indicador_meta_municipio")

    df_evolucao_meta_resultado_municipio = processar_evolucao_meta_resultado_municipio(
        df_indicador_meta_municipio,
    )
    salvar_gold(
        df_evolucao_meta_resultado_municipio,
        "evolucao_meta_resultado_municipio",
    )

    df_ranking_territorial_prioridade = processar_ranking_territorial_prioridade(
        df_indicador_meta_municipio,
        df_dominio_regiao_uf,
    )
    salvar_gold(df_ranking_territorial_prioridade, "ranking_territorial_prioridade")

    df_desigualdade_territorial_uf = processar_desigualdade_territorial_uf(
        df_indicador_meta_municipio,
        df_dominio_regiao_uf,
    )
    salvar_gold(df_desigualdade_territorial_uf, "desigualdade_territorial_uf")

    df_mapa_calor_territorial = processar_mapa_calor_territorial(
        df_indicador_meta_municipio,
        df_dominio_regiao_uf,
    )
    salvar_gold(df_mapa_calor_territorial, "mapa_calor_territorial")

    df_indicador_alfabetizacao_municipio = processar_indicador_alfabetizacao_municipio(
        df_indicador_meta_municipio,
        df_dim_municipio,
        df_fato_bolsa_familia_municipio,
    )
    salvar_gold(
        df_indicador_alfabetizacao_municipio,
        "indicador_alfabetizacao_municipio",
    )
    
    df_ranking_municipio_prioritario = processar_ranking_municipio_prioritario(
        df_indicador_meta_municipio,
    )
    salvar_gold(df_ranking_municipio_prioritario, "ranking_municipio_prioritario")
    
    df_evolucao_alfabetizacao = processar_evolucao_alfabetizacao(
        df_fato_resultado_brasil,
    )
    salvar_gold(df_evolucao_alfabetizacao, "evolucao_alfabetizacao")
    
    df_resumo_status_meta = processar_resumo_status_meta(
        df_indicador_meta_brasil,
        df_indicador_meta_uf,
        df_indicador_meta_municipio,
    )
    salvar_gold(df_resumo_status_meta, "resumo_status_meta")

    print("\n[QUALIDADE] Registrando volumetria e cobertura da Gold...")
    registrar_qualidade_gold(
        {
            "indicador_meta_uf": medir_cobertura(
                df_indicador_meta_uf, "sigla_uf", TOTAL_UF_BRASIL
            ),
            "indicador_meta_municipio": medir_cobertura(
                df_indicador_meta_municipio,
                "id_municipio",
                df_dim_municipio["id_municipio"].nunique(),
            ),
        }
    )

    print("\n" + "=" * 80)
    print("Processamento da camada Gold finalizado com sucesso!")
