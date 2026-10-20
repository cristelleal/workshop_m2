# Guide de résolution des conflits — `feature/thomas/backend` → `main`

> Généré le 2026-10-20 · Base commune (merge-base) : `0f3b62c` « init infrastructure »

## Contexte

La branche `feature/thomas/backend` **restructure le backend** : passage d'un `main.py`
monolithique (modèle `Transaction` unique) vers une architecture modulaire
(`core/`, `routes/`, `db`, `models`, `schemas`, `service/`) avec **authentification JWT**,
**migrations Alembic** et un domaine **« dons »** (`donations`) au lieu de `transactions`.

Les conflits viennent du fait que `main` et la branche ont fait évoluer les **mêmes fichiers d'infra**
en parallèle, chacun pour un objectif différent (déploiement lab vs. dev local).

## §0. Divergence des branches (à lire en premier)

Les branches ont **divergé** : `main` a avancé de **14 commits** que `feature/thomas/backend` n'a pas
(tout un **frontend React/Vite**, fixes backend `Fix route monitoring` / `Fix global front/back`,
favicon, wording, `.env.example`, et un **`docker-compose.local.yml` déjà présent**). Ta branche n'a
qu'**1 commit** d'avance (`ajout du backend`).

Conséquences :
- Les fichiers `frontend/…`, `.vscode/…`, `docker-compose.local.yml`, `correctif.md` apparaissent
  « supprimés » dans `git diff main` **uniquement parce qu'ils n'existent pas encore sur ta branche**.
  **Ils ne seront pas perdus** : `git merge main` les ramènera (aucun conflit, ajouts purs).
- La liste des **vrais conflits reste limitée à 4 fichiers** (§1–§4) — confirmée par `git merge-tree`
  qui calcule la fusion à 3 points (sommet main + sommet branche + ancêtre commun).
- ⚠️ Faire le merge **dans le sens `main` → ta branche** (ou rebase) pour récupérer le frontend et les
  fixes de `main` avant d'ouvrir/mettre à jour la PR.

## Vue d'ensemble

| Fichier | Statut | Conflit réel ? | Action recommandée |
|---|---|---|---|
| 17 fichiers (`core/`, `routes/`, `models.py`, `schemas.py`, `migrations/`, `alembic.ini`, …) | Ajoutés par la branche | ❌ Non | Garder tels quels |
| `.gitignore` | Modifié 2 côtés | ❌ Fusion auto | Garder l'union (ajoute `venv`) |
| `backend/Dockerfile` | Modifié 2 côtés | ✅ Oui | **Fusionner** (voir §1) |
| `backend/app/main.py` | Modifié 2 côtés | ✅ Oui | **Prendre la branche** + réintégrer le healthz résilient (§2) |
| `backend/requirements.txt` | Modifié 2 côtés | ✅ Oui | **Union des dépendances** (§3) |
| `docker-compose.yml` | Modifié 2 côtés | ✅ Oui | **Séparer** prod vs local (§4) |

---

## 1. `backend/Dockerfile`

**Nature du conflit :** la branche ajoute la copie d'Alembic + lance les migrations au démarrage
et supprime le `HEALTHCHECK` ; `main` conserve le `HEALTHCHECK` et un `CMD` simple.

**Recommandation : fusionner** — garder le `HEALTHCHECK` de `main` **et** le `CMD` de la branche
(qui applique les migrations avant de lancer uvicorn).

```dockerfile
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

EXPOSE 8000

# Conservé depuis main : sonde de santé conteneur
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)" || exit 1

# Depuis la branche : migrations Alembic puis uvicorn derrière le WAF/proxy
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*"]
```

> ⚠️ Le `HEALTHCHECK` interroge `/healthz`. Vérifier que l'endpoint existe toujours (il existe dans les deux versions) — voir §2.

---

## 2. `backend/app/main.py`

**Nature du conflit :** réécriture complète. `main` = monolithe `Transaction` ;
la branche = app modulaire (`routes.auth`, `routes.donations`, `core.config`, `db`, CORS).

> 💡 **Clé de lecture :** les routes `/transactions` de `main` **ne sont pas supprimées sans contrepartie**.
> Elles correspondent aux routes `/donations` de ta branche (`routes/donations.py`) : c'est **la même
> fonctionnalité** (créer une contribution, la passer de `pending` à un statut final, la lister, la lire
> par id), simplement **réécrite et enrichie**. Il ne s'agit donc pas d'une perte mais d'une évolution.

### Correspondance `transactions` (main) → `donations` (branche)

