"""
Script de Migração: SQLite para Parquet
Lê os dados existentes no banco de dados SQLite e gera os arquivos Parquet correspondentes
para Laps, Weather, Results e Telemetry.
"""
import os
import pandas as pd
from pathlib import Path
from backend.repositories.data_repository import DataRepository
from backend.db.session import get_db_connection

def migrate_season(season: int):
    print(f"\n🚀 Iniciando migração da temporada {season}...")
    repo = DataRepository()
    
    # 1. Obter todos os eventos da temporada
    events = repo.get_events_for_season(season)
    if not events:
        print(f"⚠️ Nenhumm evento encontrado para a temporada {season}.")
        return

    # Preparar diretórios
    for dtype in ["laps", "weather", "results", "telemetry"]:
        Path(f"data/{dtype}/{season}").mkdir(parents=True, exist_ok=True)

    for event in events:
        event_id = event['id']
        print(f"📦 Processando Evento: {event['name']} (ID: {event_id})...")
        
        # --- NOVO: Agrupar TUDO do Evento (Prova) em arquivos únicos ---
        
        # 1. Migrar Laps do Evento
        with get_db_connection(season) as conn:
            df_event_laps = pd.read_sql_query("""
                SELECT l.* FROM laps l
                JOIN sessions s ON l.session_id = s.id
                WHERE s.event_id = ?
            """, conn, params=(event_id,))
            if not df_event_laps.empty:
                path = Path(f"data/laps/{season}/event_{event_id}.parquet")
                df_event_laps.to_parquet(path, compression='snappy', index=False)
                print(f"    ✅ Laps do Evento migrados.")

        # 2. Migrar Telemetria do Evento (O mais pesado)
        with get_db_connection(season) as conn:
            print(f"    ⏳ Lendo telemetria completa do evento {event_id}...")
            df_event_telemetry = pd.read_sql_query("""
                SELECT t.* FROM telemetry t
                JOIN laps l ON t.lap_id = l.id
                JOIN sessions s ON l.session_id = s.id
                WHERE s.event_id = ?
            """, conn, params=(event_id,))
            if not df_event_telemetry.empty:
                # Otimizar tipos
                for col in ['speed', 'rpm', 'throttle', 'x', 'y', 'z']:
                    if col in df_event_telemetry.columns:
                        df_event_telemetry[col] = df_event_telemetry[col].astype('float32')
                for col in ['gear', 'drs']:
                    if col in df_event_telemetry.columns:
                        df_event_telemetry[col] = df_event_telemetry[col].astype('int8')
                
                path = Path(f"data/telemetry/{season}/event_{event_id}.parquet")
                df_event_telemetry.to_parquet(path, compression='snappy', index=False)
                print(f"    ✅ Telemetria do Evento migrada ({len(df_event_telemetry)} amostras).")

        # 3. Migrar Weather do Evento
        with get_db_connection(season) as conn:
            df_event_weather = pd.read_sql_query("""
                SELECT w.* FROM weather w
                JOIN sessions s ON w.session_id = s.id
                WHERE s.event_id = ?
            """, conn, params=(event_id,))
            if not df_event_weather.empty:
                path = Path(f"data/weather/{season}/event_{event_id}.parquet")
                df_event_weather.to_parquet(path, compression='snappy', index=False)
                print(f"    ✅ Weather do Evento migrado.")

        # 4. Migrar Results do Evento
        with get_db_connection(season) as conn:
            df_event_results = pd.read_sql_query("""
                SELECT r.* FROM results r
                JOIN sessions s ON r.session_id = s.id
                WHERE s.event_id = ?
            """, conn, params=(event_id,))
            if not df_event_results.empty:
                path = Path(f"data/results/{season}/event_{event_id}.parquet")
                df_event_results.to_parquet(path, compression='snappy', index=False)
                print(f"    ✅ Results do Evento migrados.")



def run_migration():
    # Descobrir temporadas disponíveis
    repo = DataRepository()
    seasons = repo.get_all_seasons()
    
    if not seasons:
        print("❌ Nenhum banco de dados SQLite encontrado em data/ para migrar.")
        return

    print(f"🔍 Temporadas encontradas para migração: {seasons}")
    for s in seasons:
        migrate_season(s)
    
    print("\n✨ Migração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
