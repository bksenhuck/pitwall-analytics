"""
Carrega TODOS os dados disponíveis do FastF1 para o cache SQLite normalizado.

Descobre todas as temporadas disponíveis (2018 até o ano atual) e executa o
SeasonPipeline para cada uma, com retry automático em caso de rate limit.

Uso:
    python scripts/load_all.py
    python scripts/load_all.py --from 2021 --to 2024
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.pipelines.season_pipeline import SeasonPipeline  # noqa: E402
from backend.services.downloader import FastF1Downloader      # noqa: E402

# FastF1 tem dados confiaveis a partir de 2018
FIRST_SEASON = 2018


def _all_seasons() -> list[int]:
    return list(range(FIRST_SEASON, datetime.now().year + 1))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Carrega todas as temporadas disponíveis do FastF1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/load_all.py
  python scripts/load_all.py --from 2021 --to 2024
        """,
    )
    parser.add_argument(
        "--from", dest="from_season", type=int,
        help="Temporada inicial (padrão: 2018)",
    )
    parser.add_argument(
        "--to", dest="to_season", type=int,
        help="Temporada final (padrão: ano atual)",
    )
    args = parser.parse_args()

    first = args.from_season or FIRST_SEASON
    last = args.to_season or datetime.now().year
    seasons = list(range(first, last + 1))

    print("\n" + "=" * 70)
    print("  PITWALL ANALYTICS - CARREGAMENTO COMPLETO DE DADOS")
    print("=" * 70)
    print(f"\n  Temporadas: {first} - {last}  ({len(seasons)} temporadas)")
    print(
        "\n  RATE LIMITING: o downloader aguarda automaticamente em caso"
        "\n  de limite de requisicoes (backoff exponencial, ate 1h)."
    )
    print()

    try:
        response = input("  Deseja continuar? (s/N): ").strip().lower()
        if response not in ("s", "sim", "y", "yes"):
            print("\n  Cancelado.")
            return
    except KeyboardInterrupt:
        print("\n\n  Cancelado.")
        return

    start = time.time()

    downloader = FastF1Downloader(cache_dir=project_root / ".ff1cache")
    pipeline = SeasonPipeline(downloader)

    for season in seasons:
        pipeline.run(season)

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print("  CONCLUIDO!")
    print(f"  Tempo total: {elapsed / 60:.1f} min")
    print(f"  Chamadas API: {downloader.api_calls}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrompido pelo usuario (Ctrl+C)")
        sys.exit(1)
