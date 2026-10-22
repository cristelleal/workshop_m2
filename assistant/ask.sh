#!/usr/bin/env bash
# Pose une question à l'assistant et affiche une réponse courte (directives à suivre).
# Avec un conteneur, joint ses derniers logs Loki à la question.
#
#   ./ask.sh "Que faire si la base ne répond plus ?"
#   ./ask.sh "Que dois-je faire ?" app-api            # + 20 derniers logs ERROR/WARN de app-api
#   ./ask.sh "Que dois-je faire ?" app-api 50
#   QUERY='{container="app-api"}' ./ask.sh "Tout va bien ?" app-api   # tous niveaux
#
# La clé d'API est lue dans $ASSISTANT_API_KEY, sinon dans le .env à côté du script.
# Dépendances : curl, jq.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

QUESTION="${1:?usage : ./ask.sh \"question\" [conteneur] [limit]}"
CONTAINER="${2:-}"
LIMIT="${3:-20}"
LOKI_URL="${LOKI_URL:-http://192.168.137.1:3100}"
ASSISTANT_URL="${ASSISTANT_URL:-http://100.76.111.69:8100}"

if [[ -z "${ASSISTANT_API_KEY:-}" && -f "$SCRIPT_DIR/.env" ]]; then
  ASSISTANT_API_KEY="$(grep -E '^ASSISTANT_API_KEY=' "$SCRIPT_DIR/.env" | cut -d= -f2-)"
fi
: "${ASSISTANT_API_KEY:?définir ASSISTANT_API_KEY (variable d'env ou .env de l'assistant)}"

logs=""
if [[ -n "$CONTAINER" ]]; then
  QUERY="${QUERY:-{container=\"$CONTAINER\"\} |~ \"(?i)error|warn\"}"
  echo "→ Loki : $QUERY (limit=$LIMIT)" >&2
  logs="$(curl -sfG -m 30 "$LOKI_URL/loki/api/v1/query_range" \
      --data-urlencode "query=$QUERY" --data-urlencode "limit=$LIMIT" \
    | jq -r '[.data.result[].values[]] | sort_by(.[0]) | .[][1]')"
  if [[ -z "$logs" ]]; then
    # Pas la peine de solliciter le modèle : il inventerait des pistes sans rien à analyser.
    echo "Aucun log correspondant dans la dernière heure pour $CONTAINER : rien à signaler."
    exit 0
  fi
fi

echo "→ réflexion en cours (1 à 3 min)…" >&2
jq -n --arg q "$QUESTION" --arg logs "$logs" '{question: $q} + (if $logs == "" then {} else {logs: $logs} end)' \
  | curl -sf -m 600 -X POST "$ASSISTANT_URL/ask" \
      -H "X-API-Key: $ASSISTANT_API_KEY" -H 'Content-Type: application/json' -d @- \
  | jq -r '.answer'
