"""
Export GitHub Pages Static Site
=================================
Generates a mobile-responsive index.html with today's predictions.
Output goes to: nba-elo-engine/pages/index.html

Run manually:   python scripts/export_github_pages.py
Run from bat:   called by push_github_pages.bat
"""

import sys
import os

# Ensure engine root and src are on path
_engine_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_src_dir = os.path.join(_engine_root, 'src')
for _p in [_engine_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hashlib
import json
import re
import pandas as pd
from datetime import datetime, timedelta

LEDGER_START = 20261001  # first season whose picks are all locked before tip-off

# --------------------------------------------------------------------------- #
# Team logo CDN URLs (cdn.nba.com)
# --------------------------------------------------------------------------- #
_NBA_LOGO_BASE = 'https://cdn.nba.com/logos/nba/{nba_id}/primary/L/logo.svg'

TEAM_LOGOS = {
    'Atlanta Hawks':          _NBA_LOGO_BASE.format(nba_id=1610612737),
    'Boston Celtics':         _NBA_LOGO_BASE.format(nba_id=1610612738),
    'Brooklyn Nets':          _NBA_LOGO_BASE.format(nba_id=1610612751),
    'Charlotte Hornets':      _NBA_LOGO_BASE.format(nba_id=1610612766),
    'Chicago Bulls':          _NBA_LOGO_BASE.format(nba_id=1610612741),
    'Cleveland Cavaliers':    _NBA_LOGO_BASE.format(nba_id=1610612739),
    'Dallas Mavericks':       _NBA_LOGO_BASE.format(nba_id=1610612742),
    'Denver Nuggets':         _NBA_LOGO_BASE.format(nba_id=1610612743),
    'Detroit Pistons':        _NBA_LOGO_BASE.format(nba_id=1610612765),
    'Golden State Warriors':  _NBA_LOGO_BASE.format(nba_id=1610612744),
    'Houston Rockets':        _NBA_LOGO_BASE.format(nba_id=1610612745),
    'Indiana Pacers':         _NBA_LOGO_BASE.format(nba_id=1610612754),
    'LA Clippers':            _NBA_LOGO_BASE.format(nba_id=1610612746),
    'Los Angeles Clippers':   _NBA_LOGO_BASE.format(nba_id=1610612746),
    'Los Angeles Lakers':     _NBA_LOGO_BASE.format(nba_id=1610612747),
    'Memphis Grizzlies':      _NBA_LOGO_BASE.format(nba_id=1610612763),
    'Miami Heat':             _NBA_LOGO_BASE.format(nba_id=1610612748),
    'Milwaukee Bucks':        _NBA_LOGO_BASE.format(nba_id=1610612749),
    'Minnesota Timberwolves': _NBA_LOGO_BASE.format(nba_id=1610612750),
    'New Orleans Pelicans':   _NBA_LOGO_BASE.format(nba_id=1610612740),
    'New York Knicks':        _NBA_LOGO_BASE.format(nba_id=1610612752),
    'Oklahoma City Thunder':  _NBA_LOGO_BASE.format(nba_id=1610612760),
    'Orlando Magic':          _NBA_LOGO_BASE.format(nba_id=1610612753),
    'Philadelphia 76ers':     _NBA_LOGO_BASE.format(nba_id=1610612755),
    'Phoenix Suns':           _NBA_LOGO_BASE.format(nba_id=1610612756),
    'Portland Trail Blazers': _NBA_LOGO_BASE.format(nba_id=1610612757),
    'Sacramento Kings':       _NBA_LOGO_BASE.format(nba_id=1610612758),
    'San Antonio Spurs':      _NBA_LOGO_BASE.format(nba_id=1610612759),
    'Toronto Raptors':        _NBA_LOGO_BASE.format(nba_id=1610612761),
    'Utah Jazz':              _NBA_LOGO_BASE.format(nba_id=1610612762),
    'Washington Wizards':     _NBA_LOGO_BASE.format(nba_id=1610612764),
}

def get_team_logo(team_name):
    return TEAM_LOGOS.get(team_name, 'https://cdn.nba.com/logos/nba/logo.svg')


# ESPN CDN abbreviations (differ from ours for GS, NO, NY, SA)
_ESPN_ABBREV_MAP = {
    'GSW': 'gs', 'NOP': 'no', 'NYK': 'ny', 'SAS': 'sa',
    'UTA': 'utah',  # ESPN's file is utah.png; uta.png 404s
}

def get_logo_by_abbrev(abbrev):
    """Return ESPN CDN logo URL for a 3-letter team abbrev."""
    espn = _ESPN_ABBREV_MAP.get(abbrev, abbrev.lower())
    return f'https://a.espncdn.com/i/teamlogos/nba/500/{espn}.png'


TEAM_ABBREVS = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL',
    'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK',
    'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI',
    'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC',
    'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA',
    'Washington Wizards': 'WSH',
}


# ESPN team abbreviations for injury page links
ESPN_TEAM_ABBREVS = {
    'Atlanta Hawks': 'atl', 'Boston Celtics': 'bos', 'Brooklyn Nets': 'bkn',
    'Charlotte Hornets': 'cha', 'Chicago Bulls': 'chi', 'Cleveland Cavaliers': 'cle',
    'Dallas Mavericks': 'dal', 'Denver Nuggets': 'den', 'Detroit Pistons': 'det',
    'Golden State Warriors': 'gs', 'Houston Rockets': 'hou', 'Indiana Pacers': 'ind',
    'Los Angeles Clippers': 'lac', 'LA Clippers': 'lac', 'Los Angeles Lakers': 'lal',
    'Memphis Grizzlies': 'mem', 'Miami Heat': 'mia', 'Milwaukee Bucks': 'mil',
    'Minnesota Timberwolves': 'min', 'New Orleans Pelicans': 'no', 'New York Knicks': 'ny',
    'Oklahoma City Thunder': 'okc', 'Orlando Magic': 'orl', 'Philadelphia 76ers': 'phi',
    'Phoenix Suns': 'phx', 'Portland Trail Blazers': 'por', 'Sacramento Kings': 'sac',
    'San Antonio Spurs': 'sa', 'Toronto Raptors': 'tor', 'Utah Jazz': 'utah',
    'Washington Wizards': 'wsh',
}

