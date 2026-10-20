# Correctifs appliqués avant le déploiement en dev

**Objectif** : déployer l'application sur la VM `host-resilience` (Proxmox, VMID 5010), y simuler des utilisateurs avec un script, et récupérer les métriques dans Prometheus et les logs dans Loki.

**Référence** : les contrats d'intégration de `espace-de-travail-devs.md`.

**Périmètre** : uniquement les problèmes qui bloquaient ce déploiement. Les autres points (CI, service `auth`, logs JSON, versions figées) sont listés à la fin.

---

## Résumé

| # | Problème | Correctif | Fichiers |
|---|----------|-----------|----------|
| 1 | Pas de route `/metrics` | Ajout de l'export Prometheus | `backend/app/main.py`, `backend/requirements.txt` |
| 2 | Route `/health` au lieu de `/healthz` | Renommée, et renvoie 503 si la base est KO | `backend/app/main.py`, `backend/Dockerfile` |
| 3 | Aucune route métier | Ajout de `POST/GET /transactions` avec sa table en base | `backend/app/main.py` |
| 4 | Le compose ne respecte pas le contrat du host | Plus de Postgres dans le compose, `expose:` seulement, réseau `resilience-net` | `docker-compose.yml`, `docker-compose.local.yml`, `.env.example` |
| 5 | Frontend impossible à déployer et sans lien avec l'API | Dockerfile + Nginx sur le port 80, bouton de don relié à l'API | `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore`, `DonationForm.tsx` |
| 6 | L'URL de base du compose du host n'indique pas de driver, et l'API peut démarrer avant la base | Driver `psycopg` 3 forcé, et l'API réessaie la connexion au démarrage | `backend/app/main.py` |

---

## 1. Ajout de `GET /metrics` (format Prometheus)

**Le problème**
Le contrat demande `GET /metrics` sur l'API, et cette route n'existait pas. Prometheus ne pouvait donc rien récupérer sur l'application.

**Le correctif**
- Ajout des dépendances `prometheus-fastapi-instrumentator` et `prometheus-client`.
- Branchement de l'instrumentation sur l'application FastAPI. Elle expose automatiquement :
  - `http_requests_total{handler, method, status}` : nombre de requêtes par route et par code de retour (2xx, 4xx, 5xx) ;
  - `http_request_duration_seconds` : la latence par route, sous forme d'histogramme.
- Ajout d'une métrique métier `transactions_total{status}` : le nombre de transactions traitées.
- `/metrics` et `/healthz` ne sont pas comptés dans ces métriques. Sinon, les appels réguliers de Prometheus et du healthcheck fausseraient les chiffres.

**Pourquoi**
C'est la condition pour que Prometheus scrape l'API et que les dashboards Grafana montrent le trafic que générera le script de simulation.

---

## 2. Renommage `/health` → `/healthz`, avec une vraie réponse en cas de panne

**Le problème**
- Le contrat impose `GET /healthz`, alors que l'API exposait `/health`.
- Quand la base était injoignable, la route plantait (erreur 500) au lieu de signaler proprement le problème.

**Le correctif**
- La route s'appelle maintenant `/healthz`.
- Elle renvoie `200 {"status":"ok"}` si la base répond, et `503 {"status":"error"}` sinon.
- Ajout d'un `HEALTHCHECK` dans `backend/Dockerfile`. Docker affiche ainsi l'état `healthy` ou `unhealthy` du conteneur.

**Pourquoi**
- La supervision et le futur WAF s'appuient sur `/healthz` pour savoir si le service est en vie.
- Un 503 explicite permet de distinguer « base en panne » de « bug de l'API ». C'est utile pour le projet résilience, dont le but est de prouver la reprise après incident.

---

## 3. Ajout d'une route métier : les transactions

**Le problème**
L'API n'avait aucune route métier. Un script de simulation n'aurait pu appeler que le healthcheck, ce qui ne donne ni métriques ni logs intéressants. En plus, le contrat demande que l'API « initie et traite une transaction fictive de bout en bout ».

**Le correctif**
- Nouvelle table `transactions` : `id`, `amount`, `currency`, `frequency`, `status`, `created_at`, `processed_at`. Elle est créée automatiquement au démarrage de l'API.
- `POST /transactions` :
  - corps attendu : `{"amount": 25, "frequency": "monthly"}` ;
  - la transaction est enregistrée avec le statut `pending`, puis traitée et passée en `completed` ;
  - la réponse est un code `201` avec la transaction ;
  - un montant invalide (≤ 0 ou > 10 000) renvoie `422`.
