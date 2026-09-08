"""
Testes do gate de qualidade e do histórico gold.metricas_qualidade.

Cobrem as três garantias que o pipeline passou a oferecer:

1. extração corrompida (percentual fora de [0,100]) **barra** a execução;
2. deduplicação de dimensão derivada de fato **não** barra;
3. as métricas ficam gravadas e a execução seguinte se compara com a anterior.

Execução: `pytest tests/`
"""
import pandas as pd
import pytest

from src.qualidade import armazenamento
from src.qualidade.metricas import (
    QualidadeInsuficienteError,
    avaliar_gates,
    coletar_metricas_cobertura,
    coletar_metricas_silver,
    comparar_cobertura_com_safra_anterior,
    comparar_com_safra_anterior,
)


DATA_EXECUCAO = "2026-09-02"
DATA_ANTERIOR = "2026-08-31"


def montar_fato_resultado_uf(taxas, flags_validas):
    """Monta um fato_resultado_uf mínimo, com a flag de intervalo já aplicada."""
    return pd.DataFrame(
        {
            "ano": [2024] * len(taxas),
            "sigla_uf": [f"U{indice}" for indice in range(len(taxas))],
            "serie": ["2 ano"] * len(taxas),
            "rede": ["publica"] * len(taxas),
            "taxa_alfabetizacao": taxas,
            "flag_taxa_alfabetizacao_valido": flags_validas,
        }
    )


def coletar(tabelas, volumetria=None):
    volumetria = volumetria or {
        nome: (len(df), len(df), len(df)) for nome, df in tabelas.items()
    }

    return coletar_metricas_silver(tabelas, volumetria, DATA_EXECUCAO)


def test_percentual_fora_do_intervalo_barra_a_execucao():
    """O cenário do enunciado: extração com percentuais inválidos não publica."""
    tabelas = {
        "fato_resultado_uf": montar_fato_resultado_uf(
            taxas=[150.0, 220.0, 99.0],
            flags_validas=[False, False, True],
        )
    }

    with pytest.raises(QualidadeInsuficienteError) as erro:
        avaliar_gates(coletar(tabelas))

    assert "percentual_fora_intervalo" in str(erro.value)


def test_percentual_fora_do_intervalo_dentro_do_limite_nao_barra():
    """Um caso isolado (abaixo do limite de 5%) alerta, mas deixa passar."""
    tabelas = {
        "fato_resultado_uf": montar_fato_resultado_uf(
            taxas=[150.0] + [80.0] * 99,
            flags_validas=[False] + [True] * 99,
        )
    }

    assert avaliar_gates(coletar(tabelas)).empty


def test_modo_alertar_registra_mas_nao_interrompe(monkeypatch):
    monkeypatch.setenv("QUALIDADE_MODO", "alertar")
    tabelas = {
        "fato_resultado_uf": montar_fato_resultado_uf(
            taxas=[150.0, 220.0],
            flags_validas=[False, False],
        )
    }

    violacoes = avaliar_gates(coletar(tabelas))

    assert len(violacoes) == 1


def test_deduplicacao_de_dimensao_nao_barra():
    """
    dim_escola nasce do fato de alunos: a deduplicação descarta a maior
    parte das linhas por construção, e isso não pode reprovar a execução.
    """
    dim_escola = pd.DataFrame(
        {
            "ano": [2024, 2024],
            "id_escola": ["1", "2"],
            "id_municipio": ["3500000", "3500001"],
        }
    )
    metricas = coletar_metricas_silver(
        {"dim_escola": dim_escola},
        {"dim_escola": (1000, 1000, 2)},
        DATA_EXECUCAO,
    )

    duplicidade = metricas[metricas["regra"] == "duplicidade_removida"].iloc[0]

    assert duplicidade["severidade"] == "alerta"
    assert avaliar_gates(metricas).empty


def test_chave_primaria_duplicada_barra_a_execucao():
    fato = montar_fato_resultado_uf(taxas=[80.0, 80.0], flags_validas=[True, True])
    fato["sigla_uf"] = ["SP", "SP"]

    with pytest.raises(QualidadeInsuficienteError):
        avaliar_gates(coletar({"fato_resultado_uf": fato}))


def test_comparacao_com_safra_anterior_detecta_aumento_de_ausencia():
    fato = montar_fato_resultado_uf(taxas=[80.0, None], flags_validas=[True, True])
    fato["flag_dado_ausente_fonte"] = [False, True]

    metricas = coletar({"fato_resultado_uf": fato})
    anterior = metricas.copy()
    anterior["data_execucao"] = DATA_ANTERIOR
    anterior.loc[
        anterior["regra"] == "metrica_ausente_fonte", "percentual_violacao"
    ] = 10.0

    comparadas = comparar_com_safra_anterior(metricas, anterior)
    aumento = comparadas[comparadas["regra"] == "aumento_ausencia_safra_anterior"]

    assert len(aumento) == 1
    # 50% de ausência agora contra 10% na safra anterior: 40 pontos de alta.
    assert aumento.iloc[0]["percentual_violacao"] == pytest.approx(40.0)
    assert aumento.iloc[0]["status"] == "alerta"


