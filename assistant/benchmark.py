"""Benchmark simple de modèles Ollama pour choisir celui de la solution.

Mesure, pour chaque modèle, la latence et le débit (tokens/s) sur un prompt
représentatif. Les modèles doivent déjà être tirés (`ollama pull <modèle>`).

Exemples :
    python benchmark.py llama3.2:3b qwen2.5:3b-instruct phi3:mini
    OLLAMA_BASE_URL=http://192.168.137.1:11434 python benchmark.py llama3.1:8b
"""
import json
import sys
import time
import urllib.request

OLLAMA = __import__("os").getenv("OLLAMA_BASE_URL", "http://localhost:11434")

PROMPT = (
    "Contexte: Le service de paiement renvoie des erreurs 503 et le WAF a bloqué "
    "des requêtes suspectes. Procédure: vérifier /healthz, consulter Grafana, "
    "relancer le conteneur api via le playbook Ansible.\n\n"
    "Question: Que doit faire l'opérateur en premier ? Réponds en 3 phrases."
)


def bench(model: str) -> dict:
    body = json.dumps({"model": model, "prompt": PROMPT, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    elapsed = time.perf_counter() - start

    eval_count = data.get("eval_count", 0)
    eval_ns = data.get("eval_duration", 1) or 1
    tok_s = eval_count / (eval_ns / 1e9)
    return {"model": model, "seconds": round(elapsed, 1), "tokens": eval_count, "tok_s": round(tok_s, 1)}


def main(models: list[str]) -> None:
    print(f"Ollama: {OLLAMA}\n")
    print(f"{'modèle':<28}{'temps(s)':>10}{'tokens':>10}{'tok/s':>10}")
    print("-" * 58)
    for model in models:
        try:
            r = bench(model)
            print(f"{r['model']:<28}{r['seconds']:>10}{r['tokens']:>10}{r['tok_s']:>10}")
        except Exception as exc:  # noqa: BLE001
            print(f"{model:<28}  ERREUR: {exc}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