| Endpoint `main` | Endpoint branche | Évolution |
|---|---|---|
| `POST /transactions` | `POST /donations` | **Auth requise** + **vrai paiement simulé** (carte de test, `failure_reason`) au lieu d'un passage auto en `completed` |
| `GET /transactions?limit=` | `GET /donations/me?limit=` | Liste **limitée aux dons de l'utilisateur connecté** (gain de sécurité) ; **pagination `?limit=` (1–100) conservée** |
| `GET /transactions/{id}` | `GET /donations/{id}` | **404 aussi si le don n'appartient pas à l'utilisateur** (on ne révèle pas son existence) |
| — | `GET /donations/presets` | **Nouveau** : montants prédéfinis (5/10/25/50 €) + bornes, public |

### Correspondance des champs (modèle + schémas)

| `Transaction` (main) | `Donation` (branche) | Remarque |
|---|---|---|
| `id: str` (uuid texte) | `id: UUID` | Type UUID natif (impossible de deviner les dons des autres) |
| `amount: Decimal` (€, 2 déc., ≤ 10000) | `amount_cents: int` (100 → 1 000 000) | Passage en **centimes** |
| `currency` (Literal `EUR`) | `currency` (défaut `EUR`) | Équivalent |
| `frequency` (`once`/`monthly`) | `frequency` (enum `DonationFrequency`) | ✅ **Réintégré** |
| `status` (`pending`→`completed`) | `status` (`pending`→`succeeded`/`failed`) | Enum + échec possible |
| `processed_at` | `processed_at` | ✅ **Réintégré** (renseigné après paiement) |
| — | `user_id` (FK `users`) | Nouveau : propriété du don |
| — | `is_custom`, `card_last4`, `failure_reason` | Nouveaux (montant libre, paiement) |

**Recommandation : prendre la version de la branche** (`feature/thomas/backend`) — c'est la nouvelle
architecture cible, et `/donations` **remplace fonctionnellement** `/transactions`. Aucun endpoint n'est
perdu : chaque route `transactions` a son équivalent `donations` ci-dessus.

**✅ Éléments de `main` réintégrés dans l'archi `donations`** (décision : on ne les perd pas) :
- **`frequency` (don ponctuel vs mensuel)** : réintroduit via l'enum `DonationFrequency` (`once`/`monthly`)
  dans `models.py`, `schemas.py` (`DonationCreate` + `DonationOut`) et posé à la création dans la route.
- **`processed_at`** : colonne nullable réajoutée au modèle `Donation`, renseignée après le paiement
  (`datetime.now(timezone.utc)`) et exposée dans `DonationOut`.
- **Pagination `?limit=`** : paramètre `limit: int = Query(default=20, ge=1, le=100)` rajouté à
  `GET /donations/me` (même borne 1–100 que `main`).
- La **migration** `ce906222b065_users_et_donations.py` a été mise à jour en conséquence
  (colonnes `frequency` + enum `donation_frequency`, et `processed_at`).

> ✅ **À l'inverse, ce n'est PAS une perte :** `GET /transactions` listait *toutes* les transactions,
> `GET /donations/me` ne liste que celles de l'utilisateur connecté. C'est un **choix de sécurité
> assumé** (isolation des données), pas une régression.

**⚠️ Deux points à ne pas perdre de `main` :**

1. **Le `/healthz` résilient.** La version `main` renvoie un `503` propre si la base est injoignable ;
   la version branche laisse remonter l'exception (500). Le `HEALTHCHECK` du Dockerfile (§1)
   fonctionne mieux avec la version résiliente. Suggestion :

   ```python
   from fastapi.responses import JSONResponse

   @app.get("/healthz", include_in_schema=False)
   def healthz():
       try:
           with engine.connect() as conn:
               conn.execute(text("SELECT 1"))
       except Exception:
           return JSONResponse(status_code=503, content={"status": "error", "db": "unreachable"})
       return {"status": "ok"}
   ```

2. **La logique de retry DB au démarrage** (`lifespan` + `DB_STARTUP_RETRIES`). Dans la branche,
   Alembic (`alembic upgrade head` du Dockerfile) et le `depends_on: service_healthy` du compose
   remplacent ce besoin — **mais seulement en local**. En déploiement lab (compose de `main`,
   `depends_on` sans healthcheck), la base peut démarrer après l'API : à vérifier que les migrations
   Alembic gèrent bien le retry, sinon réintroduire une attente.

Le reste de la version branche est à conserver tel quel (CORS, routers, Instrumentator).

