"""Normaliza fontes oficiais; Censo agregado por município/rede, nunca por máscara escolar."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from src.silver.config import MAPA_REGIAO_UF


REDES = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
INDICADORES = {
    "IN_INTERNET": "pct_escolas_internet_censo",
    "IN_AGUA_POTAVEL": "pct_escolas_agua_potavel_censo",
    "IN_BIBLIOTECA": "pct_escolas_biblioteca_censo",
    "IN_LABORATORIO_INFORMATICA": "pct_escolas_lab_informatica_censo",
    "IN_SALA_LEITURA": "pct_escolas_sala_leitura_censo",
    "IN_QUADRA_ESPORTES": "pct_escolas_quadra_esportes_censo",
    "IN_ENERGIA_REDE_PUBLICA": "pct_escolas_energia_rede_publica_censo",
    "IN_COMPUTADOR": "pct_escolas_computador_censo",
    # Indicadores complementares selecionados do catálogo do Censo Escolar.
    "IN_AGUA_REDE_PUBLICA": "pct_escolas_agua_rede_publica_censo",
    "IN_AGUA_POCO_ARTESIANO": "pct_escolas_agua_poco_artesiano_censo",
    "IN_AGUA_CACIMBA": "pct_escolas_agua_cacimba_censo",
    "IN_AGUA_FONTE_RIO": "pct_escolas_agua_fonte_rio_censo",
    "IN_AGUA_INEXISTENTE": "pct_escolas_agua_inexistente_censo",
    "IN_ENERGIA_GERADOR_FOSSIL": "pct_escolas_energia_gerador_fossil_censo",
    "IN_ENERGIA_RENOVAVEL": "pct_escolas_energia_renovavel_censo",
    "IN_ENERGIA_INEXISTENTE": "pct_escolas_energia_inexistente_censo",
    "IN_ESGOTO_REDE_PUBLICA": "pct_escolas_esgoto_rede_publica_censo",
    "IN_ESGOTO_FOSSA_SEPTICA": "pct_escolas_esgoto_fossa_septica_censo",
    "IN_ESGOTO_FOSSA_COMUM": "pct_escolas_esgoto_fossa_comum_censo",
    "IN_ESGOTO_FOSSA": "pct_escolas_esgoto_fossa_censo",
    "IN_ESGOTO_INEXISTENTE": "pct_escolas_esgoto_inexistente_censo",
    "IN_BIBLIOTECA_SALA_LEITURA": "pct_escolas_biblioteca_sala_leitura_censo",
    "IN_QUADRA_ESPORTES_COBERTA": "pct_escolas_quadra_esportes_coberta_censo",
    "IN_QUADRA_ESPORTES_DESCOBERTA": "pct_escolas_quadra_esportes_descoberta_censo",
    "IN_ACESSIBILIDADE_CORRIMAO": "pct_escolas_acessibilidade_corrimao_censo",
    "IN_ACESSIBILIDADE_ELEVADOR": "pct_escolas_acessibilidade_elevador_censo",
    "IN_ACESSIBILIDADE_PISOS_TATEIS": "pct_escolas_acessibilidade_pisos_tateis_censo",
    "IN_ACESSIBILIDADE_VAO_LIVRE": "pct_escolas_acessibilidade_vao_livre_censo",
    "IN_ACESSIBILIDADE_RAMPAS": "pct_escolas_acessibilidade_rampas_censo",
    "IN_ACESSIBILIDADE_SINAL_SONORO": "pct_escolas_acessibilidade_sinal_sonoro_censo",
    "IN_ACESSIBILIDADE_SINAL_TATIL": "pct_escolas_acessibilidade_sinal_tatil_censo",
    "IN_ACESSIBILIDADE_SINAL_VISUAL": "pct_escolas_acessibilidade_sinal_visual_censo",
    "IN_INTERNET_ALUNOS": "pct_escolas_internet_alunos_censo",
    "IN_INTERNET_ADMINISTRATIVO": "pct_escolas_internet_administrativo_censo",
    "IN_INTERNET_APRENDIZAGEM": "pct_escolas_internet_aprendizagem_censo",
    "IN_INTERNET_COMUNIDADE": "pct_escolas_internet_comunidade_censo",
    "IN_ACESSO_INTERNET_COMPUTADOR": "pct_escolas_acesso_internet_computador_censo",
    "IN_PROF": "pct_escolas_com_professores_censo",
    "IN_PROF_ADMINISTRATIVOS": "pct_escolas_com_prof_administrativos_censo",
    "IN_PROF_ALIMENTACAO": "pct_escolas_com_prof_alimentacao_censo",
    "IN_PROF_ASSIST_SOCIAL": "pct_escolas_com_prof_assist_social_censo",
    "IN_PROF_BIBLIOTECARIO": "pct_escolas_com_prof_bibliotecario_censo",
    "IN_PROF_COORDENADOR": "pct_escolas_com_prof_coordenador_censo",
    "IN_PROF_FONAUDIOLOGO": "pct_escolas_com_prof_fonoaudiologo_censo",
    "IN_PROF_GESTAO": "pct_escolas_com_prof_gestao_censo",
    "IN_PROF_MONITORES": "pct_escolas_com_prof_monitores_censo",
    "IN_PROF_NUTRICIONISTA": "pct_escolas_com_prof_nutricionista_censo",
    "IN_PROF_PEDAGOGIA": "pct_escolas_com_prof_pedagogia_censo",
    "IN_PROF_PSICOLOGO": "pct_escolas_com_prof_psicologo_censo",
    "IN_PROF_SAUDE": "pct_escolas_com_prof_saude_censo",
    "IN_MATERIAL_PED_MULTIMIDIA": "pct_escolas_material_ped_multimidia_censo",
    "IN_MATERIAL_PED_INFANTIL": "pct_escolas_material_ped_infantil_censo",
    "IN_MATERIAL_PED_CIENTIFICO": "pct_escolas_material_ped_cientifico_censo",
    "IN_MATERIAL_PED_JOGOS": "pct_escolas_material_ped_jogos_censo",
}
INDICADORES_COM_CONTAGEM_RESPOSTA = {
    "IN_INTERNET", "IN_AGUA_POTAVEL", "IN_BIBLIOTECA", "IN_LABORATORIO_INFORMATICA",
    "IN_SALA_LEITURA", "IN_QUADRA_ESPORTES", "IN_ENERGIA_REDE_PUBLICA", "IN_COMPUTADOR",
}
CONTAGENS = {"QT_MAT_FUND_AI": "matriculas_anos_iniciais_censo",
             "QT_DOC_FUND_AI": "vinculos_docentes_anos_iniciais_censo",
             "QT_TUR_FUND_AI": "turmas_anos_iniciais_censo",
             "QT_SALAS_UTILIZADAS": "salas_utilizadas_censo",
             "QT_SALAS_UTILIZA_CLIMATIZADAS": "salas_climatizadas_censo",
             "QT_SALAS_UTILIZADAS_ACESSIVEIS": "salas_acessiveis_censo",
             "QT_SALAS_UTILIZADAS_FORA": "salas_utilizadas_fora_censo"}
COLUNAS_CENSO = ["NU_ANO_CENSO", "CO_MUNICIPIO", "CO_ENTIDADE", "TP_DEPENDENCIA",
                "TP_LOCALIZACAO", "TP_SITUACAO_FUNCIONAMENTO", *INDICADORES, *CONTAGENS]


def ler_populacao(arquivo: Path, ano: int):
    bruto = json.loads(arquivo.read_text(encoding="utf-8-sig"))
    df = pd.DataFrame(bruto[1:])
    if not df.D3C.eq(str(ano)).all() or not df.NC.eq("6").all():
        raise ValueError("SIDRA: ano ou nível territorial inesperado")
    # Identidade da variável faz parte do contrato, não apenas seu valor.
    esperado = "93" if ano == 2022 else "9324"
    if not df.D2C.eq(esperado).all():
        raise ValueError("SIDRA: variável diferente de população")
    # SIDRA usa ... para não disponível e .. para não aplicável.
    # Ex.: município criado depois da referência. Não vira população zero.
    valores = df.V.mask(df.V.isin(["...", "..", "X"]))
    saida = pd.DataFrame({"id_municipio": df.D1C,
                          "populacao_municipio_ibge": pd.to_numeric(valores, errors="raise")})
    if (saida.id_municipio.duplicated().any() or not saida.id_municipio.str.fullmatch(r"\d{7}").all()
            or not saida.populacao_municipio_ibge.dropna().gt(0).all()
            or np.isinf(saida.populacao_municipio_ibge).any()):
        raise ValueError("População municipal ou chave inválida")
    saida["ano"] = ano
    saida["tipo_populacao_ibge"] = "censo_demografico" if ano == 2022 else "estimativa"
    return saida


def agregar_censo(df: pd.DataFrame, ano: int):
    df = df.copy()
    # O microdado usa 9 como "ignorado" neste campo; não é uma resposta positiva.
    if "IN_ACESSO_INTERNET_COMPUTADOR" in df:
        df["IN_ACESSO_INTERNET_COMPUTADOR"] = df["IN_ACESSO_INTERNET_COMPUTADOR"].replace(9, np.nan)
    if not df.NU_ANO_CENSO.eq(ano).all() or df.CO_ENTIDADE.isna().any() or df.CO_ENTIDADE.duplicated().any():
        raise ValueError("Censo: ano divergente ou escola duplicada/nula")
    if not df.TP_DEPENDENCIA.isin(REDES).all():
        raise ValueError("Censo: rede desconhecida")
    df = df.loc[df.TP_SITUACAO_FUNCIONAMENTO.eq(1) & df.QT_MAT_FUND_AI.gt(0)].copy()
    if df.empty or not df.CO_MUNICIPIO.astype(str).str.fullmatch(r"\d{7}").all():
        raise ValueError("Censo: nenhuma escola ativa com anos iniciais ou município inválido")
    for c in INDICADORES:
        if not df[c].dropna().isin([0, 1]).all():
            raise ValueError(f"Censo: indicador inválido {c}")
    contagens_presentes = {c: v for c, v in CONTAGENS.items() if c in df.columns}
    for c in contagens_presentes:
        if not np.isfinite(df[c].dropna()).all() or not df[c].dropna().ge(0).all():
            raise ValueError(f"Censo: contagem negativa/infinita {c}")
    if not df.TP_LOCALIZACAO.isin([1, 2]).all():
        raise ValueError("Censo: localização inválida")
    df["id_municipio"] = df.CO_MUNICIPIO.astype(str)
    df["rede"] = df.TP_DEPENDENCIA.map(REDES)
    df["rural"] = df.TP_LOCALIZACAO.eq(2).astype(float)
    agregacoes = {"escolas_anos_iniciais_censo": ("CO_ENTIDADE", "size"),
                  "pct_escolas_rurais_censo": ("rural", "mean")}
    # Não apresentar soma parcial como total quando alguma escola não informa.
    agregacoes.update({v: (c, lambda s: s.sum(min_count=len(s))) for c, v in contagens_presentes.items()})
    for c, v in INDICADORES.items():
        agregacoes[v] = (c, "mean")
        if c in INDICADORES_COM_CONTAGEM_RESPOSTA:
            agregacoes[f"escolas_resposta_{c.lower()}"] = (c, "count")
    saida = df.groupby(["id_municipio", "rede"]).agg(**agregacoes).reset_index()
    for c in [*INDICADORES.values(), "pct_escolas_rurais_censo"]:
        saida[c] *= 100
    for denom, nome in [("vinculos_docentes_anos_iniciais_censo", "matriculas_por_vinculo_docente_censo"),
                        ("turmas_anos_iniciais_censo", "matriculas_por_turma_censo")]:
        if denom in saida and "matriculas_anos_iniciais_censo" in saida:
            saida[nome] = saida.matriculas_anos_iniciais_censo / saida[denom].where(saida[denom].gt(0))
    saida["ano"] = ano
    return saida


def ler_censo(arquivo: Path, ano: int):
    with zipfile.ZipFile(arquivo) as pacote:
        nomes = [n for n in pacote.namelist() if n.endswith(f"microdados_ed_basica_{ano}.csv")]
        if len(nomes) != 1:
            raise ValueError("Arquivo de escolas não identificado univocamente no ZIP")
        with pacote.open(nomes[0]) as csv:
            df = pd.read_csv(csv, sep=";", encoding="latin1", usecols=COLUNAS_CENSO,
                             dtype={"CO_MUNICIPIO": "string", "CO_ENTIDADE": "string"})
    return agregar_censo(df, ano)


def ler_alunos_2025(arquivo: Path):
    colunas = ["NU_ANO_AVALIACAO", "ID_ALUNO", "TP_SERIE", "ID_ESCOLA", "TP_DEPENDENCIA",
               "CO_MUNICIPIO", "NO_MUNICIPIO", "SG_UF", "IN_PRESENCA_LP", "VL_PROFICIENCIA_LP", "IN_ALFABETIZADO"]
    with zipfile.ZipFile(arquivo) as pacote, pacote.open("DADOS/TS_ALUNO.csv") as csv:
        df = pd.read_csv(csv, sep=";", encoding="latin1", usecols=colunas,
                         dtype={c: "string" for c in ["ID_ALUNO", "ID_ESCOLA", "CO_MUNICIPIO"]})
    if not df.NU_ANO_AVALIACAO.eq(2025).all() or not df.TP_SERIE.eq(2).all():
        raise ValueError("AEEB 2025: ano/série inesperado")
    if not df.TP_DEPENDENCIA.dropna().isin(REDES).all() or not df.IN_PRESENCA_LP.isin([0, 1]).all():
        raise ValueError("AEEB 2025: rede/presença inválida")
    if not df.IN_ALFABETIZADO.dropna().isin([0, 1]).all():
        raise ValueError("AEEB 2025: rótulo desconhecido")
    sem_chave = df[["ID_ALUNO", "ID_ESCOLA", "CO_MUNICIPIO", "TP_DEPENDENCIA"]].isna().any(axis=1)
    quarentena = df.loc[sem_chave].copy()
    quarentena["motivo_quarentena"] = "chave_territorial_escolar_ou_rede_ausente_na_fonte"
    df = df.loc[~sem_chave].copy()
    df = df.rename(columns={"NU_ANO_AVALIACAO": "ano", "ID_ALUNO": "id_aluno", "ID_ESCOLA": "id_escola",
                            "CO_MUNICIPIO": "id_municipio", "NO_MUNICIPIO": "id_municipio_nome",
                            "SG_UF": "sigla_uf", "VL_PROFICIENCIA_LP": "proficiencia"})
    df["serie"] = "2° ano do Ensino Fundamental"
    df["rede"] = df.TP_DEPENDENCIA.map(REDES)
    df["presenca"] = df.IN_PRESENCA_LP.map({0: "Ausente", 1: "Presente"})
    df["alfabetizado"] = df.IN_ALFABETIZADO.map({0: "Não", 1: "Sim"})
    df["regiao_brasil"] = df.sigla_uf.map(MAPA_REGIAO_UF)
    if df.regiao_brasil.isna().any() or not df.id_municipio.str.fullmatch(r"\d{7}").all():
        raise ValueError("AEEB 2025: geografia inválida")
    return df[["ano", "id_municipio", "id_escola", "id_aluno", "serie", "rede", "id_municipio_nome",
               "sigla_uf", "regiao_brasil", "presenca", "proficiencia", "alfabetizado"]], quarentena
