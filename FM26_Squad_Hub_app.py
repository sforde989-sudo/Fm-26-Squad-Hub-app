import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import base64
import re
from datetime import date


def hex_to_rgba(hex_color, alpha=0.2):
    """Convert '#RRGGBB' (optionally with extra alpha digits) to 'rgba(r,g,b,a)' for Plotly."""
    h = hex_color.lstrip("#")[:6]
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ════════════════════════════════════════════════════════════════
# FM "WHAT DOES GOOD LOOK LIKE" BENCHMARK LIBRARY
# Source: community FM24/26 percentile benchmark tables.
# Each metric: (good, ok, poor) — higher value = better in all cases here.
# Column names mapped to the scouting export's actual headers.
# ════════════════════════════════════════════════════════════════
FM_BENCHMARKS = {
    "Goalkeeper": {
        "applies_to": ["GK"],
        "metrics": {
            "Sv %":   (75, 65, 55),
            "xSv %":  (88, 78, 47),
            "xGP/90": (0.25, 0.0, -0.38),
            "Pas %":  (97, 78, 47),
        }
    },
    "Centre-Back — Stopper": {
        "applies_to": ["D (C)"],
        "metrics": {
            "Tck/90":        (2.38, 1.29, 0.80),
            "Hdr %":         (82,   72,   59),
            "Clr/90":        (1.10, 0.85, 0.44),
            "Int/90":        (3.18, 2.15, 1.36),
            "Shts Blckd/90": (0.72, 0.42, 0.19),
        }
    },
    "Centre-Back — Ball-Playing": {
        "applies_to": ["D (C)"],
        "metrics": {
            "Tck/90":        (2.36, 1.24, 0.88),
            "Clr/90":        (0.89, 0.64, 0.39),
            "Int/90":        (3.00, 2.33, 1.69),
            "Shts Blckd/90": (0.63, 0.34, 0.16),
            "Pr passes/90":  (6.90, 4.52, 3.17),
        }
    },
    "Full-Back": {
        "applies_to": ["D (R)","D (L)"],
        "metrics": {
            "Tck/90":        (3.66, 2.75, 1.44),
            "Int/90":        (3.31, 2.75, 2.00),
            "Pres C/90":     (3.50, 2.48, 1.35),
            "OP-Crs C/90":   (0.47, 0.14, 0.03),
            "Pr passes/90":  (8.59, 6.13, 4.14),
        }
    },
    "Wing-Back": {
        "applies_to": ["WB (R)","WB (L)","D (R)","D (L)"],
        "metrics": {
            "Tck/90":        (3.88, 2.89, 1.57),
            "Int/90":        (3.48, 2.78, 1.89),
            "Pres C/90":     (3.64, 2.79, 1.51),
            "OP-Crs C/90":   (0.71, 0.25, 0.04),
            "Drb/90":        (3.03, 1.69, 0.39),
        }
    },
    "Midfield — Destroyer": {
        "applies_to": ["DM","M (C)"],
        "metrics": {
            "Tck/90":    (3.01, 2.16, 1.17),
            "Int/90":    (2.75, 1.97, 1.32),
            "Blk/90":    (0.75, 0.41, 0.20),
            "Pres C/90": (3.81, 2.84, 1.13),
            "Pas %":     (94,   90,   86),
        }
    },
    "Midfield — Creator": {
        "applies_to": ["M (C)","DM","AM (C)"],
        "metrics": {
            "OP-KP/90":     (1.82, 1.23, 0.76),
            "Pr passes/90": (7.19, 4.86, 2.67),
            "xA/90":        (0.33, 0.19, 0.10),
            "Drb/90":       (2.50, 1.32, 0.43),
            "Pas %":        (91,   88,   82),
        }
    },
    "Attacking Midfielder": {
        "applies_to": ["AM (C)"],
        "metrics": {
            "OP-KP/90": (1.81, 1.27, 0.75),
            "xA/90":    (0.32, 0.21, 0.13),
            "Drb/90":   (3.70, 1.85, 0.89),
            "Pas %":    (88,   85,   82),
            "ShT/90":   (1.10, 0.71, 0.37),
        }
    },
    "Wide Attacker — Provider": {
        "applies_to": ["AM (R)","AM (L)","WB (R)","WB (L)"],
        "metrics": {
            "Drb/90":      (4.69, 2.40, 1.05),
            "OP-Crs C/90": (0.66, 0.33, 0.10),
            "Sprints/90":  (18.03, 14.19, 8.57),
            "OP-KP/90":    (1.94, 1.15, 0.59),
            "xA/90":       (0.36, 0.19, 0.10),
        }
    },
    "Wide Attacker — Striker": {
        "applies_to": ["AM (R)","AM (L)","ST (C)"],
        "metrics": {
            "Drb/90":      (4.60, 3.01, 1.50),
            "ShT/90":      (1.34, 0.82, 0.43),
            "Sprints/90":  (17.49, 14.17, 8.24),
            "NP-xG/90":    (0.44, 0.25, 0.15),
            "Conv %":      (28,   16,   7),
        }
    },
    "Striker — Provider": {
        "applies_to": ["ST (C)"],
        "metrics": {
            "Hdrs W/90": (3.98, 1.95, 0.67),
            "xA/90":     (0.25, 0.14, 0.08),
            "NP-xG/90":  (0.52, 0.30, 0.21),
            "ShT/90":    (1.51, 0.94, 0.64),
            "Conv %":    (30,   20,   13),
        }
    },
    "Striker — Goalscorer": {
        "applies_to": ["ST (C)"],
        "metrics": {
            "Hdrs W/90": (5.08, 2.76, 1.03),
            "Drb/90":    (3.05, 1.17, 0.69),
            "NP-xG/90":  (0.50, 0.35, 0.22),
            "ShT/90":    (1.57, 1.09, 0.73),
            "Conv %":    (30,   21,   15),
        }
    },
}


def benchmark_score(value, good, ok, poor):
    """
    Piecewise-linear score 0-100 based on Poor/OK/Good thresholds.
    Direction is inferred from the thresholds themselves: if good >= poor,
    higher raw values are better (the FM_BENCHMARKS default). If good < poor,
    lower raw values are better (e.g. Dribbled Past/90, Fouls/90) — this lets
    custom user-added metrics work in either direction without a separate flag.
    """
    if pd.isna(value):
        return None
    value, good, ok, poor = float(value), float(good), float(ok), float(poor)

    if good >= poor:
        # Higher is better
        if value >= good:
            return 100.0
        if value <= poor:
            return 0.0
        if value >= ok:
            return 50 + (value - ok) / (good - ok) * 50
        else:
            return (value - poor) / (ok - poor) * 50
    else:
        # Lower is better
        if value <= good:
            return 100.0
        if value >= poor:
            return 0.0
        if value <= ok:
            return 50 + (ok - value) / (ok - good) * 50
        else:
            return (poor - value) / (poor - ok) * 50


def benchmark_label(score):
    if score is None:
        return "—"
    if score >= 75:
        return "🟢 Good"
    elif score >= 40:
        return "🟡 OK"
    else:
        return "🔴 Poor"


# ════════════════════════════════════════════════════════════════
# LEAGUE STRENGTH WEIGHTS
# Multiplier applied to Data Score % to reflect league quality —
# a "Good" stat line in a weaker league doesn't translate 1:1
# to the same quality in a top-5 league. 1.00 = baseline (top 5).
# Values are approximate, based on general league strength consensus.
# ════════════════════════════════════════════════════════════════
LEAGUE_WEIGHTS = {
    # Tier 1 — real-world top flights, strength score 1.00
    "Premier League": 1.00, "LaLiga": 1.00, "Serie A": 1.00,
    "Bundesliga": 1.00, "Ligue 1": 1.00,
    # Tier 2
    "EFL Championship": 0.90, "Liga Portugal": 0.90,
    # Tier 3
    "Ekstraklasa": 0.80, "Süper Lig": 0.80,
    # Tier 4
    "Eredivisie": 0.70,
    # Tier 5
    "LaLiga 2": 0.60,
    # Tier 6
    "Super League": 0.50,
    # Tier 8
    "Ligue 2": 0.30,
    # Outside Top 40 — verified via league strength dataset
    "Pro League": 0.25, "Brasileiro Série A": 0.25, "SuperSport HNL": 0.25,
    "Serie BKT": 0.25, "J1-League": 0.25, "Liga BBVA MX": 0.25,
    "William Hill Premiership": 0.25, "Super liga": 0.25, "K League 1": 0.25,
    # Default for anything not listed
    "_default": 0.25,
}

# Each top division mapped to the country it should belong to.
# Used to sanity-check the export's Division field against Based In —
# FM scouting exports sometimes carry over a stale/incorrect Division
# for a player (e.g. an Armenian club showing "Bundesliga").
DIVISION_HOME_COUNTRY = {
    "Premier League": "England", "EFL Championship": "England",
    "LaLiga": "Spain", "LaLiga 2": "Spain",
    "Serie A": "Italy", "Serie BKT": "Italy",
    "Bundesliga": "Germany",
    "Ligue 1": "France", "Ligue 2": "France",
    "Liga Portugal": "Portugal",
    "Eredivisie": "Netherlands",
    "Süper Lig": "Türkiye",
    "Pro League": "Belgium",
    "Liga BBVA MX": "Mexico",
    "Brasileiro Série A": "Brazil",
    "Ekstraklasa": "Poland",
    "Super League": "Greece",
    "Super liga": "Serbia",
    "SuperSport HNL": "Croatia",
    "J1-League": "Japan",
    "K League 1": "South Korea",
    "William Hill Premiership": "Scotland",
}

# Fallback weight by country — used when Division/Based In mismatch
# is detected. Based on each country's top domestic league strength score.
COUNTRY_WEIGHTS = {
    "England": 1.00, "France": 1.00, "Germany": 1.00, "Italy": 1.00, "Spain": 1.00,
    "Portugal": 0.90,
    "Poland": 0.80, "Türkiye": 0.80,
    "Netherlands": 0.70,
    "Greece": 0.50,
    "Belgium": 0.25, "Brazil": 0.25, "Croatia": 0.25, "Japan": 0.25,
    "Mexico": 0.25, "Scotland": 0.25, "Serbia": 0.25, "South Korea": 0.25,
    "_default": 0.25,
}


def league_weight(division, based_in=None):
    """
    Returns a league strength weight 0-1.

    If `based_in` is provided and the division's expected home country
    doesn't match it, falls back to a country-based weight instead —
    catches cases where the scouting export's Division field is stale
    or mismatched (e.g. an Armenian club showing as 'Bundesliga').
    """
    if pd.isna(division):
        if based_in is not None and pd.notna(based_in):
            return COUNTRY_WEIGHTS.get(str(based_in).strip(), COUNTRY_WEIGHTS["_default"])
        return LEAGUE_WEIGHTS["_default"]

    division = str(division).strip()
    expected_country = DIVISION_HOME_COUNTRY.get(division)

    if expected_country and based_in is not None and pd.notna(based_in):
        if str(based_in).strip() != expected_country:
            # Mismatch detected — use country-based fallback instead
            return COUNTRY_WEIGHTS.get(str(based_in).strip(), COUNTRY_WEIGHTS["_default"])

    return LEAGUE_WEIGHTS.get(division, LEAGUE_WEIGHTS["_default"])


# ════════════════════════════════════════════════════════════════
# ROLE WEIGHTS & SCORING (module-level — shared by Squad Decisions,
# Scout Report, and the Unified Squad Score model)
# ════════════════════════════════════════════════════════════════
ROLE_WEIGHTS = {
    "Advanced Forward":        {"Goals": 0.30, "xG": 0.20, "Conv %": 0.20, "ShT/90": 0.15, "Drb/90": 0.15},
    "Pressing Forward":        {"Pres C/90": 0.35, "Sprints/90": 0.25, "Goals": 0.20, "Conv %": 0.10, "ShT/90": 0.10},
    "Deep Lying Playmaker":    {"Ps C/90": 0.35, "OP-KP/90": 0.30, "Ch C/90": 0.20, "Pres C/90": 0.10, "Tck/90": 0.05},
    "Ball Winning Midfielder": {"Tck/90": 0.30, "Int/90": 0.25, "Pres C/90": 0.25, "Sprints/90": 0.15, "Ps C/90": 0.05},
    "Box to Box Midfielder":   {"Ps C/90": 0.20, "Tck/90": 0.20, "Goals": 0.15, "Sprints/90": 0.20, "Pres C/90": 0.15, "OP-KP/90": 0.10},
    "Inverted Winger":         {"Drb/90": 0.25, "ShT/90": 0.20, "Goals": 0.20, "OP-KP/90": 0.20, "Sprints/90": 0.15},
    "Attacking Midfielder":    {"OP-KP/90": 0.30, "Ch C/90": 0.20, "Drb/90": 0.20, "ShT/90": 0.15, "Goals": 0.15},
    "Wing Back (Attack)":      {"Sprints/90": 0.25, "Ch C/90": 0.20, "OP-KP/90": 0.20, "Drb/90": 0.20, "Pres C/90": 0.15},
    "Full-Back":               {"Tck/90": 0.25, "Int/90": 0.20, "Pres C/90": 0.25, "Sprints/90": 0.15, "Ps C/90": 0.15},
    "Ball Playing Defender":   {"Ps C/90": 0.35, "Tck/90": 0.25, "Int/90": 0.20, "Hdrs W/90": 0.15, "Drb/90": 0.05},
    "No Nonsense CB":          {"Hdrs W/90": 0.35, "Tck/90": 0.30, "Int/90": 0.25, "Pres C/90": 0.10},
    "Sweeper Keeper":          {"Pas %": 0.40, "Sv %": 0.30, "xSv %": 0.20, "xGP/90": 0.10},
}

# Positional eligibility — prevents a striker being scored against a CB role
ROLE_POSITION_MAP = {
    "Advanced Forward":        ["ST (C)", "AM (C)", "AM (R)", "AM (L)"],
    "Pressing Forward":        ["ST (C)", "AM (C)", "AM (R)", "AM (L)"],
    "Deep Lying Playmaker":    ["DM", "M (C)", "AM (C)"],
    "Ball Winning Midfielder": ["DM", "M (C)"],
    "Box to Box Midfielder":   ["M (C)", "DM", "AM (C)"],
    "Inverted Winger":         ["AM (R)", "AM (L)", "M (C)", "ST (C)"],
    "Attacking Midfielder":    ["AM (C)"],
    "Wing Back (Attack)":      ["WB (R)", "WB (L)", "D (R)", "D (L)"],
    "Full-Back":               ["D (R)", "D (L)"],
    "Ball Playing Defender":   ["D (C)", "DM"],
    "No Nonsense CB":          ["D (C)"],
    "Sweeper Keeper":          ["GK"],
}


def score_role(row, weights, data):
    """Score a player's fit for a tactical role (0–100), relative to squad max."""
    total, weight_sum = 0, 0
    for col, w in weights.items():
        if col in data.columns:
            col_max = data[col].max()
            if pd.notna(row.get(col)) and col_max > 0:
                total += (float(row[col]) / col_max) * w * 100
                weight_sum += w
    return round(total / weight_sum, 1) if weight_sum > 0 else 0.0


def _assign_decision(age, rating, apps, squad_score, bench_score):
    """
    Elite-squad decision model.
    Threshold philosophy: an elite squad carries no passengers.
    Any player not contributing at a high level is a sell/replace candidate
    unless they are young enough to develop into one.
    """
    apps        = int(apps or 0)
    squad_score = float(squad_score or 50)
    bench       = float(bench_score) if pd.notna(bench_score) else 50.0

    if pd.isna(age) or pd.isna(rating):
        return "⚪ Review"

    age, rating = int(age), float(rating)

    # ── Elite prospects (≤20) — only keep if already performing ──────────
    if age <= 20:
        if apps >= 10 and rating >= 7.1:
            return "🌱 Develop"   # genuinely contributing youth
        if rating >= 6.8:
            return "🌱 Loan Out"  # needs minutes elsewhere
        return "🔴 Sell"          # too far from elite standard

    # ── Ageing players — elite squads don't carry sentiment ──────────────
    if age >= 33 and rating < 7.2:
        return "🔴 Release"
    if age >= 31 and (rating < 7.0 or bench < 50):
        return "🔴 Sell"
    if age >= 29 and rating < 6.8 and squad_score < 52:
        return "🔴 Sell / Replace"  # entering decline, below elite bar

    # ── Untouchable core ─────────────────────────────────────────────────
    if rating >= 7.5 and squad_score >= 72:
        return "✅ Keep — Core"     # elite performer, irreplaceable
    if rating >= 7.2 and squad_score >= 62:
        return "✅ Keep"            # strong contributor

    # ── Young upside (21-24): only if showing elite trajectory ───────────
    if age <= 24:
        if rating >= 7.0 or squad_score >= 60:
            return "🌱 Develop"
        if rating >= 6.7:
            return "🌱 Loan Out"
        return "🔴 Sell"            # not progressing fast enough

    # ── Mid-age rotation: tight bar — elite squads demand quality depth ──
    if rating >= 7.0 and apps >= 8:
        return "🔄 Rotate"          # valuable squad cover
    if rating >= 6.9 and squad_score >= 55:
        return "🔄 Rotate"

    # ── Below elite threshold ─────────────────────────────────────────────
    if rating >= 6.7 and apps >= 12:
        return "🔴 Sell / Replace"  # minutes earner but sub-elite quality
    return "🔴 Sell / Replace"


def _player_verdict(row):
    """
    Generate a detailed elite-squad write-up for a player.
    Returns a markdown string covering: the composite score breakdown driving
    the decision, what they bring, what holds them back, age-curve context,
    wage/value context where available, and a specific recommended action.
    """
    name       = row.get("Player", "This player")
    age        = row.get("Age", None)
    age_int    = int(age) if pd.notna(age) else None
    rating     = float(row.get("Rating", 0) or 0)
    apps       = int(row.get("Apps_numeric", 0) or 0)
    sq_score   = float(row.get("Squad Score", 50) or 50)
    bench      = row.get("Benchmark Score %", None)
    bench      = float(bench) if pd.notna(bench) else None
    role_fit   = float(row.get("Role Fit %", 50) or 50)
    best_role  = row.get("Best Fit Role", "their position")
    decision   = row.get("Decision", "⚪ Review")
    goals      = int(row.get("Goals", 0) or 0)
    assists    = int(row.get("Assists", 0) or 0)
    position   = row.get("Best Pos", "")
    wage_pw    = row.get("Wage (£/wk)", None)
    contract_alert = row.get("Contract Alert", False)
    expires_year   = row.get("Expires Year", None)

    lines = []

    # ── Score breakdown — show the actual maths behind the verdict ─────
    age_curve  = max(0.0, 100.0 - abs(27.0 - float(age_int)) * 3.5) if age_int is not None else None
    rating_norm = max(0.0, min(100.0, (rating - 6.0) / 2.0 * 100.0)) if rating else None
    apps_norm  = min(100.0, (apps / 30.0) * 100.0)
    b_display  = bench if bench is not None else 50.0

    breakdown_bits = []
    breakdown_bits.append(f"Benchmark {b_display:.0f}% (35% weight)")
    breakdown_bits.append(f"Role Fit {role_fit:.0f}% as {best_role} (25% weight)")
    if age_curve is not None:
        breakdown_bits.append(f"Age Curve {age_curve:.0f}% — age {age_int}, curve peaks at 27 (15% weight)")
    if rating_norm is not None:
        breakdown_bits.append(f"Rating {rating:.2f} → {rating_norm:.0f}% on the 6.0–8.0 scale (15% weight)")
    breakdown_bits.append(f"Appearances {apps}/30 → {apps_norm:.0f}% game-time contribution (10% weight)")
    lines.append(
        f"**Squad Score {sq_score:.0f}/100 — why:** " + "; ".join(breakdown_bits) + "."
    )

    # ── Strengths ──────────────────────────────────────────────────────
    strengths = []
    if rating >= 7.4:
        strengths.append(f"performing at an elite level (avg {rating:.2f})")
    elif rating >= 7.1:
        strengths.append(f"consistent high-level performer (avg {rating:.2f})")
    elif rating >= 6.9:
        strengths.append(f"solid contributor (avg {rating:.2f})")
    if apps >= 20:
        strengths.append(f"durability across {apps} appearances — trusted with regular minutes")
    if goals >= 10:
        strengths.append(f"prolific output ({goals} goals) for {position or 'their role'}")
    if assists >= 7:
        strengths.append(f"strong creative returns ({assists} assists)")
    if role_fit >= 70:
        strengths.append(f"excellent tactical fit as {best_role} ({role_fit:.0f}%) — the system suits their attributes")
    elif role_fit >= 55:
        strengths.append(f"good role alignment as {best_role} ({role_fit:.0f}%)")
    if bench is not None and bench >= 65:
        strengths.append(f"above the FM 'what good looks like' benchmark for {position} ({bench:.0f}%)")
    if age_curve is not None and age_curve >= 90:
        strengths.append(f"sitting right in the athletic prime window (age {age_int}, curve {age_curve:.0f}%)")

    # ── Weaknesses ─────────────────────────────────────────────────────
    concerns = []
    if rating < 6.9:
        concerns.append(f"rating ({rating:.2f}) falls short of elite squad standard (6.9+ baseline)")
    if apps < 8 and age_int is not None and age_int >= 22:
        concerns.append(f"only {apps} appearances this season — questions reliability, fitness or manager trust")
    if bench is not None and bench < 48:
        concerns.append(f"attribute benchmark ({bench:.0f}%) is below what elite squads require at {position}")
    elif bench is None:
        concerns.append("insufficient minutes played to generate a reliable benchmark reading yet")
    if role_fit < 50:
        concerns.append(f"poor tactical fit for the {best_role} role ({role_fit:.0f}%) — attributes don't map well to how they're being used")
    if age_int is not None and age_int >= 31 and rating < 7.2:
        concerns.append(f"at {age_int}, past peak (age curve {age_curve:.0f}%) and unlikely to improve — replacement planning should start now")
    if sq_score < 52:
        concerns.append(f"composite squad score ({sq_score:.0f}) sits below the elite threshold of 52")
    if pd.notna(wage_pw) and float(wage_pw or 0) > 0 and rating < 7.0 and float(wage_pw) > 30000:
        concerns.append(f"wage (£{float(wage_pw):,.0f} p/w) is hard to justify against a {rating:.2f} rating — poor value for money")
    if contract_alert:
        yr_txt = f" (expires {int(expires_year)})" if pd.notna(expires_year) else ""
        concerns.append(f"contract situation is time-sensitive{yr_txt} — resolve before it becomes a free-transfer risk")

    # ── Build the write-up ─────────────────────────────────────────────
    if strengths:
        lines.append("**Strengths:** " + "; ".join(strengths) + ".")
    if concerns:
        lines.append("**Concerns:** " + "; ".join(concerns) + ".")

    # ── Decision rationale — specific, tied to the numbers above ───────
    if "Keep — Core" in decision:
        lines.append(
            f"**Verdict — Keep (Core):** {name}'s {sq_score:.0f} squad score, {role_fit:.0f}% role fit as {best_role} "
            f"and {rating:.2f} rating put them clearly above the core-squad line. Protect with a long-term contract, "
            f"build the system around their strengths, and prioritise them for match minutes over rotation options."
        )
    elif "Keep" in decision:
        lines.append(
            f"**Verdict — Keep:** A reliable {sq_score:.0f}-score contributor. Not yet undroppable, but the underlying "
            f"numbers (rating {rating:.2f}, benchmark {b_display:.0f}%) support a regular squad spot. Track the next "
            f"5–10 appearances — sustained improvement in role fit or benchmark score should trigger a review toward Core status."
        )
    elif "Rotate" in decision:
        lines.append(
            f"**Verdict — Rotate:** Useful depth (score {sq_score:.0f}) but not elite-grade — either the benchmark "
            f"({b_display:.0f}%), role fit ({role_fit:.0f}%) or minutes played hold them back from a starting claim. "
            f"Keep as squad depth only if no signable upgrade exists in the transfer market; if one appears at a similar "
            f"wage, this is the first slot to upgrade."
        )
    elif "Develop" in decision:
        lines.append(
            f"**Verdict — Develop:** Age curve ({age_curve:.0f}% at age {age_int}) justifies patience even though the "
            f"current squad score ({sq_score:.0f}) is modest. Set concrete milestones — e.g. benchmark above 55% or "
            f"role fit above 60% within one season — and reassess at that checkpoint rather than leaving it open-ended."
        )
    elif "Loan Out" in decision:
        lines.append(
            f"**Verdict — Loan Out:** Not ready for elite minutes here (role fit {role_fit:.0f}%, apps {apps}). "
            f"A loan to a side where they'll start regularly develops the attributes driving the low benchmark score "
            f"faster than sitting on this bench would. Attach a recall clause to protect the asset."
        )
    elif "Release" in decision:
        lines.append(
            f"**Verdict — Release:** Squad score ({sq_score:.0f}) and role fit ({role_fit:.0f}%) no longer justify a "
            f"squad spot, and age ({age_int}) limits resale value. Contract termination is the cleanest option — "
            f"the wage freed up funds a more useful signing."
        )
    else:
        lines.append(
            f"**Verdict — Sell:** The numbers (score {sq_score:.0f}, benchmark {b_display:.0f}%, role fit {role_fit:.0f}%) "
            f"sit below elite standard for {position or 'this position'}. Sell while resale value remains "
            f"(age {age_int if age_int is not None else '?'}) and reinvest in a profile that clears the benchmark for the role."
        )

    return "\n\n".join(lines)


def compute_squad_scores(df, played_df):
    """
    Unified player scoring model.

    Returns a DataFrame with columns:
        Player | Benchmark Score % | Role Fit % | Best Fit Role | Squad Score | Decision

    Composite Squad Score weights:
        35% Benchmark Score %  — FM 'What Does Good Look Like' thresholds for the position
        25% Role Fit %         — best positional role suitability score
        15% Age Curve          — peaks at 27, tapers for very young/old
        15% Rating (normalised)— FM average match rating mapped 6.0–8.0 → 0–100
        10% Apps               — minutes/game-time contribution
    """
    results = []

    for _, row in df.iterrows():
        player   = row.get("Player", "—")
        age      = row.get("Age")
        rating   = row.get("Rating")
        apps     = row.get("Apps_numeric", 0)
        best_pos = row.get("Best Pos")

        # ── 1. Benchmark Score % ────────────────────────────────────
        bench_score = None
        p_played = played_df[played_df["Player"] == player] if "Player" in played_df.columns else pd.DataFrame()
        if not p_played.empty and pd.notna(best_pos):
            p_played_row = p_played.iloc[0]
            applicable = [
                role for role, cfg in FM_BENCHMARKS.items()
                if best_pos in cfg["applies_to"]
            ]
            role_bench_scores = []
            for role in applicable:
                m_scores = []
                for m, (good, ok, poor) in FM_BENCHMARKS[role]["metrics"].items():
                    if m in played_df.columns and pd.notna(p_played_row.get(m)):
                        sc = benchmark_score(float(p_played_row[m]), good, ok, poor)
                        if sc is not None:
                            m_scores.append(sc)
                if m_scores:
                    role_bench_scores.append(sum(m_scores) / len(m_scores))
            if role_bench_scores:
                bench_score = round(sum(role_bench_scores) / len(role_bench_scores), 1)

        # ── 2. Role Fit % (positional eligibility aware) ────────────
        best_fit_score = 0.0
        best_fit_name  = "—"
        if not p_played.empty:
            p_played_row = p_played.iloc[0]
            # Wide position field for fallback matching
            pos_wide = str(row.get("Position", ""))
            pos_list = [p.strip() for p in re.split(r"[,/]", pos_wide) if p.strip()]

            for role_name, weights in ROLE_WEIGHTS.items():
                eligible_pos = ROLE_POSITION_MAP.get(role_name, [])
                is_eligible = (
                    (pd.notna(best_pos) and best_pos in eligible_pos)
                    or any(p in eligible_pos for p in pos_list)
                )
                if not is_eligible:
                    continue
                rs = score_role(p_played_row, weights, played_df)
                if rs > best_fit_score:
                    best_fit_score = rs
                    best_fit_name  = role_name

            # Fallback: if nothing matched (unusual position), score all roles
            if best_fit_score == 0.0:
                for role_name, weights in ROLE_WEIGHTS.items():
                    rs = score_role(p_played_row, weights, played_df)
                    if rs > best_fit_score:
                        best_fit_score = rs
                        best_fit_name  = role_name

        # ── 3. Component sub-scores ──────────────────────────────────
        # Age curve: peaks at 27, useful from 23-30, tapers outside
        age_curve = 100.0
        if pd.notna(age):
            age_curve = max(0.0, 100.0 - abs(27.0 - float(age)) * 3.5)

        # Rating normalised on a 6.0–8.0 FM scale → 0–100
        rating_norm = 50.0
        if pd.notna(rating):
            rating_norm = max(0.0, min(100.0, (float(rating) - 6.0) / 2.0 * 100.0))

        # Appearance contribution (30 apps ≈ full season)
        apps_norm = min(100.0, (float(apps or 0) / 30.0) * 100.0)

        # ── 4. Composite Squad Score ─────────────────────────────────
        b = bench_score if bench_score is not None else 50.0
        squad_score = round(
            b               * 0.35 +
            best_fit_score  * 0.25 +
            age_curve       * 0.15 +
            rating_norm     * 0.15 +
            apps_norm       * 0.10,
            1
        )

        # ── 5. Decision label ─────────────────────────────────────────
        decision = _assign_decision(age, rating, apps, squad_score, bench_score)

        results.append({
            "Player":            player,
            "Benchmark Score %": bench_score,
            "Role Fit %":        round(best_fit_score, 1),
            "Best Fit Role":     best_fit_name,
            "Squad Score":       squad_score,
            "Decision":          decision,
        })

    return pd.DataFrame(results)


st.set_page_config(page_title="FM26 Advanced Squad Hub", page_icon="📊", layout="wide")


# ── Club Badge Lookup ────────────────────────────────────────────────────────
import base64 as _b64
import os as _os

def _is_light_hex(hex_color):
    """True if a hex color is light enough to need dark text/accents on it."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.6
    except Exception:
        return False


def _darken_hex(hex_color, factor=0.12):
    """Return a very dark blend of a hex color, used for background gradients."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#0a0a0a"


def _make_theme(primary, secondary, chart_scale="Viridis"):
    """Build a full CLUB_THEMES entry from just a primary/secondary club color pair."""
    dark_bg = _darken_hex(primary)
    return {
        "primary": primary,
        "secondary": secondary,
        "text": "#000000" if _is_light_hex(primary) else "#ffffff",
        "chart_scale": chart_scale,
        "bg_gradient": f"linear-gradient(160deg, {dark_bg} 0%, #0d1117 40%, {dark_bg} 100%)",
        "sidebar_bg": dark_bg,
    }


