# 🛠️ Scripts - Ferramentas CLI

Esta pasta contém scripts administrativos e ferramentas de linha de comando para o Pitwall Analytics.

## 📄 Scripts Disponíveis

### 🚀 auto_populate_cache.py
**Script principal de população automática do cache.**

Descobre e carrega automaticamente TODOS os dados disponíveis do FastF1 para o SQLite.

**Uso:**
```bash
# Verificar o que está faltando (modo check)
python scripts/auto_populate_cache.py --season 2024 --check

# Carregar todos os dados de 2024
python scripts/auto_populate_cache.py --season 2024

# Carregar dados de 2023 em diante
python scripts/auto_populate_cache.py --from 2023

# Carregar tudo (2018-2026)
python scripts/auto_populate_cache.py
```

**Dados carregados por sessão:**
- 📊 Lap times (voltas, setores, pit stops)
- 🏁 Results (grid, classificação, pontos)
- 🌤️ Weather (temperatura, umidade, vento)
- 🚩 Race Control Messages (flags, penalidades)
- 📈 Session/Track Status (SC, VSC)
- 👥 Driver info (pilotos, equipes)

**Ver:** [../docs/AUTO_CACHE_GUIDE.md](../docs/AUTO_CACHE_GUIDE.md) para documentação completa.

---

### 🔧 populate_cache.py
**Script legado de população manual do cache.**

Ferramenta manual para popular o cache com chaves específicas.

**Uso:**
```bash
# Popular temporadas
python scripts/populate_cache.py f1_seasons

# Popular corridas de uma temporada
python scripts/populate_cache.py races_2024

# Popular uma corrida específica
python scripts/populate_cache.py race_2024_bahrain

# Listar todas as chaves no cache
python scripts/populate_cache.py --list

# Ver informações de uma chave
python scripts/populate_cache.py --info f1_seasons

# Deletar uma chave
python scripts/populate_cache.py --delete f1_seasons
```

**Quando usar:**
- Quando você precisa de controle granular sobre quais dados carregar
- Para recarregar uma sessão específica
- Para limpar/deletar dados específicos

---

### 📚 example_data_access.py
**Exemplos de como acessar dados do cache SQLite.**

Script demonstrativo que mostra como ler e trabalhar com os dados armazenados.

**Uso:**
```bash
python scripts/example_data_access.py
```

**O que faz:**
- Mostra como acessar dados de uma corrida específica
- Lista todos os dados em cache
- Demonstra como extrair informações (resultados, voltas, clima)
- Exemplos de queries e filtros

---

## 🎯 Qual Script Usar?

| Cenário | Script Recomendado |
|---------|-------------------|
| **Primeira vez carregando dados** | `auto_populate_cache.py --season 2024` |
| **Atualizar temporada atual** | `auto_populate_cache.py --season 2024` |
| **Carregar tudo de uma vez** | `auto_populate_cache.py --from 2018` |
| **Recarregar corrida específica** | `populate_cache.py race_2024_bahrain` |
| **Limpar dados antigos** | `populate_cache.py --delete <key>` |
| **Ver exemplos de código** | `example_data_access.py` |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────┐
│     Scripts CLI (este diretório)   │
│  - auto_populate_cache.py          │
│  - populate_cache.py               │
│  - example_data_access.py          │
└──────────────┬──────────────────────┘
               ↓
        ┌──────────────┐
        │   FastF1     │
        │   API        │
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │   SQLite     │
        │   Cache      │
        └──────┬───────┘
               ↓
┌──────────────────────────────────────┐
│   Backend API (Flask/FastAPI)       │
│   Serve data to frontend            │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│   Frontend (Dash)                   │
│   Data visualization                │
└──────────────────────────────────────┘
```

---

## 📖 Documentação Relacionada

- [../docs/AUTO_CACHE_GUIDE.md](../docs/AUTO_CACHE_GUIDE.md) - Guia completo do auto_populate_cache.py
- [../docs/MANUAL_CACHE_CONTROL.md](../docs/MANUAL_CACHE_CONTROL.md) - Guia do populate_cache.py
- [../README.md](../README.md) - Documentação principal do projeto
- [../docs/README.md](../docs/README.md) - Índice de toda documentação

---

## 🤝 Contribuindo

Ao adicionar novos scripts:

1. Mantenha a convenção de nomes: `verbo_substantivo.py`
2. Adicione docstring no topo explicando o propósito
3. Inclua `--help` para todos os argumentos CLI
4. Atualize este README.md
5. Adicione exemplos de uso

---

## 💡 Dicas

### Performance
- Use `--check` primeiro para ver quanto tempo vai levar
- Carregar uma temporada leva ~30-60 minutos
- O FastF1 tem rate limiting - seja paciente

### Troubleshooting
- **Erro de conexão**: Verifique sua internet (FastF1 precisa acessar API da F1)
- **Sessão não encontrada**: Normal! Nem todos os GPs têm todas as sessões
- **Cache muito grande**: Considere carregar apenas anos recentes

### Automação
```bash
# Exemplo de cron job (Linux/Mac)
0 2 * * 1 cd /path/to/project && python scripts/auto_populate_cache.py --season 2024

# Exemplo de Scheduled Task (Windows PowerShell)
$action = New-ScheduledTaskAction -Execute "python" -Argument "scripts/auto_populate_cache.py --season 2024" -WorkingDirectory "C:\path\to\project"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "PitwallCacheUpdate"
```
