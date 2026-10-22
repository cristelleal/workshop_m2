#!/usr/bin/env python3
"""
Entraîne le modèle sur un export SAIN.

  python3 train.py --prom data/baseline/prometheus.csv --loki data/baseline/loki.jsonl \
                   --out models/baseline.joblib
"""
import argparse
import json
import os

from resilience_ml.features import CLIENT_FEATURES, build_features, load_loki_jsonl, load_prom_csv
from resilience_ml.model import AnomalyModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prom", required=True)
    ap.add_argument("--loki", required=True)
    ap.add_argument("--out", default="models/baseline.joblib")
    ap.add_argument("--features-out", default="data/features_baseline.csv")
    ap.add_argument("--min-rps", type=float, default=1.0,
                    help="Exclut les fenêtres où le générateur de trafic légitime ne tournait pas "
                         "(http_rps < seuil). Ainsi un effondrement du trafic pendant une attaque "
                         "est vu comme anormal. 0 = tout garder.")
    ap.add_argument("--include-client-features", action="store_true",
                    help="Garde les features IP/User-Agent du WAF (seulement si la baseline contient "
                         "du trafic légitime venant de plusieurs clients)")
    ap.add_argument("--exclude-regex", default=r"(_mem_bytes|_rss_bytes|_mem_avail_bytes)$|^log_sys_errors$",
                    help="Features exclues : jauges mémoire (dérivent avec le temps de fonctionnement des "
                         "conteneurs) et erreurs système génériques (bruit périodique de la VM), sans lien "
                         "avec une attaque. '' = ne rien exclure.")
    args = ap.parse_args()

    X = build_features(load_prom_csv(args.prom), load_loki_jsonl(args.loki),
                       exclude=None if args.include_client_features else CLIENT_FEATURES)
    os.makedirs(os.path.dirname(args.features_out) or ".", exist_ok=True)
    if args.exclude_regex:
        import re
        drop = [c for c in X.columns if re.search(args.exclude_regex, c)]
        X = X.drop(columns=drop)
        print(f"Features exclues ({len(drop)}) : {', '.join(drop)}")
    X.to_csv(args.features_out)
    if args.min_rps > 0:
        n0 = len(X)
        X = X[X["http_rps"] >= args.min_rps]
        print(f"Fenêtres retenues (http_rps >= {args.min_rps}) : {len(X)}/{n0}")

    model = AnomalyModel().fit(X)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    model.save(args.out)

    s = model.score(X)
    print(json.dumps(model.train_stats, indent=2))
    print(f"Points sains signalés anormaux : {int(s.anomaly.sum())}/{len(s)} "
          f"({100 * s.anomaly.mean():.1f} %)")
    if s.anomaly.any():
        print(s[s.anomaly == 1][["envelope_score", "top_features"]].to_string())
    print(f"Modèle -> {args.out}   Features -> {args.features_out}")


if __name__ == "__main__":
    main()
