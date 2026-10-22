#!/usr/bin/env bash
# Récupère des logs dans Loki, les envoie à l'assistant (/analyze) et écrit
# l'analyse dans un fichier Markdown. Lancement manuel.
#
#   ./analyze-logs.sh                         # 5 derniers logs de app-api
#   ./analyze-logs.sh app-api 50              # 50 derniers logs
#   QUERY='{container="app-api"} |~ "(?i)error|warn"' ./analyze-logs.sh app-api 100
#
# La clé d'API est lue dans $ASSISTANT_API_KEY, sinon dans le .env à côté du script.
# Dépendances : curl, jq.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

CONTAINER="${1:-app-api}"
LIMIT="${2:-5}"
QUERY="${QUERY:-{container=\"$CONTAINER\"\}}"
LOKI_URL="${LOKI_URL:-http://192.168.137.1:3100}"
ASSISTANT_URL="${ASSISTANT_URL:-http://100.76.111.69:8100}"
OUT_DIR="${OUT_DIR:-$SCRIPT_DIR/analyses}"
SERVICE="${CONTAINER#app-}"   # app-api -> api

if [[ -z "${ASSISTANT_API_KEY:-}" && -f "$SCRIPT_DIR/.env" ]]; then
  ASSISTANT_API_KEY="$(grep -E '^ASSISTANT_API_KEY=' "$SCRIPT_DIR/.env" | cut -d= -f2-)"
fi
: "${ASSISTANT_API_KEY:?définir ASSISTANT_API_KEY (variable d'env ou .env de l'assistant)}"

echo "→ Loki : $QUERY (limit=$LIMIT)" >&2
loki_json="$(curl -sfG -m 30 "$LOKI_URL/loki/api/v1/query_range" \
  --data-urlencode "query=$QUERY" \
  --data-urlencode "limit=$LIMIT")"

# Tous les streams fusionnés, du plus ancien au plus récent.
logs="$(jq -r '[.data.result[].values[]] | sort_by(.[0]) | .[][1]' <<<"$loki_json")"
if [[ -z "$logs" ]]; then
  echo "Aucun log trouvé pour cette requête (Loki regarde la dernière heure par défaut)." >&2
  exit 1
fi
echo "→ $(wc -l <<<"$logs" | tr -d ' ') lignes envoyées à l'assistant, analyse en cours (1 à 4 min)…" >&2

response="$(jq -n --arg logs "$logs" --arg service "$SERVICE" '{logs: $logs, service: $service}' \
  | curl -sf -m 600 -X POST "$ASSISTANT_URL/analyze" \
      -H "X-API-Key: $ASSISTANT_API_KEY" -H 'Content-Type: application/json' -d @-)"

mkdir -p "$OUT_DIR"
out="$OUT_DIR/analyse-$CONTAINER-$(date +%Y%m%d-%H%M%S).md"
{
  echo "# Analyse des logs : $CONTAINER"
  echo
  echo "- Date : $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- Requête Loki : \`$QUERY\` (limit=$LIMIT)"
  echo
  echo "## Analyse"
  echo
  jq -r '.analysis' <<<"$response"
  echo
  echo "## Incidents connus rapprochés"
  echo
  echo "Score de 0 à 1 : au-dessus de 0,7 la correspondance est nette."
  echo
  jq -r '.matched_incidents[] | "- \(.title) (score \(.score))"' <<<"$response"
  echo
  echo "## Documents utilisés"
  echo
  jq -r '.sources[] | "- `\(.)`"' <<<"$response"
  echo
  echo "## Logs analysés"
  echo
  echo '```'
  echo "$logs"
  echo '```'
} >"$out"

echo "✓ Analyse écrite dans $out" >&2