CLUB_BADGE_MAP = {
    # Premier League
    "Chelsea (Royal Blue & White)":       "premier-league/chelsea.png",
    "Liverpool (Red & Gold)":             "premier-league/liverpool.png",
    "Arsenal":                            "premier-league/arsenal.png",
    "Aston Villa":                        "premier-league/aston-villa.png",
    "Brentford":                          "premier-league/brentford.png",
    "Brighton":                           "premier-league/brighton.png",
    "Burnley":                            "premier-league/burnley.png",
    "Crystal Palace":                     "premier-league/crystal-palace.png",
    "Everton":                            "premier-league/everton.png",
    "Leeds United":                       "premier-league/leeds-united.png",
    "Leicester City":                     "premier-league/leicester-city.png",
    "Manchester City":                    "premier-league/manchester-city.png",
    "Manchester United":                  "premier-league/manchester-united.png",
    "Newcastle United":                   "premier-league/newcastle-united.png",
    "Norwich City":                       "premier-league/norwich-city.png",
    "Southampton":                        "premier-league/southampton.png",
    "Tottenham Hotspur":                  "premier-league/tottenham-hotspur.png",
    "Watford":                            "premier-league/watford.png",
    "West Ham United":                    "premier-league/west-ham-united.png",
    "Wolves":                             "premier-league/wolves.png",
    # Bundesliga
    "Bayern Munich":                      "bundesliga/bayern.png",
    "Borussia Dortmund":                  "bundesliga/dortmund.png",
    "RB Leipzig":                         "bundesliga/redbull-leipzig.png",
    "Bayer Leverkusen":                   "bundesliga/leverkusen.png",
    "Schalke":                            "bundesliga/schalke.png",
    "Wolfsburg":                          "bundesliga/wolfsburg.png",
    "Freiburg":                           "bundesliga/freiburg.png",
    "Augsburg":                           "bundesliga/augsburg.png",
    "Hoffenheim":                         "bundesliga/hoffenheim.png",
    "Frankfurt":                          "bundesliga/frankfurt.png",
    "Hertha Berlin":                      "bundesliga/hertha-bsc-berlin.png",
    "Mainz":                              "bundesliga/mainz.png",
    "Borussia Monchengladbach":           "bundesliga/moenchengladbach.png",
    "Stuttgart":                          "bundesliga/stuttgart.png",
    "Hamburg":                            "bundesliga/hamburg.png",
    "Hannover":                           "bundesliga/hannover.png",
    "Nuremberg":                          "bundesliga/nuremberg.png",
    "Bremen":                             "bundesliga/bremen.png",
    "Furth":                              "bundesliga/furth.png",
    "Dusseldorf":                         "bundesliga/dusseldorf.png",
    # La Liga
    "Real Madrid":                        "la-liga/real-madrid.png",
    "Barcelona":                          "la-liga/barcelona.png",
    "Atletico Madrid":                    "la-liga/atletico-madrid.png",
    "Sevilla":                            "la-liga/sevilla.png",
    "Real Betis":                         "la-liga/real-betis.png",
    "Real Sociedad":                      "la-liga/real-sociedad.png",
    "Villarreal":                         "la-liga/villarreal.png",
    "Athletic Bilbao":                    "la-liga/athletic.png",
    "Valencia":                           "la-liga/valencia.png",
    "Osasuna":                            "la-liga/osasuna.png",
    "Espanyol":                           "la-liga/espanyol.png",
    "Getafe":                             "la-liga/getafe.png",
    "Cadiz":                              "la-liga/cadiz.png",
    "Mallorca":                           "la-liga/mallorca.png",
    "Rayo Vallecano":                     "la-liga/rayo-vallecano.png",
    "Granada":                            "la-liga/granada.png",
    "Celta Vigo":                         "la-liga/celta.png",
    "Levante":                            "la-liga/levante.png",
    "Elche":                              "la-liga/elche.png",
    "Deportivo Alaves":                   "la-liga/deportivo-alavez.png",
    # Serie A
    "Juventus":                           "serie-a/juventus.png",
    "Inter Milan":                        "serie-a/inter.png",
    "AC Milan":                           "serie-a/ac-milan.png",
    "Napoli":                             "serie-a/napoli.png",
    "Roma":                               "serie-a/roma.png",
    "Lazio":                              "serie-a/lazio.png",
    "Atalanta":                           "serie-a/atalanta.png",
    "Fiorentina":                         "serie-a/fiorentina.png",
    "Bologna":                            "serie-a/bologna.png",
    "Sampdoria":                          "serie-a/sampdoria.png",
    "Torino":                             "serie-a/torino.png",
    "Udinese":                            "serie-a/udinese.png",
    "Sassuolo":                           "serie-a/sassuolo.png",
    "Empoli":                             "serie-a/empoli.png",
    "Genoa":                              "serie-a/genoa.png",
    "Cagliari":                           "serie-a/cagliari.png",
    "Salernitana":                        "serie-a/salernitana.png",
    "Spezia":                             "serie-a/spezia.png",
    "Hellas Verona":                      "serie-a/hellas-verona.png",
    "Venezia":                            "serie-a/venezia.png",
    # Ligue 1
    "Paris Saint-Germain":               "french-ligue1/paris-saint-germain.png",
    "Olympique Lyonnais":                "french-ligue1/olympique-lyonnais.png",
    "Olympique Marseille":               "french-ligue1/olympique-de-marseille.png",
    "Montpellier (Orange & Sky Blue)":  "french-ligue1/montpellier-herault.png",
    "Monaco":                            "french-ligue1/as-monaco.png",
    "Lille":                             "french-ligue1/losc-lille.png",
    "Rennes":                            "french-ligue1/stade-rennais-fc.png",
    "Nice":                              "french-ligue1/ogc-nice.png",
    "Strasbourg":                        "french-ligue1/rc-strasbourg-alsace.png",
    "Lens":                              "french-ligue1/rc-lens.png",
    "Nantes":                            "french-ligue1/fc-nantes.png",
    "Angers":                            "french-ligue1/angers-sco.png",
    "Bordeaux":                          "french-ligue1/fc-girondins-de-bordeaux.png",
    "Brest":                             "french-ligue1/stade-brestois-29.png",
    "Reims":                             "french-ligue1/stade-de-reims.png",
    "Metz":                              "french-ligue1/fc-metz.png",
    "Lorient":                           "french-ligue1/fc-lorient.png",
    "Troyes":                            "french-ligue1/estac-troyes.png",
    "Clermont":                          "french-ligue1/clermont-foot-63.png",
    "Saint-Etienne":                     "french-ligue1/as-saint-etienne.png",
    # Aris (existing theme — no badge in pack)
    "Aris Thessaloniki (Yellow & Black)": None,
    "Default Football Manager Green":     None,
}

def get_club_badge_b64(theme_name):
    """Return base64-encoded PNG for the theme, searching next to the script."""
    rel = CLUB_BADGE_MAP.get(theme_name)
    if not rel:
        return None
    script_dir = _os.path.dirname(_os.path.abspath(__file__))
    # Expected: badges/ folder sits next to the .py file
    candidates = [
        _os.path.join(script_dir, "badges", "top-5-football-leagues", rel),
        _os.path.join(script_dir, "badges", rel),
        _os.path.join("badges", "top-5-football-leagues", rel),
        _os.path.join("badges", rel),
    ]
    for path in candidates:
        if _os.path.exists(path):
            with open(path, "rb") as _f:
                return _b64.b64encode(_f.read()).decode()
    return None

CLUB_THEMES = {
    "Default Football Manager Green": {
        "primary": "#00ff87", "secondary": "#1f2937", "text": "#ffffff",
        "chart_scale": "Viridis",
        "bg_gradient": "linear-gradient(160deg, #0a1a0f 0%, #0d1117 40%, #0a1a0f 100%)",
        "sidebar_bg": "#0a1a0f",
    },
    "Chelsea (Royal Blue & White)": {
        "primary": "#034694", "secondary": "#ee242c", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #010d20 0%, #0d1117 40%, #010d20 100%)",
        "sidebar_bg": "#010d20",
    },
    "Aris Thessaloniki (Yellow & Black)": {
        "primary": "#FEE100", "secondary": "#000000", "text": "#000000",
        "chart_scale": "Solar",
        "bg_gradient": "linear-gradient(160deg, #1a1500 0%, #0d1117 40%, #1a1500 100%)",
        "sidebar_bg": "#1a1500",
    },
    "Liverpool (Red & Gold)": {
        "primary": "#C8102E", "secondary": "#F6EB61", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1a0005 0%, #0d1117 40%, #1a0005 100%)",
        "sidebar_bg": "#1a0005",
    },
    "Bayern Munich": {
        "primary": "#DC052D", "secondary": "#0066B2", "text": "#ffffff",
        "chart_scale": "Electric",
        "bg_gradient": "linear-gradient(160deg, #1a0008 0%, #0d1117 40%, #00081a 100%)",
        "sidebar_bg": "#1a0008",
    },
    "Real Madrid": {
        "primary": "#FEBE10", "secondary": "#112546", "text": "#ffffff",
        "chart_scale": "YlOrRd",
        "bg_gradient": "linear-gradient(160deg, #1a1400 0%, #0d1117 40%, #060d1a 100%)",
        "sidebar_bg": "#060d1a",
    },
    "Montpellier (Orange & Sky Blue)": {
        "primary": "#FF7900", "secondary": "#0099CC", "text": "#ffffff",
        "chart_scale": "Oranges",
        "bg_gradient": "linear-gradient(160deg, #1a0d00 0%, #0d1117 40%, #001a26 100%)",
        "sidebar_bg": "#1a0d00",
    },
}

_AUTO_CLUB_THEMES = {
    "Arsenal": {
        "primary": "#EF0107", "secondary": "#063672", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1c0000 0%, #0d1117 40%, #1c0000 100%)",
        "sidebar_bg": "#1c0000",
    },
    "Aston Villa": {
        "primary": "#670E36", "secondary": "#95BFE5", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #0c0106 0%, #0d1117 40%, #0c0106 100%)",
        "sidebar_bg": "#0c0106",
    },
    "Brentford": {
        "primary": "#E30613", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0002 0%, #0d1117 40%, #1b0002 100%)",
        "sidebar_bg": "#1b0002",
    },
    "Brighton": {
        "primary": "#0057B8", "secondary": "#FFCD00", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000a16 0%, #0d1117 40%, #000a16 100%)",
        "sidebar_bg": "#000a16",
    },
    "Burnley": {
        "primary": "#6C1D45", "secondary": "#99D6EA", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #0c0308 0%, #0d1117 40%, #0c0308 100%)",
        "sidebar_bg": "#0c0308",
    },
    "Crystal Palace": {
        "primary": "#1B458F", "secondary": "#C4122E", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #030811 0%, #0d1117 40%, #030811 100%)",
        "sidebar_bg": "#030811",
    },
    "Everton": {
        "primary": "#003399", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000612 0%, #0d1117 40%, #000612 100%)",
        "sidebar_bg": "#000612",
    },
    "Leeds United": {
        "primary": "#1D428A", "secondary": "#FFCD00", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #030710 0%, #0d1117 40%, #030710 100%)",
        "sidebar_bg": "#030710",
    },
    "Leicester City": {
        "primary": "#003090", "secondary": "#FDBE11", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000511 0%, #0d1117 40%, #000511 100%)",
        "sidebar_bg": "#000511",
    },
    "Manchester City": {
        "primary": "#6CABDD", "secondary": "#1C2C5B", "text": "#000000",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #0c141a 0%, #0d1117 40%, #0c141a 100%)",
        "sidebar_bg": "#0c141a",
    },
    "Manchester United": {
        "primary": "#DA291C", "secondary": "#FBE122", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1a0403 0%, #0d1117 40%, #1a0403 100%)",
        "sidebar_bg": "#1a0403",
    },
    "Newcastle United": {
        "primary": "#3C3C3C", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greys",
        "bg_gradient": "linear-gradient(160deg, #070707 0%, #0d1117 40%, #070707 100%)",
        "sidebar_bg": "#070707",
    },
    "Norwich City": {
        "primary": "#FFF200", "secondary": "#00A650", "text": "#000000",
        "chart_scale": "YlGn",
        "bg_gradient": "linear-gradient(160deg, #1e1d00 0%, #0d1117 40%, #1e1d00 100%)",
        "sidebar_bg": "#1e1d00",
    },
    "Southampton": {
        "primary": "#D71920", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #190303 0%, #0d1117 40%, #190303 100%)",
        "sidebar_bg": "#190303",
    },
    "Tottenham Hotspur": {
        "primary": "#132257", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #02040a 0%, #0d1117 40%, #02040a 100%)",
        "sidebar_bg": "#02040a",
    },
    "Watford": {
        "primary": "#FBEE23", "secondary": "#ED2127", "text": "#000000",
        "chart_scale": "YlOrRd",
        "bg_gradient": "linear-gradient(160deg, #1e1c04 0%, #0d1117 40%, #1e1c04 100%)",
        "sidebar_bg": "#1e1c04",
    },
    "West Ham United": {
        "primary": "#7A263A", "secondary": "#1BB1E7", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #0e0406 0%, #0d1117 40%, #0e0406 100%)",
        "sidebar_bg": "#0e0406",
    },
    "Wolves": {
        "primary": "#FDB913", "secondary": "#231F20", "text": "#000000",
        "chart_scale": "YlOrBr",
        "bg_gradient": "linear-gradient(160deg, #1e1602 0%, #0d1117 40%, #1e1602 100%)",
        "sidebar_bg": "#1e1602",
    },
    "Borussia Dortmund": {
        "primary": "#FDE100", "secondary": "#000000", "text": "#000000",
        "chart_scale": "YlOrRd",
        "bg_gradient": "linear-gradient(160deg, #1e1b00 0%, #0d1117 40%, #1e1b00 100%)",
        "sidebar_bg": "#1e1b00",
    },
    "RB Leipzig": {
        "primary": "#DD0741", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1a0007 0%, #0d1117 40%, #1a0007 100%)",
        "sidebar_bg": "#1a0007",
    },
    "Bayer Leverkusen": {
        "primary": "#E32221", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0403 0%, #0d1117 40%, #1b0403 100%)",
        "sidebar_bg": "#1b0403",
    },
    "Schalke": {
        "primary": "#004D9D", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000912 0%, #0d1117 40%, #000912 100%)",
        "sidebar_bg": "#000912",
    },
    "Wolfsburg": {
        "primary": "#65B32E", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #0c1505 0%, #0d1117 40%, #0c1505 100%)",
        "sidebar_bg": "#0c1505",
    },
    "Freiburg": {
        "primary": "#000000", "secondary": "#E2001A", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #000000 0%, #0d1117 40%, #000000 100%)",
        "sidebar_bg": "#000000",
    },
    "Augsburg": {
        "primary": "#BA3733", "secondary": "#046A38", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #160606 0%, #0d1117 40%, #160606 100%)",
        "sidebar_bg": "#160606",
    },
    "Hoffenheim": {
        "primary": "#1C63B7", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #030b15 0%, #0d1117 40%, #030b15 100%)",
        "sidebar_bg": "#030b15",
    },
    "Frankfurt": {
        "primary": "#E1000F", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0001 0%, #0d1117 40%, #1b0001 100%)",
        "sidebar_bg": "#1b0001",
    },
    "Hertha Berlin": {
        "primary": "#005CA9", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000b14 0%, #0d1117 40%, #000b14 100%)",
        "sidebar_bg": "#000b14",
    },
    "Mainz": {
        "primary": "#C3141E", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #170203 0%, #0d1117 40%, #170203 100%)",
        "sidebar_bg": "#170203",
    },
    "Borussia Monchengladbach": {
        "primary": "#000000", "secondary": "#00A54F", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #000000 0%, #0d1117 40%, #000000 100%)",
        "sidebar_bg": "#000000",
    },
    "Stuttgart": {
        "primary": "#E32219", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0403 0%, #0d1117 40%, #1b0403 100%)",
        "sidebar_bg": "#1b0403",
    },
    "Hamburg": {
        "primary": "#0D3D91", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #010711 0%, #0d1117 40%, #010711 100%)",
        "sidebar_bg": "#010711",
    },
    "Hannover": {
        "primary": "#00923F", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #001107 0%, #0d1117 40%, #001107 100%)",
        "sidebar_bg": "#001107",
    },
    "Nuremberg": {
        "primary": "#C6093B", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #170107 0%, #0d1117 40%, #170107 100%)",
        "sidebar_bg": "#170107",
    },
    "Bremen": {
        "primary": "#1D9053", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #031109 0%, #0d1117 40%, #031109 100%)",
        "sidebar_bg": "#031109",
    },
    "Furth": {
        "primary": "#00713C", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #000d07 0%, #0d1117 40%, #000d07 100%)",
        "sidebar_bg": "#000d07",
    },
    "Dusseldorf": {
        "primary": "#E2001A", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0003 0%, #0d1117 40%, #1b0003 100%)",
        "sidebar_bg": "#1b0003",
    },
    "Barcelona": {
        "primary": "#A50044", "secondary": "#004D98", "text": "#ffffff",
        "chart_scale": "Magenta",
        "bg_gradient": "linear-gradient(160deg, #130008 0%, #0d1117 40%, #130008 100%)",
        "sidebar_bg": "#130008",
    },
    "Atletico Madrid": {
        "primary": "#CB3524", "secondary": "#272E61", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #180604 0%, #0d1117 40%, #180604 100%)",
        "sidebar_bg": "#180604",
    },
    "Sevilla": {
        "primary": "#D8151E", "secondary": "#0A3A6E", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #190203 0%, #0d1117 40%, #190203 100%)",
        "sidebar_bg": "#190203",
    },
    "Real Betis": {
        "primary": "#00954C", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #001109 0%, #0d1117 40%, #001109 100%)",
        "sidebar_bg": "#001109",
    },
    "Real Sociedad": {
        "primary": "#0067B1", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000c15 0%, #0d1117 40%, #000c15 100%)",
        "sidebar_bg": "#000c15",
    },
    "Villarreal": {
        "primary": "#FFE500", "secondary": "#005187", "text": "#000000",
        "chart_scale": "YlOrRd",
        "bg_gradient": "linear-gradient(160deg, #1e1b00 0%, #0d1117 40%, #1e1b00 100%)",
        "sidebar_bg": "#1e1b00",
    },
    "Athletic Bilbao": {
        "primary": "#EE2523", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1c0404 0%, #0d1117 40%, #1c0404 100%)",
        "sidebar_bg": "#1c0404",
    },
    "Valencia": {
        "primary": "#FF6B00", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Oranges",
        "bg_gradient": "linear-gradient(160deg, #1e0c00 0%, #0d1117 40%, #1e0c00 100%)",
        "sidebar_bg": "#1e0c00",
    },
    "Osasuna": {
        "primary": "#D91A21", "secondary": "#001A72", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1a0303 0%, #0d1117 40%, #1a0303 100%)",
        "sidebar_bg": "#1a0303",
    },
    "Espanyol": {
        "primary": "#0A72B7", "secondary": "#B6122A", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #010d15 0%, #0d1117 40%, #010d15 100%)",
        "sidebar_bg": "#010d15",
    },
    "Getafe": {
        "primary": "#005999", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000a12 0%, #0d1117 40%, #000a12 100%)",
        "sidebar_bg": "#000a12",
    },
    "Cadiz": {
        "primary": "#F8D616", "secondary": "#0A2A5E", "text": "#000000",
        "chart_scale": "YlOrRd",
        "bg_gradient": "linear-gradient(160deg, #1d1902 0%, #0d1117 40%, #1d1902 100%)",
        "sidebar_bg": "#1d1902",
    },
    "Mallorca": {
        "primary": "#CC0000", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #180000 0%, #0d1117 40%, #180000 100%)",
        "sidebar_bg": "#180000",
    },
    "Rayo Vallecano": {
        "primary": "#E2231A", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0403 0%, #0d1117 40%, #1b0403 100%)",
        "sidebar_bg": "#1b0403",
    },
    "Granada": {
        "primary": "#C31F39", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #170306 0%, #0d1117 40%, #170306 100%)",
        "sidebar_bg": "#170306",
    },
    "Celta Vigo": {
        "primary": "#8AC3EE", "secondary": "#FFFFFF", "text": "#000000",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #10171c 0%, #0d1117 40%, #10171c 100%)",
        "sidebar_bg": "#10171c",
    },
    "Levante": {
        "primary": "#004A93", "secondary": "#B2001F", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000811 0%, #0d1117 40%, #000811 100%)",
        "sidebar_bg": "#000811",
    },
    "Elche": {
        "primary": "#017A4A", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #000e08 0%, #0d1117 40%, #000e08 100%)",
        "sidebar_bg": "#000e08",
    },
    "Deportivo Alaves": {
        "primary": "#0455A1", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000a13 0%, #0d1117 40%, #000a13 100%)",
        "sidebar_bg": "#000a13",
    },
    "Juventus": {
        "primary": "#000000", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greys",
        "bg_gradient": "linear-gradient(160deg, #000000 0%, #0d1117 40%, #000000 100%)",
        "sidebar_bg": "#000000",
    },
    "Inter Milan": {
        "primary": "#0068A8", "secondary": "#010101", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000c14 0%, #0d1117 40%, #000c14 100%)",
        "sidebar_bg": "#000c14",
    },
    "AC Milan": {
        "primary": "#FB090B", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1e0101 0%, #0d1117 40%, #1e0101 100%)",
        "sidebar_bg": "#1e0101",
    },
    "Napoli": {
        "primary": "#12A0D7", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #021319 0%, #0d1117 40%, #021319 100%)",
        "sidebar_bg": "#021319",
    },
    "Roma": {
        "primary": "#8E1F2F", "secondary": "#F0BC42", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #110305 0%, #0d1117 40%, #110305 100%)",
        "sidebar_bg": "#110305",
    },
    "Lazio": {
        "primary": "#87D8F7", "secondary": "#FFFFFF", "text": "#000000",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #10191d 0%, #0d1117 40%, #10191d 100%)",
        "sidebar_bg": "#10191d",
    },
    "Atalanta": {
        "primary": "#1E71B8", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #030d16 0%, #0d1117 40%, #030d16 100%)",
        "sidebar_bg": "#030d16",
    },
    "Fiorentina": {
        "primary": "#482E92", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #080511 0%, #0d1117 40%, #080511 100%)",
        "sidebar_bg": "#080511",
    },
    "Bologna": {
        "primary": "#A61E22", "secondary": "#08245C", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #130304 0%, #0d1117 40%, #130304 100%)",
        "sidebar_bg": "#130304",
    },
    "Sampdoria": {
        "primary": "#1A2E5A", "secondary": "#B41E34", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #03050a 0%, #0d1117 40%, #03050a 100%)",
        "sidebar_bg": "#03050a",
    },
    "Torino": {
        "primary": "#7A263A", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #0e0406 0%, #0d1117 40%, #0e0406 100%)",
        "sidebar_bg": "#0e0406",
    },
    "Udinese": {
        "primary": "#000000", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greys",
        "bg_gradient": "linear-gradient(160deg, #000000 0%, #0d1117 40%, #000000 100%)",
        "sidebar_bg": "#000000",
    },
    "Sassuolo": {
        "primary": "#00A650", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #001309 0%, #0d1117 40%, #001309 100%)",
        "sidebar_bg": "#001309",
    },
    "Empoli": {
        "primary": "#0555A1", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000a13 0%, #0d1117 40%, #000a13 100%)",
        "sidebar_bg": "#000a13",
    },
    "Genoa": {
        "primary": "#B41E33", "secondary": "#001E62", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #150306 0%, #0d1117 40%, #150306 100%)",
        "sidebar_bg": "#150306",
    },
    "Cagliari": {
        "primary": "#A50F30", "secondary": "#00205B", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #130105 0%, #0d1117 40%, #130105 100%)",
        "sidebar_bg": "#130105",
    },
    "Salernitana": {
        "primary": "#7A263A", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #0e0406 0%, #0d1117 40%, #0e0406 100%)",
        "sidebar_bg": "#0e0406",
    },
    "Spezia": {
        "primary": "#000000", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greys",
        "bg_gradient": "linear-gradient(160deg, #000000 0%, #0d1117 40%, #000000 100%)",
        "sidebar_bg": "#000000",
    },
    "Hellas Verona": {
        "primary": "#002D62", "secondary": "#FFD400", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #00050b 0%, #0d1117 40%, #00050b 100%)",
        "sidebar_bg": "#00050b",
    },
    "Venezia": {
        "primary": "#FB6706", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Oranges",
        "bg_gradient": "linear-gradient(160deg, #1e0c00 0%, #0d1117 40%, #1e0c00 100%)",
        "sidebar_bg": "#1e0c00",
    },
    "Paris Saint-Germain": {
        "primary": "#004170", "secondary": "#DA291C", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #00070d 0%, #0d1117 40%, #00070d 100%)",
        "sidebar_bg": "#00070d",
    },
    "Olympique Lyonnais": {
        "primary": "#002B5C", "secondary": "#C8102E", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #00050b 0%, #0d1117 40%, #00050b 100%)",
        "sidebar_bg": "#00050b",
    },
    "Olympique Marseille": {
        "primary": "#2FA5DC", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #05131a 0%, #0d1117 40%, #05131a 100%)",
        "sidebar_bg": "#05131a",
    },
    "Monaco": {
        "primary": "#E2231A", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0403 0%, #0d1117 40%, #1b0403 100%)",
        "sidebar_bg": "#1b0403",
    },
    "Lille": {
        "primary": "#C3121E", "secondary": "#001A4B", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #170203 0%, #0d1117 40%, #170203 100%)",
        "sidebar_bg": "#170203",
    },
    "Rennes": {
        "primary": "#E2231A", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0403 0%, #0d1117 40%, #1b0403 100%)",
        "sidebar_bg": "#1b0403",
    },
    "Nice": {
        "primary": "#C8102E", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #180105 0%, #0d1117 40%, #180105 100%)",
        "sidebar_bg": "#180105",
    },
    "Strasbourg": {
        "primary": "#0072B5", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000d15 0%, #0d1117 40%, #000d15 100%)",
        "sidebar_bg": "#000d15",
    },
    "Lens": {
        "primary": "#FFD100", "secondary": "#C8102E", "text": "#000000",
        "chart_scale": "YlOrRd",
        "bg_gradient": "linear-gradient(160deg, #1e1900 0%, #0d1117 40%, #1e1900 100%)",
        "sidebar_bg": "#1e1900",
    },
    "Nantes": {
        "primary": "#FFD100", "secondary": "#00843D", "text": "#000000",
        "chart_scale": "YlGn",
        "bg_gradient": "linear-gradient(160deg, #1e1900 0%, #0d1117 40%, #1e1900 100%)",
        "sidebar_bg": "#1e1900",
    },
    "Angers": {
        "primary": "#000000", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greys",
        "bg_gradient": "linear-gradient(160deg, #000000 0%, #0d1117 40%, #000000 100%)",
        "sidebar_bg": "#000000",
    },
    "Bordeaux": {
        "primary": "#00204E", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #000309 0%, #0d1117 40%, #000309 100%)",
        "sidebar_bg": "#000309",
    },
    "Brest": {
        "primary": "#C8102E", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #180105 0%, #0d1117 40%, #180105 100%)",
        "sidebar_bg": "#180105",
    },
    "Reims": {
        "primary": "#C8102E", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #180105 0%, #0d1117 40%, #180105 100%)",
        "sidebar_bg": "#180105",
    },
    "Metz": {
        "primary": "#7A263A", "secondary": "#87CEEB", "text": "#ffffff",
        "chart_scale": "Purples",
        "bg_gradient": "linear-gradient(160deg, #0e0406 0%, #0d1117 40%, #0e0406 100%)",
        "sidebar_bg": "#0e0406",
    },
    "Lorient": {
        "primary": "#FF6600", "secondary": "#000000", "text": "#ffffff",
        "chart_scale": "Oranges",
        "bg_gradient": "linear-gradient(160deg, #1e0c00 0%, #0d1117 40%, #1e0c00 100%)",
        "sidebar_bg": "#1e0c00",
    },
    "Troyes": {
        "primary": "#002F6C", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Blues",
        "bg_gradient": "linear-gradient(160deg, #00050c 0%, #0d1117 40%, #00050c 100%)",
        "sidebar_bg": "#00050c",
    },
    "Clermont": {
        "primary": "#E2231A", "secondary": "#0A2240", "text": "#ffffff",
        "chart_scale": "Reds",
        "bg_gradient": "linear-gradient(160deg, #1b0403 0%, #0d1117 40%, #1b0403 100%)",
        "sidebar_bg": "#1b0403",
    },
    "Saint-Etienne": {
        "primary": "#00913F", "secondary": "#FFFFFF", "text": "#ffffff",
        "chart_scale": "Greens",
        "bg_gradient": "linear-gradient(160deg, #001107 0%, #0d1117 40%, #001107 100%)",
        "sidebar_bg": "#001107",
    },
}

CLUB_THEMES.update(_AUTO_CLUB_THEMES)


st.sidebar.header("🎨 Club Theme")
selected_theme_name = st.sidebar.selectbox("Select Club Theme", list(CLUB_THEMES.keys()))
theme = CLUB_THEMES[selected_theme_name]

# ── Club badge in sidebar ──────────────────────────────────────────────────
_badge_b64 = get_club_badge_b64(selected_theme_name)
if _badge_b64:
    st.sidebar.markdown(
        f'''<div style="text-align:center;padding:10px 0 6px 0;">
            <img src="data:image/png;base64,{_badge_b64}"
                 style="max-height:110px;max-width:120px;object-fit:contain;
                        filter:drop-shadow(0 2px 8px rgba(0,0,0,0.6));">
        </div>''',
        unsafe_allow_html=True
    )

st.markdown(f"""
<style>
/* ── Main background gradient with vignette ── */
.stApp {{
    background: {theme['bg_gradient']};
    color: white;
}}
/* ── Subtle glow accent strip at top ── */
.stApp::before {{
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent, {theme['primary']}, {theme['secondary']}, {theme['primary']}, transparent);
    z-index: 9999;
}}
/* ── Sidebar background with glow border ── */
section[data-testid="stSidebar"] {{
    background: {theme['sidebar_bg']} !important;
    border-right: 1px solid {theme['primary']}44;
    box-shadow: 4px 0 20px {theme['primary']}11;
}}
/* ── Headers ── */
h1, h2, h3 {{ color: {theme['primary']} !important; }}
/* ── Metric values ── */
div[data-testid="stMetricValue"] {{ color: {theme['primary']} !important; }}
/* ── Buttons ── */
.stButton > button {{
    background: linear-gradient(135deg, {theme['primary']}dd, {theme['primary']});
    color: {theme['text']};
    border-radius: 8px;
    border: none;
    font-weight: 700;
    box-shadow: 0 2px 12px {theme['primary']}44;
    transition: all 0.2s ease;
}}
.stButton > button:hover {{
    opacity: 0.9;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px {theme['primary']}66;
}}
/* ── Tab active indicator ── */
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {theme['primary']} !important;
    border-bottom: 3px solid {theme['primary']} !important;
}}
/* ── Metric cards with glow border ── */
div[data-testid="metric-container"] {{
    background: rgba(255,255,255,0.03);
    border: 1px solid {theme['primary']}33;
    border-radius: 8px;
    padding: 8px;
    box-shadow: 0 0 12px {theme['primary']}0a;
    transition: box-shadow 0.2s ease;
}}
div[data-testid="metric-container"]:hover {{
    box-shadow: 0 0 20px {theme['primary']}22;
}}
/* ── Divider colour ── */
hr {{ border-color: {theme['primary']}33 !important; }}
/* ── Selectbox and input accent ── */
div[data-baseweb="select"] > div {{
    border-color: {theme['primary']}55 !important;
    background: rgba(255,255,255,0.04) !important;
}}
/* ── Success/error/info box borders ── */
div[data-testid="stAlert"] {{
    border-radius: 8px;
}}
</style>
""", unsafe_allow_html=True)

# ── Main header with club badge ──────────────────────────────────────────
_club_display_name = selected_theme_name.split(" (")[0]
_header_badge      = get_club_badge_b64(selected_theme_name)

if _header_badge:
    st.markdown(
        f'''<div style="display:flex;align-items:center;gap:18px;padding:8px 0 6px 0;">
            <img src="data:image/png;base64,{_header_badge}"
                 style="height:72px;width:72px;object-fit:contain;
                        filter:drop-shadow(0 2px 10px rgba(0,0,0,0.55));">
            <div>
                <div style="font-size:28px;font-weight:800;
                            color:{theme["primary"]};line-height:1.15;">FM26 Squad Hub</div>
                <div style="font-size:16px;color:#aaa;font-weight:500;">{_club_display_name}</div>
            </div>
        </div>''',
        unsafe_allow_html=True
    )
else:
    st.title(f"📊 FM26 Squad Hub — {_club_display_name}")

st.markdown("> Upload your FM26 Squad View CSV export below.")

uploaded_file = st.file_uploader("Upload FM26 Export CSV", type=["csv"])


def parse_appearances(val):
    """Handle '34 (3)', '34', '-', NaN etc — return total appearances as int."""
    s = str(val).strip()
    if s in ("", "-", "nan"):
        return 0
    # "34 (3)" -> 34 + 3 = 37, or just take leading number
    import re
    nums = re.findall(r"\d+", s)
    if not nums:
        return 0
    return sum(int(n) for n in nums)


