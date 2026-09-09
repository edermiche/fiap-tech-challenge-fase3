from datetime import date
from pathlib import Path

from src.bronze.download_enriquecimento import FONTES, baixar
from src.bronze.processar_bronze import processar_camada_bronze
from src.silver.processar_silver import processar_camada_silver
from src.gold.processar_gold import processar_camada_gold
from src.gold.enriquecer_modelagem import executar as executar_gold_enriquecida


def main() -> None:
    """Executa o fluxo completo: Bronze -> Silver -> Gold."""
    # A data é resolvida uma vez e repassada às camadas: Silver e Gold
    # precisam gravar na mesma partição execution_date.
    data_processamento = date.today()
    execucao = data_processamento.isoformat()
    lake = Path("data")

    processar_camada_bronze()
    processar_camada_silver(data_processamento)
    processar_camada_gold(data_processamento)

    # Complementos e Gold enriquecida usam a mesma partição da execução.
    # Assim, uma chamada ao main reproduz também a base consumida pela Fase 3.
    pasta_complementos = lake / "bronze/enriquecimento_oficial" / f"execution_date={execucao}"
    for nome in FONTES:
        baixar(nome, pasta_complementos)
    executar_gold_enriquecida(lake, execucao, execucao)


if __name__ == "__main__":
    main()
