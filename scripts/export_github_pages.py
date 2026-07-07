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

import json
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
                conf_label, conf_class = 'High Confidence', 'conf-high'
            elif win_prob >= 0.63:
                conf_label, conf_class = 'Medium Confidence', 'conf-med'
            else:
                conf_label, conf_class = 'Too Close to Call', 'conf-low'

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
    """Recent graded results. In season: yesterday's games. Offseason (no games
    yesterday): fall back to the most recent graded games, so the public
    receipts are always visible to a visitor, not blank."""
    df = load_csv('data/exports/prediction_tracking.csv')
    if df.empty:
        return [], {}

    df = df.sort_values('date')
    today = datetime.now()
    yesterday_int = int((today - timedelta(days=1)).strftime('%Y%m%d'))

    week = df[df['date'] == yesterday_int]
    if week.empty:
        # Offseason fallback: the last 18 graded games (games with a result).
        graded = df[df['correct'].notna()] if 'correct' in df.columns else df
        week = graded.tail(18)
    if week.empty:
        return [], {}

    # Group by date, newest first
    days = []
    for date_int, group in sorted(week.groupby('date'), reverse=True):
        try:
            d = datetime.strptime(str(date_int), '%Y%m%d')
            day_label = d.strftime('%b %-d, %Y') if os.name != 'nt' else d.strftime('%b %#d, %Y')
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
    if 'raw_rating' not in df.columns:
        df['raw_rating'] = df['rating']
    cols = ['player_name', 'team_name', 'rating', 'raw_rating', 'games_played']
    top = df.nlargest(n, 'rating')[cols]

    players = []
    for i, (_, row) in enumerate(top.iterrows(), 1):
        team_name = row['team_name']
        team_abbr = TEAM_ABBREVS.get(team_name, team_name[:3].upper() if len(team_name) >= 3 else team_name)
        elo = int(row['rating'])
        adj = int(round(row['rating'] - row['raw_rating']))
        players.append({
            'rank': i,
            'name': row['player_name'],
            'team': team_name,
            'team_abbr': team_abbr,
            'team_logo': get_logo_by_abbrev(team_abbr),
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
    df['team_name'] = df['team_name'].fillna('—')
    if 'raw_rating' not in df.columns:
        df['raw_rating'] = df['rating']
    df = df[df['games_played'] >= min_games].nlargest(cap, 'rating')

    out = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        team_name = row['team_name']
        team_abbr = TEAM_ABBREVS.get(team_name, team_name[:3].upper() if len(team_name) >= 3 else team_name)
        out.append({
            'rank': i,
            'name': row['player_name'],
            'abbr': team_abbr,
            'logo': get_logo_by_abbrev(team_abbr),
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


def _to_iso_et(date_iso, time_str):
    """Convert '7:30 pm ET' + '2026-03-10' to an ISO-8601 string with ET offset."""
    clean = time_str.replace(' ET', '').replace(' et', '').strip()
    try:
        dt = datetime.strptime(f"{date_iso} {clean}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        return None
    offset = '-04:00' if _is_edt(dt) else '-05:00'
    return f"{date_iso}T{dt.strftime('%H:%M')}:00{offset}"


def prob_bar(home_prob, home_name, away_name, is_home_win=True):
    """Render a two-sided probability bar. Pick side = amber, opponent = muted."""
    hp = round(home_prob * 100)
    ap = 100 - hp
    if is_home_win:
        left_bar, right_bar = 'prob-bar-away', 'prob-bar-home'
        left_lbl, right_lbl = 'prob-label-away', 'prob-label-home'
    else:
        # Away is the pick — left side gets amber
        left_bar, right_bar = 'prob-bar-home', 'prob-bar-away'
        left_lbl, right_lbl = 'prob-label-home', 'prob-label-away'
    return f"""
    <div class="prob-bar-wrap">
      <span class="{left_lbl}">{ap}%</span>
      <div class="prob-bar-split">
        <div class="{left_bar}" style="width:{ap}%"></div>
        <div class="{right_bar}" style="width:{hp}%"></div>
      </div>
      <span class="{right_lbl}">{hp}%</span>
    </div>"""


def render_html(date_str, predictions, week_days, week_summary, stats, players,
                weekly=None, injuries=None):
    """Origin (video-hero) template renderer.

    Reads templates/origin.html (a plain static file — CSS/JS braces are
    NOT doubled because this is never evaluated as an f-string) and fills
    in the dynamic regions via simple str.replace() token substitution.

    `weekly` and `injuries` are accepted for call-site compatibility with
    main() but are not rendered in the Origin layout (no bar-chart weekly
    summary or per-game injury callouts in this design — flagged to Aaron
    as a deliberately deferred feature, not an oversight).
    """
    games_count = len(predictions)
    try:
        date_iso = datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
    except ValueError:
        date_iso = datetime.now().strftime('%Y-%m-%d')

    stats = stats or {}

    # ---- small local rendering helpers ---- #
    def _pct1(numerator, denominator):
        """Format a ratio as a one-decimal percent string, or '—' if invalid."""
        try:
            numerator = float(numerator)
            denominator = float(denominator)
            if denominator:
                return f"{numerator / denominator * 100:.1f}"
        except (TypeError, ValueError):
            pass
        return '—'

    def _team_logo(team_name):
        abbr = TEAM_ABBREVS.get(team_name, team_name[:3].upper() if team_name else '')
        return get_logo_by_abbrev(abbr)

    acc_pct     = _pct1(stats.get('correct'), stats.get('total'))
    total_games = stats.get('total', '—')

    # ---- {{DATE_STAMP}} ---- #
    date_stamp = f"{date_str} · {games_count} game{'s' if games_count != 1 else ''} today"

    # ---- {{STATS}} ---- #
    _tp = stats.get('tossup_pct')
    if _tp in (None, 'N/A'):
        tossup_display = _tp or '—'
    else:
        tossup_display = f"{_tp}%"

    stats_html = f"""
      <div class="stat">
        <div class="stat-value">{acc_pct}%</div>
        <div class="stat-label">Season Accuracy</div>
        <div class="stat-sub">{stats.get('correct', '—')} of {total_games} correct</div>
      </div>
      <div class="stat">
        <div class="stat-value">{tossup_display}</div>
        <div class="stat-label">Toss-Up Games</div>
        <div class="stat-sub">games within 30 elo pts</div>
      </div>
      <div class="stat">
        <div class="stat-value">{total_games}</div>
        <div class="stat-label">Games Tracked</div>
        <div class="stat-sub">since Oct 2025</div>
      </div>"""

    # ---- {{PREDICTIONS}} — live game cards, offseason CTA, or no-games ---- #
    if predictions:
        cards = []
        for p in predictions:
            status_code = p.get('game_status_code', 1)
            is_live  = status_code == 2
            is_final = status_code == 3
            if is_final:
                time_display, iso_attr = 'Final', ''
            elif is_live:
                time_display = p['time'] if p['time'] != 'TBD' else 'Live'
                iso_attr = ''
            else:
                time_display = p['time']
                iso_ts = _to_iso_et(date_iso, p['time'])
                iso_attr = f' data-iso="{iso_ts}"' if iso_ts else ''

            away_logo = _team_logo(p['away'])
            home_logo = _team_logo(p['home'])
            hp = round(p['home_prob'] * 100)
            ap = 100 - hp
            pick_pct = hp if p['is_home_win'] else ap

            cards.append(f"""
      <div class="card game-card{' game-card-final' if is_final else ''}">
        <a class="game-card-link" href="{p['nba_url']}" target="_blank" rel="noopener" aria-label="View {p['away']} @ {p['home']} on NBA.com"></a>
        <div class="game-card-head">
          <span class="game-time mono"{iso_attr}>{time_display}</span>
          <span class="chip chip-neutral">{p['conf_label']}{' &middot; Toss-up' if p['tossup'] else ''}</span>
        </div>
        <div class="result-matchup" style="margin-top:16px;">
          <span class="team-pair"><img class="team-logo" src="{away_logo}" alt="" onerror="this.style.display='none'">{p['away']}</span>
          <span class="matchup-vs">@</span>
          <span class="team-pair"><img class="team-logo" src="{home_logo}" alt="" onerror="this.style.display='none'">{p['home']}</span>
        </div>
        <div class="game-pick-line">{p['winner']} {'slight edge' if p['tossup'] else 'favored to win'} <span class="mono">&middot; {p['win_prob'] * 100:.0f}%</span></div>
        <div class="game-prob-track"><div class="game-prob-fill" style="width:{pick_pct}%;"></div></div>
        <div class="game-elo-line mono">Elo &middot; {p['away']} {p['away_elo']:.0f} &middot; {p['home']} {p['home_elo']:.0f}</div>
      </div>""")
        predictions_html = ''.join(cards)
    else:
        _md = (datetime.now().month, datetime.now().day)
        is_offseason = (6, 25) <= _md <= (10, 20)
        if is_offseason:
            predictions_html = f"""
      <div class="card card-offseason">
        <h2 class="card-headline">No games today. The season is over.</h2>
        <p class="card-body">
          The model finished {acc_pct}% across {total_games} tracked games. Daily predictions
          return opening night. Until then we break down every offseason move
          through the model's eyes.
        </p>
        <a class="btn-primary" href="https://secondbounce.substack.com" target="_blank" rel="noopener">
          <svg viewBox="0 0 24 24" fill="currentColor" style="width:15px;height:15px;flex-shrink:0;"><path d="M22.539 8.242H1.46V5.406h21.08v2.836zM1.46 10.812H22.54V24l-10.54-5.9L1.46 24V10.812zM22.54 0H1.46v2.836h21.08V0z"/></svg>
          Get the model's offseason analysis
        </a>
      </div>"""
        else:
            predictions_html = """
      <div class="card card-offseason">
        <h2 class="card-headline">No games scheduled today.</h2>
        <p class="card-body">Predictions post every game day. Check back tomorrow, or see recent results below.</p>
        <a class="btn-ghost" href="#results">See recent results</a>
      </div>"""

    # ---- {{RESULTS}} — day-grouped, ESPN logos, green/red chips ---- #
    if week_days:
        day_blocks = []
        for day in week_days:
            day_correct = day['correct']
            day_total   = day['total']
            row_blocks  = []
            for r in day['rows']:
                marker_cls = 'chip-correct' if r['correct'] else 'chip-miss'
                marker_txt = 'Correct' if r['correct'] else 'Miss'
                pick_side  = 'Home' if r['predicted'] == r['home'] else 'Away'
                away_logo  = _team_logo(r['away'])
                home_logo  = _team_logo(r['home'])
                score_html = ''
                if r['away_score'] != '':
                    score_html = f'<span class="result-score mono">{r["away_score"]}&ndash;{r["home_score"]}</span>'
                upset_html = ' <span class="chip chip-neutral">Upset</span>' if r.get('upset') else ''
                row_blocks.append(f"""
          <div class="result-row">
            <span class="result-matchup">
              <span class="team-pair"><img class="team-logo" src="{away_logo}" alt="" onerror="this.style.display='none'">{r['away']}</span>
              <span class="matchup-vs">@</span>
              <span class="team-pair"><img class="team-logo" src="{home_logo}" alt="" onerror="this.style.display='none'">{r['home']}</span>
            </span>
            {score_html}
            <span class="chip chip-neutral">Pick {pick_side}</span>{upset_html}
            <span class="chip {marker_cls}">{marker_txt}</span>
          </div>""")
            day_blocks.append(f"""
        <div class="results-day">
          <div class="results-day-head">
            <span class="results-day-label mono">{day['label']}</span>
            <span class="results-day-record mono">{day_correct}-{day_total - day_correct} ({day['pct']})</span>
          </div>
          {''.join(row_blocks)}
        </div>""")
        results_html = ''.join(day_blocks)
    else:
        results_html = '<p style="color:var(--ash);text-align:center;padding:20px 0;">No graded results yet.</p>'

    # ---- {{PLAYERS}} — full 15 rows, no truncation ---- #
    if players:
        rows = []
        for p in players:
            elo  = p['elo']
            frac = max(0.06, min(1.0, (elo - 1500) / (2650 - 1500)))
            barw = f"{frac * 100:.0f}"
            adj  = p['adj']
            if adj >= 20:
                adj_cell = f'<td class="p-adj">&#9650; +{adj}</td>'
            elif adj <= -20:
                adj_cell = f'<td class="p-adj">&#9660; {adj}</td>'
            else:
                adj_cell = '<td class="p-adj dim">&mdash;</td>'
            rows.append(f"""
              <tr>
                <td class="p-rank">{p['rank']}</td>
                <td>{p['name']}</td>
                <td class="p-team"><span class="team-cell"><img class="team-logo-sm" src="{p['team_logo']}" alt="" onerror="this.style.display='none'"><span class="mono">{p['team_abbr']}</span></span></td>
                <td class="p-gp">{p['games']}</td>
                <td class="p-rating-cell">
                  <div class="rating-track"><div class="rating-fill" style="width:{barw}%;"></div></div>
                  <span class="rating-num">{elo}</span>
                </td>
                {adj_cell}
              </tr>""")
        players_html = ''.join(rows)
    else:
        players_html = '<tr><td colspan="6" style="text-align:center;color:var(--ash);padding:20px;">No player ratings available.</td></tr>'

    # ---- {{RECEIPT}} / {{FOOTER_LEGAL}} ---- #
    receipt_html = f"[ {acc_pct}% · {total_games} games · verified walk-forward ]"
    footer_legal_html = f"&copy; {datetime.now().year} Second Bounce &nbsp;&middot;&nbsp; Updated {datetime.now().strftime('%b %d, %Y %I:%M %p')}"

    # ---- Assemble from the static template via token replacement ---- #
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'origin.html')
    with open(template_path, encoding='utf-8') as f:
        html = f.read()

    # Full rated roster for the client-side player lookup (compact JSON)
    players_json = json.dumps(get_all_players(), separators=(',', ':'), ensure_ascii=False)

    replacements = {
        '{{DATE_STR}}':     date_str,
        '{{DATE_STAMP}}':   date_stamp,
        '{{STATS}}':        stats_html,
        '{{PREDICTIONS}}':  predictions_html,
        '{{RESULTS}}':      results_html,
        '{{PLAYERS}}':      players_html,
        '{{PLAYERS_JSON}}': players_json,
        '{{RECEIPT}}':      receipt_html,
        '{{FOOTER_LEGAL}}': footer_legal_html,
    }
    for token, value in replacements.items():
        html = html.replace(token, value)

    return html


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
