# resilience-ml — détection d'anomalies sur la plateforme RESILIENCE-ALPHA

Apprentissage **non supervisé sur le système sain** (métriques Prometheus + journaux Loki de la
plateforme elle-même), puis détection en temps réel branchée sur la stack : le détecteur expose ses
scores à Prometheus, Grafana les affiche et alerte.

```
Prometheus ─┐                         ┌─> /metrics :9105 ─> Prometheus ─> Grafana (panneaux + alertes)
            ├─> features (15 s) ─> modèle
Loki ───────┘                         └─> stdout JSON ─> Promtail ─> Loki ─> SIEM
```

## Démarrer avec les notebooks (marimo)

```bash
pip install -r requirements.txt
# place tes exports dans data/baseline/prometheus.csv et data/baseline/loki.jsonl
marimo edit notebooks/02_detection_guidee.py     # tu construis le détecteur toi-même
marimo edit notebooks/01_detection_complete.py   # version complète et interactive (= correction)
marimo run  notebooks/01_detection_complete.py   # mode présentation jury (code masqué)
```

- **`01_detection_complete.py`** : exploration, défauts de collecte, curseurs sur tous les paramètres, PCA expliquée,
  validation hors échantillon, comparaison avec Isolation Forest, simulateur d'attaques, évaluation du run
  d'attaque (se remplit dès que `data/attack/` existe), bouton d'export du modèle pour le détecteur live.
- **`02_detection_guidee.py`** : 9 exercices (lecture de l'export, features Prometheus et Loki, choix des fenêtres,
  PCA, Isolation Forest, enveloppe, validation par blocs, précision/rappel). Chaque exercice a des indices repliés et
  une cellule de vérification automatique (⏳ / ❌ / ✅). Un interrupteur permet de continuer avec les features de
  référence si on bloque.

Les notebooks s'appuient sur `resilience_ml/`, la bibliothèque qu'utilise aussi le détecteur temps réel :
les features calculées en live sont ainsi exactement celles de l'entraînement.

## Contenu

| Fichier | Rôle |
|---|---|
| `resilience_ml/features.py` | 71 features par fenêtre de 15 s : trafic/latence/erreurs HTTP, paiements, CPU/RAM/réseau des conteneurs clés, nœuds host + SOC, logs WAF/API/DB/système. **Même code hors ligne et en live.** |
| `resilience_ml/model.py` | PCA (erreur de reconstruction) + enveloppe par feature, avec explication des features en cause |
| `notebooks/` | Notebooks marimo : complet/interactif et guidé à compléter |
| `train.py` | Entraîne sur un export sain (équivalent ligne de commande du notebook) |
| `score.py` | Score un export (run d'attaque), graphique + précision/rappel si vérité terrain fournie |
| `export.py` | Exporte une période depuis Prometheus/Loki au bon format |
| `detector.py` | Détecteur temps réel (métriques `resilience_ml_*`) |
| `deploy/` | Compose durci, job de scrape, règles d'alerte |
| `models/baseline.joblib` | Modèle entraîné sur la baseline du 21/10 (12:10–13:25) |
| `tests/` | Contrôles synthétiques + faux Prometheus/Loki pour tester sans la stack |

## Pourquoi ce modèle (à défendre devant le jury)

- **Entraîné uniquement sur du sain** : on ne connaît pas à l'avance toutes les attaques ; on apprend
  le normal et on signale l'écart. Les données d'attaque servent à **évaluer**, pas à entraîner.
- **PCA / erreur de reconstruction** : apprend comment les métriques bougent *ensemble* (débit WAF ↔ CPU API ↔
  réseau DB). Testée contre un Isolation Forest sur cette baseline : l'IF ne détectait ni une charge ×3 ni
  une combinaison incohérente (trafic faible mais CPU/DB au max) ; la PCA détecte les deux.
- **Enveloppe par feature** : couvre ce qui vaut 0 en sain (5xx, 4xx, saturation DB) et que la PCA ne peut
  pas apprendre, et donne l'explication lisible : `log_waf_4xx=27.4, log_waf_uniq_paths=9.3…`
- **log1p** sur toutes les features : un DDoS se lit en ordres de grandeur.
- **Alerte après 2 fenêtres consécutives** (30 s) pour filtrer les faux positifs isolés.

## Résultats sur la baseline (sans données d'attaque réelles pour l'instant)

- 249 fenêtres de 15 s retenues (générateur actif), 71 features, 3 composantes PCA.
- Faux positifs **hors échantillon** (validation croisée par blocs de 10 min) : **12/249 = 4,8 %**, dont 10
  dans les 7 premières minutes (démarrage du générateur, vu une seule fois). Régime établi : 2/223.
- Attaques **synthétiques** (contrôle de cohérence, pas des mesures) : charge ×2 / ×3 / ×20, 5xx, scan bloqué
  par le WAF, effondrement du trafic légitime, combinaison incohérente → toutes détectées.
  Les vrais chiffres viendront du run d'attaque.

## Run d'attaque — procédure

1. **Ne rien changer à la collecte entre la baseline et l'attaque** (exporters, labels, conteneurs).
   Sinon tout paraît « anormal » et l'évaluation ne vaut rien. Si tu modifies la collecte (cf. node-exporter
   plus bas), refais une baseline.
