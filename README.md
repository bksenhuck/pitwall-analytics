# Pitwall Analytics

A minimal motorsport data analytics dashboard built with Dash, FastF1 and Pandas.

## Overview

This project is a starter MVP to explore race sessions, lap times, positions and telemetry.

## 🚀 High-Performance Normalized Database

The project uses a **high-performance normalized SQLite cache** that:
- ✅ **10-100x faster** than JSON blobs
- ✅ **Only shows data that exists** in cache (no more failed loads!)
- ✅ **Structured tables** (seasons, events, sessions, laps, results, weather)
- ✅ **Backend reads from cache** (no more slow FastF1 calls)

**Quick Start:**
```bash
# 1. Populate cache
python scripts/populate_cache.py --season 2024

# 2. Start backend
python main.py

# 3. Frontend uses /api/data/available to discover data
```

**📚 Documentation:**
- 👉 **[CACHE_V2_SUMMARY.md](CACHE_V2_SUMMARY.md)** - Complete implementation summary
- 👉 **[docs/CACHE_V2_GUIDE.md](docs/CACHE_V2_GUIDE.md)** - Detailed guide
- 👉 **[frontend_integration_example.py](frontend_integration_example.py)** - Integration example

---

## Structure

- `app.py` - main Dash app and routing
- `pages/` - Dash multipage app pages (`home.py`, `analytics.py`)
- `data_loader.py` - wrappers for FastF1 session loading and caching
- `charts.py` - Plotly chart helper functions
- `assets/style.css` - minimal styling
- `requirements.txt` - dependencies

## Setup

1. Create and activate a Python virtualenv (optional but recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install requirements

```bash
pip install -r requirements.txt
```

3. Run the app

```bash
python app.py
```

4. Open http://127.0.0.1:8050 in your browser.

## Data Population (NEW! ⚡)

This project now includes an **automatic cache population system** that intelligently downloads ALL available F1 data from FastF1.

### Quick Start

```bash
# Check what data is available for 2024
python scripts/auto_populate_cache.py --season 2024 --check

# Download all 2024 data
python scripts/auto_populate_cache.py --season 2024

# Download everything from 2023 onwards
python scripts/auto_populate_cache.py --from 2023
```

### What gets loaded?

For each session (FP1, FP2, FP3, Qualifying, Sprint, Race):
- 📊 **Lap times** - complete timing, sectors, pit stops
- 🏁 **Results** - grid positions, final standings, points
- 🌤️ **Weather** - temperature, humidity, wind, rain
- 🚩 **Race Control** - flags, penalties, investigations
- 📈 **Session/Track Status** - Safety Car, VSC, track status
- 👥 **Driver info** - participants, teams, numbers

**See [docs/AUTO_CACHE_GUIDE.md](docs/AUTO_CACHE_GUIDE.md) for complete documentation.**

## Notes

- The system uses SQLite cache in `data/pitwall_cache.db` for fast access
- Backend serves data from cache; frontend never hits FastF1 directly
- First-time data load per season takes ~30-60 minutes

## 📚 Documentation

Complete documentation is available in the [`docs/`](docs/) folder:

- **[docs/AUTO_CACHE_GUIDE.md](docs/AUTO_CACHE_GUIDE.md)** - Complete cache auto-population guide ⭐
- **[docs/MANUAL_CACHE_CONTROL.md](docs/MANUAL_CACHE_CONTROL.md)** - Manual cache control
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- **[docs/DEPLOY.md](docs/DEPLOY.md)** - Deployment guide
- **[scripts/README.md](scripts/README.md)** - CLI tools documentation

See [docs/README.md](docs/README.md) for the complete documentation index.

## Professional project structure (recommended)

To make this project more production-ready consider restructuring into a package layout and adding tests and CI:

Recommended layout:

- pitwall-analytics/
	- pyproject.toml
	- .gitignore
	- README.md
	- src/
		- pitwall_analytics/
			- __init__.py
			- app.py (or run.py)
			- data_loader.py
			- charts.py
			- pages/
				- __init__.py
				- home.py
				- analytics.py
			- assets/
	- tests/
	- requirements.txt

Why this helps:
- `src/` + package name reduces accidental imports from project root.
- `pyproject.toml` enables modern packaging and dependency metadata.
- `.gitignore` keeps environment and cache files out of git.
- Adding `tests/` makes it easy to add unit tests and CI pipelines.

If you want, I can refactor the current code into the `src/pitwall_analytics` package and wire up a small test and `Makefile`/`tasks` next.
