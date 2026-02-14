# Pitwall Analytics

A minimal motorsport data analytics dashboard built with Dash, FastF1 and Pandas.

## Overview

This project is a starter MVP to explore race sessions, lap times, positions and telemetry.

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

## Notes

- The app enables a FastF1 local cache at `.ff1cache` to speed up subsequent loads.
- The Analytics page uses FastF1 to load race sessions; the first load may take extra time.

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
