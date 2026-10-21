# Déploiement de la stack de dev sur Proxmox

Ce guide déploie l'API et le frontend sur la VM `host-resilience`, en environnement de **dev** (pas de prod).

- **Cible** : VM `host-resilience` (Proxmox VMID 5010), Ubuntu Server, IP lab `192.168.137.1`.
- **Ce qu'on déploie** :
  - `api` : FastAPI, avec comptes utilisateurs (JWT) et dons ;
  - `frontend` : React servi par Nginx.
- **Déjà en place sur la VM, on n'y touche pas** :
  - la base `db` (Postgres 17) ;
  - le WAF `security-waf` (ModSecurity + OWASP CRS), qui est l'entrée sur le port 80 ;
  - le monitoring : Prometheus, Grafana, Loki, Promtail, node-exporter et cAdvisor.

> **Ce qu'il faut faire sur le Proxmox, en version courte** : voir [`a-faire-proxmox.md`](a-faire-proxmox.md).
>
> **Deux façons de copier le code sur la VM :**
> - **Ce guide** : on copie les fichiers depuis son poste avec `rsync`. C'est le plus simple pour un premier essai.
> - **[`deploimentAuto.md`](deploimentAuto.md)** : le repo est cloné sur la VM avec une deploy key, et une mise à jour se fait en une commande (`deploy-app.sh`). C'est la méthode recommandée dès qu'on déploie souvent.
>
> Les sections 3 à 9 et 11 à 12 de ce guide (compose, `.env`, vérifications, monitoring, trafic, dépannage) servent pour les deux méthodes.

---

## Sommaire

