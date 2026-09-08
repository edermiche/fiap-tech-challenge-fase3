# As anotações `X | None` precisam ser adiadas: o Glue Python Shell roda 3.9.
from __future__ import annotations

from datetime import date

import pandas as pd

from src.silver.config import (
    CHAVE_NATURAL_ALUNOS,
    COLUNAS_METAS,
    COLUNAS_NIVEIS,
    COLUNAS_NUMERICAS_META,
    COLUNAS_NUMERICAS_RESULTADO,
    MAPA_REGIAO_UF,
)


def padronizar_texto(valor):
    if pd.isna(valor):
        return valor

    return str(valor).strip()


def padronizar_sigla_uf(valor):
    if pd.isna(valor):
        return valor

    return str(valor).strip().upper()


def padronizar_codigo(valor):
    if pd.isna(valor):
        return valor

    return str(valor).strip()


def validar_percentual(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    df_validado = df.copy()

    for coluna in colunas:
        if coluna in df_validado.columns:
            df_validado[f"flag_{coluna}_valido"] = (
                df_validado[coluna].isna()
                | df_validado[coluna].between(0, 100)
            )

    return df_validado

def sinalizar_dado_ausente_fonte(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """
    Sinaliza registros cuja métrica veio nula da fonte (INEP/Saeb).

    Extração Bronze é literal (queries/bronze/, SELECT sem filtro de métricas),
    portanto o nulo é da origem. A decisão de projeto é NÃO imputar
    valores: o registro é mantido e marcado, preservando a
    rastreabilidade da ausência na fonte.
    """
    df_sinalizado = df.copy()

    colunas_existentes = [c for c in colunas if c in df_sinalizado.columns]
    if not colunas_existentes:
        df_sinalizado["flag_dado_ausente_fonte"] = False
        return df_sinalizado

    df_sinalizado["flag_dado_ausente_fonte"] = (
        df_sinalizado[colunas_existentes].isna().any(axis=1)
    )

    return df_sinalizado


def converter_colunas_numericas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    df_convertido = df.copy()

    for coluna in colunas:
        if coluna in df_convertido.columns:
            df_convertido[coluna] = pd.to_numeric(df_convertido[coluna], errors="coerce")

    return df_convertido


def padronizar_uf(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano"] = df_base["ano"].astype("Int64")
    df_base["sigla_uf"] = df_base["sigla_uf"].apply(padronizar_sigla_uf)
    df_base["sigla_uf_nome"] = df_base["sigla_uf_nome"].apply(padronizar_texto)
    df_base["serie"] = df_base["serie"].apply(padronizar_texto)
    df_base["rede"] = df_base["rede"].apply(padronizar_texto)

    df_base = converter_colunas_numericas(df_base, COLUNAS_NUMERICAS_RESULTADO)

    return df_base.drop_duplicates().reset_index(drop=True)


def padronizar_municipio(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano"] = df_base["ano"].astype("Int64")
    df_base["id_municipio"] = df_base["id_municipio"].apply(padronizar_codigo)
    df_base["id_municipio_nome"] = df_base["id_municipio_nome"].apply(padronizar_texto)
    df_base["serie"] = df_base["serie"].apply(padronizar_texto)
    df_base["rede"] = df_base["rede"].apply(padronizar_texto)

    df_base = converter_colunas_numericas(df_base, COLUNAS_NUMERICAS_RESULTADO)

    return df_base.drop_duplicates().reset_index(drop=True)


def padronizar_meta_brasil(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano"] = df_base["ano"].astype("Int64")
    df_base["rede"] = df_base["rede"].apply(padronizar_texto)

    df_base = converter_colunas_numericas(df_base, COLUNAS_NUMERICAS_META)

    return df_base.drop_duplicates().reset_index(drop=True)


def padronizar_meta_uf(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano"] = df_base["ano"].astype("Int64")
    df_base["sigla_uf"] = df_base["sigla_uf"].apply(padronizar_sigla_uf)
    df_base["sigla_uf_nome"] = df_base["sigla_uf_nome"].apply(padronizar_texto)
    df_base["rede"] = df_base["rede"].apply(padronizar_texto)

    df_base = converter_colunas_numericas(df_base, COLUNAS_NUMERICAS_META)

    return df_base.drop_duplicates().reset_index(drop=True)


def padronizar_meta_municipio(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano"] = df_base["ano"].astype("Int64")
    df_base["id_municipio"] = df_base["id_municipio"].apply(padronizar_codigo)
    df_base["id_municipio_nome"] = df_base["id_municipio_nome"].apply(padronizar_texto)
    df_base["rede"] = df_base["rede"].apply(padronizar_texto)

    if "nivel_alfabetizacao" in df_base.columns:
        df_base["nivel_alfabetizacao"] = df_base["nivel_alfabetizacao"].astype("Int64")

    df_base = converter_colunas_numericas(df_base, COLUNAS_NUMERICAS_META)

    return df_base.drop_duplicates().reset_index(drop=True)


def padronizar_alunos(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano"] = df_base["ano"].astype("Int64")
    df_base["id_municipio"] = df_base["id_municipio"].apply(padronizar_codigo)
    df_base["id_municipio_nome"] = df_base["id_municipio_nome"].apply(padronizar_texto)
    df_base["id_escola"] = df_base["id_escola"].apply(padronizar_codigo)
    df_base["id_aluno"] = df_base["id_aluno"].apply(padronizar_codigo)
    df_base["caderno"] = df_base["caderno"].apply(padronizar_texto)
    df_base["serie"] = df_base["serie"].apply(padronizar_texto)
    df_base["rede"] = df_base["rede"].apply(padronizar_texto)
    df_base["presenca"] = df_base["presenca"].apply(padronizar_texto)
    df_base["preenchimento_caderno"] = df_base["preenchimento_caderno"].apply(padronizar_texto)
    df_base["alfabetizado"] = df_base["alfabetizado"].apply(padronizar_texto)

    df_base = converter_colunas_numericas(df_base, ["proficiencia", "peso_aluno"])

    return df_base.drop_duplicates().reset_index(drop=True)


def combinar_alunos_batch_streaming(
    df_alunos_batch: pd.DataFrame,
    df_alunos_streaming: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Une os alunos ingeridos por batch e por streaming em uma única base.

    Os eventos de streaming carregam o mesmo dado de alunos do batch
    (o producer reemite os registros da avaliação), então entram na mesma
    base padronizada. Quando o mesmo registro chega pelos dois modos, o
    batch prevalece (keep="first"); a coluna modo_ingestao preserva a
    origem de cada registro que sobrevive à deduplicação.
    """
    df_batch = padronizar_alunos(df_alunos_batch)

    if df_alunos_streaming is None or df_alunos_streaming.empty:
        return df_batch

    df_streaming = padronizar_alunos(df_alunos_streaming)
    df = pd.concat([df_batch, df_streaming], ignore_index=True)

    chave_natural = [
        coluna
        for coluna in CHAVE_NATURAL_ALUNOS
        if coluna in df.columns
    ]

    print(
        f"Alunos híbrido: {len(df_batch)} batch + {len(df_streaming)} streaming"
    )

    return df.drop_duplicates(subset=chave_natural, keep="first").reset_index(drop=True)


def padronizar_bolsa_familia_municipio(df: pd.DataFrame) -> pd.DataFrame:
    df_base = df.copy()

    df_base["ano_competencia"] = df_base["ano_competencia"].astype("Int64")
    df_base["id_municipio"] = df_base["id_municipio"].apply(padronizar_codigo)
    df_base["sigla_uf"] = df_base["sigla_uf"].apply(padronizar_sigla_uf)

    df_base = converter_colunas_numericas(
        df_base, ["total_beneficiarios", "valor_total_pago"]
    )

    return df_base.drop_duplicates().reset_index(drop=True)


def criar_dominio_regiao_uf(data_processamento: date) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {"sigla_uf": sigla_uf, "regiao_brasil": regiao_brasil}
            for sigla_uf, regiao_brasil in MAPA_REGIAO_UF.items()
        ]
    )
    df["data_processamento_silver"] = data_processamento.isoformat()

    return df.sort_values(["regiao_brasil", "sigla_uf"]).reset_index(drop=True)


def criar_dim_uf(
    df_uf_base: pd.DataFrame,
    df_dominio_regiao_uf: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = (
        df_uf_base[["sigla_uf", "sigla_uf_nome"]]
        .drop_duplicates()
        .merge(
            df_dominio_regiao_uf[["sigla_uf", "regiao_brasil"]],
            on="sigla_uf",
            how="left",
        )
        .sort_values("sigla_uf")
        .reset_index(drop=True)
    )
    df["data_processamento_silver"] = data_processamento.isoformat()

    return df


def criar_dim_municipio(df_municipio_base: pd.DataFrame, data_processamento: date) -> pd.DataFrame:
    df = (
        df_municipio_base[["id_municipio", "id_municipio_nome"]]
        .drop_duplicates()
        .sort_values("id_municipio")
        .reset_index(drop=True)
    )
    df["data_processamento_silver"] = data_processamento.isoformat()

    return df


def criar_dim_escola(df_alunos_base: pd.DataFrame, data_processamento: date) -> pd.DataFrame:
    df = (
        df_alunos_base[["ano", "id_escola", "id_municipio", "id_municipio_nome"]]
        .drop_duplicates()
        .sort_values(["ano", "id_municipio", "id_escola"])
        .reset_index(drop=True)
    )
    df["data_processamento_silver"] = data_processamento.isoformat()

    return df


def criar_fato_resultado_uf(df_uf_base: pd.DataFrame, data_processamento: date) -> pd.DataFrame:
    df = df_uf_base[
        ["ano", "sigla_uf", "serie", "rede", "taxa_alfabetizacao", "media_portugues"]
    ].copy()
    df = validar_percentual(df, ["taxa_alfabetizacao"])
    df = sinalizar_dado_ausente_fonte(df, ["taxa_alfabetizacao", "media_portugues"])
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "sigla_uf", "serie", "rede"])
        .reset_index(drop=True)
    )


def criar_fato_resultado_municipio(
    df_municipio_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_municipio_base[
        ["ano", "id_municipio", "serie", "rede", "taxa_alfabetizacao", "media_portugues"]
    ].copy()
    df = validar_percentual(df, ["taxa_alfabetizacao"])
    df = sinalizar_dado_ausente_fonte(df, ["taxa_alfabetizacao", "media_portugues"])
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "id_municipio", "serie", "rede"])
        .reset_index(drop=True)
    )


def criar_fato_resultado_brasil(
    df_meta_brasil_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_meta_brasil_base[
        ["ano", "rede", "taxa_alfabetizacao", "percentual_participacao"]
    ].copy()
    df = validar_percentual(df, ["taxa_alfabetizacao", "percentual_participacao"])
    df = sinalizar_dado_ausente_fonte(df, ["taxa_alfabetizacao", "percentual_participacao"])
    df["nivel_agregacao"] = "Brasil"
    df["data_processamento_silver"] = data_processamento.isoformat()

    return df.drop_duplicates().sort_values(["ano", "rede"]).reset_index(drop=True)


def criar_fato_resultado_meta_uf(
    df_meta_uf_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_meta_uf_base[
        ["ano", "sigla_uf", "rede", "taxa_alfabetizacao", "percentual_participacao"]
    ].copy()
    df = validar_percentual(df, ["taxa_alfabetizacao", "percentual_participacao"])
    df = sinalizar_dado_ausente_fonte(df, ["taxa_alfabetizacao", "percentual_participacao"])
    df["nivel_agregacao"] = "UF"
    df["data_processamento_silver"] = data_processamento.isoformat()
    
    return (
        df.drop_duplicates()
        .sort_values(["ano", "sigla_uf", "rede"])
        .reset_index(drop=True)
    )


def criar_fato_resultado_meta_municipio(
    df_meta_municipio_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_meta_municipio_base[
        [
            "ano",
            "id_municipio",
            "rede",
            "taxa_alfabetizacao",
            "nivel_alfabetizacao",
            "percentual_participacao",
        ]
    ].copy()
    df = validar_percentual(df, ["taxa_alfabetizacao", "percentual_participacao"])
    df = sinalizar_dado_ausente_fonte(df, ["taxa_alfabetizacao", "percentual_participacao"])
    df["nivel_agregacao"] = "Municipio"
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "id_municipio", "rede", "nivel_alfabetizacao"])
        .reset_index(drop=True)
    )


def criar_fato_distribuicao_nivel_uf(
    df_uf_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_uf_base.melt(
        id_vars=["ano", "sigla_uf", "serie", "rede"],
        value_vars=COLUNAS_NIVEIS,
        var_name="nivel_alfabetizacao",
        value_name="proporcao_alunos",
    )
    df["nivel_alfabetizacao"] = (
        df["nivel_alfabetizacao"].str.extract(r"(\d+)").astype("Int64")
    )
    df = validar_percentual(df, ["proporcao_alunos"])
    df = sinalizar_dado_ausente_fonte(df, ["proporcao_alunos"])
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "sigla_uf", "serie", "rede", "nivel_alfabetizacao"])
        .reset_index(drop=True)
    )


def criar_fato_distribuicao_nivel_municipio(
    df_municipio_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_municipio_base.melt(
        id_vars=["ano", "id_municipio", "serie", "rede"],
        value_vars=COLUNAS_NIVEIS,
        var_name="nivel_alfabetizacao",
        value_name="proporcao_alunos",
    )
    df["nivel_alfabetizacao"] = (
        df["nivel_alfabetizacao"].str.extract(r"(\d+)").astype("Int64")
    )
    df = validar_percentual(df, ["proporcao_alunos"])
    df = sinalizar_dado_ausente_fonte(df, ["proporcao_alunos"])
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "id_municipio", "serie", "rede", "nivel_alfabetizacao"])
        .reset_index(drop=True)
    )


def criar_fato_meta_anual_brasil(
    df_meta_brasil_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_meta_brasil_base.melt(
        id_vars=["ano", "rede"],
        value_vars=COLUNAS_METAS,
        var_name="ano_meta",
        value_name="meta_alfabetizacao",
    )
    df["ano_meta"] = df["ano_meta"].str.extract(r"(\d{4})").astype("Int64")
    df = validar_percentual(df, ["meta_alfabetizacao"])
    df["nivel_agregacao"] = "Brasil"
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "rede", "ano_meta"])
        .reset_index(drop=True)
    )


def criar_fato_meta_anual_uf(
    df_meta_uf_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_meta_uf_base.melt(
        id_vars=["ano", "sigla_uf", "rede"],
        value_vars=COLUNAS_METAS,
        var_name="ano_meta",
        value_name="meta_alfabetizacao",
    )
    df["ano_meta"] = df["ano_meta"].str.extract(r"(\d{4})").astype("Int64")
    df = validar_percentual(df, ["meta_alfabetizacao"])
    df["nivel_agregacao"] = "UF"
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "sigla_uf", "rede", "ano_meta"])
        .reset_index(drop=True)
    )


def criar_fato_meta_anual_municipio(
    df_meta_municipio_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_meta_municipio_base.melt(
        id_vars=["ano", "id_municipio", "rede"],
        value_vars=COLUNAS_METAS,
        var_name="ano_meta",
        value_name="meta_alfabetizacao",
    )
    df["ano_meta"] = df["ano_meta"].str.extract(r"(\d{4})").astype("Int64")
    df = validar_percentual(df, ["meta_alfabetizacao"])
    df["nivel_agregacao"] = "Municipio"
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "id_municipio", "rede", "ano_meta"])
        .reset_index(drop=True)
    )


def criar_fato_aluno_alfabetizacao(
    df_alunos_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    colunas = [
        "ano",
        "id_aluno",
        "id_escola",
        "id_municipio",
        "serie",
        "rede",
        "caderno",
        "presenca",
        "preenchimento_caderno",
        "alfabetizado",
        "proficiencia",
        "peso_aluno",
        "modo_ingestao",
    ]
    df = df_alunos_base[
        [coluna for coluna in colunas if coluna in df_alunos_base.columns]
    ].copy()

    df["flag_id_aluno_valido"] = df["id_aluno"].notna() & (df["id_aluno"] != "")
    df["flag_id_escola_valido"] = df["id_escola"].notna() & (df["id_escola"] != "")
    df["flag_id_municipio_valido"] = df["id_municipio"].notna() & (df["id_municipio"] != "")
    df["flag_proficiencia_valida"] = df["proficiencia"].isna() | (df["proficiencia"] >= 0)
    df["flag_peso_aluno_valido"] = df["peso_aluno"].isna() | (df["peso_aluno"] > 0)
    df["flag_presenca_preenchida"] = df["presenca"].notna() & (df["presenca"] != "")
    df["flag_alfabetizado_preenchido"] = df["alfabetizado"].notna() & (df["alfabetizado"] != "")
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano", "id_municipio", "id_escola", "id_aluno"])
        .reset_index(drop=True)
    )


def criar_fato_bolsa_familia_municipio(
    df_bolsa_familia_base: pd.DataFrame,
    data_processamento: date,
) -> pd.DataFrame:
    df = df_bolsa_familia_base[
        [
            "ano_competencia",
            "id_municipio",
            "sigla_uf",
            "total_beneficiarios",
            "valor_total_pago",
        ]
    ].copy()

    df["flag_total_beneficiarios_valido"] = df["total_beneficiarios"].isna() | (
        df["total_beneficiarios"] >= 0
    )
    df["flag_valor_total_pago_valido"] = df["valor_total_pago"].isna() | (
        df["valor_total_pago"] >= 0
    )
    df["data_processamento_silver"] = data_processamento.isoformat()

    return (
        df.drop_duplicates()
        .sort_values(["ano_competencia", "sigla_uf", "id_municipio"])
        .reset_index(drop=True)
    )


def transformar_bronze_para_silver(
    dados_bronze: dict[str, pd.DataFrame],
    data_processamento: date,
) -> dict[str, pd.DataFrame]:
    df_uf_base = padronizar_uf(dados_bronze["uf"])
    df_municipio_base = padronizar_municipio(dados_bronze["municipio"])
    df_meta_brasil_base = padronizar_meta_brasil(dados_bronze["meta_alfabetizacao_brasil"])
    df_meta_uf_base = padronizar_meta_uf(dados_bronze["meta_alfabetizacao_uf"])
    df_meta_municipio_base = padronizar_meta_municipio(
        dados_bronze["meta_alfabetizacao_municipio"]
    )
    df_alunos_base = combinar_alunos_batch_streaming(
        dados_bronze["alunos"],
        dados_bronze.get("alunos_streaming"),
    )
    df_bolsa_familia_base = padronizar_bolsa_familia_municipio(
        dados_bronze["bolsa_familia_municipio"]
    )

    df_dominio_regiao_uf = criar_dominio_regiao_uf(data_processamento)

    return {
        "dominio_regiao_uf": df_dominio_regiao_uf,
        "dim_uf": criar_dim_uf(df_uf_base, df_dominio_regiao_uf, data_processamento),
        "dim_municipio": criar_dim_municipio(df_municipio_base, data_processamento),
        "dim_escola": criar_dim_escola(df_alunos_base, data_processamento),
        "fato_resultado_brasil": criar_fato_resultado_brasil(
            df_meta_brasil_base,
            data_processamento,
        ),
        "fato_resultado_uf": criar_fato_resultado_uf(df_uf_base, data_processamento),
        "fato_resultado_municipio": criar_fato_resultado_municipio(
            df_municipio_base,
            data_processamento,
        ),
        "fato_resultado_meta_uf": criar_fato_resultado_meta_uf(
            df_meta_uf_base,
            data_processamento,
        ),
        "fato_resultado_meta_municipio": criar_fato_resultado_meta_municipio(
            df_meta_municipio_base,
            data_processamento,
        ),
        "fato_meta_anual_brasil": criar_fato_meta_anual_brasil(
            df_meta_brasil_base,
            data_processamento,
        ),
        "fato_meta_anual_uf": criar_fato_meta_anual_uf(
            df_meta_uf_base,
            data_processamento,
        ),
        "fato_meta_anual_municipio": criar_fato_meta_anual_municipio(
            df_meta_municipio_base,
            data_processamento,
        ),
        "fato_distribuicao_nivel_uf": criar_fato_distribuicao_nivel_uf(
            df_uf_base,
            data_processamento,
        ),
        "fato_distribuicao_nivel_municipio": criar_fato_distribuicao_nivel_municipio(
            df_municipio_base,
            data_processamento,
        ),
        "fato_aluno_alfabetizacao": criar_fato_aluno_alfabetizacao(
            df_alunos_base,
            data_processamento,
        ),
        "fato_bolsa_familia_municipio": criar_fato_bolsa_familia_municipio(
            df_bolsa_familia_base,
            data_processamento,
        ),
    }
