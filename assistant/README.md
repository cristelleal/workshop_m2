# Assistant opérateur (Ollama + Qdrant + RAG)

Reçoit des logs d'erreur ou de warning et propose un diagnostic et des actions, à partir de deux sources stockées dans Qdrant :

- la collection `docs` : les procédures de l'équipe (`.md`, `.txt`, `.pdf`) ;
- la collection `incidents` : les incidents connus (symptômes, cause, solution).

L'assistant **propose**, il n'exécute rien : la remédiation reste à l'opérateur ou à Ansible.

## Architecture

```
VM host (Proxmox)  ── logs ──>  Tailscale  ──>  PC IA :8100  assistant ──> qdrant :6333
                                                                       └──> ollama :11434
```

Seul le port `8100` de l'assistant est publié, et uniquement sur l'IP Tailscale du PC. Ollama et Qdrant ne sortent pas du PC.

## Installation sur le PC IA

```bash
cd assistant
cp .env.example .env
# renseigner ASSISTANT_API_KEY (openssl rand -hex 32) et ASSISTANT_BIND (tailscale ip -4)
docker compose up -d --build
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull gemma4:e4b
docker compose restart assistant      # indexe les docs maintenant que les modèles sont là
```

Au premier démarrage, l'assistant indexe `../docs` et charge les incidents de `knowledge/incidents.json`. Les données sont dans le volume `qdrant_data` : elles survivent aux redémarrages.

Si Tailscale démarre après Docker, la publication sur l'IP Tailscale échoue : relancer `docker compose up -d`.

## Tester manuellement

Variables à définir une fois (depuis le PC : `http://localhost:8100`, depuis le tailnet : l'IP Tailscale du PC) :

```bash
export AI=http://100.x.y.z:8100
export KEY=<valeur de ASSISTANT_API_KEY>
```

| Test | Commande |
|---|---|
| Le service répond (sans clé) | `curl $AI/health` |
| Poser une question sur les procédures | `curl -X POST $AI/chat -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d '{"question":"Comment se déroule le déploiement automatique ?"}'` |
| Analyser des logs | voir ci-dessous |
| Voir les incidents connus | `curl $AI/incidents -H "X-API-Key: $KEY"` |

Analyser un fichier de logs (le JSON est construit par `jq`, qui gère les guillemets et retours à la ligne) :

```bash
jq -n --rawfile logs erreurs.log '{logs: $logs, service: "api"}' \
  | curl -X POST $AI/analyze -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d @-
```

La réponse contient `analysis` (diagnostic, cause, actions, gravité), `matched_incidents` (incidents reconnus, score de 0 à 1 : au-dessus de 0,7 la correspondance est nette) et `sources` (docs utilisées).

Interface graphique : `http://<IP du PC>:8100/docs` (Swagger) permet d'appeler chaque route depuis le navigateur (bouton **Authorize** pour la clé). Le contenu brut de Qdrant est visible sur `http://localhost:6333/dashboard`, depuis le PC uniquement.

Sur CPU, compter 1 à 4 minutes par réponse : prévoir un timeout client large (`curl -m 600`).

## Alimenter la base

### Ajouter une procédure

Envoyer le fichier : il est enregistré dans `docs/uploads/` et indexé aussitôt. Renvoyer un fichier du même nom remplace l'ancienne version.

```bash
curl -X POST $AI/documents -H "X-API-Key: $KEY" -F "file=@procedure-redis.md"
```

Autre possibilité, sur le PC : déposer les fichiers dans `docs/` puis tout réindexer avec `curl -X POST $AI/reindex -H "X-API-Key: $KEY"`.

### Ajouter un incident résolu

C'est ce qui améliore le plus les analyses. Dans `symptoms`, mettre la ligne de log caractéristique telle qu'elle apparaît : c'est elle qui sera comparée aux logs reçus.

```bash
curl -X POST $AI/incidents -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d '{
  "title": "Redis injoignable",
  "service": "api",
  "symptoms": "redis.exceptions.ConnectionError: Error 111 connecting to redis:6379. Connection refused.",
  "cause": "Le conteneur redis est arrêté.",
  "solution": "1. docker compose ps redis. 2. docker compose restart redis. 3. Vérifier avec redis-cli ping."
}'
```

Les logs bruts ne sont pas stockés dans Qdrant : ils sont bruités et noieraient les procédures. On n'y garde que ce qui a été compris (un incident et sa solution).

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `LLM_MODEL` | (vide) | Modèle de génération, à tirer dans Ollama |
| `EMBED_MODEL` | `nomic-embed-text` | Modèle d'embeddings. En changer impose de vider Qdrant |
| `ASSISTANT_API_KEY` | (obligatoire) | Clé exigée dans `X-API-Key` |
| `ASSISTANT_BIND` | `127.0.0.1` | IP de publication du port 8100 |
| `DOCS_DIR` | `../docs` | Dossier des documents indexés |
| `RETRIEVER_K` / `INCIDENTS_K` | `4` / `3` | Nombre de passages de docs / d'incidents envoyés au modèle |
| `MAX_LOG_CHARS` | `3000` | Taille max des logs analysés (on garde la fin) |
