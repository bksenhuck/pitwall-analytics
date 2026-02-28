"""
Season Pipeline

Orchestrates downloading and storing a complete F1 season (or a filtered
subset of events) using FastF1Downloader + BasePipeline helpers.
"""
import logging
from typing import Optional

from backend.pipelines.base import BasePipeline
from backend.services.downloader import FastF1Downloader

logger = logging.getLogger(__name__)

# Map EventFormat values to session type lists (no extra API calls needed)
_SESSION_TYPES: dict[str, list[str]] = {
    "conventional":    ["FP1", "FP2", "FP3", "Q", "R"],
    "sprint":          ["FP1", "SQ", "S", "Q", "R"],
    "sprint_shootout": ["FP1", "SQ", "S", "Q", "R"],
    "testing":         ["FP1", "FP2", "FP3"],  # test events: 3 practice days
}
_SESSION_TYPES_DEFAULT = _SESSION_TYPES["conventional"]


class SeasonPipeline(BasePipeline):
    """
    Downloads and stores all data for one or more F1 seasons.

    Usage:
        downloader = FastF1Downloader(cache_dir=Path(".ff1cache"))
        pipeline   = SeasonPipeline(downloader)
        pipeline.run(2024)
        pipeline.run(2024, event_filter="Bahrain")
    """

    def __init__(self, downloader: FastF1Downloader):
        super().__init__(downloader)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, season: int, event_filter: Optional[str] = None) -> None:
        """
        Download and store all events (and their sessions) for *season*.

        Args:
            season: F1 season year (e.g. 2024).
            event_filter: Optional substring to filter events by name
                          (case-insensitive). E.g. "Bahrain".
        """
        print(f"\n{'='*60}")
        print(f"  Temporada {season}")
        print(f"{'='*60}\n")

        self._init_season_db(season)
        self._insert_season(season)

        try:
            schedule = self.downloader.get_event_schedule(season)
        except Exception as exc:
            print(f"  ERRO ao buscar calendario de {season}: {exc}")
            logger.error("Failed to fetch schedule for %d: %s", season, exc)
            return

        total = len(schedule)
        for idx, (_, event_info) in enumerate(schedule.iterrows(), 1):
            event_name = str(
                event_info.get(
                    "EventName",
                    event_info.get("OfficialEventName", f"Round {idx}"),
                )
            )
            event_format = str(
                event_info.get("EventFormat", "conventional")
            ).lower()

            if event_filter and event_filter.lower() not in event_name.lower():
                continue

            print(f"\n[{idx}/{total}] {event_name}  [{event_format}]")
            print("-" * 60)

            event_id = self._insert_event(season, event_info, idx)
            if not event_id:
                print("  Evento ignorado (falha ao inserir no banco)")
                continue

            session_types = _SESSION_TYPES.get(
                event_format, _SESSION_TYPES_DEFAULT
            )
            self._run_event_sessions(
                season, event_name, event_id, session_types
            )

        print(f"\n{'='*60}")
        print(
            f"  Temporada {season} concluida  "
            f"|  {self.downloader.api_calls} chamadas API"
        )
        print(f"{'='*60}\n")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_event_sessions(
        self,
        season: int,
        event_name: str,
        event_id: int,
        session_types: list[str],
    ) -> None:
        """Download and store the given session types for one event."""
        for session_type in session_types:
            print(f"  {session_type}...", end=" ", flush=True)
            try:
                session = self.downloader.get_session(
                    season, event_name, session_type
                )
                self.downloader.load_session(
                    session,
                    laps=True,
                    telemetry=True,
                    weather=True,
                    messages=True,
                )

                session_id = self._insert_session(
                    season, event_id, session_type, session
                )
                if not session_id:
                    print("ERRO (falha ao inserir sessao)")
                    continue

                laps = self._insert_laps(season, session_id, session)
                tel = self._insert_telemetry(season, session_id, session)
                results = self._insert_results(season, session_id, session)
                weather = self._insert_weather(season, session_id, session)
                msgs = self._insert_race_control_messages(
                    season, session_id, session
                )
                status = self._insert_session_status(
                    season, session_id, session
                )

                print(
                    f"OK  "
                    f"L:{laps} T:{tel} R:{results} "
                    f"W:{weather} M:{msgs} S:{status}"
                )

            except Exception as exc:
                print(f"IGNORADO  ({str(exc)[:70]})")
                logger.warning(
                    "Session %s/%s/%s skipped: %s",
                    season, event_name, session_type, exc,
                )
                continue