def clean_fm_data(df):
    numeric_cols = [
        "Rating", "Ability", "Age", "Goals", "xG", "Assists",
        "Ps C/90", "Pres C/90", "Pres A/90", "Sprints/90",
        "OP-KP/90", "Ch C/90", "ShT/90", "Drb/90",
        "Tck/90", "Int/90", "Hdrs W/90", "Pr passes/90",
        "Dist/90", "xGP/90", "Mins/Gm", "CCC",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ".", regex=False).str.strip(),
                errors="coerce"
            )

    pct_cols = ["Shot %", "Conv %", "OP-Cr %", "Cr C/A", "Tck R", "Hdr %", "Sv %", "xSv %"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("%", "", regex=False).str.strip(),
                errors="coerce"
            ).fillna(0)

    # Fix Appearances — "34 (3)" style
    if "Appearances" in df.columns:
        df["Apps_numeric"] = df["Appearances"].apply(parse_appearances)
        df["Has Played"] = df["Apps_numeric"] > 0
    else:
        df["Apps_numeric"] = 0
        df["Has Played"] = False

    # Derived metrics
    if {"Goals", "xG"}.issubset(df.columns):
        df["Goals - xG"] = (df["Goals"].fillna(0) - df["xG"].fillna(0)).round(2)

    if "Ps C/90" in df.columns:
        mx = df["Ps C/90"].max()
        if pd.notna(mx) and mx > 0:
            df["Pass Rating (rel%)"] = ((df["Ps C/90"] / mx) * 100).round(1)

    if {"Pres C/90", "Pres A/90"}.issubset(df.columns):
        df["Press Success %"] = np.where(
            df["Pres A/90"] > 0,
            (df["Pres C/90"] / df["Pres A/90"] * 100).round(1),
            0
        )

    if "Rating" in df.columns:
        df = df.sort_values("Rating", ascending=False, na_position="last")

    # ── Wage parsing — handles "£12,500 p/w", "£1.2M p/a" etc ──
    if "Wage" in df.columns:
        def parse_wage(val):
            s = str(val).upper().replace("£","").replace(",","").replace(" ","").strip()
            if s in ("","NAN","NONE","-","—"):
                return None
            try:
                # Per week
                if "P/W" in s or "PW" in s:
                    s = s.replace("P/W","").replace("PW","")
                    if "M" in s: return float(s.replace("M","")) * 1_000_000 / 52
                    if "K" in s: return float(s.replace("K","")) * 1_000
                    return float(s)
                # Per year
                elif "P/A" in s or "PA" in s:
                    s = s.replace("P/A","").replace("PA","")
                    if "M" in s: return float(s.replace("M","")) * 1_000_000 / 52
                    if "K" in s: return float(s.replace("K","")) * 1_000 / 52
                    return float(s) / 52
                else:
                    if "M" in s: return float(s.replace("M","")) * 1_000_000 / 52
                    if "K" in s: return float(s.replace("K","")) * 1_000
                    return float(s)
            except:
                return None
        df["Wage (£/wk)"] = df["Wage"].apply(parse_wage)
        df["Wage (£M/yr)"] = (df["Wage (£/wk)"].fillna(0) * 52 / 1_000_000).round(2)

    # ── Contract expiry parsing ──────────────────────────────────
    for col in ["Expires", "Contract Expires", "Contract"]:
        if col in df.columns:
            df["Contract Expiry"] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            df["Expires Year"] = df["Contract Expiry"].dt.year
            # Flag contracts expiring within 12 months
            df["Contract Alert"] = df["Contract Expiry"].apply(
                lambda x: True if pd.notna(x) and (x - pd.Timestamp.now()).days <= 365 else False
            )
            break

    return df


