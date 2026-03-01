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
    "testing":         ["FP1", "FP2", "FP3"],  # mapped to day 1/2/3
}
_SESSION_TYPES_DEFAULT = _SESSION_TYPES["conventional"]

# Testing session types map to day numbers for get_testing_session()
_TESTING_DAY_MAP: dict[str, int] = {"FP1": 1, "FP2": 2, "FP3": 3}


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
        test_counter = 0  # tracks how many testing events we've seen

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
            round_number = int(event_info.get("RoundNumber", idx))

            if event_filter and event_filter.lower() not in event_name.lower():
                continue

            print(
                f"\n[{idx}/{total}] {event_name}  "
                f"[round {round_number}  {event_format}]"
            )
            print("-" * 60)

            event_id = self._insert_event(season, event_info, idx)
            if not event_id:
                print("  Evento ignorado (falha ao inserir no banco)")
                continue

            session_types = _SESSION_TYPES.get(
                event_format, _SESSION_TYPES_DEFAULT
            )

            if event_format == "testing":
                test_counter += 1
                self._run_testing_sessions(
                    season, test_counter, event_name, event_id, session_types
                )
            else:
                # Regular events: use round_number (int) — avoids FastF1
                # fuzzy name matching that can redirect to the wrong event.
                self._run_event_sessions(
                    season, round_number, event_name, event_id, session_types
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
        round_number: int,
        event_name: str,
        event_id: int,
        session_types: list[str],
    ) -> None:
        """Download and store regular (non-testing) event sessions.

        Uses round_number (int) for the FastF1 lookup — unambiguous,
        no fuzzy name matching.
        """
        for session_type in session_types:
            print(f"  {session_type}...", end=" ", flush=True)
            try:
                session = self.downloader.get_session(
                    season, round_number, session_type
                )
                self.downloader.load_session(
                    session,
                    laps=True,
                    telemetry=True,
                    weather=True,
                    messages=True,
                )
                self._store_session(
                    season, event_id, session_type, session, event_name
                )
            except Exception as exc:
                print(f"IGNORADO  ({str(exc)[:70]})")
                logger.warning(
                    "Session %s/%d/%s/%s skipped: %s",
                    season, round_number, event_name, session_type, exc,
                )

    def _run_testing_sessions(
        self,
        season: int,
        test_number: int,
        event_name: str,
        event_id: int,
        session_types: list[str],
    ) -> None:
        """Download and store pre-season testing sessions.

        Uses fastf1.get_testing_session(season, test_number, day_number)
        which bypasses event-name lookup entirely — no fuzzy matching.
        """
        for session_type in session_types:
            day_number = _TESTING_DAY_MAP.get(session_type)
            if day_number is None:
                continue

            print(f"  {session_type} (dia {day_number})...", end=" ", flush=True)
            try:
                session = self.downloader.get_testing_session(
                    season, test_number, day_number
                )
                self.downloader.load_session(
                    session,
                    laps=True,
                    telemetry=True,
                    weather=True,
                    messages=True,
                )
                self._store_session(
                    season, event_id, session_type, session, event_name
                )
            except Exception as exc:
                print(f"IGNORADO  ({str(exc)[:70]})")
                logger.warning(
                    "Testing session %s/test%d/%s/%s skipped: %s",
                    season, test_number, event_name, session_type, exc,
                )

    def _store_session(
        self,
        season: int,
        event_id: int,
        session_type: str,
        session,
        event_name: str,
    ) -> None:
        """Insert session data into the DB and print result summary."""
        session_id = self._insert_session(
            season, event_id, session_type, session
        )
        if not session_id:
            print("ERRO (falha ao inserir sessao)")
            return

        laps = self._insert_laps(season, session_id, session)
        tel = self._insert_telemetry(season, session_id, session)
        results = self._insert_results(season, session_id, session)
        weather = self._insert_weather(season, session_id, session)
        msgs = self._insert_race_control_messages(season, session_id, session)
        status = self._insert_session_status(season, session_id, session)

        print(
            f"OK  L:{laps} T:{tel} R:{results} "
            f"W:{weather} M:{msgs} S:{status}"
        )
