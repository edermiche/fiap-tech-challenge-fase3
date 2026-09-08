import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from src.gold.enriquecer_modelagem import juntar_contextos, aplicar_historico_anterior
from src.silver.enriquecimento_oficial import agregar_censo, ler_populacao, ler_alunos_2025, INDICADORES


def escolas():
    return pd.DataFrame({"NU_ANO_CENSO": [2023] * 3, "CO_MUNICIPIO": ["1100015"] * 3,
                         "CO_ENTIDADE": ["1", "2", "3"], "TP_DEPENDENCIA": [3, 3, 2],
                         "TP_LOCALIZACAO": [1, 2, 1], "TP_SITUACAO_FUNCIONAMENTO": [1] * 3,
                         "QT_MAT_FUND_AI": [20, 40, 10], "QT_DOC_FUND_AI": [2, 2, 1],
                         "QT_TUR_FUND_AI": [1, 2, 1], **{c: [1, np.nan, 0] for c in INDICADORES}})


def base():
    return pd.DataFrame({"ano": [2024], "id_municipio": ["1100015"], "id_escola": ["mascara"],
                         "id_aluno": ["a"], "serie": ["2"], "rede": ["Municipal"]})


def test_agrega_rede_sem_confundir_faltante_com_zero_ou_docente_unico():
    r = agregar_censo(escolas(), 2023).set_index("rede")
    assert r.loc["Municipal", "matriculas_anos_iniciais_censo"] == 60
    assert r.loc["Municipal", "vinculos_docentes_anos_iniciais_censo"] == 4
    assert r.loc["Municipal", "matriculas_por_vinculo_docente_censo"] == 15
    assert r.loc["Municipal", "pct_escolas_internet_censo"] == 100
    assert r.loc["Municipal", "escolas_resposta_in_internet"] == 1
    assert r.loc["Estadual", "pct_escolas_internet_censo"] == 0


def test_contagem_incompleta_nao_vira_total_parcial():
    d = escolas()
    d.loc[1, "QT_DOC_FUND_AI"] = np.nan
    r = agregar_censo(d, 2023).set_index("rede")
    assert pd.isna(r.loc["Municipal", "vinculos_docentes_anos_iniciais_censo"])
    assert pd.isna(r.loc["Municipal", "matriculas_por_vinculo_docente_censo"])


def test_join_temporal_preserva_aluno_e_rejeita_duplicacao_e_futuro():
    p = pd.DataFrame({"ano": [2022], "id_municipio": ["1100015"], "populacao_municipio_ibge": [100]})
    c = agregar_censo(escolas(), 2023)
    r = juntar_contextos(base(), p, c)
    assert len(r) == 1 and r.matriculas_anos_iniciais_censo.iloc[0] == 60
    with pytest.raises(pd.errors.MergeError):
        juntar_contextos(base(), pd.concat([p, p]), c)
    with pytest.raises(ValueError, match="contemporâneo"):
        juntar_contextos(base(), p, c.assign(ano=2024))


def test_ibge_nao_disponivel_e_zero_sao_diferentes(tmp_path):
    p = tmp_path / "pop.json"
    dados = [{}, {"D1C": "1100015", "D2C": "93", "D3C": "2022", "NC": "6", "V": "..."}]
    p.write_text(json.dumps(dados))
    assert pd.isna(ler_populacao(p, 2022).populacao_municipio_ibge.iloc[0])
    dados[1]["V"] = "0"
    p.write_text(json.dumps(dados))
    with pytest.raises(ValueError, match="População"):
        ler_populacao(p, 2022)


def test_historico_vem_da_edicao_anterior_sem_rotulo_atual():
    cols = ["taxa_alfabetizacao_municipio_anterior", "alunos_avaliados_municipio_anterior",
            "ano_referencia_historico_municipio", "taxa_presenca_municipio_anterior", "tem_historico"]
    nova = base().assign(**{c: np.nan for c in cols}, alfabetizado_binario=1)
    antiga = pd.DataFrame({"ano": [2023] * 3, "id_municipio": ["1100015"] * 3,
                           "elegivel_modelagem": [True, True, False], "alfabetizado_binario": [1, 0, np.nan],
                           "motivo_exclusao_modelagem": ["elegivel", "elegivel", "ausente"]})
    r = aplicar_historico_anterior(nova, antiga)
    assert r.taxa_alfabetizacao_municipio_anterior.iloc[0] == 50
    assert r.taxa_presenca_municipio_anterior.iloc[0] == pytest.approx(200 / 3)
    alterado = aplicar_historico_anterior(nova.assign(alfabetizado_binario=0), antiga)
    pd.testing.assert_frame_equal(r[cols], alterado[cols])


def test_aeeb_preserva_registro_sem_chave_em_quarentena(tmp_path):
    arquivo = tmp_path / "aeeb.zip"
    d = pd.DataFrame({"NU_ANO_AVALIACAO": [2025, 2025], "ID_ALUNO": ["a", "b"], "TP_SERIE": [2, 2],
                      "ID_ESCOLA": ["mascara", None], "TP_DEPENDENCIA": [3, None],
                      "CO_MUNICIPIO": ["1100015", None], "NO_MUNICIPIO": ["Município", None], "SG_UF": ["RO", "RO"],
                      "IN_PRESENCA_LP": [1, 1], "VL_PROFICIENCIA_LP": [750., 740.], "IN_ALFABETIZADO": [1, 0]})
    with zipfile.ZipFile(arquivo, "w") as z:
        z.writestr("DADOS/TS_ALUNO.csv", d.to_csv(index=False, sep=";").encode("latin1"))
    validos, quarentena = ler_alunos_2025(arquivo)
    assert len(validos) == len(quarentena) == 1
    assert validos.id_municipio_nome.iloc[0] == "Município"
    assert validos.regiao_brasil.iloc[0] == "Norte"
    assert quarentena.ID_ALUNO.iloc[0] == "b"
