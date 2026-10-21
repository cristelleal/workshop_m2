# Déploiement de la stack de dev depuis Git

Cette procédure remplace la copie manuelle des fichiers (`rsync`) décrite dans [`deploiment.md`](deploiment.md).

Le repo est **cloné une seule fois** sur la VM avec une clé en lecture seule. Ensuite, chaque mise à jour se fait en **une seule commande** sur la VM : elle récupère le code, reconstruit les images et vérifie que l'API répond.

- **Cible** : VM `host-resilience` (Proxmox VMID 5010), IP lab `192.168.137.1`.
- **Repo** : `git@github.com:cristelleal/workshop_m2.git`.
- **Branche à déployer** :
  - tant que la PR du backend n'est pas mergée : `feature/thomas/backend` ;
  - une fois mergée : `main` (voir [section 8](#passer-sur-main-après-le-merge)).

> ⚠️ Tant que `feature/thomas/backend` n'est pas mergée, `main` contient l'**ancienne** API (`/transactions`, sans comptes).

**Ce guide ne remplace que la copie du code.** Le compose du host (avec `JWT_SECRET_KEY`), le `.env`, les vérifications, le monitoring et la simulation de donateurs sont décrits dans [`deploiment.md`](deploiment.md), sections 3 à 9.

---

## Sommaire

0. [Principe](#0-principe)
1. [Créer une clé de déploiement sur la VM](#1-créer-une-clé-de-déploiement-sur-la-vm)
2. [Ajouter la clé sur GitHub](#2-ajouter-la-clé-sur-github)
3. [Configurer SSH pour GitHub](#3-configurer-ssh-pour-github)
4. [Cloner le repo](#4-cloner-le-repo)
5. [Relier le compose du host au clone](#5-relier-le-compose-du-host-au-clone)
6. [Installer le script de déploiement](#6-installer-le-script-de-déploiement)
7. [Premier déploiement](#7-premier-déploiement)
8. [Mettre à jour après une modif](#8-mettre-à-jour-après-une-modif)
9. [Revenir en arrière](#9-revenir-en-arrière)
10. [Optionnel : déploiement automatique toutes les 5 minutes](#10-optionnel--déploiement-automatique)
11. [Variante sans clé sur la VM](#11-variante-sans-clé-sur-la-vm)
12. [Dépannage](#12-dépannage)
13. [Retirer l'accès](#13-retirer-laccès)

---

## 0. Principe

```
  Poste dev                       GitHub                         VM host-resilience
 ───────────                    ──────────                     ─────────────────────
  git push   ───────────────▶   workshop_m2   ◀── git pull ───  /opt/workshop_m2  (clone)
                                                  (deploy key,        │
                                                   lecture seule)     │ liens symboliques
                                                                      ▼
                                                    /opt/resilience/app/services/api      → backend/
                                                    /opt/resilience/app/services/frontend → frontend/
                                                                      │
                                                    docker compose up -d --build api frontend
```

**Pourquoi des liens symboliques ?**
Le `compose.yaml` du host construit les images depuis `./services/api` et `./services/frontend`. En faisant de ces deux dossiers des liens vers le clone, on n'a pas à toucher aux chemins du compose. Ce montage a été testé : Docker construit bien l'image à travers un lien symbolique.

**Pourquoi cloner hors de `/opt/resilience` ?**
`/opt/resilience` est déjà un dépôt git, géré par l'équipe infra. Y imbriquer un autre dépôt créerait de la confusion dans son `git status`.

---

## 1. Créer une clé de déploiement sur la VM

Se connecter à la VM :

```bash
ssh ubuntu@192.168.137.1
```

Générer une clé **dédiée à ce repo**, sans passphrase, pour que le script puisse l'utiliser sans intervention :

```bash
ssh-keygen -t ed25519 -f ~/.ssh/workshop_deploy -N "" -C "host-resilience deploy workshop_m2"
cat ~/.ssh/workshop_deploy.pub
```

Copier la ligne affichée (elle commence par `ssh-ed25519 ...`). C'est la clé **publique**, on peut la partager sans risque. La clé privée `~/.ssh/workshop_deploy` ne quitte jamais la VM.

---

## 2. Ajouter la clé sur GitHub

Dans le repo **`cristelleal/workshop_m2`** sur GitHub :

1. **Settings** → **Deploy keys** → **Add deploy key**.
2. **Title** : `host-resilience (dev)`.
3. **Key** : coller la clé publique de l'étape 1.
4. **Laisser « Allow write access » décoché.** La VM n'a besoin que de lire le code.
5. **Add key**.

> Il faut être **admin du repo** pour ajouter une deploy key. Si on ne l'est pas, envoyer la clé publique à la propriétaire du repo (Cristelle) pour qu'elle l'ajoute.

**Pourquoi une deploy key plutôt que sa clé perso ?**
- Elle ne donne accès **qu'à ce repo**, et **en lecture seule**.
- Si la VM est compromise (c'est un lab avec une machine Kali attaquante), l'attaquant ne peut ni modifier le code ni accéder à vos autres repos.
- Elle se révoque en un clic, sans toucher aux clés des devs.

---

## 3. Configurer SSH pour GitHub

Toujours sur la VM :

```bash
cat >> ~/.ssh/config <<'EOF'

Host github.com
    IdentityFile ~/.ssh/workshop_deploy
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

Tester la connexion :

```bash
ssh -T git@github.com
```

- **Résultat attendu** : `Hi cristelleal/workshop_m2! You've successfully authenticated, but GitHub does not provide shell access.`
- **À la première connexion**, SSH demande de confirmer l'empreinte de GitHub : répondre `yes`.

**Si la connexion bloque ou expire** (le pare-feu du lab, la VM `FW`, peut fermer le port 22 vers Internet), passer par le port 443. Remplacer le bloc ajouté ci-dessus par :

```
Host github.com
    HostName ssh.github.com
    Port 443
    IdentityFile ~/.ssh/workshop_deploy
    IdentitiesOnly yes
```

Puis retester avec `ssh -T git@github.com`.

---

## 4. Cloner le repo

```bash
sudo mkdir -p /opt/workshop_m2
sudo chown ubuntu: /opt/workshop_m2
git clone -b feature/thomas/backend git@github.com:cristelleal/workshop_m2.git /opt/workshop_m2
```

> Si la PR du backend est **déjà mergée** au moment où tu fais cette étape, cloner directement `main` : remplacer `-b feature/thomas/backend` par `-b main`.

Vérifier :

```bash
git -C /opt/workshop_m2 branch --show-current
git -C /opt/workshop_m2 log -1 --oneline
ls /opt/workshop_m2/backend /opt/workshop_m2/frontend
```

Ce qu'on doit voir :
- la branche choisie et son dernier commit ;
- dans `backend/` : `Dockerfile`, `alembic.ini`, `app/`, `migrations/`, `requirements.txt` ;
- dans `frontend/` : `Dockerfile`, `nginx.conf`, `package.json`, etc.

> ⚠️ **Ne jamais modifier de fichiers directement dans `/opt/workshop_m2`.** Toute modif passe par le repo (poste dev → push). Sinon le `git pull` refusera de s'exécuter.

---

## 5. Relier le compose du host au clone

```bash
cd /opt/resilience/app/services
ls -la
```

**Si `api/` ou `frontend/` existent déjà** (par exemple après une copie avec `rsync` via `deploiment.md`), les mettre de côté plutôt que de les supprimer :

```bash
mv api api.old 2>/dev/null; mv frontend frontend.old 2>/dev/null
```

Créer les liens :

```bash
ln -s /opt/workshop_m2/backend  api
ln -s /opt/workshop_m2/frontend frontend
ls -la
```

Ce qu'on doit voir :

```
api      -> /opt/workshop_m2/backend
frontend -> /opt/workshop_m2/frontend
```

Une fois le premier déploiement validé (étape 7), on peut supprimer `api.old` et `frontend.old`.

### Compose et `.env` du host

Si ce n'est pas déjà fait :
- **le compose** : décommenter `api` et `frontend` (laisser `auth` commenté) et **ajouter `JWT_SECRET_KEY: ${JWT_SECRET_KEY}`** dans le bloc `api`. Voir [`deploiment.md`, section 3](deploiment.md#3-activer-les-services-dans-le-compose) ;
- **la clé JWT** : la générer dans le `.env`. Voir [`deploiment.md`, section 4](deploiment.md#4-préparer-le-env-clé-jwt).

Ces deux étapes ne se font qu'**une seule fois** : elles ne dépendent pas de la méthode de copie du code.

---

## 6. Installer le script de déploiement

Le script se place **hors du repo** (`~/bin`). Ainsi, un `git pull` ne peut pas le modifier pendant qu'il tourne.

```bash
mkdir -p ~/bin
cat > ~/bin/deploy-app.sh <<'EOF'
#!/usr/bin/env bash
# Déploie la stack de dev (api + frontend) depuis le clone Git.
# Usage : deploy-app.sh [branche]     (par défaut : la branche actuelle du clone)
set -euo pipefail

REPO=/opt/workshop_m2
APP=/opt/resilience/app
SERVICES=(api frontend)

BRANCH="${1:-$(git -C "$REPO" rev-parse --abbrev-ref HEAD)}"

echo "==> Récupération de la branche '$BRANCH'"
git -C "$REPO" fetch --prune origin
git -C "$REPO" checkout "$BRANCH"
git -C "$REPO" pull --ff-only origin "$BRANCH"
echo "    Commit déployé : $(git -C "$REPO" log -1 --format='%h %s (%an)')"

echo "==> Sauvegarde des images actuelles (tag :prev)"
for svc in "${SERVICES[@]}"; do
  if docker image inspect "resilience-app-$svc:latest" >/dev/null 2>&1; then
    docker tag "resilience-app-$svc:latest" "resilience-app-$svc:prev"
  fi
done

echo "==> Build et redémarrage de : ${SERVICES[*]}"
cd "$APP"
docker compose up -d --build "${SERVICES[@]}"

echo "==> Attente du healthcheck de app-api (90 s max)"
for _ in $(seq 1 45); do
  status=$(docker inspect -f '{{.State.Health.Status}}' app-api 2>/dev/null || echo "absent")
  if [ "$status" = "healthy" ]; then
    echo "OK : app-api est healthy, déploiement terminé."
    exit 0
  fi
  sleep 2
done

echo "ERREUR : app-api n'est pas healthy après 90 s (statut : $status)." >&2
echo "Derniers logs :" >&2
docker logs --tail 30 app-api >&2
echo "Pour revenir à la version précédente : voir la section 'Revenir en arrière'." >&2
exit 1
EOF
chmod +x ~/bin/deploy-app.sh
```

**Ce que fait le script :**
1. Il récupère la dernière version de la branche, avec `--ff-only` : il refuse de continuer si le clone a été modifié localement.
2. Il garde une copie des images actuelles sous le tag `:prev`, pour pouvoir revenir en arrière.
3. Il reconstruit et redémarre `api` et `frontend`. L'API applique toute seule les migrations Alembic au démarrage. La base `db` n'est pas touchée.
4. Il attend que `app-api` soit `healthy`. Sinon, il affiche les logs et sort en erreur.

> `~/bin` est automatiquement ajouté au `PATH` sur Ubuntu à la prochaine connexion. En attendant, appeler le script avec `~/bin/deploy-app.sh`.

---

## 7. Premier déploiement

```bash
~/bin/deploy-app.sh
```

Le premier build prend quelques minutes, le temps de télécharger les images Python, Node et Nginx.

Ce qu'on doit voir à la fin :

```
==> Récupération de la branche 'feature/thomas/backend'
    Commit déployé : <hash> <message du dernier commit> (<auteur>)
==> Sauvegarde des images actuelles (tag :prev)
==> Build et redémarrage de : api frontend
==> Attente du healthcheck de app-api (90 s max)
OK : app-api est healthy, déploiement terminé.
```

Le minimum à vérifier ensuite :

```bash
docker run --rm --network resilience-net curlimages/curl:8.11.1 -s http://api:8000/healthz   # {"status":"ok"}
curl -s http://localhost/donations/presets                                                   # chemin WAF -> API
curl -s 'http://localhost:9090/api/v1/query?query=up{job="resilience-app"}'                  # api:8000 → "1"
```

> Ne pas tester la santé avec `curl http://localhost/healthz` : c'est le WAF qui répond `OK`, même si l'API est arrêtée.

Pour les vérifications complètes (compte, connexion, dons, metrics, Loki) et la simulation de donateurs : voir [`deploiment.md`, sections 6 à 8](deploiment.md#6-vérifier-que-tout-marche).

---

## 8. Mettre à jour après une modif

**Sur son poste :**

```bash
git push
```

**Sur la VM :**

```bash
deploy-app.sh
```

C'est tout. On peut aussi tout lancer depuis son poste, sans ouvrir de session sur la VM :

```bash
git push && ssh ubuntu@192.168.137.1 '~/bin/deploy-app.sh'
```

> Pendant les quelques secondes du redémarrage de l'API, le WAF renvoie `502` : c'est normal.

### Déployer une autre branche

Par exemple pour tester une feature :

```bash
deploy-app.sh feature/ma-branche
```

Le clone reste ensuite sur cette branche, et les `deploy-app.sh` suivants (sans argument) la redéploient.

### Passer sur `main` après le merge

Une fois la PR `feature/thomas/backend` mergée dans `main`, basculer **une seule fois** :

```bash
deploy-app.sh main
```

Ensuite, `deploy-app.sh` (sans argument) suit `main`.

---

## 9. Revenir en arrière

### Option rapide : reprendre les images précédentes

Le script garde une copie des images avant chaque déploiement :

```bash
docker tag resilience-app-api:prev      resilience-app-api:latest
docker tag resilience-app-frontend:prev resilience-app-frontend:latest
cd /opt/resilience/app && docker compose up -d --no-build api frontend
```

> - Le tag `:prev` ne garde **qu'une seule** version en arrière.
> - Revenir à une ancienne image **ne défait pas les migrations** de base déjà appliquées.

### Option propre : revenir sur un commit précis

```bash
git -C /opt/workshop_m2 log --oneline -10        # trouver le commit voulu
git -C /opt/workshop_m2 checkout <commit>
cd /opt/resilience/app && docker compose up -d --build api frontend
```

Le clone est alors en « detached HEAD » : il n'est plus sur une branche. Pour reprendre les déploiements normaux, redonner la branche suivie :

```bash
deploy-app.sh main        # ou feature/thomas/backend si la PR n'est pas encore mergée
```

---

## 10. Optionnel : déploiement automatique

Pour que la VM déploie **toute seule** chaque nouveau commit, on ajoute une tâche `cron` qui vérifie toutes les 5 minutes s'il y a du nouveau sur GitHub.

```bash
cat > ~/bin/deploy-if-changed.sh <<'EOF'
#!/usr/bin/env bash
# Lance deploy-app.sh seulement si la branche distante a de nouveaux commits.
set -euo pipefail
REPO=/opt/workshop_m2
BRANCH=$(git -C "$REPO" rev-parse --abbrev-ref HEAD)
[ "$BRANCH" = "HEAD" ] && exit 0      # clone en detached HEAD (retour arrière manuel) : ne rien faire
git -C "$REPO" fetch --quiet origin "$BRANCH"
if [ "$(git -C "$REPO" rev-parse HEAD)" != "$(git -C "$REPO" rev-parse "origin/$BRANCH")" ]; then
  echo "[$(date -Is)] nouveaux commits sur $BRANCH, déploiement"
  "$HOME/bin/deploy-app.sh" "$BRANCH"
fi
EOF
chmod +x ~/bin/deploy-if-changed.sh

# Lancer toutes les 5 minutes, avec un verrou pour éviter deux déploiements en parallèle
( crontab -l 2>/dev/null; echo '*/5 * * * * flock -n /tmp/deploy-app.lock $HOME/bin/deploy-if-changed.sh >> $HOME/deploy-app.log 2>&1' ) | crontab -
```

- **Branche suivie** : le cron suit la branche **actuelle** du clone. Après le merge, faire une fois `deploy-app.sh main` (section 8) pour qu'il suive `main`.
- **Suivre les déploiements automatiques** : `tail -f ~/deploy-app.log`.
- **Désactiver** : `crontab -e`, puis supprimer la ligne `deploy-if-changed.sh`.

> ⚠️ Avec ce mode, **chaque push sur la branche suivie part sur la VM** dans les 5 minutes, même un commit cassé. C'est acceptable en dev. Pour plus de contrôle, rester sur le déploiement manuel de la section 8.

---

## 11. Variante sans clé sur la VM

Si on ne veut stocker **aucune clé** sur la VM, ou si on ne peut pas ajouter de deploy key, on peut utiliser le **transfert d'agent SSH**. La clé de son poste est alors utilisée à distance, le temps de la session.

```bash
# Sur son poste : vérifier que sa clé est chargée dans l'agent
ssh-add -l
# Se connecter avec -A
ssh -A ubuntu@192.168.137.1
# Sur la VM, git utilise la clé du poste
deploy-app.sh
```

- Dans ce cas, **sauter les étapes 1 à 3** et cloner directement à l'étape 4.
- Il faut aussi **ne pas** ajouter le bloc `Host github.com` avec `IdentityFile` dans `~/.ssh/config`.

**Limites :**
- Pendant la session, quiconque est root sur la VM peut utiliser votre clé, et donc accéder à **tous vos repos**.
- Le déploiement automatique de la section 10 ne fonctionne pas : `cron` n'a pas accès à votre agent.

La deploy key reste la solution recommandée.

---

## 12. Dépannage

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| `git@github.com: Permission denied (publickey)` | Deploy key non ajoutée sur GitHub, ou mauvaise clé utilisée | Vérifier l'étape 2. Debug : `ssh -vT git@github.com 2>&1 \| grep -i "offering\|identity"` doit montrer `workshop_deploy` |
| `ssh -T git@github.com` reste bloqué puis expire | Port 22 sortant fermé par le pare-feu du lab | Passer par le port 443 (fin de l'étape 3) |
| `Host key verification failed` | Empreinte de GitHub jamais acceptée (cas du cron) | Lancer une fois `ssh -T git@github.com` à la main et répondre `yes` |
| Le script s'arrête sur `app-api n'est pas healthy`, logs : `jwt_secret_key` | Ligne `JWT_SECRET_KEY` absente du compose, ou clé absente ou trop courte dans `.env` | [`deploiment.md`, sections 3 et 4](deploiment.md#4-préparer-le-env-clé-jwt) |
| Le script s'arrête sur `app-api n'est pas healthy`, et `/transactions` existe encore | Clone sur un `main` d'avant le merge du backend | `git -C /opt/workshop_m2 branch --show-current`, puis `deploy-app.sh feature/thomas/backend` |
| `fatal: Not possible to fast-forward, aborting.` | Fichiers modifiés directement sur la VM, ou historique réécrit (force-push) | Voir les modifs : `git -C /opt/workshop_m2 status`. Pour revenir à la version GitHub (**efface les modifs locales**) : `git -C /opt/workshop_m2 reset --hard origin/<branche>` |
| `error: Your local changes ... would be overwritten by checkout` | Même cause | Même solution |
| `error: pathspec 'main' did not match` | Branche inconnue du clone | `git -C /opt/workshop_m2 fetch origin`, puis relancer le script |
| `docker compose` : `unable to prepare context: path ".../services/api" not found` | Lien symbolique cassé ou absent | `ls -la /opt/resilience/app/services` : les liens doivent pointer vers `/opt/workshop_m2/backend` et `/frontend` |
| Le script s'arrête sur `app-api n'est pas healthy` (autre cas) | L'API ne démarre pas ou ne joint pas la base | Lire les logs affichés. Voir [`deploiment.md`, section 12](deploiment.md#12-dépannage). Revenir en arrière avec la section 9 |
| `deploy-app.sh: command not found` | `~/bin` pas encore dans le `PATH` | Utiliser `~/bin/deploy-app.sh`, ou se reconnecter |
| Le cron ne déploie rien | Clone en detached HEAD, ou erreur dans le log | `tail ~/deploy-app.log` et `git -C /opt/workshop_m2 status` |

---

## 13. Retirer l'accès

En fin de projet, ou si la VM est compromise :

1. **Sur GitHub** : Settings → Deploy keys → **Delete** sur `host-resilience (dev)`.
2. **Sur la VM** :

   ```bash
   rm ~/.ssh/workshop_deploy ~/.ssh/workshop_deploy.pub
   crontab -l | grep -v deploy-if-changed | crontab -     # si le cron était actif
   ```