def get_espn_injury_url(team_name):
    abbrev = ESPN_TEAM_ABBREVS.get(team_name, '')
    if abbrev:
        return f'https://www.espn.com/nba/team/injuries/_/name/{abbrev}'
    return 'https://www.espn.com/nba/injuries'


# --------------------------------------------------------------------------- #
# Data loading helpers
# --------------------------------------------------------------------------- #

def load_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def get_today_predictions():
    """Pull today's predictions using the same pipeline as the newsletter."""
    try:
        from src.scrapers.nba_api_data_fetcher import get_todays_games as fetch_nba_games
        from src.utils.file_io import load_csv_to_dataframe

        # Same data loading as newsletter
        team_history = load_csv_to_dataframe('data/exports/team_elo_history_phase_1_6.csv')
        latest_teams = team_history.sort_values('date').groupby('team_id').last().reset_index()
        latest_teams['rating'] = latest_teams['rating_after']
        team_ratings = latest_teams[['team_id', 'team_name', 'rating']].copy()

        games = fetch_nba_games()
        if not games:
            return []

        # Import the same predict_game function the newsletter uses
        import importlib.util, types
        # Inline the core prediction to avoid loading the full newsletter module
        from src.utils.elo_math import calculate_win_probability, elo_diff_to_expected_margin
        import yaml as _yaml
        _score_cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'score_model.yaml')
        try:
            with open(_score_cfg_path) as _f:
                _score_model = _yaml.safe_load(_f).get('score_model', {})
        except Exception:
            _score_model = {'intercept': 2.84, 'coefficient': 0.034507, 'league_avg_ppg': 114.15}
        _score_intercept = _score_model.get('intercept', 2.84)
        _score_coef      = _score_model.get('coefficient', 0.034507)
        _league_avg      = _score_model.get('league_avg_ppg', 114.15)

        # Quarter model (Sprint 3)
        _q_cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'quarter_model.yaml')
        _Q_DEFAULTS = {
            'q1': {'intercept': -0.7353, 'coefficient': 0.010391, 'league_avg': 27.972},
            'q2': {'intercept':  0.3779, 'coefficient': 0.006782, 'league_avg': 28.560},
            'q3': {'intercept': -1.6465, 'coefficient': 0.004861, 'league_avg': 28.028},
            'q4': {'intercept':  1.0494, 'coefficient': 0.000163, 'league_avg': 26.620},
        }
        try:
            with open(_q_cfg_path) as _f:
                _q_raw = _yaml.safe_load(_f).get('quarter_model', {})
            _quarter_cfg = {q: _q_raw.get(q, _Q_DEFAULTS[q]) for q in ['q1', 'q2', 'q3', 'q4']}
        except Exception:
            _quarter_cfg = _Q_DEFAULTS

        predictions = []
        for game in games:
            home_id   = game.get('home_id')
            away_id   = game.get('away_id')
            home_name = game.get('home_team', '')
            away_name = game.get('away_team', '')
            game_time = game.get('time', 'TBD')
            game_id   = game.get('game_id', '')

            home_row = team_ratings[team_ratings['team_id'] == home_id]
            away_row = team_ratings[team_ratings['team_id'] == away_id]
            if home_row.empty or away_row.empty:
                continue

            home_elo = float(home_row.iloc[0]['rating'])
            away_elo = float(away_row.iloc[0]['rating'])
            home_prob = calculate_win_probability(home_elo, away_elo, home_advantage=60)

            # Score prediction
            _pred_margin = elo_diff_to_expected_margin(
                home_elo - away_elo, coefficient=_score_coef, intercept=_score_intercept
            )
            _pred_home_score = max(70, round(_league_avg + _pred_margin / 2))
            _pred_away_score = max(70, round(_league_avg - _pred_margin / 2))

            # Quarter predictions (Sprint 3)
            _elo_diff_gtp = home_elo - away_elo
            _q_preds = {}
            for _qn, _qk in [(1, 'q1'), (2, 'q2'), (3, 'q3'), (4, 'q4')]:
                _qc   = _quarter_cfg[_qk]
                _qmgn = _qc['intercept'] + _qc['coefficient'] * _elo_diff_gtp
                _qavg = _qc['league_avg']
                _q_preds[f'predicted_home_q{_qn}'] = max(15, round(_qavg + _qmgn / 2))
                _q_preds[f'predicted_away_q{_qn}'] = max(15, round(_qavg - _qmgn / 2))

            if home_prob >= 0.5:
                winner, win_prob, is_home_win = home_name, home_prob, True
            else:
                winner, win_prob, is_home_win = away_name, 1.0 - home_prob, False

            conf_label, conf_class = _conf(win_prob), ''
            tossup = win_prob < 0.60
            nba_url = f'https://www.nba.com/game/{game_id}' if game_id else 'https://www.nba.com/games'

            predictions.append({
                'time': game_time,
                'home': home_name,
                'away': away_name,
                'nba_url': nba_url,
                'winner': winner,
                'win_prob': win_prob,
                'home_prob': home_prob,
                'away_prob': 1.0 - home_prob,
                'is_home_win': is_home_win,
                'conf_label': conf_label,
                'conf_class': conf_class,
                'tossup': tossup,
                'home_elo': home_elo,
                'away_elo': away_elo,
                'game_status_code': game.get('game_status_code', 1),
                'home_id': home_id,
                'away_id': away_id,
                'logged_at': None,
                'predicted_home_score': _pred_home_score,
                'predicted_away_score': _pred_away_score,
                'predicted_margin': round(_pred_margin, 1),
                **_q_preds,
            })

        # Sort: scheduled first, then live, then final
        _overlay_logged(predictions)
        status_order = {1: 0, 2: 1, 3: 2}
        predictions.sort(key=lambda x: (status_order.get(x.get('game_status_code', 1), 0), x['time']))
        return predictions
    except Exception as e:
        print(f"  Warning: Could not load predictions ({e})")
        return []


