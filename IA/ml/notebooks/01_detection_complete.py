import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="RESILIENCE-ALPHA — détection d'anomalies")

with app.setup:
    import sys
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import RobustScaler

    ROOT = Path(mo.notebook_dir() or Path.cwd()).resolve().parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # Bibliothèque partagée avec le détecteur temps réel : features et modèle IDENTIQUES en live
    from resilience_ml.features import (
        CLIENT_FEATURES,
        build_features,
        load_loki_jsonl,
        load_prom_csv,
    )
    from resilience_ml.model import AnomalyModel
    from resilience_ml.model import _tx as log1p_signed

    TZ = "Europe/Paris"

    def to_local(index):
        """Timestamps unix -> heure de Paris (naïve, pour l'affichage Altair)."""
        return pd.to_datetime(index, unit="s", utc=True).tz_convert(TZ).tz_localize(None)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # RESILIENCE-ALPHA — Détection d'anomalies par apprentissage automatique

    **Objectif** : apprendre le comportement **sain** de la plateforme de dons à partir de ses propres
    métriques (Prometheus) et journaux (Loki), puis signaler tout écart (DDoS, scan, panne…) en temps réel.

    | Étape | Contenu |
    |:--|:--|
    | 1 | Chargement des exports Prometheus / Loki |
    | 2 | Exploration et défauts de collecte |
    | 3 | Construction des features (fenêtres de 15 s) |
    | 4 | Entraînement : PCA + enveloppe, paramètres réglables |
    | 5 | Validation hors échantillon (faux positifs) |
    | 6 | Pourquoi PCA plutôt qu'Isolation Forest |
    | 7 | Simulateur d'attaques |
    | 8 | Évaluation sur le run d'attaque réel |
    | 9 | Export du modèle pour le détecteur live |

    > Mode présentation (code masqué) : `marimo run notebooks/01_detection_complete.py`
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 1. Chargement des données
    """)
    return


@app.cell
def _():
    prom_path = mo.ui.text(value=str(ROOT / "data/baseline/prometheus.csv"),
                           label="Export Prometheus (baseline saine)", full_width=True)
    loki_path = mo.ui.text(value=str(ROOT / "data/baseline/loki.jsonl"),
                           label="Export Loki (baseline saine)", full_width=True)
    mo.vstack([prom_path, loki_path])
    return loki_path, prom_path


@app.cell
def _(loki_path, prom_path):
    _missing = [p for p in (prom_path.value, loki_path.value) if not Path(p).exists()]
    mo.stop(bool(_missing), mo.callout(mo.md(
        "Fichier introuvable : " + ", ".join(f"`{p}`" for p in _missing)
        + "\n\nCopie tes exports dans `data/baseline/` ou corrige les chemins."), kind="danger"))
    with mo.status.spinner("Lecture des exports…"):
        prom = load_prom_csv(prom_path.value)
        loki = load_loki_jsonl(loki_path.value)
    return loki, prom


@app.cell
def _(loki, prom):
    _vms = sorted({L.get("vm") for L in prom["labels"] if L.get("vm")})
    _dur = (prom.timestamp.max() - prom.timestamp.min()) / 60
    mo.hstack([
        mo.stat(f"{len(prom):,}".replace(",", " "), label="Points Prometheus"),
        mo.stat(prom["query"].nunique(), label="Requêtes PromQL"),
        mo.stat(f"{len(loki):,}".replace(",", " "), label="Lignes de logs"),
        mo.stat(f"{_dur:.0f} min", label="Durée", caption=f"pas de {int(np.median(np.diff(sorted(prom.timestamp.unique()))))} s"),
        mo.stat(", ".join(_vms), label="VM"),
    ], widths="equal")
    return


@app.cell
def _(loki, prom):
    _q = prom.groupby("query").agg(points=("value", "size"), valeurs_manquantes=("value", lambda v: int(v.isna().sum()))).sort_values("points", ascending=False).reset_index()
    _streams = pd.DataFrame([{"service": r["labels"].get("service_name"), "fichier/conteneur": r["labels"].get("filename") or r["labels"].get("container"), "niveau": r["labels"].get("detected_level")} for r in loki]).value_counts().rename("lignes").reset_index()
    mo.ui.tabs({"Requêtes Prometheus": mo.ui.table(_q, page_size=12, selection=None),
                "Flux de logs Loki": mo.ui.table(_streams, selection=None)})
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 2. Exploration

    On calcule d'abord **toutes** les features (une ligne par fenêtre de 15 s) pour regarder les données.
    Les métriques Prometheus sont des `rate(...[1m])` évaluées toutes les 15 s ; les logs sont comptés dans la
    fenêtre de 15 s qui se termine au même instant.
    """)
    return


