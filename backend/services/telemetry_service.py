"""
F1 Telemetry Head-to-Head Analysis Service

Reads optimized telemetry from the SQLite cache.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from backend.repositories.data_repository import DataRepository

class TelemetryService:
    """Service for handling telemetry comparison using cached SQL data"""

    def __init__(self):
        self.repo = DataRepository()

    def get_head_to_head_telemetry(
        self,
        year: int,
        gp: str,
        session_type: str,
        drivers: List[str],
    ) -> Dict[str, Any]:
        """
        Fetches and aligns telemetry for N drivers' best laps from cache.
        All drivers are interpolated onto a common distance axis.
        """
        # 1. Resolver evento e sessão
        event = self.repo.get_event_by_name(year, gp)
        if not event:
            raise ValueError(f"Evento {gp} não encontrado para {year}")

        session = self.repo.get_session(year, event['id'], session_type)
        if not session:
            raise ValueError(f"Sessão {session_type} não encontrada")

        # 2. Buscar melhor volta de cada piloto
        rename_map = {
            'speed': 'Speed',
            'rpm': 'RPM',
            'throttle': 'Throttle',
            'gear': 'nGear',
            'drs': 'DRS',
        }

        laps_data: Dict[str, dict] = {}
        tele_data: Dict[str, pd.DataFrame] = {}

        for drv in drivers:
            laps = self.repo.get_laps_for_session(year, session['id'], drv)
            valid_laps = [l for l in laps if l.get('lap_time_seconds')]
            if not valid_laps:
                raise ValueError(f"Nenhuma volta válida encontrada para {drv}")

            best_lap = min(valid_laps, key=lambda x: x['lap_time_seconds'])
            raw = self.repo.get_telemetry_for_lap(year, best_lap['id'])
            if not raw:
                raise ValueError(f"Telemetria não encontrada para {drv}")

            df = pd.DataFrame(raw)

            # Se tivermos 'distance' (vindo do Parquet), use ela.
            # Caso contrário, calcule a partir de velocidade/tempo (fallback SQL).
            if 'distance' in df.columns:
                df['Distance'] = df['distance']
            else:
                # Fallback calculation (m/s * dt)
                dt = df['session_time_seconds'].diff().fillna(0)
                df['Distance'] = (df['speed'] / 3.6 * dt).cumsum()

            df = df.rename(columns=rename_map)

            laps_data[drv] = best_lap
            tele_data[drv] = df

        # 3. Eixo de distância comum (mínimo entre todos os pilotos)
        max_dist = min(df['Distance'].max() for df in tele_data.values())
        distance_points = np.linspace(0, max_dist, 1000)

        cols = ['Speed', 'RPM', 'Throttle', 'nGear', 'DRS']

        def interpolate_driver(df: pd.DataFrame) -> Dict[str, list]:
            result = {'Distance': distance_points.tolist()}
            for col in cols:
                if col in df.columns:
                    result[col] = np.interp(distance_points, df['Distance'], df[col]).tolist()
                else:
                    result[col] = [0] * len(distance_points)
            return result

        return {
            'metadata': {
                'year': year,
                'event': event['name'],
                'session': session['name'],
                'drivers': drivers,
                'lap_times': {
                    drv: laps_data[drv]['lap_time_seconds']
                    for drv in drivers
                },
            },
            'telemetry': {
                'distance': distance_points.tolist(),
                'drivers': {drv: interpolate_driver(df) for drv, df in tele_data.items()},
            },
            'corners': [],
        }
