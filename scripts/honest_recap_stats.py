"""Compute the honest (walk-forward) 2025-26 recap stats for the launch post."""

import pandas as pd

h = pd.read_csv("data/exports/honest_walkforward_2025_26.csv")
t = pd.read_csv("data/exports/prediction_tracking_vps_final.csv")
t["game_id"] = [f"{r.date}_{r.home_team_id}_{r.away_team_id}" for r in t.itertuples()]
df = t.merge(h[["game_id", "honest_home_prob", "honest_correct"]], on="game_id")
df["conf"] = df.honest_home_prob.where(df.honest_home_prob >= 0.5,
                                       1 - df.honest_home_prob)
df["ok"] = df.honest_correct.astype(bool)

n = len(df)
print(f"overall: {df.ok.mean()*100:.2f}%  ({df.ok.sum()} of {n})")

df["month"] = df.date.astype(str).str[:6]
print("\nmonthly:")
print((df.groupby("month").ok.agg(["count", "mean"]) * [1, 100]).round(1))

hc = df[df.conf >= 0.75]
print(f"\nhigh-conf (>=75%): {len(hc)} games, {hc.ok.mean()*100:.1f}%")
cg = df[df.is_close_game == True]
print(f"close games: {len(cg)} games, {cg.ok.mean()*100:.1f}%")

bins = [0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
labels = ["50-60%", "60-70%", "70-80%", "80-90%", "90%+"]
df["bucket"] = pd.cut(df.conf, bins=bins, labels=labels, right=False)
cal = df.groupby("bucket", observed=True).agg(
    n=("ok", "size"), actual=("ok", "mean"), expected=("conf", "mean"))
print("\ncalibration:")
print((cal * [1, 100, 100]).round(1))

s = df.sort_values(["date", "timestamp"]).ok.astype(int)
streak = s.groupby((s.diff() != 0).cumsum()).cumsum().max()
print(f"\nlongest correct streak: {int(streak)}")

miss = df[(~df.ok) & (df.conf >= 0.85)].sort_values("conf", ascending=False)
cols = ["date", "home_team_name", "away_team_name", "conf",
        "actual_home_score", "actual_away_score", "honest_home_prob"]
print("\nmost confident misses:")
print(miss[cols].head(4).to_string(index=False))

dog = df[((df.honest_home_prob >= 0.5) & (df.elo_diff < 0)) |
         ((df.honest_home_prob < 0.5) & (df.elo_diff > 0))]
print(f"\npicked against raw ELO favorite: {len(dog)} games, "
      f"{dog.ok.mean()*100:.1f}%")
