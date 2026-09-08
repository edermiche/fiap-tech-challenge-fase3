import pandas as pd
import pytest

from src.gold.base_modelagem import construir_base_modelagem_aluno, preparar_metas
from src.gold.processar_gold import processar_indicador_meta_brasil
from src.bronze.leitores import listar_arquivos_entidade


def alunos_exemplo():
    return pd.DataFrame({
        "ano": [2023, 2023, 2024, 2024, 2024],
        "id_municipio": ["1100015"] * 5, "id_escola": ["E1"] * 5,
        "id_aluno": ["A", "B", "C", "D", "E"], "serie": ["2 ano"] * 5,
        "rede": ["Municipal"] * 5, "id_municipio_nome": ["Cidade"] * 5,
        "sigla_uf": ["RO"] * 5, "regiao_brasil": ["Norte"] * 5,
        "presenca": ["Presente", "Ausente", "Presente", "Presente", "Presente"],
        "proficiencia": [800, None, 700, None, 743],
        "alfabetizado": ["Sim", "Não", "Não", "Não", "Sim"],
    })


def bolsa_exemplo():
    return pd.DataFrame({"ano_competencia": [2023, 2024], "id_municipio": ["1100015"] * 2,
                         "total_beneficiarios": [10, 999], "valor_total_pago": [6000, 999999]})


def test_historico_defasado_e_rotulos_sem_medicao():
    base = construir_base_modelagem_aluno(alunos_exemplo(), bolsa_exemplo(), {})
    assert len(base) == 5
    assert base.loc[base.ano.eq(2023), "total_pagamentos_bolsa_familia_anterior"].isna().all()
    atual = base.loc[base.ano.eq(2024)]
    assert atual.total_pagamentos_bolsa_familia_anterior.eq(10).all()
    assert atual.taxa_alfabetizacao_municipio_anterior.eq(100).all()
    assert "taxa_alfabetizacao_escola_anterior" not in atual
    assert atual.taxa_presenca_municipio_anterior.eq(50).all()
    assert base.loc[base.id_aluno.isin(["B", "D"]), "alfabetizado_binario"].isna().all()
    assert base.loc[base.id_aluno.eq("E"), "alfabetizado_binario"].item() == 1
    assert "proficiencia" not in base


def test_mudar_resultado_atual_nao_muda_features_do_mesmo_ano():
    from src.gold.base_modelagem import FEATURES
    alunos = alunos_exemplo()
    antes = construir_base_modelagem_aluno(alunos, bolsa_exemplo(), {})
    alunos.loc[alunos.ano.eq(2024), ["proficiencia", "alfabetizado"]] = [850, "Sim"]
    depois = construir_base_modelagem_aluno(alunos, bolsa_exemplo(), {})
    pd.testing.assert_frame_equal(antes[FEATURES], depois[FEATURES])


def test_juncao_duplicada_e_rejeitada():
    bolsa = bolsa_exemplo()
    with pytest.raises(pd.errors.MergeError):
        construir_base_modelagem_aluno(alunos_exemplo(), pd.concat([bolsa, bolsa]), {})


def test_meta_futura_ou_revisada_nao_substitui_versao_anterior():
    meta = pd.DataFrame({"ano": [2023, 2024, 2025], "ano_meta": [2024] * 3,
                         "rede": ["Pública"] * 3, "meta_alfabetizacao": [60, 70, 80]})
    resultado = preparar_metas(meta, "brasil")
    assert resultado.meta_alfabetizacao_brasil.tolist() == [60]
    assert resultado.ano_base_meta_brasil.tolist() == [2023]


def test_resultado_sem_meta_continua_na_gold():
    resultados = pd.DataFrame({"ano": [2023, 2024], "rede": ["Pública"] * 2,
                               "nivel_agregacao": ["Brasil"] * 2, "taxa_alfabetizacao": [55, 60]})
    metas = pd.DataFrame({"ano": [2023, 2024], "ano_meta": [2024, 2024],
                         "rede": ["Pública"] * 2, "nivel_agregacao": ["Brasil"] * 2,
                         "meta_alfabetizacao": [60, 60]})
    gold = processar_indicador_meta_brasil(resultados, metas)
    assert len(gold) == 2
    assert gold.loc[gold.ano.eq(2023), "status_meta"].item() == "Sem informação"
    assert gold.ano_meta.tolist() == [2023, 2024]


def test_regiao_conta_ufs_sem_meta_sem_dividir_o_mesmo_ano():
    from src.gold.processar_gold import processar_indicador_meta_regiao
    uf = pd.DataFrame({"ano": [2024, 2024], "ano_meta": [2024, 2024],
                       "sigla_uf": ["RO", "AC"], "rede": ["Pública"] * 2,
                       "taxa_alfabetizacao": [65, 55], "meta_alfabetizacao": [60, None],
                       "distancia_meta": [5, None], "status_meta": ["Meta atingida", "Sem informação"]})
    regioes = pd.DataFrame({"sigla_uf": ["RO", "AC"], "regiao_brasil": ["Norte", "Norte"]})
    resultado = processar_indicador_meta_regiao(uf, regioes)
    assert len(resultado) == 1
    assert resultado.total_ufs.item() == 2
    assert resultado.total_sem_informacao.item() == 1


def test_bronze_usa_um_snapshot_completo(tmp_path):
    for dia in ["2026-07-08", "2026-09-07"]:
        pasta = tmp_path / f"execution_date={dia}"
        pasta.mkdir()
        (pasta / "alunos.parquet").touch()
    assert listar_arquivos_entidade(tmp_path) == [tmp_path / "execution_date=2026-09-07/alunos.parquet"]


def test_codigo_escolar_em_municipios_diferentes_preserva_os_dois_anos():
    from datetime import date
    from src.silver.transformacoes import criar_dim_escola
    from src.silver.qualidade import aplicar_qualidade_silver
    origem = pd.DataFrame({"ano": [2023, 2024], "id_escola": ["E1", "E1"],
                           "id_municipio": ["1100015", "3550308"],
                           "id_municipio_nome": ["Cidade A", "Cidade B"]})
    dim = criar_dim_escola(origem, date(2026, 9, 7))
    tabelas, _ = aplicar_qualidade_silver({"dim_escola": dim})
    assert len(tabelas["dim_escola"]) == 2
