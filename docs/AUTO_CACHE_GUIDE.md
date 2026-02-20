# 🏎️ Auto Cache Population - Guia Completo

> **📍 Localização**: Este documento está em `docs/AUTO_CACHE_GUIDE.md`  
> **🔗 Veja também**: [MANUAL_CACHE_CONTROL.md](MANUAL_CACHE_CONTROL.md) | [../scripts/README.md](../scripts/README.md)

## O que é?

Um sistema inteligente que automaticamente descobre e carrega **TODOS** os dados disponíveis do FastF1 para o cache SQLite local.

## O que ele carrega?

Para cada sessão (Treino Livre, Qualificação, Corrida, Sprint), o sistema carrega:

### 📊 Dados de Voltas (Laps)
- Tempos de volta completos
- Tempos de setores (S1, S2, S3)
- Informações de pit stops
- Compostos de pneu
- Vida útil dos pneus
- Posições na pista
- Flags de voltas deletadas

### 🏁 Resultados (Results)
- Posições finais
- Tempos de qualificação (Q1, Q2, Q3)
- Grid positions
- Pontos conquistados
- Status de finalização

### 🌤️ Dados Meteorológicos (Weather)
- Temperatura do ar
- Temperatura da pista
- Umidade
- Pressão atmosférica
- Velocidade e direção do vento
- Chuva

### 🚩 Mensagens de Controle (Race Control Messages)
- Bandeiras (Verde, Amarela, Vermelha, SC, VSC)
- Investigações
- Penalidades
- Decisões dos comissários

### 📈 Status da Sessão/Pista
- Status da sessão (Started, Finished, Aborted)
- Status da pista (Green, Yellow, SC, VSC)
- Timestamps de eventos importantes

### 👥 Informações de Pilotos
- Lista de pilotos participantes
- Números dos carros
- Equipes

### 📡 Metadados
- Disponibilidade de telemetria
- Suporte da API F1
- Total de voltas programadas

> **Nota sobre Telemetria**: Dados de telemetria detalhada (Speed, RPM, Throttle, Brake, XYZ positions) são **muito grandes** e devem ser acessados sob demanda, não armazenados no cache.

## Como usar?

### 1. Verificar o que está faltando (Modo Check)

```bash
# Ver tudo que está faltando
python scripts/auto_populate_cache.py --check

# Ver o que falta de 2024
python scripts/auto_populate_cache.py --season 2024 --check

# Ver o que falta de 2023 em diante
python scripts/auto_populate_cache.py --from 2023 --check
```

### 2. Carregar dados automaticamente

```bash
# Carregar TUDO (2018 até hoje) - ISSO VAI DEMORAR!
python scripts/auto_populate_cache.py

# Carregar apenas 2024
python scripts/auto_populate_cache.py --season 2024

# Carregar de 2023 em diante
python scripts/auto_populate_cache.py --from 2023

# Carregar de 2022 até 2024
python scripts/auto_populate_cache.py --from 2022 --to 2024
```

### 3. Exemplos práticos

```bash
# Verificar o que precisa antes de baixar
python scripts/auto_populate_cache.py --season 2024 --check

# Se estiver ok, baixar
python scripts/auto_populate_cache.py --season 2024
```

## O que acontece?

1. **Descoberta**: O script busca todos os GPs da(s) temporada(s)
2. **Verificação**: Para cada GP, verifica todas as sessões (FP1, FP2, FP3, Q, Sprint, R)
3. **Cache Check**: Verifica se os dados já existem no SQLite
4. **Download**: Se não existir, baixa do FastF1
5. **Armazenamento**: Salva no SQLite com chave estruturada

## Tipos de Sessão

O script tenta carregar todas as sessões possíveis:

| Código | Nome | Quando existe |
|--------|------|---------------|
| FP1 | Free Practice 1 | Todos os GPs |
| FP2 | Free Practice 2 | Todos os GPs |
| FP3 | Free Practice 3 | GPs sem Sprint |
| Q | Qualifying | Todos os GPs |
| S | Sprint | Apenas fins de semana Sprint |
| SQ | Sprint Qualifying | Sprint em 2022 |
| SS | Sprint Shootout | Sprint desde 2023 |
| R | Race | Todos os GPs |

## Estrutura das Chaves de Cache

```
session_{ano}_{evento}_{tipo_sessao}_full
```

Exemplos:
- `session_2024_bahrain_grand_prix_r_full`
- `session_2024_monaco_grand_prix_q_full`
- `session_2024_miami_grand_prix_s_full`

## Performance e Tempo

### Por sessão:
- Sessões sem telemetria: ~5-15 segundos
- Sessões com telemetria: ~30-60 segundos (mas não salvamos telemetria!)

### Por temporada:
- ~24 GPs × ~6 sessões cada = ~144 sessões
- Tempo estimado: **30-60 minutos** por temporada

### Todas as temporadas (2018-2024):
- ~7 temporadas × 60 minutos = **~7 horas**

## Recomendações

### 🎯 Para desenvolvimento
```bash
python scripts/auto_populate_cache.py --season 2024
```

### 🎯 Para produção
```bash
# Carregar tudo de uma vez (deixe rodando)
python scripts/auto_populate_cache.py --from 2018
```

### 🎯 Para testar
```bash
# Primeiro veja o que vai baixar
python scripts/auto_populate_cache.py --season 2024 --check
```

## Vantagens vs `scripts/populate_cache.py` antigo

| Aspecto | Antigo | Novo |
|---------|--------|------|
| **Descoberta** | Manual | Automática |
| **Sessões** | Uma por vez | Todas de uma vez |
| **Verificação** | Não tinha | Verifica o que existe |
| **Dados** | Apenas voltas | TODOS os dados |
| **Usabilidade** | Precisa saber o nome exato | Apenas escolhe o ano |

## Integração com Backend

O backend continua funcionando igual:

```python
# Frontend chama backend
GET /api/read?key=session_2024_bahrain_grand_prix_r_full

# Backend lê do SQLite
# Retorna JSON com todos os dados
```

## Próximos Passos

1. Execute o script para carregar os dados que você precisa
2. Inicie o backend: `.\start.ps1`
3. O frontend terá acesso a TODOS os dados automaticamente

## Troubleshooting

### Erro: "No events found"
- Verifique sua conexão de internet
- FastF1 precisa acessar a API da F1

### Erro: Sessão específica falha
- Normal! Nem todos os GPs têm todas as sessões
- Sprints só existem em alguns GPs
- Continue, o script pula automaticamente

### Cache muito grande?
- Cada temporada: ~500MB-1GB
- Considere carregar apenas anos recentes

## Automatização

Você pode adicionar ao cron/scheduler para atualizar automaticamente:

```bash
# Toda segunda-feira às 2am, atualizar temporada atual
0 2 * * 1 cd /path/to/project && python scripts/auto_populate_cache.py --season 2024
```
