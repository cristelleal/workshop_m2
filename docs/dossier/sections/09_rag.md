# Assistant opérateur RAG

## Rôle

Pendant un incident, l'opérateur doit vite comprendre ce qui se passe et retrouver la bonne procédure. L'assistant répond à ses questions sur l'architecture et les procédures, et propose un diagnostic à partir des journaux. Il propose, mais il n'exécute rien : il n'a aucun accès à Docker, à Ansible ni à la base de données, et ne connaît aucun secret. Ce cloisonnement est voulu. La réponse d'un modèle de langage varie d'une fois sur l'autre et peut se tromper avec aplomb. Elle ne doit donc jamais déclencher seule une action sur la production.

## Architecture

Un modèle de langage de taille utile ne tient pas dans les 8 Go du serveur à côté de la supervision. Toute la stack de l'assistant tourne donc sur un PC IA séparé, avec Docker Compose (code dans `assistant/`, sur la branche `feature/thomas/assistantOllamaQdrant`). Ollama sert deux modèles : Qwen3.5 pour la génération des réponses, retenu après comparaison avec le script `benchmark.py`, et `nomic-embed-text` pour transformer les textes en vecteurs. Ces vecteurs sont stockés dans Qdrant, en deux collections. La première contient les procédures de l'équipe (Markdown, texte, PDF). La seconde contient les incidents déjà résolus, chacun décrit par son symptôme, sa cause et sa solution. Une API FastAPI, construite avec LangChain, orchestre l'ensemble. Elle n'écoute que sur l'adresse Tailscale du PC et exige une clé d'API à chaque appel. Qdrant n'est accessible que depuis le PC lui-même.

## Fonctionnement

Quand l'opérateur pose une question, l'assistant retrouve les quatre passages de documentation et les trois incidents connus les plus proches, puis demande au modèle de répondre à partir de ces seuls extraits, avec une température basse (0,1) pour limiter les inventions. La route `/chat` répond aux questions libres en citant ses sources. La route `/ask` donne une réponse courte, la situation et au plus trois consignes, à partir d'une question accompagnée de journaux. La route `/analyze` produit un diagnostic complet : cause probable, actions et gravité, avec les incidents connus reconnus et leur score de ressemblance. Deux scripts relient l'assistant à la supervision. `ask.sh` récupère dans Loki les dernières erreurs d'un conteneur et les soumet à l'assistant. `analyze-logs.sh` produit un rapport d'analyse en Markdown.

La base de connaissances s'enrichit au fil des incidents, par l'ajout de procédures ou d'incidents résolus. Les journaux bruts, en revanche, ne sont jamais indexés : trop volumineux et trop bruités, ils noieraient les procédures dans les résultats de recherche. Seul ce qui a été compris (un symptôme, sa cause, sa solution) entre dans la base.

## Limites

Sur le processeur du PC IA, une réponse prend une à quatre minutes. L'assistant sert donc à l'analyse et à la rédaction après coup, pas à la réaction en temps réel. Le risque d'injection de prompt par un document piégé (scénario SS11) est contenu de deux façons : le corpus est interne et ne s'alimente que par une route protégée, et même trompé, l'assistant n'a aucun droit d'action. Enfin, l'assistant n'était pas encore fusionné dans la branche principale au gel du code.