def _truthy(v):
    return v is True or v == 1 or str(v).strip().lower() in ('true', '1', '1.0')


def _graded(df):
    """Rows with a result, with `correct` coerced to a real bool. The column comes
    back as bool, object or float depending on whether any row is still blank."""
    if df.empty or 'correct' not in df.columns:
        return df.iloc[0:0]
    g = df[df['correct'].notna()].copy()
    g['correct'] = g['correct'].map(_truthy)
    return g


def _season_start(today=None):
    """Oct 1 of the current season, as YYYYMMDD. A game in Jan-Sep belongs to the
    season that started the previous October."""
    today = today or datetime.now()
    year = today.year if today.month >= 10 else today.year - 1
    return year * 10000 + 1001, f"{year}-{(year + 1) % 100:02d}"


def get_week_results(n_days=3):
    """The last few graded game days, newest first. Same in season and out: the
    offseason simply shows the last nights of the playoffs, so the public receipts
    are never blank."""
    df = _graded(load_csv('data/exports/prediction_tracking.csv'))
    if df.empty:
        return [], {}

    days = []
    for date_int in sorted(df['date'].unique())[-n_days:][::-1]:
        group = df[df['date'] == date_int]
        d = datetime.strptime(str(int(date_int)), '%Y%m%d')
        rows = []
        for _, row in group.iterrows():
            home, away = row.get('home_team_name', ''), row.get('away_team_name', '')
            rows.append({
                'home': home,
                'away': away,
                'pick': home if row.get('predicted_winner') == 'home' else away,
                'pick_prob': float(row.get('confidence', 0) or 0),
                'correct': bool(row['correct']),
                'home_score': row.get('actual_home_score', ''),
                'away_score': row.get('actual_away_score', ''),
            })
        correct = sum(r['correct'] for r in rows)
        days.append({
            'label': f"{d:%b} {d.day}",
            'weekday': f"{d:%A}",
            'rows': rows,
            'correct': correct,
            'total': len(rows),
        })

    total = sum(d['total'] for d in days)
    correct = sum(d['correct'] for d in days)
    return days, {'total': total, 'correct': correct}


def _summary(s):
    n = len(s)
    if not n:
        return {'n': 0, 'correct': 0, 'pct': 'n/a', 'brier': 'n/a'}
    c = int(s['correct'].sum())
    y = (s['actual_winner'] == 'home').astype(int)
    brier = float(((s['predicted_home_prob'] - y) ** 2).mean())
    return {'n': n, 'correct': c, 'pct': f"{c / n * 100:.1f}", 'brier': f"{brier:.4f}"}


def get_season_stats():
    """Two records, never blended. `live` is the current season, every pick logged
    before tip-off. `audit` is 2025-26: a walk-forward replay rebuilt after the
    fact (all 657 rows carry post-game timestamps), honest but a different claim.
    Until 2026-11-17 the site added them together as one '845 games' number."""
    df = _graded(load_csv('data/exports/prediction_tracking.csv'))
    if df.empty:
        return {}
    df = df.sort_values('date')
    start, label = _season_start()
    live = df[df['date'] >= max(start, LEDGER_START)]
    audit = df[(df['date'] >= 20251001) & (df['date'] < LEDGER_START)]

    cutoff7 = int((datetime.now() - timedelta(days=7)).strftime('%Y%m%d'))
    last7 = live[live['date'] >= cutoff7]
    close = live[live['confidence'] < 0.60]

    calib = []
    for lo, hi in [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]:
        b = live[(live['confidence'] >= lo) & (live['confidence'] < hi)]
        if len(b):
            calib.append({'lo': lo, 'hi': min(hi, 1.0), 'n': len(b),
                          'stated': float(b['confidence'].mean()),
                          'won': float(b['correct'].mean())})

    first = int(live['date'].min()) if len(live) else None
    day_no = ((datetime.now() - datetime.strptime(str(first), '%Y%m%d')).days + 1) if first else None

    return {
        'season_label': label,
        'live': _summary(live),
        'audit': _summary(audit),
        'last7': (int(last7['correct'].sum()), len(last7) - int(last7['correct'].sum())),
        'close': (int(close['correct'].sum()), len(close) - int(close['correct'].sum())),
        'calib': calib,
        'day': day_no,
        'recent': live.tail(6).iloc[::-1].to_dict('records'),
    }


def get_weekly_summary():
    """Last 7 days broken down by date with W-L and accuracy bar."""
    df = load_csv('data/exports/prediction_tracking.csv')
    if df.empty:
        return []

    df = df.sort_values('date')
    today_int = int(datetime.now().strftime('%Y%m%d'))
    cutoff = int((datetime.now() - timedelta(days=7)).strftime('%Y%m%d'))
    week = df[(df['date'] >= cutoff) & (df['date'] < today_int)]
    if week.empty:
        return []

    days = []
    for date_int, group in week.groupby('date'):
        total   = len(group)
        correct = int(group['correct'].sum())
        pct     = correct / total if total > 0 else 0
        # Format date as "Mon-02-26" (Windows-compatible)
        try:
            d = datetime.strptime(str(date_int), '%Y%m%d')
            label = f"{d.strftime('%a')}-{d.day:02d}-{d.strftime('%y')}"
        except Exception:
            label = str(date_int)
        days.append({
            'label': label,
            'correct': correct,
            'total': total,
            'pct': pct,
            'pct_str': f"{pct*100:.0f}%",
        })

    return days