@app.cell
def _(loki, prom):
    with mo.status.spinner("Calcul des features…"):
        X_all = build_features(prom, loki)  # toutes les features collectées (y compris IP/UA client)
    return (X_all,)


@app.cell
def _(X_all):
    feature_pick = mo.ui.multiselect(
        options=list(X_all.columns),
        value=[c for c in ["http_rps", "http_latency_p95_s", "c_app_api_cpu", "log_waf_lines"] if c in X_all],
        label="Features à afficher", max_selections=6)
    feature_pick
    return (feature_pick,)


@app.cell
def _(X_all, feature_pick):
    mo.stop(not feature_pick.value, mo.md("_Choisis au moins une feature._"))
    _d = X_all[feature_pick.value].assign(heure=to_local(X_all.index)).melt("heure", var_name="feature", value_name="valeur")
    alt.Chart(_d).mark_line(strokeWidth=1.4).encode(
        x=alt.X("heure:T", title="Heure (Paris)", axis=alt.Axis(format="%H:%M")),
        y=alt.Y("valeur:Q", title=None),
        color=alt.Color("feature:N", legend=None),
        tooltip=["heure:T", "feature:N", alt.Tooltip("valeur:Q", format=".4g")],
    ).properties(width=680, height=90).facet(
        row=alt.Row("feature:N", title=None, header=alt.Header(labelAngle=0, labelAlign="left"))
    ).resolve_scale(y="independent")
    return


