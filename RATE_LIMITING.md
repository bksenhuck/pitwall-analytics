# Rate Limiting - FastF1 API

## Problema

A API oficial da F1 (usada pelo FastF1) tem um **limite de 500 chamadas por hora**.

Quando esse limite é ultrapassado, você verá este aviso:
```
⚠️ any API: 500 calls/h
```

## Solução Implementada

Ambos os scripts de carregamento de dados implementam rate limiting automático:

### 1. **scripts/populate_cache.py**
- Delay de **10 segundos** entre cada sessão carregada
- Permite ~360 chamadas/hora (margem de segurança)
- Mostra contador de API calls durante execução

### 2. **scripts/load_all.py**
- Delay de **10 segundos** entre cada sessão carregada
- Estatísticas finais incluem tempo gasto com rate limiting
- Configurável via constante `RATE_LIMIT_DELAY`

## Cálculos

### Limite da API
- **500 calls/hora** = 8.33 calls/minuto = 7.2 segundos/call (mínimo)

### Delay Configurado
- **10 segundos/call** = 6 calls/minuto = **360 calls/hora**
- Margem de segurança: **28% abaixo do limite**

### Tempo Estimado

Para carregar uma temporada completa (exemplo: 2024):
- **24 corridas** × **5 sessões** (FP1, FP2, FP3, Q, R) = 120 sessões
- 120 sessões × 10 segundos = **1.200 segundos** = **20 minutos** (só de delay)
- Tempo total: ~30-40 minutos (incluindo processamento)

Para carregar todas as temporadas (2018-2026):
- **9 temporadas** × ~22 corridas × 5 sessões = ~990 sessões
- 990 sessões × 10 segundos = **9.900 segundos** = **2h 45min** (só de delay)
- Tempo total estimado: **4-6 horas** (incluindo processamento)

## Como Ajustar

Se você tem acesso a uma API com limite diferente, pode ajustar o delay:

### Em `populate_cache.py` (linha ~28):
```python
RATE_LIMIT_DELAY = 10  # Altere para o valor desejado em segundos
```

### Em `load_all.py` (linha ~28):
```python
RATE_LIMIT_DELAY = 10  # Altere para o valor desejado em segundos
```

### Valores Recomendados

| Limite da API | Delay Recomendado | Calls/Hora |
|---------------|-------------------|------------|
| 500 calls/h   | 10 segundos       | 360        |
| 1000 calls/h  | 5 segundos        | 720        |
| 200 calls/h   | 20 segundos       | 180        |
| Sem limite    | 0 segundos        | Ilimitado  |

⚠️ **Importante:** Nunca configure delay menor que o permitido pelo seu limite!

## Cache do FastF1

O FastF1 também tem seu próprio cache local (`.ff1cache/`):
- Primeira vez: Faz chamada à API (conta no limite)
- Próximas vezes: Lê do cache local (NÃO conta no limite)

Portanto, se você reexecutar os scripts, sessões já baixadas serão puladas automaticamente.

## Monitoramento

Durante a execução, você verá:

```bash
   ⏳ R   - Carregando... ✅ 2667 laps, 20 results
      ⏱️  Aguardando 10s (rate limit: 15 calls)... ✓
```

Isso indica:
- ✅ Dados carregados com sucesso
- ⏱️ Aguardando 10 segundos
- 15 chamadas de API feitas até agora

## Resumo Final

Ao final da execução, você verá estatísticas completas:

```
📊 Estatísticas:
   ✅ Temporadas processadas: 9
   ✅ Eventos processados: 198
   ✅ Sessões carregadas: 990
   📡 API calls realizadas: 990
   ⏱️  Tempo total: 245.3 minutos
   ⏱️  Tempo de rate limiting: 165.0 minutos
   ⏱️  Tempo de processamento: 80.3 minutos
```

Isso permite você entender:
- Quanto tempo foi gasto esperando (rate limiting)
- Quanto tempo foi gasto processando dados
- Quantas chamadas de API foram feitas

## Troubleshooting

### "⚠️ any API: 500 calls/h"
- **Causa:** Você ultrapassou o limite
- **Solução:** Aumente o `RATE_LIMIT_DELAY` ou aguarde 1 hora

### "Muito lento!"
- **Causa:** Delay de 10s entre sessões
- **Solução:** Isso é intencional para respeitar o rate limit. Não reduza abaixo de 7 segundos!

### "Sessões sendo puladas"
- **Causa:** Já existem no banco de dados (cache SQLite)
- **Solução:** Isso é normal! O script pula sessões já carregadas

---

**Atualizado:** 2026-02-20