def get_injuries_for_games(predictions):
    """Fetch ESPN injuries for teams playing today, cross-referenced with player ELO."""
    if not predictions:
        return {}
    try:
        from scrapers.espn_team_injuries import get_injury_report
        injury_data = get_injury_report()
        if not injury_data:
            return {}

        # Build player ELO lookup for impact ranking
        ratings = load_csv('data/exports/player_ratings_bpm_adjusted.csv')
        elo_lookup = {}
        if not ratings.empty:
            for _, row in ratings.iterrows():
                elo_lookup[row['player_name'].lower()] = float(row['rating'])

        # Teams playing today
        today_teams = set()
        for p in predictions:
            today_teams.add(p['home'])
            today_teams.add(p['away'])

        result = {}
        for team_name in today_teams:
            injuries = injury_data.get(team_name, [])
            if not injuries:
                continue
            # Rank by player ELO (highest impact first), limit to 3
            ranked = sorted(
                injuries,
                key=lambda x: elo_lookup.get(x.get('name', '').lower(), 0),
                reverse=True
            )[:3]
            key_injuries = []
            for inj in ranked:
                name   = inj.get('name', '')
                status = inj.get('status', '')
                elo    = elo_lookup.get(name.lower(), 0)
                if elo > 1600:
                    impact = 'star'
                elif elo > 1400:
                    impact = 'starter'
                else:
                    impact = 'role'
                key_injuries.append({
                    'name': name,
                    'status': status,
                    'impact': impact,
                    'elo': int(elo) if elo else 0,
                })
            if key_injuries:
                result[team_name] = key_injuries

        return result
    except Exception as e:
        return {}


def get_top_players(n=15):
    """Top N players by ELO from ratings + mapping."""
    ratings = load_csv('data/exports/player_ratings_bpm_adjusted.csv')
    mapping = load_csv('data/exports/player_team_mapping.csv')
    if ratings.empty:
        return []

    df = ratings.merge(mapping, on='player_name', how='left')
    df['team_name'] = df['team_name'].fillna('')
    if 'raw_rating' not in df.columns:
        df['raw_rating'] = df['rating']
    cols = ['player_name', 'team_name', 'rating', 'raw_rating', 'games_played']
    top = df.nlargest(n, 'rating')[cols]

    players = []
    for i, (_, row) in enumerate(top.iterrows(), 1):
        team_name = row['team_name']
        team_abbr = TEAM_ABBREVS.get(team_name, team_name[:3].upper()) if team_name else 'No team'
        elo = int(row['rating'])
        adj = int(round(row['rating'] - row['raw_rating']))
        players.append({
            'rank': i,
            'name': row['player_name'],
            'team': team_name,
            'team_abbr': team_abbr,
            'team_logo': get_logo_by_abbrev(team_abbr) if team_name else '',
            'elo': elo,
            'adj': adj,  # model adjustment vs raw box score (+boost / -dock)
            'games': int(row['games_played']),
        })
    return players


def get_all_players(min_games=8, cap=400):
    """Full searchable roster for the player-lookup box: every rated player with
    a meaningful sample, ranked by model rating. Compact keys keep the embedded
    JSON small; the front-end filter renders these into the same table."""
    ratings = load_csv('data/exports/player_ratings_bpm_adjusted.csv')
    mapping = load_csv('data/exports/player_team_mapping.csv')
    if ratings.empty:
        return []

    df = ratings.merge(mapping, on='player_name', how='left')
    df['team_name'] = df['team_name'].fillna('')
    if 'raw_rating' not in df.columns:
        df['raw_rating'] = df['rating']
    df = df[df['games_played'] >= min_games].nlargest(cap, 'rating')

    out = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        team_name = row['team_name']
        team_abbr = TEAM_ABBREVS.get(team_name, team_name[:3].upper()) if team_name else 'No team'
        out.append({
            'rank': i,
            'name': row['player_name'],
            'abbr': team_abbr,
            'logo': get_logo_by_abbrev(team_abbr) if team_name else '',
            'elo': int(row['rating']),
            'adj': int(round(row['rating'] - row['raw_rating'])),
            'games': int(row['games_played']),
        })
    return out


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #

