
import sys
from pathlib import Path
import pandas as pd
import fastf1 as ff1
from typing import List, Dict, Any

# Ajustar o path para importar os módulos do backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.repositories.data_repository import DataRepository
from backend.services.downloader import FastF1Downloader

def get_db_status() -> Dict[int, List[str]]:
    """Retorna um mapeamento de temporada -> lista de nomes de eventos no DB local."""
    db_status = {}
    seasons = DataRepository.get_all_seasons()
    
    for season in seasons:
        try:
            events = DataRepository.get_events_for_season(season)
            db_status[season] = [ev['name'] for ev in events]
        except Exception:
            db_status[season] = []
            
    return db_status

def compare_data(seasons_to_check: List[int]):
    """Compara o que existe no FastF1 vs o que existe no banco local."""
    print(f"{'Temporada':<10} | {'Evento':<30} | {'Status Local':<15} | {'Disponível FastF1'}")
    print("-" * 80)
    
    db_status = get_db_status()
    downloader = FastF1Downloader(cache_dir=project_root / ".ff1cache")
    
    for season in seasons_to_check:
        try:
            # Pegar cronograma do FastF1
            schedule = downloader.get_event_schedule(season)
            local_events = db_status.get(season, [])
            
            for _, event in schedule.iterrows():
                event_name = event['EventName']
                is_local = event_name in local_events
                
                # Check simple availability (se a data do evento já passou, provavelmente tem dados)
                # O FastF1 não tem um "is_available" direto sem tentar dar load, 
                # mas o cronograma indica o que DEVERIA existir.
                status_local = "✅ Carregado" if is_local else "❌ Faltando"
                
                # Para o FastF1, consideramos disponível se estiver no schedule
                print(f"{season:<10} | {event_name[:30]:<30} | {status_local:<15} | Sim")
                
        except Exception as e:
            print(f"{season:<10} | Erro ao buscar: {str(e)[:50]}")

if __name__ == "__main__":
    import datetime
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=int, default=2018, help="Ano inicial para verificação")
    args = parser.parse_args()
    
    current_year = datetime.datetime.now().year
    seasons = list(range(current_year, args.since - 1, -1))
    
    print(f"\n=== Comparação de Dados: FastF1 vs Banco de Dados Local (Desde {args.since}) ===\n")
    compare_data(seasons)
    
    # Mostrar também o que temos no DB que não pedimos para checar (seasons antigas)
    all_local_seasons = DataRepository.get_all_seasons()
    extra_seasons = [s for s in all_local_seasons if s not in seasons]
    if extra_seasons:
        print(f"\nOutras temporadas encontradas no DB: {extra_seasons}")