---

## 3. `backend/requirements.txt`

**Nature du conflit :** la branche ajoute les dépendances d'auth et retire `python-dotenv`
et `prometheus-client`.

**Recommandation : union des dépendances.** Attention à deux retraits :

- `prometheus-client` : utilisé par le `Counter` de l'ancien `main.py`. Si on prend le nouveau
  `main.py` (§2), il n'est plus importé directement → suppression OK **sauf** si `service/payment.py`
  ou une route définit des métriques custom. À vérifier (`grep -r prometheus_client backend/app`).
- `python-dotenv` : vérifier que `core/config.py` (pydantic-settings) charge bien le `.env` sans lui.

Liste fusionnée proposée :

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg[binary]
pydantic-settings
alembic
pyjwt
pwdlib[argon2]
python-multipart
email-validator
prometheus-fastapi-instrumentator
prometheus-client        # garder si des métriques custom subsistent, sinon retirer
```

---

## 4. `docker-compose.yml`

> ⚠️ **Mise à jour importante :** `main` a divergé de 14 commits (voir §0) et possède **déjà** un
> `docker-compose.local.yml` propre, qui gère la base `db`, les ports et le `--reload` en s'appuyant
> sur le réseau externe `resilience-net`. **Il ne faut donc PAS en créer un** — il existe.

**Nature du conflit :** ta branche a réécrit `docker-compose.yml` pour en faire un compose « dev local »
tout-en-un (base `db` intégrée, ports publiés, volumes, `--reload`). Or `main` a choisi une **séparation
prod / local** : `docker-compose.yml` = déploiement lab, `docker-compose.local.yml` = override dev.

| | `main` (`docker-compose.yml`) | `feature/thomas/backend` |
|---|---|---|
| Base de données | Externe (fournie par le lab) | Service `db` Postgres intégré |
| Ports | `expose:` uniquement (WAF en entrée) | `ports: 5432`, `8000` publiés |
| Réseau | Externe `resilience-net` | Réseau par défaut |
| Volumes / reload | Non (dans `docker-compose.local.yml`) | `./backend:/code` + `--reload` |
| Cible | **Déploiement lab (prod)** | **Dev local** |

**Recommandation : adopter la structure de `main` (ne pas écraser son `docker-compose.yml`).**

- `docker-compose.yml` → **garder la version `main`** (déploiement lab : réseau externe, pas de ports, pas de db).
- `docker-compose.local.yml` → **garder celui de `main`** (il existe déjà et fait le travail).
- Les apports utiles de ta branche à **reporter** dans ces fichiers de `main` **s'ils manquent** :
  les variables d'env de l'auth sur le service `api` (`JWT_SECRET_KEY`, `CORS_ORIGINS`, `LOG_LEVEL`).

Usage local inchangé : `docker compose -f docker-compose.yml -f docker-compose.local.yml up --build`.

> ⚠️ Variables d'env introduites par la branche (`JWT_SECRET_KEY`, `CORS_ORIGINS`, `LOG_LEVEL`,
> et `PROJECT_NAME` si utilisé) : vérifier qu'elles sont bien dans `.env` / `.env.example` **et**
> passées au service `api` du compose **prod** (lab), sinon l'auth JWT ne démarrera pas en déploiement.

---

## Procédure de merge pas à pas

```bash
# Depuis ta branche, synchronise main puis démarre le merge
git checkout feature/thomas/backend
git fetch origin
git merge origin/main        # déclenche les conflits ci-dessus

# Résous les 4 fichiers en conflit (voir §1 à §4), puis :
git add backend/Dockerfile backend/app/main.py backend/requirements.txt docker-compose.yml .gitignore

git commit                   # finalise le merge
# Le frontend, .vscode/, docker-compose.local.yml, correctif.md arrivent de main sans conflit.
```

### Checklist post-résolution
- [ ] `docker compose -f docker-compose.yml -f docker-compose.local.yml up --build` démarre sans erreur
- [ ] `alembic upgrade head` s'exécute au démarrage du conteneur `api`
- [ ] `GET /healthz` répond `200` (base up) et `503` (base down)
- [ ] `/metrics` exposé, auth JWT (`/auth`) et `/donations` fonctionnels
- [ ] `.env` / `.env.example` contient `JWT_SECRET_KEY`, `CORS_ORIGINS`, `PROJECT_NAME`, `LOG_LEVEL`
- [ ] Dépendances : `pip install -r backend/requirements.txt` OK, aucun import manquant
