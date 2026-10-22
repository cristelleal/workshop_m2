#!/usr/bin/env python3
"""
Détecteur temps réel : toutes les 15 s, interroge Prometheus + Loki, calcule les mêmes features
qu'à l'entraînement, score la fenêtre et expose le résultat en métriques Prometheus sur :9105.
Prometheus le scrape -> Grafana l'affiche et l'alerte -> la boucle est fermée sur la stack.

  python3 detector.py --prom-url http://prometheus:9090 --loki-url http://loki:3100 \
                      --model models/baseline.joblib

Une ligne JSON par fenêtre est aussi écrite sur stdout (récupérée par Promtail -> Loki -> SIEM).
"""
import argparse
import json
import logging
import sys
import time
import numpy as np
import requests

from prometheus_client import Counter, Gauge, start_http_server

from resilience_ml.features import LOG_COLUMNS, STEP, build_features
from resilience_ml.features import STEP, build_features
from resilience_ml.model import AnomalyModel
from resilience_ml.sources import loki_range, prom_instant

PFX = "resilience_ml_"
G_PCA = Gauge(PFX + "pca_ratio", "Erreur de reconstruction PCA / seuil (>1 = anormal)")
G_ENV = Gauge(PFX + "envelope_score", "Écart max à l'enveloppe saine (>1 = anormal)")
G_ANOM = Gauge(PFX + "anomaly", "1 si la dernière fenêtre est anormale")
G_CONSEC = Gauge(PFX + "anomaly_consecutive", "Nombre de fenêtres anormales consécutives")
G_DEV = Gauge(PFX + "feature_deviation", "Écart à l'enveloppe saine par feature", ["feature"])
G_WIN = Gauge(PFX + "window_timestamp_seconds", "Fin de la dernière fenêtre évaluée")
G_TRUNC = Gauge(PFX + "loki_truncated", "1 si les logs de la fenêtre ont été tronqués (flood)")
C_ERR = Counter(PFX + "errors_total", "Erreurs de collecte/scoring")

log = logging.getLogger("detector")


def evaluate(model, prom_url, loki_url, t):
    prom = prom_instant(prom_url, t)
    if prom.empty:
        raise RuntimeError(f"Prometheus n'a renvoyé aucune série à t={t} (URL, scrape ou horloge ?)")
    logs, truncated = loki_range(loki_url, (t - STEP) * 10**9 + 1, t * 10**9)
    X = build_features(prom, logs, columns=model.columns)
    X = X.loc[[t]]
    return model.score(X).iloc[0], model.deviations(X).iloc[0], truncated, len(logs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prom-url", default="http://prometheus:9090")
    ap.add_argument("--loki-url", default="http://loki:3100")
    ap.add_argument("--model", default="models/baseline.joblib")
    ap.add_argument("--port", type=int, default=9105)
    ap.add_argument("--lag", type=int, default=30,
                    help="Retard (s) appliqué à 'maintenant' pour laisser le temps aux scrapes et à "
                         "l'ingestion Loki d'arriver")
    ap.add_argument("--replay-offset", type=int, default=0,
                    help="Décale l'horloge de N secondes dans le passé : rejoue en temps réel une "
                         "période déjà enregistrée (démo d'une attaque passée devant le jury)")
    ap.add_argument("--once", type=int, metavar="UNIX_TS",
                    help="Évalue une seule fenêtre (fin = UNIX_TS) et quitte (debug / rejeu)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")

    model = AnomalyModel.load(args.model)
    log.info("Modèle chargé : %s", json.dumps(model.train_stats))

    if args.once:
        s, dev, trunc, n = evaluate(model, args.prom_url, args.loki_url, args.once)
        print(json.dumps({"window_end": args.once, **{k: (v.item() if hasattr(v, "item") else v)
                                                       for k, v in s.items()}, "log_lines": n}))
        return

    start_http_server(args.port)
    log.info("Métriques exposées sur :%d/metrics", args.port)
    consec, last_t = 0, None
    while True:
        t = int((time.time() - args.lag - args.replay_offset) // STEP * STEP)
        if t != last_t:
            try:
                s, dev, trunc, n = evaluate(model, args.prom_url, args.loki_url, t)
                consec = consec + 1 if s.anomaly else 0
                G_PCA.set(s.pca_ratio); G_ENV.set(s.envelope_score); G_ANOM.set(int(s.anomaly))
                G_CONSEC.set(consec); G_WIN.set(t); G_TRUNC.set(int(trunc))
                for f, v in dev.items():
                    G_DEV.labels(feature=f).set(float(v))
                print(json.dumps({"logger": "resilience_ml", "window_end": t,
                                  "anomaly": int(s.anomaly), "consecutive": consec,
                                  "pca_ratio": round(float(s.pca_ratio), 3),
                                  "envelope_score": round(float(s.envelope_score), 3),
                                  "top_features": s.top_features, "log_lines": n,
                                  "loki_truncated": trunc}), flush=True)
                last_t = t
            except Exception as e:  # la boucle ne doit jamais mourir
                C_ERR.inc()
                log.exception("Fenêtre %s : %s", t, e)
        time.sleep(1)


if __name__ == "__main__":
    main()
