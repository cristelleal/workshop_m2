#!/usr/bin/env python3
"""
Score un export (ex. le run avec attaques DDoS) avec le modèle entraîné sur le sain.

  python3 score.py --model models/baseline.joblib \
                   --prom data/attack/prometheus.csv --loki data/attack/loki.jsonl \
                   --attacks attacks.csv --out reports/attack

attacks.csv (optionnel) = la vérité terrain, une ligne par attaque lancée :
  start,end,label
  2026-10-21T14:05:00+02:00,2026-10-21T14:10:00+02:00,http_flood
  2026-10-21T14:20:00+02:00,2026-10-21T14:25:00+02:00,syn_flood

Sorties : <out>_scores.csv, <out>.png, et si --attacks : précision / rappel / délai de détection.
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from resilience_ml.features import build_features, load_loki_jsonl, load_prom_csv
from resilience_ml.model import ENVELOPE_THRESHOLD, AnomalyModel


def load_attacks(path):
    a = pd.read_csv(path)
    a["start"] = pd.to_datetime(a["start"], utc=True)
    a["end"] = pd.to_datetime(a["end"], utc=True)
    return a


def label_rows(index_utc, attacks):
    lab = pd.Series("normal", index=index_utc)
    for _, r in attacks.iterrows():
        lab[(index_utc >= r.start) & (index_utc <= r.end)] = r.label
    return lab


def evaluate(s, attacks):
    y = (s["truth"] != "normal").astype(int)
    p = s["anomaly"]
    tp, fp = int(((p == 1) & (y == 1)).sum()), int(((p == 1) & (y == 0)).sum())
    fn, tn = int(((p == 0) & (y == 1)).sum()), int(((p == 0) & (y == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    print(f"\nFenêtres de 15 s  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Précision={prec:.2f}  Rappel={rec:.2f}  "
          f"Taux de faux positifs={fp / (fp + tn) if fp + tn else 0:.3f}")
    print("\nPar attaque :")
    for _, r in attacks.iterrows():
        win = s[(s.index >= r.start) & (s.index <= r.end)]
        hit = win[win.anomaly == 1]
        delay = (hit.index[0] - r.start).total_seconds() if len(hit) else None
        top = hit["top_features"].iloc[0] if len(hit) else "-"
        print(f"  {r.label:<15} détectée={'oui' if len(hit) else 'NON'}  "
              f"délai={'%.0f s' % delay if delay is not None else '-'}  "
              f"couverture={len(hit)}/{len(win)}  1re explication: {top}")


def plot(s, attacks, path, title):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
    a1.plot(s.index, s["pca_ratio"], lw=1.2, color="#3b6fb6", label="PCA — erreur de reconstruction / seuil")
    a1.axhline(1, color="#888", ls="--", lw=0.8)
    a2.plot(s.index, s["envelope_score"].clip(upper=20), lw=1.2, color="#c8553d",
            label="Écart à l'enveloppe saine (max des features)")
    a2.axhline(ENVELOPE_THRESHOLD, color="#888", ls="--", lw=0.8)
    for ax in (a1, a2):
        if attacks is not None:
            for _, r in attacks.iterrows():
                ax.axvspan(r.start, r.end, color="#f2c14e", alpha=0.25)
        an = s[s.anomaly == 1]
        ax.scatter(an.index, [ax.get_ylim()[0]] * len(an), marker="|", color="crimson", s=60)
        ax.legend(loc="upper left", fontsize=8, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
    a1.set_title(title, loc="left", fontsize=11)
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz="Europe/Paris"))
    a2.set_xlabel("Heure (Paris) — traits rouges = fenêtre détectée anormale, zones jaunes = attaques")
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/baseline.joblib")
    ap.add_argument("--prom", required=True)
    ap.add_argument("--loki", required=True)
    ap.add_argument("--attacks")
    ap.add_argument("--out", default="reports/run")
    args = ap.parse_args()

    model = AnomalyModel.load(args.model)
    X = build_features(load_prom_csv(args.prom), load_loki_jsonl(args.loki), columns=model.columns)
    s = model.score(X)
    s.index = pd.to_datetime(s.index, unit="s", utc=True)

    attacks = load_attacks(args.attacks) if args.attacks else None
    if attacks is not None:
        s["truth"] = label_rows(s.index, attacks)

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    s.to_csv(f"{args.out}_scores.csv")
    plot(s, attacks, f"{args.out}.png", f"Détection d'anomalies — {os.path.basename(args.prom)}")
    print(f"{int(s.anomaly.sum())}/{len(s)} fenêtres anormales -> {args.out}_scores.csv, {args.out}.png")
    if attacks is not None:
        evaluate(s, attacks)


if __name__ == "__main__":
    main()