@app.cell(hide_code=True)
def _(X_all, prom):
    _host_rx = X_all["node_host_net_rx_bps"].mean()
    _api_rx = X_all["c_app_api_net_rx_bps"].mean()
    _estab = ", ".join(f"{v:g}" for v in sorted(X_all["node_host_tcp_estab"].unique()))
    _clients = int(X_all["log_waf_uniq_clients"].max())
    _up = prom[prom["query"] == "up"]
    _up_max = _up.groupby(_up["labels"].map(lambda L: L.get("instance")))["value"].max()
    _down = sorted(_up_max[_up_max < 1].index)
    _active = X_all[X_all.http_rps >= 1]
    mo.vstack([
        mo.md("### Défauts de collecte repérés dans les données"),
        mo.callout(mo.md(
            f"**node-exporter ne voit pas la machine** : trafic réseau du nœud host = **{_host_rx:.0f} o/s** "
            f"alors que le seul conteneur API reçoit **{_api_rx/1000:.1f} ko/s** ; connexions TCP établies = {_estab}. "
            "node-exporter tourne dans son propre namespace réseau → un SYN flood serait invisible côté nœud. "
            "Correctif : `network_mode: host`, `pid: host` (voir README)."), kind="danger"),
        mo.callout(mo.md(
            f"**Un seul client légitime** : au plus {_clients} IP distincte vue par le WAF par fenêtre (`curl` depuis "
            "host-resilience). Les features IP/User-Agent ne sont donc **pas utilisables** : une attaque serait détectée "
            "parce qu'« une nouvelle IP apparaît », pas parce qu'elle ressemble à une attaque."), kind="warn"),
        mo.callout(mo.md(
            f"**Charge plate** : en régime établi, `http_rps` = {_active.http_rps.median():.2f} ± {_active.http_rps.std():.2f} req/s. "
            "Le modèle considérera toute variation notable comme anormale ; une baseline avec paliers/rafales légitimes serait plus réaliste."), kind="warn"),
        mo.callout(mo.md(f"**Cibles DOWN pendant toute la baseline** : {', '.join(f'`{d}`' for d in _down) or 'aucune'} (exclues des features)."), kind="info"),
    ])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 3. Paramètres d'entraînement

    - **Seuil de trafic légitime** : on n'apprend que sur les fenêtres où le générateur tournait. Sinon
      « zéro trafic » devient normal et un effondrement du service pendant un DDoS passe inaperçu.
    - **PCA** : apprend comment les métriques varient *ensemble* ; une fenêtre qui casse ces corrélations
      se reconstruit mal (erreur SPE). Le seuil est un quantile des erreurs observées sur le sain.
    - **Enveloppe** : pour chaque feature, distance hors de la plage saine `[min, max]`, divisée par sa dispersion
      saine (q95 − q05, avec un plancher). Couvre les features toujours à 0 en sain (5xx, 4xx).
    """)
    return


@app.cell
def _():
    min_rps = mo.ui.slider(0, 7, step=0.5, value=1.0, label="Trafic légitime minimal (req/s)", show_value=True)
    include_clients = mo.ui.checkbox(value=False, label="Inclure les features IP / User-Agent du WAF")
    pca_var = mo.ui.slider(0.80, 0.99, step=0.01, value=0.95, label="PCA : variance conservée", show_value=True)
    pca_q = mo.ui.slider(0.950, 1.000, step=0.001, value=0.995, label="PCA : quantile du seuil", show_value=True)
    env_thr = mo.ui.slider(0.5, 3.0, step=0.1, value=1.0, label="Enveloppe : seuil d'alerte", show_value=True)
    env_scale = mo.ui.slider(0.05, 1.0, step=0.05, value=0.25, label="Enveloppe : dispersion minimale (log1p)", show_value=True)
    mo.hstack([mo.vstack([min_rps, include_clients]), mo.vstack([pca_var, pca_q]), mo.vstack([env_thr, env_scale])], widths="equal")
    return env_scale, env_thr, include_clients, min_rps, pca_q, pca_var


@app.cell
def _(X_all, env_scale, env_thr, include_clients, min_rps, pca_q, pca_var):
    params = dict(pca_variance=pca_var.value, pca_quantile=pca_q.value,
                  envelope_threshold=env_thr.value, envelope_min_scale=env_scale.value)
    _drop = [] if include_clients.value else [c for c in CLIENT_FEATURES if c in X_all]
    X_feat = X_all.drop(columns=_drop)
    X_train = X_feat[X_feat["http_rps"] >= min_rps.value]
    model = AnomalyModel(**params).fit(X_train)
    _s = model.score(X_train)
    mo.hstack([
        mo.stat(f"{len(X_train)}/{len(X_feat)}", label="Fenêtres d'entraînement"),
        mo.stat(model.train_stats["n_features"], label="Features", caption=f"{model.train_stats['n_features_varying']} varient en sain"),
        mo.stat(model.train_stats["pca_components"], label="Composantes PCA"),
        mo.stat(f"{_s.anomaly.mean():.1%}", label="Alertes sur l'entraînement", caption="optimiste : voir §5"),
    ], widths="equal")
    return X_feat, X_train, model, params


@app.cell(hide_code=True)
def _(model):
    _active_cols = np.array(model.columns)[model.active]
    _ev = pd.DataFrame({"composante": [f"PC{i+1}" for i in range(model.pca.n_components_)],
                        "variance expliquée": model.pca.explained_variance_ratio_})
    _load = pd.DataFrame(model.pca.components_.T, index=_active_cols,
                         columns=_ev["composante"]).abs()
    _top = {_c: _load[_c].sort_values(ascending=False).head(6).rename("poids").rename_axis("feature").reset_index()
            for _c in _ev["composante"]}
    _c1 = alt.Chart(_ev).mark_bar(color="#3b6fb6").encode(
        x=alt.X("composante:N", title=None), y=alt.Y("variance expliquée:Q", axis=alt.Axis(format="%")),
        tooltip=["composante", alt.Tooltip("variance expliquée:Q", format=".1%")]).properties(width=160, height=200)
    _c2 = alt.vconcat(*[alt.Chart(_d, title=f"{_c} : {_ev.set_index('composante').loc[_c].iloc[0]:.0%} de la variance").mark_bar(color="#7a9cc6").encode(
        y=alt.Y("feature:N", sort="-x", title=None), x=alt.X("poids:Q", title="|poids|", scale=alt.Scale(domain=[0, 1])),
        tooltip=["feature", alt.Tooltip("poids:Q", format=".2f")]).properties(width=280, height=110) for _c, _d in _top.items()])
    mo.vstack([mo.md("**Ce que la PCA a appris** : chaque composante est un groupe de métriques qui bougent ensemble en sain."),
               mo.hstack([_c1, _c2], justify="start", gap=2)])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 4. Scores sur toute la baseline

    En rouge, les fenêtres signalées. Les zones où le générateur était arrêté ou intermittent ressortent :
    c'est voulu (elles ne font pas partie de l'apprentissage).
    """)
    return


