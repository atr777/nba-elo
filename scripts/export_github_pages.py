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

import pandas as pd
from datetime import datetime, timedelta

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

            if win_prob >= 0.75:
                conf_label, conf_class = 'Strong', 'conf-high'
            elif win_prob >= 0.63:
                conf_label, conf_class = 'Moderate', 'conf-med'
            else:
                conf_label, conf_class = 'Tossup', 'conf-low'

            tossup = abs(home_elo - away_elo) < 30
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
                'predicted_home_score': _pred_home_score,
                'predicted_away_score': _pred_away_score,
                'predicted_margin': round(_pred_margin, 1),
                **_q_preds,
            })

        # Sort: scheduled first, then live, then final
        status_order = {1: 0, 2: 1, 3: 2}
        predictions.sort(key=lambda x: (status_order.get(x.get('game_status_code', 1), 0), x['time']))
        return predictions
    except Exception as e:
        print(f"  Warning: Could not load predictions ({e})")
        return []


def get_week_results():
    """Return yesterday's results only."""
    df = load_csv('data/exports/prediction_tracking.csv')
    if df.empty:
        return [], {}

    df = df.sort_values('date')
    today = datetime.now()
    yesterday_int = int((today - timedelta(days=1)).strftime('%Y%m%d'))

    week = df[df['date'] == yesterday_int]
    if week.empty:
        return [], {}

    # Group by date, newest first
    days = []
    for date_int, group in sorted(week.groupby('date'), reverse=True):
        try:
            d = datetime.strptime(str(date_int), '%Y%m%d')
            day_label = f"{d.strftime('%a')}-{d.day:02d}-{d.strftime('%y')}"
            nba_scores_url = f"https://www.nba.com/games?date={d.strftime('%Y-%m-%d')}"
        except Exception:
            day_label = str(date_int)
            nba_scores_url = 'https://www.nba.com/scores'

        rows = []
        for _, row in group.iterrows():
            rows.append({
                'home': row.get('home_team_name', ''),
                'away': row.get('away_team_name', ''),
                'predicted': row.get('predicted_winner', ''),
                'correct': bool(row.get('correct', False)),
                'home_score': row.get('actual_home_score', ''),
                'away_score': row.get('actual_away_score', ''),
                'upset': bool(row.get('upset', False)),
            })

        total = len(rows)
        correct = sum(1 for r in rows if r['correct'])
        days.append({
            'label': day_label,
            'nba_url': nba_scores_url,
            'rows': rows,
            'correct': correct,
            'total': total,
            'pct': f"{correct/total*100:.0f}%" if total > 0 else '—',
        })

    all_rows = [r for d in days for r in d['rows']]
    total = len(all_rows)
    correct = sum(1 for r in all_rows if r['correct'])
    summary = {
        'total': total,
        'correct': correct,
        'pct': f"{correct/total*100:.1f}" if total > 0 else '—',
    }
    return days, summary


