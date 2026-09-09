"""Auditoria local reproduzível, sem exibir microdados individuais.

Uso: python -m src.qualidade.auditar_lake --saida docs/auditoria_lake.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.common.particionamento import ler_tabela_mais_recente
from src.gold.base_modelagem import CHAVE, FEATURES


def auditar(lake: Path) -> dict:
    resultado = {"executado_em": datetime.now().isoformat(), "tabelas": [], "alunos": {}, "modelagem": {}}
    for camada in ["bronze", "silver", "gold"]:
        for tabela in sorted((lake / camada).iterdir()):
            if not tabela.is_dir():
                continue
            execucoes = sorted(tabela.glob("execution_date=*"))
            if not execucoes:
                continue
            arquivos = sorted(execucoes[-1].rglob("*.parquet"))
            resultado["tabelas"].append({"camada": camada, "tabela": tabela.name,
                "execucao": execucoes[-1].name.split("=", 1)[1],
                "linhas": sum(pq.ParquetFile(p).metadata.num_rows for p in arquivos),
                "arquivos": len(arquivos), "bytes": sum(p.stat().st_size for p in arquivos)})
    alunos = ler_tabela_mais_recente(lake / "silver/fato_aluno_alfabetizacao")
    for ano, grupo in alunos.groupby("ano"):
        resultado["alunos"][str(ano)] = {
            "linhas": len(grupo), "municipios": grupo.id_municipio.nunique(),
            "escolas": grupo.id_escola.nunique(), "prefixos_uf": sorted(grupo.id_municipio.str[:2].unique().tolist()),
            "ausentes": int(grupo.presenca.eq("Ausente").sum()),
            "presentes_sem_proficiencia": int((grupo.presenca.eq("Presente") & grupo.proficiencia.isna()).sum()),
            "duplicatas_chave": int(grupo.duplicated(CHAVE).sum()),
            "nulos": grupo.isna().sum().to_dict(),
        }
    escolas = alunos[["ano", "id_escola", "id_municipio"]].drop_duplicates()
    anos = sorted(escolas.ano.unique())
    resultado["estabilidade_codigo_escolar"] = {}
    for anterior, atual in zip(anos, anos[1:]):
        pares = escolas.loc[escolas.ano.eq(anterior)].merge(
            escolas.loc[escolas.ano.eq(atual)], on="id_escola", suffixes=("_anterior", "_atual"))
        resultado["estabilidade_codigo_escolar"][f"{anterior}-{atual}"] = {
            "codigos_em_ambos": len(pares),
            "mesmo_municipio": int(pares.id_municipio_anterior.eq(pares.id_municipio_atual).sum()),
            "municipio_diferente": int(pares.id_municipio_anterior.ne(pares.id_municipio_atual).sum()),
        }
    del alunos
    caminho = lake / "gold/base_modelagem_aluno"
    if caminho.exists():
        base = ler_tabela_mais_recente(caminho)
        for ano, grupo in base.groupby("ano"):
            elegiveis = grupo.loc[grupo.elegivel_modelagem]
            resultado["modelagem"][str(ano)] = {
                "linhas": len(grupo), "elegiveis": len(elegiveis),
                "alfabetizados": int(elegiveis.alfabetizado_binario.eq(1).sum()),
                "nao_alfabetizados": int(elegiveis.alfabetizado_binario.eq(0).sum()),
                "com_historico": int(elegiveis.tem_historico.sum()),
                "com_bolsa_anterior": int(elegiveis.tem_bolsa_familia_anterior.sum()),
                "duplicatas_chave": int(grupo.duplicated(CHAVE).sum()),
                "cobertura_features_pct": elegiveis[FEATURES].notna().mean().mul(100).round(3).to_dict(),
                "cobertura_metas_pct": elegiveis.filter(regex="^meta_alfabetizacao_").notna().mean().mul(100).round(3).to_dict(),
                "referencias_futuras": int(sum((grupo[c].notna() & grupo[c].ge(grupo.ano)).sum()
                    for c in grupo.columns if c.startswith(("ano_referencia_", "ano_base_meta_")))),
            }
    for tabela in ["indicador_meta_uf", "indicador_meta_municipio"]:
        df = ler_tabela_mais_recente(lake / "gold" / tabela)
        resultado[tabela] = {str(ano): {"linhas": len(g), "sem_meta": int(g.meta_alfabetizacao.isna().sum()),
            "sem_resultado": int(g.taxa_alfabetizacao.isna().sum())} for ano, g in df.groupby("ano")}
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake", type=Path, default=Path("data"))
    parser.add_argument("--saida", type=Path, default=Path("docs/auditoria_lake.json"))
    args = parser.parse_args()
    resultado = auditar(args.lake)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=int), encoding="utf-8")
    print(json.dumps({k: v for k, v in resultado.items() if k != "tabelas"}, ensure_ascii=False, indent=2, default=int))
    print(f"Auditoria salva em {args.saida}")


if __name__ == "__main__":
    main()