@app.cell
def _(X_feat, model):
    scores_all = model.score(X_feat)
    _d = scores_all.assign(heure=to_local(scores_all.index))
    _base = alt.Chart(_d).encode(x=alt.X("heure:T", title="Heure (Paris)", axis=alt.Axis(format="%H:%M")))
    def _panel(col, title, thr, color):
        _line = _base.mark_line(color=color, strokeWidth=1.3).encode(
            y=alt.Y(f"{col}:Q", title=title, scale=alt.Scale(type="symlog")),
            tooltip=["heure:T", alt.Tooltip(f"{col}:Q", format=".2f"), "top_features:N"])
        _rule = alt.Chart(pd.DataFrame({"y": [thr]})).mark_rule(strokeDash=[4, 3], color="#888").encode(y="y:Q")
        _ticks = _base.transform_filter("datum.anomaly == 1").mark_tick(color="crimson", thickness=2).encode(y=alt.value(150))
        return (_line + _rule + _ticks).properties(width=700, height=150)
    mo.vstack([
        _panel("pca_ratio", "PCA / seuil", 1.0, "#3b6fb6"),
        _panel("envelope_score", "Écart enveloppe", model.envelope_threshold, "#c8553d"),
    ])
    return (scores_all,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 5. Validation hors échantillon

    Les alertes sur les données d'entraînement ne prouvent rien : le modèle les a déjà vues. On découpe donc la
    baseline en **blocs de 10 min** ; pour chaque bloc, on entraîne sans lui puis on le score. Toute alerte est
    un **faux positif**, puisque tout est sain.
    """)
    return


@app.cell
def _(X_train, params):
    _blk = (X_train.index - X_train.index.min()) // 600
    _rows, _parts = [], []
    for _b in sorted(_blk.unique()):
        _s = AnomalyModel(**params).fit(X_train[_blk != _b]).score(X_train[_blk == _b])
        _parts.append(_s)
        _h = to_local(X_train[_blk == _b].index)
        _rows.append({"bloc": f"{_h.min():%H:%M}–{_h.max():%H:%M}", "fenêtres": len(_s),
                      "faux positifs": int(_s.anomaly.sum()),
                      "exemple d'explication": next((t for t in _s.top_features[_s.anomaly == 1] if t), "")})
    cv_scores = pd.concat(_parts).sort_index()
    _fp = cv_scores.anomaly.mean()
    # Alerte réelle = au moins 2 fenêtres anormales consécutives (règle MLAnomalieDetectee)
    _a = cv_scores.anomaly.to_numpy()
    _runs, _n = [], 0
    for _v in list(_a) + [0]:
        if _v:
            _n += 1
        else:
            if _n:
                _runs.append(_n)
            _n = 0
    _alerts = sum(1 for _r in _runs if _r >= 2)
    _hours = len(cv_scores) * 15 / 3600
    mo.vstack([
        mo.hstack([mo.stat(f"{_fp:.1%}", label="Taux de faux positifs hors échantillon",
                           caption=f"{int(cv_scores.anomaly.sum())}/{len(cv_scores)} fenêtres"),
                   mo.stat(f"{_alerts}", label="Fausses alertes déclenchées",
                           caption=f"règle « 2 fenêtres consécutives », sur {_hours:.1f} h de données saines")], widths="equal"),
        mo.ui.table(pd.DataFrame(_rows), selection=None),
    ])
    return (cv_scores,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 6. Simulateur d'attaques

    On part de fenêtres saines réelles et on déforme les features comme le ferait une attaque.
    **Ce sont des contrôles de cohérence, pas des mesures** : les vrais chiffres viennent du run d'attaque (§8).
    """)
    return