if uploaded_file:
    try:
        sample = uploaded_file.read(2048).decode("utf-8", errors="ignore")
        uploaded_file.seek(0)
        sep = ";" if ";" in sample else ","

        raw_df = pd.read_csv(uploaded_file, sep=sep)
        raw_df.columns = [c.lstrip("\ufeff").strip() for c in raw_df.columns]
        df = clean_fm_data(raw_df)

        has_age = "Age" in df.columns and df["Age"].notna().any()

        # All players who have appeared at all
        played_df = df[df["Has Played"]].copy()

        # ── Unified Squad Scores (computed once, merged into both dfs) ──
        with st.spinner("⚙️ Computing unified squad scores…"):
            _squad_scores = compute_squad_scores(df, played_df)
            _score_cols   = ["Player", "Benchmark Score %", "Role Fit %", "Best Fit Role", "Squad Score", "Decision"]
            df        = df.merge(_squad_scores[_score_cols], on="Player", how="left")
            played_df = played_df.merge(_squad_scores[_score_cols], on="Player", how="left")

        # ── Theme accent vars (used across multiple tabs) ─────────────
        is_light_primary = _is_light_hex(theme["primary"])
        pdf_accent       = theme["secondary"] if is_light_primary else theme["primary"]
        pdf_accent_txt   = "#ffffff"
        header_text      = "#000000" if is_light_primary else "#ffffff"
        bar_color_high   = theme["secondary"] if is_light_primary else theme["primary"]
        bar_color_low    = "#e0e0e0"

        st.success(f"✅ Loaded {len(df)} players — {len(played_df)} with appearances.")

        # ── TOP METRICS ──────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Squad Size", len(df))
        c2.metric("With Appearances", len(played_df))
        c3.metric("Total Goals", int(df["Goals"].fillna(0).sum()) if "Goals" in df.columns else "—")
        c4.metric("Total xG", round(df["xG"].fillna(0).sum(), 1) if "xG" in df.columns else "—")
        c5.metric("Total Assists", int(df["Assists"].fillna(0).sum()) if "Assists" in df.columns else "—")

        # ── ALERTS ───────────────────────────────────────────────────
        st.header("🚨 Assistant Manager Alerts")
        alerts = 0
        a1, a2 = st.columns(2)

        with a1:
            if "Goals - xG" in played_df.columns:
                under = played_df[played_df["Goals - xG"] < -1.5]
                if not under.empty:
                    alerts += 1
                    names = ", ".join(under["Player"].tolist()) if "Player" in under.columns else "—"
                    st.error(f"⚠️ xG underperformers (< -1.5): {names}")
                over = played_df[played_df["Goals - xG"] > 3.0]
                if not over.empty:
                    alerts += 1
                    names = ", ".join(over["Player"].tolist()) if "Player" in over.columns else "—"
                    st.warning(f"🍀 xG overperformers (luck risk > +3): {names}")

        with a2:
            if has_age:
                vets = df[df["Age"] >= 30]
                youth = df[df["Age"] <= 21]
                if len(vets) > len(youth):
                    alerts += 1
                    st.info(f"📅 Aging squad: {len(vets)} veterans vs {len(youth)} youngsters.")
            if "Pass Rating (rel%)" in played_df.columns:
                poor = played_df[played_df["Pass Rating (rel%)"] < 40]
                if not poor.empty:
                    alerts += 1
                    st.warning(f"🔴 Poor passing output: {len(poor)} player(s) in bottom 40% of squad.")

        if alerts == 0:
            st.success("✅ No major issues detected.")

        # ── MULTI-SEASON STORAGE ──────────────────────────────────────
        import json

        st.sidebar.header("📅 Season Archive")

        # Load existing history from uploaded JSON
        history_upload = st.sidebar.file_uploader(
            "Load Season History (JSON)",
            type=["json"],
            key="history_upload"
        )

        if "season_history" not in st.session_state:
            st.session_state.season_history = {}

        if history_upload:
            loaded = json.loads(history_upload.read().decode("utf-8"))
            st.session_state.season_history = loaded
            st.sidebar.success(f"✅ Loaded {len(loaded)} season(s).")

        # Save current season
        season_label = st.sidebar.text_input("Season Label", value="2025/26", key="season_label")

        if st.sidebar.button("💾 Save Current Season"):
            season_data = df.copy()
            # Store key columns only to keep file size small
            keep_cols = [c for c in [
                "Player","Age","Position","Best Pos","Best Role","Rating",
                "Goals","xG","Assists","Appearances","Apps_numeric",
                "Ps C/90","Pres C/90","Sprints/90","Tck/90","Int/90",
                "Conv %","ShT/90","OP-KP/90","Mins/Gm","Goals - xG"
            ] if c in season_data.columns]
            season_data = season_data[keep_cols].copy()
            season_data["Season"] = season_label
            st.session_state.season_history[season_label] = season_data.to_dict(orient="records")
            st.sidebar.success(f"✅ Season {season_label} saved.")

        # Download history as JSON
        if st.session_state.season_history:
            history_json = json.dumps(st.session_state.season_history, ensure_ascii=False, indent=2)
            st.sidebar.download_button(
                "📥 Download Season History",
                data=history_json.encode("utf-8"),
                file_name="fm26_season_history.json",
                mime="application/json"
            )
            st.sidebar.caption(f"Archive: {len(st.session_state.season_history)} season(s) stored.")

        # ── TABS ──────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
            "📋 Squad Sheet", "📈 Analytics", "🎯 Radar & Compare",
            "⏳ Squad Planning", "🔀 Transfers",
            "📖 Club Chronicle", "🕵️ Scouting", "📄 Player Report",
            "🏆 Elite Benchmark", "🔄 Replace/Upgrade"
        ])

        # ════════════════════════════════════════════════════════
        # TAB 1 — SQUAD SHEET
        # ════════════════════════════════════════════════════════
        with tab1:
            st.subheader("Full Squad Database")

            f1, f2, f3, f4 = st.columns(4)
            with f1:
                if "Best Pos" in df.columns and df["Best Pos"].notna().any():
                    best_pos_opts = ["All"] + sorted(df["Best Pos"].dropna().unique().tolist())
                    best_pos_filter = st.selectbox(
                        "Filter by Best Pos (narrow)", best_pos_opts,
                        help="Narrow positional filter, e.g. 'D (C)' — best for finding exact role coverage."
                    )
                else:
                    best_pos_filter = "All"
            with f2:
                if "Position" in df.columns:
                    pos_opts = ["All"] + sorted(df["Position"].dropna().unique().tolist())
                    pos_filter = st.selectbox(
                        "Filter by Position (wide)", pos_opts,
                        help="Wider positional grouping, e.g. 'D (C), DM, M (C)' — shows all eligible positions for a player."
                    )
                else:
                    pos_filter = "All"
            with f3:
                if "Decision" in df.columns and df["Decision"].notna().any():
                    dec_opts = ["All"] + sorted(df["Decision"].dropna().unique().tolist())
                    decision_filter = st.selectbox("Filter by Decision", dec_opts, key="tab1_dec_filter")
                else:
                    decision_filter = "All"
            with f4:
                show_played_only = st.checkbox("Only players with appearances", value=False)

            view = df.copy()
            if best_pos_filter != "All":
                view = view[view["Best Pos"] == best_pos_filter]
            if pos_filter != "All":
                view = view[view["Position"] == pos_filter]
            if decision_filter != "All":
                view = view[view["Decision"] == decision_filter]
            if show_played_only:
                view = view[view["Has Played"]]

            hide_cols = ["Has Played", "Apps_numeric"]
            show_cols = [c for c in view.columns if c not in hide_cols]

            # ── Priority column ordering ──────────────────────────────
            # Always surface identity + score columns first, then benchmark
            # stats for the selected position (if one is chosen), then rest.
            identity_cols   = [c for c in ["Player", "Age", "Best Pos", "Position", "Best Role",
                                            "Rating", "Squad Score", "Decision",
                                            "Benchmark Score %", "Role Fit %", "Best Fit Role"]
                                if c in show_cols]
            if best_pos_filter != "All":
                applicable_roles = [
                    role for role, cfg in FM_BENCHMARKS.items()
                    if best_pos_filter in cfg["applies_to"]
                ]
                priority_metrics = []
                for role in applicable_roles:
                    for m in FM_BENCHMARKS[role]["metrics"]:
                        if m not in priority_metrics:
                            priority_metrics.append(m)

                priority_present = [m for m in priority_metrics if m in show_cols and m not in identity_cols]
                if priority_present:
                    remaining_cols = [c for c in show_cols if c not in identity_cols and c not in priority_present]
                    show_cols = identity_cols + priority_present + remaining_cols
                    st.caption(
                        f"📊 Columns reordered for **{best_pos_filter}** — showing "
                        f"{', '.join(priority_present)} first based on role benchmarks."
                    )
                else:
                    remaining_cols = [c for c in show_cols if c not in identity_cols]
                    show_cols = identity_cols + remaining_cols
            else:
                remaining_cols = [c for c in show_cols if c not in identity_cols]
                show_cols = identity_cols + remaining_cols

            st.dataframe(view[show_cols], use_container_width=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                view[show_cols].to_excel(w, index=False)
            st.download_button("📥 Export to Excel", buf.getvalue(),
                               file_name="fm26_squad.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # ════════════════════════════════════════════════════════
        # TAB 2 — ANALYTICS  (fully configurable scatter plots)
        # ════════════════════════════════════════════════════════
        with tab2:

            # Work out which numeric columns are usable
            numeric_available = [
                c for c in played_df.select_dtypes(include="number").columns
                if c not in ["Has Played", "Apps_numeric"]
                and played_df[c].notna().sum() > 1
            ]

            if len(numeric_available) < 2:
                st.warning("Not enough numeric data with appearances to plot. Check your CSV export.")
            else:
                # ── Scatter plot 1 ───────────────────────────────
                st.subheader("Scatter Plot A")
                sa1, sa2, sa3, sa4 = st.columns(4)

                default_x_a = "xG" if "xG" in numeric_available else numeric_available[0]
                default_y_a = "Goals" if "Goals" in numeric_available else numeric_available[1]
                default_c_a = "Rating" if "Rating" in numeric_available else numeric_available[0]

                x_a = sa1.selectbox("X Axis", numeric_available, index=numeric_available.index(default_x_a), key="xa")
                y_a = sa2.selectbox("Y Axis", numeric_available, index=numeric_available.index(default_y_a), key="ya")
                c_a = sa3.selectbox("Colour By", numeric_available, index=numeric_available.index(default_c_a), key="ca")
                diag_a = sa4.checkbox("Show diagonal reference line", value=True, key="diag_a")

                pos_filter_a = "All"
                if "Best Pos" in played_df.columns:
                    pos_opts_a = ["All"] + sorted(played_df["Best Pos"].dropna().unique().tolist())
                    pos_filter_a = st.selectbox("Filter Best Position (Plot A)", pos_opts_a, key="pfa")

                plot_df_a = played_df if pos_filter_a == "All" else played_df[played_df["Best Pos"] == pos_filter_a]

                fig_a = px.scatter(
                    plot_df_a, x=x_a, y=y_a,
                    color=c_a,
                    hover_name="Player" if "Player" in plot_df_a.columns else None,
                    hover_data={c: True for c in ["Position", "Best Role", "Rating", "Goals", "xG", "Assists"] if c in plot_df_a.columns},
                    color_continuous_scale=theme["chart_scale"],
                    template="plotly_dark",
                    title=f"{y_a} vs {x_a}",
                    height=500
                )
                fig_a.update_traces(marker=dict(size=10, opacity=0.85))

                if diag_a:
                    min_v = min(plot_df_a[x_a].min(), plot_df_a[y_a].min())
                    max_v = max(plot_df_a[x_a].max(), plot_df_a[y_a].max())
                    fig_a.add_shape(type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v,
                                    line=dict(color="grey", dash="dot", width=1))

                st.plotly_chart(fig_a, use_container_width=True)

                st.divider()

                # ── Scatter plot 2 ───────────────────────────────
                st.subheader("Scatter Plot B")
                sb1, sb2, sb3, sb4 = st.columns(4)

                default_x_b = "Pres C/90" if "Pres C/90" in numeric_available else numeric_available[0]
                default_y_b = "Sprints/90" if "Sprints/90" in numeric_available else numeric_available[1]
                default_c_b = "Rating" if "Rating" in numeric_available else numeric_available[0]

                x_b = sb1.selectbox("X Axis", numeric_available, index=numeric_available.index(default_x_b), key="xb")
                y_b = sb2.selectbox("Y Axis", numeric_available, index=numeric_available.index(default_y_b), key="yb")
                c_b = sb3.selectbox("Colour By", numeric_available, index=numeric_available.index(default_c_b), key="cb")
                diag_b = sb4.checkbox("Show diagonal reference line", value=False, key="diag_b")

                pos_filter_b = "All"
                if "Best Pos" in played_df.columns:
                    pos_opts_b = ["All"] + sorted(played_df["Best Pos"].dropna().unique().tolist())
                    pos_filter_b = st.selectbox("Filter Best Position (Plot B)", pos_opts_b, key="pfb")

                plot_df_b = played_df if pos_filter_b == "All" else played_df[played_df["Best Pos"] == pos_filter_b]

                fig_b = px.scatter(
                    plot_df_b, x=x_b, y=y_b,
                    color=c_b,
                    hover_name="Player" if "Player" in plot_df_b.columns else None,
                    hover_data={c: True for c in ["Position", "Best Role", "Rating", "Goals", "xG", "Assists"] if c in plot_df_b.columns},
                    color_continuous_scale=theme["chart_scale"],
                    template="plotly_dark",
                    title=f"{y_b} vs {x_b}",
                    height=500
                )
                fig_b.update_traces(marker=dict(size=10, opacity=0.85))

                if diag_b:
                    min_v = min(plot_df_b[x_b].min(), plot_df_b[y_b].min())
                    max_v = max(plot_df_b[x_b].max(), plot_df_b[y_b].max())
                    fig_b.add_shape(type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v,
                                    line=dict(color="grey", dash="dot", width=1))

                st.plotly_chart(fig_b, use_container_width=True)

                st.divider()

                # ── Bar chart ────────────────────────────────────
                st.subheader("Bar Chart — Compare Players")
                bc1, bc2, bc3 = st.columns(3)

                bar_metric = bc1.selectbox("Metric", numeric_available,
                                           index=numeric_available.index("Goals") if "Goals" in numeric_available else 0,
                                           key="bar_metric")
                bar_top_n  = bc2.slider("Top N players", 5, len(played_df), min(15, len(played_df)), key="bar_n")
                bar_pos    = bc3.selectbox("Best Position filter", ["All"] + sorted(played_df["Best Pos"].dropna().unique().tolist()) if "Best Pos" in played_df.columns else ["All"], key="bar_pos")

                bar_df = played_df if bar_pos == "All" else played_df[played_df["Best Pos"] == bar_pos]
                bar_df = bar_df.dropna(subset=[bar_metric]).sort_values(bar_metric, ascending=False).head(bar_top_n)

                if not bar_df.empty and "Player" in bar_df.columns:
                    fig_bar = px.bar(
                        bar_df, x="Player", y=bar_metric,
                        color=bar_metric,
                        color_continuous_scale=theme["chart_scale"],
                        template="plotly_dark",
                        title=f"Top {bar_top_n} — {bar_metric}",
                        height=450
                    )
                    fig_bar.update_layout(xaxis_tickangle=-35, coloraxis_showscale=False)
                    st.plotly_chart(fig_bar, use_container_width=True)

        # ════════════════════════════════════════════════════════
        # TAB 3 — RADAR & COMPARISON
        # ════════════════════════════════════════════════════════
        with tab3:
            st.subheader("🎯 Player Radar & Comparison")
            st.markdown("Compare 2–4 players side by side — metrics auto-preset from the first player's position, editable below.")

            # Define preset metric groups per role type
            RADAR_PRESETS = {
                "Attacking (Forwards)":      ["Goals", "xG", "Conv %", "ShT/90", "Drb/90", "Ch C/90", "Goals - xG"],
                "Pressing Forward":          ["Pres C/90", "Pres A/90", "Sprints/90", "Goals", "ShT/90", "Conv %", "Ch C/90"],
                "Midfielder — Creative":     ["Ps C/90", "OP-KP/90", "Ch C/90", "Assists", "Drb/90", "Pres C/90", "ShT/90"],
                "Midfielder — Defensive":    ["Tck/90", "Int/90", "Pres C/90", "Pres A/90", "Ps C/90", "Hdrs W/90", "Drb/90"],
                "Wide / Winger":             ["Drb/90", "OP-KP/90", "Sprints/90", "Ch C/90", "ShT/90", "Pres C/90", "Assists"],
                "Fullback / Wing Back":      ["Sprints/90", "Pres C/90", "Tck/90", "Int/90", "Ch C/90", "OP-KP/90", "Hdrs W/90"],
                "Centre Back":               ["Tck/90", "Int/90", "Hdrs W/90", "Pres C/90", "Ps C/90", "Drb/90", "Dist/90"],
                "Goalkeeper":                ["Sv %", "xSv %", "Ps C/90", "xGP/90"],
                "Custom (choose below)":     [],
            }

            # Maps a player's Best Pos directly to the radar preset that
            # matches the FM "What Does Good Look Like" benchmark for
            # that position — so picking a player auto-loads the right metrics.
            BEST_POS_TO_RADAR_PRESET = {
                "GK":     "Goalkeeper",
                "D (C)":  "Centre Back",
                "D (R)":  "Fullback / Wing Back",
                "D (L)":  "Fullback / Wing Back",
                "WB (R)": "Fullback / Wing Back",
                "WB (L)": "Fullback / Wing Back",
                "DM":     "Midfielder — Defensive",
                "M (C)":  "Midfielder — Creative",
                "AM (C)": "Midfielder — Creative",
                "AM (R)": "Wide / Winger",
                "AM (L)": "Wide / Winger",
                "ST (C)": "Attacking (Forwards)",
            }

            COMPARE_COLORS = [theme["primary"], "orange", "#00bfff", "#ff66cc"]

            # Only keep metrics that actually exist and have data
            all_numeric = [
                c for c in played_df.select_dtypes(include="number").columns
                if c not in ["Has Played", "Apps_numeric"]
                and played_df[c].notna().sum() > 0
            ]

            player_list = sorted(played_df["Player"].dropna().tolist()) if "Player" in played_df.columns else []

            if not player_list:
                st.warning("No players with appearances found.")
            else:
                # ── Player selector: 2-4 players ──────────────────────
                selected_players = st.multiselect(
                    "Select players to compare (2–4)",
                    options=player_list,
                    default=player_list[:2] if len(player_list) >= 2 else player_list,
                    max_selections=4,
                    key="radar_cmp_players"
                )

                if len(selected_players) < 2:
                    st.info("Select at least 2 players to compare.")
                else:
                    player_1 = selected_players[0]

                    # ── Auto-detect preset from Player 1's Best Pos ──────
                    auto_preset = None
                    p1_best_pos = None
                    player_1_row = played_df[played_df["Player"] == player_1]
                    if not player_1_row.empty and "Best Pos" in player_1_row.columns:
                        p1_best_pos = player_1_row.iloc[0].get("Best Pos", None)
                        if pd.notna(p1_best_pos):
                            auto_preset = BEST_POS_TO_RADAR_PRESET.get(str(p1_best_pos).strip())

                    preset_options = list(RADAR_PRESETS.keys())
                    default_index = preset_options.index(auto_preset) if auto_preset in preset_options else 0

                    # Reset the preset selectbox's stored value whenever the
                    # player-1 selection changes, so it always reflects the
                    # new player's position instead of sticking to the last pick.
                    if st.session_state.get("radar_preset_player") != player_1:
                        st.session_state["radar_preset"] = preset_options[default_index]
                        st.session_state["radar_preset_player"] = player_1

                    pc1, pc2 = st.columns([3, 1])
                    with pc1:
                        preset_name = st.selectbox(
                            "Metric Preset",
                            preset_options,
                            key="radar_preset"
                        )
                    with pc2:
                        if auto_preset:
                            st.caption(f"🎯 Auto-detected from **{p1_best_pos}**: {auto_preset}")

                    if preset_name == "Custom (choose below)":
                        default_metrics = all_numeric[:6] if len(all_numeric) >= 6 else all_numeric
                    else:
                        default_metrics = [m for m in RADAR_PRESETS[preset_name] if m in all_numeric]
                        if len(default_metrics) < 3:
                            st.info("Some preset metrics not in your export. Showing available ones.")

                    # ── Force metrics to follow the preset automatically ──
                    # Streamlit keeps a multiselect's previous selection in
                    # session_state across reruns, which would otherwise stop
                    # the metrics from updating when the player/preset changes.
                    # Track the active preset+player combo and reset the
                    # widget's stored value whenever either changes.
                    metrics_signature = f"{player_1}|{preset_name}"
                    if st.session_state.get("radar_metrics_signature") != metrics_signature:
                        st.session_state["radar_metrics"] = default_metrics[:8]
                        st.session_state["radar_metrics_signature"] = metrics_signature

                    radar_metrics = st.multiselect(
                        "Metrics to display (3–10 recommended) — auto-selected for this position, edit freely",
                        options=all_numeric,
                        key="radar_metrics"
                    )

                    if len(radar_metrics) < 3:
                        st.warning("Select at least 3 metrics to draw a radar.")
                    else:
                        def get_radar_values(player_name, metrics, data):
                            row = data[data["Player"] == player_name]
                            if row.empty:
                                return None
                            vals = []
                            for m in metrics:
                                v = row[m].values[0]
                                # Normalise 0-100 relative to squad max
                                col_max = data[m].max()
                                col_min = data[m].min()
                                if pd.isna(v):
                                    vals.append(0)
                                elif col_max == col_min:
                                    vals.append(50)
                                else:
                                    vals.append(round((v - col_min) / (col_max - col_min) * 100, 1))
                            return vals

                        def get_raw_values(player_name, metrics, data):
                            row = data[data["Player"] == player_name]
                            if row.empty:
                                return [0] * len(metrics)
                            return [round(float(row[m].values[0]), 2) if pd.notna(row[m].values[0]) else 0 for m in metrics]

                        # ── Radar overlay (2-4 players) ─────────────────
                        fig_radar = go.Figure()
                        raw_by_player = {}
                        for idx, p in enumerate(selected_players):
                            vals_p = get_radar_values(p, radar_metrics, played_df)
                            raw_p = get_raw_values(p, radar_metrics, played_df)
                            raw_by_player[p] = raw_p
                            if vals_p is None:
                                continue
                            color = COMPARE_COLORS[idx % 4]
                            fig_radar.add_trace(go.Scatterpolar(
                                r=vals_p + [vals_p[0]],
                                theta=radar_metrics + [radar_metrics[0]],
                                fill="toself",
                                fillcolor=hex_to_rgba(color, 0.2) if color.startswith("#") else "rgba(255,165,0,0.2)",
                                line=dict(color=color, width=2, dash="solid" if idx == 0 else "dash"),
                                name=p,
                                hovertemplate="<b>" + p + "</b><br>%{theta}: %{r:.1f} (normalised)<extra></extra>"
                            ))

                        fig_radar.update_layout(
                            polar=dict(
                                bgcolor="#1a1f2e",
                                radialaxis=dict(
                                    visible=True, range=[0, 100],
                                    tickfont=dict(color="grey", size=9),
                                    gridcolor="#333",
                                ),
                                angularaxis=dict(
                                    tickfont=dict(color="white", size=11),
                                    gridcolor="#444",
                                )
                            ),
                            paper_bgcolor="#0d1117",
                            plot_bgcolor="#0d1117",
                            font=dict(color="white"),
                            legend=dict(
                                bgcolor="#1a1f2e", bordercolor="#444",
                                font=dict(color="white")
                            ),
                            title=dict(
                                text=" vs ".join(selected_players) + " — Normalised (0–100 relative to squad)",
                                font=dict(color=theme["primary"], size=14)
                            ),
                            height=560
                        )
                        st.plotly_chart(fig_radar, use_container_width=True)

                        # ── Raw stats comparison table (colour-coded best value) ──
                        st.subheader("Raw Stats")
                        LOWER_IS_BETTER = {"Age"}

                        table_html = "<table style='width:100%;border-collapse:collapse;color:white;'>"
                        table_html += "<tr><th style='text-align:left;padding:8px;border-bottom:2px solid #444'>Metric</th>"
                        for p in selected_players:
                            table_html += f"<th style='text-align:center;padding:8px;border-bottom:2px solid #444'>{p}</th>"
                        table_html += "</tr>"

                        for m in radar_metrics:
                            vals = {p: raw_by_player[p][radar_metrics.index(m)] for p in selected_players}
                            valid_vals = {p: v for p, v in vals.items() if v is not None}
                            if not valid_vals:
                                continue
                            if m in LOWER_IS_BETTER:
                                best_val = min(valid_vals.values())
                            else:
                                best_val = max(valid_vals.values())

                            table_html += f"<tr><td style='padding:8px;border-bottom:1px solid #333;font-weight:600;color:#aaa'>{m}</td>"
                            for p in selected_players:
                                v = vals[p]
                                display_v = f"{v:.2f}" if isinstance(v, float) else str(v)
                                is_best = (v == best_val)
                                multi_val = len(set(valid_vals.values())) > 1
                                bg = f"{theme['primary']}33" if (is_best and multi_val) else "transparent"
                                font_weight = "800" if (is_best and multi_val) else "400"
                                color = theme['primary'] if (is_best and multi_val) else "white"
                                table_html += (f"<td style='padding:8px;border-bottom:1px solid #333;text-align:center;"
                                                f"background:{bg};font-weight:{font_weight};color:{color}'>{display_v}</td>")
                            table_html += "</tr>"
                        table_html += "</table>"

                        st.markdown(table_html, unsafe_allow_html=True)
                        st.caption(f"🟢 Highlighted cells in {theme['primary']} indicate the best value for that metric (lower is better for Age).")

                        st.divider()

                        # ── Bar chart comparison ────────────────────────
                        st.subheader("Bar Comparison")
                        bar_metric_cmp = st.selectbox("Metric for bar chart", radar_metrics, key="cmp_bar_metric")
                        bar_cmp_df = pd.DataFrame([
                            {"Player": p, bar_metric_cmp: raw_by_player[p][radar_metrics.index(bar_metric_cmp)]}
                            for p in selected_players
                        ]).dropna()
                        if not bar_cmp_df.empty:
                            fig_cmp_bar = px.bar(
                                bar_cmp_df, x="Player", y=bar_metric_cmp,
                                color="Player",
                                color_discrete_sequence=COMPARE_COLORS,
                                title=f"{bar_metric_cmp} Comparison",
                                template="plotly_dark", height=380
                            )
                            fig_cmp_bar.update_layout(showlegend=False)
                            st.plotly_chart(fig_cmp_bar, use_container_width=True)

                        st.divider()

                        # ── PIZZA CHART ────────────────────────────
                        st.subheader("🍕 Percentile Pizza Chart")
                        st.caption(
                            "Each slice shows the player's percentile rank within the squad for that metric "
                            "(100% = best in squad, 50% = squad median)."
                        )

                        # Group metrics by category for colour coding
                        PIZZA_CATEGORIES = {
                            "Attacking": ["Goals","xG","Conv %","ShT/90","Ch C/90","Assists","CCC","Goals - xG"],
                            "Possession": ["Ps C/90","OP-KP/90","Pr passes/90","Drb/90","Pass Rating (rel%)"],
                            "Defending": ["Tck/90","Int/90","Hdrs W/90","Tck R","Press Success %"],
                            "Physical": ["Pres C/90","Pres A/90","Sprints/90","Dist/90"],
                        }
                        PIZZA_COLORS = {
                            "Attacking": "#e63946",
                            "Possession": "#2a9d8f",
                            "Defending": "#457b9d",
                            "Physical": "#f4a261",
                            "Other": "#9d9d9d",
                        }

                        def categorise_metric(m):
                            for cat, mlist in PIZZA_CATEGORIES.items():
                                if m in mlist:
                                    return cat
                            return "Other"

                        def percentile_rank(series, value):
                            valid = series.dropna()
                            if len(valid) == 0 or pd.isna(value):
                                return 0
                            return round((valid < value).sum() / len(valid) * 100, 1)

                        for pz_player in selected_players:
                            pz_row = played_df[played_df["Player"] == pz_player].iloc[0]

                            percentiles = []
                            categories  = []
                            raw_vals    = []
                            for m in radar_metrics:
                                if m in played_df.columns and pd.notna(pz_row.get(m)):
                                    percentiles.append(percentile_rank(played_df[m], pz_row[m]))
                                    categories.append(categorise_metric(m))
                                    raw_vals.append(round(float(pz_row[m]), 2))
                                else:
                                    percentiles.append(0)
                                    categories.append("Other")
                                    raw_vals.append(0)

                            n_slices = len(radar_metrics)
                            angle_width = 360 / n_slices

                            fig_pizza = go.Figure()

                            for i, (m, pct, cat, rawv) in enumerate(zip(radar_metrics, percentiles, categories, raw_vals)):
                                # Background "track" (full 100%) - faint, drawn first (bottom layer)
                                fig_pizza.add_trace(go.Barpolar(
                                    r=[100],
                                    theta=[i * angle_width + angle_width/2],
                                    width=[angle_width * 0.92],
                                    marker_color="rgba(255,255,255,0.06)",
                                    marker_line_color="#0d1117",
                                    marker_line_width=2,
                                    opacity=1,
                                    showlegend=False,
                                    hoverinfo="skip"
                                ))
                                # Coloured percentile bar - drawn on top
                                fig_pizza.add_trace(go.Barpolar(
                                    r=[pct],
                                    theta=[i * angle_width + angle_width/2],
                                    width=[angle_width * 0.92],
                                    marker_color=PIZZA_COLORS.get(cat, "#9d9d9d"),
                                    marker_line_color="#0d1117",
                                    marker_line_width=2,
                                    opacity=0.95,
                                    name=cat,
                                    showlegend=False,
                                    hovertemplate=f"<b>{m}</b><br>Percentile: {pct}%<br>Value: {rawv}<extra></extra>"
                                ))

                            # Add metric labels around the outside
                            annotations = []
                            for i, (m, pct, rawv) in enumerate(zip(radar_metrics, percentiles, raw_vals)):
                                theta_deg = i * angle_width + angle_width/2
                                annotations.append(dict(
                                    text=f"<b>{m}</b><br>{rawv}",
                                    x=0.5 + 0.62 * np.cos(np.radians(90 - theta_deg)),
                                    y=0.5 + 0.62 * np.sin(np.radians(90 - theta_deg)),
                                    showarrow=False,
                                    font=dict(size=10, color="white"),
                                    xref="paper", yref="paper",
                                    align="center"
                                ))

                            fig_pizza.update_layout(
                                polar=dict(
                                    bgcolor="#0d1117",
                                    barmode="overlay",
                                    radialaxis=dict(visible=False, range=[0,100]),
                                    angularaxis=dict(visible=False, rotation=90, direction="clockwise")
                                ),
                                paper_bgcolor="#0d1117",
                                font=dict(color="white"),
                                title=dict(
                                    text=f"{pz_player} — Squad Percentile Pizza",
                                    font=dict(color=theme["primary"], size=14),
                                    x=0.5, xanchor="center"
                                ),
                                annotations=annotations,
                                height=580,
                                margin=dict(l=60, r=60, t=60, b=40)
                            )
                            st.plotly_chart(fig_pizza, use_container_width=True)

                        # Category legend
                        leg_cols = st.columns(len(PIZZA_CATEGORIES))
                        for col, (cat, color) in zip(leg_cols, PIZZA_COLORS.items()):
                            if cat == "Other":
                                continue
                            col.markdown(
                                f"<div style='display:flex;align-items:center;gap:6px;'>"
                                f"<div style='width:14px;height:14px;border-radius:3px;background:{color}'></div>"
                                f"<span style='font-size:12px;color:#ccc'>{cat}</span></div>",
                                unsafe_allow_html=True
                            )

        # ════════════════════════════════════════════════════════
        # TAB 4 — SQUAD PLANNING
        # ════════════════════════════════════════════════════════
        with tab4:
            # ── SQUAD DECISION MATRIX ────────────────────────────────
            st.subheader("🎯 Squad Decision Matrix")
            st.caption(
                "Unified recommendation per player based on FM benchmark data, "
                "role fit, age curve, rating and appearances."
            )

            if "Decision" in df.columns and "Squad Score" in df.columns:
                # ── Summary counts ───────────────────────────────────
                decision_order = [
                    "✅ Keep — Core", "✅ Keep", "🔄 Rotate",
                    "🌱 Develop", "🌱 Loan Out",
                    "🔴 Sell", "🔴 Sell / Replace", "🔴 Release", "⚪ Review"
                ]
                present_decisions = [d for d in decision_order if d in df["Decision"].values]
                if present_decisions:
                    dcols = st.columns(len(present_decisions))
                    for i, dec in enumerate(present_decisions):
                        cnt = (df["Decision"] == dec).sum()
                        dcols[i].metric(dec, cnt)

                # ── Filter + table ───────────────────────────────────
                dec_matrix_filter = st.multiselect(
                    "Show decisions",
                    options=present_decisions,
                    default=present_decisions,
                    key="dec_matrix_filter"
                )

                dec_display_cols = [c for c in [
                    "Player", "Age", "Best Pos", "Rating", "Apps_numeric",
                    "Benchmark Score %", "Role Fit %", "Squad Score", "Decision", "Best Fit Role"
                ] if c in df.columns]

                dec_view = df[dec_display_cols].rename(columns={"Apps_numeric": "Apps"})
                if dec_matrix_filter:
                    dec_view = dec_view[dec_view["Decision"].isin(dec_matrix_filter)]
                dec_view = dec_view.sort_values("Squad Score", ascending=False)

                st.dataframe(dec_view, use_container_width=True, hide_index=True)

                # ── Decision distribution chart ──────────────────────
                _dec_vc = df["Decision"].value_counts()
                dec_counts_df = pd.DataFrame({"Decision": _dec_vc.index, "Count": _dec_vc.values})

                DECISION_COLORS = {
                    "✅ Keep — Core":    "#1a8a3a",
                    "✅ Keep":           "#2ecc71",
                    "🔄 Rotate":         "#2255aa",
                    "🌱 Develop":        "#00bfff",
                    "🌱 Loan Out":       "#7ecef5",
                    "🔴 Sell":           "#cc2200",
                    "🔴 Sell / Replace": "#e05500",
                    "🔴 Release":        "#8b0000",
                    "⚪ Review":         "#888888",
                }
                fig_dec = px.bar(
                    dec_counts_df,
                    x="Decision", y="Count",
                    color="Decision",
                    color_discrete_map=DECISION_COLORS,
                    title="Squad Decision Distribution",
                    template="plotly_dark",
                    height=340,
                )
                fig_dec.update_layout(showlegend=False, xaxis_tickangle=-20)
                st.plotly_chart(fig_dec, use_container_width=True)

                # ── Export decision matrix ───────────────────────────
                dec_buf = io.BytesIO()
                with pd.ExcelWriter(dec_buf, engine="openpyxl") as dw:
                    dec_view.to_excel(dw, index=False)
                st.download_button(
                    "📥 Export Decision Matrix (Excel)",
                    dec_buf.getvalue(),
                    file_name="fm26_squad_decisions.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # ── Elite Squad Verdicts ─────────────────────────────
                st.divider()
                st.subheader("🏆 Elite Squad Verdicts")
                st.caption("Player-by-player critique through an elite squad lens. Every decision justified.")

                _verdict_defaults = [d for d in ["✅ Keep — Core", "✅ Keep", "🔄 Rotate", "🔴 Sell / Replace", "🔴 Sell"] if d in present_decisions]
                _verdict_filter = st.multiselect(
                    "Filter by decision",
                    options=present_decisions,
                    default=_verdict_defaults,
                    key="verdict_filter"
                )

                _verdict_df = df[df["Decision"].isin(_verdict_filter)].copy()
                _verdict_df = _verdict_df.sort_values("Squad Score", ascending=False)

                VERDICT_COLORS = {
                    "✅ Keep — Core":    "#1a8a3a",
                    "✅ Keep":           "#2ecc71",
                    "🔄 Rotate":         "#2255aa",
                    "🌱 Develop":        "#00bfff",
                    "🌱 Loan Out":       "#7ecef5",
                    "🔴 Sell":           "#cc2200",
                    "🔴 Sell / Replace": "#e05500",
                    "🔴 Release":        "#8b0000",
                    "⚪ Review":         "#888888",
                }

                for _, _vrow in _verdict_df.iterrows():
                    _vname    = _vrow.get("Player", "Player")
                    _vdec     = _vrow.get("Decision", "⚪ Review")
                    _vscore   = _vrow.get("Squad Score", 0)
                    _vrating  = _vrow.get("Rating", 0)
                    _vage     = _vrow.get("Age", "?")
                    _vpos     = _vrow.get("Best Pos", "")
                    _vcolor   = VERDICT_COLORS.get(_vdec, "#888888")
                    _write_up = _player_verdict(_vrow)

                    with st.expander(
                        f"{_vdec}  |  **{_vname}**  ·  {_vpos}  ·  Age {int(_vage) if pd.notna(_vage) else '?'}  ·  Rating {_vrating}  ·  Squad Score {_vscore:.0f}",
                        expanded=False
                    ):
                        st.markdown(
                            f'''<div style="border-left:4px solid {_vcolor};padding:10px 14px;
                                            border-radius:4px;background:rgba(255,255,255,0.04);">
                            ''',
                            unsafe_allow_html=True
                        )
                        st.markdown(_write_up)
                        st.markdown("</div>", unsafe_allow_html=True)

            else:
                st.info("Squad scores are being calculated. Please wait a moment and refresh.")

            st.divider()

            # ── PITCH DEPTH MAP ──────────────────────────────────
            st.subheader("⚽ Position Depth Map")

            has_best_pos = "Best Pos" in df.columns and df["Best Pos"].notna().any()

            if not has_best_pos:
                st.info("Add the **Best Pos** column to your FM26 export to enable the pitch depth map.")
            else:
                # FM26 Best Pos -> (label, x%, y%) on a 500x780 SVG pitch
                # x: 0=left edge, 500=right edge  |  y: 0=top (attacking), 780=bottom (GK end)
                PITCH_ZONES = {
                    "GK":     ("GK",    250, 700),
                    "D (C)":  ("CB",    250, 590),
                    "D (R)":  ("RB",    400, 590),
                    "D (L)":  ("LB",    100, 590),
                    "WB (R)": ("RWB",   440, 490),
                    "WB (L)": ("LWB",    60, 490),
                    "DM":     ("DM",    250, 460),
                    "M (C)":  ("CM",    250, 360),
                    "AM (C)": ("CAM",   250, 260),
                    "AM (R)": ("RM/RW", 420, 200),
                    "AM (L)": ("LM/LW",  80, 200),
                    "ST (C)": ("ST",    250, 120),
                }

                # Count players per Best Pos
                pos_counts  = {}
                pos_players = {}
                for _, row in df.iterrows():
                    bp = str(row.get("Best Pos", "")).strip()
                    if bp in PITCH_ZONES:
                        pos_counts[bp] = pos_counts.get(bp, 0) + 1
                        pname  = row.get("Player", "?")
                        rating = row.get("Rating", None)
                        pos_players.setdefault(bp, []).append(
                            f"{pname} ({rating})" if pd.notna(rating) else pname
                        )

                def depth_color(count):
                    if count == 0:   return "#cc2200"
                    elif count == 1: return "#cc7700"
                    elif count == 2: return "#aaaa00"
                    else:            return "#1a8a3a"

                # Build SVG circles + tooltips
                circles_svg = ""
                for pos_code, (zone_label, cx, cy) in PITCH_ZONES.items():
                    count       = pos_counts.get(pos_code, 0)
                    players_here = pos_players.get(pos_code, [])
                    color       = depth_color(count)
                    players_str = "&#10;".join(players_here) if players_here else "No players assigned"
                    status      = "Strong ✓" if count >= 3 else "OK" if count == 2 else "Thin ⚠" if count == 1 else "Uncovered ✗"
                    tooltip     = f"{zone_label} ({pos_code}) | {count} player(s) | {status}&#10;{players_str}"

                    circles_svg += f"""
                    <g class="zone" transform="translate({cx},{cy})">
                      <title>{tooltip}</title>
                      <circle r="34" fill="{color}" stroke="rgba(255,255,255,0.8)" stroke-width="2" opacity="0.92"/>
                      <text y="-8" text-anchor="middle" fill="white" font-size="13" font-weight="bold" font-family="Segoe UI,Arial,sans-serif">{zone_label}</text>
                      <text y="10" text-anchor="middle" fill="white" font-size="16" font-weight="bold" font-family="Segoe UI,Arial,sans-serif">{count}</text>
                    </g>"""

                pitch_svg = f"""
                <div style="display:flex;justify-content:center;background:#0d1117;padding:12px 0;">
                <svg viewBox="0 0 500 780" width="480" height="750"
                     xmlns="http://www.w3.org/2000/svg" style="border-radius:8px;">

                  <!-- Pitch background -->
                  <rect width="500" height="780" fill="#2d5a1b"/>

                  <!-- Pitch border -->
                  <rect x="20" y="20" width="460" height="740" fill="none"
                        stroke="rgba(255,255,255,0.7)" stroke-width="2.5"/>

                  <!-- Halfway line -->
                  <line x1="20" y1="390" x2="480" y2="390"
                        stroke="rgba(255,255,255,0.5)" stroke-width="1.5"/>

                  <!-- Centre circle -->
                  <circle cx="250" cy="390" r="60"
                        fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="1.5"/>
                  <circle cx="250" cy="390" r="3" fill="rgba(255,255,255,0.6)"/>

                  <!-- Top penalty area (attacking) -->
                  <rect x="130" y="20" width="240" height="110" fill="none"
                        stroke="rgba(255,255,255,0.5)" stroke-width="1.5"/>
                  <!-- Top 6-yard box -->
                  <rect x="190" y="20" width="120" height="45" fill="none"
                        stroke="rgba(255,255,255,0.4)" stroke-width="1"/>
                  <!-- Top goal -->
                  <rect x="210" y="10" width="80" height="12" fill="none"
                        stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>

                  <!-- Bottom penalty area (defensive/GK end) -->
                  <rect x="130" y="650" width="240" height="110" fill="none"
                        stroke="rgba(255,255,255,0.5)" stroke-width="1.5"/>
                  <!-- Bottom 6-yard box -->
                  <rect x="190" y="715" width="120" height="45" fill="none"
                        stroke="rgba(255,255,255,0.4)" stroke-width="1"/>
                  <!-- Bottom goal -->
                  <rect x="210" y="758" width="80" height="12" fill="none"
                        stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>

                  <!-- Attack / Defend labels -->
                  <text x="250" y="55" text-anchor="middle" fill="rgba(255,255,255,0.35)"
                        font-size="12" font-family="Segoe UI,Arial,sans-serif" letter-spacing="2">ATTACKING END</text>
                  <text x="250" y="745" text-anchor="middle" fill="rgba(255,255,255,0.35)"
                        font-size="12" font-family="Segoe UI,Arial,sans-serif" letter-spacing="2">DEFENSIVE END</text>

                  <!-- Position bubbles -->
                  {circles_svg}
                </svg>
                </div>

                <!-- Legend -->
                <div style="display:flex;gap:24px;justify-content:center;padding:10px 0;
                            background:#0d1117;font-family:Segoe UI,Arial,sans-serif;font-size:13px;">
                  <span style="color:#fff">
                    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
                                 background:#1a8a3a;margin-right:5px;vertical-align:middle;"></span>
                    Strong (3+)
                  </span>
                  <span style="color:#fff">
                    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
                                 background:#aaaa00;margin-right:5px;vertical-align:middle;"></span>
                    OK (2)
                  </span>
                  <span style="color:#fff">
                    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
                                 background:#cc7700;margin-right:5px;vertical-align:middle;"></span>
                    Thin (1)
                  </span>
                  <span style="color:#fff">
                    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
                                 background:#cc2200;margin-right:5px;vertical-align:middle;"></span>
                    Uncovered (0)
                  </span>
                </div>
                <p style="text-align:center;color:rgba(255,255,255,0.4);font-size:11px;
                           font-family:Segoe UI,Arial,sans-serif;background:#0d1117;padding-bottom:8px;">
                  Hover over a bubble to see which players fill that position
                </p>
                """

                st.components.v1.html(pitch_svg, height=820, scrolling=False)

                # Depth table
                st.subheader("Position Depth Detail")
                depth_rows = []
                for pos_code, (zone_label, cx, cy) in PITCH_ZONES.items():
                    count        = pos_counts.get(pos_code, 0)
                    players_here = pos_players.get(pos_code, [])
                    status       = "✅ Strong" if count >= 3 else "✓ OK" if count == 2 else "⚠️ Thin" if count == 1 else "❌ Uncovered"
                    depth_rows.append({
                        "Position": pos_code,
                        "Zone":     zone_label,
                        "Players":  count,
                        "Status":   status,
                        "Squad Members": ", ".join(players_here) if players_here else "—"
                    })
                st.dataframe(pd.DataFrame(depth_rows), use_container_width=True, hide_index=True)

            st.divider()

            if not has_age:
                st.warning("⚠️ Age column not found in export. Add it to your FM26 squad view to enable age charts.")
            else:
                p1, p2 = st.columns(2)

                with p1:
                    fig_age = px.histogram(
                        df, x="Age",
                        color="Best Pos" if has_best_pos else ("Position" if "Position" in df.columns else None),
                        nbins=16, title="Squad Age Distribution",
                        template="plotly_dark", height=400
                    )
                    st.plotly_chart(fig_age, use_container_width=True)

                with p2:
                    if "Rating" in played_df.columns and "Position" in played_df.columns:
                        fig_box = px.box(
                            played_df, x="Best Pos" if has_best_pos else "Position",
                            y="Rating",
                            color="Best Pos" if has_best_pos else "Position",
                            title="Rating Distribution by Position",
                            template="plotly_dark", height=400
                        )
                        fig_box.update_layout(xaxis_tickangle=-30, showlegend=False)
                        st.plotly_chart(fig_box, use_container_width=True)

                if {"Age","Rating"}.issubset(df.columns):
                    fig_ar = px.scatter(
                        df, x="Age", y="Rating",
                        hover_name="Player" if "Player" in df.columns else None,
                        color="Best Pos" if has_best_pos else ("Position" if "Position" in df.columns else None),
                        title="Age vs Rating — squad profile",
                        template="plotly_dark", height=450
                    )
                    fig_ar.update_traces(marker=dict(size=10, opacity=0.85))
                    st.plotly_chart(fig_ar, use_container_width=True)

                st.subheader("Depth Breakdown")
                d1, d2 = st.columns(2)
                age_cols = [c for c in ["Player","Best Pos","Position","Age","Rating","Best Role"] if c in df.columns]
                with d1:
                    st.markdown("**🧓 Veterans (30+)**")
                    st.dataframe(df[df["Age"] >= 30][age_cols].reset_index(drop=True), use_container_width=True)
                with d2:
                    st.markdown("**🌱 Youngsters (21 and under)**")
                    st.dataframe(df[df["Age"] <= 21][age_cols].reset_index(drop=True), use_container_width=True)

            # ── CONTRACT & WAGES ─────────────────────────────────
            has_wages    = "Wage (£/wk)" in df.columns and df["Wage (£/wk)"].notna().any()
            has_contract = "Contract Expiry" in df.columns and df["Contract Expiry"].notna().any()

            if has_wages or has_contract:
                st.divider()
                st.subheader("💰 Contract & Wages")

                if not has_wages and not has_contract:
                    st.info("Add **Wage** and **Expires** columns to your FM26 squad export to unlock this section.")
                else:
                    # ── Wage bill ────────────────────────────────────
                    if has_wages:
                        total_wage_pw = df["Wage (£/wk)"].fillna(0).sum()
                        total_wage_yr = df["Wage (£M/yr)"].fillna(0).sum()

                        w1, w2, w3, w4 = st.columns(4)
                        w1.metric("Total Wage Bill", f"£{total_wage_pw:,.0f} p/w")
                        w2.metric("Annual Wage Bill", f"£{total_wage_yr:.2f}M")
                        if has_contract:
                            expiring = df[df.get("Contract Alert", pd.Series([False]*len(df)))]
                            w3.metric("Contracts Expiring (<12 months)", len(expiring))
                        avg_wage = df["Wage (£/wk)"].dropna().mean()
                        w4.metric("Avg Wage", f"£{avg_wage:,.0f} p/w")

                        # Wage chart by position
                        if "Best Pos" in df.columns:
                            wage_by_pos = df.groupby("Best Pos")["Wage (£/wk)"].sum().sort_values(ascending=False).reset_index()
                            fig_wage = px.bar(
                                wage_by_pos, x="Best Pos", y="Wage (£/wk)",
                                color="Wage (£/wk)",
                                color_continuous_scale=theme["chart_scale"],
                                title="Weekly Wage Bill by Position",
                                template="plotly_dark", height=380
                            )
                            fig_wage.update_layout(coloraxis_showscale=False)
                            st.plotly_chart(fig_wage, use_container_width=True)

                    # ── Contract expiry timeline ──────────────────────
                    if has_contract:
                        st.subheader("📅 Contract Expiry Timeline")

                        contract_cols = [c for c in [
                            "Player", "Age", "Best Pos", "Rating",
                            "Wage (£/wk)", "Expires Year", "Contract Alert"
                        ] if c in df.columns]

                        contract_df = df[contract_cols].dropna(subset=["Expires Year"]).sort_values("Expires Year")

                        # Colour-code by urgency
                        now_year = pd.Timestamp.now().year
                        urgent   = contract_df[contract_df["Expires Year"] <= now_year + 1]
                        soon     = contract_df[(contract_df["Expires Year"] == now_year + 2)]
                        secure   = contract_df[contract_df["Expires Year"] > now_year + 2]

                        cu1, cu2, cu3 = st.columns(3)
                        with cu1:
                            st.markdown("**🔴 Expiring within 12 months**")
                            if not urgent.empty:
                                st.dataframe(urgent.drop(columns=["Contract Alert"], errors="ignore").reset_index(drop=True),
                                             use_container_width=True, hide_index=True)
                            else:
                                st.success("No contracts expiring imminently.")
                        with cu2:
                            st.markdown("**🟡 Expiring in 2 years**")
                            if not soon.empty:
                                st.dataframe(soon.drop(columns=["Contract Alert"], errors="ignore").reset_index(drop=True),
                                             use_container_width=True, hide_index=True)
                            else:
                                st.info("None expiring in 2 years.")
                        with cu3:
                            st.markdown("**🟢 Secure (2+ years remaining)**")
                            if not secure.empty:
                                st.dataframe(secure.drop(columns=["Contract Alert"], errors="ignore").reset_index(drop=True),
                                             use_container_width=True, hide_index=True)

                        # Expiry bar chart
                        expiry_counts = contract_df.groupby("Expires Year").size().reset_index(name="Players")
                        fig_expiry = px.bar(
                            expiry_counts, x="Expires Year", y="Players",
                            color="Players",
                            color_continuous_scale=[[0,"#1a8a3a"],[0.5,"#aaaa00"],[1,"#cc2200"]],
                            title="Contract Expiry by Year — Squad Exposure",
                            template="plotly_dark", height=350
                        )
                        fig_expiry.update_layout(coloraxis_showscale=False)
                        st.plotly_chart(fig_expiry, use_container_width=True)
            else:
                st.divider()
                st.info(
                    "💡 **Add Wage & Contract data to your export for financial planning tools.**\n\n"
                    "In FM26: Squad screen → right-click column header → add **Wage** and **Expires**."
                )

        # TAB 5 — TRANSFER HISTORY (CSV/Excel)
        # ════════════════════════════════════════════════════════
        with tab5:
            st.subheader("🔀 Transfer History")
            st.markdown("""
Upload a CSV or Excel file of your transfer history, or add transfers manually.

**Expected columns** *(column names are flexible — the app will try to match them automatically)*:
`player`, `fee`, `date`, `from_club`, `to_club`, `direction` (IN or OUT), `season` *(optional)*
""")

            if "transfer_log" not in st.session_state:
                st.session_state.transfer_log = []

            # ── Download template ─────────────────────────────────
            template_df = pd.DataFrame([{
                "player": "Jan Houska", "fee": "£35.5M", "date": "9/7/2036",
                "from_club": "Vitória de Guimarães", "to_club": "Aris", "direction": "IN", "season": "2036/37"
            },{
                "player": "Jairo Soriano", "fee": "£69M", "date": "23/8/2036",
                "from_club": "Aris", "to_club": "Blu-neri", "direction": "OUT", "season": "2036/37"
            }])
            tmpl_buf = io.BytesIO()
            with pd.ExcelWriter(tmpl_buf, engine="openpyxl") as tw:
                template_df.to_excel(tw, index=False)
            st.download_button(
                "📥 Download Transfer Template (Excel)",
                tmpl_buf.getvalue(),
                file_name="fm26_transfer_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.divider()

            # ── File upload ───────────────────────────────────────
            transfer_file = st.file_uploader(
                "Upload Transfer History (CSV or Excel)",
                type=["csv","xlsx","xls"],
                key="transfer_file"
            )

            if transfer_file:
                try:
                    ext = transfer_file.name.split(".")[-1].lower()
                    if ext == "csv":
                        t_upload = pd.read_csv(transfer_file)
                    else:
                        t_upload = pd.read_excel(transfer_file)

                    # Normalise column names — lowercase, strip spaces
                    t_upload.columns = [c.lower().strip().replace(" ","_") for c in t_upload.columns]

                    # Flexible column matching
                    col_map = {}
                    for target, variants in {
                        "player":    ["player","name","player_name"],
                        "fee":       ["fee","transfer_fee","amount","value"],
                        "date":      ["date","transfer_date","signed"],
                        "from_club": ["from_club","from","selling_club","previous_club","source"],
                        "to_club":   ["to_club","to","buying_club","destination","club"],
                        "direction": ["direction","type","in_out","transfer_type"],
                        "season":    ["season","year"],
                        "apps":      ["apps","appearances"],
                        "goals":     ["goals"],
                        "assists":   ["assists"],
                        "rating":    ["rating"],
                    }.items():
                        for v in variants:
                            if v in t_upload.columns:
                                col_map[target] = v
                                break

                    if "player" not in col_map:
                        st.error("Could not find a player name column. Check your file has a 'player' or 'name' column.")
                    else:
                        # Build normalised records
                        records = []
                        for _, row in t_upload.iterrows():
                            rec = {
                                "player":    str(row.get(col_map.get("player","player"), "—")),
                                "fee":       str(row.get(col_map.get("fee","fee"), "—")),
                                "date":      str(row.get(col_map.get("date","date"), "—")),
                                "from_club": str(row.get(col_map.get("from_club","from_club"), "—")),
                                "to_club":   str(row.get(col_map.get("to_club","to_club"), "—")),
                                "direction": str(row.get(col_map.get("direction","direction"), "IN")).upper().strip(),
                                "season":    str(row.get(col_map.get("season","season"), "—")),
                                "apps":      row.get(col_map.get("apps","apps"), None),
                                "goals":     row.get(col_map.get("goals","goals"), None),
                                "assists":   row.get(col_map.get("assists","assists"), None),
                                "rating":    row.get(col_map.get("rating","rating"), None),
                            }
                            records.append(rec)

                        season_label_t = st.selectbox(
                            "Season for this import (override if needed)",
                            options=["Keep from file"] + [f"20{y}/{y-1999:02d}" for y in range(25,45)],
                            key="t_season_override"
                        )
                        if st.button("✅ Import Transfers", key="import_transfers"):
                            if season_label_t != "Keep from file":
                                for r in records:
                                    r["season"] = season_label_t
                            existing_players = {r["player"] for r in st.session_state.transfer_log}
                            new_records = [r for r in records if r["player"] not in existing_players]
                            st.session_state.transfer_log.extend(new_records)
                            st.success(f"✅ Imported {len(new_records)} transfer(s). ({len(records)-len(new_records)} duplicates skipped.)")

                except Exception as ex:
                    st.error(f"Could not read file: {ex}")

            st.divider()

            # ── Manual entry ──────────────────────────────────────
            with st.expander("➕ Add Transfer Manually"):
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc5, mc6, mc7, mc8 = st.columns(4)
                m_player    = mc1.text_input("Player",         key="m_player")
                m_fee       = mc2.text_input("Fee",            key="m_fee", placeholder="£2.5M")
                m_date      = mc3.text_input("Date",           key="m_date", placeholder="Jul 2025")
                m_season    = mc4.text_input("Season",         key="m_season", placeholder="2025/26")
                m_from      = mc5.text_input("From Club",      key="m_from")
                m_to        = mc6.text_input("To Club",        key="m_to")
                m_direction = mc7.selectbox("Direction",       ["IN","OUT"], key="m_direction")
                m_rating    = mc8.text_input("Rating (opt.)",  key="m_rating", placeholder="7.24")
                if st.button("Add Transfer", key="add_manual_transfer"):
                    if m_player:
                        st.session_state.transfer_log.append({
                            "player": m_player, "fee": m_fee, "date": m_date,
                            "from_club": m_from, "to_club": m_to,
                            "direction": m_direction, "season": m_season,
                            "apps": None, "goals": None, "assists": None,
                            "rating": m_rating or None
                        })
                        st.success(f"✅ Added {m_player}.")

            # ── Display log ───────────────────────────────────────
            if st.session_state.transfer_log:
                transfer_df = pd.DataFrame(st.session_state.transfer_log)

                # Season filter
                if "season" in transfer_df.columns:
                    seasons_t = ["All"] + sorted(transfer_df["season"].dropna().unique().tolist())
                    sel_season_t = st.selectbox("Filter by Season", seasons_t, key="t_season_filter")
                    view_t = transfer_df if sel_season_t == "All" else transfer_df[transfer_df["season"] == sel_season_t]
                else:
                    view_t = transfer_df

                t_in  = view_t[view_t["direction"] == "IN"]  if "direction" in view_t.columns else pd.DataFrame()
                t_out = view_t[view_t["direction"] == "OUT"] if "direction" in view_t.columns else pd.DataFrame()

                ti1, ti2, ti3, ti4 = st.columns(4)
                ti1.metric("Players Signed",          len(t_in))
                ti2.metric("Players Sold / Released", len(t_out))

                # Net spend calculation
                def parse_fee(fee_str):
                    """Convert £35.5M, £850K, Free etc to float millions."""
                    s = str(fee_str).upper().replace("£","").replace(",","").strip()
                    if any(x in s for x in ["FREE","LOAN","—","NAN","NONE",""]):
                        return 0.0
                    try:
                        if "M" in s:
                            return float(s.replace("M","").replace("+","").strip())
                        elif "K" in s:
                            return float(s.replace("K","").replace("+","").strip()) / 1000
                        else:
                            return float(s.replace("+","").strip()) / 1_000_000
                    except:
                        return 0.0

                if "fee" in view_t.columns:
                    spent   = sum(parse_fee(f) for f in t_in["fee"])  if not t_in.empty  else 0
                    received= sum(parse_fee(f) for f in t_out["fee"]) if not t_out.empty else 0
                    net     = received - spent
                    ti3.metric("Total Spent",    f"£{spent:.1f}M")
                    ti4.metric("Net Spend", f"£{abs(net):.1f}M {'surplus' if net >= 0 else 'deficit'}",
                               delta=f"{'▲' if net >= 0 else '▼'} £{abs(net):.1f}M")

                col_in, col_out = st.columns(2)
                display_cols = [c for c in ["player","from_club","to_club","fee","date","season","apps","goals","assists","rating"]
                                if c in view_t.columns]
                with col_in:
                    st.markdown(f"### 🟢 Arrivals ({len(t_in)})")
                    if not t_in.empty:
                        st.dataframe(t_in[display_cols].reset_index(drop=True),
                                     use_container_width=True, hide_index=True)
                with col_out:
                    st.markdown(f"### 🔴 Departures ({len(t_out)})")
                    if not t_out.empty:
                        st.dataframe(t_out[display_cols].reset_index(drop=True),
                                     use_container_width=True, hide_index=True)

                # Fee breakdown chart
                if "fee" in view_t.columns and "player" in view_t.columns:
                    st.subheader("💰 Transfer Fee Breakdown")
                    fee_data = view_t.copy()
                    fee_data["fee_m"] = fee_data["fee"].apply(parse_fee)
                    fee_data = fee_data[fee_data["fee_m"] > 0].sort_values("fee_m", ascending=False).head(15)
                    if not fee_data.empty:
                        fig_fees = px.bar(
                            fee_data, x="player", y="fee_m",
                            color="direction",
                            color_discrete_map={"IN": "#1a8a3a", "OUT": "#cc2200"},
                            title="Top 15 Transfer Fees (£M)",
                            labels={"fee_m": "Fee (£M)", "player": "Player"},
                            template="plotly_dark", height=400
                        )
                        fig_fees.update_layout(xaxis_tickangle=-35, showlegend=True)
                        st.plotly_chart(fig_fees, use_container_width=True)

                # Export
                t_buf = io.BytesIO()
                with pd.ExcelWriter(t_buf, engine="openpyxl") as tw:
                    transfer_df.to_excel(tw, index=False)
                dl1, dl2 = st.columns(2)
                dl1.download_button(
                    "📥 Export Transfer Log (Excel)",
                    t_buf.getvalue(),
                    file_name="fm26_transfers.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                csv_buf = transfer_df.to_csv(index=False).encode("utf-8")
                dl2.download_button(
                    "📥 Export Transfer Log (CSV)",
                    csv_buf,
                    file_name="fm26_transfers.csv",
                    mime="text/csv"
                )
                if st.button("🗑️ Clear Transfer Log", key="clear_transfers"):
                    st.session_state.transfer_log = []
                    st.rerun()
            else:
                st.info("No transfers logged yet. Upload a file or add manually above.")

        # ════════════════════════════════════════════════════════
        # TAB 6 — CLUB CHRONICLE (incl. Season Archive & Career Records)
        # ════════════════════════════════════════════════════════
        with tab6:
            st.subheader("📖 Club Chronicle")
            st.markdown("Season archive, career records and an auto-generated narrative history of your club.")

            if not st.session_state.season_history:
                st.info(
                    "No season history saved yet.\n\n"
                    "**How to build your archive:**\n"
                    "1. At the end of each season, type a season label in the sidebar (e.g. 2025/26)\n"
                    "2. Click **Save Current Season**\n"
                    "3. Click **Download Season History** to save the JSON file\n"
                    "4. Next season, upload that JSON file via **Load Season History** before uploading your new CSV\n\n"
                    "Over time this builds a complete record of every player across your entire save — "
                    "and the story of your club will be written here."
                )
            else:
                all_seasons_chron = pd.DataFrame([
                    record
                    for season_records in st.session_state.season_history.values()
                    for record in season_records
                ])
                seasons_sorted = sorted(st.session_state.season_history.keys())
                club_name_chron = selected_theme_name.split(" (")[0]

                st.caption(f"Archive covers {len(seasons_sorted)} season(s): {', '.join(seasons_sorted)}")

                # ── Season Summary Cards ─────────────────────────
                st.subheader("📋 Season Summaries")
                for season in seasons_sorted:
                    s_df = pd.DataFrame(st.session_state.season_history[season])
                    with st.expander(f"📋 {season}", expanded=(season == seasons_sorted[-1])):
                        sm1, sm2, sm3, sm4 = st.columns(4)
                        sm1.metric("Players", len(s_df))
                        sm2.metric("Total Goals", int(s_df["Goals"].fillna(0).sum()) if "Goals" in s_df.columns else "—")
                        sm3.metric("Total xG", round(s_df["xG"].fillna(0).sum(), 1) if "xG" in s_df.columns else "—")
                        sm4.metric("Avg Rating", round(s_df["Rating"].dropna().mean(), 2) if "Rating" in s_df.columns else "—")

                        if "Goals" in s_df.columns and "Player" in s_df.columns:
                            top_scorer = s_df.nlargest(1, "Goals").iloc[0]
                            st.markdown(f"⚽ **Top Scorer:** {top_scorer['Player']} — {int(top_scorer['Goals'])} goals")
                        if "Assists" in s_df.columns and "Player" in s_df.columns:
                            top_assist = s_df.nlargest(1, "Assists").iloc[0]
                            st.markdown(f"🎯 **Top Assister:** {top_assist['Player']} — {int(top_assist['Assists'])} assists")
                        if "Rating" in s_df.columns and "Player" in s_df.columns:
                            top_rated = s_df.dropna(subset=["Rating"]).nlargest(1, "Rating").iloc[0]
                            st.markdown(f"⭐ **Best Rated:** {top_rated['Player']} — {top_rated['Rating']}")
                        if "Apps_numeric" in s_df.columns and "Player" in s_df.columns:
                            most_apps = s_df.nlargest(1, "Apps_numeric").iloc[0]
                            st.markdown(f"👕 **Most Appearances:** {most_apps['Player']} — {int(most_apps['Apps_numeric'])} apps")

                st.divider()

                # ── Player Career Arcs ───────────────────────────
                st.subheader("📈 Player Career Arc")
                all_players = sorted(all_seasons_chron["Player"].dropna().unique().tolist()) if "Player" in all_seasons_chron.columns else []

                if all_players:
                    arc_metric_opts = [c for c in ["Rating","Goals","xG","Assists","Pres C/90","Ps C/90"] if c in all_seasons_chron.columns]
                    arc_col1, arc_col2 = st.columns(2)
                    arc_players = arc_col1.multiselect("Select Players", all_players, default=all_players[:3], key="arc_players")
                    arc_metric  = arc_col2.selectbox("Metric", arc_metric_opts, key="arc_metric")

                    if arc_players and arc_metric:
                        arc_df = all_seasons_chron[all_seasons_chron["Player"].isin(arc_players)][["Player","Season", arc_metric]].dropna()
                        fig_arc = px.line(
                            arc_df, x="Season", y=arc_metric, color="Player",
                            markers=True,
                            title=f"{arc_metric} — Career Progression",
                            template="plotly_dark", height=400
                        )
                        fig_arc.update_traces(line=dict(width=2), marker=dict(size=8))
                        st.plotly_chart(fig_arc, use_container_width=True)

                st.divider()

                # ── All-Time Best XI ─────────────────────────────
                st.subheader("🏆 All-Time Best XI")
                st.caption("Best performing player per position across all seasons, weighted by total minutes played.")

                XI_POSITIONS = ["GK","D (C)","D (R)","D (L)","DM","M (C)","AM (R)","AM (L)","AM (C)","ST (C)","WB (R)"]

                if "Apps_numeric" in all_seasons_chron.columns and "Best Pos" in all_seasons_chron.columns and "Rating" in all_seasons_chron.columns:
                    career = all_seasons_chron.groupby(["Player","Best Pos"]).agg(
                        Total_Apps=("Apps_numeric","sum"),
                        Avg_Rating=("Rating","mean"),
                        Total_Goals=("Goals","sum") if "Goals" in all_seasons_chron.columns else ("Apps_numeric","count"),
                    ).reset_index()
                    career["Career Score"] = (career["Avg_Rating"] * career["Total_Apps"]).round(1)

                    best_xi_rows = []
                    for pos in XI_POSITIONS:
                        candidates = career[career["Best Pos"] == pos]
                        if not candidates.empty:
                            best = candidates.nlargest(1, "Career Score").iloc[0]
                            best_xi_rows.append({
                                "Position": pos,
                                "Player": best["Player"],
                                "Avg Rating": round(best["Avg_Rating"], 2),
                                "Total Apps": int(best["Total_Apps"]),
                                "Career Score": best["Career Score"]
                            })

                    if best_xi_rows:
                        best_xi_df = pd.DataFrame(best_xi_rows)
                        st.dataframe(best_xi_df, use_container_width=True, hide_index=True)

                        st.subheader("📊 All-Time Career Leaderboard")
                        top_career = career.nlargest(15, "Career Score")[["Player","Best Pos","Avg_Rating","Total_Apps","Career Score"]]
                        top_career.columns = ["Player","Best Pos","Avg Rating","Total Apps","Career Score"]
                        fig_career = px.bar(
                            top_career, x="Player", y="Career Score",
                            color="Career Score",
                            color_continuous_scale=theme["chart_scale"],
                            title="Top 15 — All-Time Career Score (Avg Rating × Apps)",
                            template="plotly_dark", height=420
                        )
                        fig_career.update_layout(xaxis_tickangle=-35, coloraxis_showscale=False)
                        st.plotly_chart(fig_career, use_container_width=True)
                else:
                    st.info("Need Best Pos, Rating and Appearances columns across seasons to build the Best XI.")

                # ── Best Season XI ───────────────────────────────
                st.subheader("🥇 Best Season XI")
                st.caption("Best player per position in their single best season by rating.")

                if "Best Pos" in all_seasons_chron.columns and "Rating" in all_seasons_chron.columns:
                    best_season_xi = []
                    for pos in XI_POSITIONS:
                        candidates = all_seasons_chron[all_seasons_chron["Best Pos"] == pos].dropna(subset=["Rating"])
                        if not candidates.empty:
                            best = candidates.nlargest(1, "Rating").iloc[0]
                            best_season_xi.append({
                                "Position": pos,
                                "Player": best["Player"],
                                "Season": best.get("Season","—"),
                                "Rating": best["Rating"],
                                "Goals": int(best["Goals"]) if "Goals" in best and pd.notna(best.get("Goals")) else "—"
                            })
                    if best_season_xi:
                        st.dataframe(pd.DataFrame(best_season_xi), use_container_width=True, hide_index=True)

                st.divider()

                # ── Club-level opening narrative ──────────────────
                st.subheader("📖 The Story So Far")

                total_seasons = len(seasons_sorted)
                first_season  = seasons_sorted[0]
                latest_season = seasons_sorted[-1]

                opening = (
                    f"*Spanning {total_seasons} season{'s' if total_seasons != 1 else ''}, "
                    f"from {first_season} to {latest_season}.*\n\n"
                )
                st.markdown(opening)

                # ── Season-by-season narrative ─────────────────────
                for season in seasons_sorted:
                    s_df = pd.DataFrame(st.session_state.season_history[season])

                    story_parts = [f"### 📅 {season}"]

                    # Squad size and average rating
                    avg_r = s_df["Rating"].dropna().mean() if "Rating" in s_df.columns else None
                    if avg_r is not None:
                        if avg_r >= 7.1:
                            tone = "an excellent campaign across the board"
                        elif avg_r >= 6.8:
                            tone = "a solid, professional season"
                        else:
                            tone = "a difficult season with mixed performances"
                        story_parts.append(
                            f"The {season} season was {tone}, with the squad averaging a "
                            f"**{round(avg_r,2)} rating** across {len(s_df)} registered players."
                        )

                    # Top scorer narrative
                    if "Goals" in s_df.columns and "Player" in s_df.columns:
                        top_s = s_df.dropna(subset=["Goals"]).nlargest(1, "Goals")
                        if not top_s.empty and top_s.iloc[0]["Goals"] > 0:
                            ts = top_s.iloc[0]
                            xg_val = ts.get("xG", None)
                            if pd.notna(xg_val):
                                clin = ts["Goals"] - xg_val
                                if clin > 2:
                                    clin_phrase = f", finishing well ahead of an xG of {round(xg_val,1)} — a season of ruthless edge in front of goal"
                                elif clin < -2:
                                    clin_phrase = f", despite generating {round(xg_val,1)} xG — chances were created but not always taken"
                                else:
                                    clin_phrase = f", matching an xG of {round(xg_val,1)} almost perfectly"
                            else:
                                clin_phrase = ""
                            story_parts.append(
                                f"**{ts['Player']}** was the season's standout marksman, netting "
                                f"**{int(ts['Goals'])} goals**{clin_phrase}."
                            )

                    # Top assister
                    if "Assists" in s_df.columns and "Player" in s_df.columns:
                        top_a = s_df.dropna(subset=["Assists"]).nlargest(1, "Assists")
                        if not top_a.empty and top_a.iloc[0]["Assists"] > 0:
                            ta = top_a.iloc[0]
                            story_parts.append(
                                f"In the creative department, **{ta['Player']}** provided "
                                f"**{int(ta['Assists'])} assists**, pulling the strings behind the attack."
                            )

                    # Best rated
                    if "Rating" in s_df.columns and "Player" in s_df.columns:
                        top_r = s_df.dropna(subset=["Rating"]).nlargest(1, "Rating")
                        if not top_r.empty:
                            tr = top_r.iloc[0]
                            story_parts.append(
                                f"The Player of the Season honours go to **{tr['Player']}**, whose "
                                f"**{tr['Rating']}** average rating made them the most consistent performer of the campaign."
                            )

                    # Transfer activity for this season
                    if st.session_state.get("transfer_log"):
                        t_df_chron = pd.DataFrame(st.session_state.transfer_log)
                        if "season" in t_df_chron.columns:
                            s_transfers = t_df_chron[t_df_chron["season"] == season]
                            s_in  = s_transfers[s_transfers["direction"]=="IN"]  if "direction" in s_transfers.columns else pd.DataFrame()
                            s_out = s_transfers[s_transfers["direction"]=="OUT"] if "direction" in s_transfers.columns else pd.DataFrame()

                            if not s_in.empty:
                                arrivals_names = s_in["player"].tolist()
                                if len(arrivals_names) == 1:
                                    arrival_text = f"**{arrivals_names[0]}** arrived at the club"
                                elif len(arrivals_names) <= 3:
                                    arrival_text = f"the squad welcomed **{', '.join(arrivals_names[:-1])} and {arrivals_names[-1]}**"
                                else:
                                    arrival_text = f"the squad welcomed **{len(arrivals_names)} new arrivals**, including {', '.join(arrivals_names[:2])}"

                                # Biggest fee
                                def _fee_to_m(f):
                                    s = str(f).upper().replace("£","").replace(",","").strip()
                                    if "FREE" in s or "—" in s: return 0
                                    try:
                                        if "M" in s: return float(s.replace("M","").replace("+",""))
                                        if "K" in s: return float(s.replace("K","").replace("+",""))/1000
                                        return float(s)/1_000_000
                                    except: return 0
                                s_in_copy = s_in.copy()
                                s_in_copy["fee_m"] = s_in_copy["fee"].apply(_fee_to_m) if "fee" in s_in_copy.columns else 0
                                biggest = s_in_copy.nlargest(1,"fee_m") if not s_in_copy.empty else pd.DataFrame()
                                fee_text = ""
                                if not biggest.empty and biggest.iloc[0]["fee_m"] > 0:
                                    fee_text = (f" The headline signing was **{biggest.iloc[0]['player']}** "
                                                f"for a fee of **{biggest.iloc[0]['fee']}**.")

                                story_parts.append(f"On the transfer front, {arrival_text}.{fee_text}")

                            if not s_out.empty:
                                departure_names = s_out["player"].tolist()
                                if len(departure_names) == 1:
                                    dep_text = f"**{departure_names[0]}** departed the club"
                                else:
                                    dep_text = f"**{len(departure_names)} players** left the club, including {', '.join(departure_names[:2])}"
                                story_parts.append(f"Meanwhile, {dep_text}.")

                    with st.expander(f"📅 {season}", expanded=(season == latest_season)):
                        st.markdown("\n\n".join(story_parts))

                st.divider()

                # ── Career legacy section ──────────────────────────
                st.subheader("🏛️ Legacy Players")
                st.caption("Players who have featured in 3 or more seasons — the backbone of the club's identity.")

                if "Player" in all_seasons_chron.columns:
                    player_season_counts = all_seasons_chron.groupby("Player")["Season"].nunique().sort_values(ascending=False)
                    legacy_players = player_season_counts[player_season_counts >= 3]

                    if legacy_players.empty:
                        st.info("No players have featured in 3+ seasons yet. Keep building the archive!")
                    else:
                        for player_name, n_seasons in legacy_players.items():
                            p_seasons = all_seasons_chron[all_seasons_chron["Player"] == player_name]
                            avg_rating_p = p_seasons["Rating"].dropna().mean() if "Rating" in p_seasons.columns else None
                            total_goals_p = int(p_seasons["Goals"].fillna(0).sum()) if "Goals" in p_seasons.columns else 0
                            total_apps_p = int(p_seasons["Apps_numeric"].fillna(0).sum()) if "Apps_numeric" in p_seasons.columns else 0
                            best_season_row = p_seasons.dropna(subset=["Rating"]).nlargest(1,"Rating") if "Rating" in p_seasons.columns else pd.DataFrame()
                            best_season_label = best_season_row.iloc[0]["Season"] if not best_season_row.empty else "—"
                            best_season_rating = best_season_row.iloc[0]["Rating"] if not best_season_row.empty else "—"

                            legacy_text = (
                                f"**{player_name}** has been a fixture of the squad across **{n_seasons} seasons**, "
                                f"making **{total_apps_p} appearances** and scoring **{total_goals_p} goals**. "
                            )
                            if avg_rating_p is not None:
                                if avg_rating_p >= 7.1:
                                    legacy_text += f"With a career average rating of **{round(avg_rating_p,2)}**, they rank among the club's all-time greats. "
                                elif avg_rating_p >= 6.8:
                                    legacy_text += f"A career average rating of **{round(avg_rating_p,2)}** reflects a dependable, professional servant of the club. "
                                else:
                                    legacy_text += f"A career average rating of **{round(avg_rating_p,2)}** tells the story of a squad rotation player who never quite nailed down a starting spot. "
                            legacy_text += f"Their peak came in **{best_season_label}**, with a season rating of **{best_season_rating}**."

                            with st.expander(f"⭐ {player_name} — {n_seasons} seasons"):
                                st.markdown(legacy_text)

        # ════════════════════════════════════════════════════════
        # TAB 7 — MONEYBALL SCOUTING (external player database)
        # ════════════════════════════════════════════════════════
        with tab7:
            st.subheader("🕵️ Moneyball Scouting")
            st.markdown(
                "Upload a player search export from FM26 (Player Database / Recruitment search) "
                "to find transfer targets that match your squad's system, and compare them against "
                "your current players."
            )

            scout_file = st.file_uploader(
                "Upload Scouting Database (CSV or Excel)",
                type=["csv","xlsx","xls"],
                key="scout_db_file"
            )

            if scout_file:
                try:
                    ext_s = scout_file.name.split(".")[-1].lower()
                    if ext_s == "csv":
                        sample_s = scout_file.read(2048).decode("utf-8", errors="ignore")
                        scout_file.seek(0)
                        sep_s = ";" if ";" in sample_s else ","
                        scout_df = pd.read_csv(scout_file, sep=sep_s, encoding="utf-8-sig")
                    else:
                        scout_df = pd.read_excel(scout_file)

                    scout_df.columns = [c.lstrip("\ufeff").strip() for c in scout_df.columns]

                    # Clean numeric columns the same way as the squad importer
                    scout_numeric_cols = [c for c in scout_df.columns if c not in
                                           ["Inf","Player","Club","Transfer Value","Division","Based In","Best Pos","Rating",
                                            "Wage","Expires","Contract Expires","Contract","Contract Start Date"]]
                    for col in scout_numeric_cols:
                        scout_df[col] = pd.to_numeric(
                            scout_df[col].astype(str).str.replace(",",".",regex=False).str.replace("%","",regex=False).str.strip(),
                            errors="coerce"
                        )
                    if "Rating" in scout_df.columns:
                        scout_df["Rating"] = pd.to_numeric(
                            scout_df["Rating"].astype(str).str.replace(",",".",regex=False).str.strip(),
                            errors="coerce"
                        )
                    if "Age" in scout_df.columns:
                        scout_df["Age"] = pd.to_numeric(scout_df["Age"], errors="coerce")

                    # Parse Transfer Value range -> midpoint £M
                    def parse_value_range(val):
                        s = str(val).upper().replace("£","").replace(",","").strip()
                        if s in ["-","NAN","NONE",""]:
                            return None
                        def to_m(x):
                            x = x.strip()
                            if x.endswith("M"): return float(x[:-1])
                            if x.endswith("K"): return float(x[:-1]) / 1000
                            try: return float(x)
                            except: return None
                        if "-" in s:
                            parts = s.split("-")
                            lo, hi = to_m(parts[0]), to_m(parts[1])
                            if lo is not None and hi is not None:
                                return round((lo + hi) / 2, 2)
                            return lo or hi
                        return to_m(s)

                    if "Transfer Value" in scout_df.columns:
                        scout_df["Value (£M est.)"] = scout_df["Transfer Value"].apply(parse_value_range)

                    # Parse Wage if present
                    for wage_col in ["Wage", "Salary"]:
                        if wage_col in scout_df.columns:
                            def parse_wage_scout(val):
                                s = str(val).upper().replace("£","").replace(",","").replace(" ","").strip()
                                if s in ("","NAN","NONE","-","—"): return None
                                try:
                                    if "P/W" in s or "PW" in s:
                                        s = s.replace("P/W","").replace("PW","")
                                        if "K" in s: return float(s.replace("K","")) * 1000
                                        if "M" in s: return float(s.replace("M","")) * 1_000_000 / 52
                                        return float(s)
                                    elif "P/A" in s or "PA" in s:
                                        s = s.replace("P/A","").replace("PA","")
                                        if "M" in s: return float(s.replace("M","")) * 1_000_000 / 52
                                        if "K" in s: return float(s.replace("K","")) * 1000 / 52
                                        return float(s) / 52
                                    else:
                                        if "K" in s: return float(s.replace("K","")) * 1000
                                        if "M" in s: return float(s.replace("M","")) * 1_000_000 / 52
                                        return float(s)
                                except: return None
                            scout_df["Wage (£/wk)"] = scout_df[wage_col].apply(parse_wage_scout)
                            break

                    # Parse Contract Expiry if present
                    for exp_col in ["Expires", "Contract Expires", "Contract"]:
                        if exp_col in scout_df.columns:
                            scout_df["Contract Expiry"] = pd.to_datetime(scout_df[exp_col], errors="coerce", dayfirst=True)
                            scout_df["Expires Year"] = scout_df["Contract Expiry"].dt.year
                            break

                    st.success(f"✅ Loaded {len(scout_df)} players from scouting database.")
                    st.session_state["scout_df_cache"] = scout_df.copy()

                    # ── FILTERS ────────────────────────────────────
                    st.subheader("🔍 Filters")

                    if "Minutes" in scout_df.columns:
                        scout_df["Minutes"] = pd.to_numeric(
                            scout_df["Minutes"].astype(str).str.replace(",","",regex=False),
                            errors="coerce"
                        )

                    f1, f2, f3, f4, f5 = st.columns(5)

                    with f1:
                        pos_opts_s = sorted(scout_df["Best Pos"].dropna().unique().tolist()) if "Best Pos" in scout_df.columns else []
                        sel_pos_s = st.multiselect("Position", pos_opts_s, key="scout_pos")

                    with f2:
                        if "Age" in scout_df.columns:
                            age_min, age_max = int(scout_df["Age"].min()), int(scout_df["Age"].max())
                            sel_age_s = st.slider("Age Range", age_min, age_max, (age_min, min(age_max,30)), key="scout_age")
                        else:
                            sel_age_s = None

                    with f3:
                        if "Value (£M est.)" in scout_df.columns:
                            val_data = scout_df["Value (£M est.)"].dropna()
                            if not val_data.empty:
                                v_min, v_max = float(val_data.min()), float(val_data.max())
                                sel_val_s = st.slider("Max Value (£M)", v_min, v_max, min(v_max, 50.0), key="scout_val")
                            else:
                                sel_val_s = None
                        else:
                            sel_val_s = None

                    with f4:
                        div_opts_s = sorted(scout_df["Division"].dropna().unique().tolist()) if "Division" in scout_df.columns else []
                        sel_div_s = st.multiselect("Division", div_opts_s, key="scout_div")

                    with f5:
                        if "Minutes" in scout_df.columns and scout_df["Minutes"].notna().any():
                            min_mins_max = int(scout_df["Minutes"].max())
                            sel_mins_s = st.slider(
                                "Min Minutes Played", 0, min_mins_max, 500,
                                step=50, key="scout_mins",
                                help="Filters out players with too few minutes for the stats to be meaningful — e.g. someone with 60 minutes can show misleadingly extreme per-90 numbers."
                            )
                        else:
                            sel_mins_s = None

                    # Wage filter
                    sel_wage_s = None
                    if "Wage (£/wk)" in scout_df.columns and scout_df["Wage (£/wk)"].notna().any():
                        w_max = int(scout_df["Wage (£/wk)"].dropna().max())
                        sel_wage_s = st.slider(
                            "Max Weekly Wage (£)", 0, w_max, w_max,
                            step=500, key="scout_wage",
                            help="Filter by maximum weekly wage — useful when scouting within a budget."
                        )

                    # Contract expiry filter
                    sel_exp_year = None
                    if "Expires Year" in scout_df.columns and scout_df["Expires Year"].notna().any():
                        exp_years = sorted(scout_df["Expires Year"].dropna().unique().astype(int).tolist())
                        sel_exp_year = st.selectbox(
                            "Contract Expires By",
                            ["Any"] + [str(y) for y in exp_years],
                            key="scout_exp_year",
                            help="Find players out of contract soon — potential cut-price or free agent targets."
                        )

                    # Apply filters
                    filtered_scout = scout_df.copy()
                    if sel_pos_s:
                        filtered_scout = filtered_scout[filtered_scout["Best Pos"].isin(sel_pos_s)]
                    if sel_age_s:
                        filtered_scout = filtered_scout[
                            (filtered_scout["Age"] >= sel_age_s[0]) & (filtered_scout["Age"] <= sel_age_s[1])
                        ]
                    if sel_val_s is not None:
                        filtered_scout = filtered_scout[
                            filtered_scout["Value (£M est.)"].isna() | (filtered_scout["Value (£M est.)"] <= sel_val_s)
                        ]
                    if sel_div_s:
                        filtered_scout = filtered_scout[filtered_scout["Division"].isin(sel_div_s)]
                    if sel_mins_s is not None:
                        filtered_scout = filtered_scout[filtered_scout["Minutes"].fillna(0) >= sel_mins_s]
                    if sel_wage_s is not None and "Wage (£/wk)" in filtered_scout.columns:
                        filtered_scout = filtered_scout[
                            filtered_scout["Wage (£/wk)"].isna() | (filtered_scout["Wage (£/wk)"] <= sel_wage_s)
                        ]
                    if sel_exp_year and sel_exp_year != "Any" and "Expires Year" in filtered_scout.columns:
                        filtered_scout = filtered_scout[
                            filtered_scout["Expires Year"].isna() | (filtered_scout["Expires Year"] <= int(sel_exp_year))
                        ]

                    # Exclude players already in squad (by name match)
                    if "Player" in filtered_scout.columns and "Player" in df.columns:
                        squad_names = set(df["Player"].dropna().tolist())
                        filtered_scout = filtered_scout[~filtered_scout["Player"].isin(squad_names)]

                    st.caption(f"{len(filtered_scout)} players match your filters (squad players excluded).")

                    if filtered_scout.empty:
                        st.warning("No players match these filters. Try widening the criteria.")
                    else:
                        st.divider()

                        # ── SCATTER EXPLORER (FM26 Statistics-style scatter) ──
                        st.subheader("📊 Scatter Explorer")
                        st.markdown(
                            "Plot any two stats against each other across the filtered pool — same idea as the "
                            "in-game Statistics → Scatter view (e.g. xG per 90 vs Goals per 90 to spot "
                            "over/under-performers relative to their chances)."
                        )

                        scout_numeric_available = sorted([
                            c for c in filtered_scout.columns
                            if pd.api.types.is_numeric_dtype(filtered_scout[c])
                            and filtered_scout[c].notna().any()
                        ])

                        if len(scout_numeric_available) < 2:
                            st.info("Not enough numeric columns in this export to build a scatter plot.")
                        else:
                            sx1, sx2, sx3, sx4 = st.columns(4)

                            def _pick_default(options, preferred, fallback_idx=0):
                                for p in preferred:
                                    if p in options:
                                        return options.index(p)
                                return fallback_idx

                            x_s_idx = _pick_default(scout_numeric_available, ["xG per 90", "xG/90", "xG"])
                            y_s_idx = _pick_default(scout_numeric_available, ["Goals per 90", "Gls/90", "Goals"], 1)
                            c_s_idx = _pick_default(scout_numeric_available, ["Rating"])

                            x_s = sx1.selectbox("X Axis", scout_numeric_available, index=x_s_idx, key="scatter_scout_x")
                            y_s = sx2.selectbox("Y Axis", scout_numeric_available, index=min(y_s_idx, len(scout_numeric_available)-1), key="scatter_scout_y")
                            c_s = sx3.selectbox("Colour By", scout_numeric_available, index=min(c_s_idx, len(scout_numeric_available)-1), key="scatter_scout_c")
                            diag_s = sx4.checkbox("Show diagonal reference line", value=True, key="scatter_scout_diag")

                            scatter_pool = filtered_scout.dropna(subset=[x_s, y_s])

                            if scatter_pool.empty:
                                st.info("No players have data for both selected axes.")
                            else:
                                hover_cols_s = {c: True for c in ["Club", "Division", "Best Pos", "Age", "Minutes", "Rating"] if c in scatter_pool.columns}
                                fig_scout_scatter = px.scatter(
                                    scatter_pool, x=x_s, y=y_s,
                                    color=c_s,
                                    hover_name="Player" if "Player" in scatter_pool.columns else None,
                                    hover_data=hover_cols_s,
                                    color_continuous_scale=theme["chart_scale"],
                                    template="plotly_dark",
                                    title=f"{y_s} vs {x_s}",
                                    height=550
                                )
                                fig_scout_scatter.update_traces(marker=dict(size=10, opacity=0.85))

                                if diag_s:
                                    min_v_s = min(scatter_pool[x_s].min(), scatter_pool[y_s].min())
                                    max_v_s = max(scatter_pool[x_s].max(), scatter_pool[y_s].max())
                                    fig_scout_scatter.add_shape(
                                        type="line", x0=min_v_s, y0=min_v_s, x1=max_v_s, y1=max_v_s,
                                        line=dict(color="grey", dash="dot", width=1)
                                    )

                                st.plotly_chart(fig_scout_scatter, use_container_width=True)
                                st.caption(
                                    f"{len(scatter_pool)} players plotted. Players above the dotted line are "
                                    f"outperforming {x_s} relative to {y_s} (and vice versa below it) when both "
                                    "axes are on comparable per-90 scales."
                                )

                        st.divider()

                        # ── DATA-LED SCOUTING (MONEYBALL BENCHMARKS) ──
                        st.subheader("💰 Data-Led Scouting — Moneyball Benchmarks")
                        st.markdown(
                            "Based on community-sourced FM 'Good / OK / Poor' benchmark tables. "
                            "Each player is scored 0-100 per metric against real statistical thresholds — "
                            "not just compared to your current squad. Find players with elite underlying "
                            "data that the market hasn't priced in yet."
                        )

                        if not sel_pos_s:
                            st.info("Select one or more positions in the filters above to use benchmark scoring.")
                        else:
                            # Find applicable benchmark roles for selected positions
                            applicable_roles = [
                                role for role, cfg in FM_BENCHMARKS.items()
                                if any(p in cfg["applies_to"] for p in sel_pos_s)
                            ]

                            if not applicable_roles:
                                st.info(f"No benchmark profile available yet for {', '.join(sel_pos_s)}.")
                            else:
                                bench_role = st.selectbox(
                                    "Benchmark Role Profile",
                                    applicable_roles,
                                    key="bench_role_select"
                                )
                                bench_metrics = FM_BENCHMARKS[bench_role]["metrics"]
                                available_bench_metrics = {
                                    m: th for m, th in bench_metrics.items() if m in filtered_scout.columns
                                }

                                # ── Custom Metrics ─────────────────────────
                                with st.expander("➕ Add custom metrics for scoring"):
                                    st.markdown(
                                        "Pull in any other numeric column from your export — e.g. **xG/Shot**, "
                                        "**Dribbled Past/90**, **Poss Won/90**, **NP-xG Overperformance** — and it'll "
                                        "be scored 0-100 alongside this role's benchmark metrics. Since community "
                                        "Good/OK/Poor tables don't exist for every stat, thresholds are auto-set from "
                                        "the **80th/50th/20th percentile of your currently filtered player pool** — "
                                        "you can override them manually below."
                                    )

                                    exclude_meta_cols = {
                                        "Player","Club","Division","Based In","Best Pos","Age","Minutes",
                                        "Value (£M est.)","Wage (£/wk)","Expires Year","Inf","Transfer Value",
                                        "Wage","Salary","Expires","Contract Expires","Contract",
                                        "Contract Start Date","Contract Expiry"
                                    }
                                    custom_metric_candidates = sorted([
                                        c for c in filtered_scout.columns
                                        if c not in bench_metrics and c not in exclude_meta_cols
                                    ])

                                    sel_custom_metrics = st.multiselect(
                                        "Columns to add",
                                        custom_metric_candidates,
                                        key="custom_bench_metrics"
                                    )

                                    custom_metric_config = {}
                                    for cm in sel_custom_metrics:
                                        cm_series = pd.to_numeric(
                                            filtered_scout[cm].astype(str).str.replace("%","",regex=False).str.replace(",",".",regex=False),
                                            errors="coerce"
                                        )
                                        if cm_series.notna().sum() < 3:
                                            st.caption(f"⚠️ '{cm}' doesn't have enough numeric data in this pool to set thresholds — skipped.")
                                            continue

                                        cc1, cc2, cc3, cc4 = st.columns([1.3, 1, 1, 1])
                                        with cc1:
                                            higher_better = st.checkbox(
                                                f"Higher is better — {cm}", value=True, key=f"cm_dir_{cm}",
                                                help="Untick for stats where a lower number is the good outcome, e.g. Dribbled Past/90 or Fouls/90."
                                            )
                                        if higher_better:
                                            default_good = round(float(cm_series.quantile(0.80)), 2)
                                            default_ok   = round(float(cm_series.quantile(0.50)), 2)
                                            default_poor = round(float(cm_series.quantile(0.20)), 2)
                                        else:
                                            default_good = round(float(cm_series.quantile(0.20)), 2)
                                            default_ok   = round(float(cm_series.quantile(0.50)), 2)
                                            default_poor = round(float(cm_series.quantile(0.80)), 2)

                                        with cc2:
                                            good_v = st.number_input("Good", value=default_good, key=f"cm_good_{cm}", format="%.2f")
                                        with cc3:
                                            ok_v = st.number_input("OK", value=default_ok, key=f"cm_ok_{cm}", format="%.2f")
                                        with cc4:
                                            poor_v = st.number_input("Poor", value=default_poor, key=f"cm_poor_{cm}", format="%.2f")

                                        custom_metric_config[cm] = (good_v, ok_v, poor_v)

                                    if custom_metric_config:
                                        available_bench_metrics = {**available_bench_metrics, **custom_metric_config}
                                        st.caption(f"✅ Added: {', '.join(custom_metric_config.keys())}")

                                if not available_bench_metrics:
                                    st.warning("None of this role's benchmark metrics are present in your scouting export.")
                                else:
                                    missing = set(bench_metrics) - set(available_bench_metrics)
                                    if missing:
                                        st.caption(f"⚠️ Not available in export, skipped: {', '.join(missing)}")

                                    # Compute benchmark scores
                                    bench_pool = filtered_scout.copy()
                                    for m in available_bench_metrics:
                                        bench_pool[m] = pd.to_numeric(
                                            bench_pool[m].astype(str).str.replace("%","",regex=False).str.replace(",",".",regex=False),
                                            errors="coerce"
                                        )

                                    score_cols = []
                                    for m, (good, ok, poor) in available_bench_metrics.items():
                                        score_col = f"_score_{m}"
                                        bench_pool[score_col] = bench_pool[m].apply(lambda v: benchmark_score(v, good, ok, poor))
                                        score_cols.append(score_col)

                                    bench_pool["Data Score %"] = bench_pool[score_cols].mean(axis=1, skipna=True).round(1)

                                    # ── League Strength Weighting ─────
                                    apply_league_weight = st.checkbox(
                                        "🌍 Adjust for league strength (experimental)",
                                        value=False,
                                        help=(
                                            "A 'Good' stat line in a weaker league doesn't carry the same weight as in a top-5 league. "
                                            "When enabled, Data Score is multiplied by a league strength factor "
                                            "(1.00 = Premier League/LaLiga/Serie A/Bundesliga level, scaling down for weaker leagues). "
                                            "⚠️ The 'Division' column in FM26 exports is sometimes inconsistent with a player's actual "
                                            "club (e.g. reserve teams or loan records can show the parent league). "
                                            "Always cross-check the Club and Division columns in the results table before trusting "
                                            "the adjusted score for a specific player."
                                        ),
                                        key="apply_league_weight"
                                    )
                                    if apply_league_weight:
                                        st.caption(
                                            "⚠️ Division data can be unreliable for some players (loanees, reserve teams). "
                                            "Verify Club vs Division in the table below before acting on the adjusted score."
                                        )

                                    if "Division" in bench_pool.columns:
                                        if "Based In" in bench_pool.columns:
                                            bench_pool["League Weight"] = bench_pool.apply(
                                                lambda r: league_weight(r.get("Division"), r.get("Based In")), axis=1
                                            )
                                        else:
                                            bench_pool["League Weight"] = bench_pool["Division"].apply(league_weight)
                                    else:
                                        bench_pool["League Weight"] = LEAGUE_WEIGHTS["_default"]

                                    if apply_league_weight:
                                        bench_pool["Adj. Data Score %"] = (bench_pool["Data Score %"] * bench_pool["League Weight"]).round(1)
                                        score_for_sort = "Adj. Data Score %"
                                    else:
                                        bench_pool["Adj. Data Score %"] = bench_pool["Data Score %"]
                                        score_for_sort = "Data Score %"

                                    # Value Ratio — Score per £M (higher = more value for money)
                                    if "Value (£M est.)" in bench_pool.columns:
                                        bench_pool["Value Ratio"] = (
                                            bench_pool[score_for_sort] / (bench_pool["Value (£M est.)"].fillna(0) + 1)
                                        ).round(1)
                                    else:
                                        bench_pool["Value Ratio"] = None

                                    # ── Recruitment Score ─────────────────────────────
                                    # Composite: Data Score (40%) + Value Ratio (25%) +
                                    # Age Curve (20%, peaks at ≤24) + Minutes (15%)
                                    def _rec_score(row):
                                        age_v  = row.get("Age")
                                        mins_v = float(row.get("Minutes") or 0)
                                        data_v = float(row.get(score_for_sort) or 50)
                                        vr_v   = float(row.get("Value Ratio") or 0) if pd.notna(row.get("Value Ratio")) else 0

                                        # Age curve for recruits — high for young players, drops after 28
                                        if pd.notna(age_v):
                                            a = float(age_v)
                                            if a <= 24:   age_sc = 100
                                            elif a <= 28: age_sc = 100 - (a - 24) * 9
                                            elif a <= 32: age_sc = max(0, 64 - (a - 28) * 10)
                                            else:         age_sc = max(0, 24 - (a - 32) * 6)
                                        else:
                                            age_sc = 50

                                        vr_sc   = min(100, vr_v * 8)          # normalise Value Ratio
                                        mins_sc = min(100, mins_v / 20.0)     # 2000 mins → 100

                                        return round(max(0, min(100,
                                            data_v * 0.40 +
                                            vr_sc  * 0.25 +
                                            age_sc * 0.20 +
                                            mins_sc * 0.15
                                        )), 1)

                                    bench_pool["Recruitment Score"] = bench_pool.apply(_rec_score, axis=1)

                                    bench_pool = bench_pool.dropna(subset=["Data Score %"])

                                    if bench_pool.empty:
                                        st.warning("No players have enough data for these benchmark metrics.")
                                    else:
                                        sort_choice = st.radio(
                                            "Sort by",
                                            [
                                                "Recruitment Score (composite)",
                                                f"{score_for_sort} (best raw data)",
                                                "Value Ratio (best value for money)",
                                            ],
                                            horizontal=True, key="bench_sort"
                                        )
                                        if "Recruitment Score" in sort_choice:
                                            sort_col = "Recruitment Score"
                                        elif "Value Ratio" in sort_choice:
                                            sort_col = "Value Ratio"
                                        else:
                                            sort_col = score_for_sort

                                        top_n_bench = st.slider("Show top N", 5, 50, 15, key="bench_topn")

                                        bench_display = bench_pool.sort_values(sort_col, ascending=False).head(top_n_bench)

                                        # Build display table with Good/OK/Poor tags per metric
                                        display_rows = []
                                        for _, row in bench_display.iterrows():
                                            division_val = row.get("Division","—")
                                            based_in_val = row.get("Based In", None)
                                            expected_country = DIVISION_HOME_COUNTRY.get(str(division_val).strip()) if pd.notna(division_val) else None
                                            mismatch = (
                                                expected_country is not None
                                                and pd.notna(based_in_val)
                                                and str(based_in_val).strip() != expected_country
                                            )
                                            division_display = f"⚠️ {division_val}" if mismatch else division_val

                                            rec = {
                                                "Player": row.get("Player","—"),
                                                "Club": row.get("Club","—"),
                                                "Division": division_display,
                                                "Country": based_in_val if pd.notna(based_in_val) else "—",
                                                "Age": row.get("Age","—"),
                                                "Mins": int(row["Minutes"]) if pd.notna(row.get("Minutes")) else "—",
                                                "Value (£M)": row.get("Value (£M est.)","—"),
                                                "Data Score %": row["Data Score %"],
                                            }
                                            if apply_league_weight:
                                                rec["League Wt"] = row["League Weight"]
                                                rec["Adj. Score %"] = row["Adj. Data Score %"]
                                            rec["Recruitment Score"] = row.get("Recruitment Score", "—")
                                            rec["Value Ratio"]       = row.get("Value Ratio", "—")
                                            for m in available_bench_metrics:
                                                val = row.get(m, None)
                                                score = row.get(f"_score_{m}", None)
                                                tag = benchmark_label(score)
                                                val_str = f"{val:.2f}" if isinstance(val,(int,float)) and pd.notna(val) else "—"
                                                rec[m] = f"{val_str} {tag}"
                                            display_rows.append(rec)

                                        bench_table = pd.DataFrame(display_rows)
                                        st.dataframe(bench_table, use_container_width=True, hide_index=True)

                                        # ── 💎 Hidden Gems — Recruitment Score powered ──
                                        if "Recruitment Score" in bench_pool.columns:
                                            val_median = (
                                                bench_pool["Value (£M est.)"].dropna().quantile(0.40)
                                                if "Value (£M est.)" in bench_pool.columns and not bench_pool["Value (£M est.)"].dropna().empty
                                                else 999
                                            )
                                            gems = bench_pool[
                                                (bench_pool["Recruitment Score"] >= 60) &
                                                (bench_pool["Value (£M est.)"].fillna(999) <= val_median)
                                            ].sort_values("Recruitment Score", ascending=False).head(6)

                                            if not gems.empty:
                                                st.markdown("#### 💎 Hidden Gems — High Recruitment Score, Below-Median Price")
                                                st.caption(
                                                    "Recruitment Score ≥ 60 + estimated value in the bottom 40% of the pool. "
                                                    "Strong underlying data at a price the market may not have caught up with yet."
                                                )
                                                gem_text = ""
                                                for _, g in gems.iterrows():
                                                    val_str  = f"£{g['Value (£M est.)']:.1f}M" if pd.notna(g.get("Value (£M est.)")) else "Value unknown"
                                                    rec_str  = f"{g['Recruitment Score']:.0f}"
                                                    data_str = f"{g[score_for_sort]:.0f}%"
                                                    age_str  = str(int(g["Age"])) if pd.notna(g.get("Age")) else "?"
                                                    league_str = f" · {g.get('Division','—')}" if apply_league_weight else ""
                                                    vr_str   = f" · VFM: {g['Value Ratio']:.1f}" if pd.notna(g.get("Value Ratio")) else ""
                                                    gem_text += (
                                                        f"<div style='padding:10px 14px;margin:5px 0;"
                                                        f"background:{theme['primary']}1a;"
                                                        f"border-left:4px solid {theme['primary']};border-radius:5px;"
                                                        f"display:flex;justify-content:space-between;align-items:center;'>"
                                                        f"<div>"
                                                        f"<b style='font-size:13px'>{g['Player']}</b> "
                                                        f"<span style='color:#aaa;font-size:11px'>"
                                                        f"({g.get('Club','—')}, Age {age_str}{league_str})</span>"
                                                        f"</div>"
                                                        f"<div style='text-align:right;font-size:12px'>"
                                                        f"<span style='color:{theme['primary']};font-weight:800;font-size:15px'>{rec_str}</span>"
                                                        f"<span style='color:#aaa'> / 100 &nbsp;·&nbsp; "
                                                        f"{val_str}{vr_str} &nbsp;·&nbsp; Data {data_str}</span>"
                                                        f"</div>"
                                                        f"</div>"
                                                    )
                                                st.markdown(gem_text, unsafe_allow_html=True)

                                        # Benchmark radar for a selected player
                                        st.markdown("##### Inspect a Player's Benchmark Profile")
                                        bench_player = st.selectbox(
                                            "Player",
                                            bench_display["Player"].tolist() if "Player" in bench_display.columns else [],
                                            key="bench_player_select"
                                        )
                                        if bench_player:
                                            p_bench_row = bench_pool[bench_pool["Player"]==bench_player].iloc[0]
                                            metric_names = list(available_bench_metrics.keys())
                                            scores_b = [p_bench_row[f"_score_{m}"] for m in metric_names]

                                            fig_bench = go.Figure()
                                            fig_bench.add_trace(go.Scatterpolar(
                                                r=scores_b + [scores_b[0]],
                                                theta=metric_names + [metric_names[0]],
                                                fill="toself",
                                                fillcolor=hex_to_rgba(theme["primary"], 0.25),
                                                line=dict(color=theme["primary"], width=2),
                                                name=bench_player
                                            ))
                                            # Reference rings at 50 (OK threshold)
                                            fig_bench.add_trace(go.Scatterpolar(
                                                r=[50]*(len(metric_names)+1),
                                                theta=metric_names + [metric_names[0]],
                                                line=dict(color="grey", dash="dot", width=1),
                                                name="OK threshold"
                                            ))
                                            fig_bench.update_layout(
                                                polar=dict(
                                                    bgcolor="#1a1f2e",
                                                    radialaxis=dict(visible=True, range=[0,100], gridcolor="#333", tickfont=dict(color="grey", size=9)),
                                                    angularaxis=dict(gridcolor="#444", tickfont=dict(color="white", size=11))
                                                ),
                                                paper_bgcolor="#0d1117", font=dict(color="white"),
                                                title=dict(text=f"{bench_player} — {bench_role} Benchmark Profile",
                                                          font=dict(color=theme["primary"], size=14)),
                                                height=450,
                                                legend=dict(bgcolor="#1a1f2e", font=dict(color="white"))
                                            )
                                            st.plotly_chart(fig_bench, use_container_width=True)

                        st.divider()

                        # ── SYSTEM FIT SCORING ──────────────────────
                        st.subheader("⚡ System Fit Scoring")
                        st.caption(
                            "Scores each scouted player against your squad's top performers in the same position, "
                            "using the same profile-matching logic used across the hub."
                        )

                        # Position-based default metric profiles
                        def get_profile_metrics_for_pos(pos):
                            if pos == "GK":
                                return [c for c in ["Sv %","xSv %","Ps C/90","xGP/90"] if c in scout_df.columns and c in played_df.columns]
                            elif pos in ["D (C)","D (R)","D (L)","WB (R)","WB (L)"]:
                                return [c for c in ["Tck/90","Int/90","Hdrs W/90","Ps C/90","Pres C/90"] if c in scout_df.columns and c in played_df.columns]
                            elif pos in ["DM","M (C)"]:
                                return [c for c in ["Ps C/90","Tck/90","Int/90","Pres C/90","OP-KP/90"] if c in scout_df.columns and c in played_df.columns]
                            elif pos in ["AM (C)","AM (R)","AM (L)"]:
                                return [c for c in ["OP-KP/90","Ch C/90","Drb/90","Goals per 90 minutes","Sprints/90"] if c in scout_df.columns and c in played_df.columns]
                            else:
                                return [c for c in ["Goals per 90 minutes","xG/90","Conv %","ShT/90","Drb/90"] if c in scout_df.columns and c in played_df.columns]

                        # Build squad profiles per position (top 3 by rating) once
                        squad_profiles = {}
                        if "Best Pos" in df.columns:
                            for pos in df["Best Pos"].dropna().unique():
                                pool = played_df[played_df["Best Pos"]==pos]
                                if "Rating" in pool.columns:
                                    pool = pool.dropna(subset=["Rating"]).nlargest(3,"Rating")
                                if not pool.empty:
                                    squad_profiles[pos] = pool

                        fit_scores = []
                        for _, srow in filtered_scout.iterrows():
                            pos = srow.get("Best Pos","")
                            metrics = get_profile_metrics_for_pos(pos)
                            if not metrics or pos not in squad_profiles:
                                fit_scores.append(None)
                                continue
                            pool = squad_profiles[pos]
                            total_match, n_valid = 0, 0
                            for m in metrics:
                                if m not in srow.index or pd.isna(srow[m]):
                                    continue
                                # Use 'Goals per 90 minutes' as proxy if Goals not directly in scout file
                                squad_col = m
                                if squad_col not in played_df.columns:
                                    continue
                                squad_min, squad_max = played_df[squad_col].min(), played_df[squad_col].max()
                                if squad_max <= squad_min:
                                    continue
                                target_norm = (srow[m] - squad_min) / (squad_max - squad_min) * 100
                                target_norm = max(0, min(100, target_norm))
                                profile_avg = pool[squad_col].mean()
                                profile_norm = (profile_avg - squad_min) / (squad_max - squad_min) * 100
                                profile_norm = max(0, min(100, profile_norm))
                                match = 100 - abs(target_norm - profile_norm)
                                total_match += max(0, match)
                                n_valid += 1
                            fit_scores.append(round(total_match/n_valid,1) if n_valid > 0 else None)

                        filtered_scout = filtered_scout.copy()
                        filtered_scout["System Fit %"] = fit_scores

                        # ── RESULTS TABLE ────────────────────────────
                        display_cols_s = [c for c in [
                            "Player","Age","Club","Division","Best Pos","Rating","Minutes","Wage (£/wk)","Expires Year",
                            "Transfer Value","Value (£M est.)","System Fit %"
                        ] if c in filtered_scout.columns]

                        sort_options = ["System Fit %","Rating","Value (£M est.)","Age"]
                        sort_options = [c for c in sort_options if c in filtered_scout.columns]
                        sort_by = st.selectbox("Sort by", sort_options, key="scout_sort")
                        ascending = st.checkbox("Ascending", value=(sort_by=="Value (£M est.)" or sort_by=="Age"), key="scout_asc")

                        result_df = filtered_scout[display_cols_s].dropna(subset=["System Fit %"]) if "System Fit %" in filtered_scout.columns else filtered_scout[display_cols_s]
                        result_df = result_df.sort_values(sort_by, ascending=ascending, na_position="last")

                        st.dataframe(result_df.head(50), use_container_width=True, hide_index=True)
                        st.caption(f"Showing top 50 of {len(result_df)} results.")

                        # ── Quick Player Report card for selected scouted player ──
                        st.divider()
                        st.subheader("📄 Scout Target Report")
                        _s_names = result_df["Player"].dropna().tolist() if "Player" in result_df.columns else []
                        if _s_names:
                            _s_sel = st.selectbox("Select target to view report", _s_names, key="scout_quick_sel")
                            _s_row = filtered_scout[filtered_scout["Player"] == _s_sel].iloc[0] if not filtered_scout[filtered_scout["Player"] == _s_sel].empty else None
                            if _s_row is not None:
                                _sc1, _sc2, _sc3 = st.columns([2,1,1])
                                _s_age    = int(_s_row.get("Age", 0) or 0)
                                _s_pos    = _s_row.get("Position", _s_row.get("Best Pos","—"))
                                _s_rating = _s_row.get("Rating","—")
                                _s_val    = _s_row.get("Value","—")
                                _s_fit    = float(_s_row.get("System Fit %", 0) or 0)
                                _s_club   = _s_row.get("Club","—")
                                _s_goals  = int(_s_row.get("Goals", 0) or 0)
                                _s_ast    = int(_s_row.get("Assists", 0) or 0)
                                _s_apps   = int(_s_row.get("Apps_numeric", 0) or 0)
                                _s_contr  = _s_row.get("Contract Expires","—")
                                _s_wage   = _s_row.get("Wage","—")

                                with _sc1:
                                    st.markdown(f"### {_s_sel}")
                                    st.markdown(f"**{_s_pos}** · Age {_s_age} · {_s_club}")
                                    _s_grade = "A" if _s_fit >= 78 else "B" if _s_fit >= 65 else "C" if _s_fit >= 52 else "D" if _s_fit >= 40 else "F"
                                    _s_gc    = {"A":"🟢","B":"🟩","C":"🟡","D":"🟠","F":"🔴"}.get(_s_grade,"⚪")
                                    st.markdown(f"**System Fit:** {_s_gc} {_s_fit:.0f}% (Grade {_s_grade})")
                                    st.markdown(f"**Rating:** {_s_rating} &nbsp; **Goals:** {_s_goals} &nbsp; **Assists:** {_s_ast} &nbsp; **Apps:** {_s_apps}")
                                    st.markdown(f"**Value:** {_s_val} &nbsp;·&nbsp; **Wage:** {_s_wage} &nbsp;·&nbsp; **Contract:** {_s_contr}")

                                with _sc2:
                                    # Strengths bullets
                                    st.markdown("**✦ Strengths**")
                                    _s_str = []
                                    if pd.notna(_s_row.get("Rating")) and float(_s_row.get("Rating",0) or 0) >= 7.0:
                                        _s_str.append(f"Strong performer (avg {_s_row['Rating']})")
                                    if _s_goals >= 8:
                                        _s_str.append(f"Goal threat ({_s_goals} goals)")
                                    if _s_ast >= 5:
                                        _s_str.append(f"Creative returns ({_s_ast} assists)")
                                    if _s_fit >= 65:
                                        _s_str.append(f"Excellent system fit ({_s_fit:.0f}%)")
                                    if pd.notna(_s_row.get("Drb/90")) and float(_s_row.get("Drb/90",0) or 0) > 1.5:
                                        _s_str.append(f"Direct dribbler ({_s_row['Drb/90']:.1f}/90)")
                                    if pd.notna(_s_row.get("Pres C/90")) and float(_s_row.get("Pres C/90",0) or 0) > 4:
                                        _s_str.append(f"High pressing output")
                                    for _sl in _s_str[:4]:
                                        st.markdown(f"• {_sl}")
                                    if not _s_str:
                                        st.caption("Insufficient data for strengths.")

                                with _sc3:
                                    # Recommendation
                                    st.markdown("**📋 Recommendation**")
                                    if _s_fit >= 70 and float(_s_rating or 0) >= 7.0:
                                        _s_rec = "🟢 **Priority Target** — high fit & strong form. Move quickly."
                                    elif _s_fit >= 55:
                                        _s_rec = "🟡 **Monitor** — solid fit, verify over more games."
                                    elif _s_age <= 22 and _s_fit >= 40:
                                        _s_rec = "🔵 **Development Signing** — upside justifies patience."
                                    else:
                                        _s_rec = "🔴 **Low Priority** — below threshold for current targets."
                                    st.markdown(_s_rec)
                                    if _s_contr and str(_s_contr) != "—":
                                        st.markdown(f"⏳ Contract: **{_s_contr}**")
                                    st.markdown(f"💰 Est. Value: **{_s_val}**")

                                # Generate full HTML report for download
                                _s_today = date.today().strftime("%d %B %Y")
                                _s_badge = get_club_badge_b64(selected_theme_name)
                                _s_badge_html = f'<img src="data:image/png;base64,{_s_badge}" style="height:44px;object-fit:contain;">' if _s_badge else ""
                                _s_proj = "Priority target — move in next window." if _s_fit >= 70 else "Monitor over coming months." if _s_fit >= 50 else "Low priority — below squad threshold."
                                _s_acc = theme["secondary"] if theme["secondary"] != theme["primary"] else "#2255aa"

                                _s_str_html = "".join(f'<div style="font-size:11px;margin-bottom:5px;">• {x}</div>' for x in (_s_str[:4] if _s_str else ["Insufficient data."]))
                                _s_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* {{margin:0;padding:0;box-sizing:border-box;}}
body {{font-family:'Segoe UI',Arial,sans-serif;background:#fff;color:#222;}}
.topbar {{background:{theme['primary']};color:{header_text};padding:14px 24px;display:flex;justify-content:space-between;align-items:center;}}
.accent-bar {{height:4px;background:{theme['secondary']};}}
.hero {{background:#fff;display:grid;grid-template-columns:1fr 200px;border-bottom:3px solid {_s_acc};}}
.hero-info {{padding:18px 22px;}}
.hero-name {{font-size:24px;font-weight:900;color:#111;}}
.hero-pos {{display:inline-block;background:{_s_acc};color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;margin:5px 0 10px 0;}}
.hero-detail {{font-size:11px;color:#666;margin:3px 0;}}
.hero-detail span {{color:#111;font-weight:600;}}
.stat-strip {{background:{_s_acc};display:grid;grid-template-columns:repeat(5,1fr);text-align:center;padding:8px 0;}}
.sv {{font-size:17px;font-weight:800;color:#fff;}}
.sl {{font-size:9px;color:rgba(255,255,255,0.75);text-transform:uppercase;letter-spacing:0.8px;margin-top:1px;}}
.hero-right {{padding:18px;background:#f8f8f8;border-left:1px solid #eee;}}
.body {{padding:18px 24px;}}
.st {{font-size:11px;font-weight:800;letter-spacing:2px;color:{_s_acc};border-bottom:2px solid {_s_acc};padding-bottom:3px;margin:14px 0 8px 0;text-transform:uppercase;}}
.two-col {{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
.panel {{background:#f9f9f9;border-radius:6px;padding:12px;}}
.footer {{padding:8px 24px;background:#f0f0f0;font-size:9px;color:#999;display:flex;justify-content:space-between;}}
</style></head><body>
<div class="topbar">
  <div style="display:flex;align-items:center;gap:14px;">{_s_badge_html}<div><div style="font-size:18px;font-weight:900;">FM26 Scout Target Report</div><div style="font-size:10px;opacity:0.8;">{selected_theme_name.split(" (")[0]} · {_s_today}</div></div></div>
  <div style="font-size:11px;opacity:0.8;">Season 2026 · Scouting Dept.</div>
</div>
<div class="accent-bar"></div>
<div class="hero">
  <div class="hero-info">
    <div class="hero-name">{_s_sel}</div>
    <div class="hero-pos">{_s_pos}</div>
    <div class="hero-detail">Club: <span>{_s_club}</span></div>
    <div class="hero-detail">Age: <span>{_s_age}</span></div>
    <div class="hero-detail">System Fit: <span>{_s_fit:.0f}%</span></div>
    <div class="hero-detail">Market Value: <span>{_s_val}</span></div>
    <div class="hero-detail">Contract Expires: <span>{_s_contr}</span></div>
    <div class="hero-detail">Wage: <span>{_s_wage}</span></div>
  </div>
  <div class="hero-right">
    <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Recommendation</div>
    <div style="font-size:13px;font-weight:700;color:#111;">{_s_proj}</div>
    <div style="margin-top:12px;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;">System Fit Grade</div>
    <div style="font-size:28px;font-weight:900;color:{_s_acc};">{_s_grade}</div>
    <div style="font-size:10px;color:#888;">{_s_fit:.0f} / 100</div>
  </div>
</div>
<div class="stat-strip">
  <div><div class="sv">{_s_rating}</div><div class="sl">Rating</div></div>
  <div><div class="sv">{_s_apps}</div><div class="sl">Games</div></div>
  <div><div class="sv">{_s_goals}</div><div class="sl">Goals</div></div>
  <div><div class="sv">{_s_ast}</div><div class="sl">Assists</div></div>
  <div><div class="sv">{_s_fit:.0f}%</div><div class="sl">System Fit</div></div>
</div>
<div class="body">
  <div class="st">Analysis</div>
  <div class="two-col">
    <div class="panel">
      <div style="font-size:11px;font-weight:800;color:#1a8a3a;margin-bottom:8px;">✦ Strengths</div>
      {_s_str_html}
    </div>
    <div class="panel">
      <div style="font-size:11px;font-weight:800;color:#cc7700;margin-bottom:8px;">⚠ Considerations</div>
      <div style="font-size:11px;margin-bottom:5px;">• Verify performance level vs league quality</div>
      <div style="font-size:11px;margin-bottom:5px;">• Assess adaptation to tactical system</div>
      <div style="font-size:11px;margin-bottom:5px;">• Contract timing and negotiation window</div>
    </div>
  </div>
</div>
<div class="footer">
  <span>FM26 Squad Hub — Scout Report — {_s_today}</span>
  <span>{_s_sel} · {selected_theme_name.split(" (")[0]}</span>
</div>
</body></html>"""
                                st.download_button(
                                    f"📥 Download {_s_sel} Report (HTML)",
                                    _s_html.encode("utf-8"),
                                    file_name=f"scout_{_s_sel.replace(' ','_')}.html",
                                    mime="text/html",
                                    key=f"dl_scout_{_s_sel}"
                                )
                                st.caption("Open in browser → File → Print → Save as PDF")

                        st.divider()

                        # Fit % distribution chart
                        if "System Fit %" in result_df.columns and result_df["System Fit %"].notna().any():
                            top_targets = result_df.dropna(subset=["System Fit %"]).head(15)
                            fig_scout_bar = px.bar(
                                top_targets, x="Player", y="System Fit %",
                                color="System Fit %",
                                color_continuous_scale=theme["chart_scale"],
                                hover_data=[c for c in ["Club","Age","Value (£M est.)","Rating"] if c in top_targets.columns],
                                title="Top 15 Targets by System Fit %",
                                template="plotly_dark", height=420
                            )
                            fig_scout_bar.update_layout(xaxis_tickangle=-35, coloraxis_showscale=False)
                            st.plotly_chart(fig_scout_bar, use_container_width=True)

                        st.divider()

                        # ── COMPARE SCOUTED PLAYER VS SQUAD PLAYER ───
                        st.subheader("📊 Compare Scout Target vs Current Squad Player")

                        sc1, sc2 = st.columns(2)
                        scout_player_names = result_df["Player"].dropna().tolist() if "Player" in result_df.columns else []
                        squad_player_names = sorted(played_df["Player"].dropna().tolist()) if "Player" in played_df.columns else []

                        with sc1:
                            cmp_scout_player = st.selectbox("Scouted Player", scout_player_names, key="cmp_scout_p")
                        with sc2:
                            cmp_squad_player = st.selectbox("Current Squad Player", squad_player_names, key="cmp_squad_p")

                        if cmp_scout_player and cmp_squad_player:
                            scout_row = filtered_scout[filtered_scout["Player"]==cmp_scout_player].iloc[0]
                            squad_row = played_df[played_df["Player"]==cmp_squad_player].iloc[0]

                            # Find shared numeric metrics
                            shared_metrics = [c for c in scout_df.columns if c in played_df.columns
                                              and pd.api.types.is_numeric_dtype(scout_df[c])
                                              and c not in ["Has Played","Apps_numeric","Age"]]
                            default_shared = [c for c in ["Rating","Ps C/90","Tck/90","Int/90","Pres C/90","Sprints/90","Drb/90","OP-KP/90"] if c in shared_metrics]
                            cmp_shared_metrics = st.multiselect(
                                "Metrics to compare",
                                options=shared_metrics,
                                default=default_shared[:7] if default_shared else shared_metrics[:7],
                                key="cmp_shared_metrics"
                            )

                            if len(cmp_shared_metrics) >= 3:
                                fig_scout_radar = go.Figure()
                                norm_squad, norm_scout, raw_squad, raw_scout = [], [], [], []
                                for m in cmp_shared_metrics:
                                    combined = pd.concat([played_df[m], filtered_scout[m]]).dropna()
                                    col_min, col_max = combined.min(), combined.max()
                                    sv = squad_row.get(m, np.nan)
                                    tv = scout_row.get(m, np.nan)
                                    norm_squad.append(round((sv-col_min)/(col_max-col_min)*100,1) if pd.notna(sv) and col_max>col_min else 0)
                                    norm_scout.append(round((tv-col_min)/(col_max-col_min)*100,1) if pd.notna(tv) and col_max>col_min else 0)
                                    raw_squad.append(round(float(sv),2) if pd.notna(sv) else 0)
                                    raw_scout.append(round(float(tv),2) if pd.notna(tv) else 0)

                                fig_scout_radar.add_trace(go.Scatterpolar(
                                    r=norm_squad+[norm_squad[0]], theta=cmp_shared_metrics+[cmp_shared_metrics[0]],
                                    fill="toself", fillcolor=hex_to_rgba(theme["primary"],0.2),
                                    line=dict(color=theme["primary"], width=2), name=cmp_squad_player
                                ))
                                fig_scout_radar.add_trace(go.Scatterpolar(
                                    r=norm_scout+[norm_scout[0]], theta=cmp_shared_metrics+[cmp_shared_metrics[0]],
                                    fill="toself", fillcolor="rgba(255,140,0,0.2)",
                                    line=dict(color="orange", width=2, dash="dash"), name=cmp_scout_player
                                ))
                                fig_scout_radar.update_layout(
                                    polar=dict(bgcolor="#1a1f2e",
                                        radialaxis=dict(visible=True, range=[0,100], gridcolor="#333", tickfont=dict(color="grey",size=9)),
                                        angularaxis=dict(gridcolor="#444", tickfont=dict(color="white",size=11))),
                                    paper_bgcolor="#0d1117", font=dict(color="white"),
                                    title=dict(text=f"{cmp_scout_player} vs {cmp_squad_player}", font=dict(color=theme["primary"],size=14)),
                                    height=480, legend=dict(bgcolor="#1a1f2e", font=dict(color="white"))
                                )
                                st.plotly_chart(fig_scout_radar, use_container_width=True)

                                cmp_table = pd.DataFrame({
                                    "Metric": cmp_shared_metrics,
                                    cmp_squad_player: raw_squad,
                                    cmp_scout_player: raw_scout,
                                })
                                cmp_table["Better"] = [
                                    cmp_squad_player if a>b else cmp_scout_player if b>a else "Draw"
                                    for a,b in zip(raw_squad, raw_scout)
                                ]
                                st.dataframe(cmp_table, use_container_width=True, hide_index=True)

                                # Scout target summary card
                                fit_val = scout_row.get("System Fit %", None)
                                val_est = scout_row.get("Value (£M est.)", None)
                                summary_bits = []
                                if pd.notna(fit_val):
                                    summary_bits.append(f"System Fit: **{fit_val}%**")
                                if pd.notna(val_est):
                                    summary_bits.append(f"Est. Value: **£{val_est}M**")
                                if "Age" in scout_row and pd.notna(scout_row.get("Age")):
                                    summary_bits.append(f"Age: **{int(scout_row['Age'])}**")
                                if "Club" in scout_row and pd.notna(scout_row.get("Club")):
                                    summary_bits.append(f"Current Club: **{scout_row['Club']}**")
                                if summary_bits:
                                    st.info(" · ".join(summary_bits))
                            else:
                                st.info("Select at least 3 metrics to compare.")

                        st.divider()

                        # ── SHORTLIST ─────────────────────────────────
                        st.subheader("⭐ Transfer Shortlist")
                        st.caption("Save promising targets here. Shortlist persists for this session and can be exported.")

                        if "scout_shortlist" not in st.session_state:
                            st.session_state.scout_shortlist = []

                        add_player = st.selectbox(
                            "Add player to shortlist",
                            [""] + (result_df["Player"].dropna().tolist() if "Player" in result_df.columns else []),
                            key="shortlist_add_select"
                        )
                        if add_player and st.button("➕ Add to Shortlist", key="add_to_shortlist"):
                            existing_names = {p.get("Player") for p in st.session_state.scout_shortlist}
                            if add_player not in existing_names:
                                row_to_add = filtered_scout[filtered_scout["Player"] == add_player].iloc[0]
                                shortlist_cols = [c for c in [
                                    "Player","Age","Club","Division","Best Pos","Rating","Minutes","Wage (£/wk)","Expires Year",
                                    "Transfer Value","Value (£M est.)","System Fit %"
                                ] if c in row_to_add.index]
                                st.session_state.scout_shortlist.append({c: row_to_add[c] for c in shortlist_cols})
                                st.success(f"✅ Added {add_player} to shortlist.")
                            else:
                                st.info(f"{add_player} is already on the shortlist.")

                        if st.session_state.scout_shortlist:
                            shortlist_df = pd.DataFrame(st.session_state.scout_shortlist)
                            st.dataframe(shortlist_df, use_container_width=True, hide_index=True)

                            sl1, sl2 = st.columns(2)
                            with sl1:
                                remove_player = st.selectbox(
                                    "Remove from shortlist",
                                    [""] + shortlist_df["Player"].tolist(),
                                    key="shortlist_remove_select"
                                )
                                if remove_player and st.button("🗑️ Remove", key="remove_from_shortlist"):
                                    st.session_state.scout_shortlist = [
                                        p for p in st.session_state.scout_shortlist if p.get("Player") != remove_player
                                    ]
                                    st.rerun()

                            with sl2:
                                sl_buf = io.BytesIO()
                                with pd.ExcelWriter(sl_buf, engine="openpyxl") as sw:
                                    shortlist_df.to_excel(sw, index=False)
                                st.download_button(
                                    "📥 Export Shortlist (Excel)",
                                    sl_buf.getvalue(),
                                    file_name="fm26_transfer_shortlist.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.info("No players shortlisted yet.")

                except Exception as ex:
                    st.error(f"Could not read scouting file: {ex}")
                    st.exception(ex)
            else:
                st.info(
                    "Upload an FM26 Player Search / Recruitment export to get started. "
                    "This should include columns like Player, Age, Club, Transfer Value, Best Pos, Division and performance stats."
                )

        # ════════════════════════════════════════════════════════
        # TAB 8 — SCOUT REPORT (PDF)
        # ════════════════════════════════════════════════════════
        with tab8:
            st.subheader("📄 Player Scout Report")
            st.caption("Select a player to generate a full scouting PDF with radar, stats, role scores and auto summary.")

            if played_df.empty or "Player" not in played_df.columns:
                st.warning("No players with appearances found. Check your CSV export.")
            else:
                scout_player = st.selectbox(
                    "Select Player",
                    sorted(played_df["Player"].dropna().tolist()),
                    key="scout_player"
                )

                p_row = played_df[played_df["Player"] == scout_player].iloc[0]

                # ── Role suitability scoring (uses module-level ROLE_WEIGHTS + score_role) ──
                # ── Restrict candidate roles to those matching the player's
                # actual positions (Best Pos first, falls back to the
                # wider Position field if Best Pos isn't usable) ──────
                player_best_pos = p_row.get("Best Pos", None)
                player_position_field = str(p_row.get("Position", ""))
                player_positions_wide = [p.strip() for p in re.split(r"[,/]", player_position_field) if p.strip()]

                eligible_roles = {}
                for role, weights in ROLE_WEIGHTS.items():
                    role_positions = ROLE_POSITION_MAP.get(role, [])
                    is_eligible = (
                        (pd.notna(player_best_pos) and player_best_pos in role_positions)
                        or any(p in role_positions for p in player_positions_wide)
                    )
                    if is_eligible:
                        eligible_roles[role] = weights

                # Fallback: if no role matches (unusual position string),
                # score against all roles rather than showing nothing.
                if not eligible_roles:
                    eligible_roles = dict(ROLE_WEIGHTS)

                role_scores = {
                    role: score_role(p_row, weights, played_df)
                    for role, weights in eligible_roles.items()
                }
                role_scores_sorted = dict(sorted(role_scores.items(), key=lambda x: x[1], reverse=True))
                best_role_fit = list(role_scores_sorted.keys())[0]
                best_role_score = list(role_scores_sorted.values())[0]

                # ── Auto text summary ────────────────────────────
                def generate_summary(row, role_scores, data):
                    name        = row.get("Player", "This player")
                    pos         = row.get("Position", "Unknown")
                    best_pos    = row.get("Best Pos", pos)
                    rating      = row.get("Rating", None)
                    age         = row.get("Age", None)
                    best_fit    = list(role_scores.keys())[0]
                    best_score  = list(role_scores.values())[0]
                    goals       = row.get("Goals", None)
                    xg          = row.get("xG", None)
                    assists     = row.get("Assists", None)
                    clinicality = row.get("Goals - xG", None)
                    press       = row.get("Pres C/90", None)
                    sprints     = row.get("Sprints/90", None)
                    ps          = row.get("Ps C/90", None)
                    op_kp       = row.get("OP-KP/90", None)
                    tck         = row.get("Tck/90", None)
                    int_        = row.get("Int/90", None)
                    hdrs        = row.get("Hdrs W/90", None)
                    drb         = row.get("Drb/90", None)
                    conv        = row.get("Conv %", None)
                    apps        = row.get("Apps_numeric", None)

                    squad_avg   = lambda col: data[col].mean() if col in data.columns else None
                    squad_rank  = lambda col, v: int((data[col] > v).sum()) + 1 if col in data.columns and pd.notna(v) else None
                    squad_size  = len(data)

                    paragraphs = []

                    # ── Opening line — age + role identity ──────────
                    age_desc = ""
                    if pd.notna(age):
                        if int(age) <= 19:
                            age_desc = f"At just {int(age)}, "
                        elif int(age) <= 23:
                            age_desc = f"Still only {int(age)} years old, "
                        elif int(age) >= 32:
                            age_desc = f"At {int(age)}, in the veteran stage of his career, "
                        elif int(age) >= 29:
                            age_desc = f"At {int(age)} and entering the peak-to-twilight phase, "
                        else:
                            age_desc = f"At {int(age)}, "

                    fit_desc = "an outstanding" if best_score >= 75 else "a strong" if best_score >= 60 else "a reasonable" if best_score >= 45 else "a developing"
                    paragraphs.append(
                        f"{age_desc}{name} profiles as {fit_desc} fit for the **{best_fit}** role, "
                        f"scoring {best_score}% in our system analysis. "
                        f"Naturally deployed as a {best_pos}, their positional intelligence and technical profile make them "
                        f"{'one of the most tactically versatile options in the squad' if best_score >= 70 else 'a player worth monitoring closely as the system evolves'}."
                    )

                    # ── Season narrative ─────────────────────────────
                    if pd.notna(rating):
                        rank = squad_rank("Rating", rating)
                        rank_desc = (
                            f"ranked {rank} in the squad" if rank and rank <= squad_size else "among the squad"
                        )
                        if float(rating) >= 7.3:
                            season_line = f"This has been a **standout season** — a rating of {rating} ({rank_desc}) puts them firmly in the conversation for the best performers in the squad."
                        elif float(rating) >= 7.0:
                            season_line = f"A **consistent and dependable** season: rated {rating} ({rank_desc}), they have delivered when called upon and justified their place in the starting eleven."
                        elif float(rating) >= 6.7:
                            season_line = f"A **solid if unspectacular** campaign — the {rating} rating ({rank_desc}) reflects a player doing their job without setting the world alight."
                        else:
                            season_line = f"It has been a **difficult season** — a rating of {rating} ({rank_desc}) points to either limited game time or performances below expectation."
                        if pd.notna(apps) and int(apps) > 0:
                            season_line += f" They featured in {int(apps)} appearances."
                        paragraphs.append(season_line)

                    # ── Goal contribution paragraph ───────────────────
                    goal_lines = []
                    if pd.notna(goals) and pd.notna(xg) and float(xg) > 0.5:
                        xg_r = round(float(xg), 1)
                        g_i  = int(goals) if pd.notna(goals) else 0
                        if pd.notna(clinicality) and float(clinicality) > 2.5:
                            goal_lines.append(
                                f"In front of goal, {name} has been **ruthlessly clinical** — {g_i} goals from just {xg_r} xG is the mark of a finisher who makes the most of every chance. "
                                f"The {round(float(clinicality),1):+.1f} goals-over-xG figure is among the best in the squad and suggests genuine quality rather than luck."
                            )
                        elif pd.notna(clinicality) and float(clinicality) > 0.5:
                            goal_lines.append(
                                f"Finishing has been a **positive story** this term — {g_i} goals from {xg_r} xG shows they are converting slightly better than their opportunities suggest."
                            )
                        elif pd.notna(clinicality) and float(clinicality) < -2.0:
                            goal_lines.append(
                                f"There is a **case for optimism** in the xG numbers — generating {xg_r} expected goals but converting only {g_i} suggests either poor finishing or unfortunate timing. "
                                f"If they can match their xG next season, the goal return should look significantly better."
                            )
                        elif g_i > 0:
                            goal_lines.append(
                                f"Contributed {g_i} goals against an xG of {xg_r} — a return broadly in line with expectations for their position and role."
                            )
                    if pd.notna(assists) and float(assists) > 0:
                        a_rank = squad_rank("Assists", assists)
                        assist_desc = f" ({a_rank} in the squad)" if a_rank and a_rank <= 5 else ""
                        goal_lines.append(f"Added {int(assists)} assists{assist_desc} to their direct contribution.")
                    if goal_lines:
                        paragraphs.append(" ".join(goal_lines))

                    # ── Engine / pressing paragraph ───────────────────
                    engine_lines = []
                    avg_press  = squad_avg("Pres C/90")
                    avg_sprint = squad_avg("Sprints/90")
                    if pd.notna(press) and avg_press:
                        press_ratio = float(press) / avg_press
                        if press_ratio >= 1.4:
                            engine_lines.append(
                                f"Off the ball, {name} is a **genuine pressing machine** — {round(float(press),1)} completed presses per 90 is {round(press_ratio,1)}x the squad average. "
                                f"In a high-intensity system, they are a defensive weapon before the ball is even lost."
                            )
                        elif press_ratio >= 1.15:
                            engine_lines.append(
                                f"Shows **above-average pressing intensity** with {round(float(press),1)} completed presses per 90, making them a useful fit for pressing-heavy tactical setups."
                            )
                        elif press_ratio < 0.65:
                            engine_lines.append(
                                f"The pressing numbers ({round(float(press),1)} per 90) are **below squad average**, which is worth flagging if the system demands high defensive activity."
                            )
                    if pd.notna(sprints) and avg_sprint:
                        sprint_ratio = float(sprints) / avg_sprint
                        if sprint_ratio >= 1.3:
                            engine_lines.append(f"Their sprint output ({round(float(sprints),1)}/90) also stands out, underlining a player with exceptional athletic capacity.")
                        elif sprint_ratio < 0.7 and engine_lines:
                            engine_lines.append(f"Sprint output ({round(float(sprints),1)}/90) is on the lower side — likely a positional trait rather than a fitness concern.")
                    if engine_lines:
                        paragraphs.append(" ".join(engine_lines))

                    # ── Technical / passing paragraph ─────────────────
                    tech_lines = []
                    avg_ps    = squad_avg("Ps C/90")
                    avg_kp    = squad_avg("OP-KP/90")
                    if pd.notna(ps) and avg_ps:
                        ps_rank = squad_rank("Ps C/90", ps)
                        if float(ps) > avg_ps * 1.25:
                            tech_lines.append(
                                f"Technically, {name} is one of the squad's **most reliable ball-players** — "
                                f"{round(float(ps),1)} completed passes per 90 places them {ps_rank}{'st' if ps_rank==1 else 'nd' if ps_rank==2 else 'rd' if ps_rank==3 else 'th'} in the squad for passing volume."
                            )
                    if pd.notna(op_kp) and avg_kp:
                        if float(op_kp) > avg_kp * 1.3:
                            tech_lines.append(
                                f"The **key pass creation rate** ({round(float(op_kp),1)}/90) is particularly impressive — this is a player who consistently creates chances for others."
                            )
                    if pd.notna(drb) and "Drb/90" in data.columns:
                        avg_drb = data["Drb/90"].mean()
                        if float(drb) > avg_drb * 1.5:
                            tech_lines.append(
                                f"Dribbling is another weapon in the armoury — {round(float(drb),1)} successful dribbles per 90 makes them a genuine 1v1 threat."
                            )
                    if tech_lines:
                        paragraphs.append(" ".join(tech_lines))

                    # ── Defensive paragraph ───────────────────────────
                    def_lines = []
                    avg_tck = squad_avg("Tck/90")
                    avg_int = squad_avg("Int/90")
                    if pd.notna(tck) and pd.notna(int_) and avg_tck and avg_int:
                        combined      = float(tck) + float(int_)
                        avg_combined  = avg_tck + avg_int
                        if combined > avg_combined * 1.35:
                            def_lines.append(
                                f"Defensively, {name} is **extremely active** — {round(float(tck),1)} tackles and {round(float(int_),1)} interceptions per 90 "
                                f"puts their combined defensive actions significantly above the squad average. They break up play regularly."
                            )
                        elif combined > avg_combined * 1.1:
                            def_lines.append(
                                f"Contributes well defensively with {round(float(tck),1)} tackles and {round(float(int_),1)} interceptions per 90 — above average across both metrics."
                            )
                    if pd.notna(hdrs) and "Hdrs W/90" in data.columns:
                        avg_hdrs = data["Hdrs W/90"].mean()
                        if float(hdrs) > avg_hdrs * 1.4:
                            def_lines.append(
                                f"Aerial dominance is a standout quality — winning {round(float(hdrs),1)} headers per 90 makes them a key asset at set pieces and in physical duels."
                            )
                    if def_lines:
                        paragraphs.append(" ".join(def_lines))

                    # ── Closing verdict ───────────────────────────────
                    if pd.notna(age) and int(age) <= 20 and pd.notna(rating) and float(rating) >= 6.8:
                        verdict = (
                            f"**Verdict:** At {int(age)}, {name} is a genuine asset for the future. "
                            f"The combination of a {rating} rating and strong system fit at this age suggests a player capable of developing into a squad cornerstone. "
                            f"Prioritise minutes and a long-term contract."
                        )
                    elif pd.notna(rating) and float(rating) >= 7.3 and best_score >= 65:
                        verdict = (
                            f"**Verdict:** A complete performer this season. High rating, strong system fit — "
                            f"{name} is the type of player you build your squad around. "
                            f"Protecting their contract situation should be a priority."
                        )
                    elif pd.notna(age) and int(age) >= 31 and pd.notna(rating) and float(rating) < 7.0:
                        verdict = (
                            f"**Verdict:** With age and performances trending in the same direction, "
                            f"it may be time to consider succession planning for {name}'s position. "
                            f"Still useful in a rotation role, but building a long-term dependency would be risky."
                        )
                    elif best_score >= 70:
                        verdict = (
                            f"**Verdict:** The system fit numbers speak for themselves — {name} was built for this setup. "
                            f"If performances can be maintained, they should be a fixture in the starting eleven."
                        )
                    else:
                        verdict = (
                            f"**Verdict:** {name} offers genuine quality in specific areas of the game. "
                            f"Used in the right role and with clear tactical instructions, "
                            f"there is a reliable contributor here."
                        )
                    paragraphs.append(verdict)

                    return "\n\n".join(paragraphs)

                summary_text = generate_summary(p_row, role_scores_sorted, played_df)
                # Convert markdown **bold** and newlines to HTML
                import re as _re
                summary_html = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', summary_text)
                summary_html = summary_html.replace("\n\n", "</p><p style='margin-top:10px'>")

                # ── Alerts for this player ───────────────────────
                player_alerts = []
                if "Goals - xG" in p_row and pd.notna(p_row["Goals - xG"]):
                    if float(p_row["Goals - xG"]) < -1.5:
                        player_alerts.append("⚠️ Significantly underperforming xG this season.")
                    if float(p_row["Goals - xG"]) > 3.0:
                        player_alerts.append("🍀 Overperforming xG — finishing may not be sustainable.")
                if "Pass Rating (rel%)" in p_row and pd.notna(p_row["Pass Rating (rel%)"]):
                    if float(p_row["Pass Rating (rel%)"]) < 40:
                        player_alerts.append("🔴 Passing output in bottom 40% of squad.")
                if has_age and "Age" in p_row and pd.notna(p_row["Age"]):
                    if int(p_row["Age"]) >= 32:
                        player_alerts.append(f"📅 Veteran (Age {int(p_row['Age'])}) — contract and succession planning recommended.")
                    if int(p_row["Age"]) <= 20:
                        player_alerts.append(f"🌱 Young talent (Age {int(p_row['Age'])}) — high development potential.")
                if not player_alerts:
                    player_alerts.append("✅ No major flags detected.")

                # ── Radar for PDF (base64 PNG) ───────────────────
                REPORT_METRICS = ["Goals","xG","Ps C/90","Pres C/90","Sprints/90","Tck/90","Int/90","OP-KP/90","ShT/90","Drb/90"]
                radar_cols = [m for m in REPORT_METRICS if m in played_df.columns and pd.notna(p_row.get(m))]

                radar_vals = []
                for m in radar_cols:
                    col_max = played_df[m].max()
                    col_min = played_df[m].min()
                    v = float(p_row[m])
                    if col_max == col_min:
                        radar_vals.append(50)
                    else:
                        radar_vals.append(round((v - col_min) / (col_max - col_min) * 100, 1))

                fig_pdf_radar = go.Figure()
                fig_pdf_radar.add_trace(go.Scatterpolar(
                    r=radar_vals + [radar_vals[0]],
                    theta=radar_cols + [radar_cols[0]],
                    fill="toself",
                    fillcolor=f"rgba({int(theme['primary'][1:3],16)},{int(theme['primary'][3:5],16)},{int(theme['primary'][5:7],16)},0.3)",
                    line=dict(color=theme["primary"], width=2),
                    name=scout_player
                ))
                fig_pdf_radar.update_layout(
                    polar=dict(
                        bgcolor="#f8f8f8",
                        radialaxis=dict(visible=True, range=[0,100], tickfont=dict(size=8)),
                        angularaxis=dict(tickfont=dict(size=10))
                    ),
                    paper_bgcolor="white",
                    height=380, width=420,
                    margin=dict(l=50, r=50, t=40, b=40),
                    showlegend=False
                )
                radar_png = fig_pdf_radar.to_image(format="png", scale=2)
                radar_b64 = base64.b64encode(radar_png).decode()

                # ── Role scores bar chart (base64 PNG) ───────────
                # ── Light theme detection — needed for PDF and charts ────

                fig_roles = px.bar(
                    x=list(role_scores_sorted.values()),
                    y=list(role_scores_sorted.keys()),
                    orientation="h",
                    color=list(role_scores_sorted.values()),
                    color_continuous_scale=[[0, bar_color_low],[0.5, bar_color_high],[1.0, bar_color_high]],
                    range_color=[0, 100]
                )
                fig_roles.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    height=360, width=600,
                    margin=dict(l=200, r=30, t=20, b=20),
                    showlegend=False,
                    coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed", tickfont=dict(size=11), ticklen=0),
                    xaxis=dict(range=[0,100], tickfont=dict(size=9), title="Score (0–100)")
                )
                fig_roles.update_traces(
                    marker_line_width=0,
                    text=[f"{v:.0f}%" for v in role_scores_sorted.values()],
                    textposition="outside",
                    textfont=dict(size=10, color="#333")
                )
                roles_png = fig_roles.to_image(format="png", scale=2)
                roles_b64 = base64.b64encode(roles_png).decode()

                # ── Key stats for table ──────────────────────────
                STAT_GROUPS = {
                    "Attacking":  ["Goals","xG","Goals - xG","Conv %","ShT/90","Ch C/90","Assists"],
                    "Pressing":   ["Pres C/90","Pres A/90","Press Success %","Sprints/90"],
                    "Passing":    ["Ps C/90","OP-KP/90","Pr passes/90"],
                    "Defensive":  ["Tck/90","Int/90","Hdrs W/90","Dist/90"],
                    "General":    ["Rating","Appearances","Mins/Gm"],
                }

                def stat_rows_html(row, groups, primary_color, accent_color):
                    html = ""
                    for group, cols in groups.items():
                        available = [(c, row[c]) for c in cols if c in row.index and pd.notna(row.get(c))]
                        if not available:
                            continue
                        grp_text = "#000" if primary_color in ["#FEE100","#FEBE10","#00ff87"] else "#fff"
                        html += f"""
                        <tr>
                          <td colspan="4" style="background:{accent_color};color:#fff;
                              font-weight:700;font-size:11px;padding:5px 8px;letter-spacing:1px;">
                            {group.upper()}
                          </td>
                        </tr>"""
                        pairs = [available[i:i+2] for i in range(0, len(available), 2)]
                        for pair in pairs:
                            html += "<tr>"
                            for col, val in pair:
                                display_val = f"{val:.1f}" if isinstance(val, float) else str(val)
                                html += f"""
                                <td style="color:#555;font-size:11px;padding:4px 8px;width:25%">{col}</td>
                                <td style="font-weight:700;font-size:12px;padding:4px 8px;width:25%;color:#111">{display_val}</td>"""
                            if len(pair) == 1:
                                html += "<td></td><td></td>"
                            html += "</tr>"
                    return html

                stats_html = stat_rows_html(p_row, STAT_GROUPS, theme["primary"], pdf_accent)

                alerts_html = "".join(
                    f'<div style="padding:5px 10px;margin:4px 0;background:#fff8f0;border-left:3px solid #e67e22;font-size:12px;color:#333">{a}</div>'
                    for a in player_alerts
                )

                today_str = date.today().strftime("%d %B %Y")
                player_pos  = p_row.get("Position","—")
                player_role = p_row.get("Best Role", best_role_fit)
                player_age  = int(p_row["Age"]) if has_age and pd.notna(p_row.get("Age")) else "—"
                player_rat  = p_row.get("Rating","—")

                # ── Build scatter chart PNGs (Goal Threat + Dribbling) ──
                def make_scatter_png(df_data, x_col, y_col, x_label, y_label, title, player_name, accent):
                    import plotly.graph_objects as _go2
                    fig = _go2.Figure()
                    # All players
                    xs = df_data[x_col].dropna()
                    ys = df_data[y_col].dropna()
                    common = df_data[[x_col, y_col, "Player"]].dropna()
                    fig.add_trace(_go2.Scatter(
                        x=common[x_col], y=common[y_col],
                        mode="markers+text",
                        text=common["Player"].apply(lambda n: n.split()[-1] if n != player_name else n),
                        textposition="top center",
                        textfont=dict(size=8, color="#aaa"),
                        marker=dict(color="#cc3333", size=7, opacity=0.7),
                        name="Squad"
                    ))
                    # Highlight selected player
                    p_x = df_data.loc[df_data["Player"]==player_name, x_col]
                    p_y = df_data.loc[df_data["Player"]==player_name, y_col]
                    if not p_x.empty:
                        fig.add_trace(_go2.Scatter(
                            x=p_x, y=p_y, mode="markers+text",
                            text=[player_name.split()[-1]],
                            textposition="top center",
                            textfont=dict(size=9, color=accent, family="Arial Black"),
                            marker=dict(color=accent, size=12, symbol="circle",
                                        line=dict(color="white", width=2)),
                            name=player_name
                        ))
                    # Average lines
                    if not common.empty:
                        fig.add_hline(y=common[y_col].mean(), line_dash="dash", line_color="#888", line_width=1)
                        fig.add_vline(x=common[x_col].mean(), line_dash="dash", line_color="#888", line_width=1)
                    fig.update_layout(
                        title=dict(text=title, font=dict(size=11, color="#333"), x=0.02),
                        xaxis=dict(title=x_label, titlefont=dict(size=10), tickfont=dict(size=9), gridcolor="#eee"),
                        yaxis=dict(title=y_label, titlefont=dict(size=10), tickfont=dict(size=9), gridcolor="#eee"),
                        paper_bgcolor="white", plot_bgcolor="white",
                        height=300, width=420,
                        margin=dict(l=50, r=20, t=40, b=50),
                        showlegend=False
                    )
                    png = fig.to_image(format="png", scale=2)
                    return base64.b64encode(png).decode()

                # Goal Threat scatter (xG/90 vs Goals/90)
                scatter_goal_b64 = ""
                scatter_drb_b64  = ""
                _plot_df = played_df.copy()
                _plot_df["Goals/90"] = _plot_df.apply(
                    lambda r: round(float(r["Goals"]) / max(float(r.get("Apps_numeric",1) or 1), 1), 2)
                    if pd.notna(r.get("Goals")) else None, axis=1)
                _plot_df["xG/90"] = _plot_df.apply(
                    lambda r: round(float(r["xG"]) / max(float(r.get("Apps_numeric",1) or 1), 1), 2)
                    if pd.notna(r.get("xG")) else None, axis=1)

                try:
                    if "xG" in played_df.columns and "Goals" in played_df.columns:
                        scatter_goal_b64 = make_scatter_png(
                            _plot_df, "xG/90", "Goals/90",
                            "xG /90", "Goals /90",
                            "Goal Threat", scout_player, pdf_accent
                        )
                except Exception:
                    pass

                try:
                    if "Drb/90" in played_df.columns and "ShT/90" in played_df.columns:
                        scatter_drb_b64 = make_scatter_png(
                            played_df, "Drb/90", "ShT/90",
                            "Dribbles /90", "Shots /90",
                            "Dribbling & Shooting", scout_player, pdf_accent
                        )
                    elif "Drb/90" in played_df.columns and "Pres C/90" in played_df.columns:
                        scatter_drb_b64 = make_scatter_png(
                            played_df, "Drb/90", "Pres C/90",
                            "Dribbles /90", "Press Complete /90",
                            "Dribbling Efficiency", scout_player, pdf_accent
                        )
                except Exception:
                    pass

                # ── Strengths & Development from summary_text ──────────
                def extract_strengths_development(row):
                    strengths, development = [], []
                    rating  = float(row.get("Rating", 0) or 0)
                    goals   = int(row.get("Goals", 0) or 0)
                    assists = int(row.get("Assists", 0) or 0)
                    drb     = float(row.get("Drb/90", 0) or 0)
                    press   = float(row.get("Pres C/90", 0) or 0)
                    tck     = float(row.get("Tck/90", 0) or 0)
                    xg      = float(row.get("xG", 0) or 0)
                    clinicality = float(row.get("Goals - xG", 0) or 0)
                    age     = int(row.get("Age", 25) or 25)
                    ps      = float(row.get("Ps C/90", 0) or 0)
                    hdrs    = float(row.get("Hdrs W/90", 0) or 0)
                    sprints = float(row.get("Sprints/90", 0) or 0)
                    avg = lambda col: float(played_df[col].mean()) if col in played_df.columns else 0

                    if rating >= 7.3:
                        strengths.append(("<strong>Elite Form:</strong>", f"Averaging {rating:.2f} — among the best performers in the squad this season."))
                    elif rating >= 7.0:
                        strengths.append(("<strong>Consistent Rating:</strong>", f"Season average of {rating:.2f} demonstrates reliable quality across all appearances."))

                    if clinicality > 1.5:
                        strengths.append(("<strong>Clinical Finishing:</strong>", f"Outscoring xG by {clinicality:+.1f} — a genuine eye for goal beyond expected output."))
                    elif goals >= 8:
                        strengths.append(("<strong>Goal Threat:</strong>", f"{goals} goals this season makes them a consistent attacking weapon."))

                    if assists >= 5:
                        strengths.append(("<strong>Chance Creation:</strong>", f"{assists} assists reflect a player who regularly puts teammates in on goal."))

                    if drb > avg("Drb/90") * 1.4:
                        strengths.append(("<strong>Dribbling & Speed:</strong>", f"{drb:.1f} successful dribbles per 90 — a direct threat in 1v1 situations."))

                    if press > avg("Pres C/90") * 1.3:
                        strengths.append(("<strong>Pressing:</strong>", f"{press:.1f} completed presses per 90 — intense, disciplined work rate off the ball."))

                    if tck > avg("Tck/90") * 1.3:
                        strengths.append(("<strong>Defensive Contribution:</strong>", f"Above-average tackle rate ({tck:.1f}/90) adds defensive value to their game."))

                    if ps > avg("Ps C/90") * 1.25:
                        strengths.append(("<strong>Ball Retention:</strong>", f"Completed passes per 90 ({ps:.1f}) is well above squad average — reliable in possession."))

                    if hdrs > avg("Hdrs W/90") * 1.4:
                        strengths.append(("<strong>Aerial Ability:</strong>", f"Wins {hdrs:.1f} headers per 90 — a useful set-piece and physical duel asset."))

                    # Development areas
                    if age <= 23:
                        development.append(("<strong>Physicality:</strong>", "At this age, strength and presence in duels will continue to develop with regular minutes."))
                    if clinicality < -1.5 and xg > 2:
                        development.append(("<strong>Finishing Consistency:</strong>", f"Generating {xg:.1f} xG but underconverting — composure in front of goal needs improvement."))
                    if drb < avg("Drb/90") * 0.7:
                        development.append(("<strong>Direct Threat:</strong>", "Dribble success rate below squad average — needs to become more decisive in 1v1 situations."))
                    if press < avg("Pres C/90") * 0.7:
                        development.append(("<strong>Pressing Intensity:</strong>", "Off-ball activity is below squad average — pressing engagement needs to improve for high-press systems."))
                    if sprints < avg("Sprints/90") * 0.7:
                        development.append(("<strong>Athletic Output:</strong>", "Sprint numbers are low relative to squad — physical conditioning or positional discipline may need attention."))
                    if not development:
                        development.append(("<strong>Decision-Making:</strong>", "Continue to refine timing of passes and runs in tight defensive spaces."))

                    return strengths[:4], development[:3]

                _strengths, _development = extract_strengths_development(p_row)

                def bullet_list(items, accent):
                    html = ""
                    for label, text in items:
                        html += f'''<div style="display:flex;gap:8px;margin-bottom:8px;">
                            <div style="color:{accent};font-size:16px;line-height:1.3;">•</div>
                            <div style="font-size:12px;line-height:1.5;color:#333">{label} {text}</div>
                        </div>'''
                    return html

                # Match grade (A–F based on squad score)
                _sq = float(p_row.get("Squad Score", 50) or 50)
                _grade = "A" if _sq >= 78 else "B" if _sq >= 65 else "C" if _sq >= 52 else "D" if _sq >= 40 else "F"
                _grade_color = {"A":"#1a8a3a","B":"#2ecc71","C":"#e6a817","D":"#e05500","F":"#cc2200"}.get(_grade,"#888")

                # Recommendation & Projection
                _rec  = p_row.get("Decision", "Monitor development")
                _rec  = _rec.replace("✅ ","").replace("🔄 ","").replace("🌱 ","").replace("🔴 ","").replace("⚪ ","")
                _proj_parts = []
                _proj_age = int(p_row.get("Age", 25) or 25)
                if _proj_age <= 22:
                    _proj_parts.append(f"High development upside at {_proj_age}")
                    _proj_parts.append("Development pathway via loan or regular minutes")
                elif _sq >= 70:
                    _proj_parts.append(f"Elite system fit ({_sq:.0f}%) — starting XI candidate")
                    _proj_parts.append("Long-term contract recommended")
                elif _sq >= 52:
                    _proj_parts.append("Solid rotation option with improvement potential")
                    _proj_parts.append("Monitor over next half-season")
                else:
                    _proj_parts.append("Below elite squad threshold")
                    _proj_parts.append("Sell/replace window recommended")
                _proj_html = "".join(f"<div style='font-size:11px;color:#555;margin-bottom:3px;'>{p}</div>" for p in _proj_parts)

                _contract = p_row.get("Contract Expires", "—")
                _wage     = p_row.get("Wage", "—")
                _value    = p_row.get("Value", "—")
                _apps     = int(p_row.get("Apps_numeric", 0) or 0)
                _mins     = p_row.get("Mins/Gm", "—")
                _goals    = int(p_row.get("Goals", 0) or 0)
                _assists  = int(p_row.get("Assists", 0) or 0)
                _badge_html = f'''<img src="data:image/png;base64,{_badge_b64}" style="height:50px;object-fit:contain;">''' if _badge_b64 else ""

                # ── Build full HTML PDF ──────────────────────────
                html_report = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#1a1a2e; color:#222; font-size:13px; }}

  /* ── TOP HEADER BAR ── */
  .topbar {{
    background:{theme['primary']};
    color:{header_text};
    padding:16px 28px;
    display:flex; justify-content:space-between; align-items:center;
  }}
  .topbar-left {{ display:flex; align-items:center; gap:16px; }}
  .topbar-left .club-badge {{ opacity:0.9; }}
  .topbar-title {{ font-size:22px; font-weight:900; letter-spacing:1px; }}
  .topbar-sub {{ font-size:11px; opacity:0.8; margin-top:2px; }}
  .topbar-right {{ text-align:right; font-size:11px; opacity:0.8; }}
  .accent-bar {{ height:4px; background:{theme['secondary']}; }}

  /* ── PLAYER HERO CARD ── */
  .hero {{
    background:#fff;
    display:grid;
    grid-template-columns:160px 1fr 220px;
    gap:0;
    border-bottom:3px solid {pdf_accent};
  }}
  .hero-photo {{
    background:linear-gradient(135deg,{theme['primary']}22,{theme['secondary']}44);
    display:flex; align-items:center; justify-content:center;
    padding:20px; min-height:160px;
  }}
  .hero-photo svg {{ opacity:0.3; }}
  .hero-info {{ padding:20px 24px; }}
  .hero-name {{ font-size:26px; font-weight:900; color:#111; line-height:1.1; }}
  .hero-pos  {{ display:inline-block; background:{pdf_accent}; color:#fff;
                font-size:11px; font-weight:700; padding:3px 10px;
                border-radius:12px; margin:6px 0 10px 0; letter-spacing:1px; }}
  .hero-detail {{ font-size:11px; color:#666; margin:3px 0; display:flex; align-items:center; gap:6px; }}
  .hero-detail span {{ color:#111; font-weight:600; }}
  .hero-right {{ padding:20px; background:#f8f8f8; border-left:1px solid #eee; }}

  /* Season stats strip */
  .stat-strip {{
    background:{pdf_accent};
    display:grid; grid-template-columns:repeat(5,1fr);
    text-align:center; padding:10px 0;
  }}
  .stat-item .stat-val {{ font-size:18px; font-weight:800; color:#fff; }}
  .stat-item .stat-lbl {{ font-size:9px; color:rgba(255,255,255,0.75); text-transform:uppercase; letter-spacing:0.8px; margin-top:1px; }}

  /* ── MAIN BODY ── */
  .body {{ background:#fff; padding:20px 28px; }}
  .section-title {{
    font-size:11px; font-weight:800; letter-spacing:2px;
    color:{pdf_accent}; border-bottom:2px solid {pdf_accent};
    padding-bottom:3px; margin:18px 0 10px 0; text-transform:uppercase;
  }}

  /* 3-col layout */
  .three-col {{ display:grid; grid-template-columns:1fr 1fr 200px; gap:20px; margin-bottom:8px; }}
  .two-col   {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}

  /* Summary */
  .summary-box {{
    background:#f7f9fc; border-left:4px solid {pdf_accent};
    padding:12px 16px; border-radius:4px;
    font-size:11.5px; line-height:1.7; color:#444;
  }}

  /* Strengths / Development */
  .panel {{ background:#f9f9f9; border-radius:6px; padding:14px; }}
  .panel-title {{ font-size:11px; font-weight:800; text-transform:uppercase;
                  letter-spacing:1px; color:{pdf_accent}; margin-bottom:10px; }}

  /* Match Grade */
  .grade-box {{
    background:#f9f9f9; border-radius:6px; padding:14px; text-align:center;
  }}
  .grade-circle {{
    width:64px; height:64px; border-radius:50%;
    background: conic-gradient({_grade_color} {int(_sq)}%, #ddd {int(_sq)}%);
    display:flex; align-items:center; justify-content:center;
    margin:0 auto 6px auto; position:relative;
  }}
  .grade-inner {{
    width:52px; height:52px; border-radius:50%; background:#f9f9f9;
    display:flex; align-items:center; justify-content:center;
    font-size:22px; font-weight:900; color:{_grade_color};
  }}
  .grade-label {{ font-size:9px; color:#888; text-transform:uppercase; letter-spacing:1px; }}

  /* Rec / Projection */
  .rec-box {{ background:#f9f9f9; border-radius:6px; padding:14px; }}
  .rec-title {{ font-size:10px; color:#888; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }}
  .rec-val   {{ font-size:13px; font-weight:700; color:#111; margin-bottom:10px; }}

  /* Radar */
  .radar-wrap {{ text-align:center; }}
  .radar-wrap img {{ max-width:100%; }}
  .chart-label {{ font-size:9px; color:#888; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }}

  /* Stats table */
  table {{ width:100%; border-collapse:collapse; }}
  tr:nth-child(even) td {{ background:#fafafa; }}
  .footer {{
    padding:10px 28px; background:#f0f0f0;
    font-size:9px; color:#999;
    display:flex; justify-content:space-between;
  }}
  img {{ max-width:100%; }}
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <div class="topbar-left">
    <div class="club-badge">{_badge_html}</div>
    <div>
      <div class="topbar-title">FM26 Player Report</div>
      <div class="topbar-sub">{selected_theme_name.split(' (')[0]} &nbsp;·&nbsp; {today_str}</div>
    </div>
  </div>
  <div class="topbar-right">Season 2026 &nbsp;·&nbsp; {player_pos}</div>
</div>
<div class="accent-bar"></div>

<!-- HERO CARD -->
<div class="hero">
  <div class="hero-photo">
    <svg width="80" height="80" viewBox="0 0 80 80">
      <circle cx="40" cy="28" r="18" fill="{pdf_accent}"/>
      <ellipse cx="40" cy="72" rx="28" ry="20" fill="{pdf_accent}"/>
    </svg>
  </div>
  <div class="hero-info">
    <div class="hero-name">{scout_player}</div>
    <div class="hero-pos">{player_pos}</div>
    <div class="hero-detail">Date of Birth / Age: <span>{player_age}</span></div>
    <div class="hero-detail">Best Fit Role: <span>{best_role_fit} ({best_role_score:.0f}%)</span></div>
    <div class="hero-detail">Market Value: <span>{_value}</span></div>
    <div class="hero-detail">Contract Expires: <span>{_contract}</span></div>
    <div class="hero-detail">Wage: <span>{_wage}</span></div>
  </div>
  <div class="hero-right" style="display:flex;flex-direction:column;justify-content:center;gap:10px;">
    <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Match Grade</div>
    <div class="grade-circle" style="width:72px;height:72px;margin:0 auto;">
      <div class="grade-inner">{_grade}</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:9px;color:#888;margin-top:4px;">Squad Score: {_sq:.0f}/100</div>
    </div>
    <div style="margin-top:8px;">
      <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Recommendation</div>
      <div style="font-size:12px;font-weight:700;color:#111;">{_rec}</div>
    </div>
    <div style="margin-top:8px;">
      <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Projection</div>
      {_proj_html}
    </div>
  </div>
</div>

<!-- SEASON STAT STRIP -->
<div class="stat-strip">
  <div class="stat-item"><div class="stat-val">{player_rat}</div><div class="stat-lbl">Rating</div></div>
  <div class="stat-item"><div class="stat-val">{_apps}</div><div class="stat-lbl">Games</div></div>
  <div class="stat-item"><div class="stat-val">{_goals}</div><div class="stat-lbl">Goals</div></div>
  <div class="stat-item"><div class="stat-val">{_assists}</div><div class="stat-lbl">Assists</div></div>
  <div class="stat-item"><div class="stat-val">{_mins}</div><div class="stat-lbl">Mins/Gm</div></div>
</div>

<div class="body">

  <!-- SUMMARY -->
  <div class="section-title">Summary</div>
  <div class="summary-box"><p>{summary_html}</p></div>

  <!-- STRENGTHS + DEVELOPMENT + GRADE -->
  <div class="section-title">Analysis</div>
  <div class="three-col">
    <div class="panel">
      <div class="panel-title" style="color:#1a8a3a;">✦ Strengths</div>
      {bullet_list(_strengths, '#1a8a3a')}
    </div>
    <div class="panel">
      <div class="panel-title" style="color:#cc7700;">⚠ Development Areas</div>
      {bullet_list(_development, '#cc7700')}
    </div>
    <div class="panel" style="text-align:center;">
      <div class="panel-title">Match Grade</div>
      <div class="grade-circle" style="margin:8px auto;">
        <div class="grade-inner">{_grade}</div>
      </div>
      <div style="font-size:9px;color:#888;margin-top:4px;">Squad Score: {_sq:.0f}/100</div>
      <div style="font-size:9px;color:#888;margin-top:8px;text-align:left;border-top:1px solid #ddd;padding-top:8px;">
        <strong style="color:#111;">Recommendation</strong><br>{_rec}
      </div>
    </div>
  </div>

  <!-- SCATTER CHARTS -->
  {f'<div class="section-title">Performance Charts</div><div class="two-col"><div><div class="chart-label">Goal Threat — xG vs Goals per 90</div><img src="data:image/png;base64,{scatter_goal_b64}"/></div><div><div class="chart-label">Dribbling Efficiency</div><img src="data:image/png;base64,{scatter_drb_b64}"/></div></div>' if scatter_goal_b64 and scatter_drb_b64 else '<div class="section-title">Performance Profile</div><div style="text-align:center;padding:10px 0;"><div class="chart-label">Radar — normalised vs squad (0–100)</div><img src="data:image/png;base64,{radar_b64}" style="max-width:380px"/></div>'}

  <!-- ROLE FIT + STATS -->
  <div class="two-col" style="margin-top:16px;">
    <div>
      <div class="section-title">Role Suitability</div>
      <img src="data:image/png;base64,{roles_b64}" style="max-width:100%"/>
    </div>
    <div>
      <div class="section-title">Key Statistics</div>
      <table>{stats_html}</table>
    </div>
  </div>

  <!-- ALERTS -->
  <div class="section-title">Flags</div>
  {alerts_html}

</div>

<div class="footer">
  <span>FM26 Squad Hub — Player Report — Generated {today_str}</span>
  <span>{scout_player} &nbsp;·&nbsp; {selected_theme_name.split(' (')[0]}</span>
</div>

</body>
</html>"""

                # ── Preview in app ───────────────────────────────
                st.markdown("### Preview")
                st.components.v1.html(html_report, height=900, scrolling=True)

                # ── Download button ──────────────────────────────
                st.download_button(
                    label=f"📥 Download {scout_player} Scout Report (HTML)",
                    data=html_report.encode("utf-8"),
                    file_name=f"scout_report_{scout_player.replace(' ','_')}.html",
                    mime="text/html"
                )
                st.caption("💡 Open the downloaded HTML file in your browser and use File → Print → Save as PDF for a perfect PDF export.")

        # ═══════════════════════════════════════════════════════════
        # TAB 9 — ELITE BENCHMARK (compare vs title-winning squads)
        # ═══════════════════════════════════════════════════════════
        with tab9:
            st.subheader("🏆 Elite Benchmark")
            st.markdown(
                "Upload the squad export of a team you want to reach — Bayern, Real Madrid, Man City, "
                "whoever sets the standard for your target level — and compare your players against "
                "theirs, position by position. Great for grounding Squad Planning decisions in what an "
                "actual title-winning squad looks like at each role, rather than abstract benchmark tables."
            )

            if "elite_reference_squads" not in st.session_state:
                st.session_state["elite_reference_squads"] = {}

            with st.expander("📤 Upload a reference squad", expanded=not st.session_state["elite_reference_squads"]):
                ref_name = st.text_input("Squad name (e.g. 'Bayern Munich 25/26')", key="ref_squad_name")
                ref_file = st.file_uploader("Reference squad CSV export", type=["csv"], key="ref_squad_upload")

                if ref_file and ref_name:
                    if st.button("Add reference squad", key="add_ref_squad_btn"):
                        try:
                            ref_sample = ref_file.read(2048).decode("utf-8", errors="ignore")
                            ref_file.seek(0)
                            ref_sep = ";" if ";" in ref_sample else ","
                            ref_raw = pd.read_csv(ref_file, sep=ref_sep, encoding="utf-8-sig")
                            ref_raw.columns = [c.lstrip("\ufeff").strip() for c in ref_raw.columns]
                            ref_clean = clean_fm_data(ref_raw)
                            st.session_state["elite_reference_squads"][ref_name] = ref_clean
                            st.success(f"✅ Added '{ref_name}' — {len(ref_clean)} players loaded.")
                            st.rerun()
                        except Exception as ref_e:
                            st.error(f"Couldn't read that file: {ref_e}")
                elif ref_file and not ref_name:
                    st.info("Give the squad a name above before adding it.")

                if st.session_state["elite_reference_squads"]:
                    st.caption("Currently loaded: " + ", ".join(
                        f"{n} ({len(d)})" for n, d in st.session_state["elite_reference_squads"].items()
                    ))
                    rm_choice = st.selectbox(
                        "Remove a reference squad", ["—"] + list(st.session_state["elite_reference_squads"].keys()),
                        key="rm_ref_squad"
                    )
                    if rm_choice != "—" and st.button("Remove", key="rm_ref_squad_btn"):
                        del st.session_state["elite_reference_squads"][rm_choice]
                        st.rerun()

            if not st.session_state["elite_reference_squads"]:
                st.info("Upload at least one reference squad above to unlock comparisons.")
            else:
                ref_squad_name = st.selectbox(
                    "Compare against", list(st.session_state["elite_reference_squads"].keys()),
                    key="elite_ref_select"
                )
                ref_df = st.session_state["elite_reference_squads"][ref_squad_name]

                if "Best Pos" not in ref_df.columns or "Best Pos" not in played_df.columns:
                    st.warning("Both squads need a 'Best Pos' column for position-matched comparison.")
                else:
                    common_numeric = sorted([
                        c for c in ref_df.columns
                        if c in played_df.columns
                        and pd.api.types.is_numeric_dtype(ref_df[c])
                        and pd.api.types.is_numeric_dtype(played_df[c])
                        and c not in ["Age"]
                    ])

                    elite_view = st.radio(
                        "View",
                        ["👤 Individual Player vs Elite Position Average", "📊 Whole Squad Overview by Position"],
                        horizontal=True, key="elite_view_mode"
                    )

                    st.divider()

                    if elite_view.startswith("👤"):
                        # ── Individual player comparison ──────────────
                        own_player = st.selectbox("Your player", played_df["Player"].dropna().unique().tolist(), key="elite_own_player")
                        own_row = played_df[played_df["Player"] == own_player].iloc[0]
                        own_pos = own_row.get("Best Pos", None)

                        ref_pos_pool = ref_df[ref_df["Best Pos"] == own_pos]

                        if ref_pos_pool.empty:
                            st.warning(f"'{ref_squad_name}' has no players listed at Best Pos '{own_pos}' to compare against.")
                        else:
                            best_role_for_pos = None
                            for role_name, cfg in FM_BENCHMARKS.items():
                                if own_pos in cfg.get("applies_to", []):
                                    best_role_for_pos = role_name
                                    break
                            role_metrics = list(FM_BENCHMARKS[best_role_for_pos]["metrics"].keys()) if best_role_for_pos else []
                            compare_metrics = [m for m in role_metrics if m in common_numeric] or \
                                               [m for m in ["Rating", "Goals", "Assists", "xG"] if m in common_numeric]

                            st.markdown(f"**{own_player}** ({own_pos}) vs **{ref_squad_name}**'s {len(ref_pos_pool)} player(s) at {own_pos}")

                            comp_rows = []
                            gap_scores = []
                            for m in compare_metrics:
                                own_val = own_row.get(m, None)
                                ref_avg = ref_pos_pool[m].mean()
                                ref_best_idx = ref_pos_pool[m].idxmax()
                                ref_best_val = ref_pos_pool.loc[ref_best_idx, m]
                                ref_best_name = ref_pos_pool.loc[ref_best_idx, "Player"] if "Player" in ref_pos_pool.columns else "—"
                                if pd.notna(own_val) and pd.notna(ref_avg) and ref_avg != 0:
                                    pct_of_avg = round((own_val / ref_avg) * 100, 0)
                                    gap_scores.append(min(pct_of_avg, 150))
                                else:
                                    pct_of_avg = None
                                comp_rows.append({
                                    "Metric": m,
                                    own_player: round(own_val, 2) if pd.notna(own_val) else "—",
                                    f"{ref_squad_name} Avg": round(ref_avg, 2) if pd.notna(ref_avg) else "—",
                                    f"{ref_squad_name} Best": f"{round(ref_best_val,2)} ({ref_best_name})" if pd.notna(ref_best_val) else "—",
                                    "% of Elite Avg": f"{pct_of_avg:.0f}%" if pct_of_avg is not None else "—",
                                })

                            comp_table = pd.DataFrame(comp_rows)
                            st.dataframe(comp_table, use_container_width=True, hide_index=True)

                            if compare_metrics:
                                fig_elite_bar = go.Figure()
                                fig_elite_bar.add_trace(go.Bar(
                                    name=own_player,
                                    x=compare_metrics,
                                    y=[own_row.get(m, 0) or 0 for m in compare_metrics],
                                    marker_color=theme["primary"]
                                ))
                                fig_elite_bar.add_trace(go.Bar(
                                    name=f"{ref_squad_name} Avg",
                                    x=compare_metrics,
                                    y=[ref_pos_pool[m].mean() for m in compare_metrics],
                                    marker_color=theme["secondary"]
                                ))
                                fig_elite_bar.update_layout(
                                    barmode="group", template="plotly_dark", height=420,
                                    title=f"{own_player} vs {ref_squad_name} — {own_pos} benchmark metrics"
                                )
                                st.plotly_chart(fig_elite_bar, use_container_width=True)

                            if gap_scores:
                                elite_gap_pct = round(sum(gap_scores) / len(gap_scores), 0)
                                st.metric(f"Elite Standard Gap — {own_player}", f"{elite_gap_pct:.0f}%",
                                          help=f"Average of {own_player}'s metrics as a % of {ref_squad_name}'s average at {own_pos}. 100% = matches the elite average.")

                                if elite_gap_pct >= 100:
                                    st.success(
                                        f"**{own_player} is at or above {ref_squad_name}'s average standard** for {own_pos} "
                                        f"on the metrics that matter for this role. This is a Keep/Core-level profile against "
                                        f"an elite benchmark, not just against your own squad."
                                    )
                                elif elite_gap_pct >= 80:
                                    st.info(
                                        f"**{own_player} is close ({elite_gap_pct:.0f}%) to {ref_squad_name}'s standard** for {own_pos}. "
                                        f"The gap is real but not huge — targeted training focus on the weakest metric(s) above "
                                        f"could close it within a season or two."
                                    )
                                elif elite_gap_pct >= 60:
                                    st.warning(
                                        f"**{own_player} is meaningfully behind ({elite_gap_pct:.0f}%) {ref_squad_name}'s standard** "
                                        f"for {own_pos}. Fine as squad depth at your current level, but this is the kind of gap "
                                        f"that shows up if you're benchmarking against a genuine title-winning level."
                                    )
                                else:
                                    st.error(
                                        f"**Large gap ({elite_gap_pct:.0f}%) to {ref_squad_name}'s standard** for {own_pos}. "
                                        f"If reaching that level is the actual target, this position is a priority recruitment "
                                        f"area rather than a development one."
                                    )

                    else:
                        # ── Whole squad overview by position ──────────
                        st.markdown(f"Average metrics by **Best Pos**, your squad vs **{ref_squad_name}**.")

                        overview_metric_options = [m for m in common_numeric if m in
                                                    ["Rating", "Goals", "Assists", "xG", "Tck/90", "Int/90",
                                                     "Pr passes/90", "OP-KP/90", "Drb/90", "Sv %", "Hdr %"]] or common_numeric[:6]
                        chosen_overview_metrics = st.multiselect(
                            "Metrics to compare", common_numeric,
                            default=overview_metric_options[:5],
                            key="elite_overview_metrics"
                        )

                        if not chosen_overview_metrics:
                            st.info("Pick at least one metric above.")
                        else:
                            own_positions = played_df["Best Pos"].dropna().unique().tolist()
                            overview_rows = []
                            for pos in sorted(own_positions):
                                own_pos_pool = played_df[played_df["Best Pos"] == pos]
                                ref_pos_pool = ref_df[ref_df["Best Pos"] == pos]
                                if ref_pos_pool.empty:
                                    continue
                                row_rec = {"Best Pos": pos, "Your Players": len(own_pos_pool), f"{ref_squad_name} Players": len(ref_pos_pool)}
                                pos_gap_scores = []
                                for m in chosen_overview_metrics:
                                    own_avg = own_pos_pool[m].mean()
                                    ref_avg = ref_pos_pool[m].mean()
                                    if pd.notna(own_avg) and pd.notna(ref_avg) and ref_avg != 0:
                                        pos_gap_scores.append(min((own_avg / ref_avg) * 100, 150))
                                    row_rec[f"You: {m}"] = round(own_avg, 2) if pd.notna(own_avg) else "—"
                                    row_rec[f"{ref_squad_name}: {m}"] = round(ref_avg, 2) if pd.notna(ref_avg) else "—"
                                row_rec["Elite Gap %"] = f"{sum(pos_gap_scores)/len(pos_gap_scores):.0f}%" if pos_gap_scores else "—"
                                overview_rows.append(row_rec)

                            if not overview_rows:
                                st.warning(f"No overlapping positions found between your squad and {ref_squad_name}.")
                            else:
                                overview_table = pd.DataFrame(overview_rows).sort_values("Elite Gap %", ascending=True)
                                st.dataframe(overview_table, use_container_width=True, hide_index=True)
                                st.caption(
                                    "Elite Gap % = average of your position group's metrics as a % of the reference squad's "
                                    "average at that position. Sort ascending (default) to see your weakest positions "
                                    "relative to the target squad first — those are your priority recruitment areas."
                                )


        # ═══════════════════════════════════════════════════════════
        # TAB 10 — REPLACE / UPGRADE FINDER
        # ═══════════════════════════════════════════════════════════
        with tab10:
            st.subheader("🔄 Replace / Upgrade Finder")
            st.markdown(
                "Pick a player who's leaving (or one you want to upgrade) and this pulls the best-matching "
                "candidates from your Scouting database, ranked on the exact metrics that matter for their role — "
                "with the top contributor for each individual metric called out."
            )

            if played_df.empty or "Player" not in played_df.columns:
                st.warning("No players with appearances found in your squad.")
            elif "scout_df_cache" not in st.session_state:
                st.info(
                    "Upload a scouting database export in the **🕵️ Scouting** tab first — this page reuses "
                    "that same data, so you only need to upload it once."
                )
            else:
                pool_df = st.session_state["scout_df_cache"]

                dep_player = st.selectbox(
                    "Player leaving / to upgrade",
                    sorted(played_df["Player"].dropna().unique().tolist()),
                    key="dep_player_select"
                )
                dep_row = played_df[played_df["Player"] == dep_player].iloc[0]
                dep_pos = dep_row.get("Best Pos", None)

                if pd.isna(dep_pos) or dep_pos is None:
                    st.warning(f"No 'Best Pos' found for {dep_player} — can't match a role profile.")
                else:
                    # ── Match this position to an FM_BENCHMARKS role ──
                    dep_role = None
                    for role_name, cfg in FM_BENCHMARKS.items():
                        if dep_pos in cfg.get("applies_to", []):
                            dep_role = role_name
                            break

                    if dep_role is None:
                        st.warning(f"No benchmark role profile matches position '{dep_pos}'.")
                    else:
                        role_metrics_all = list(FM_BENCHMARKS[dep_role]["metrics"].keys())
                        available_role_metrics = {
                            m: th for m, th in FM_BENCHMARKS[dep_role]["metrics"].items()
                            if m in pool_df.columns
                        }
                        missing_role_metrics = set(role_metrics_all) - set(available_role_metrics)

                        st.markdown(f"**{dep_player}** — Best Pos `{dep_pos}` → matched role: **{dep_role}**")
                        if missing_role_metrics:
                            st.caption(f"⚠️ Not in your scouting export, skipped: {', '.join(sorted(missing_role_metrics))}")

                        if not available_role_metrics:
                            st.warning("None of this role's benchmark metrics are present in your scouting database.")
                        else:
                            # ── Filters ────────────────────────────────
                            st.markdown("#### 🔍 Filters")
                            fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)

                            candidate_pool = pool_df[pool_df.get("Best Pos", pd.Series(dtype=object)) == dep_pos].copy() \
                                if "Best Pos" in pool_df.columns else pool_df.copy()

                            with fcol1:
                                if "Age" in candidate_pool.columns and candidate_pool["Age"].notna().any():
                                    age_min_r, age_max_r = int(candidate_pool["Age"].min()), int(candidate_pool["Age"].max())
                                    age_range = st.slider("Age range", age_min_r, age_max_r, (age_min_r, age_max_r), key="rf_age")
                                    candidate_pool = candidate_pool[
                                        candidate_pool["Age"].between(age_range[0], age_range[1]) | candidate_pool["Age"].isna()
                                    ]
                            with fcol2:
                                if "Value (£M est.)" in candidate_pool.columns and candidate_pool["Value (£M est.)"].notna().any():
                                    max_val_r = float(candidate_pool["Value (£M est.)"].max())
                                    val_cap = st.number_input("Max value (£M)", value=round(max_val_r, 1), min_value=0.0, key="rf_val")
                                    candidate_pool = candidate_pool[
                                        (candidate_pool["Value (£M est.)"] <= val_cap) | candidate_pool["Value (£M est.)"].isna()
                                    ]
                            with fcol3:
                                if "Division" in candidate_pool.columns:
                                    div_opts = ["All"] + sorted(candidate_pool["Division"].dropna().unique().tolist())
                                    div_pick = st.selectbox("Division", div_opts, key="rf_div")
                                    if div_pick != "All":
                                        candidate_pool = candidate_pool[candidate_pool["Division"] == div_pick]
                            with fcol4:
                                exclude_own_squad = st.checkbox("Exclude own squad players", value=True, key="rf_excl_own")
                                if exclude_own_squad and "Player" in candidate_pool.columns and "Player" in played_df.columns:
                                    own_names = set(played_df["Player"].dropna().unique().tolist())
                                    candidate_pool = candidate_pool[~candidate_pool["Player"].isin(own_names)]
                            with fcol5:
                                min_minutes_r = 0
                                if "Minutes" in candidate_pool.columns and candidate_pool["Minutes"].notna().any():
                                    candidate_pool["Minutes"] = pd.to_numeric(candidate_pool["Minutes"], errors="coerce")
                                    minutes_max_r = int(candidate_pool["Minutes"].max())
                                    min_minutes_r = st.number_input(
                                        "Min minutes played", value=min(450, minutes_max_r), min_value=0,
                                        max_value=minutes_max_r, step=90, key="rf_min_minutes",
                                        help="Per-90 stats from a handful of matches are noisy — filter out small sample sizes."
                                    )
                                    candidate_pool = candidate_pool[candidate_pool["Minutes"] >= min_minutes_r]
                                else:
                                    st.caption("No 'Minutes' column in this export — can't filter or adjust for sample size.")

                            st.caption(f"{len(candidate_pool)} candidates at {dep_pos} match your filters.")

                            if candidate_pool.empty:
                                st.warning("No candidates match these filters. Try widening them.")
                            else:
                                # ── Composite score for candidates ──────
                                score_cols = []
                                for m, (good, ok, poor) in available_role_metrics.items():
                                    score_col = f"__score_{m}"
                                    candidate_pool[score_col] = pd.to_numeric(
                                        candidate_pool[m], errors="coerce"
                                    ).apply(lambda v: benchmark_score(v, good, ok, poor))
                                    score_cols.append(score_col)
                                candidate_pool["Recruitment Score"] = candidate_pool[score_cols].mean(axis=1, skipna=True).round(1)

                                # ── Minutes-adjusted reliability shrinkage ──
                                # Per-90 rates from a small sample are noisy (e.g. 1 goal in
                                # 90 minutes looks elite but tells you almost nothing). Shrink
                                # each candidate's score toward the filtered pool's average,
                                # proportional to how far below a "reliable sample" cutoff
                                # their minutes are — so low-minute overperformers don't
                                # dominate the leaderboard on noise.
                                has_minutes = "Minutes" in candidate_pool.columns and candidate_pool["Minutes"].notna().any()
                                if has_minutes:
                                    apply_minutes_adj = st.checkbox(
                                        "⏱️ Apply minutes-adjusted reliability (shrink small-sample scores toward the pool average)",
                                        value=True, key="rf_minutes_adj"
                                    )
                                    reliable_minutes_threshold = st.slider(
                                        "Minutes considered a 'reliable sample'", 450, 2700, 900, step=90,
                                        key="rf_reliable_mins", disabled=not apply_minutes_adj,
                                        help="Candidates at or above this many minutes keep their raw score. Below it, their score is pulled toward the pool average in proportion to how little they've played."
                                    )
                                    if apply_minutes_adj:
                                        pool_avg_score = candidate_pool["Recruitment Score"].mean()
                                        confidence = (candidate_pool["Minutes"].fillna(0) / reliable_minutes_threshold).clip(upper=1.0)
                                        candidate_pool["Raw Recruitment Score"] = candidate_pool["Recruitment Score"]
                                        candidate_pool["Recruitment Score"] = (
                                            candidate_pool["Recruitment Score"] * confidence
                                            + pool_avg_score * (1 - confidence)
                                        ).round(1)
                                        st.caption(
                                            f"Scores below {reliable_minutes_threshold} minutes are blended toward the pool average "
                                            f"({round(pool_avg_score,1)}) — the fewer minutes played, the more their raw score is pulled down "
                                            f"toward that baseline. Raw (unadjusted) score is still shown in the leaderboard."
                                        )



                                # ── Composite score for the departing player (same metrics) ──
                                dep_scores = []
                                dep_raw = {}
                                for m, (good, ok, poor) in available_role_metrics.items():
                                    dv = pd.to_numeric(pd.Series([dep_row.get(m, None)]), errors="coerce").iloc[0]
                                    dep_raw[m] = dv
                                    sc = benchmark_score(dv, good, ok, poor)
                                    if sc is not None:
                                        dep_scores.append(sc)
                                dep_composite = round(sum(dep_scores) / len(dep_scores), 1) if dep_scores else None

                                if dep_composite is not None:
                                    st.metric(f"{dep_player}'s current Recruitment Score ({dep_role} metrics)", f"{dep_composite}/100")

                                st.divider()

                                # ── Top contributors per metric ─────────
                                st.markdown("#### 🏅 Highest Contributor Per Metric")
                                st.caption(f"Best available candidate for each of {dep_role}'s key metrics, vs {dep_player}'s own number.")

                                contrib_rows = []
                                for m in available_role_metrics:
                                    m_series = pd.to_numeric(candidate_pool[m], errors="coerce")
                                    if m_series.notna().sum() == 0:
                                        continue
                                    top_idx = m_series.idxmax()
                                    top_name = candidate_pool.loc[top_idx, "Player"] if "Player" in candidate_pool.columns else "—"
                                    top_club = candidate_pool.loc[top_idx, "Club"] if "Club" in candidate_pool.columns else "—"
                                    top_val = m_series.loc[top_idx]
                                    dv = dep_raw.get(m, None)
                                    beats_dep = (pd.notna(dv) and top_val > dv) if pd.notna(top_val) else False
                                    contrib_rows.append({
                                        "Metric": m,
                                        "Top Contributor": f"{top_name} ({top_club})",
                                        "Their Value": round(float(top_val), 2) if pd.notna(top_val) else "—",
                                        f"{dep_player}'s Value": round(float(dv), 2) if pd.notna(dv) else "—",
                                        "Upgrade?": "✅ Yes" if beats_dep else ("➖ No" if pd.notna(dv) else "—"),
                                    })

                                if contrib_rows:
                                    st.dataframe(pd.DataFrame(contrib_rows), use_container_width=True, hide_index=True)

                                st.divider()

                                # ── Ranked leaderboard ──────────────────
                                st.markdown("#### 📋 Ranked Candidates")
                                sort_desc = candidate_pool.sort_values("Recruitment Score", ascending=False)

                                display_cols = [c for c in ["Player","Club","Division","Age","Minutes","Value (£M est.)","Wage (£/wk)","Raw Recruitment Score","Recruitment Score"] if c in sort_desc.columns]
                                display_cols += [m for m in available_role_metrics if m in sort_desc.columns]

                                top_n = st.slider("Show top N candidates", 3, min(30, len(sort_desc)), min(10, len(sort_desc)), key="rf_top_n")
                                leaderboard = sort_desc[display_cols].head(top_n).reset_index(drop=True)

                                if dep_composite is not None:
                                    leaderboard.insert(
                                        leaderboard.columns.get_loc("Recruitment Score") + 1,
                                        "vs " + dep_player,
                                        leaderboard["Recruitment Score"].apply(
                                            lambda s: f"+{round(s - dep_composite,1)}" if s >= dep_composite else f"{round(s - dep_composite,1)}"
                                        )
                                    )

                                st.dataframe(leaderboard, use_container_width=True, hide_index=True)

                                if dep_composite is not None:
                                    upgrades = sort_desc[sort_desc["Recruitment Score"] > dep_composite]
                                    st.caption(
                                        f"**{len(upgrades)} of {len(sort_desc)}** filtered candidates score higher than "
                                        f"{dep_player}'s current {dep_composite}/100 on these metrics — those are genuine upgrades, "
                                        f"not just replacements."
                                    )

                                # ── Bar chart of top candidates ─────────
                                if len(sort_desc) > 0:
                                    bar_chart_df = sort_desc[["Player","Recruitment Score"]].head(top_n)
                                    fig_rf_bar = px.bar(
                                        bar_chart_df, x="Player", y="Recruitment Score",
                                        color="Recruitment Score", color_continuous_scale=theme["chart_scale"],
                                        template="plotly_dark", height=420,
                                        title=f"Top {top_n} candidates — Recruitment Score for {dep_pos}"
                                    )
                                    if dep_composite is not None:
                                        fig_rf_bar.add_hline(
                                            y=dep_composite, line_dash="dash", line_color="white",
                                            annotation_text=f"{dep_player}: {dep_composite}", annotation_position="top left"
                                        )
                                    st.plotly_chart(fig_rf_bar, use_container_width=True)


    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.exception(e)
