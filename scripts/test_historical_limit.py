
import fastf1 as ff1
from typing import List

def check_years(start_year: int, end_year: int):
    print(f"{'Ano':<6} | {'Status Schedule':<20} | {'Status Session'}")
    print("-" * 50)
    
    for year in range(start_year, end_year + 1):
        try:
            # Tentar pegar o calendário
            schedule = ff1.get_event_schedule(year)
            schedule_status = "✅ OK" if not schedule.empty else "❓ Vazio"
            
            # Tentar pegar o primeiro evento/sessão do calendário (Round 1)
            try:
                session = ff1.get_session(year, 1, 'R')
                session_status = "✅ Session OK"
            except Exception:
                session_status = "❌ Sem sessão"
                
            print(f"{year:<6} | {schedule_status:<20} | {session_status}")
        except Exception as e:
            print(f"{year:<6} | ❌ Erro: {str(e)[:30]}")

if __name__ == "__main__":
    print("=== Teste de Disponibilidade Histórica FastF1 ===\n")
    # Testar de 2015 até hoje
    check_years(2015, 2026)