@app.cell
def _():
    VOLUME = ["http_rps", "http_rps_donations", "http_rps_2xx", "log_waf_lines", "log_waf_2xx",
              "log_api_lines", "c_security_waf_net_rx_bps", "c_app_api_net_rx_bps"]
    LEGIT = ["http_rps", "http_rps_2xx", "http_rps_donations", "donations_succeeded_rps", "donations_failed_rps"]

    def simulate(base: pd.DataFrame, scenario: str, k: float) -> pd.DataFrame:
        a = base.copy()
        has = lambda cols: [c for c in cols if c in a]
        if scenario == "Flood HTTP (volume × k)":
            a[has(VOLUME)] *= k
            a["c_app_api_cpu"] = (a["c_app_api_cpu"] * k).clip(upper=1.0)
        elif scenario == "Erreurs 5xx (k req/s)":
            a["http_rps_5xx"] = k
        elif scenario == "Flood bloqué par le WAF (403, × k)":
            a["log_waf_lines"] *= k
            a["log_waf_4xx"] = a["log_waf_lines"] * 0.9
            a["log_waf_uniq_paths"] = 2 * k
        elif scenario == "Effondrement du trafic légitime (÷ k)":
            a[has(LEGIT)] /= k
        elif scenario == "Saturation base de données (latence × k)":
            for c in has(["http_latency_avg_s", "http_latency_p95_s", "payment_latency_avg_s",
                          "payment_latency_p95_s"]):
                a[c] *= k
            a["c_app_db_cpu"] = (a["c_app_db_cpu"] * k).clip(upper=1.0)
        elif scenario == "Combinaison incohérente (k ignoré)":
            ref = base  # trafic au plancher sain, mais CPU API et réseau DB au plafond sain
            for c in has(["http_rps", "http_rps_2xx", "http_rps_donations", "log_waf_lines", "log_waf_2xx", "log_api_lines"]):
                a[c] = ref[c].quantile(0.02)
            for c in has(["c_app_api_cpu", "c_app_db_net_rx_bps", "c_app_db_net_tx_bps", "http_latency_avg_s"]):
                a[c] = ref[c].quantile(0.98)
        return a

    SCENARIOS = ["Flood HTTP (volume × k)", "Erreurs 5xx (k req/s)", "Flood bloqué par le WAF (403, × k)",
                 "Effondrement du trafic légitime (÷ k)", "Saturation base de données (latence × k)",
                 "Combinaison incohérente (k ignoré)"]
    return SCENARIOS, simulate


@app.cell
def _(SCENARIOS):
    scenario = mo.ui.dropdown(SCENARIOS, value=SCENARIOS[0], label="Scénario")
    intensity = mo.ui.slider(1, 20, step=0.25, value=3, label="Intensité k", show_value=True)
    mo.hstack([scenario, intensity], justify="start", gap=2)
    return intensity, scenario