2. Lance le générateur de trafic légitime, attends ~5 min, puis les attaques depuis la Kali.
   **Note l'heure exacte de début/fin de chaque attaque** dans `attacks.csv` :
   ```
   start,end,label
   2026-10-21T15:05:00+02:00,2026-10-21T15:10:00+02:00,http_flood
   2026-10-21T15:20:00+02:00,2026-10-21T15:25:00+02:00,syn_flood
   ```
   Laisse ~5 min de calme entre deux attaques pour montrer le retour à la normale.
3. Exporte puis évalue :
   ```bash
   python3 export.py --prom-url http://localhost:9090 --loki-url http://localhost:3100 \
                     --start 2026-10-21T15:00:00+02:00 --end 2026-10-21T16:00:00+02:00 --out data/attack
   python3 score.py --model models/baseline.joblib --prom data/attack/prometheus.csv \
                    --loki data/attack/loki.jsonl --attacks attacks.csv --out reports/attack
   ```
   → `reports/attack.png` + précision, rappel, délai de détection et explication par attaque.

Entraîner à nouveau : `python3 train.py --prom data/baseline/prometheus.csv --loki data/baseline/loki.jsonl`

## Déploiement live

```bash
# sur host-resilience
docker compose -f deploy/compose.ml-detector.yaml up -d --build
# ajouter deploy/prometheus-scrape.yml à prometheus.yml, deploy/alert-rules.yml en rule_files, recharger
```
Requêtes Grafana utiles :
`resilience_ml_pca_ratio`, `resilience_ml_envelope_score`, `resilience_ml_anomaly_consecutive`,
`topk(5, resilience_ml_feature_deviation)` (quelles métriques dérivent).

Démo jury d'une attaque passée, en temps réel : `--replay-offset <secondes>` rejoue une période enregistrée.
Debug d'une fenêtre : `python3 detector.py --once <unix_ts>`.

## Problèmes constatés dans la collecte actuelle

1. **node-exporter ne voit pas la machine.** `node_host_net_rx_bps` ≈ 42 o/s et `Tcp_CurrEstab` = 1 en
   permanence, alors que l'API reçoit ~16 ko/s : node-exporter tourne dans son propre namespace réseau.
   Conséquence : **un SYN flood ou un flood L4 serait invisible côté nœud.** Correctif (host et SOC) :
   ```yaml
   node-exporter:
     image: prom/node-exporter
     network_mode: host
     pid: host
     volumes: ["/:/host:ro,rslave"]
     command: ["--path.rootfs=/host"]
   ```
   (Prometheus doit alors le scraper via l'IP de l'hôte, ex. `172.18.0.1:9100`.) Les features TCP
   (`PassiveOpens`, `InSegs`, `OutRsts`, `ListenDrops`, `SyncookiesSent`, `TIME_WAIT`) sont déjà prévues :
   elles s'activent automatiquement dès qu'une baseline les contient.
2. **Un seul client légitime** : tout le trafic sain est `curl` depuis host-resilience (IP vue par le WAF :
   `172.18.0.1`). Les features IP / User-Agent sont donc **désactivées** (sinon on détecte « une nouvelle IP »,
   pas une attaque, et un simple navigateur déclenche une alerte). Pour les réactiver
   (`--include-client-features`), génère du trafic légitime depuis 2–3 machines différentes.
3. **Charge plate** (~7,25 req/s constant) : le modèle considère toute variation ≥ ×1,5 comme anormale.
   Un générateur avec des variations (paliers, rafales légitimes) rendrait la baseline plus réaliste
   et réduirait les faux positifs.
4. La cible `auth:8000` est **DOWN pendant toute la baseline** (`up=0`) : service absent ou mauvais
   job de scrape. Exclue des features.
5. Pas de logs Loki des VM SOC et Kali (seul host-resilience remonte).
