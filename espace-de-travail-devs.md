# Espace de travail DEV, RESILIENCE-ALPHA

## La machine

VM `host` (Ubuntu Server 26.04), 6 vCPU, 8 Go, 60 Go, Docker 29.9 + Compose. C'est le serveur du SI, c'est là que vos conteneurs tournent. Adresse lab `192.168.137.1`.

## Accès

Lab accessible via Tailscale (déjà en place pour vous). SSH sur `host` : compte `ubuntu`, par clé (envoyez votre clé publique à Mathieu).

## Ce qui tourne déjà dessus

- Supervision en service : Prometheus (9090), Grafana (3000), Loki (3100), Promtail, node-exporter, cAdvisor. Les 3 machines du projet (host, soc, kali) sont monitorées.
- PostgreSQL 17 prêt (service `db`).
- Réseau Docker partagé `resilience-net` (externe, déjà créé). Tous vos services s'y branchent.
- Dépôt du projet : `/opt/resilience` (git). Votre zone : `app/services/`.

## Le dépôt `/opt/resilience`

- `app/` : votre plateforme de paiement (à implémenter). `app/compose.yaml` fournit déjà `db`.
- `monitoring/` : supervision (en service, ne pas toucher).
- `security/` : WAF, secrets (équipe SOC/cyber). `ansible/` : déploiement, remédiation (équipe Ansible).
- `docs/ONBOARDING-DEVS.md` : à lire en premier, détaille les contrats.

## Votre stack

- `auth` : authentification par token JWT. Backend Python.
- `api` : API métier (transactions). Backend Python (FastAPI recommandé).
- `frontend` : TypeScript (React + Tailwind).

## Contrats d'intégration (à respecter)

- `api` et `auth` : port `8000`, `GET /healthz` (200 si sain), `GET /metrics` (format Prometheus). Pas de `ports:` publiés (le WAF sera l'entrée), seulement `expose:`. Rejoindre `resilience-net`.
- `frontend` : port `80`.
- L'API initie et traite une transaction fictive de bout en bout (c'est la preuve de reprise). Aucune donnée bancaire réelle. Logs sur stdout.

## Identifiants (lab, à ne PAS committer dans un repo public)

- Grafana : `admin` / `resilience` (port 3000).
- PostgreSQL : user `payment`, base `payment`, mot de passe dans `.env` (défaut `change-me`, à changer).
- SSH `host` : compte `ubuntu`, par clé (fournie par Mathieu).

## Démarrer

```
cd /opt/resilience/app
docker compose up -d db            # la base est prête
# implémentez services/api, services/auth, services/frontend (Dockerfile + code)
# décommentez les services dans compose.yaml, puis :
docker compose up -d
```