- `GET /transactions?limit=20` : liste les dernières transactions.
- `GET /transactions/{id}` : renvoie une transaction précise, ou `404` si elle n'existe pas.
- Chaque étape écrit une ligne de log sur stdout, par exemple `transaction initiee id=...` puis `transaction traitee id=... status=completed`.

**Pourquoi**
- Le script de simulation dispose de vraies routes à appeler, qui écrivent en base. Cela produit des métriques de latence et de volume réalistes.
- Les logs sur stdout sont récupérés par Promtail et envoyés dans Loki, sans configuration supplémentaire.
- La transaction de bout en bout est la « preuve de reprise » demandée par le contrat.
- Aucune donnée bancaire réelle n'est manipulée : seulement un montant, une devise (EUR) et une fréquence.

> Note : il n'y a pas encore de migrations Alembic. La table est créée au démarrage, ce qui suffit pour un environnement de dev. Pour la suite, il faudra passer à Alembic.

---

## 4. Le `docker-compose.yml` aligné sur le contrat du host

**Le problème**
L'ancien compose posait trois problèmes :
- **Une deuxième base Postgres** : la base `db` tourne déjà sur le host via `/opt/resilience/app/compose.yaml`. Il y aurait eu deux bases, et un conflit sur le port 5432.
- **Des ports publiés** (`5432:5432`, `8000:8000`) : le contrat interdit `ports:`, car c'est le WAF qui doit être le seul point d'entrée.
- **Pas de réseau `resilience-net`** : Prometheus, qui est sur ce réseau, n'aurait pas pu joindre l'API pour la scraper.

