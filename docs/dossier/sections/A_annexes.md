# Annexe A : Arborescences

## Dépôt de l'équipe (`github.com/cristelleal/workshop_m2`)

| Chemin | Contenu |
|---|---|
| `backend/` | API FastAPI : `app/routes/` (auth, donations), `app/core/` (configuration, sécurité, logs, métriques), `app/service/payment.py`, `migrations/` (Alembic), `Dockerfile` |
| `frontend/` | Frontal React + Tailwind (`src/pages`, `src/components`, `src/services`), `Dockerfile`, `nginx.conf` |
| `docker-compose.yml`, `docker-compose.local.yml` | Déploiement sur le host, surcharge pour le développement local |
| `docs/` | Guides de déploiement (`deploiment.md`, `deploimentAuto.md`, `a-faire-proxmox.md`), ce dossier (`docs/dossier/`) |
| `.github/workflows/config.yml` | CI : lint et tests, npm audit, pip-audit, gitleaks |
| branche `feature/thomas/assistantOllamaQdrant` | `assistant/` : assistant RAG (FastAPI, LangChain, Ollama, Qdrant) |
| `IA/ml/` (hors Git au 22/10) | Détection ML : `resilience_ml/`, `train.py`, `score.py`, `export.py`, `detector.py`, `deploy/`, `notebooks/`, `tests/` |

## Socle de la VM (`/opt/resilience`)

| Chemin | Contenu |
|---|---|
| `app/compose.yaml` | Services `db`, `api`, `frontend` (code dans `app/services/`) |
| `monitoring/` | Compose de supervision, `prometheus/prometheus.yml`, `prometheus/alert-rules-ml.yml`, Loki, Promtail, dashboards Grafana |
| `security/waf/` | WAF ModSecurity CRS : `compose.yaml`, `proxy_backend.conf.template`, `blocklist.conf` |
| `edge/`, `edge-dns/` | Caddy (HTTPS) et CoreDNS (noms du lab) |
| `dev-access/` | Accès des développeurs au frontal (:8081) |
| `ansible/` | README uniquement |
| `docs/` | `ARCHITECTURE.md`, `ONBOARDING-DEVS.md` |

# Annexe B : API et déploiement

## Routes de l'API

| Route | Jeton requis | Rôle |
|---|---|---|
| `POST /auth/register` | non | Créer un compte (e-mail, mot de passe de 8 caractères minimum) |
| `POST /auth/login` | non | Se connecter, obtenir un jeton valable 60 min |
| `GET /auth/me` | oui | Compte connecté |
| `GET /donations/presets` | non | Montants proposés (5, 10, 25, 50 €) et bornes (1 € à 10 000 €) |
| `POST /donations` | oui | Faire un don (montant en centimes, fréquence, carte de test) |
| `GET /donations/me`, `GET /donations/{id}` | oui | Ses propres dons (404 pour le don d'un autre) |
| `GET /donations/all` | oui | Faille volontaire : tous les dons de tous les utilisateurs |
| `GET /healthz`, `GET /metrics`, `GET /docs` | non | Santé, métriques Prometheus, documentation Swagger |

## Déploiement

Le déploiement complet est décrit dans deux guides du dépôt. `docs/deploiment.md` copie le code sur la VM par `rsync`, prépare le `.env`, puis détaille les vérifications, la simulation de donateurs et le dépannage. `docs/deploimentAuto.md` installe un clone Git sur la VM avec une clé de déploiement, puis met à jour l'application en une commande (`deploy-app.sh`), retour arrière compris. Les trois commandes les plus utiles sont la mise à jour de l'application, le déploiement du détecteur et le réentraînement du modèle :

```
cd /opt/resilience/app && docker compose up -d --build api frontend
docker compose -f deploy/compose.ml-detector.yaml up -d --build
python3 train.py --prom data/baseline/prometheus.csv --loki data/baseline/loki.jsonl
```

# Annexe C : Les 63 features du modèle en production

| Famille | Features |
|---|---|
| HTTP | `http_rps`, `http_rps_donations`, `http_rps_login`, `http_rps_register`, `http_rps_unmatched`, `http_rps_2xx`, `http_rps_4xx`, `http_rps_5xx`, `http_latency_avg_s`, `http_latency_p95_s`, `http_req_size_avg_b`, `http_resp_size_avg_b` |
| Paiement | `payment_latency_p95_s`, `payment_latency_avg_s`, `donations_succeeded_rps`, `donations_failed_rps` |
| Processus API | `api_process_cpu`, `api_open_fds` |
| Conteneurs | `c_app_api_cpu`, `c_security_waf_cpu`, `c_app_db_cpu`, `c_app_frontend_cpu`, et `c_<conteneur>_net_rx_bps` / `_net_tx_bps` pour les 4 conteneurs |
| Nœud host | `node_host_cpu_busy`, `node_host_load1`, `node_host_net_rx_bps`, `node_host_net_tx_bps`, `node_host_tcp_estab`, `node_host_tcp_inuse` |
| Nœud SOC | `node_soc_cpu_busy`, `node_soc_load1`, `node_soc_net_rx_bps`, `node_soc_net_tx_bps`, `node_soc_tcp_estab`, `node_soc_tcp_inuse` |
| Supervision | `targets_down` |
| Logs WAF | `log_waf_lines`, `log_waf_2xx`, `log_waf_3xx`, `log_waf_4xx`, `log_waf_5xx`, `log_waf_bytes`, `log_waf_uniq_paths` |
| Logs frontal et API | `log_front_lines`, `log_front_4xx`, `log_front_5xx`, `log_api_lines`, `log_api_warn_err`, `log_api_fail_events`, `log_api_login_events` |
| Logs base | `log_db_lines`, `log_db_errors`, `log_db_conn_saturation` |
| Logs système | `log_sys_syslog_lines`, `log_sys_auth_lines`, `log_sys_kern_lines` |

Sont exclues à l'entraînement les jauges mémoire (`*_mem_bytes`, `*_rss_bytes`, `*_mem_avail_bytes`), `log_sys_errors` et les indicateurs clients du WAF (adresses IP et navigateurs). 17 des 63 indicateurs sont constants sur la baseline : ils ne participent qu'à l'enveloppe.

# Annexe D : Glossaire

| Terme | Définition |
|---|---|
| WAF / CRS | Pare-feu applicatif web. L'OWASP Core Rule Set est un jeu de règles génériques contre les attaques web |
| PCA / SPE | Analyse en composantes principales. Le SPE (erreur quadratique de prédiction) mesure ce que le modèle ne sait pas reconstruire |
| Enveloppe | Plage [min, max] observée en régime sain pour chaque feature |
| Fenêtre | Intervalle de 15 s sur lequel les features sont calculées |
| Faux positif hors échantillon | Fenêtre saine jugée anormale par un modèle qui ne l'a pas vue à l'entraînement |
| RTO / RPO | Durée maximale d'interruption admissible / perte de données maximale admissible |
| RAG | Génération augmentée par recherche : le modèle répond à partir de passages retrouvés dans une base documentaire |
| BOLA | Broken Object Level Authorization : accès aux objets d'autres utilisateurs (OWASP API1) |
