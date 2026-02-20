"""
Carrega TODOS os dados disponíveis do FastF1 para o cache SQLite normalizado.

Este script:
1. Descobre todas as temporadas disponíveis (2018 até o ano atual)
2. Para cada temporada, carrega todos os eventos (GPs)
3. Para cada evento, carrega todas as sessões (FP1, FP2, FP3, Q, Sprint, Race)
4. Salva tudo no banco SQLite normalizado

Uso:
    python scripts/load_all.py
    
Atenção: Isso pode demorar VÁRIAS HORAS dependendo da conexão e quantidade de dados!
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import fastf1 as ff1
from datetime import datetime
from backend.db.session import init_database, get_db_connection
from typing import List, Tuple
import time


class AllDataLoader:
    """Carrega todos os dados disponíveis do FastF1."""
    
    def __init__(self):
        self.stats = {
            'seasons': 0,
            'events': 0,
            'sessions_loaded': 0,
            'sessions_skipped': 0,
            'errors': []
        }
        self.start_time = time.time()
    
    def get_all_seasons(self) -> List[int]:
        """Retorna lista de todas as temporadas disponíveis."""
        current_year = datetime.now().year
        # FastF1 tem dados confiáveis de 2018 em diante
        return list(range(2018, current_year + 1))
    
    def session_exists(self, season: int, event_name: str, session_type: str) -> bool:
        """Verifica se a sessão já existe no banco."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Busca a sessão no banco
                cursor.execute("""
                    SELECT COUNT(*) FROM sessions s
                    JOIN events e ON s.event_id = e.id
                    WHERE e.season = ? AND e.event_name = ? AND s.session_type = ?
                """, (season, event_name, session_type))
                
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            return False
    
    def save_session_to_db(self, session, season: int, event_name: str) -> Tuple[bool, str]:
        """
        Salva uma sessão completa no banco normalizado.
        
        Returns:
            (success: bool, message: str)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Inserir/obter season
                cursor.execute("""
                    INSERT OR IGNORE INTO seasons (season) VALUES (?)
                """, (season,))
                
                # 2. Inserir/obter event
                event_date = str(session.date.date()) if session.date else None
                cursor.execute("""
                    INSERT OR IGNORE INTO events (season, event_name, location, event_date)
                    VALUES (?, ?, ?, ?)
                """, (season, event_name, session.event.get('Location', ''), event_date))
                
                cursor.execute("""
                    SELECT id FROM events WHERE season = ? AND event_name = ?
                """, (season, event_name))
                event_id = cursor.fetchone()[0]
                
                # 3. Inserir session
                session_date = str(session.date) if session.date else None
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (event_id, session_type, session_name, session_date)
                    VALUES (?, ?, ?, ?)
                """, (event_id, session.name, session.name, session_date))
                
                cursor.execute("SELECT last_insert_rowid()")
                session_id = cursor.fetchone()[0]
                
                # 4. Inserir laps
                if session.laps is not None and len(session.laps) > 0:
                    laps_inserted = 0
                    for _, lap in session.laps.iterrows():
                        try:
                            lap_time_sec = lap['LapTime'].total_seconds() if 'LapTime' in lap and lap['LapTime'] is not None else None
                            sector1_sec = lap['Sector1Time'].total_seconds() if 'Sector1Time' in lap and lap['Sector1Time'] is not None else None
                            sector2_sec = lap['Sector2Time'].total_seconds() if 'Sector2Time' in lap and lap['Sector2Time'] is not None else None
                            sector3_sec = lap['Sector3Time'].total_seconds() if 'Sector3Time' in lap and lap['Sector3Time'] is not None else None
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO laps
                                (session_id, driver_code, lap_number, lap_time_seconds,
                                 sector1_time_seconds, sector2_time_seconds, sector3_time_seconds,
                                 speed_i1, speed_i2, speed_fl, speed_st,
                                 is_personal_best, compound, tyre_life, stint, fresh_tyre,
                                 team, lap_start_time, lap_start_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                session_id,
                                lap.get('Driver', ''),
                                int(lap.get('LapNumber', 0)),
                                lap_time_sec,
                                sector1_sec,
                                sector2_sec,
                                sector3_sec,
                                float(lap['SpeedI1']) if 'SpeedI1' in lap and lap['SpeedI1'] is not None else None,
                                float(lap['SpeedI2']) if 'SpeedI2' in lap and lap['SpeedI2'] is not None else None,
                                float(lap['SpeedFL']) if 'SpeedFL' in lap and lap['SpeedFL'] is not None else None,
                                float(lap['SpeedST']) if 'SpeedST' in lap and lap['SpeedST'] is not None else None,
                                bool(lap.get('IsPersonalBest', False)),
                                lap.get('Compound', ''),
                                int(lap['TyreLife']) if 'TyreLife' in lap and lap['TyreLife'] is not None else None,
                                int(lap['Stint']) if 'Stint' in lap and lap['Stint'] is not None else None,
                                bool(lap.get('FreshTyre', False)),
                                lap.get('Team', ''),
                                str(lap.get('LapStartTime', '')),
                                str(lap.get('LapStartDate', ''))
                            ))
                            laps_inserted += 1
                        except Exception as e:
                            # Continua mesmo se uma volta falhar
                            continue
                
                # 5. Inserir results
                if session.results is not None and len(session.results) > 0:
                    for _, result in session.results.iterrows():
                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO results
                                (session_id, driver_code, position, grid_position, status, points, team)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                session_id,
                                result.get('Abbreviation', result.get('Driver', '')),
                                int(result.get('Position', 0)) if result.get('Position') else None,
                                int(result.get('GridPosition', 0)) if result.get('GridPosition') else None,
                                result.get('Status', ''),
                                float(result.get('Points', 0)),
                                result.get('TeamName', result.get('Team', ''))
                            ))
                        except Exception:
                            continue
                
                # 6. Inserir weather (sample - não todos os pontos)
                if session.weather_data is not None and len(session.weather_data) > 0:
                    # Pega apenas 1 ponto a cada 5 minutos para não sobrecarregar
                    weather_sample = session.weather_data.iloc[::30]  # Sample
                    for _, weather in weather_sample.iterrows():
                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO weather
                                (session_id, air_temp, track_temp, humidity, pressure, wind_speed, rainfall)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                session_id,
                                float(weather.get('AirTemp', 0)) if weather.get('AirTemp') is not None else None,
                                float(weather.get('TrackTemp', 0)) if weather.get('TrackTemp') is not None else None,
                                float(weather.get('Humidity', 0)) if weather.get('Humidity') is not None else None,
                                float(weather.get('Pressure', 0)) if weather.get('Pressure') is not None else None,
                                float(weather.get('WindSpeed', 0)) if weather.get('WindSpeed') is not None else None,
                                bool(weather.get('Rainfall', False))
                            ))
                        except Exception:
                            continue
                
                # 7. Race control messages (sample)
                if session.race_control_messages is not None and len(session.race_control_messages) > 0:
                    for _, msg in session.race_control_messages.iterrows():
                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO race_control_messages
                                (session_id, category, message, flag, scope)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                session_id,
                                msg.get('Category', ''),
                                msg.get('Message', ''),
                                msg.get('Flag', ''),
                                msg.get('Scope', '')
                            ))
                        except Exception:
                            continue
                
                conn.commit()
                return True, f"Salvou {laps_inserted} voltas"
                
        except Exception as e:
            return False, f"Erro ao salvar: {str(e)}"
    
    def load_session(self, season: int, event_name: str, session_type: str) -> bool:
        """
        Carrega uma sessão do FastF1 e salva no banco.
        
        Returns:
            True se sucesso, False se erro
        """
        session_name = f"{season} {event_name} - {session_type}"
        
        try:
            # Verifica se já existe
            if self.session_exists(season, event_name, session_type):
                print(f"   ⏭️  {session_type:3} - Já existe no cache")
                self.stats['sessions_skipped'] += 1
                return True
            
            print(f"   ⏳ {session_type:3} - Carregando...", end='', flush=True)
            
            # Carrega sessão
            session = ff1.get_session(season, event_name, session_type)
            session.load(laps=True, telemetry=False, weather=True, messages=True)
            
            # Salva no banco
            success, message = self.save_session_to_db(session, season, event_name)
            
            if success:
                print(f" ✅ {message}")
                self.stats['sessions_loaded'] += 1
                return True
            else:
                print(f" ❌ {message}")
                self.stats['errors'].append(f"{session_name}: {message}")
                return False
                
        except Exception as e:
            print(f" ❌ Erro: {str(e)[:50]}")
            self.stats['errors'].append(f"{session_name}: {str(e)}")
            return False
    
    def load_event(self, season: int, event):
        """Carrega todas as sessões de um evento."""
        event_name = event['EventName']
        event_format = event.get('EventFormat', 'conventional')
        
        # Pula eventos de teste
        if 'testing' in event_name.lower() or 'test' in event_name.lower():
            print(f"\n  ⏭️  {event_name} - Pulado (evento de teste)")
            return
        
        print(f"\n  📍 {event_name}")
        
        # Lista de sessões para tentar
        sessions_to_load = ['FP1', 'FP2', 'FP3', 'Q', 'R']
        
        # Se for formato Sprint, adiciona Sprint sessions
        if event_format == 'sprint':
            sessions_to_load = ['FP1', 'SQ', 'S', 'Q', 'R']
        elif event_format == 'sprint_shootout':
            sessions_to_load = ['FP1', 'SS', 'S', 'Q', 'R']
        
        for session_type in sessions_to_load:
            self.load_session(season, event_name, session_type)
        
        self.stats['events'] += 1
    
    def load_season(self, season: int):
        """Carrega todas as corridas de uma temporada."""
        print(f"\n{'='*80}")
        print(f"🏁 TEMPORADA {season}")
        print(f"{'='*80}")
        
        try:
            # Busca schedule
            schedule = ff1.get_event_schedule(season)
            print(f"   Encontrados {len(schedule)} eventos")
            
            # Carrega cada evento
            for idx, event in schedule.iterrows():
                self.load_event(season, event)
            
            self.stats['seasons'] += 1
            
        except Exception as e:
            print(f"   ❌ Erro ao processar temporada {season}: {e}")
            self.stats['errors'].append(f"Season {season}: {e}")
    
    def run(self):
        """Executa o carregamento completo."""
        print("\n" + "="*80)
        print("🏎️  PITWALL ANALYTICS - CARREGAMENTO COMPLETO DE DADOS")
        print("="*80)
        print()
        print("Este script vai carregar TODOS os dados disponíveis do FastF1.")
        print("Isso pode demorar VÁRIAS HORAS!")
        print()
        
        # Inicializa banco
        print("📦 Inicializando banco de dados...")
        init_database()
        print("✅ Banco inicializado\n")
        
        # Habilita cache do FastF1
        cache_dir = project_root / "data" / ".ff1cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        ff1.Cache.enable_cache(str(cache_dir))
        print(f"✅ FastF1 cache: {cache_dir}\n")
        
        # Busca todas as temporadas
        seasons = self.get_all_seasons()
        print(f"📅 Temporadas a carregar: {seasons[0]} - {seasons[-1]} ({len(seasons)} temporadas)\n")
        
        # Confirmação
        try:
            response = input("Deseja continuar? (s/N): ").strip().lower()
            if response not in ['s', 'sim', 'y', 'yes']:
                print("\n❌ Cancelado pelo usuário")
                return
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado pelo usuário")
            return
        
        print("\n🚀 Iniciando carregamento...\n")
        
        # Carrega cada temporada
        for season in seasons:
            self.load_season(season)
        
        # Estatísticas finais
        elapsed = time.time() - self.start_time
        print("\n" + "="*80)
        print("🏁 CARREGAMENTO CONCLUÍDO!")
        print("="*80)
        print(f"\n📊 Estatísticas:")
        print(f"   ✅ Temporadas processadas: {self.stats['seasons']}")
        print(f"   ✅ Eventos processados: {self.stats['events']}")
        print(f"   ✅ Sessões carregadas: {self.stats['sessions_loaded']}")
        print(f"   ⏭️  Sessões já existentes: {self.stats['sessions_skipped']}")
        print(f"   ⏱️  Tempo total: {elapsed/60:.1f} minutos")
        
        if self.stats['errors']:
            print(f"\n   ⚠️  Erros encontrados: {len(self.stats['errors'])}")
            print(f"   (Primeiros 5 erros:)")
            for error in self.stats['errors'][:5]:
                print(f"      - {error}")
        
        print("\n✅ Cache SQLite atualizado com sucesso!")
        print(f"   Localização: {project_root / 'data' / 'pitwall_cache.db'}")
        print()


if __name__ == '__main__':
    loader = AllDataLoader()
    try:
        loader.run()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompido pelo usuário (Ctrl+C)")
        print(f"\n📊 Progresso até agora:")
        print(f"   Temporadas: {loader.stats['seasons']}")
        print(f"   Eventos: {loader.stats['events']}")
        print(f"   Sessões carregadas: {loader.stats['sessions_loaded']}")
        sys.exit(1)
