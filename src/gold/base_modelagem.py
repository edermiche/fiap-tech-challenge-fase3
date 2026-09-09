"""Contrato de consumo da Fase 3: uma observação de aluno por avaliação.

Preserva ausentes para auditoria, com alvo nulo. As medidas educacionais e
sociais usadas como atributos vêm exclusivamente do ano anterior. Metas
ficam disponíveis como contexto, fora da lista padrão de features até que
sua data de publicação seja comprovada (ano-base não é data de publicação).
"""
from __future__ import annotations

import pandas as pd


CHAVE = ["ano", "id_municipio", "id_escola", "id_aluno", "serie", "rede"]
FEATURES_CATEGORICAS = ["rede", "sigla_uf", "regiao_brasil"]
FEATURES_NUMERICAS = [
    "taxa_alfabetizacao_municipio_anterior",
    "taxa_presenca_municipio_anterior",
    "alunos_avaliados_municipio_anterior",
    "total_pagamentos_bolsa_familia_anterior",
    "valor_total_bolsa_familia_anterior",
    "valor_medio_pagamento_bolsa_familia_anterior",
]
FEATURES = FEATURES_CATEGORICAS + FEATURES_NUMERICAS


def preparar_metas(meta: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Seleciona a versão de ano-base mais recente anterior ao ano-alvo.

    Rede Municipal/Pública descreve a abrangência da meta, não a rede do
    aluno. É mantida explicitamente para evitar confundir as duas coisas.
    """
    territorio = {"municipio": ["id_municipio"], "uf": ["sigla_uf"], "brasil": []}[nivel]
    df = meta.loc[meta.ano.lt(meta.ano_meta)].copy()
    chave = ["ano_meta", *territorio]
    df = df.sort_values("ano").drop_duplicates([*chave, "rede"], keep="last")
    if df.duplicated(chave).any():
        raise ValueError(f"Metas {nivel} com múltiplas redes: definir abrangência antes da junção")
    colunas = ["ano", "ano_meta", *territorio, "rede", "meta_alfabetizacao"]
    return df[colunas].rename(columns={
        "ano": f"ano_base_meta_{nivel}", "ano_meta": "ano",
        "rede": f"rede_meta_{nivel}", "meta_alfabetizacao": f"meta_alfabetizacao_{nivel}",
    })


def construir_base_modelagem_aluno(
    alunos: pd.DataFrame,
    bolsa: pd.DataFrame,
    metas: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if alunos.empty or alunos[CHAVE].isna().any().any() or alunos.duplicated(CHAVE).any():
        raise ValueError("Base de alunos vazia ou chave de avaliação inválida/duplicada")
    base = alunos[[*CHAVE, "id_municipio_nome", "sigla_uf", "regiao_brasil"]].copy()
    presente = alunos.presenca.eq("Presente")
    medido = alunos.proficiencia.notna() & alunos.proficiencia.ge(0)
    rotulo_valido = alunos.alfabetizado.isin(["Sim", "Não"])
    consistente = alunos.alfabetizado.eq("Sim").eq(alunos.proficiencia.ge(743))
    elegivel = presente & medido & rotulo_valido & consistente
    base["elegivel_modelagem"] = elegivel
    base["motivo_exclusao_modelagem"] = "elegivel"
    base.loc[~presente, "motivo_exclusao_modelagem"] = "ausente"
    base.loc[presente & ~medido, "motivo_exclusao_modelagem"] = "sem_proficiencia_valida"
    base.loc[presente & medido & (~rotulo_valido | ~consistente), "motivo_exclusao_modelagem"] = "rotulo_invalido_ou_inconsistente"
    base["alfabetizado_binario"] = alunos.alfabetizado.eq("Sim").astype("Int8").where(elegivel)

    historico = base.loc[elegivel]
    # IDs escolares não têm correspondência longitudinal comprovada.
    # Nem mesmo a coincidência de ID+município garante a mesma escola.
    for nivel, grupos in [("municipio", ["id_municipio"])]:
        agregado = historico.groupby(["ano", *grupos], observed=True).agg(**{
            f"taxa_alfabetizacao_{nivel}_anterior": ("alfabetizado_binario", "mean"),
            f"alunos_avaliados_{nivel}_anterior": ("alfabetizado_binario", "size"),
        }).reset_index()
        agregado[f"taxa_alfabetizacao_{nivel}_anterior"] *= 100
        agregado[f"ano_referencia_historico_{nivel}"] = agregado.ano
        agregado["ano"] += 1
        base = base.merge(agregado, on=["ano", *grupos], how="left", validate="many_to_one")

    presencas = alunos.assign(presente=presente).groupby(["ano", "id_municipio"]).presente.mean().mul(100).reset_index(name="taxa_presenca_municipio_anterior")
    presencas["ano"] += 1
    base = base.merge(presencas, on=["ano", "id_municipio"], how="left", validate="many_to_one")

    contexto = bolsa[["ano_competencia", "id_municipio", "total_beneficiarios", "valor_total_pago"]].rename(columns={
        "ano_competencia": "ano_referencia_bolsa_familia",
        # O SQL de origem faz COUNT(1) de pagamentos, não COUNT DISTINCT de pessoas.
        "total_beneficiarios": "total_pagamentos_bolsa_familia_anterior",
        "valor_total_pago": "valor_total_bolsa_familia_anterior",
    }).copy()
    contexto["ano"] = contexto.ano_referencia_bolsa_familia + 1
    denominador = contexto.total_pagamentos_bolsa_familia_anterior.where(contexto.total_pagamentos_bolsa_familia_anterior.gt(0))
    contexto["valor_medio_pagamento_bolsa_familia_anterior"] = contexto.valor_total_bolsa_familia_anterior / denominador
    base = base.merge(contexto, on=["ano", "id_municipio"], how="left", validate="many_to_one")

    for nivel, meta in metas.items():
        territorio = {"municipio": ["id_municipio"], "uf": ["sigla_uf"], "brasil": []}[nivel]
        base = base.merge(preparar_metas(meta, nivel), on=["ano", *territorio], how="left", validate="many_to_one")
    base["tem_historico"] = base.taxa_alfabetizacao_municipio_anterior.notna()
    base["tem_bolsa_familia_anterior"] = base.total_pagamentos_bolsa_familia_anterior.notna()
    if len(base) != len(alunos):
        raise ValueError("Junções alteraram a quantidade de observações de aluno")
    return base
