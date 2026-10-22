"""Lecture de Prometheus et Loki via leurs API HTTP (utilisé par detector.py et export.py)."""
from __future__ import annotations

import pandas as pd
import requests

from .features import LOKI_SELECTORS, PROM_QUERIES, STEP

LOKI_PAGE = 5000          # limite par défaut de Loki (max_entries_limit_per_query)
LOKI_MAX_LINES = 100_000  # garde-fou mémoire par fenêtre (pendant un flood)


def prom_instant(prom_url: str, t: int, timeout=10) -> pd.DataFrame:
    """Évalue toutes les PROM_QUERIES à l'instant t -> format long (timestamp, query, labels, value)."""
    rows = []
    for q in PROM_QUERIES:
        r = requests.get(f"{prom_url}/api/v1/query", params={"query": q, "time": t}, timeout=timeout)
        r.raise_for_status()
        for res in r.json()["data"]["result"]:
            L = {k: v for k, v in res["metric"].items() if k != "__name__"}
            rows.append((t, q, L, float(res["value"][1])))
    return pd.DataFrame(rows, columns=["timestamp", "query", "labels", "value"])


def prom_range(prom_url: str, start: int, end: int, step: int = STEP, timeout=60) -> pd.DataFrame:
    rows = []
    for q in PROM_QUERIES:
        r = requests.get(f"{prom_url}/api/v1/query_range",
                         params={"query": q, "start": start, "end": end, "step": step}, timeout=timeout)
        r.raise_for_status()
        for res in r.json()["data"]["result"]:
            L = {k: v for k, v in res["metric"].items() if k != "__name__"}
            for ts, v in res["values"]:
                rows.append((int(float(ts)), q, L, float(v)))
    return pd.DataFrame(rows, columns=["timestamp", "query", "labels", "value"])


def loki_range(loki_url: str, start_ns: int, end_ns: int, timeout=30,
               max_lines: int = LOKI_MAX_LINES) -> tuple[list[dict], bool]:
    """Toutes les lignes de LOKI_SELECTORS dans [start_ns, end_ns], paginées.
    Renvoie (records, tronqué?)."""
    out, truncated = [], False
    for sel in LOKI_SELECTORS:
        cur = start_ns
        while True:
            r = requests.get(f"{loki_url}/loki/api/v1/query_range", timeout=timeout, params={
                "query": sel, "start": cur, "end": end_ns, "limit": LOKI_PAGE, "direction": "forward"})
            r.raise_for_status()
            batch = []
            for stream in r.json()["data"]["result"]:
                for ts, line in stream["values"]:
                    batch.append({"ts_ns": int(ts), "labels": stream["stream"], "line": line})
            out.extend(batch)
            if len(batch) < LOKI_PAGE:
                break
            if len(out) >= max_lines:
                truncated = True
                break
            cur = max(b["ts_ns"] for b in batch) + 1
    return out, truncated
