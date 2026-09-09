"""Downloads oficiais IBGE/Inep, com cache verificável e manifesto de origem.

Uso: python -m src.bronze.download_enriquecimento --execution-date 2026-09-08
Não altera a extração BigQuery existente. Fontes complementares são públicas.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


FONTES = {
    "ibge_populacao_2021": {
        "url": "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2021",
        "extensao": "json", "ano_referencia": 2021,
        "tipo": "estimativa_populacional", "divulgacao_edicao": "2021-08-27",
        "pagina": "https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html?edicao=31451&t=custom-data-edicao",
    },
    "ibge_populacao_2022": {
        "url": "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022",
        "extensao": "json", "ano_referencia": 2022,
        "tipo": "censo_demografico", "divulgacao_edicao": "2023-12-22",
        "pagina": "https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html?t=resultados",
    },
    "ibge_populacao_2024": {
        "url": "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2024",
        "extensao": "json", "ano_referencia": 2024,
        "tipo": "estimativa_populacional", "divulgacao_edicao": "2024-08-29",
        "pagina": "https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html",
    },
    "alfabetizacao_2025": {
        "url": "http://download.inep.gov.br/dados_abertos/microdados_AEEB_2025.zip",
        "extensao": "zip", "ano_referencia": 2025, "tipo": "avaliacao_alfabetizacao",
        "divulgacao_edicao": None,
        "pagina": "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/avaliacao-da-alfabetizacao/resultados/2025",
    },
    "idhm_municipios_2010": {
        "url": "https://raw.githubusercontent.com/mauriciocramos/IDHM/main/municipal.csv",
        "extensao": "csv", "ano_referencia": 2010, "tipo": "idhm_municipal",
        "divulgacao_edicao": None,
        "pagina": "https://www.undp.org/pt/brazil/idhm-municipios-2010",
    },
    **{f"censo_escolar_{ano}": {
        # O endpoint público do Inep responde em HTTP; HTTPS encerra TLS
        # neste servidor. Não desabilitamos verificação de certificados.
        "url": f"http://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{ano}.zip",
        "extensao": "zip", "ano_referencia": ano, "tipo": "censo_escolar",
        # Data exata da versão atualmente servida não é inferida do ano.
        "divulgacao_edicao": None,
        "pagina": "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar",
    } for ano in [2022, 2023, 2024]},
}


def hash_arquivo(caminho):
    with Path(caminho).open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def salvar_json(caminho, valor):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(valor, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(caminho)


def baixar(nome, pasta):
    fonte = FONTES[nome]
    arquivo = pasta / f"{nome}.{fonte['extensao']}"
    manifesto = pasta / f"{nome}.manifesto.json"
    if arquivo.exists() and manifesto.exists():
        meta = json.loads(manifesto.read_text(encoding="utf-8"))
        if meta["sha256"] != hash_arquivo(arquivo) or meta["url"] != fonte["url"]:
            raise ValueError(f"Cache divergente: {arquivo}; escolha outra execution-date")
        print(f"[CACHE] {nome}: hash conferido", flush=True)
        return meta
    pasta.mkdir(parents=True, exist_ok=True)
    tmp = arquivo.with_suffix(arquivo.suffix + ".part")
    print(f"[DOWNLOAD] {nome}", flush=True)
    sessao = requests.Session()
    adaptador = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]))
    sessao.mount("http://", adaptador)
    sessao.mount("https://", adaptador)
    with sessao, sessao.get(fonte["url"], timeout=(30, 90), stream=True) as resposta, tmp.open("wb") as destino:
        resposta.raise_for_status()
        headers = {h: resposta.headers.get(h) for h in ["ETag", "Last-Modified", "Content-Length"]}
        for bloco in resposta.iter_content(1024 * 1024):
            destino.write(bloco)
    if fonte["extensao"] == "zip":
        with zipfile.ZipFile(tmp) as pacote:
            if pacote.testzip() is not None:
                raise ValueError(f"ZIP inválido: {nome}")
    elif fonte["extensao"] == "csv":
        cabecalho = tmp.read_text(encoding="utf-8-sig", errors="strict").splitlines()[0]
        if "IDHM" not in cabecalho or "Codmun7" not in cabecalho:
            raise ValueError(f"CSV de IDHM sem colunas esperadas: {nome}")
    else:
        payload = json.loads(tmp.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError(f"Resposta SIDRA sem dados: {nome}")
    tmp.replace(arquivo)
    meta = {**fonte, "arquivo": arquivo.name, "sha256": hash_arquivo(arquivo),
            "bytes": arquivo.stat().st_size, "headers": headers,
            "obtido_em_utc": datetime.now(timezone.utc).isoformat(),
            "vintage_historico_comprovado": False,
            "limite": "Data de edição não comprova versão histórica dos bytes baixados; avaliação retrospectiva."}
    salvar_json(manifesto, meta)
    print(f"[OK] {nome}: {meta['bytes'] / 1024**2:.1f} MB", flush=True)
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake", type=Path, default=Path("data"))
    parser.add_argument("--execution-date", default=date.today().isoformat())
    parser.add_argument("--fontes", nargs="+", choices=FONTES, default=list(FONTES))
    args = parser.parse_args()
    date.fromisoformat(args.execution_date)
    pasta = args.lake / "bronze/enriquecimento_oficial" / f"execution_date={args.execution_date}"
    for nome in args.fontes:
        baixar(nome, pasta)


if __name__ == "__main__":
    main()