def get_season_stats():
    """Return accuracy stats for the current season."""
    df = load_csv('data/exports/prediction_tracking.csv')
    if df.empty:
        return {}

    df = df.sort_values('date')
    season = df[df['date'] >= 20251001]
    total = len(season)
    correct = season['correct'].sum() if total > 0 else 0

    # Last 7 days
    cutoff7 = int((datetime.now() - timedelta(days=7)).strftime('%Y%m%d'))
    last7 = season[season['date'] >= cutoff7]
    w7 = int(last7['correct'].sum())
    l7 = len(last7) - w7

    # Tossup accuracy
    tu = season[season['is_toss_up'] == True] if 'is_toss_up' in season.columns else pd.DataFrame()
    tu_str = f"{int(tu['correct'].sum())}-{len(tu)-int(tu['correct'].sum())}" if len(tu) > 0 else 'N/A'
    tu_pct = f"{tu['correct'].mean()*100:.1f}" if len(tu) > 0 else 'N/A'

    return {
        'total': total,
        'correct': int(correct),
        'pct': f"{correct/total*100:.2f}" if total > 0 else '—',
        'last7_w': w7, 'last7_l': l7,
        'last7_pct': f"{w7/(w7+l7)*100:.1f}" if (w7+l7) > 0 else '—',
        'tossup_record': tu_str,
        'tossup_pct': tu_pct,
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
    df['team_name'] = df['team_name'].fillna('—')
    top = df.nlargest(n, 'rating')[['player_name', 'team_name', 'rating', 'games_played']]

    players = []
    for i, (_, row) in enumerate(top.iterrows(), 1):
        team_name = row['team_name']
        team_abbr = TEAM_ABBREVS.get(team_name, team_name[:3].upper() if len(team_name) >= 3 else team_name)
        players.append({
            'rank': i,
            'name': row['player_name'],
            'team': team_name,
            'team_abbr': team_abbr,
            'team_logo': get_logo_by_abbrev(team_abbr),
            'elo': int(row['rating']),
            'games': int(row['games_played']),
        })
    return players


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


def _to_iso_et(date_iso, time_str):
    """Convert '7:30 pm ET' + '2026-03-10' to an ISO-8601 string with ET offset."""
    clean = time_str.replace(' ET', '').replace(' et', '').strip()
    try:
        dt = datetime.strptime(f"{date_iso} {clean}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        return None
    offset = '-04:00' if _is_edt(dt) else '-05:00'
    return f"{date_iso}T{dt.strftime('%H:%M')}:00{offset}"


def prob_bar(home_prob, home_name, away_name):
    """Render a two-sided probability bar. Away = left/muted, home = right/amber."""
    hp = round(home_prob * 100)
    ap = 100 - hp
    return f"""
    <div class="prob-bar-wrap">
      <span class="prob-label-away">{ap}%</span>
      <div class="prob-bar-split">
        <div class="prob-bar-away" style="width:{ap}%"></div>
        <div class="prob-bar-home" style="width:{hp}%"></div>
      </div>
      <span class="prob-label-home">{hp}%</span>
    </div>"""


def render_html(date_str, predictions, week_days, week_summary, stats, players,
                weekly=None, injuries=None):
    games_count = len(predictions)
    try:
        date_iso = datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
    except ValueError:
        date_iso = datetime.now().strftime('%Y-%m-%d')

    # ---- Predictions HTML ---- #
    injuries = injuries or {}

    if predictions:
        pred_cards = ''
        for p in predictions:
            bar = prob_bar(p['home_prob'], p['home'], p['away'])

            # Injury alerts for this game
            inj_html = ''
            for team_key in [p['away'], p['home']]:
                team_inj = injuries.get(team_key, [])
                if team_inj:
                    espn_url = get_espn_injury_url(team_key)
                    items = ''
                    for inj in team_inj:
                        impact_cls = {'star': 'inj-star', 'starter': 'inj-starter', 'role': 'inj-role'}.get(inj['impact'], 'inj-role')
                        items += f'<a href="{espn_url}" target="_blank" rel="noopener" class="inj-pill {impact_cls}">{inj["name"]} <em>{inj["status"]}</em></a> '
                    inj_html += f'<div class="inj-row"><span class="inj-team">{team_key}:</span> {items}</div>'
            inj_block = f'<div class="inj-block">{inj_html}</div>' if inj_html else ''

            away_logo = get_team_logo(p['away'])
            home_logo = get_team_logo(p['home'])
            status_code = p.get('game_status_code', 1)
            is_live  = status_code == 2
            is_final = status_code == 3
            # Live/Final games get a status badge instead of scheduled time
            if is_final:
                time_display = 'FINAL'
                time_cls     = ' game-time-final'
                iso_attr     = ''
            elif is_live:
                time_display = p['time'] if p['time'] != 'TBD' else 'LIVE'
                time_cls     = ' game-time-live'
                iso_attr     = ''
            else:
                time_display = p['time']
                time_cls     = ''
                iso_ts   = _to_iso_et(date_iso, p['time'])
                iso_attr = f' data-iso="{iso_ts}"' if iso_ts else ''
            # ── Quarter Score Grid (Sprint 3) ──────────────────────────────
            # Use real per-quarter model outputs when available; fall back to
            # the cyclic-offset distribution described in the design spec.
            _away_tot = p.get('predicted_away_score', 0) or 0
            _home_tot = p.get('predicted_home_score', 0) or 0
            _q_offsets = [-1, 2, -1, 0]  # sum = 0, total preserved
            if p.get('predicted_away_q1') is not None:
                _aq = [p[f'predicted_away_q{i}'] for i in range(1, 5)]
                _hq = [p[f'predicted_home_q{i}'] for i in range(1, 5)]
            else:
                _aq = [max(20, round(_away_tot / 4) + _q_offsets[i]) for i in range(4)]
                _hq = [max(20, round(_home_tot / 4) + _q_offsets[i]) for i in range(4)]
            # Running (cumulative) totals after each quarter
            _aq_run = [sum(_aq[:i+1]) for i in range(4)]
            _hq_run = [sum(_hq[:i+1]) for i in range(4)]
            _away_display = _aq_run[3]
            _home_display = _hq_run[3]
            _winner_is_home = p['is_home_win']
            _away_row_cls = 'qs-winner' if not _winner_is_home else ''
            _home_row_cls = 'qs-winner' if _winner_is_home else ''
            _away_abbr = TEAM_ABBREVS.get(p['away'], p['away'][:3].upper())
            _home_abbr = TEAM_ABBREVS.get(p['home'], p['home'][:3].upper())
            # Margin line: plain-English expected win margin
            _margin_pts = abs(round(p.get('predicted_margin', _home_display - _away_display)))
            _margin_html = f'<div class="qscore-margin"><span>Expected to win by <strong>{_margin_pts} pts</strong></span><span class="qscore-margin-prob">{p["win_prob"]*100:.0f}% win probability</span></div>'
            _qscore_html = f"""<div class="qscore-wrap">
  <div class="qscore-label">Projected Score</div>
  <table class="qscore-table">
    <thead><tr><th></th><th>Q1</th><th>Q2</th><th>Q3</th><th class="col-final">FINAL</th></tr></thead>
    <tbody>
      <tr class="{_away_row_cls}"><td>{_away_abbr}</td><td>{_aq_run[0]}</td><td>{_aq_run[1]}</td><td>{_aq_run[2]}</td><td class="col-final">{_away_display}</td></tr>
      <tr class="{_home_row_cls}"><td>{_home_abbr}</td><td>{_hq_run[0]}</td><td>{_hq_run[1]}</td><td>{_hq_run[2]}</td><td class="col-final">{_home_display}</td></tr>
    </tbody>
  </table>
  {_margin_html}
</div>"""
            # ───────────────────────────────────────────────────────────────

            pred_cards += f"""
      <div class="card game-card{'  game-card-final' if is_final else ''}">
        <a class="game-card-link" href="{p['nba_url']}" target="_blank" rel="noopener" aria-label="View {p['away']} @ {p['home']} on NBA.com"></a>
        <div class="game-header">
          <span class="game-time{time_cls}"{iso_attr}>{time_display}</span>
          <span class="badge {p['conf_class']}">{p['conf_label']}{' · Tossup' if p['tossup'] else ''}</span>
        </div>
        <div class="matchup">
          <img class="team-logo{' team-logo-pick' if not p['is_home_win'] else ''}" src="{away_logo}" alt="{p['away']}" onerror="this.style.display='none'">
          <span class="{'team-pick' if not p['is_home_win'] else ''}">{p['away']}</span>
          <span class="vs">@</span>
          <img class="team-logo{' team-logo-pick' if p['is_home_win'] else ''}" src="{home_logo}" alt="{p['home']}" onerror="this.style.display='none'">
          <span class="{'team-pick' if p['is_home_win'] else ''}">{p['home']}</span>
        </div>
        <div class="prediction-line">
          <strong>{p['winner']}</strong> {'slight edge' if p.get('tossup') else 'favored to win'} <span class="favored-tag">· {p['win_prob']*100:.0f}% chance</span>
        </div>
        {_qscore_html}
        {bar}
        <div class="elo-line">ELO: {p['away']} {p['away_elo']:.0f} · {p['home']} {p['home_elo']:.0f}</div>
        {inj_block}
      </div>"""
    else:
        pred_cards = '<div class="card"><p style="text-align:center;color:#888">No games scheduled today or predictions unavailable.</p></div>'

    # ---- This Week Results HTML ---- #
    _check_svg = '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="rgba(16,185,129,0.15)" stroke="#10b981" stroke-width="1.5"/><path d="M5 8l2 2 4-4" stroke="#10b981" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    _x_svg    = '<svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="rgba(239,68,68,0.12)" stroke="#ef4444" stroke-width="1.5"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round"/></svg>'

    if week_days:
        week_pill_cls = 'pill-good' if week_summary['correct'] > week_summary['total'] // 2 else 'pill-ok'
        week_body = ''
        for day in week_days:
            day_correct = day['correct']
            day_total = day['total']
            nba_url = day.get('nba_url', 'https://www.nba.com/scores')
            day_rows = ''
            for r in day['rows']:
                icon = _check_svg if r['correct'] else _x_svg
                score_str = f"{r['away_score']}–{r['home_score']}" if r['away_score'] != '' else ''
                upset_badge = ' <span class="badge upset-badge">UPSET</span>' if r['upset'] else ''
                day_rows += f"""
        <div class="result-row {'result-correct' if r['correct'] else 'result-miss'}">
          <span class="result-icon">{icon}</span>
          <a class="result-teams" href="{nba_url}" target="_blank" rel="noopener">{r['away']} @ {r['home']}</a>
          <span class="result-pick">Pick: {r['predicted']}{upset_badge}</span>
          <span class="result-score">{score_str}</span>
        </div>"""
            day_pct_cls = 'day-pct-good' if day_correct >= day_total * 0.65 else ('day-pct-ok' if day_correct >= day_total * 0.5 else 'day-pct-bad')
            week_body += f"""
        <div class="day-group">
          <div class="day-header">
            <span class="day-label">{day['label']}</span>
            <span class="day-record {day_pct_cls}">{day_correct}-{day_total - day_correct} &nbsp;<small>{day['pct']}</small></span>
          </div>
          {day_rows}
        </div>"""
        yesterday_html = f"""
      <div class="card">
        <details class="week-details" open>
          <summary class="section-title week-summary">
            Yesterday's Results
            <span class="record-pill {week_pill_cls}">
              {week_summary['correct']}-{week_summary['total'] - week_summary['correct']} ({week_summary['pct']}%)
            </span>
            <span class="chevron">▾</span>
          </summary>
          {week_body}
        </details>
      </div>"""
    else:
        yesterday_html = ''

    # ---- Stats bar ---- #
    stats_html = f"""
    <div class="stats-bar">
      <div class="stat-item">
        <div class="stat-val">{stats.get('pct','—')}%</div>
        <div class="stat-lbl">Season Accuracy</div>
        <div class="stat-sub">{stats.get('correct','—')} of {stats.get('total','—')} correct</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{stats.get('last7_w','—')}-{stats.get('last7_l','—')}</div>
        <div class="stat-lbl">Last 7 Days</div>
        <div class="stat-sub">{stats.get('last7_w','—')} right, {stats.get('last7_l','—')} wrong</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{stats.get('tossup_pct','—')}%</div>
        <div class="stat-lbl">Toss-Up Games</div>
        <div class="stat-sub">games within 30 ELO pts</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{stats.get('total','—')}</div>
        <div class="stat-lbl">Games Tracked</div>
        <div class="stat-sub">since Oct 2025</div>
      </div>
    </div>""" if stats else ''

    # ---- Weekly summary HTML ---- #
    if weekly:
        week_rows = ''
        for day in weekly:
            bar_w = int(day['pct'] * 100)
            bar_color = '#22c55e' if day['pct'] >= 0.65 else ('#f59e0b' if day['pct'] >= 0.50 else '#ef4444')
            week_rows += f"""
        <div class="week-row">
          <span class="week-day">{day['label']}</span>
          <div class="week-bar-wrap">
            <div class="week-bar" style="width:{bar_w}%;background:{bar_color}"></div>
          </div>
          <span class="week-record">{day['correct']}-{day['total']-day['correct']} <small>({day['pct_str']})</small></span>
        </div>"""
        weekly_html = f"""
      <div class="card">
        <h2 class="section-title">Last Week</h2>
        {week_rows}
      </div>"""
    else:
        weekly_html = ''

    # ---- Player rankings HTML ---- #
    if players:
        player_rows = ''
        for p in players:
            player_rows += f"""
        <tr>
          <td class="rank">{p['rank']}</td>
          <td class="pname">{p['name']}</td>
          <td class="pteam"><img class="pteam-logo" src="{p['team_logo']}" alt="{p['team_abbr']}" onerror="this.style.display='none'"> {p['team_abbr']}</td>
          <td class="pelo">{p['elo']}</td>
        </tr>"""
        players_html = f"""
      <div class="card">
        <h2 class="section-title">Top 15 Player ELO</h2>
        <div class="table-wrap">
          <table class="player-table">
            <thead><tr><th>#</th><th>Player</th><th>Team</th><th class="th-elo">ELO</th></tr></thead>
            <tbody>{player_rows}</tbody>
          </table>
        </div>
      </div>"""
    else:
        players_html = ''

    # ---- Full page ---- #
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Second Bounce — {date_str}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="logo.png">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:         #080c14;
      --surface:    #0f1623;
      --surface-hi: #1a2234;
      --border:     #1e2d45;
      --text:       #e8ecf4;
      --muted:      #64748b;
      --accent:     #4b8bf4;
      --pick:       #f8a100;
      --green:      #10b981;
      --amber:      #f59e0b;
      --red:        #ef4444;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 15px;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
    }}

    header {{
      background-color: rgba(15, 22, 35, 0.78);
      background-image:
        radial-gradient(55% 130px at 50% 100%, rgba(255,255,255,0.045), transparent),
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.72' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.055'/%3E%3C/svg%3E");
      backdrop-filter: blur(18px) saturate(140%) brightness(1.04);
      -webkit-backdrop-filter: blur(18px) saturate(140%) brightness(1.04);
      border-top: 3px solid var(--accent);
      border-bottom: 1px solid rgba(255,255,255,0.06);
      border-radius: 0 0 1.5rem 1.5rem;
      padding: 1.4rem 1.5rem 1.25rem;
      position: sticky;
      top: 0;
      z-index: 100;
      overflow: hidden;
    }}
    /* Glow line at bottom edge — mirrors footer-glow-line at top */
    header::before {{
      content: '';
      position: absolute;
      bottom: 0; left: 50%; transform: translateX(-50%);
      width: 38%; height: 1px;
      background: rgba(255,255,255,0.2);
      border-radius: 999px;
      filter: blur(2px);
      pointer-events: none;
      z-index: 2;
    }}
    /* Tiled basketball pattern across full header — hue-rotated to light blue */
    header::after {{
      content: '';
      position: absolute;
      inset: 0;
      background: url('pattern.png') 0 0 / 380px 380px repeat;
      opacity: 0.13;
      filter: hue-rotate(178deg) saturate(0.8) brightness(1.6);
      pointer-events: none;
    }}
    .header-inner {{
      max-width: 680px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      position: relative;
      z-index: 1;
    }}
    .header-text {{ display: flex; flex-direction: column; gap: 0.2rem; }}
    header h1 {{ font-family: 'DM Serif Display', Georgia, serif; font-size: clamp(2.85rem, 7.5vw, 3.9rem); font-weight: 400; letter-spacing: -0.5px; line-height: 1.05; }}
    header .tagline {{ font-size: 0.72rem; color: var(--muted); letter-spacing: 0.4px; text-transform: uppercase; }}
    .games-date {{ font-size: 0.7rem; color: var(--muted); font-weight: 500; letter-spacing: 0.3px; margin-bottom: 0.4rem; }}
    .site-logo {{
      width: 144px;
      height: 144px;
      object-fit: contain;
      flex-shrink: 0;
      filter: drop-shadow(0 0 18px rgba(248,161,0,0.45)) drop-shadow(0 0 6px rgba(248,161,0,0.2));
    }}

    .container {{ max-width: 680px; margin: 0 auto; padding: 0.75rem; }}

    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.5rem;
      margin: 0.75rem 0;
    }}
    .stat-item {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.6rem 0.25rem;
      text-align: center;
    }}
    .stat-item:first-child {{ border-top: 2px solid var(--accent); }}
    .stat-val {{ font-size: 1.1rem; font-weight: 800; color: var(--accent); }}
    .stat-lbl {{ font-size: 0.6rem; color: var(--muted); margin-top: 0.15rem; text-transform: uppercase; letter-spacing: 0.8px; }}
    .stat-sub {{ font-size: 0.58rem; color: var(--muted); opacity: 0.65; margin-top: 0.1rem; }}

    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem;
      margin-bottom: 0.75rem;
    }}

    .section-title {{
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--muted);
      border-left: 3px solid var(--accent);
      padding-left: 0.6rem;
      margin-bottom: 0.75rem;
    }}

    .games-header {{
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--muted);
      border-left: 3px solid var(--accent);
      padding-left: 0.6rem;
      margin-bottom: 0.6rem;
    }}

    .game-card {{
      margin-bottom: 0.75rem;
      transition: background 0.15s, border-color 0.15s;
    }}
    .game-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.45rem;
    }}
    .game-time {{ font-size: 0.75rem; color: var(--muted); font-weight: 500; }}
    .game-time-live  {{ color: #22c55e; font-weight: 700; letter-spacing: 0.3px; }}
    .game-time-final {{ color: var(--muted); font-weight: 600; letter-spacing: 0.5px; opacity: 0.6; }}
    .game-card-final {{ opacity: 0.72; }}

    .matchup {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.97rem;
      font-weight: 600;
      margin-bottom: 0.35rem;
      flex-wrap: wrap;
    }}
    .team-pick {{ color: var(--pick); font-weight: 700; }}
    .vs {{ color: var(--muted); font-size: 0.78rem; font-weight: 400; }}

    .prediction-line {{
      font-size: 0.82rem;
      color: var(--muted);
      margin-bottom: 0.5rem;
    }}
    .prediction-line strong {{ color: var(--text); font-weight: 600; }}
    .favored-tag {{ color: var(--muted); font-weight: 400; }}

    .prob-bar-wrap {{ display: flex; align-items: center; gap: 0.5rem; margin: 0.45rem 0 0.1rem; font-size: 0.68rem; }}
    .prob-label-away {{ color: var(--muted); min-width: 28px; text-align: right; }}
    .prob-label-home {{ color: var(--pick); min-width: 28px; font-weight: 600; }}
    .prob-bar-split {{
      flex: 1;
      height: 5px;
      border-radius: 3px;
      overflow: hidden;
      display: flex;
      gap: 1px;
      background: var(--border);
    }}
    .prob-bar-away {{ height: 100%; background: var(--border); }}
    .prob-bar-home {{ height: 100%; background: var(--pick); border-radius: 0 3px 3px 0; }}

    .elo-line {{ font-size: 0.68rem; color: var(--muted); margin-top: 0.25rem; letter-spacing: 0.1px; }}

    .score-projection {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.18rem; letter-spacing: 0.1px; }}

    /* ── Quarter Score Breakdown (Sprint 3) ─────────────────────────────── */
    .qscore-wrap {{
      margin-top: 0.55rem;
      margin-bottom: 0.1rem;
    }}
    .qscore-label {{
      font-size: 0.62rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--muted);
      margin-bottom: 0.3rem;
    }}
    .qscore-table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      table-layout: fixed;
    }}
    .qscore-table th {{
      font-size: 0.6rem;
      font-weight: 600;
      color: var(--muted);
      text-align: center;
      padding: 0.28rem 0.25rem;
      border-bottom: 1px solid var(--border);
    }}
    .qscore-table th:first-child {{ text-align: left; padding-left: 0.5rem; width: 38px; }}
    .qscore-table th.col-final {{ text-align: right; padding-right: 0.5rem; width: 48px; border-left: 1px solid var(--border); }}
    .qscore-table td {{
      font-size: 0.78rem;
      font-weight: 700;
      text-align: center;
      padding: 0.3rem 0.25rem;
      color: var(--text);
      opacity: 0.6;
    }}
    .qscore-table td:first-child {{
      font-size: 0.7rem;
      font-weight: 600;
      text-align: left;
      padding-left: 0.5rem;
      opacity: 1;
      color: var(--muted);
      letter-spacing: 0.2px;
    }}
    .qscore-table td.col-final {{
      font-size: 0.82rem;
      font-weight: 800;
      text-align: right;
      padding-right: 0.5rem;
      color: var(--muted);
      opacity: 1;
      border-left: 1px solid var(--border);
    }}
    .qscore-table tr + tr td {{ border-top: 1px solid var(--border); }}
    /* Winner row */
    .qscore-table tr.qs-winner td {{ color: var(--pick); opacity: 1; }}
    .qscore-table tr.qs-winner td:first-child {{ color: var(--pick); }}
    .qscore-table tr.qs-winner td.col-final {{ color: var(--accent); }}
    /* Plain-English margin line below score grid */
    .qscore-margin {{ display: flex; justify-content: space-between; margin-top: 0.3rem; font-size: 0.65rem; color: var(--muted); }}
    .qscore-margin strong {{ color: var(--pick); font-weight: 700; }}
    .qscore-margin-prob {{ color: var(--muted); }}

    .badge {{
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border-radius: 4px;
      font-size: 0.63rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .conf-high {{ background: rgba(16,185,129,0.15); color: #34d399; }}
    .conf-med  {{ background: rgba(75,139,244,0.15); color: #93bbff; }}
    .conf-low  {{ background: rgba(248,161,0,0.15); color: #fbbf24; }}
    .upset-badge {{ background: rgba(239,68,68,0.15); color: #f87171; }}
    .tossup-badge {{ background: rgba(248,161,0,0.12); color: #fbbf24; }}

    /* Collapsible week results */
    .week-details {{ border: none; }}
    .week-summary {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      list-style: none;
      user-select: none;
    }}
    .week-summary::-webkit-details-marker {{ display: none; }}
    .week-summary::marker {{ display: none; }}
    .chevron {{
      margin-left: auto;
      font-size: 3rem;
      color: var(--muted);
      transition: transform 0.2s;
      line-height: 1;
    }}
    .week-details[open] .chevron {{ transform: rotate(180deg); }}
    .week-summary:hover {{ color: var(--text); }}

    /* This week day grouping */
    .day-group {{ margin-bottom: 0.25rem; }}
    .day-group:last-child {{ margin-bottom: 0; }}
    .day-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.45rem 0 0.2rem;
      border-top: 1px solid var(--border);
      margin-top: 0.1rem;
    }}
    .day-group:first-child .day-header {{ border-top: none; padding-top: 0; }}
    .day-label {{ font-size: 0.7rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; }}
    .day-record {{ font-size: 0.72rem; font-weight: 700; }}
    .day-pct-good {{ color: #34d399; }}
    .day-pct-ok   {{ color: #fbbf24; }}
    .day-pct-bad  {{ color: #f87171; }}

    /* Results rows */
    .result-row {{
      display: grid;
      grid-template-columns: 1.5rem 1fr auto auto;
      align-items: center;
      gap: 0.4rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid var(--border);
      font-size: 0.8rem;
    }}
    .result-row:last-child {{ border-bottom: none; }}
    .result-correct {{ opacity: 1; }}
    .result-miss {{ opacity: 0.6; }}
    .result-teams {{ color: var(--muted); font-size: 0.73rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-decoration: none; }}
    .result-teams:hover {{ color: var(--accent); text-decoration: underline; }}
    .result-pick {{ font-weight: 500; font-size: 0.78rem; }}
    .result-score {{ font-size: 0.73rem; color: var(--muted); text-align: right; white-space: nowrap; }}
    .result-icon {{ font-size: 0.9rem; }}

    .record-pill {{
      font-size: 0.7rem;
      padding: 0.1rem 0.45rem;
      border-radius: 4px;
      font-weight: 700;
    }}
    .pill-good {{ background: rgba(16,185,129,0.12); color: #34d399; }}
    .pill-ok   {{ background: rgba(248,161,0,0.12); color: #fbbf24; }}

    /* Player table */
    .table-wrap {{ overflow-x: auto; }}
    .player-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    .player-table th {{
      text-align: left;
      padding: 0.4rem 0.5rem;
      color: var(--muted);
      font-size: 0.63rem;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      border-bottom: 1px solid var(--border);
      font-weight: 600;
    }}
    .player-table td {{
      padding: 0.45rem 0.5rem;
      border-bottom: 1px solid rgba(30,45,69,0.8);
    }}
    .rank {{ color: var(--muted); width: 2rem; font-size: 0.72rem; }}
    .pname {{ font-weight: 600; }}
    .pteam {{ color: var(--muted); font-size: 0.75rem; white-space: nowrap; }}
    .pteam-logo {{ width: 18px; height: 18px; object-fit: contain; vertical-align: middle; opacity: 0.85; margin-right: 0.2rem; }}
    .pelo {{ font-weight: 700; color: var(--accent); text-align: right; }}
    .th-elo {{ text-align: right !important; }}
    .result-icon {{ display: flex; align-items: center; }}

    /* Weekly summary */
    .week-row {{
      display: grid;
      grid-template-columns: 5rem 1fr auto;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4rem 0;
      border-bottom: 1px solid var(--border);
    }}
    .week-row:last-child {{ border-bottom: none; }}
    .week-day {{ font-size: 0.75rem; color: var(--muted); font-weight: 500; }}
    .week-bar-wrap {{ background: rgba(30,45,69,0.6); border-radius: 3px; height: 8px; overflow: hidden; }}
    .week-bar {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
    .week-record {{ font-size: 0.75rem; font-weight: 700; white-space: nowrap; }}
    .week-record small {{ font-weight: 400; color: var(--muted); }}

    /* Injury alerts */
    .inj-block {{ margin-top: 0.5rem; border-top: 1px solid var(--border); padding-top: 0.4rem; }}
    .inj-row {{ font-size: 0.7rem; margin-bottom: 0.2rem; line-height: 1.5; }}
    .inj-team {{ color: var(--muted); margin-right: 0.3rem; font-weight: 600; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.5px; }}
    .inj-pill {{ display: inline-block; margin-right: 0.35rem; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.68rem; }}
    .inj-pill em {{ font-style: normal; opacity: 0.7; }}
    .inj-star    {{ background: rgba(239,68,68,0.12); color: #f87171; }}
    .inj-starter {{ background: rgba(248,161,0,0.12); color: #fbbf24; }}
    .inj-role    {{ background: rgba(100,116,139,0.15); color: #94a3b8; }}

    /* ── Footer ── */
    footer {{
      position: relative;
      width: 100%;
      max-width: 860px;
      margin: 2rem auto 0;
      border-top: 1px solid var(--border);
      border-radius: 1.25rem 1.25rem 0 0;
      background: radial-gradient(35% 80px at 50% 0%, rgba(255,255,255,0.04), transparent);
      padding: 2.5rem 1.5rem 2rem;
      overflow: hidden;
    }}
    .footer-glow-line {{
      position: absolute;
      top: 0; left: 50%; transform: translateX(-50%);
      width: 33%; height: 1px;
      background: rgba(255,255,255,0.18);
      border-radius: 999px;
      filter: blur(2px);
    }}
    .footer-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 2rem;
    }}
    @media (min-width: 640px) {{
      .footer-grid {{ grid-template-columns: 1fr 2fr; gap: 2.5rem; }}
    }}
    .footer-brand {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .footer-brand-name {{
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.1rem;
      color: var(--text);
      letter-spacing: -0.02em;
    }}
    .footer-brand-copy {{
      font-size: 0.68rem;
      color: var(--muted);
      line-height: 1.6;
    }}
    .footer-links-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.5rem 1rem;
    }}
    @media (min-width: 640px) {{
      .footer-links-grid {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    .footer-section-label {{
      font-size: 0.6rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--text);
      margin-bottom: 0.75rem;
    }}
    .footer-links {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }}
    .footer-links a {{
      font-size: 0.72rem;
      color: var(--muted);
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      transition: color 0.2s;
    }}
    .footer-links a:hover {{ color: var(--text); }}
    .footer-links svg {{
      width: 13px; height: 13px;
      flex-shrink: 0;
      opacity: 0.7;
    }}
    /* Entrance animation */
    .footer-anim {{
      opacity: 0;
      transform: translateY(-8px);
      filter: blur(4px);
      transition: opacity 0.7s ease, transform 0.7s ease, filter 0.7s ease;
    }}
    .footer-anim.in-view {{
      opacity: 1;
      transform: translateY(0);
      filter: blur(0);
    }}

    /* Clickable game card — overlay anchor, avoids block-in-inline parsing issues */
    .game-card {{ position: relative; cursor: pointer; }}
    .game-card-link {{
      position: absolute;
      inset: 0;
      z-index: 1;
      border-radius: 10px;
    }}
    .game-card:hover {{
      background: var(--surface-hi);
      border-color: var(--accent);
    }}

    /* Injury pills sit above the card overlay so tapping them opens ESPN, not NBA.com */
    .inj-block {{ position: relative; z-index: 2; }}
    a.inj-pill {{
      text-decoration: none;
      cursor: pointer;
      position: relative;
      z-index: 2;
    }}
    a.inj-pill:hover {{ text-decoration: underline; opacity: 1; }}

    /* Team logos */
    .team-logo {{
      width: 26px;
      height: 26px;
      object-fit: contain;
      vertical-align: middle;
      opacity: 0.7;
    }}
    .team-logo-pick {{
      opacity: 1;
      filter: drop-shadow(0 0 3px rgba(248,161,0,0.4));
    }}

    @media (max-width: 400px) {{
      .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
      header h1 {{ font-size: 2.55rem; }}
      .team-logo {{ width: 20px; height: 20px; }}
      .qscore-label {{ font-size: 0.58rem; }}
    }}

    /* ── Glowing border ring (Aceternity-style, vanilla port) ── */
    .game-card {{ isolation: isolate; }}
    .glow-ring {{
      position: absolute;
      inset: -1px;
      border-radius: 11px;
      padding: 1px;
      background-image: conic-gradient(
        from calc((var(--glow-start, 0) - 35) * 1deg) at 50% 50%,
        transparent   0deg,
        #dd7bbb      12deg,
        #f8a100      25deg,
        #a855f7      38deg,
        #4b8bf4      52deg,
        transparent  70deg,
        transparent 360deg
      );
      -webkit-mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      z-index: 0;
      opacity: var(--glow-active, 0);
      transition: opacity 0.35s ease;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div class="header-text">
        <h1>Second Bounce</h1>
        <p class="tagline">NBA game predictions, powered by ELO</p>
      </div>
      <img src="logo.png" alt="Second Bounce" class="site-logo" onerror="this.style.display='none'">
    </div>
  </header>

  <div class="container">
    {stats_html}

    {weekly_html}

    <div class="games-date">{date_str} &nbsp;·&nbsp; {games_count} game{'s' if games_count != 1 else ''} today</div>
    <div class="games-header">Today's Predictions</div>
    {pred_cards}

    {yesterday_html}

    {players_html}
  </div>

  <footer>
    <div class="footer-glow-line"></div>
    <div class="footer-grid">

      <div class="footer-brand footer-anim" style="transition-delay:0s">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="14" cy="14" r="13" stroke="var(--accent)" stroke-width="1.5"/>
          <circle cx="14" cy="14" r="6" fill="var(--pick)" opacity="0.85"/>
        </svg>
        <span class="footer-brand-name">Second Bounce</span>
        <p class="footer-brand-copy">
          NBA game predictions powered by a hybrid ELO model.<br>
          Updated daily. &copy; {datetime.now().year} Aaron Thomas.
        </p>
      </div>

      <div class="footer-links-grid">

        <div class="footer-anim" style="transition-delay:0.1s">
          <div class="footer-section-label">Predictions</div>
          <ul class="footer-links">
            <li><a href="#today">Today's Picks</a></li>
            <li><a href="#week">This Week</a></li>
            <li><a href="#stats">Season Stats</a></li>
            <li><a href="#injuries">Injury Report</a></li>
          </ul>
        </div>

        <div class="footer-anim" style="transition-delay:0.2s">
          <div class="footer-section-label">Model</div>
          <ul class="footer-links">
            <li><a href="https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/" target="_blank" rel="noopener">Methodology</a></li>
            <li><a href="https://github.com/atr777/nba-predictions" target="_blank" rel="noopener">GitHub</a></li>
            <li><a href="https://harvardsportsanalysis.org/2019/01/a-simple-improvement-to-fivethirtyeights-nba-elo-model/" target="_blank" rel="noopener">Research</a></li>
          </ul>
        </div>

        <div class="footer-anim" style="transition-delay:0.35s">
          <div class="footer-section-label">Social</div>
          <ul class="footer-links">
            <li>
              <span style="display:inline-flex;align-items:center;gap:0.3rem;font-size:0.72rem;color:var(--muted);opacity:0.5;">
                <svg viewBox="0 0 24 24" fill="currentColor" style="width:13px;height:13px"><path d="M22.46 6c-.77.35-1.6.58-2.46.69.88-.53 1.56-1.37 1.88-2.38-.83.5-1.75.85-2.72 1.05C18.37 4.5 17.26 4 16 4c-2.35 0-4.27 1.92-4.27 4.29 0 .34.04.67.11.98C8.28 9.09 5.11 7.38 3 4.79c-.37.63-.58 1.37-.58 2.15 0 1.49.75 2.81 1.91 3.56-.71 0-1.37-.2-1.95-.5v.03c0 2.08 1.48 3.82 3.44 4.21a4.22 4.22 0 0 1-1.93.07 4.28 4.28 0 0 0 4 2.98 8.521 8.521 0 0 1-5.33 1.84c-.34 0-.68-.02-1.02-.06C3.44 20.29 5.7 21 8.12 21 16 21 20.33 14.46 20.33 8.79c0-.19 0-.37-.01-.56.84-.6 1.56-1.36 2.14-2.23z"/></svg>
                Twitter / X <em style="font-style:normal;font-size:0.6rem;opacity:0.7;">(Soon)</em>
              </span>
            </li>
            <li>
              <a href="https://github.com/atr777/nba-predictions" target="_blank" rel="noopener">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/></svg>
                GitHub
              </a>
            </li>
            <li>
              <span style="display:inline-flex;align-items:center;gap:0.3rem;font-size:0.72rem;color:var(--muted);opacity:0.5;">
                <svg viewBox="0 0 24 24" fill="currentColor" style="width:13px;height:13px"><path d="M20.317 4.492c-1.53-.69-3.17-1.2-4.885-1.49a.075.075 0 0 0-.079.036c-.21.369-.444.85-.608 1.23a18.566 18.566 0 0 0-5.487 0 12.36 12.36 0 0 0-.617-1.23A.077.077 0 0 0 8.562 3c-1.714.29-3.354.8-4.885 1.491a.07.07 0 0 0-.032.027C.533 9.093-.32 13.555.099 17.961a.08.08 0 0 0 .031.055 20.03 20.03 0 0 0 5.993 2.98.078.078 0 0 0 .084-.026c.462-.62.874-1.275 1.226-1.963.021-.04.001-.088-.041-.104a13.201 13.201 0 0 1-1.872-.878.075.075 0 0 1-.008-.125c.126-.093.252-.19.372-.287a.075.075 0 0 1 .078-.01c3.927 1.764 8.18 1.764 12.061 0a.075.075 0 0 1 .079.009c.12.098.245.195.372.288a.075.075 0 0 1-.006.125c-.598.344-1.22.635-1.873.877a.075.075 0 0 0-.041.105c.36.687.772 1.341 1.225 1.962a.077.077 0 0 0 .084.028 19.963 19.963 0 0 0 6.002-2.981.076.076 0 0 0 .032-.054c.5-5.094-.838-9.52-3.549-13.442a.06.06 0 0 0-.031-.028z"/></svg>
                Discord <em style="font-style:normal;font-size:0.6rem;opacity:0.7;">(Soon)</em>
              </span>
            </li>
          </ul>
        </div>

      </div>
    </div>

    <div class="footer-anim" style="transition-delay:0.5s;margin-top:2rem;padding-top:1rem;border-top:1px solid var(--border);text-align:center;font-size:0.62rem;color:var(--muted);opacity:0.6;">
      Hybrid ELO Model &nbsp;·&nbsp; Updated {datetime.now().strftime('%b %d, %Y %I:%M %p')} &nbsp;·&nbsp; Made by Aaron Thomas &amp; Claude Code
    </div>
  </footer>

  <script>
    // Convert ET game times to the visitor's local timezone
    document.querySelectorAll('.game-time[data-iso]').forEach(function(el) {{
      try {{
        var d = new Date(el.dataset.iso);
        if (isNaN(d.getTime())) return;
        var day  = d.toLocaleDateString(undefined, {{ weekday: 'short' }});
        var time = d.toLocaleTimeString(undefined, {{ hour: 'numeric', minute: '2-digit' }});
        el.textContent = day + ' \u00b7 ' + time;
      }} catch(e) {{}}
    }});

    // ── Header scroll transparency: full opacity at top → 30% opacity (70% transparent) on scroll ──
    (function() {{
      var hdr = document.querySelector('header');
      if (!hdr) return;
      var BASE_ALPHA = 0.78;   // starting opacity at top
      var MIN_ALPHA  = 0.30;   // target opacity when scrolled (70% transparent)
      var FADE_PX    = 120;    // pixels of scroll to complete the transition
      function updateHeader() {{
        var t = Math.min(window.scrollY / FADE_PX, 1);
        var alpha = BASE_ALPHA + (MIN_ALPHA - BASE_ALPHA) * t;
        hdr.style.backgroundColor = 'rgba(15,22,35,' + alpha.toFixed(3) + ')';
      }}
      window.addEventListener('scroll', updateHeader, {{ passive: true }});
      updateHeader();
    }})();

    // ── Footer entrance animations (IntersectionObserver, replaces motion/react whileInView) ──
    (function() {{
      var els = document.querySelectorAll('.footer-anim');
      if (!els.length) return;
      var obs = new IntersectionObserver(function(entries) {{
        entries.forEach(function(entry) {{
          if (entry.isIntersecting) {{
            entry.target.classList.add('in-view');
            obs.unobserve(entry.target);
          }}
        }});
      }}, {{ threshold: 0.15 }});
      els.forEach(function(el) {{ obs.observe(el); }});
    }})();

    // ── Glowing border ring — Aceternity-style vanilla port ──
    (function() {{
      var cards = Array.from(document.querySelectorAll('.game-card'));
      var states = new Map();

      cards.forEach(function(card) {{
        var ring = document.createElement('div');
        ring.className = 'glow-ring';
        card.appendChild(ring);
        states.set(card, {{ current: 0, target: 0, raf: null }});
      }});

      function normDiff(d) {{ return ((d % 360) + 540) % 360 - 180; }}

      function tick(card) {{
        var s = states.get(card);
        var diff = normDiff(s.target - s.current);
        if (Math.abs(diff) < 0.2) {{ s.current = s.target; s.raf = null; return; }}
        s.current += diff * 0.08;
        card.style.setProperty('--glow-start', s.current.toFixed(1));
        s.raf = requestAnimationFrame(function() {{ tick(card); }});
      }}

      document.body.addEventListener('pointermove', function(e) {{
        var mx = e.clientX, my = e.clientY;
        cards.forEach(function(card) {{
          var r = card.getBoundingClientRect();
          var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
          var prox = 64;
          var active = mx > r.left - prox && mx < r.right + prox &&
                       my > r.top  - prox && my < r.bottom + prox;
          card.style.setProperty('--glow-active', active ? '1' : '0');
          if (!active) return;
          var s = states.get(card);
          s.target = Math.atan2(my - cy, mx - cx) * 180 / Math.PI + 90;
          if (!s.raf) s.raf = requestAnimationFrame(function() {{ tick(card); }});
        }});
      }}, {{ passive: true }});
    }})();
  </script>
</body>
</html>"""


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
    return out_path


if __name__ == '__main__':
    # Change to nba-elo-engine dir so relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    engine_dir = os.path.join(script_dir, '..')
    os.chdir(engine_dir)
    main()
