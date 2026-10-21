# À faire sur le Proxmox

Checklist pour mettre la nouvelle API (comptes + dons) sur la VM `host-resilience` (`192.168.137.1`). Chaque étape est détaillée dans [`deploiment.md`](deploiment.md).

**Durée** : environ 15 minutes, dont quelques minutes de build.

---

## Avant de commencer

- [ ] Tailscale connecté, et `ssh ubuntu@192.168.137.1` fonctionne.
- [ ] Sur son poste, le repo est sur la bonne branche, à jour (`git pull`) :
  - `feature/thomas/backend` tant que la PR n'est pas mergée ;
  - `main` une fois mergée.

---

## 1. Envoyer le code (depuis son poste, à la racine du repo)

```bash
rsync -av --delete --exclude __pycache__ --exclude .venv --exclude venv \
  backend/  ubuntu@192.168.137.1:/opt/resilience/app/services/api/
rsync -av --delete --exclude node_modules --exclude dist \
  frontend/ ubuntu@192.168.137.1:/opt/resilience/app/services/frontend/
```

> En cas de `Permission denied` : ajouter `--rsync-path="sudo rsync"`. Variante sans copie, avec un clone Git : [`deploimentAuto.md`](deploimentAuto.md).

---

## 2. Modifier le compose du host (sur la VM, une seule fois)

```bash
ssh ubuntu@192.168.137.1
cd /opt/resilience/app
cp compose.yaml compose.yaml.bak
nano compose.yaml
```

- [ ] Décommenter le bloc **`api`**.
- [ ] Décommenter le bloc **`frontend`**.
- [ ] **Laisser `auth` commenté** : l'authentification est intégrée à `api`.
- [ ] **Ajouter dans `api` → `environment:`** la ligne suivante, alignée sous `DATABASE_URL` :

  ```yaml
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
  ```

- [ ] Vérifier : `docker compose config --services` doit afficher `db`, `api` et `frontend`.

Le bloc `api` complet attendu se trouve dans [`deploiment.md`, section 3](deploiment.md#3-activer-les-services-dans-le-compose).

---

## 3. Générer la clé JWT (sur la VM, une seule fois)

```bash
cd /opt/resilience/app
grep -q '^JWT_SECRET_KEY=' .env 2>/dev/null || echo "JWT_SECRET_KEY=$(openssl rand -base64 48)" >> .env
chmod 600 .env
docker compose config | grep -c JWT_SECRET_KEY     # doit afficher 1
```

- [ ] Ne **pas** toucher à `POSTGRES_PASSWORD` si la base tourne déjà.
- [ ] Ne **jamais** commiter ce `.env`.

---

## 4. Lancer

```bash
cd /opt/resilience/app
docker compose up -d --build api frontend
docker compose ps          # app-api doit passer en (healthy) en ~20 s
```

> Un seul redémarrage de `app-api` au tout premier lancement est normal : la migration de la base peut démarrer avant Postgres.

---

## 5. Vérifier (sur la VM)

```bash
docker run --rm --network resilience-net curlimages/curl:8.11.1 -s http://api:8000/healthz
# -> {"status":"ok"}   (en direct : sur /healthz, le WAF répond lui-même "OK", même si l'API est arrêtée)

curl -s http://localhost/donations/presets
# -> {"currency":"EUR","presets_cents":[500,1000,2500,5000],...}   (chemin complet WAF -> API)

curl -s 'http://localhost:9090/api/v1/query?query=up{job="resilience-app"}'
# -> "instance":"api:8000" avec la valeur "1"

curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost/auth/login -d "username=admin' OR '1'='1&password=x"
# -> 403 (le WAF bloque l'injection SQL)
```

- [ ] Les trois résultats sont bons.
- [ ] Faire le parcours complet (compte, connexion, dons, metrics, front) : [`deploiment.md`, section 6](deploiment.md#6-vérifier-que-tout-marche).

---

## 6. Générer du trafic et regarder Grafana

- [ ] Installer `~/simu-dons.sh` sur la VM (copier-coller depuis [`deploiment.md`, section 8](deploiment.md#8-simuler-des-donateurs)).
- [ ] Lancer `~/simu-dons.sh`. Résultat attendu : `200 201`.
- [ ] Dans Grafana (http://192.168.137.1:3000) → **Explore** :
  - **Prometheus** : `sum by (status) (rate(donations_total[1m]))` ;
  - **Loki** : `{container="app-api"} | json | message="donation_processed"`.

---

## 7. Prévenir les autres équipes

| Équipe | Message |
|--------|---------|
| **SOC / WAF** | L'API est en ligne derrière `security-waf`, sans changement de leur côté. `GET /donations/all` est une **faille volontaire** (tout utilisateur connecté voit tous les dons). `/metrics` et `/docs` sont publics via le WAF. Le front n'est pas exposé tant que le `BACKEND` du WAF vise `api:8000`. |
| **Monitoring** | Rien à changer. Nouvelles metrics : `donations_total`, `donations_amount_euros_total`, `payment_processing_seconds`. La cible `auth:8000` restera DOWN : il n'y a pas de service `auth` séparé, elle peut être retirée de `prometheus.yml`. |
| **Ansible** | Le compose du host a changé : blocs `api` et `frontend` décommentés, ligne `JWT_SECRET_KEY` ajoutée. Le `.env` contient maintenant `JWT_SECRET_KEY`. À reporter dans leurs playbooks s'ils redéploient la VM. |

---

## ⛔ À ne jamais faire

- **`docker compose down -v`** dans `/opt/resilience/app` : supprime toute la base.
- **Changer `POSTGRES_PASSWORD`** dans `.env` alors que la base tourne : l'API ne pourra plus s'y connecter.
- **Committer le `.env`**, ou la clé JWT, dans un repo.

**En cas de problème** : [`deploiment.md`, section 12 (Dépannage)](deploiment.md#12-dépannage).
