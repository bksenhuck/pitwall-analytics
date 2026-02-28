"""
Populate Cache - CLI para baixar dados do FastF1 e salvar no SQLite

Uso:
    python scripts/populate_cache.py --season 2024
    python scripts/populate_cache.py --season 2024 --event "Bahrain"
    python scripts/populate_cache.py --from 2023 --to 2024
    python scripts/populate_cache.py --list
"""
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.pipelines.season_pipeline import SeasonPipeline  # noqa: E402
from backend.repositories.data_repository import (  # noqa: E402
    DataRepository,
)
from backend.services.downloader import FastF1Downloader  # noqa: E402


def _make_pipeline() -> SeasonPipeline:
    downloader = FastF1Downloader(cache_dir=project_root / ".ff1cache")
    return SeasonPipeline(downloader)


def cmd_list() -> None:
    """Print all seasons and events currently stored in the local DB."""
    seasons = DataRepository.get_all_seasons()
    if not seasons:
        print("Nenhum dado disponivel. Execute --season primeiro.")
        return

    total_events = 0
    for season in seasons:
        try:
            events = DataRepository.get_events_for_season(season)
        except Exception:
            events = []
        total_events += len(events)
        print(f"\n{season}  ({len(events)} eventos)")
        for ev in events:
            location = ev.get("location", "")
            date = ev.get("event_date", "")
            suffix = f"  {location}" if location else ""
            suffix += f"  [{date}]" if date else ""
            print(f"  {ev['round_number']:>2}.  {ev['event_name']}{suffix}")

    print(f"\nTotal: {len(seasons)} temporada(s), {total_events} evento(s)")


def cmd_download(
    season: int | None = None,
    from_season: int | None = None,
    to_season: int | None = None,
    event: str | None = None,
) -> None:
    """Download one or more seasons using the SeasonPipeline."""
    pipeline = _make_pipeline()

    if from_season and to_season:
        for s in range(from_season, to_season + 1):
            pipeline.run(s)
    else:
        pipeline.run(season, event_filter=event)  # type: ignore[arg-type]

    print("Populacao concluida!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Popula o cache SQLite com dados do FastF1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/populate_cache.py --list
  python scripts/populate_cache.py --season 2024
  python scripts/populate_cache.py --season 2024 --event "Bahrain"
  python scripts/populate_cache.py --from 2023 --to 2024
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista todas as temporadas e corridas ja baixadas",
    )
    parser.add_argument(
        "--season", type=int, help="Temporada (ex: 2024)"
    )
    parser.add_argument(
        "--event", type=str, help="Filtro de evento (ex: 'Bahrain')"
    )
    parser.add_argument(
        "--from", dest="from_season", type=int, help="Temporada inicial"
    )
    parser.add_argument(
        "--to", dest="to_season", type=int, help="Temporada final"
    )

    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.from_season and args.to_season:
        cmd_download(from_season=args.from_season, to_season=args.to_season)
    elif args.season:
        cmd_download(season=args.season, event=args.event)
    else:
        parser.print_help()
        print("\nERRO: Especifique --list, --season ou --from/--to")
        sys.exit(1)


if __name__ == "__main__":
    main()
