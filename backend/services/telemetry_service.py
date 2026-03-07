"""
F1 Telemetry Head-to-Head Analysis Service

Reads optimized telemetry from the SQLite cache.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List
from backend.repositories.data_repository import DataRepository

logger = logging.getLogger(__name__)

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
        print(f"\n{'='*80}")
        print(f"🔍 INICIANDO TELEMETRIA: {year} {gp} {session_type} drivers={drivers}")
        print(f"{'='*80}\n")
        logger.info(f"🔍 Iniciando telemetria: {year} {gp} {session_type} drivers={drivers}")
        
        try:
            # 1. Resolver evento e sessão
            print(f"📍 Procurando evento: {gp}")
            logger.info(f"📍 Procurando evento: {gp}")
            event = self.repo.get_event_by_name(year, gp)
            if not event:
                print(f"❌ Evento não encontrado: {gp} {year}")
                logger.error(f"❌ Evento não encontrado: {gp} {year}")
                raise ValueError(f"Evento {gp} não encontrado para {year}")
            print(f"✅ Evento encontrado: {event['name']} (ID: {event['id']})")
            logger.info(f"✅ Evento encontrado: {event['name']} (ID: {event['id']})")

            print(f"🔎 Procurando sessão: {session_type}")
            logger.info(f"🔎 Procurando sessão: {session_type}")
            session = self.repo.get_session(year, event['id'], session_type)
            if not session:
                print(f"❌ Sessão não encontrada: {session_type}")
                logger.error(f"❌ Sessão não encontrada: {session_type}")
                raise ValueError(f"Sessão {session_type} não encontrada")
            print(f"✅ Sessão encontrada: {session['name']} (ID: {session['id']})")
            logger.info(f"✅ Sessão encontrada: {session['name']} (ID: {session['id']})")

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
            logger.info(f"🏎️  Processando piloto: {drv}")
            try:
                laps = self.repo.get_laps_for_session(year, session['id'], driver_filter=drv)
                logger.info(f"   📊 Voltas encontradas: {len(laps)}")
                
                valid_laps = [l for l in laps if l.get('lap_time_seconds')]
                logger.info(f"   ✓ Voltas válidas: {len(valid_laps)}")
                
                if not valid_laps:
                    logger.error(f"   ❌ Nenhuma volta válida para {drv}")
                    raise ValueError(f"Nenhuma volta válida encontrada para {drv}")

                best_lap = min(valid_laps, key=lambda x: x['lap_time_seconds'])
                logger.info(f"   🏁 Melhor volta: {best_lap['lap_time_seconds']:.3f}s (ID: {best_lap['id']})")
                
                logger.info(f"   🔄 Buscando telemetria para lap_id={best_lap['id']}")
                df = self.repo.get_telemetry_for_lap(year, best_lap['id'], session_id=best_lap.get('session_id'))
                logger.info(f"   📈 Telemetria bruta: {len(df) if df else 0} pontos")
                
                if df is None or not df:
                    logger.error(f"   ❌ Telemetria vazia para {drv}")
                    raise ValueError(f"Telemetria não encontrada para {drv}")

                df = pd.DataFrame(df)
                if df.empty:
                    logger.error(f"   ❌ DataFrame vazio para {drv}")
                    raise ValueError(f"Telemetria vazia para {drv}")
                
                logger.info(f"   🔍 Colunas do DataFrame: {list(df.columns)}")

                # Se tivermos 'distance' (vindo do Parquet), use ela.
                # Caso contrário, calcule a partir de velocidade/tempo (fallback SQL).
                if 'distance' in df.columns:
                    logger.info(f"   ✓ Usando coluna 'distance' do Parquet")
                    df['Distance'] = df['distance']
                else:
                    logger.info(f"   ⚠️  Recalculando 'distance' a partir de speed/time")
                    # Fallback calculation (m/s * dt)
                    if 'session_time_seconds' in df.columns:
                        dt = df['session_time_seconds'].diff().fillna(0)
                        logger.info(f"   ✓ Usando session_time_seconds")
                    elif 'time' in df.columns:
                        dt = df['time'].diff().fillna(0)
                        logger.info(f"   ✓ Usando time")
                    else:
                        dt = 0.1  # Default time step
                        logger.warn(f"   ⚠️  Usando tempo padrão 0.1s")
                    
                    if 'speed' in df.columns:
                        logger.info(f"   ✓ Usando speed para calcular distance")
                        df['Distance'] = (df['speed'] / 3.6 * dt).cumsum()
                    else:
                        logger.warn(f"   ⚠️  Sem coluna speed, usando index como distance")
                        # No speed data, use index-based distance
                        df['Distance'] = np.arange(len(df))
                
                logger.info(f"   📏 Distance range: {df['Distance'].min():.2f} - {df['Distance'].max():.2f}")

                df = df.rename(columns=rename_map)

                laps_data[drv] = best_lap
                tele_data[drv] = df
                logger.info(f"   ✅ Piloto {drv} processado com sucesso")
            except Exception as e:
                logger.exception(f"   ❌ ERRO ao processar {drv}: {str(e)}")
                raise

        # 3. Alinhamento e calculo de Delta (gap)
        logger.info(f"🔀 Iniciando interpolação para {len(tele_data)} pilotos")
        
        # Usamos o primeiro piloto como referencia para o Delta
        ref_drv = drivers[0]
        ref_tele = tele_data[ref_drv]
        
        # Eixo de distância comum: usamos a distância da volta de referência
        # (geralmente a melhor volta do primeiro piloto selecionado)
        max_dist = ref_tele['Distance'].max() if 'Distance' in ref_tele.columns else 100
        logger.info(f"📏 Distância máxima (referência): {max_dist:.2f}")
        
        if max_dist <= 0:
            logger.warn(f"⚠️  Distância inválida, usando fallback 100")
            max_dist = 100  # Default fallback
        
        distance_points = np.linspace(0, max_dist, 1000)
        logger.info(f"✓ Eixo de distância criado: {len(distance_points)} pontos [0-{max_dist:.2f}]")

        def interpolate_driver(df: pd.DataFrame) -> Dict[str, list]:
            result = {}
            # Speed, RPM, etc.
            cols_to_interp = ['Speed', 'RPM', 'Throttle', 'nGear', 'DRS', 'x', 'y', 'z']
            for col in cols_to_interp:
                if col in df.columns:
                    # Garantir que interpolamos contra a distância prorpia do DF
                    try:
                        result[col] = np.interp(distance_points, df['Distance'], df[col]).tolist()
                    except Exception as e:
                        logger.warn(f"   ⚠️  Erro interpolando {col}: {str(e)}, usando zeros")
                        result[col] = [0] * len(distance_points)
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
                try:
                    lap_start_time = df['session_time_seconds'].iloc[0]
                    accum_time = df['session_time_seconds'] - lap_start_time
                    result['AccumTime'] = np.interp(distance_points, df['Distance'], accum_time).tolist()
                except Exception as e:
                    logger.warn(f"   ⚠️  Erro calculando AccumTime: {str(e)}, usando zeros")
                    result['AccumTime'] = [0] * len(distance_points)
            else:
                # Fallback se não tiver tempo de sessão: calcula por dist/speed
                # (menos preciso que o tempo real do sensor)
                # ... mas idealmente o repo sempre retorna session_time_seconds
                logger.warn(f"   ⚠️  Sem session_time_seconds, AccumTime será zero")
                result['AccumTime'] = [0] * len(distance_points)
                
            return result

        logger.info(f"📊 Interpolando dados para {len(tele_data)} pilotos...")
        interpolated = {}
        for drv, df in tele_data.items():
            logger.info(f"   Interpolando {drv}...")
            try:
                interpolated[drv] = interpolate_driver(df)
                logger.info(f"   ✅ {drv} interpolado")
            except Exception as e:
                logger.exception(f"   ❌ ERRO interpolando {drv}: {str(e)}")
                raise
        
        # Calcular Delta (em relação ao primeiro piloto)
        logger.info(f"📈 Calculando Delta em relação a {ref_drv}...")
        # Delta = Tempo(Piloto X) - Tempo(Referência)
        ref_accum_time = np.array(interpolated[ref_drv]['AccumTime'])
        for drv in drivers:
            drv_accum_time = np.array(interpolated[drv]['AccumTime'])
            interpolated[drv]['Delta'] = (drv_accum_time - ref_accum_time).tolist()
            delta_min = min(interpolated[drv]['Delta'])
            delta_max = max(interpolated[drv]['Delta'])
            logger.info(f"   {drv}: Delta range [{delta_min:.3f}s - {delta_max:.3f}s]")

        logger.info(f"✅ Telemetria completa! Retornando resultado...")
        print(f"\n✅ SUCESSO! Resultado retornado\n")
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
        
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ ERRO CRÍTICO NA TELEMETRIA:")
            print(f"{type(e).__name__}: {str(e)}")
            print(f"{'='*80}\n")
            logger.exception(f"❌ ERRO CRÍTICO: {str(e)}")
            raise
