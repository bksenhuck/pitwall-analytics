"""
generate_all_predictions.py — Pre-compute ML predictions for all historical events.

Saves results to data/predictions/{season}/event_{event_id}.parquet.
Skips events that already have a parquet (use --force to recompute).

Usage:
    python -m scripts.generate_all_predictions
    python -m scripts.generate_all_predictions --season 2024
    python -m scripts.generate_all_predictions --force
"""
import argparse
import os
import sys

import pandas as pd

from backend.db.session import get_available_season_dbs
from backend.db.utils import db_fetchall
from ml.predict import generate_predictions

PREDICTIONS_DIR = os.path.join("data", "predictions")


def _get_race_events(season: int):
    """Return list of (event_id, event_name) that have a Race session with data."""
    rows = db_fetchall(season, """
        SELECT DISTINCT e.id, e.event_name
        FROM events e
        JOIN sessions s ON s.event_id = e.id
        WHERE e.season = ?
          AND s.session_type = 'R'
          AND s.has_data = 1
        ORDER BY e.round_number
    """, (season,))
    return [(r["id"], r["event_name"]) for r in rows]


def generate_season(season: int, force: bool = False):
    events = _get_race_events(season)
    if not events:
        print(f"  [SKIP] Nenhum evento com corrida encontrado para {season}")
        return

    season_dir = os.path.join(PREDICTIONS_DIR, str(season))
    os.makedirs(season_dir, exist_ok=True)

    for event_id, event_name in events:
        out_path = os.path.join(season_dir, f"event_{event_id}.parquet")
        if os.path.exists(out_path) and not force:
            print(f"  [OK]   {season} · {event_name} (já existe)")
            continue

        print(f"  [RUN]  {season} · {event_name} ...", end=" ", flush=True)
        try:
            df = generate_predictions(season=season, event_name=event_name)
            if df is None or df.empty:
                print("sem dados")
                continue
            df.to_parquet(out_path, index=False)
            print(f"salvo ({len(df)} pilotos)")
        except Exception as e:
            print(f"ERRO: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    seasons = [args.season] if args.season else get_available_season_dbs()
    print(f"Gerando predições para {len(seasons)} temporada(s): {seasons}")

    for season in seasons:
        print(f"\n=== Temporada {season} ===")
        generate_season(season, force=args.force)

    print("\nConcluído.")


if __name__ == "__main__":
    main()
