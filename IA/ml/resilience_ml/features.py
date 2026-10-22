"""
Extraction de features pour la détection d'anomalies RESILIENCE-ALPHA.

Une ligne = une fenêtre de STEP secondes (15 s par défaut, le pas de l'export Prometheus).
Le MÊME code est utilisé hors ligne (CSV/JSONL exportés) et en live (detector.py),
pour garantir que le modèle voit exactement les mêmes colonnes dans les deux cas.

Format d'entrée Prometheus (long) : timestamp, query, labels (dict), value
Format d'entrée Loki             : ts_ns, labels (dict), line
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict

import numpy as np
import pandas as pd

STEP = 15  # secondes

# VM surveillées. La VM "attacker" (Kali) est volontairement EXCLUE des features :
# en production on ne surveille pas la machine de l'attaquant, l'inclure serait de la fuite de label.
MONITORED_VMS = ["host", "soc"]

# Conteneurs applicatifs du PC Hôte qui encaissent un DDoS
KEY_CONTAINERS = ["app-api", "security-waf", "app-db", "app-frontend"]

# Requêtes PromQL exactes (identiques à celles de l'export, + 5xx implicite via le label status)
PROM_QUERIES = [
    "rate(http_requests_total[1m])",
    "rate(http_request_duration_seconds_sum[1m])",
    "rate(http_request_duration_seconds_count[1m])",
    "rate(http_request_size_bytes_sum[1m])",
    "rate(http_request_size_bytes_count[1m])",
    "rate(http_response_size_bytes_sum[1m])",
    "rate(http_response_size_bytes_count[1m])",
    "histogram_quantile(0.95, sum by (le, job) (rate(http_request_duration_seconds_bucket[1m])))",
    "histogram_quantile(0.95, sum by (le) (rate(payment_processing_seconds_bucket[1m])))",
    "rate(payment_processing_seconds_sum[1m])",
    "rate(payment_processing_seconds_count[1m])",
    "rate(donations_total[1m])",
    "rate(process_cpu_seconds_total[1m])",
    "process_open_fds",
    "process_resident_memory_bytes",
    "rate(container_cpu_usage_seconds_total[1m])",
    "container_memory_working_set_bytes",
    "rate(container_network_receive_bytes_total[1m])",
    "rate(container_network_transmit_bytes_total[1m])",
    "rate(node_cpu_seconds_total[1m])",
    "node_load1",
    "node_memory_MemAvailable_bytes",
    "rate(node_network_receive_bytes_total[1m])",
    "rate(node_network_transmit_bytes_total[1m])",
    "node_netstat_Tcp_CurrEstab",
    "node_sockstat_TCP_inuse",
    # Couche TCP (SYN flood, saturation du backlog) — nécessite un node-exporter dans le netns de l'hôte
    "rate(node_netstat_Tcp_PassiveOpens[1m])",
    "rate(node_netstat_Tcp_InSegs[1m])",
    "rate(node_netstat_Tcp_OutRsts[1m])",
    "rate(node_netstat_TcpExt_ListenDrops[1m])",
    "rate(node_netstat_TcpExt_SyncookiesSent[1m])",
    "node_sockstat_TCP_tw",
    "up",
]

# Features exclues par défaut à l'entraînement : la baseline actuelle n'a qu'UN client (curl depuis
# host-resilience, IP 172.18.0.1). Avec elles, une attaque serait détectée parce qu'"une nouvelle IP
# apparaît" (et un simple navigateur déclencherait une alerte). À réactiver (--include-client-features)
# quand la baseline contient du trafic légitime venant de plusieurs machines.
CLIENT_FEATURES = ["log_waf_uniq_clients", "log_waf_top_client_share", "log_waf_uniq_ua"]

# Sélecteurs LogQL pour le live (mêmes flux que l'export)
LOKI_SELECTORS = [
    '{service_name=~"app-api|security-waf|app-frontend|app-db"}',
    '{job="varlogs"}',
]


# --------------------------------------------------------------------------- Prometheus
def load_prom_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["labels"] = df["labels"].map(json.loads)
    return df[["timestamp", "query", "labels", "value"]]


def _sel(df, query, where=None, by=None, agg="sum"):
    """Filtre une requête, puis agrège par timestamp (et éventuellement par clé de label)."""
    d = df[df["query"] == query]
    if where is not None and len(d):
        d = d[d["labels"].map(where)]
    if not len(d):
        return None
    if by is None:
        return d.groupby("timestamp")["value"].agg(agg)
    key = d["labels"].map(by)
    return d.assign(_k=key).groupby(["timestamp", "_k"])["value"].agg(agg).unstack("_k")


def _job_app(L):
    return L.get("job") == "resilience-app"


def prom_features(df: pd.DataFrame) -> pd.DataFrame:
    f: dict[str, pd.Series] = {}
    expected: list[str] = []
    present = set(df["query"].unique())
    uncollected: set[str] = set()
    touched: list[str] = []

    def sel(q, *a, **k):
        touched.append(q)
        return _sel(df, q, *a, **k)

    def put(name, s, missing=None):
        # Schéma FIXE : une série absente (ex. aucune 5xx pendant la baseline) devient 0,
        # sinon la colonne n'existerait pas à l'entraînement et ne pourrait jamais alerter.
        # En revanche, si la REQUÊTE elle-même n'a pas été collectée, la feature est marquée
        # "non collectée" et retirée à l'entraînement (sinon elle exploserait en live).
        expected.append(name)
        if missing is None:
            missing = any(q not in present for q in touched)
        if missing:
            uncollected.add(name)
        touched.clear()
        if s is not None:
            f[name] = s

    # --- Trafic HTTP de l'API (FastAPI, instrumentation prometheus-fastapi-instrumentator)
    q = "rate(http_requests_total[1m])"
    put("http_rps", sel(q, _job_app))
    for h, name in [("/donations", "donations"), ("/auth/login", "login"),
                    ("/auth/register", "register"), ("none", "unmatched")]:
        put(f"http_rps_{name}", sel(q, lambda L, h=h: _job_app(L) and L.get("handler") == h))
    for cls in ["2", "4", "5"]:
        put(f"http_rps_{cls}xx",
            sel(q, lambda L, c=cls: _job_app(L) and str(L.get("status", "")).startswith(c)))

    def ratio(num_q, den_q):
        n, d = sel(num_q, _job_app), sel(den_q, _job_app)
        if n is None or d is None:
            return None
        return (n / d.replace(0, np.nan)).fillna(0.0)

    put("http_latency_avg_s", ratio("rate(http_request_duration_seconds_sum[1m])",
                                    "rate(http_request_duration_seconds_count[1m])"))
    put("http_req_size_avg_b", ratio("rate(http_request_size_bytes_sum[1m])",
                                     "rate(http_request_size_bytes_count[1m])"))
    put("http_resp_size_avg_b", ratio("rate(http_response_size_bytes_sum[1m])",
                                      "rate(http_response_size_bytes_count[1m])"))
    put("http_latency_p95_s", sel("histogram_quantile(0.95, sum by (le, job) "
                                       "(rate(http_request_duration_seconds_bucket[1m])))",
                                   _job_app, agg="max"))
    put("payment_latency_p95_s", sel("histogram_quantile(0.95, sum by (le) "
                                          "(rate(payment_processing_seconds_bucket[1m])))", agg="max"))
    put("payment_latency_avg_s", ratio("rate(payment_processing_seconds_sum[1m])",
                                       "rate(payment_processing_seconds_count[1m])"))
    for st in ["succeeded", "failed"]:
        put(f"donations_{st}_rps",
            sel("rate(donations_total[1m])", lambda L, s=st: L.get("status") == s))

    # --- Process de l'API
    api = lambda L: _job_app(L) and L.get("instance", "").startswith("api:")
    put("api_process_cpu", sel("rate(process_cpu_seconds_total[1m])", api))
    put("api_open_fds", sel("process_open_fds", api))
    put("api_rss_bytes", sel("process_resident_memory_bytes", api))

    # --- Conteneurs clés (cAdvisor du PC Hôte)
    on_host = lambda L: L.get("vm") == "host" and L.get("name") in KEY_CONTAINERS
    for q, suffix in [("rate(container_cpu_usage_seconds_total[1m])", "cpu"),
                      ("container_memory_working_set_bytes", "mem_bytes"),
                      ("rate(container_network_receive_bytes_total[1m])", "net_rx_bps"),
                      ("rate(container_network_transmit_bytes_total[1m])", "net_tx_bps")]:
        wide = _sel(df, q, on_host, by=lambda L: L["name"])
        for c in KEY_CONTAINERS:
            put(f"c_{c.replace('-', '_')}_{suffix}",
                wide[c] if wide is not None and c in wide else None, missing=q not in present)

    # --- Nœuds (VM host et SOC)
    for vm in MONITORED_VMS:
        isvm = lambda L, vm=vm: L.get("vm") == vm
        idle = sel("rate(node_cpu_seconds_total[1m])",
                    lambda L, vm=vm: isvm(L) and L.get("mode") == "idle", agg="mean")
        put(f"node_{vm}_cpu_busy", None if idle is None else (1 - idle).clip(lower=0))
        put(f"node_{vm}_load1", sel("node_load1", isvm))
        put(f"node_{vm}_mem_avail_bytes", sel("node_memory_MemAvailable_bytes", isvm))
        not_lo = lambda L, vm=vm: isvm(L) and L.get("device") != "lo"
        put(f"node_{vm}_net_rx_bps", sel("rate(node_network_receive_bytes_total[1m])", not_lo))
        put(f"node_{vm}_net_tx_bps", sel("rate(node_network_transmit_bytes_total[1m])", not_lo))
        put(f"node_{vm}_tcp_estab", sel("node_netstat_Tcp_CurrEstab", isvm))
        put(f"node_{vm}_tcp_inuse", sel("node_sockstat_TCP_inuse", isvm))
        for q, name in [("rate(node_netstat_Tcp_PassiveOpens[1m])", "tcp_passive_opens_ps"),
                        ("rate(node_netstat_Tcp_InSegs[1m])", "tcp_in_segs_ps"),
                        ("rate(node_netstat_Tcp_OutRsts[1m])", "tcp_out_rsts_ps"),
                        ("rate(node_netstat_TcpExt_ListenDrops[1m])", "tcp_listen_drops_ps"),
                        ("rate(node_netstat_TcpExt_SyncookiesSent[1m])", "tcp_syncookies_ps"),
                        ("node_sockstat_TCP_tw", "tcp_timewait")]:
            put(f"node_{vm}_{name}", sel(q, isvm))

    # --- Disponibilité : nombre de cibles DOWN (hors auth:8000, absente du déploiement actuel)
    put("targets_down", sel("up", lambda L: L.get("instance") != "auth:8000",
                             agg=lambda v: float((v < 1).sum())))

    idx = sorted(df["timestamp"].unique())
    out = pd.DataFrame(f).reindex(index=idx, columns=expected)
    out.index.name = "timestamp"
    return out, sorted(uncollected)


# --------------------------------------------------------------------------- Loki
def load_loki_jsonl(path: str) -> list[dict]:
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


# Format nginx "combined" + X-Forwarded-For (WAF et frontend)
_NGINX = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "(\S+) (\S+)[^"]*" (\d{3}) (\d+) "[^"]*" "([^"]*)"(?: "([^"]*)")?')


def _bucket(ts_ns: int) -> int:
    # Prometheus évalue rate(...) en t sur ]t-1m, t] : on range un log dans le pas qui le "clôt"
    return int(math.ceil(ts_ns / 1e9 / STEP) * STEP)


def loki_features(records: list[dict]) -> pd.DataFrame:
    rows = defaultdict(lambda: defaultdict(float))
    ips = defaultdict(lambda: defaultdict(int))
    uas = defaultdict(set)
    paths = defaultdict(set)

    for r in records:
        t = _bucket(r["ts_ns"])
        L, line = r["labels"], r["line"]
        svc = L.get("service_name")
        row = rows[t]
        if svc in ("security-waf", "app-frontend"):
            pre = "log_waf" if svc == "security-waf" else "log_front"
            m = _NGINX.match(line)
            row[f"{pre}_lines"] += 1
            if not m:
                continue
            ip, _method, path, status, size, ua, xff = m.groups()
            row[f"{pre}_{status[0]}xx"] += 1
            row[f"{pre}_bytes"] += int(size)
            if pre == "log_waf":
                client = xff if xff and xff != "-" else ip
                ips[t][client] += 1
                uas[t].add(ua)
                paths[t].add(path.split("?")[0])
        elif svc == "app-api":
            row["log_api_lines"] += 1
            try:
                d = json.loads(line)
            except ValueError:
                continue
            lvl, msg = d.get("level", ""), str(d.get("message", ""))
            if lvl in ("WARNING", "ERROR", "CRITICAL"):
                row["log_api_warn_err"] += 1
            if "fail" in msg or "denied" in msg or "invalid" in msg:
                row["log_api_fail_events"] += 1
            if msg.startswith("login_"):
                row["log_api_login_events"] += 1
        elif svc == "app-db":
            row["log_db_lines"] += 1
            if re.search(r"\b(ERROR|FATAL|PANIC)\b", line):
                row["log_db_errors"] += 1
            if "too many" in line or "remaining connection slots" in line:
                row["log_db_conn_saturation"] += 1
        elif L.get("job") == "varlogs":
            fn = L.get("filename", "")
            if fn.endswith("auth.log"):
                row["log_sys_auth_lines"] += 1
            elif fn.endswith("kern.log"):
                row["log_sys_kern_lines"] += 1
            else:
                row["log_sys_syslog_lines"] += 1
            if L.get("detected_level") == "error":
                row["log_sys_errors"] += 1

    for t in rows:
        c = ips[t]
        n = sum(c.values())
        rows[t]["log_waf_uniq_clients"] = len(c)
        rows[t]["log_waf_top_client_share"] = (max(c.values()) / n) if n else 0.0
        rows[t]["log_waf_uniq_ua"] = len(uas[t])
        rows[t]["log_waf_uniq_paths"] = len(paths[t])

    out = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    out.index.name = "timestamp"
    return out


LOG_COLUMNS = [
    "log_waf_lines", "log_waf_2xx", "log_waf_3xx", "log_waf_4xx", "log_waf_5xx", "log_waf_bytes",
    "log_waf_uniq_clients", "log_waf_top_client_share", "log_waf_uniq_ua", "log_waf_uniq_paths",
    "log_front_lines", "log_front_4xx", "log_front_5xx",
    "log_api_lines", "log_api_warn_err", "log_api_fail_events", "log_api_login_events",
    "log_db_lines", "log_db_errors", "log_db_conn_saturation",
    "log_sys_syslog_lines", "log_sys_auth_lines", "log_sys_kern_lines", "log_sys_errors",
]


# --------------------------------------------------------------------------- Assemblage
def build_features(prom: pd.DataFrame, loki: list[dict], columns: list[str] | None = None,
                   exclude: list[str] | None = None) -> pd.DataFrame:
    """Joint métriques et logs sur la grille Prometheus.
    - columns=None (entraînement) : retire les features non collectées et `exclude`.
    - columns=[...] (scoring/live) : force le jeu de colonnes du modèle, absente -> 0."""
    pf, uncollected = prom_features(prom)
    lf = loki_features(loki) if loki else pd.DataFrame(index=pf.index)
    lf = lf.reindex(columns=LOG_COLUMNS)
    X = pf.join(lf, how="left")
    # Absence de logs / de trafic = 0 (ex. p95 = NaN quand aucune requête)
    X = X.fillna(0.0)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0.0)
    else:
        drop = [c for c in uncollected + list(exclude or []) if c in X.columns]
        if uncollected:
            print(f"Features non collectées dans cet export (ignorées) : {len(uncollected)} "
                  f"-> {', '.join(uncollected[:6])}{'…' if len(uncollected) > 6 else ''}")
        X = X.drop(columns=drop)
    X.index = X.index.astype(int)
    return X.sort_index()