@app.cell
def _(X_train, intensity, model, scenario, simulate):
    _base = X_train.iloc[len(X_train) // 2: len(X_train) // 2 + 20]
    _att = simulate(X_train, scenario.value, intensity.value).loc[_base.index] if scenario.value.startswith("Combinaison") \
        else simulate(_base, scenario.value, intensity.value)
    _s = model.score(_att)
    _dev = model.deviations(_att).mean().sort_values(ascending=False).head(10).rename("écart").reset_index()
    _dev.columns = ["feature", "écart"]
    _detected = _s.anomaly.mean()
    _bars = alt.Chart(_dev).mark_bar().encode(
        y=alt.Y("feature:N", sort="-x", title=None), x=alt.X("écart:Q", title="Écart à l'enveloppe saine"),
        color=alt.condition(alt.datum["écart"] > model.envelope_threshold, alt.value("#c8553d"), alt.value("#bbb")),
        tooltip=["feature", alt.Tooltip("écart:Q", format=".2f")]).properties(width=420, height=220)
    _rule = alt.Chart(pd.DataFrame({"x": [model.envelope_threshold]})).mark_rule(strokeDash=[4, 3]).encode(x="x:Q")
    mo.hstack([
        mo.vstack([
            mo.stat(f"{_detected:.0%}", label="Fenêtres détectées",
                    caption="✅ détecté" if _detected > 0.5 else "❌ non détecté"),
            mo.stat(f"{_s.pca_ratio.mean():.2f}", label="PCA / seuil", caption="> 1 = corrélations cassées"),
            mo.stat(f"{_s.envelope_score.mean():.2f}", label="Écart enveloppe max", caption=f"> {model.envelope_threshold} = hors plage"),
        ]),
        (_bars + _rule) if len(_dev) and _dev["écart"].max() > 0 else mo.md("_Aucune feature hors enveloppe : seule la PCA peut voir ce scénario._"),
    ], justify="start", gap=3)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 7. Pourquoi PCA + enveloppe, et pas un Isolation Forest seul ?

    Même données d'entraînement, même méthode de seuil (quantile des scores sains). L'Isolation Forest découpe
    l'espace **à l'intérieur** de la plage vue à l'entraînement : il ne peut pas exploiter une feature constante en sain
    (5xx = 0) et sous-évalue les points qui sortent de la plage.
    """)
    return


@app.cell
def _(SCENARIOS, X_train, model, params, simulate):
    _Z = log1p_signed(X_train[model.columns])
    _sc = RobustScaler(quantile_range=(5, 95)).fit(_Z)
    _std = lambda X: np.clip(np.nan_to_num(_sc.transform(log1p_signed(X[model.columns]))), -50, 50)
    _if = IsolationForest(n_estimators=300, random_state=42).fit(_std(X_train))
    _thr = np.quantile(-_if.score_samples(_std(X_train)), params["pca_quantile"])
    _base = X_train.iloc[len(X_train) // 2: len(X_train) // 2 + 20]
    _k = {"Erreurs 5xx (k req/s)": 2, "Effondrement du trafic légitime (÷ k)": 5}
    _rows = []
    for _sc_name in SCENARIOS:
        _kk = _k.get(_sc_name, 3)
        _a = simulate(X_train, _sc_name, _kk).loc[_base.index] if _sc_name.startswith("Combinaison") else simulate(_base, _sc_name, _kk)
        _s = model.score(_a)
        _rows.append({"scénario": _sc_name.replace("(k ignoré)", "").replace("k req/s", f"{_kk} req/s").replace("× k", f"× {_kk}").replace("÷ k", f"÷ {_kk}").strip(),
                      "Isolation Forest": f"{(-_if.score_samples(_std(_a)) > _thr).mean():.0%}",
                      "PCA seule": f"{(_s.pca_ratio > 1).mean():.0%}",
                      "Enveloppe seule": f"{(_s.envelope_score > model.envelope_threshold).mean():.0%}",
                      "PCA + enveloppe": f"{_s.anomaly.mean():.0%}"})
    mo.ui.table(pd.DataFrame(_rows), selection=None)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 8. Évaluation sur le run d'attaque réel

    Après le run avec attaques : exporte la période (`python3 export.py --start … --end … --out data/attack`)
    et note les heures de chaque attaque dans `data/attack/attacks.csv` :

    ```
    start,end,label
    2026-10-21T15:05:00+02:00,2026-10-21T15:10:00+02:00,http_flood
    ```
    """)
    return


@app.cell
def _():
    atk_prom = mo.ui.text(value=str(ROOT / "data/attack/prometheus.csv"), label="Export Prometheus (attaque)", full_width=True)
    atk_loki = mo.ui.text(value=str(ROOT / "data/attack/loki.jsonl"), label="Export Loki (attaque)", full_width=True)
    atk_truth = mo.ui.text(value=str(ROOT / "data/attack/attacks.csv"), label="Vérité terrain (attacks.csv)", full_width=True)
    mo.vstack([atk_prom, atk_loki, atk_truth])
    return atk_loki, atk_prom, atk_truth


