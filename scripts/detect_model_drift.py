"""
Automated Model Drift Detection — Sprint 6
Runs after every daily update. Reads prediction_tracking.csv and checks:
  1. 7-day accuracy drops 5+ pp below 30-day baseline
  2. 3+ consecutive wrong picks

Outputs:
  - data/exports/DRIFT_STATUS.md  (written every run — healthy or not)
  - logs/daily_update.log          (appends [DRIFT] lines only on alert)

Usage:
    python scripts/detect_model_drift.py
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.utils.file_io import load_yaml, get_config_path

# ── Paths ────────────────────────────────────────────────────────────────────
TRACKING_FILE  = Path('data/exports/prediction_tracking.csv')
STATUS_FILE    = Path('data/exports/DRIFT_STATUS.md')
LOG_FILE       = Path('logs/daily_update.log')

# ── Helpers ──────────────────────────────────────────────────────────────────
def _now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _log(message: str):
    """Print and append to daily_update.log in the same format as daily_update.py."""
    ts = _now_str()
    line = f"[{ts}] {message}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

def _load_settings():
    try:
        cfg = load_yaml(get_config_path('settings.yaml'))
        drift = cfg.get('drift_detection', {})
        return {
            'min_games_7d':  drift.get('min_games_7d', 5),
            'min_games_30d': drift.get('min_games_30d', 10),
            'acc_drop':      drift.get('accuracy_drop_threshold', 0.05),
            'streak_limit':  drift.get('consecutive_loss_threshold', 3),
        }
    except Exception:
        return {'min_games_7d': 5, 'min_games_30d': 10, 'acc_drop': 0.05, 'streak_limit': 3}

# ── Core logic ────────────────────────────────────────────────────────────────
def run_drift_check():
    cfg = _load_settings()

    # Load tracking data
    if not TRACKING_FILE.exists():
        _log('[DRIFT] SKIP: prediction_tracking.csv not found')
        return

    df = pd.read_csv(TRACKING_FILE)

    # Normalise date column (stored as int YYYYMMDD or string)
    try:
        df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d', errors='coerce')
    except Exception:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    df = df.sort_values('date')
    scored = df[df['correct'].notna()].copy()
    scored['correct'] = scored['correct'].astype(bool)

    if len(scored) == 0:
        _log('[DRIFT] SKIP: no scored predictions found')
        return

    today = pd.Timestamp.now().normalize()
    last_7  = scored[scored['date'] >= today - timedelta(days=7)]
    last_30 = scored[scored['date'] >= today - timedelta(days=30)]

    n7  = len(last_7)
    n30 = len(last_30)
    acc_7d  = last_7['correct'].mean()  if n7  > 0 else None
    acc_30d = last_30['correct'].mean() if n30 > 0 else None

    # Consecutive loss streak from most recent picks
    recent_correct = scored['correct'].tolist()[-20:]
    streak = 0
    for val in reversed(recent_correct):
        if not val:
            streak += 1
        else:
            break

    # Season overall
    current_season_start = pd.Timestamp('2025-10-01')
    season = scored[scored['date'] >= current_season_start]
    acc_season = season['correct'].mean() if len(season) > 0 else None

    # ── Drift checks ─────────────────────────────────────────────────────────
    alerts = []

    drop_pp = None
    if (acc_7d is not None and acc_30d is not None
            and n7 >= cfg['min_games_7d'] and n30 >= cfg['min_games_30d']):
        drop = acc_30d - acc_7d
        drop_pp = drop * 100
        if drop >= cfg['acc_drop']:
            alerts.append(
                f"7-day accuracy {acc_7d*100:.1f}% is {drop_pp:.1f}pp below "
                f"30-day baseline {acc_30d*100:.1f}%"
            )

    if streak >= cfg['streak_limit']:
        alerts.append(f"{streak} consecutive wrong picks")

    # ── Write DRIFT_STATUS.md ─────────────────────────────────────────────────
    status_icon = 'DRIFT DETECTED' if alerts else 'OK'
    status_emoji = 'ALERT' if alerts else 'OK'

    def _row(label, value, threshold, ok):
        status = 'OK' if ok else 'ALERT'
        return f'| {label} | {value} | {threshold} | {status} |'

    rows = []
    rows.append(_row(
        '7-day accuracy',
        f"{acc_7d*100:.1f}%" if acc_7d is not None else 'N/A (too few games)',
        '—', True
    ))
    rows.append(_row(
        '30-day accuracy',
        f"{acc_30d*100:.1f}%" if acc_30d is not None else 'N/A',
        '—', True
    ))
    rows.append(_row(
        '7-day vs 30-day drop',
        f"{drop_pp:.1f}pp" if drop_pp is not None else 'N/A',
        f"≥ {cfg['acc_drop']*100:.0f}pp",
        drop_pp is None or drop_pp < cfg['acc_drop'] * 100
    ))
    rows.append(_row(
        'Consecutive wrong picks',
        str(streak),
        f"≥ {cfg['streak_limit']}",
        streak < cfg['streak_limit']
    ))
    rows.append(_row(
        'Games in 7-day window',
        str(n7),
        f"≥ {cfg['min_games_7d']}",
        n7 >= cfg['min_games_7d']
    ))
    rows.append(_row(
        'Season accuracy',
        f"{acc_season*100:.1f}% ({len(season)} games)" if acc_season is not None else 'N/A',
        '—', True
    ))

    alert_block = ''
    if alerts:
        alert_block = '\n## Alerts\n\n' + '\n'.join(f'- {a}' for a in alerts) + '\n'

    md = f"""# Model Drift Status — {datetime.now().strftime('%Y-%m-%d %H:%M')} ET

## Status: {status_emoji} — {status_icon}

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
{chr(10).join(rows)}
{alert_block}
_Last checked: {_now_str()} | Thresholds: 5pp drop · {cfg['streak_limit']} consecutive losses_
"""

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(md, encoding='utf-8')

    # ── Log output ────────────────────────────────────────────────────────────
    if alerts:
        for alert in alerts:
            _log(f'[DRIFT] WARNING: {alert}')
        _log(f'[DRIFT] Full report: {STATUS_FILE}')
    else:
        acc_str = f"{acc_7d*100:.1f}%" if acc_7d is not None else "N/A"
        _log(f'[DRIFT] OK — 7-day accuracy {acc_str}, {streak} consecutive wrong, no drift detected')

    return len(alerts) == 0


if __name__ == '__main__':
    ok = run_drift_check()
    sys.exit(0 if ok else 1)