def _is_edt(date):
    """Return True if America/New_York is on EDT (UTC-4) for the given date."""
    # DST: 2nd Sunday in March → 1st Sunday in November
    year = date.year
    mar1 = datetime(year, 3, 1)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = datetime(year, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    return dst_start.date() <= date.date() < dst_end.date()


_TIME_RE = re.compile(r'(\d{1,2}:\d{2})\s*([AP]M)', re.I)


def _clean_time(time_str):
    """'11/17 - 10:30 PM EST' (ESPN) or '7:30 pm ET' (NBA) -> '10:30 PM ET'."""
    m = _TIME_RE.search(time_str or '')
    return f"{m.group(1)} {m.group(2).upper()} ET" if m else (time_str or 'TBD')


def _to_iso_et(date_iso, time_str):
    """Scheduled ET time -> ISO-8601 with the right ET offset, for local display."""
    m = _TIME_RE.search(time_str or '')
    if not m:
        return None
    try:
        dt = datetime.strptime(f"{date_iso} {m.group(1)} {m.group(2).upper()}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        return None
    offset = '-04:00' if _is_edt(dt) else '-05:00'
    return f"{date_iso}T{dt.strftime('%H:%M')}:00{offset}"


def _conf(win_prob):
    if win_prob >= 0.75:
        return 'High confidence'
    if win_prob >= 0.63:
        return 'Medium confidence'
    return 'Too close to call'


def _overlay_logged(predictions):
    """Show the pick we grade, not a second opinion.

    The tracker locks each game into pending_predictions.csv with the deployed
    model's rest and form adjustments. This page used to recompute its own number
    from raw ratings, and the two disagreed by up to ten points (2026-11-17: Lakers
    75% on the page, 84% in the record). Logged games now show the logged pick;
    anything not yet logged is marked as outside the record.
    """
    frames = [load_csv(p) for p in ('data/exports/pending_predictions.csv',
                                    'data/exports/prediction_tracking.csv')]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return
    d = pd.concat(frames, ignore_index=True)
    d = d[d['date'] == int(datetime.now().strftime('%Y%m%d'))]
    logged = {(int(r['home_team_id']), int(r['away_team_id'])): r for _, r in d.iterrows()}
    for p in predictions:
        r = logged.get((p.get('home_id'), p.get('away_id')))
        if r is None:
            continue
        hp = float(r['predicted_home_prob'])
        home_pick = r['predicted_winner'] == 'home'
        win_prob = hp if home_pick else 1 - hp
        p.update({
            'home_prob': hp, 'away_prob': 1 - hp, 'is_home_win': home_pick,
            'winner': p['home'] if home_pick else p['away'], 'win_prob': win_prob,
            'conf_label': _conf(win_prob), 'tossup': win_prob < 0.60,
            'home_elo': float(r['home_elo']), 'away_elo': float(r['away_elo']),
            'logged_at': str(r['timestamp'])[11:16],
        })
        if pd.notna(r.get('predicted_home_score')):
            p['predicted_home_score'] = int(r['predicted_home_score'])
            p['predicted_away_score'] = int(r['predicted_away_score'])


def _barcode(seed, w=150, h=30):
    """Decorative, deterministic bars from a pick's id. The same pick always draws
    the same code, so a screenshot and the ledger row visibly belong together."""
    hx = hashlib.sha1(str(seed).encode()).hexdigest() * 2
    x, bars = 0, []
    for ch in hx:
        v = int(ch, 16)
        bw, gap = 1 + v % 3, 1 + (v >> 2) % 2
        if x + bw > w:
            break
        bars.append(f'<rect x="{x}" width="{bw}" height="{h}"/>')
        x += bw + gap
    return (f'<svg class="barcode" viewBox="0 0 {x} {h}" preserveAspectRatio="none" '
            f'aria-hidden="true">{"".join(bars)}</svg>')


def _abbr(team_name):
    return TEAM_ABBREVS.get(team_name, (team_name or '???')[:3].upper())


def _ticket(p, n, total, date_iso):
    status = p.get('game_status_code', 1)
    if status == 3:
        status_html = '<span class="t-status">Final</span>'
    elif status == 2:
        status_html = f'<span class="t-status live">Live &middot; {p["time"]}</span>'
    else:
        t = _clean_time(p['time'])
        iso = _to_iso_et(date_iso, p['time'])
        status_html = (f'<span class="t-status" data-iso="{iso}">{t}</span>' if iso
                       else f'<span class="t-status">{t}</span>')

    away_pick = not p['is_home_win']
    pick_pct = round(p['win_prob'] * 100)
    teams = []
    for side, name, elo, is_pick in (('away', p['away'], p['away_elo'], away_pick),
                                     ('home', p['home'], p['home_elo'], not away_pick)):
        teams.append(
            f'<div class="t-team {side}{" is-pick" if is_pick else ""}">'
            f'<div class="abbr"><img src="{get_logo_by_abbrev(_abbr(name))}" alt="" '
            f'onerror="this.style.display=\'none\'"><span>{_abbr(name)}</span></div>'
            f'<div class="name">{name}</div></div>')

    proj = ''
    if p.get('predicted_home_score'):
        proj = f"Proj {p['predicted_away_score']}&ndash;{p['predicted_home_score']}"

    if p.get('logged_at'):
        stub_cls, stub_foot = 't-stub', f'Logged {p["logged_at"]} ET'
    else:
        stub_cls, stub_foot = 't-stub unlogged', 'Not in the record'

    return f"""
      <article class="ticket">
        <a class="ticket-link" href="{p['nba_url']}" target="_blank" rel="noopener" aria-label="{p['away']} at {p['home']} on NBA.com"></a>
        <div class="t-main">
          <div class="t-top mono"><span>Game {n:02d} / {total:02d}</span>{status_html}</div>
          <div class="t-route">{teams[0]}<div class="t-at mono">at</div>{teams[1]}</div>
          <div class="t-bar{' home-pick' if not away_pick else ''}"><i class="p" style="width:{pick_pct}%"></i></div>
          <div class="t-foot mono"><span>{p['conf_label']}</span><span>{proj}</span></div>
        </div>
        <div class="{stub_cls}">
          <div><div class="lbl mono">Pick</div><div class="pk">{_abbr(p['winner'])}</div></div>
          <div class="pr">{pick_pct}<small>%</small></div>
          {_barcode(f"{date_iso}_{p.get('home_id')}_{p.get('away_id')}")}
          <div class="lg mono">{stub_foot}</div>
        </div>
      </article>"""


def _receipt_card(stats, run_time):
    live = stats.get('live', {})
    lines = []
    for r in stats.get('recent', []):
        d = datetime.strptime(str(int(r['date'])), '%Y%m%d')
        pick = r['home_team_name'] if r['predicted_winner'] == 'home' else r['away_team_name']
        mark = '<span class="ok">&#10003; Won</span>' if r['correct'] else '<span class="no">&#10007; Miss</span>'
        lines.append(f'<div class="r-row"><span>{d:%b} {d.day:02d} {_abbr(r["away_team_name"])} @ '
                     f'{_abbr(r["home_team_name"])} &rarr; {_abbr(pick)}</span>{mark}</div>')
    day = f"Day {stats['day']}" if stats.get('day') else ''
    return f"""
      <div class="receipt" role="img" aria-label="Season receipt: {live.get('pct')}% across {live.get('n')} games">
        <div class="r-head"><b>Second Bounce</b>NBA prediction engine</div>
        <hr>
        <div class="r-row"><span>Season {stats.get('season_label', '')}</span><span>{day}</span></div>
        <div class="r-row"><span>Run</span><span>{run_time}</span></div>
        <hr>
        {''.join(lines) or '<div class="r-row"><span>No graded picks yet</span></div>'}
        <hr>
        <div class="r-row"><span>Graded</span><span>{live.get('n', 0)}</span></div>
        <div class="r-row"><span>Correct</span><span>{live.get('correct', 0)}</span></div>
        <div class="r-row"><span>Brier</span><span>{live.get('brier')}</span></div>
        <div class="r-row r-total"><span>Accuracy</span><span>{live.get('pct')}%</span></div>
        {_barcode(f"season_{stats.get('season_label')}_{live.get('n')}", 300, 38)}
        <div class="r-note">Logged before tip. Graded after the final.</div>
      </div>"""


def _calibration_svg(calib):
    """Stated confidence (x) against how often those picks won (y), one dot per
    bucket, dashed diagonal = perfectly calibrated. Single series, so no legend box;
    the n per bucket is direct-labelled and repeated in the table view below."""
    W, H, L, R, T, B = 520, 300, 46, 16, 14, 40
    lo, hi = 0.4, 1.0
    sx = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    sy = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    grid, axis = [], []
    for v in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        grid.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/>')
        axis.append(f'<text x="{L - 8}" y="{sy(v) + 4:.1f}" text-anchor="end">{v * 100:.0f}%</text>')
        axis.append(f'<text x="{sx(v):.1f}" y="{H - B + 18}" text-anchor="middle">{v * 100:.0f}%</text>')
    axis.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 4}" text-anchor="middle">Stated confidence</text>')
    dots = []
    for b in calib:
        x, y = sx(b['stated']), sy(b['won'])
        tip = (f"<b>{b['lo'] * 100:.0f}&ndash;{b['hi'] * 100:.0f}% picks</b><br>"
               f"said {b['stated'] * 100:.0f}%, won {b['won'] * 100:.0f}% of {b['n']}")
        dots.append(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="8" tabindex="0" '
                    f'data-tip="{tip}" aria-label="{b["lo"] * 100:.0f} to {b["hi"] * 100:.0f} percent picks: '
                    f'won {b["won"] * 100:.0f} percent of {b["n"]}"/>')
        # Alternate above/below so neighbouring buckets' labels never collide.
        ly = y - 15 if len(dots) % 4 == 1 else y + 24
        dots.append(f'<text class="dl" x="{x:.1f}" y="{ly:.1f}" text-anchor="middle">'
                    f'{b["won"] * 100:.0f}% of {b["n"]}</text>')
    return (f'<svg class="calib" viewBox="0 0 {W} {H}" role="img" aria-label="Calibration: '
            f'stated confidence against actual win rate">'
            f'<g class="grid">{"".join(grid)}</g><g class="axis">{"".join(axis)}</g>'
            f'<line class="ref" x1="{sx(0.5):.1f}" y1="{sy(0.5):.1f}" x2="{sx(1.0):.1f}" y2="{sy(1.0):.1f}"/>'
            f'<text class="reflbl" x="{sx(0.93):.1f}" y="{sy(0.99):.1f}" text-anchor="end">perfectly calibrated</text>'
            f'{"".join(dots)}</svg>')


def render_html(date_str, predictions, week_days, week_summary, stats, players,
                weekly=None, injuries=None):
    """Ticket template renderer (2026-11). Fills templates/ticket.html by plain
    str.replace token substitution, so the template's CSS and JS braces stay
    literal. `weekly` and `injuries` are accepted for call-site compatibility."""
    try:
        date_iso = datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
    except ValueError:
        date_iso = datetime.now().strftime('%Y-%m-%d')
    stats = stats or {}
    live, audit = stats.get('live', {}), stats.get('audit', {})
    # Early in a season the live sample can be empty; lead with the audit then.
    lead = live if live.get('n') else audit
    now = datetime.now()
    run_time = f"{now:%b} {now.day:02d} {now:%I:%M %p} ET".upper()
    games_count = len(predictions)

    # ---- hero ---- #
    hero_meta = (f"<b>Second Bounce</b><span>NBA prediction engine</span>"
                 f"<span>Season {stats.get('season_label', '')}"
                 f"{' &middot; Day ' + str(stats['day']) if stats.get('day') else ''}</span>"
                 f"<span>Last run {run_time}</span>")
    if live.get('n'):
        hero_sub = (f"Every pick is logged before the game starts and graded after the final. "
                    f"Nothing gets recomputed, and the misses stay in. This season: "
                    f"<strong>{live['pct']}% across {live['n']} games.</strong>")
    else:
        hero_sub = (f"Every pick is logged before the game starts and graded after the final. "
                    f"Nothing gets recomputed, and the misses stay in. Last season's audit: "
                    f"<strong>{audit.get('pct')}% across {audit.get('n')} games.</strong>")

    # ---- today ---- #
    date_stamp = f"{date_str} &middot; {games_count} game{'s' if games_count != 1 else ''}"
    if predictions:
        predictions_html = ('<div class="tickets">'
                            + ''.join(_ticket(p, i, games_count, date_iso)
                                      for i, p in enumerate(predictions, 1))
                            + '</div>')
    else:
        md = (now.month, now.day)
        if (6, 25) <= md <= (10, 20):
            predictions_html = f"""
      <div class="empty-card"><h3>No games today. The season's over.</h3>
        <p>Daily picks return on opening night. Until then the newsletter covers the offseason
        through the model's eyes, and the full record stays up below.</p>
        <a class="btn" href="https://secondbounce.substack.com" target="_blank" rel="noopener">Read the newsletter</a></div>"""
        else:
            predictions_html = """
      <div class="empty-card"><h3>No games on the schedule today.</h3>
        <p>Picks post every game day before the first tip. The last few nights are graded below.</p>
        <a class="btn ghost" href="#results">See recent results</a></div>"""

    # ---- record ---- #
    w7, l7 = stats.get('last7', (0, 0))
    cw, cl = stats.get('close', (0, 0))
    calib = stats.get('calib', [])
    calib_rows = ''.join(
        f"<tr><td>{b['lo'] * 100:.0f}&ndash;{b['hi'] * 100:.0f}%</td><td>{b['n']}</td>"
        f"<td>{b['stated'] * 100:.0f}%</td><td>{b['won'] * 100:.0f}%</td></tr>" for b in calib)
    chart_html = (f"""
        <div class="chart-card">
          <h3>Does it mean what it says?</h3>
          <p class="sub">Each dot is a group of {stats.get('season_label', '')} picks. On the dashed line, a 70% pick wins 70% of the time.</p>
          {_calibration_svg(calib)}
          <div class="tip" role="tooltip"></div>
          <table class="calib-table"><thead><tr><th>Bucket</th><th>Picks</th><th>Said</th><th>Won</th></tr></thead>
          <tbody>{calib_rows}</tbody></table>
        </div>""" if calib else '')
    lede = (f"{live['correct']} of {live['n']} picks correct this season, every one logged before tip-off."
            if live.get('n') else
            "No picks graded yet this season. The number above is last season's walk-forward audit.")
    record_html = f"""
      <div class="record">
        <div>
          <span class="mono">03 / The record &middot; {stats.get('season_label', '')}</span>
          <div class="big-num">{lead.get('pct')}<small>%</small></div>
          <p class="lede">{lede}</p>
          <div class="kpis">
            <div class="kpi"><span class="mono">Last 7 days</span><b>{w7}&ndash;{l7}</b></div>
            <div class="kpi"><span class="mono">Brier score</span><b>{lead.get('brier')}</b></div>
            <div class="kpi"><span class="mono">Picks under 60%</span><b>{cw}&ndash;{cl}</b></div>
          </div>
          <div class="audit">
            <b>Last season, audited:</b> {audit.get('pct')}% across {audit.get('n')} games. We first published
            73.5%, then found the tracker had been grading games with ratings that already knew the result.
            The audit replays 2025-26 in strict time order. It was rebuilt after the fact, so it's
            reported separately from this season's locked picks.
            <a href="https://secondbounce.substack.com/p/how-we-caught-our-own-model-cheating" target="_blank" rel="noopener">Read how we caught it</a>
          </div>
          <div class="verify">
            <a href="ledger.csv">Download every pick (CSV)</a>
            <a href="https://github.com/atr777/nba-predictions/commits/main/ledger.csv" target="_blank" rel="noopener">Check the timestamps on GitHub</a>
          </div>
        </div>
        {chart_html}
      </div>"""

    # ---- results timeline ---- #
    if week_days:
        blocks = []
        for day in week_days:
            rows = []
            for r in day['rows']:
                score = ''
                if pd.notna(r['away_score']) and r['away_score'] != '':
                    score = f"{int(r['away_score'])}&ndash;{int(r['home_score'])}"
                chip = ('<span class="chip ok">&#10003; Correct</span>' if r['correct']
                        else '<span class="chip no">&#10007; Miss</span>')
                rows.append(f"""
            <div class="res">
              <span class="mu"><img src="{get_logo_by_abbrev(_abbr(r['away']))}" alt="" onerror="this.style.display='none'"><span class="tn">{r['away']}</span><span class="ta">{_abbr(r['away'])}</span>
                <span class="at">at</span><img src="{get_logo_by_abbrev(_abbr(r['home']))}" alt="" onerror="this.style.display='none'"><span class="tn">{r['home']}</span><span class="ta">{_abbr(r['home'])}</span></span>
              <span class="sc">{score}</span>
              <span class="pk">Pick {_abbr(r['pick'])} &middot; {r['pick_prob'] * 100:.0f}%</span>
              {chip}
            </div>""")
            blocks.append(f"""
        <div class="day">
          <div class="day-label"><div class="d">{day['label']}</div><div class="rec mono">{day['weekday']} &middot; {day['correct']}&ndash;{day['total'] - day['correct']}</div></div>
          <div class="day-rows">{''.join(rows)}</div>
        </div>""")
        results_html = ''.join(blocks)
    else:
        results_html = '<div class="empty-card"><p>No graded results yet.</p></div>'

    # ---- players ---- #
    if players:
        rows = []
        for p in players:
            frac = max(0.06, min(1.0, (p['elo'] - 1500) / (2650 - 1500)))
            adj = p['adj']
            if adj <= -20:
                adj_cell = f'<td class="adj">&#9660; {adj}</td>'
            elif adj >= 20:
                adj_cell = f'<td class="adj">&#9650; +{adj}</td>'
            else:
                adj_cell = '<td class="adj dim">0</td>'
            rows.append(
                f'<tr><td class="rk">{p["rank"]}</td><td class="nm">{p["name"]}</td>'
                f'<td><span class="tm"><img src="{p["team_logo"]}" alt="" onerror="this.style.display=\'none\'">{p["team_abbr"]}</span></td>'
                f'<td class="gp">{p["games"]}</td>'
                f'<td><div class="rt"><div class="track"><div class="fill" style="width:{frac * 100:.0f}%"></div></div><b>{p["elo"]}</b></div></td>'
                f'{adj_cell}</tr>')
        players_html = ''.join(rows)
    else:
        players_html = '<tr><td colspan="6" class="empty">No player ratings available.</td></tr>'

    # ---- footer + metadata ---- #
    footer_receipt = (f"[ {lead.get('pct')}% &middot; {lead.get('n')} games &middot; "
                      f"{stats.get('season_label', '')} &middot; logged before tip ]")
    footer_legal = f"&copy; {now.year} Second Bounce &middot; Updated {run_time}"
    site_url = 'https://atr777.github.io/nba-predictions/'
    if live.get('n'):
        share_title = f"Second Bounce · {live['pct']}% on {live['n']} NBA games, logged before tip-off"
        meta_description = (
            f"An NBA prediction model with a public receipt: {live['pct']}% across {live['n']} "
            f"games this season, every pick logged before tip-off and graded after the final. "
            f"Daily win probabilities, a downloadable ledger, and the misses left in.")
    else:
        share_title = f"Second Bounce · NBA predictions logged before tip-off"
        meta_description = (
            f"An NBA prediction model with a public receipt. Every pick is logged before tip-off "
            f"and graded after the final. Last season's walk-forward audit: {audit.get('pct')}% "
            f"across {audit.get('n')} games.")
    json_ld = json.dumps({
        '@context': 'https://schema.org',
        '@type': 'Dataset',
        'name': 'Second Bounce NBA prediction ledger',
        'description': meta_description,
        'url': site_url,
        'distribution': {'@type': 'DataDownload', 'encodingFormat': 'text/csv',
                         'contentUrl': site_url + 'ledger.csv'},
        'creator': {'@type': 'Organization', 'name': 'Second Bounce', 'url': site_url},
        'isAccessibleForFree': True,
        'license': 'https://creativecommons.org/licenses/by/4.0/',
        'temporalCoverage': '2026-10-20/..',
        'keywords': ['NBA', 'predictions', 'Elo rating', 'forecast accuracy', 'calibration'],
        'variableMeasured': [
            {'@type': 'PropertyValue', 'name': 'Prediction accuracy',
             'value': lead.get('pct'), 'unitText': 'percent'},
            {'@type': 'PropertyValue', 'name': 'Games graded',
             'value': lead.get('n'), 'unitText': 'games'},
        ],
    }, indent=2)

    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'ticket.html')
    with open(template_path, encoding='utf-8') as f:
        html = f.read()
    players_json = json.dumps(get_all_players(), separators=(',', ':'), ensure_ascii=False)

    replacements = {
        '{{DATE_STR}}': date_str,
        '{{SITE_URL}}': site_url,
        '{{SHARE_TITLE}}': share_title,
        '{{META_DESCRIPTION}}': meta_description,
        '{{JSON_LD}}': json_ld,
        '{{HERO_META}}': hero_meta,
        '{{HERO_SUB}}': hero_sub,
        '{{RECEIPT_CARD}}': _receipt_card(stats, run_time),
        '{{STAMP_VALUE}}': f"{lead.get('pct')}%",
        '{{SEASON_LABEL}}': stats.get('season_label', ''),
        '{{DATE_STAMP}}': date_stamp,
        '{{PREDICTIONS}}': predictions_html,
        '{{RECORD}}': record_html,
        '{{RESULTS}}': results_html,
        '{{PLAYERS}}': players_html,
        '{{PLAYERS_JSON}}': players_json,
        '{{FOOTER_RECEIPT}}': footer_receipt,
        '{{FOOTER_LEGAL}}': footer_legal,
    }
    for token, value in replacements.items():
        html = html.replace(token, str(value))
    return html