@app.cell
def _(atk_loki, atk_prom, atk_truth, model):
    mo.stop(not (Path(atk_prom.value).exists() and Path(atk_loki.value).exists()),
            mo.callout(mo.md("Pas encore d'export d'attaque. Cette section se remplira automatiquement "
                             "dès que les fichiers seront présents."), kind="info"))
    with mo.status.spinner("Scoring du run d'attaque…"):
        X_atk = build_features(load_prom_csv(atk_prom.value), load_loki_jsonl(atk_loki.value), columns=model.columns)
        atk_scores = model.score(X_atk)
    atk_scores["heure"] = to_local(atk_scores.index)
    attacks = None
    if Path(atk_truth.value).exists():
        attacks = pd.read_csv(atk_truth.value)
        attacks["start"] = pd.to_datetime(attacks["start"], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        attacks["end"] = pd.to_datetime(attacks["end"], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        atk_scores["vérité"] = "normal"
        for _, _r in attacks.iterrows():
            atk_scores.loc[(atk_scores.heure >= _r.start) & (atk_scores.heure <= _r.end), "vérité"] = _r.label
    return atk_scores, attacks


@app.cell
def _(atk_scores, attacks, model):
    _base = alt.Chart(atk_scores).encode(x=alt.X("heure:T", title="Heure (Paris)", axis=alt.Axis(format="%H:%M")))
    _layers = []
    if attacks is not None:
        _layers.append(alt.Chart(attacks).mark_rect(color="#f2c14e", opacity=0.3).encode(x="start:T", x2="end:T", tooltip=["label"]))
    _layers += [
        _base.mark_line(color="#3b6fb6").encode(y=alt.Y("pca_ratio:Q", scale=alt.Scale(type="symlog"), title="score / seuil"), tooltip=["heure:T", "top_features:N"]),
        _base.mark_line(color="#c8553d").encode(y="envelope_score:Q"),
        _base.transform_filter("datum.anomaly == 1").mark_tick(color="crimson", thickness=2).encode(y=alt.value(190)),
    ]
    _chart = mo.vstack([alt.layer(*_layers).properties(width=720, height=200),
                        mo.md("<small>Bleu : PCA / seuil · rouge : écart à l'enveloppe · zones jaunes : attaques déclarées · traits rouges : fenêtres détectées</small>")])

    if attacks is None:
        _out = mo.vstack([_chart, mo.callout(mo.md("Ajoute `attacks.csv` pour obtenir précision / rappel."), kind="info")])
    else:
        _y = atk_scores["vérité"] != "normal"
        _p = atk_scores["anomaly"] == 1
        _tp, _fp, _fn, _tn = int((_p & _y).sum()), int((_p & ~_y).sum()), int((~_p & _y).sum()), int((~_p & ~_y).sum())
        _rows = []
        for _, _r in attacks.iterrows():
            _w = atk_scores[(atk_scores.heure >= _r.start) & (atk_scores.heure <= _r.end)]
            _h = _w[_w.anomaly == 1]
            _rows.append({"attaque": _r.label, "détectée": "oui" if len(_h) else "NON",
                          "délai (s)": (_h.heure.iloc[0] - _r.start).total_seconds() if len(_h) else None,
                          "couverture": f"{len(_h)}/{len(_w)}",
                          "explication": _h.top_features.iloc[0] if len(_h) else ""})
        _out = mo.vstack([
            mo.hstack([mo.stat(f"{_tp / max(_tp + _fp, 1):.2f}", label="Précision"),
                       mo.stat(f"{_tp / max(_tp + _fn, 1):.2f}", label="Rappel"),
                       mo.stat(f"{_fp / max(_fp + _tn, 1):.1%}", label="Faux positifs (hors attaques)")], widths="equal"),
            _chart, mo.ui.table(pd.DataFrame(_rows), selection=None)])
    _out
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 9. Export du modèle pour le détecteur temps réel

    Le détecteur (`detector.py`, conteneur `monitoring-ml-detector`) charge ce fichier et calcule exactement les mêmes
    features via la bibliothèque `resilience_ml`. Les paramètres choisis avec les curseurs sont enregistrés dans le modèle.
    """)
    return


@app.cell
def _():
    save_btn = mo.ui.run_button(label="Enregistrer models/baseline.joblib", kind="success")
    save_btn
    return (save_btn,)


@app.cell
def _(X_feat, model, save_btn):
    mo.stop(not save_btn.value, mo.md(f"_Paramètres actuels : `{model.params()}`_"))
    (ROOT / "models").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    model.save(ROOT / "models/baseline.joblib")
    X_feat.to_csv(ROOT / "data/features_baseline.csv")
    mo.callout(mo.md(f"Modèle enregistré : `models/baseline.joblib` — {model.train_stats['n_features']} features, "
                     f"paramètres `{model.params()}`. Reconstruire l'image du détecteur pour le déployer."), kind="success")
    return


if __name__ == "__main__":
    app.run()
