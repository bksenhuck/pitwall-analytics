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
            laps = self.repo.get_laps_for_session(year, session['id'], driver_filter=drv)
            valid_laps = [l for l in laps if l.get('lap_time_seconds')]
            if not valid_laps:
                raise ValueError(f"Nenhuma volta válida encontrada para {drv}")

            best_lap = min(valid_laps, key=lambda x: x['lap_time_seconds'])
            df = self.repo.get_telemetry_for_lap(year, best_lap['id'], session_id=best_lap.get('session_id'))
            if df is None or not df:
                raise ValueError(f"Telemetria não encontrada para {drv}")

            df = pd.DataFrame(df)
            if df.empty:
                raise ValueError(f"Telemetria vazia para {drv}")

            # Se tivermos 'distance' (vindo do Parquet), use ela.
            # Caso contrário, calcule a partir de velocidade/tempo (fallback SQL).
            if 'distance' in df.columns:
                df['Distance'] = df['distance']
            else:
                # Fallback calculation (m/s * dt)
                if 'session_time_seconds' in df.columns:
                    dt = df['session_time_seconds'].diff().fillna(0)
                elif 'time' in df.columns:
                    dt = df['time'].diff().fillna(0)
                else:
                    dt = 0.1  # Default time step
                
                if 'speed' in df.columns:
                    df['Distance'] = (df['speed'] / 3.6 * dt).cumsum()
                else:
                    df['Distance'] = 0  # No speed data, use zero distance

            df = df.rename(columns=rename_map)

            laps_data[drv] = best_lap
            tele_data[drv] = df

        # 3. Alinhamento e calculo de Delta (gap)
        # Usamos o primeiro piloto como referencia para o Delta
        ref_drv = drivers[0]
        ref_tele = tele_data[ref_drv]
        
        # Eixo de distância comum: usamos a distância da volta de referência
        # (geralmente a melhor volta do primeiro piloto selecionado)
        max_dist = ref_tele['Distance'].max() if 'Distance' in ref_tele.columns else 100
        if max_dist <= 0:
            max_dist = 100  # Default fallback
        distance_points = np.linspace(0, max_dist, 1000)

        def interpolate_driver(df: pd.DataFrame) -> Dict[str, list]:
            result = {}
            # Speed, RPM, etc.
            cols_to_interp = ['Speed', 'RPM', 'Throttle', 'nGear', 'DRS', 'x', 'y', 'z']
            for col in cols_to_interp:
                if col in df.columns:
                    # Garantir que interpolamos contra a distância prorpia do DF
                    result[col] = np.interp(distance_points, df['Distance'], df[col]).tolist()
                else:
                    result[col] = [0] * len(distance_points)
                    
            # Calculo do Tempo Acumulado para o Delta
            # time = distance / speed
            # Evitar divisão por zero
            if 'Speed' in df.columns:
                speed_ms = np.maximum(df['Speed'] / 3.6, 0.1)
            else:
                speed_ms = 0.1
            # Interpola o tempo acumulado na distância comum
            # Primeiro calculamos o tempo acumulado no DF original
            if 'session_time_seconds' in df.columns:
                # Usamos o tempo da sessão relativo ao início da volta
                lap_start_time = df['session_time_seconds'].iloc[0]
                accum_time = df['session_time_seconds'] - lap_start_time
                result['AccumTime'] = np.interp(distance_points, df['Distance'], accum_time).tolist()
            else:
                # Fallback se não tiver tempo de sessão: calcula por dist/speed
                # (menos preciso que o tempo real do sensor)
                # ... mas idealmente o repo sempre retorna session_time_seconds
                result['AccumTime'] = [0] * len(distance_points)
                
            return result

        interpolated = {drv: interpolate_driver(df) for drv, df in tele_data.items()}
        
        # Calcular Delta (em relação ao primeiro piloto)
        # Delta = Tempo(Piloto X) - Tempo(Referência)
        ref_accum_time = np.array(interpolated[ref_drv]['AccumTime'])
        for drv in drivers:
            drv_accum_time = np.array(interpolated[drv]['AccumTime'])
            interpolated[drv]['Delta'] = (drv_accum_time - ref_accum_time).tolist()

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
                'drivers': interpolated,
            },
            'corners': [],
        }