**Le correctif**
- `docker-compose.yml`, utilisé sur le host :
  - plus de service `db` : on utilise celle du host via `POSTGRES_HOST` (`db` par défaut) ;
  - `expose:` seulement (8000 pour l'API, 80 pour le front), aucun `ports:` ;
  - `api` et `frontend` rejoignent le réseau externe `resilience-net` ;
  - suppression de `--reload` et du montage du code en volume : l'image tourne telle quelle, ce qui est plus stable pour mesurer les performances ;
  - suppression de `container_name` : ça évite les collisions de noms avec les autres conteneurs du host.
- `docker-compose.local.yml`, nouveau, pour le dev sur le poste uniquement : il rajoute une base Postgres locale, publie les ports (API sur 8000, front sur 8080, base sur 5432) et réactive le rechargement auto du code.
- `.env.example` est pré-rempli avec les valeurs de la doc : `payment` / `payment` / `change-me`, plus `POSTGRES_HOST=db`.

**Pourquoi**
- On respecte le contrat, et on ne marche pas sur les services déjà en place.
- Sans le réseau `resilience-net`, aucune métrique applicative n'arriverait dans Prometheus.
- Le fichier local évite aux devs de perdre leur environnement de travail.

**Utilisation en local sur son poste**

```bash
docker network create resilience-net    # une seule fois
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

> Sur le host, on n'utilise **pas** ce `docker-compose.yml` : on passe par le `compose.yaml` déjà en place dans `/opt/resilience/app` (voir la section « Déploiement sur host-resilience »).

---

## 5. Frontend déployable, et relié à l'API

**Le problème**
- Pas de Dockerfile : le frontend ne pouvait pas tourner sur le host. Le contrat demande le port 80.
- Le bouton de don pointait vers `/don`, une page qui n'existe pas, et n'appelait jamais l'API.

**Le correctif**
- `frontend/Dockerfile`, construit en deux étapes :
  1. une image Node 22 qui installe les dépendances (`npm ci`) et fait le build (`npm run build`) ;
  2. une image Nginx qui sert uniquement le résultat du build (`dist/`) sur le port 80.
- `frontend/nginx.conf` :
  - sert les fichiers du site ;
  - **`/api/*` est transmis à `http://api:8000/*`** (explications ci-dessous) ;
  - `resolver 127.0.0.11` : Nginx cherche l'adresse de l'API à chaque requête. Il ne plante donc pas au démarrage si l'API n'est pas encore lancée ;
  - `try_files ... /index.html` : si des routes React sont ajoutées plus tard, un rechargement de page ne donnera pas de 404.
- `frontend/.dockerignore` : exclut `node_modules` et `dist` du contexte de build.
- `DonationForm.tsx` : le bouton « Continuer » envoie `POST /api/transactions` avec le montant et la fréquence, puis affiche un message de succès ou d'erreur.

**Pourquoi la conf Nginx transmet `/api`**
Le code React tourne dans le navigateur de l'utilisateur, pas dans Docker :
- l'API n'a aucun port publié (contrat), donc le navigateur ne peut pas la joindre directement ;
- le nom `api` n'existe que dans le réseau Docker `resilience-net`, et le navigateur ne sait pas le résoudre.

Le front appelle donc `/api/...` sur son propre domaine, et Nginx, qui est dans le réseau Docker, transmet à l'API. Avantage en plus : front et API ont la même origine, donc pas de config CORS à gérer.

> Si le WAF est configuré plus tard pour envoyer lui-même `/api/*` vers l'API, ce bloc de la conf Nginx pourra être retiré.

**Pas de conflit avec la VM `104 Nginx`**
- C'est une VM à part, avec sa propre IP. Le Nginx du front tourne dans un conteneur sur `host-resilience`.
- De toute façon, le conteneur ne publie aucun port : le port 80 de la VM `host-resilience` reste libre.

---

## 6. Compatibilité avec le `compose.yaml` du host

Une fois le `/opt/resilience/app/compose.yaml` du host connu, deux ajustements ont été faits dans `backend/app/main.py`.

**a) L'URL de la base**
- Le compose du host fournit `DATABASE_URL: postgresql://...`, sans préciser le driver.
- Avec SQLAlchemy 2.0, cette URL choisit le driver `psycopg2`, qui n'est pas installé : l'API plante au démarrage. Avec SQLAlchemy 2.1 (la version installée aujourd'hui), ça marche, car `psycopg` 3 est le driver par défaut.
- Comme les versions ne sont pas figées dans `requirements.txt`, l'API convertit maintenant `postgresql://` en `postgresql+psycopg://`. Ça marche quelle que soit la version, et le compose du host n'a pas à être modifié.

**b) L'API attend la base au démarrage**
- Le compose du host déclare `depends_on: [db]` sans condition de santé. Docker démarre donc l'API dès que le conteneur de la base est lancé, même si Postgres n'accepte pas encore de connexions.
- Au démarrage, l'API réessaie maintenant la connexion toutes les 2 secondes, jusqu'à 30 fois (1 minute), au lieu de planter. Chaque essai raté écrit une ligne `base pas encore prete (essai N/30)` dans les logs.
- Ce cas s'est produit pendant le test : l'API a attendu un essai, puis a démarré normalement.

---

## Déploiement sur host-resilience

Le host attend le code dans `/opt/resilience/app/services/<nom>/` et fournit un `compose.yaml` avec les services `api`, `auth` et `frontend` en commentaire. On suit ce chemin, plutôt que notre `docker-compose.yml`, pour garder les noms de conteneurs prévus par l'infra (`app-api`, `app-frontend`). C'est sûrement sous ces noms que la supervision les attend.

**Correspondance des dossiers**

| Dans ce repo | Sur le host |
|--------------|-------------|
| `backend/` | `/opt/resilience/app/services/api/` |
| `frontend/` | `/opt/resilience/app/services/frontend/` |

**Étapes**

```bash
# Depuis son poste, à la racine du repo
rsync -av --exclude node_modules --exclude dist --exclude __pycache__ \
  backend/  ubuntu@host-resilience:/opt/resilience/app/services/api/
rsync -av --exclude node_modules --exclude dist \
  frontend/ ubuntu@host-resilience:/opt/resilience/app/services/frontend/

# Sur le host
cd /opt/resilience/app
# 1. Dans compose.yaml, décommenter les blocs `api` et `frontend` (laisser `auth` commenté)
# 2. Mettre le vrai mot de passe dans .env (POSTGRES_PASSWORD), sinon le défaut est `change-me`
docker compose up -d --build api frontend
docker compose ps
```

**Vérification depuis le host** (aucun port n'est publié, donc on teste depuis un conteneur sur `resilience-net`) :

```bash
docker run --rm --network resilience-net curlimages/curl:8.11.1 -s http://app-api:8000/healthz
docker run --rm --network resilience-net curlimages/curl:8.11.1 -s http://app-api:8000/metrics | grep transactions_total
docker logs -f app-api
```

---

## Tests effectués en local

La stack complète a été lancée avec `docker-compose.yml` + `docker-compose.local.yml` :

| Test | Résultat |
|------|----------|
| Build des images `api` (Python 3.15) et `frontend` (TypeScript + Vite) | OK |
| `GET /healthz` avec la base démarrée | `200` |
| `GET /healthz` avec la base arrêtée | `503`, puis `200` au redémarrage de la base |
| `POST /transactions` en direct sur l'API | `201`, statut `completed` |
| `POST /api/transactions` en passant par le Nginx du front | `201` |
| `POST /transactions` avec un montant négatif | `422` |
| `GET /transactions` et `GET /transactions/{id}` inexistant | `200` et `404` |
| `GET /` sur le frontend | `200` |
| `GET /metrics` | `transactions_total`, `http_requests_total` et `http_request_duration_seconds` présents |
| Logs du conteneur API | lignes `transaction initiee` / `transaction traitee` sur stdout |
| `docker compose config` sans le fichier local | aucun port publié, réseau `resilience-net` externe |
| **Simulation du host** : même arborescence `services/api` et `services/frontend`, `compose.yaml` du host décommenté tel quel | les 3 conteneurs démarrent, `app-api` est `healthy` |
| L'API démarre avant la base (simulation du host) | 1 essai raté, puis démarrage normal |
| Appels depuis un conteneur sur `resilience-net` vers `api`, `app-api`, `frontend` et `app-frontend` | tous joignables (`200` / `201`) |
| `POST http://app-frontend/api/transactions` | `201`, Nginx transmet bien à l'API |

---

## À vérifier sur le host avant de lancer

1. **Le nom de la base** : confirmé. Le compose du host déclare le service `db` (conteneur `app-db`) sur `resilience-net`, et l'URL de l'API pointe vers `db:5432`.
2. **La cible de Prometheus** : confirmé. `monitoring/prometheus/prometheus.yml` contient déjà le job `resilience-app`, qui scrape `api:8000` et `auth:8000` toutes les 15 s avec le label `stack=resilience`. Prometheus est branché sur `resilience-net`, donc rien à modifier côté monitoring.
   - La cible `auth:8000` sera **DOWN** tant que le service `auth` n'existe pas. C'est normal.
   - Pour vérifier : http://<host>:9090/targets doit afficher `api:8000` en **UP**.
   - **Logs** : Promtail lit les logs de tous les conteneurs Docker et leur ajoute le label `container`. Dans Grafana, les logs de l'API se trouvent avec `{container="app-api"}`.

3. **Pas de doublon de noms** : aucun autre conteneur ne doit s'appeler `api` ou `frontend` sur `resilience-net`. Et il ne faut pas lancer en plus notre `docker-compose.yml` sur le host, sinon il y aurait deux API.

   ```bash
   docker ps --format '{{.Names}}\t{{.Ports}}'
   docker network inspect resilience-net --format '{{range .Containers}}{{.Name}} {{end}}'
   ```

4. **Le script de simulation** : aucun port n'est publié, donc il doit tourner sur le réseau `resilience-net` (par exemple `docker run --network resilience-net ...` vers `http://api:8000`). L'autre option est de passer par le WAF une fois en place.

---

## Requêtes utiles dans Grafana

**Prometheus**

```promql
# L'API est-elle scrapée ? (1 = oui)
up{job="resilience-app"}

# Requêtes par seconde, par route et par code de retour
sum by (handler, status) (rate(http_requests_total{job="resilience-app"}[1m]))

# Transactions traitées par seconde
sum by (status) (rate(transactions_total[1m]))

# Latence p95 globale (histogramme précis, sans détail par route)
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_highr_seconds_bucket{job="resilience-app"}[5m])))
```

**Loki**

```logql
{container="app-api"}
{container="app-api"} |= "transaction traitee"
{container="app-api"} |= "POST /transactions" |= " 422 "
{container="app-frontend"}
```

---

## Restant à faire (non bloquant)

- **CI** : `npm ci` et `npm test` sont lancés à la racine, où il n'y a pas de `package.json`, et le script `test` n'existe pas. La règle de branche attend `feature/`, alors que l'équipe utilise `feat/`.
- **Service `auth`** (JWT) : pas encore implémenté.
- **Versions des dépendances Python** : non figées dans `requirements.txt`.
- **Logs au format JSON** : plus faciles à filtrer dans Loki et Grafana.
- **Migrations Alembic** : à mettre en place à la place du `create_all` au démarrage.
- **Identifiants du lab** : ils sont présents dans `espace-de-travail-devs.md`, alors que la doc dit de ne pas les committer.
