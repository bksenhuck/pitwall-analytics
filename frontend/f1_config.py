"""
F1 Team & Driver Configuration
================================
Central registry for team colors, driver-team mappings,
car images, and logos.

How to update:
- Add a new season key to each team's `drivers` dict.
- Add a new year folder to each team's `cars` dict.
- Add alias strings to `aliases` whenever FastF1/SQLite
  reports a team under a different name.
"""
from typing import Optional

# ── Fallback ─────────────────────────────────────────────────────────────────
_FALLBACK_COLOR = "#6B7280"   # --muted gray
_FALLBACK_TEXT  = "#FFFFFF"

# ── Team registry ─────────────────────────────────────────────────────────────
# Key  : lowercase internal slug (used in code, never shown to user)
# color: primary hex used in charts/UI
# text_color: contrasting label color on colored backgrounds
# aliases: all name variants returned by FastF1 / stored in SQLite
# cars  : {year: Dash asset URL}  (/assets/... paths served by Dash)
# logos : {year: Dash asset URL}  — populate as files are added
# drivers: {year: [3-letter driver codes]}

TEAM_CONFIG: dict = {

    "ferrari": {
        "display": "Ferrari",
        "color": "#E8002D",
        "text_color": "#FFFFFF",
        "aliases": [
            "Ferrari", "Scuderia Ferrari", "Scuderia Ferrari HP",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/ferrari.png",
        },
        "logos": {},
        "drivers": {
            2026: ["LEC", "HAM"],
            2025: ["LEC", "HAM"],
            2024: ["LEC", "SAI"],
            2023: ["LEC", "SAI"],
        },
    },

    "redbull": {
        "display": "Red Bull",
        "color": "#3671C6",
        "text_color": "#FFFFFF",
        "aliases": [
            "Red Bull Racing", "Red Bull", "Oracle Red Bull Racing",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/redbull.png",
        },
        "logos": {},
        "drivers": {
            2026: ["VER", "LAW"],
            2025: ["VER", "LAW"],
            2024: ["VER", "PER"],
            2023: ["VER", "PER"],
        },
    },

    "mclaren": {
        "display": "McLaren",
        "color": "#FF8000",
        "text_color": "#FFFFFF",
        "aliases": [
            "McLaren", "McLaren F1 Team",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/mclaren.png",
        },
        "logos": {},
        "drivers": {
            2026: ["NOR", "PIA"],
            2025: ["NOR", "PIA"],
            2024: ["NOR", "PIA"],
            2023: ["NOR", "PIA"],
        },
    },

    "mercedes": {
        "display": "Mercedes",
        "color": "#00D2BE",
        "text_color": "#000000",
        "aliases": [
            "Mercedes", "Mercedes-AMG Petronas F1 Team",
            "Mercedes AMG Petronas",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/mercedes.png",
        },
        "logos": {},
        "drivers": {
            2026: ["RUS", "ANT"],
            2025: ["RUS", "ANT"],
            2024: ["HAM", "RUS"],
            2023: ["HAM", "RUS"],
        },
    },

    "aston_martin": {
        "display": "Aston Martin",
        "color": "#358C75",
        "text_color": "#FFFFFF",
        "aliases": [
            "Aston Martin", "Aston Martin F1 Team",
            "Aston Martin Aramco", "Aston Martin Aramco F1 Team",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/aston_martin.png",
        },
        "logos": {},
        "drivers": {
            2026: ["ALO", "STR"],
            2025: ["ALO", "STR"],
            2024: ["ALO", "STR"],
            2023: ["ALO", "STR"],
        },
    },

    "alpine": {
        "display": "Alpine",
        "color": "#0090FF",
        "text_color": "#FFFFFF",
        "aliases": [
            "Alpine", "BWT Alpine F1 Team", "Alpine F1 Team",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/alpine.png",
        },
        "logos": {},
        "drivers": {
            2026: ["GAS", "COL"],
            2025: ["GAS", "DOO"],
            2024: ["GAS", "OCO"],
            2023: ["GAS", "OCO"],
        },
    },

    "williams": {
        "display": "Williams",
        "color": "#005AFF",
        "text_color": "#FFFFFF",
        "aliases": [
            "Williams", "Williams Racing",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/williams.png",
        },
        "logos": {},
        "drivers": {
            2026: ["SAI", "ALB"],
            2025: ["SAI", "ALB"],
            2024: ["ALB", "SAR"],
            2023: ["ALB", "SAR"],
        },
    },

    "racing_bulls": {
        "display": "Racing Bulls",
        "color": "#4E5F9E",
        "text_color": "#FFFFFF",
        "aliases": [
            "RB", "Racing Bulls", "Visa Cash App RB Formula One Team",
            "AlphaTauri", "Scuderia AlphaTauri",
            "Scuderia AlphaTauri Honda",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/racing_bulls.png",
        },
        "logos": {},
        "drivers": {
            2026: ["TSU", "HAD"],
            2025: ["TSU", "HAD"],
            2024: ["TSU", "RIC"],
            2023: ["TSU", "DEV"],
        },
    },

    "haas": {
        "display": "Haas",
        "color": "#B6BABD",
        "text_color": "#000000",
        "aliases": [
            "Haas", "Haas F1 Team", "MoneyGram Haas F1 Team",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/haas.png",
        },
        "logos": {},
        "drivers": {
            2026: ["OCO", "BEA"],
            2025: ["OCO", "BEA"],
            2024: ["HUL", "MAG"],
            2023: ["HUL", "MAG"],
        },
    },

    "audi": {
        "display": "Audi",
        "color": "#636363",
        "text_color": "#FFFFFF",
        "aliases": [
            "Audi", "Stake F1 Team Kick Sauber",
            "Kick Sauber", "Sauber",
            "Alfa Romeo", "Alfa Romeo Racing",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/audi.png",
        },
        "logos": {},
        "drivers": {
            2026: ["HUL", "BOR"],
            2025: ["HUL", "BOR"],
            2024: ["ZHO", "BOT"],
            2023: ["ZHO", "BOT"],
        },
    },

    "cadillac": {
        "display": "Cadillac",
        "color": "#CC0033",
        "text_color": "#FFFFFF",
        "aliases": [
            "Cadillac", "Andretti Cadillac",
            "Andretti Global",
        ],
        "cars": {
            2026: "/assets/static/images/2026/cars_drawing/cadillac.png",
        },
        "logos": {},
        "drivers": {
            # 2026 lineup TBD
            2026: [],
        },
    },
}


