#!/usr/bin/env python3
"""
Exporte une période depuis Prometheus + Loki au format attendu par train.py / score.py
(mêmes requêtes que le détecteur, donc mêmes colonnes garanties).

  # dernière heure et quart
  python3 export.py --prom-url http://localhost:9090 --loki-url http://localhost:3100 \
                    --since 75m --out data/attack
  # ou une plage précise (heure de Paris acceptée)
  python3 export.py --start 2026-10-21T15:00:00+02:00 --end 2026-10-21T16:15:00+02:00 --out data/attack
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone

import pandas as pd

from resilience_ml.features import STEP
from resilience_ml.sources import loki_range, prom_range


def parse_since(s):
    unit = {"s": 1, "m": 60, "h": 3600}[s[-1]]
    return int(s[:-1]) * unit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prom-url", default="http://localhost:9090")
    ap.add_argument("--loki-url", default="http://localhost:3100")
    ap.add_argument("--since")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--out", required=True, help="dossier de sortie")
    a = ap.parse_args()

    end = int(pd.Timestamp(a.end).timestamp()) if a.end else int(time.time())
    start = int(pd.Timestamp(a.start).timestamp()) if a.start else end - parse_since(a.since or "60m")
    start, end = start // STEP * STEP, end // STEP * STEP
    os.makedirs(a.out, exist_ok=True)

    prom = prom_range(a.prom_url, start, end)
    prom["iso"] = prom["timestamp"].map(lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat())
    prom["metric"] = prom["query"].str.extract(r"([a-zA-Z_:]+_(?:total|seconds|bytes|count|sum|fds)\w*|up)")[0]
    prom["labels"] = prom["labels"].map(lambda d: json.dumps(d, sort_keys=True))
    prom[["timestamp", "iso", "query", "metric", "labels", "value"]].to_csv(f"{a.out}/prometheus.csv", index=False)

    # Loki par tranches de 5 min pour rester sous les limites de requête
    n = 0
    with open(f"{a.out}/loki.jsonl", "w") as fh:
        for t0 in range(start - STEP, end, 300):
            recs, trunc = loki_range(a.loki_url, t0 * 10**9 + 1, min(t0 + 300, end) * 10**9)
            if trunc:
                print(f"! logs tronqués sur la tranche {t0} (flood) — comptes sous-estimés")
            for r in sorted(recs, key=lambda r: r["ts_ns"]):
                r["iso"] = datetime.fromtimestamp(r["ts_ns"] / 1e9, timezone.utc).isoformat()
                fh.write(json.dumps({"ts_ns": r["ts_ns"], "iso": r["iso"], "labels": r["labels"],
                                     "line": r["line"]}) + "\n")
                n += 1
    print(f"{len(prom)} points Prometheus, {n} lignes Loki -> {a.out}/")


if __name__ == "__main__":
    main()