def test_cobertura_territorial_registra_uf_ausente():
    """
    AC e DF não têm meta 2024 na fonte e RR não tem resultado: a Gold
    publica 24 das 27 UFs, e isso precisa aparecer no histórico.
    """
    metricas = coletar_metricas_cobertura(
        {"indicador_meta_uf": {2024: (24, 27), 2025: (26, 27)}},
        DATA_EXECUCAO,
    )

    de_2024 = metricas[metricas["escopo"] == "ano=2024"].iloc[0]

    assert de_2024["registros_violando"] == 3
    assert de_2024["percentual_violacao"] == pytest.approx(11.11, abs=0.01)
    assert de_2024["status"] == "alerta"
    # A cobertura não barra: ausência estrutural da fonte não é erro do pipeline.
    assert avaliar_gates(metricas).empty


def test_cobertura_dentro_do_esperado_nao_alerta():
    metricas = coletar_metricas_cobertura(
        {"indicador_meta_municipio": {2024: (5232, 5550)}},
        DATA_EXECUCAO,
    )

    assert metricas.iloc[0]["status"] == "ok"


def test_queda_de_cobertura_entre_safras_alerta():
    atual = coletar_metricas_cobertura(
        {"indicador_meta_uf": {2024: (20, 27)}},
        DATA_EXECUCAO,
    )
    anterior = coletar_metricas_cobertura(
        {"indicador_meta_uf": {2024: (24, 27)}},
        DATA_ANTERIOR,
    )

    comparadas = comparar_cobertura_com_safra_anterior(atual, anterior)
    queda = comparadas[comparadas["regra"] == "queda_cobertura_safra_anterior"]

    assert len(queda) == 1
    # 4 UFs que existiam na safra anterior sumiram desta.
    assert queda.iloc[0]["registros_violando"] == 4
    assert queda.iloc[0]["status"] == "alerta"


def test_cobertura_estavel_entre_safras_nao_alerta():
    cobertura = {"indicador_meta_uf": {2024: (24, 27)}}
    atual = coletar_metricas_cobertura(cobertura, DATA_EXECUCAO)
    anterior = coletar_metricas_cobertura(cobertura, DATA_ANTERIOR)

    comparadas = comparar_cobertura_com_safra_anterior(atual, anterior)
    queda = comparadas[comparadas["regra"] == "queda_cobertura_safra_anterior"]

    assert queda.iloc[0]["status"] == "ok"


def test_historico_persistido_permite_ler_a_safra_anterior(tmp_path, monkeypatch):
    monkeypatch.setattr(armazenamento, "GOLD_PATH", tmp_path)
    monkeypatch.delenv("LAKE_S3_BUCKET", raising=False)

    fato = montar_fato_resultado_uf(taxas=[80.0], flags_validas=[True])
    metricas_anteriores = coletar({"fato_resultado_uf": fato})
    metricas_anteriores["data_execucao"] = DATA_ANTERIOR

    armazenamento.salvar_metricas_qualidade(metricas_anteriores, DATA_ANTERIOR)

    assert armazenamento.listar_execucoes() == [DATA_ANTERIOR]

    recuperadas = armazenamento.ler_metricas_safra_anterior(DATA_EXECUCAO)

    assert recuperadas is not None
    assert len(recuperadas) == len(metricas_anteriores)
    assert armazenamento.ler_metricas_safra_anterior(DATA_ANTERIOR) is None


def test_gravacao_da_gold_preserva_as_metricas_da_silver(tmp_path, monkeypatch):
    monkeypatch.setattr(armazenamento, "GOLD_PATH", tmp_path)
    monkeypatch.delenv("LAKE_S3_BUCKET", raising=False)

    fato = montar_fato_resultado_uf(taxas=[80.0], flags_validas=[True])
    metricas_silver = coletar({"fato_resultado_uf": fato})
    armazenamento.salvar_metricas_qualidade(metricas_silver, DATA_EXECUCAO)

    metricas_gold = metricas_silver.head(1).copy()
    metricas_gold["camada"] = "gold"
    armazenamento.salvar_metricas_qualidade(metricas_gold, DATA_EXECUCAO)

    gravadas = armazenamento.ler_metricas_execucao(DATA_EXECUCAO)
    contagem = gravadas["camada"].value_counts()

    assert contagem["silver"] == len(metricas_silver)
    assert contagem["gold"] == 1