# ── Internal lookup indexes (built once at import time) ───────────────────────

# alias (lowercase) → slug
_ALIAS_INDEX = {}
# (year, driver_code_uppercase) → slug
_DRIVER_INDEX = {}
# all indexed years, sorted descending (for fallback search)
_INDEXED_YEARS = []

for _slug, _cfg in TEAM_CONFIG.items():
    for _alias in _cfg["aliases"]:
        _ALIAS_INDEX[_alias.lower()] = _slug
    for _year, _drivers in _cfg["drivers"].items():
        for _drv in _drivers:
            _DRIVER_INDEX[(_year, _drv.upper())] = _slug

_INDEXED_YEARS = sorted({y for (y, _) in _DRIVER_INDEX}, reverse=True)


# ── Public helpers ────────────────────────────────────────────────────────────

def get_team_slug(name: str) -> Optional[str]:
    """
    Resolve a team name (any alias) to the canonical internal slug.
    Case-insensitive. Returns None if not found.
    """
    return _ALIAS_INDEX.get(name.strip().lower())


def get_team_config(name: str) -> Optional[dict]:
    """Return the full config dict for a team name / alias."""
    slug = get_team_slug(name)
    return TEAM_CONFIG.get(slug) if slug else None


def get_team_color(name: str) -> str:
    """
    Return the primary hex color for a team name.
    Falls back to _FALLBACK_COLOR if the team is not registered.
    """
    cfg = get_team_config(name)
    return cfg["color"] if cfg else _FALLBACK_COLOR


def get_driver_team_slug(season: Optional[int], driver_code: str) -> Optional[str]:
    """
    Return the team slug for a driver in a given season.
    Driver code is case-insensitive (e.g., 'ver', 'VER').

    If the exact season is not found, falls back to the closest indexed year
    so that drivers without a season mapping still get their team color.
    """
    code = driver_code.upper()
    if season is not None:
        slug = _DRIVER_INDEX.get((int(season), code))
        if slug is not None:
            return slug
    # Fallback: closest season in index, then all others
    search_order = (
        sorted(_INDEXED_YEARS, key=lambda y: abs(y - (season or 0)))
        if season
        else _INDEXED_YEARS
    )
    for yr in search_order:
        slug = _DRIVER_INDEX.get((yr, code))
        if slug is not None:
            return slug
    return None


def get_driver_color(season: Optional[int], driver_code: str) -> str:
    """
    Return the team color hex for a driver in a given season.
    Falls back to _FALLBACK_COLOR if driver is not registered in any season.
    """
    slug = get_driver_team_slug(season, driver_code)
    if slug is None:
        return _FALLBACK_COLOR
    return TEAM_CONFIG[slug]["color"]


def get_car_image(season: int, name: str) -> Optional[str]:
    """
    Return the Dash asset URL for a team's car image in a given season.
    `name` can be any alias.  Returns None if not available.
    """
    cfg = get_team_config(name)
    if cfg is None:
        return None
    return cfg["cars"].get(season)


def color_list_for_drivers(season: int, driver_codes: list) -> list:
    """
    Return a list of hex colors, one per driver, based on their team.
    Useful for direct assignment to Plotly marker_color.
    """
    return [get_driver_color(season, d) for d in driver_codes]


def color_list_for_teams(team_names: list) -> list:
    """
    Return a list of hex colors, one per team name / alias.
    """
    return [get_team_color(t) for t in team_names]


# ── Driver full names ──────────────────────────────────────────────────────────

DRIVER_FULL_NAMES: dict = {
    "ALB": "Alexander Albon",
    "ALO": "Fernando Alonso",
    "ANT": "Kimi Antonelli",
    "BEA": "Oliver Bearman",
    "BOT": "Valtteri Bottas",
    "BOR": "Gabriel Bortoleto",
    "COL": "Franco Colapinto",
    "DEV": "Nyck de Vries",
    "DOO": "Jack Doohan",
    "GAS": "Pierre Gasly",
    "HAD": "Isack Hadjar",
    "HAM": "Lewis Hamilton",
    "HUL": "Nico Hulkenberg",
    "IWA": "Ayumu Iwasa",
    "LAW": "Liam Lawson",
    "LEC": "Charles Leclerc",
    "MAG": "Kevin Magnussen",
    "MAR": "Mick Schumacher",
    "NOR": "Lando Norris",
    "OCO": "Esteban Ocon",
    "PER": "Sergio Perez",
    "PIA": "Oscar Piastri",
    "RIC": "Daniel Ricciardo",
    "RUS": "George Russell",
    "SAI": "Carlos Sainz",
    "SAR": "Logan Sargeant",
    "STR": "Lance Stroll",
    "TSU": "Yuki Tsunoda",
    "VER": "Max Verstappen",
    "ZHO": "Guanyu Zhou",
}


def get_driver_full_name(driver_code: str) -> str:
    """Return the full name for a driver code, or the code itself if unknown."""
    return DRIVER_FULL_NAMES.get(driver_code.upper(), driver_code)
