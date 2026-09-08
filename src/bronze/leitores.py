from pathlib import Path

import pandas as pd


EXTENSOES_SUPORTADAS = [".parquet", ".csv", ".xlsx"]


def listar_arquivos_entidade(caminho_entidade: Path) -> list[Path]:
    """
    Lista os arquivos existentes dentro da pasta da entidade e subpastas,
    ignorando arquivos já processados.
    """
    if not caminho_entidade.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {caminho_entidade}")

    # Cada extração batch é um snapshot completo. Somar execution_dates
    # mistura versões corrigidas da mesma observação e duplica o histórico.
    execucoes = sorted(caminho_entidade.glob("execution_date=*"))
    origem = execucoes[-1] if execucoes else caminho_entidade
    arquivos = [
        arquivo
        for arquivo in origem.rglob("*")
        if arquivo.is_file()
        and arquivo.suffix.lower() in EXTENSOES_SUPORTADAS
        and "processado" not in arquivo.relative_to(origem).parts
        and not arquivo.name.endswith("_processado.parquet")
    ]

    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em: {caminho_entidade}")

    return sorted(arquivos)


def ler_arquivo(caminho_arquivo: Path) -> pd.DataFrame:
    """
    Lê um arquivo conforme sua extensão.
    """
    extensao = caminho_arquivo.suffix.lower()

    if extensao == ".parquet":
        return pd.read_parquet(caminho_arquivo)

    if extensao == ".csv":
        return pd.read_csv(
            caminho_arquivo,
            sep=None,
            engine="python",
            encoding="utf-8"
        )

    if extensao == ".xlsx":
        return pd.read_excel(caminho_arquivo)

    raise ValueError(f"Extensão não suportada: {extensao}")


def ler_entidade_bronze(caminho_entidade: Path) -> pd.DataFrame:
    """
    Lê todos os arquivos encontrados na pasta da entidade e subpastas
    e consolida em um único DataFrame.
    """
    arquivos = listar_arquivos_entidade(caminho_entidade)

    dataframes = []

    for arquivo in arquivos:
        print(f"Lendo arquivo: {arquivo}")

        df = ler_arquivo(arquivo)
        dataframes.append(df)

    return pd.concat(dataframes, ignore_index=True)