def write_ledger(pages_dir):
    """pages/ledger.csv: every pre-game-locked pick, graded or still pending.

    The site's git history commits this file five times a day, so anyone can check
    that a pick existed before its game started without trusting us. Only 2026-27
    onward: the 2025-26 record is a walk-forward replay (rebuilt after the fact,
    logged post-game), which is honest but is not the same claim, so it is not
    mixed in here.
    """
    frames = []
    for path in ('data/exports/prediction_tracking.csv',
                 'data/exports/pending_predictions.csv'):
        if os.path.exists(path):
            frames.append(pd.read_csv(path))
    if not frames:
        return 0
    d = pd.concat(frames, ignore_index=True)
    d = d[d['date'] >= LEDGER_START].copy()
    if 'correct' not in d.columns:
        d['correct'] = pd.NA
    for col in ('actual_home_score', 'actual_away_score'):
        if col not in d.columns:
            d[col] = pd.NA
    home_pick = d['predicted_winner'] == 'home'
    out = pd.DataFrame({
        'date': d['date'],
        'logged_at_et': d['timestamp'].astype(str).str[:19],
        'away_team': d['away_team_name'],
        'home_team': d['home_team_name'],
        'pick': d['home_team_name'].where(home_pick, d['away_team_name']),
        'pick_prob': d['confidence'].round(4),
        'home_win_prob': d['predicted_home_prob'].round(4),
        'away_score': d['actual_away_score'].astype('Int64'),
        'home_score': d['actual_home_score'].astype('Int64'),
        'correct': d['correct'].map({True: 1, False: 0, 'True': 1, 'False': 0}).astype('Int64'),
    }).sort_values(['date', 'logged_at_et'])
    out.to_csv(os.path.join(pages_dir, 'ledger.csv'), index=False)
    return len(out)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    date_str = datetime.now().strftime('%B %d, %Y')

    print(f"Generating GitHub Pages site for {date_str}...")

    predictions      = get_today_predictions()
    week_days, week_summary = get_week_results()
    stats            = get_season_stats()
    players          = get_top_players(15)
    weekly           = get_weekly_summary()
    print("  Fetching injuries from ESPN...")
    injuries         = get_injuries_for_games(predictions)

    print(f"  Predictions: {len(predictions)} games")
    print(f"  This week: {sum(len(d['rows']) for d in week_days)} results across {len(week_days)} days")
    print(f"  Players: {len(players)} ranked")
    print(f"  Weekly days: {len(weekly)}")
    print(f"  Teams with injuries: {len(injuries)}")

    html = render_html(date_str, predictions, week_days, week_summary, stats, players,
                       weekly=weekly, injuries=injuries)

    # Write to pages/
    pages_dir = os.path.join(os.path.dirname(__file__), '..', 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    out_path = os.path.join(pages_dir, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  Saved: pages/index.html ({len(html):,} bytes)")

    # sitemap.xml is generated rather than static so <lastmod> stays honest: the
    # page changes every pipeline run, and a sitemap claiming otherwise is worse
    # than no sitemap. robots.txt IS static (pages/robots.txt) because it does not
    # carry a date.
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        '    <loc>https://atr777.github.io/nba-predictions/</loc>\n'
        f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
        '    <changefreq>daily</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>\n'
    )
    sitemap_path = os.path.join(pages_dir, 'sitemap.xml')
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f"  Saved: pages/sitemap.xml")

    # robots.txt is copied out of templates/ rather than kept in pages/, because
    # pages/ is NOT tracked by this repo: locally it is a clone of the
    # atr777/nba-predictions repo, and on the VPS it is a scratch output dir. A
    # static file living only there would be absent on the VPS, the deploy's `cp`
    # would fail, and because that copy chain is joined by && the whole site update
    # would stop. Found the hard way 2026-07-29.
    robots_src = os.path.join(os.path.dirname(__file__), '..', 'templates', 'robots.txt')
    robots_path = os.path.join(pages_dir, 'robots.txt')
    with open(robots_src, encoding='utf-8') as f:
        robots = f.read()
    with open(robots_path, 'w', encoding='utf-8') as f:
        f.write(robots)
    print(f"  Saved: pages/robots.txt")

    # Non-fatal: the ledger is a public receipt, not the page itself, and must not
    # be able to stop today's predictions from publishing.
    try:
        print(f"  Saved: pages/ledger.csv ({write_ledger(pages_dir)} picks)")
    except Exception as e:
        print(f"  [WARN] ledger not written ({e})")

    return out_path


if __name__ == '__main__':
    # Change to nba-elo-engine dir so relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    engine_dir = os.path.join(script_dir, '..')
    os.chdir(engine_dir)
    main()
