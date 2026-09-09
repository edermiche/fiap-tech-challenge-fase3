"""Publica Gold enriquecida e a edição AEEB 2025 sem sobrescrever a referência inicial."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.bronze.download_enriquecimento import FONTES, hash_arquivo, salvar_json
from src.common.particionamento import ler_particoes, salvar_particionado_por_ano
from src.gold.base_modelagem import CHAVE, construir_base_modelagem_aluno
from src.silver.enriquecimento_oficial import ler_alunos_2025, ler_censo, ler_populacao


POPULACAO_POR_EDICAO = {2023: 2021, 2024: 2022, 2025: 2024}
NOVAS_FEATURES = [
    "populacao_municipio_ibge", "escolas_anos_iniciais_censo", "matriculas_anos_iniciais_censo",
    "vinculos_docentes_anos_iniciais_censo", "turmas_anos_iniciais_censo",
    "pct_escolas_rurais_censo", "pct_escolas_internet_censo", "pct_escolas_agua_potavel_censo",
    "pct_escolas_biblioteca_censo", "pct_escolas_lab_informatica_censo",
    "pct_escolas_sala_leitura_censo", "pct_escolas_quadra_esportes_censo",
    "pct_escolas_energia_rede_publica_censo", "pct_escolas_computador_censo",
    "pct_escolas_agua_rede_publica_censo", "pct_escolas_agua_poco_artesiano_censo",
    "pct_escolas_agua_cacimba_censo", "pct_escolas_agua_fonte_rio_censo", "pct_escolas_agua_inexistente_censo",
    "pct_escolas_energia_gerador_fossil_censo", "pct_escolas_energia_renovavel_censo", "pct_escolas_energia_inexistente_censo",
    "pct_escolas_esgoto_rede_publica_censo", "pct_escolas_esgoto_fossa_septica_censo",
    "pct_escolas_esgoto_fossa_comum_censo", "pct_escolas_esgoto_fossa_censo", "pct_escolas_esgoto_inexistente_censo",
    "pct_escolas_biblioteca_sala_leitura_censo", "pct_escolas_quadra_esportes_coberta_censo",
    "pct_escolas_quadra_esportes_descoberta_censo", "pct_escolas_acessibilidade_corrimao_censo",
    "pct_escolas_acessibilidade_elevador_censo", "pct_escolas_acessibilidade_pisos_tateis_censo",
    "pct_escolas_acessibilidade_vao_livre_censo", "pct_escolas_acessibilidade_rampas_censo",
    "pct_escolas_acessibilidade_sinal_sonoro_censo", "pct_escolas_acessibilidade_sinal_tatil_censo",
    "pct_escolas_acessibilidade_sinal_visual_censo", "pct_escolas_internet_alunos_censo",
    "pct_escolas_internet_administrativo_censo", "pct_escolas_internet_aprendizagem_censo",
    "pct_escolas_internet_comunidade_censo", "pct_escolas_acesso_internet_computador_censo",
    "pct_escolas_com_professores_censo", "pct_escolas_com_prof_administrativos_censo",
    "pct_escolas_com_prof_alimentacao_censo", "pct_escolas_com_prof_assist_social_censo",
    "pct_escolas_com_prof_bibliotecario_censo", "pct_escolas_com_prof_coordenador_censo",
    "pct_escolas_com_prof_fonoaudiologo_censo", "pct_escolas_com_prof_gestao_censo",
    "pct_escolas_com_prof_monitores_censo", "pct_escolas_com_prof_nutricionista_censo",
    "pct_escolas_com_prof_pedagogia_censo", "pct_escolas_com_prof_psicologo_censo",
    "pct_escolas_com_prof_saude_censo", "pct_escolas_material_ped_multimidia_censo",
    "pct_escolas_material_ped_infantil_censo", "pct_escolas_material_ped_cientifico_censo",
    "pct_escolas_material_ped_jogos_censo",
    "salas_utilizadas_censo", "salas_climatizadas_censo", "salas_acessiveis_censo", "salas_utilizadas_fora_censo",
    "matriculas_por_vinculo_docente_censo", "matriculas_por_turma_censo",
]


def juntar_contextos(base, populacao, censo):
    ano = int(base.ano.iloc[0])
    if base.ano.nunique() != 1 or base[CHAVE].isna().any().any() or base.duplicated(CHAVE).any():
        raise ValueError("Base deve conter uma edição e chave válida")
    if not censo.ano.eq(ano - 1).all() or not populacao.ano.lt(ano).all():
        raise ValueError("Contexto contemporâneo/futuro não pode entrar na Gold")
    p = populacao.rename(columns={"ano": "ano_referencia_ibge"})
    c = censo.rename(columns={"ano": "ano_referencia_censo"})
    resultado = base.merge(p, on="id_municipio", how="left", validate="many_to_one")
    resultado = resultado.merge(c, on=["id_municipio", "rede"], how="left", validate="many_to_one")
    resultado["tem_populacao_ibge"] = resultado.populacao_municipio_ibge.notna()
    resultado["tem_censo_escolar"] = resultado.escolas_anos_iniciais_censo.notna()
    if len(resultado) != len(base):
        raise ValueError("Enriquecimento alterou a quantidade de avaliações")
    return resultado


def aplicar_historico_anterior(base_nova, base_anterior):
    ano = int(base_nova.ano.iloc[0])
    if not base_anterior.ano.eq(ano - 1).all():
        raise ValueError("Histórico deve vir exclusivamente da edição anterior")
    validos = base_anterior.loc[base_anterior.elegivel_modelagem]
    historico = validos.groupby("id_municipio").agg(
        taxa_alfabetizacao_municipio_anterior=("alfabetizado_binario", "mean"),
        alunos_avaliados_municipio_anterior=("alfabetizado_binario", "size"),
    ).reset_index()
    historico["taxa_alfabetizacao_municipio_anterior"] *= 100
    historico["ano_referencia_historico_municipio"] = ano - 1
    presenca = base_anterior.assign(presente=base_anterior.motivo_exclusao_modelagem.ne("ausente")).groupby(
        "id_municipio").presente.mean().mul(100).reset_index(name="taxa_presenca_municipio_anterior")
    cols = [c for c in historico if c != "id_municipio"] + ["taxa_presenca_municipio_anterior", "tem_historico"]
    resultado = base_nova.drop(columns=cols).merge(historico, on="id_municipio", how="left", validate="many_to_one")
    resultado = resultado.merge(presenca, on="id_municipio", how="left", validate="many_to_one")
    resultado["tem_historico"] = resultado.taxa_alfabetizacao_municipio_anterior.notna()
    return resultado


def executar(lake, execucao, origem):
    date.fromisoformat(execucao)
    date.fromisoformat(origem)
    bronze = lake / "bronze/enriquecimento_oficial" / f"execution_date={execucao}"
    destino = lake / "gold/base_modelagem_aluno_enriquecida" / f"execution_date={execucao}"
    fontes = []
    for nome in FONTES:
        manifesto = json.loads((bronze / f"{nome}.manifesto.json").read_text(encoding="utf-8"))
        if hash_arquivo(bronze / manifesto["arquivo"]) != manifesto["sha256"]:
            raise ValueError(f"Hash da Bronze divergente: {nome}")
        fontes.append(manifesto)
    def silver(nome):
        pasta = lake / "silver" / nome / f"execution_date={origem}"
        for p in sorted(pasta.rglob("*.parquet")):
            fontes.append({"arquivo": str(p.relative_to(lake)), "sha256": hash_arquivo(p)})
        return ler_particoes(pasta)
    bolsa = silver("fato_bolsa_familia_municipio")
    metas = {nivel: silver(f"fato_meta_anual_{nivel}") for nivel in ["municipio", "uf", "brasil"]}
    cobertura = {}
    auditoria_2025 = {}
    anterior = None
    for ano, ref_pop in POPULACAO_POR_EDICAO.items():
        print(f"[ENRIQUECIMENTO] Edição {ano}", flush=True)
        if ano < 2025:
            arquivo = lake / "gold/base_modelagem_aluno" / f"execution_date={origem}" / f"ano={ano}/base_modelagem_aluno.parquet"
            base = pq.ParquetFile(arquivo).read().to_pandas()
            base["ano"] = ano
            fontes.append({"arquivo": str(arquivo.relative_to(lake)), "sha256": hash_arquivo(arquivo)})
        else:
            alunos, quarentena = ler_alunos_2025(bronze / "alfabetizacao_2025.zip")
            auditoria_2025 = {"linhas_bronze": len(alunos) + len(quarentena), "quarentena_sem_chave": len(quarentena)}
            pasta_quarentena = lake / "silver/quarentena_alfabetizacao" / f"execution_date={execucao}/ano=2025"
            pasta_quarentena.mkdir(parents=True, exist_ok=True)
            quarentena.to_parquet(pasta_quarentena / "quarentena.parquet", index=False)
            salvar_particionado_por_ano(alunos, lake / "silver/alunos_alfabetizacao_oficial" / f"execution_date={execucao}", "alunos_alfabetizacao_oficial.parquet")
            base = construir_base_modelagem_aluno(alunos, bolsa, metas)
            del alunos
            base = aplicar_historico_anterior(base, anterior)
        # Somente a base não enriquecida do ano anterior alimenta o lag seguinte.
        anterior = base
        pop = ler_populacao(bronze / f"ibge_populacao_{ref_pop}.json", ref_pop)
        censo = ler_censo(bronze / f"censo_escolar_{ano - 1}.zip", ano - 1)
        for nome, df in [("contexto_ibge_municipio", pop), ("contexto_censo_municipio_rede", censo)]:
            salvar_particionado_por_ano(df, lake / "silver" / nome / f"execution_date={execucao}", f"{nome}.parquet")
        gold = juntar_contextos(base, pop, censo)
        gold["data_processamento_gold"] = execucao
        salvar_particionado_por_ano(gold, destino, "base_modelagem_aluno_enriquecida.parquet")
        validos = gold.loc[gold.elegivel_modelagem]
        cobertura[str(ano)] = {
            "linhas_gold": len(gold), "elegiveis": len(validos), "ufs": sorted(gold.sigla_uf.unique().tolist()),
            "exclusoes": gold.motivo_exclusao_modelagem.value_counts().to_dict(),
            "cobertura_populacao_pct": float(validos.tem_populacao_ibge.mean() * 100),
            "cobertura_censo_pct": float(validos.tem_censo_escolar.mean() * 100),
            "cobertura_historico_pct": float(validos.tem_historico.mean() * 100),
            "cobertura_bolsa_pct": float(validos.tem_bolsa_familia_anterior.mean() * 100),
            "ausencias_features_pct": validos[NOVAS_FEATURES].isna().mean().mul(100).to_dict(),
            "ano_ibge": ref_pop, "ano_censo": ano - 1,
        }
        print(f"[GOLD] {ano}: {len(gold):,} linhas; IBGE {cobertura[str(ano)]['cobertura_populacao_pct']:.2f}%; Censo {cobertura[str(ano)]['cobertura_censo_pct']:.2f}%", flush=True)
        del gold, validos
    relatorio = {"execution_date": execucao, "origem_execution_date": origem,
                 "tabela": "base_modelagem_aluno_enriquecida", "novas_features": NOVAS_FEATURES,
                 "fontes": fontes, "cobertura": cobertura, "auditoria_ingestao_2025": auditoria_2025,
                 "vintage_historico_comprovado": False,
                 "limites": ["Referência anterior não prova a disponibilidade histórica da versão baixada.",
                             "Estimativa IBGE e Censo Demográfico têm métodos distintos; não medir crescimento diretamente.",
                             "Docentes somados são vínculos por escola, não pessoas únicas.",
                             "Percentuais de infraestrutura usam escolas com resposta válida, sem imputar ausência como não."]}
    relatorio["arquivos_gold"] = [{"arquivo": str(p.relative_to(lake)), "sha256": hash_arquivo(p)}
                                   for p in sorted(destino.rglob("*.parquet"))]
    salvar_json(destino / "manifesto_enriquecimento.json", relatorio)
    return relatorio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake", type=Path, default=Path("data"))
    parser.add_argument("--execution-date", default=date.today().isoformat())
    parser.add_argument("--origem-execution-date", default="2026-09-07")
    args = parser.parse_args()
    executar(args.lake, args.execution_date, args.origem_execution_date)


if __name__ == "__main__":
    main()