0. [Vue d'ensemble](#0-vue-densemble)
1. [Prérequis](#1-prérequis)
2. [Copier le code sur la VM](#2-copier-le-code-sur-la-vm)
3. [Activer les services dans le compose](#3-activer-les-services-dans-le-compose)
4. [Préparer le `.env` (clé JWT)](#4-préparer-le-env-clé-jwt)
5. [Construire et lancer](#5-construire-et-lancer)
6. [Vérifier que tout marche](#6-vérifier-que-tout-marche)
7. [Vérifier le monitoring (Prometheus et Loki)](#7-vérifier-le-monitoring)
8. [Simuler des donateurs](#8-simuler-des-donateurs)
9. [Accéder au frontend depuis son navigateur](#9-accéder-au-frontend-depuis-son-navigateur)
10. [Mettre à jour après un changement de code](#10-mettre-à-jour)
11. [Arrêter ou revenir en arrière](#11-arrêter-ou-revenir-en-arrière)
12. [Dépannage](#12-dépannage)

---

## 0. Vue d'ensemble

```
                          VM host-resilience (192.168.137.1)
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  :80 publié (seule entrée de l'app)                                        │
 │    │          réseau Docker « resilience-net »                             │
 │  ┌─▼──────────────────────────────────────────────────────────────────┐    │
 │  │ security-waf ──────────▶ app-api :8000 ──────────▶ app-db :5432    │    │
 │  │ (ModSecurity + CRS)      (FastAPI + JWT)           (Postgres)      │    │
 │  │                             ▲     ▲                                │    │
 │  │ app-frontend :80 ──/api/*───┘     │ scrape /metrics (15 s)         │    │
 │  │ (Nginx + React, non exposé)     monitoring-prometheus              │    │
 │  └────────────────────────────────────────────────────────────────────┘    │
 │  monitoring-promtail : logs stdout de tous les conteneurs ──▶ Loki         │
 │  Autres ports publiés : 9090 Prometheus, 3000 Grafana, 3100 Loki           │
 └────────────────────────────────────────────────────────────────────────────┘
```

**Le trafic** : le WAF (`BACKEND: http://api:8000`) envoie **tout** vers l'API. Depuis son poste (via Tailscale), l'API se joint donc directement sur `http://192.168.137.1/...`, et depuis la VM sur `http://localhost/...`. Le frontend n'est pas exposé par le WAF : voir la [section 9](#9-accéder-au-frontend-depuis-son-navigateur).

### Les routes de l'API

| Route | Token requis | Rôle |
|-------|:------------:|------|
| `GET /healthz` | non | Santé : `200 {"status":"ok"}` si la base répond. ⚠️ **Via le WAF, cette route ne touche pas l'API** : le WAF répond lui-même `OK` (c'est sa propre sonde), même si l'API est arrêtée. Tester en direct sur `api:8000` |
| `GET /metrics` | non | Metrics Prometheus |
| `POST /auth/register` | non | Créer un compte. JSON : `{"email": "...", "password": "..."}` (8 caractères minimum) |
| `POST /auth/login` | non | Se connecter. **Formulaire** (pas JSON) : `username=<email>&password=<mdp>`. Renvoie un token valable 60 min |
| `GET /auth/me` | oui | Le compte connecté |
| `GET /donations/presets` | non | Montants proposés (5, 10, 25, 50 €) et bornes du montant libre (1 € à 10 000 €) |
| `POST /donations` | oui | Faire un don. JSON : `{"amount_cents": 2500, "frequency": "once", "card_number": "4242424242424242"}` |
| `GET /donations/me` | oui | Ses propres dons |
| `GET /donations/{id}` | oui | Un de ses dons (404 si c'est le don de quelqu'un d'autre) |
| `GET /donations/all` | oui | ⚠️ **Tous les dons de tous les utilisateurs** (faille volontaire, voir ci-dessous) |
| `GET /docs` | non | Documentation Swagger interactive |

- Le token s'envoie dans l'en-tête `Authorization: Bearer <token>`.
- `frequency` vaut `once` ou `monthly`.
- Les montants sont **en centimes** (`2500` = 25 €).

### Les cartes de test

Le paiement est **simulé**, sans prestataire externe. Seules ces cartes sont reconnues, et seuls leurs 4 derniers chiffres sont stockés :

| Carte | Résultat (`status` / `failure_reason`) |
|-------|----------------------------------------|
| `4242424242424242` | `succeeded` |
| `4000000000000002` | `failed` / `card_declined` |
| `4000000000009995` | `failed` / `insufficient_funds` |
| toute autre carte de 16 chiffres | `failed` / `unknown_test_card` |

Le traitement prend volontairement entre 0,1 et 0,6 s, pour avoir une latence réaliste dans Grafana.

### ⚠️ Failles connues (volontaires)

L'environnement sert aussi d'exercice d'attaque (VM `attacker-kali`) et de détection (équipe SOC). **Ne pas corriger ces points sans en parler à l'équipe :**

| Point | Détail |
|-------|--------|
| `GET /donations/all` | **Vecteur d'attaque voulu.** N'importe quel utilisateur connecté voit les dons de tout le monde : montant, statut, 4 derniers chiffres de carte. C'est un contrôle d'accès cassé (type OWASP API1, *Broken Object Level Authorization*). |
| `/metrics` et `/docs` publics | Le WAF transmet tout à l'API : ces deux routes sont lisibles depuis l'extérieur. |

---

## 1. Prérequis

Sur son poste :

- **Tailscale** connecté au lab.
- **Sa clé SSH** autorisée sur la VM. Pour l'obtenir, envoyer sa clé publique à Mathieu.
- **`rsync`** installé sur son poste.
- **Le repo sur la bonne branche** :
  - tant que la PR du backend n'est pas mergée : `feature/thomas/backend` ;
  - une fois mergée : `main`.

> ⚠️ Tant que `feature/thomas/backend` n'est pas mergée, `main` contient l'**ancienne** API (`/transactions`, sans comptes). Ce guide décrit la nouvelle API : les commandes des sections 6 et 8 ne marcheront pas sur l'ancienne.

Vérifier sa branche et la mettre à jour :

```bash
git branch --show-current
git pull
```

Tester l'accès à la VM :

```bash
ssh ubuntu@192.168.137.1 'hostname && docker --version && docker network ls | grep resilience-net'
```

Ce qu'on doit voir : `host-resilience`, une version de Docker, et une ligne `resilience-net`.

> Pour s'éviter de retaper l'adresse, ajouter dans `~/.ssh/config` :
> ```
> Host resilience
>     HostName 192.168.137.1
>     User ubuntu
> ```
> On peut alors écrire `ssh resilience` à la place de `ssh ubuntu@192.168.137.1`.

---

## 2. Copier le code sur la VM

Depuis son poste, **à la racine du repo** :

```bash
rsync -av --delete \
  --exclude __pycache__ --exclude .venv --exclude venv --exclude .pytest_cache \
  backend/  ubuntu@192.168.137.1:/opt/resilience/app/services/api/

rsync -av --delete \
  --exclude node_modules --exclude dist \
  frontend/ ubuntu@192.168.137.1:/opt/resilience/app/services/frontend/
```

- Le `/` à la fin de `backend/` et `frontend/` est important : on copie le **contenu** du dossier, pas le dossier lui-même.
- `--delete` supprime sur la VM les fichiers qui n'existent plus dans le repo. Il ne touche qu'à `services/api/` et `services/frontend/`.

**En cas de `Permission denied`** (dossier `/opt/resilience` appartenant à root), ajouter `--rsync-path="sudo rsync"` aux deux commandes.

**Vérifier sur la VM :**

```bash
ssh ubuntu@192.168.137.1 'ls /opt/resilience/app/services/api /opt/resilience/app/services/frontend'
```

Ce qu'on doit voir :
- dans `api/` : `Dockerfile`, `alembic.ini`, `app/`, `migrations/`, `requirements.txt` ;
- dans `frontend/` : `Dockerfile`, `nginx.conf`, `package.json`, `src/`, etc.

> `/opt/resilience` est lui-même un dépôt git. Les fichiers copiés y apparaîtront dans `git status`. Ne pas les commiter dans ce dépôt sans en parler avec l'équipe qui le gère.

---

## 3. Activer les services dans le compose

Se connecter à la VM :

```bash
ssh ubuntu@192.168.137.1
cd /opt/resilience/app
cp compose.yaml compose.yaml.bak      # sauvegarde avant modification
nano compose.yaml
```

Décommenter les blocs `api` et `frontend`, et **laisser `auth` en commentaire** : l'authentification est intégrée à `api`, il n'y a pas de service `auth` séparé.

> ⚠️ **Nouveau : ajouter la ligne `JWT_SECRET_KEY` dans le bloc `api`.** Sans elle, l'API refuse de démarrer et redémarre en boucle.

La section `services:` doit ressembler à ceci, en respectant l'indentation de 2 espaces :

```yaml
services:
  db:
    # ... inchangé ...

  api:
    build: ./services/api
    container_name: app-api
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-payment}:${POSTGRES_PASSWORD:-change-me}@db:5432/${POSTGRES_DB:-payment}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}          # <-- ligne à ajouter (valeur dans .env, section 4)
    expose: ["8000"]       # /healthz et /metrics sur 8000, PAS de ports: (le WAF est l'entree)
    networks: [resilience-net]
    depends_on: [db]

  # auth:
  #   ... reste commenté (intégré à api) ...

  frontend:
    build: ./services/frontend
    container_name: app-frontend
    restart: unless-stopped
    expose: ["80"]
    networks: [resilience-net]
```

Vérifier que le fichier est valide :

```bash
docker compose config --services
```

Ce qu'on doit voir : `db`, `api`, `frontend`. Une erreur à cette étape vient presque toujours d'un problème d'indentation.

> **Variables facultatives**, à ajouter au même endroit si besoin :
> - `LOG_LEVEL: DEBUG` pour plus de logs (par défaut `INFO`) ;
> - `CORS_ORIGINS: http://...` seulement si un site **d'une autre origine** doit appeler l'API (par défaut : aucun).

---

## 4. Préparer le `.env` (clé JWT)

Le `.env` de `/opt/resilience/app` est lu par le compose. Il contient :
- `POSTGRES_USER`, `POSTGRES_PASSWORD` et `POSTGRES_DB`. Sans `.env`, ce sont les valeurs par défaut `payment` / `change-me` / `payment` ;
- **`JWT_SECRET_KEY`** : la clé qui signe les tokens de connexion. Elle doit faire **32 caractères minimum**.

```bash
cd /opt/resilience/app
cat .env 2>/dev/null || echo "pas encore de .env"

# Ajoute une clé JWT aléatoire, seulement s'il n'y en a pas déjà une
grep -q '^JWT_SECRET_KEY=' .env 2>/dev/null || echo "JWT_SECRET_KEY=$(openssl rand -base64 48)" >> .env
chmod 600 .env                          # le fichier contient des secrets

docker compose config | grep -c JWT_SECRET_KEY    # doit afficher 1
```

> ⚠️ **Ne jamais commiter ce `.env`**, ni copier la clé dans le repo.
>
> 🔑 **Changer la clé déconnecte tout le monde** : les tokens déjà distribués deviennent invalides (401). Ce n'est pas grave en dev.
>
> ⚠️ **Ne pas changer `POSTGRES_PASSWORD` si la base `db` tourne déjà.** Postgres ne lit ce mot de passe qu'à la toute première création de la base. Si on le change ensuite dans `.env`, l'API utilisera le nouveau, la base attendra l'ancien, et la connexion échouera. Voir [Dépannage](#12-dépannage).

---

## 5. Construire et lancer

Toujours dans `/opt/resilience/app` :

```bash
docker compose up -d --build api frontend
```

- **Ce que fait la commande** : elle construit les deux images, puis démarre `app-api` et `app-frontend`. La base `db` n'est pas redémarrée si elle tourne déjà.
- **Durée** : le premier build prend quelques minutes (images Python, Node et Nginx, plus `pip install` et `npm ci`). La VM doit avoir accès à Internet.
- **Au démarrage**, l'API applique d'abord les **migrations Alembic** (création des tables `users` et `donations`), puis lance le serveur.

Suivre le démarrage :

```bash
docker compose ps
docker logs -f app-api        # Ctrl+C pour quitter
```

Ce qu'on doit voir dans les logs de l'API. Les logs applicatifs sont en **JSON**, une ligne par événement :

```
INFO  [alembic.runtime.migration] Running upgrade  -> ce906222b065, users et donations    <- 1er démarrage uniquement
{"time": "...", "level": "INFO", "logger": "uvicorn.error", "message": "Application startup complete."}
```

> **Un redémarrage au tout premier lancement est normal** si la base démarre en même temps que l'API. La migration échoue alors avec une erreur `psycopg.OperationalError ... Connection refused`, Docker relance l'API, et ça passe. Ça ne doit pas se répéter.

`app-api` doit passer en `(healthy)` dans `docker compose ps` au bout d'une vingtaine de secondes.

---

## 6. Vérifier que tout marche

Depuis la VM, `http://localhost` passe **par le WAF**, exactement comme un vrai client. Pour viser directement un conteneur (sans le WAF), on utilise un petit conteneur `curl` branché sur `resilience-net`.

Copier-coller ce bloc dans un terminal sur la VM :

```bash
API=http://localhost
alias rcurl='docker run --rm --network resilience-net curlimages/curl:8.11.1 -s'

# 1. Santé de l'API, en direct (via le WAF, /healthz est intercepté par le WAF lui-même)
rcurl http://api:8000/healthz; echo
# 1 bis. Chemin complet WAF -> API, avec une route publique
curl -s $API/donations/presets; echo

# 2. Créer un compte (201, ou 409 s'il existe déjà)
curl -s -o /dev/null -w '%{http_code}\n' -X POST $API/auth/register \
  -H 'content-type: application/json' -d '{"email":"test@lab.fr","password":"SimPass-2026"}'

# 3. Se connecter et garder le token (formulaire, pas JSON)
TOKEN=$(curl -s -X POST $API/auth/login -d 'username=test@lab.fr&password=SimPass-2026' \
  | sed -E 's/.*"access_token":"([^"]+)".*/\1/')
echo "token : ${TOKEN:0:25}..."

# 4. Un don accepté, puis un don refusé
curl -s -X POST $API/donations -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"amount_cents":2500,"frequency":"once","card_number":"4242424242424242"}'; echo
curl -s -X POST $API/donations -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"amount_cents":2500,"frequency":"once","card_number":"4000000000000002"}'; echo

# 5. Sans token : refusé
curl -s -o /dev/null -w '%{http_code}\n' -X POST $API/donations -H 'content-type: application/json' \
  -d '{"amount_cents":2500,"card_number":"4242424242424242"}'

# 6. Metrics (directement sur l'API)
rcurl http://api:8000/metrics | grep '^donations_total'

# 7. Frontend, y compris une page interne de React Router
rcurl -o /dev/null -w '%{http_code}\n' http://app-frontend/
rcurl -o /dev/null -w '%{http_code}\n' http://app-frontend/don/paiement

# 8. Le WAF bloque une injection SQL
curl -s -o /dev/null -w '%{http_code}\n' -X POST $API/auth/login -d "username=admin' OR '1'='1&password=x"
```

| Étape | Résultat attendu |
|-------|------------------|
| 1. Santé (direct) | `{"status":"ok"}` |
| 1 bis. Via le WAF | `{"currency":"EUR","presets_cents":[500,1000,2500,5000],"min_cents":100,"max_cents":1000000}` |
| 2. Inscription | `201` (ou `409` au 2e essai) |
| 3. Connexion | `token : eyJhbGciOiJIUzI1NiIsInR5c...` |
| 4. Dons | `"status":"succeeded"` puis `"status":"failed","failure_reason":"card_declined"` |
| 5. Sans token | `401` |
| 6. Metrics | `donations_total{amount="25",status="succeeded"} 1.0` et `...status="failed"} 1.0` |
| 7. Frontend | `200` et `200` (et non `404`) |
| 8. Injection SQL | `403` (bloquée par le WAF) |

> Depuis son poste, les commandes 1 bis à 5 et 8 marchent aussi, en remplaçant `API=http://localhost` par `API=http://192.168.137.1`.
>
> ⚠️ **Ne pas tester la santé de l'API avec `curl http://localhost/healthz`** : c'est le WAF qui répond `OK`, même si l'API est arrêtée.

---

## 7. Vérifier le monitoring

Rien n'est à configurer : Prometheus a déjà un job `resilience-app` qui scrape `api:8000`, et Promtail récupère automatiquement les logs de tous les conteneurs, y compris ceux du WAF.

### Prometheus

Dans le navigateur (via Tailscale), aller sur **http://192.168.137.1:9090/targets** :
- `resilience-app` → `api:8000` doit être **UP** ;
- `auth:8000` sera **DOWN** : il n'y a pas de service `auth` séparé (l'authentification est dans `api`). C'est normal. Pour faire disparaître cette cible, l'équipe monitoring peut la retirer de `prometheus.yml`.

Ou bien en ligne de commande, sur la VM :

```bash
curl -s 'http://localhost:9090/api/v1/query?query=up{job="resilience-app"}'
```

Ce qu'on doit voir : `"instance":"api:8000"` avec la valeur `"1"`.

> La cible peut mettre jusqu'à 15 secondes (l'intervalle de scrape) avant de passer UP.

### Les metrics de l'API

| Metric | Labels | Contenu |
|--------|--------|---------|
| `donations_total` | `status` (`succeeded` / `failed`), `amount` (`5`, `10`, `25`, `50` ou `libre`) | Nombre de tentatives de don |
| `donations_amount_euros_total` | `amount` | Montant cumulé des dons **réussis**, en euros |
| `payment_processing_seconds` | (histogramme) | Durée du paiement simulé |
| `http_requests_total` | `handler`, `method`, `status` (`2xx`, `4xx`…) | Toutes les requêtes HTTP |
| `http_request_duration_highr_seconds` | (histogramme) | Latence HTTP globale |

### Requêtes Prometheus utiles dans Grafana

```promql
# Dons par seconde, réussis / échoués
sum by (status) (rate(donations_total[1m]))

# Taux de succès des paiements (0 à 1)
sum(rate(donations_total{status="succeeded"}[5m])) / sum(rate(donations_total[5m]))

# Euros collectés par minute
sum(increase(donations_amount_euros_total[1m]))

# Répartition presets / montant libre
sum by (amount) (rate(donations_total[5m]))

# Latence p95 du paiement simulé
histogram_quantile(0.95, sum by (le) (rate(payment_processing_seconds_bucket[5m])))

# Requêtes HTTP par route et par code (401 = token manquant ou expiré)
sum by (handler, status) (rate(http_requests_total{job="resilience-app"}[1m]))

# CPU et RAM des conteneurs de l'app (via cAdvisor)
rate(container_cpu_usage_seconds_total{name=~"app-.*"}[1m])
container_memory_usage_bytes{name=~"app-.*"}
```

### Loki

Les logs de l'API sont en JSON : dans Grafana, le filtre `| json` permet de filtrer sur chaque champ. Aller sur **http://192.168.137.1:3000**, puis **Explore** → source **Loki** :

```logql
# Tous les logs de l'API
{container="app-api"}

# Les dons traités, puis seulement les échecs
{container="app-api"} | json | message="donation_processed"
{container="app-api"} | json | message="donation_processed" | status="failed"

# Échecs de paiement par raison, sur 5 minutes
sum by (failure_reason) (count_over_time({container="app-api"} | json | message="donation_processed" | status="failed" [5m]))

# Connexions ratées (utile pour repérer une attaque par force brute)
{container="app-api"} | json | message="login_failed"

# Requêtes bloquées par le WAF (IP du client, URL, règle déclenchée)
{container="security-waf"} |= "transaction"
```

Ou bien en ligne de commande, sur la VM :

```bash
curl -sG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={container="app-api"} |= "donation_processed"' --data-urlencode 'limit=5'
```

> **L'IP réelle des clients** : l'API lit l'en-tête `X-Forwarded-For` envoyé par le WAF, et ses logs d'accès montrent donc l'IP du client, pas celle du WAF. Cet en-tête peut être falsifié par un client : **pour le SOC, l'IP qui fait foi est celle des logs du WAF.**

---

## 8. Simuler des donateurs

Ce script simule de vrais utilisateurs. Chacun :
1. crée un compte ;
2. se connecte **une seule fois** ;
3. enchaîne des dons, avec un mélange de cartes acceptées et refusées, et de montants prédéfinis ou libres.

Les utilisateurs tournent en parallèle et passent par le WAF.

> **Pourquoi une seule connexion par utilisateur ?** Le mot de passe est vérifié avec Argon2, volontairement coûteux en CPU et en mémoire. Se reconnecter avant chaque don saturerait la VM et fausserait les metrics.

**Installer le script** (une fois, sur la VM ou sur son poste) :

```bash
cat > ~/simu-dons.sh <<'EOF'
#!/usr/bin/env bash
# Simulation de donateurs : chaque utilisateur s'inscrit, se connecte UNE fois, puis enchaîne des dons.
# Usage : ./simu-dons.sh [nb_utilisateurs] [dons_par_utilisateur] [url]
set -u
USERS=${1:-5}
DONS=${2:-40}
API=${3:-http://localhost}          # via le WAF ; depuis son poste : http://192.168.137.1
PASS="SimPass-2026"
RUN=$(date +%s)                     # suffixe unique : chaque lancement crée de nouveaux comptes

simulate_user() {
  local email="sim-$RUN-$1@lab.fr" token card amount i
  curl -s -o /dev/null -X POST "$API/auth/register" -H 'content-type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$PASS\"}"
  token=$(curl -s -X POST "$API/auth/login" -d "username=$email&password=$PASS" \
    | sed -E 's/.*"access_token":"([^"]+)".*/\1/')
  for i in $(seq 1 "$DONS"); do
    case $((i % 10)) in
      0) card=4000000000000002 ;;   # refusée
      5) card=4000000000009995 ;;   # fonds insuffisants
      *) card=4242424242424242 ;;   # acceptée
    esac
    if [ $((i % 4)) -eq 0 ]; then amount=1234; else amount=2500; fi   # montant libre / preset 25 €
    curl -s -o /dev/null -w "%{http_code}\n" -X POST "$API/donations" \
      -H "Authorization: Bearer $token" -H 'content-type: application/json' \
      -d "{\"amount_cents\":$amount,\"frequency\":\"once\",\"card_number\":\"$card\"}"
  done
}

echo "Simulation : $USERS utilisateurs x $DONS dons sur $API"
for u in $(seq 1 "$USERS"); do simulate_user "$u" & done | sort | uniq -c
EOF
chmod +x ~/simu-dons.sh
```

**Lancer :**

```bash
~/simu-dons.sh                              # 5 utilisateurs x 40 dons, sur la VM
~/simu-dons.sh 20 100                       # plus de charge
~/simu-dons.sh 5 40 http://192.168.137.1    # depuis son poste, via Tailscale
```

**Ce qu'on doit voir :**

```
Simulation : 5 utilisateurs x 40 dons sur http://localhost
    200 201
```

- **Tous les dons répondent `201`**, même ceux refusés par la « banque ». Le refus se lit dans le `status` du don et dans les metrics.
- **Répartition** : environ 80 % de dons acceptés, 10 % `card_declined`, 10 % `insufficient_funds`, dont un quart en montant libre (12,34 €).
- **Durée** : environ 15 secondes avec les valeurs par défaut.

Les courbes de la section 7 doivent monter dans Grafana dans les 15 à 30 secondes.

> **Si des `401` apparaissent** : la connexion a échoué pour cet utilisateur. Vérifier `JWT_SECRET_KEY` (section 4) et les logs (`docker logs app-api`).
> **Si des `403` apparaissent** : le WAF a bloqué des requêtes. Voir `docker logs security-waf | grep -i "access denied"`.

---

## 9. Accéder au frontend depuis son navigateur

Le WAF envoie tout vers l'API : **le frontend n'est pas exposé**. Pour le voir en dev sans rien modifier, on passe par un **tunnel SSH vers l'IP interne du conteneur**.

**1. Sur la VM**, récupérer l'IP du conteneur :

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' app-frontend
# ex : 172.18.0.5
```

**2. Sur son poste**, ouvrir le tunnel en remplaçant l'IP :

```bash
ssh -N -L 8081:172.18.0.5:80 ubuntu@192.168.137.1
```

**3. Ouvrir http://localhost:8081.**

- On peut parcourir tout le site : accueil, `/don` → `/don/paiement` → `/don/confirmation`, et `/connexion`.
- Le front **n'est pas encore branché sur l'API** :
  - le parcours de don est simulé dans le navigateur (la carte `4000 0000 0000 0002` affiche un refus), sans rien envoyer au serveur ;
  - le formulaire `/connexion` ne fait encore rien.
- Pour générer des dons dans l'API, utiliser la [section 8](#8-simuler-des-donateurs).

> L'IP du conteneur peut changer à chaque redémarrage. Il faut alors refaire l'étape 1.
>
> Pour exposer le site sur `http://192.168.137.1/`, il faudrait que l'équipe SOC passe le `BACKEND` du WAF à `http://frontend:80`. Le Nginx du front transmet déjà `/api/*` à l'API. Les appels à l'API (et la section 8) passeraient alors par `/api/...`.

---

## 10. Mettre à jour

Après un changement de code dans le repo :

```bash
# 1. Sur son poste : se mettre à jour, puis renvoyer le code (mêmes commandes qu'à l'étape 2)
git pull
rsync -av --delete --exclude __pycache__ --exclude .venv --exclude venv --exclude .pytest_cache \
  backend/  ubuntu@192.168.137.1:/opt/resilience/app/services/api/
rsync -av --delete --exclude node_modules --exclude dist \
  frontend/ ubuntu@192.168.137.1:/opt/resilience/app/services/frontend/

# 2. Sur la VM : reconstruire et redémarrer seulement ce qui a changé
cd /opt/resilience/app
docker compose up -d --build api frontend
```

- **Ne mettre à jour que l'API** : `docker compose up -d --build api`.
- **Les données en base sont conservées** : elles sont dans le volume `db-data`, qui n'est pas touché.
- **Si une nouvelle migration Alembic** a été ajoutée dans `backend/migrations/versions/`, elle s'applique toute seule au redémarrage de l'API.
- **Pendant les quelques secondes du redémarrage**, le WAF renvoie `502` : c'est normal.

> Pour ne plus avoir à copier les fichiers à chaque modif, passer à [`deploimentAuto.md`](deploimentAuto.md).

---

## 11. Arrêter ou revenir en arrière

### Arrêter l'app sans toucher à la base

```bash
cd /opt/resilience/app
docker compose stop api frontend      # arrête les conteneurs
docker compose start api frontend     # les relance
```

> ⛔ **Ne jamais lancer `docker compose down -v`** dans `/opt/resilience/app`.
> Le `-v` supprime le volume `db-data`, c'est-à-dire **toute la base** (comptes et dons).
> Un `docker compose down` sans `-v` arrête aussi `db`, ce qui coupe la base pour tout le monde. Préférer `stop api frontend`.

### Revenir à la version précédente

Avant une mise à jour risquée, garder une copie des images actuelles :

```bash
docker tag resilience-app-api:latest      resilience-app-api:prev
docker tag resilience-app-frontend:latest resilience-app-frontend:prev
```

Pour y revenir en cas de problème :

```bash
docker tag resilience-app-api:prev      resilience-app-api:latest
docker tag resilience-app-frontend:prev resilience-app-frontend:latest
docker compose up -d --no-build api frontend
```

> ⚠️ Revenir à une ancienne image **ne défait pas les migrations** déjà appliquées à la base. Avec une seule migration, ce n'est pas un problème. Plus tard, une migration qui supprime ou renomme une colonne pourra empêcher l'ancienne image de fonctionner.

L'autre option : revenir au commit précédent dans le repo sur son poste, puis refaire l'étape 10.

### Tout retirer

```bash
cd /opt/resilience/app
docker compose rm -sf api frontend     # supprime les conteneurs (pas la base)
cp compose.yaml.bak compose.yaml       # remet le compose d'origine
```

---

## 12. Dépannage

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| `app-api` redémarre en boucle, logs : `jwt_secret_key Field required` | La ligne `JWT_SECRET_KEY` manque dans le bloc `api` du compose | Ajouter la ligne (section 3), puis `docker compose up -d api` |
| `app-api` redémarre en boucle, logs : `JWT_SECRET_KEY doit faire au moins 32 caractères` | Clé absente ou trop courte dans `.env` | Section 4, puis `docker compose up -d api` |
| Au 1er démarrage : `psycopg.OperationalError ... Connection refused`, puis l'API repart | La migration a démarré avant la base | Normal, une seule fois. Si ça boucle : `docker compose ps db` et `docker logs app-db` |
| `app-api` redémarre en boucle, logs : `password authentication failed` | Le mot de passe dans `.env` ne correspond pas à celui de la base | Remettre l'ancien mot de passe dans `.env`, **ou** changer celui de la base : `docker exec -it app-db psql -U payment -c "ALTER USER payment PASSWORD 'nouveau';"` |
| `/healthz` renvoie `500`, ou `app-api` reste `unhealthy` | L'API tourne mais la base est injoignable | Vérifier `app-db` (voir les lignes ci-dessus) |
| `/transactions` renvoie `404` | Ancienne API : les transactions sont devenues des dons | Utiliser `/donations` avec un token (sections 0 et 6) |
| `401 Token invalide ou expiré` | Token absent, expiré (60 min) ou clé JWT changée depuis | Se reconnecter (`/auth/login`) pour obtenir un nouveau token |
| `/auth/login` renvoie `422` | Identifiants envoyés en JSON | Le login attend un **formulaire** : `-d 'username=...&password=...'` |
| `http://localhost/...` renvoie `502` | L'API est arrêtée ou en train de redémarrer | `docker compose ps api`. Normal quelques secondes pendant un redéploiement |
| `curl http://localhost/healthz` répond `OK` alors que l'API est en panne | Le WAF répond lui-même sur `/healthz` (sa propre sonde de santé) | Tester l'API en direct : `rcurl http://api:8000/healthz` (section 6) |
| Le WAF ne redémarre plus, logs : `host not found in upstream "api"` | Le WAF a redémarré alors que `app-api` était arrêté | Relancer `app-api`, puis `docker restart security-waf` |
| Une requête légitime reçoit `403` | Faux positif du WAF | `docker logs security-waf \| grep -i "access denied"` donne la règle. Voir avec l'équipe SOC |
| Prometheus : `api:8000` **DOWN** | `app-api` arrêté, ou pas sur `resilience-net` | `docker inspect app-api -f '{{json .NetworkSettings.Networks}}'` doit contenir `resilience-net` |
| `rcurl http://app-frontend/api/...` renvoie `502` | Nginx ne joint pas l'API | Vérifier que `app-api` tourne : `docker compose ps api` |
| `/don/paiement` renvoie `404` | Ancienne image du front, sans la conf Nginx | `docker compose up -d --build frontend` |
| Une URL inconnue du front affiche une page blanche | Le front n'a pas encore de page 404 | Pas un problème de déploiement |
| Rien dans Loki pour `app-api` | Fenêtre de temps trop courte dans Grafana, ou Promtail en erreur | Élargir la période à « Last 1 hour », et `docker logs monitoring-promtail \| tail` |
| Le build du frontend échoue à `npm ci` | Pas d'accès Internet, ou `package-lock.json` absent ou désynchronisé | Vérifier que `services/frontend/package-lock.json` existe, et tester `curl -I https://registry.npmjs.org` |
| `docker compose config` renvoie une erreur YAML | Indentation cassée en décommentant | 2 espaces par niveau, et `api:` / `frontend:` alignés avec `db:` |
| `network resilience-net declared as external, but could not be found` | Le réseau partagé n'existe pas | `docker network create resilience-net`, puis prévenir l'équipe infra |
| `Permission denied` pendant le `rsync` | `/opt/resilience` appartient à root | Ajouter `--rsync-path="sudo rsync"` |

### Commandes de diagnostic

```bash
cd /opt/resilience/app
docker compose ps                                   # état des conteneurs
docker logs --tail 50 app-api                       # derniers logs de l'API
docker logs --tail 50 app-frontend                  # derniers logs de Nginx
docker logs --tail 50 security-waf                  # derniers logs du WAF
docker stats --no-stream app-api app-frontend app-db   # CPU / RAM
docker exec app-db psql -U payment -c "SELECT status, count(*) FROM donations GROUP BY status;"   # dons en base
docker network inspect resilience-net --format '{{range .Containers}}{{.Name}} {{end}}'
```

---

## Récapitulatif rapide

```bash
# Poste : bonne branche (feature/thomas/backend avant le merge, main après), puis envoyer le code
git pull
rsync -av --delete --exclude __pycache__ --exclude .venv --exclude venv backend/  ubuntu@192.168.137.1:/opt/resilience/app/services/api/
rsync -av --delete --exclude node_modules --exclude dist frontend/ ubuntu@192.168.137.1:/opt/resilience/app/services/frontend/

# VM (une seule fois) : décommenter api + frontend, ajouter JWT_SECRET_KEY au bloc api, générer la clé
cd /opt/resilience/app
grep -q '^JWT_SECRET_KEY=' .env 2>/dev/null || echo "JWT_SECRET_KEY=$(openssl rand -base64 48)" >> .env

# VM : lancer
docker compose up -d --build api frontend

# VM : vérifier
docker run --rm --network resilience-net curlimages/curl:8.11.1 -s http://api:8000/healthz   # santé de l'API, en direct
curl -s http://localhost/donations/presets                                                   # chemin WAF -> API
curl -s 'http://localhost:9090/api/v1/query?query=up{job="resilience-app"}'
~/simu-dons.sh
```
