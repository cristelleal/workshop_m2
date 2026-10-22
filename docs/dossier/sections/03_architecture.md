# Architecture et flux

## Vue d'ensemble

![Architecture cible de RESILIENCE-ALPHA (schéma VaultObsidian/SchemaArchiV4.excalidraw)](img/architecture.png)

> **Lecture de la figure.** Le schéma représente l'architecture visée, organisée en blocs colorés par pilier : bleu pour le développement, vert pour l'infrastructure et la supervision, violet pour l'IA, rouge pour la cybersécurité. En haut, le navigateur de l'utilisateur et les scénarios Red Team du PC attaquant convergent vers le WAF, seul point d'entrée du PC hôte. La flèche pointillée rouge marque le flux d'attaque. Le WAF répartit ensuite les requêtes vers le frontend, le service d'authentification et l'API, qui partagent la base PostgreSQL. Une sonde (Iris) interroge elle aussi le WAF pour vérifier le service de l'extérieur. Sous l'hôte, le bloc de supervision collecte les métriques (Prometheus) et les journaux (Loki), qui alimentent Grafana et le détecteur ML. Le bloc AIOps, en bas, enchaîne le détecteur, le moteur de remédiation et les playbooks Ansible. À droite, l'assistant RAG et Ollama sont isolés sur le PC de délestage. Dans le déploiement réel, les playbooks Ansible sont exécutés depuis la VM Host-Docker plutôt que depuis le serveur, et deux éléments du schéma ne sont pas déployés : le service `AUTH` séparé (l'authentification est dans l'API) et Uptime Kuma.

L'ensemble applicatif tourne en conteneurs Docker sur `host-resilience`. Les services se retrouvent sur un réseau Docker partagé, `resilience-net`. Nous avons fait du WAF la seule porte d'entrée HTTP : l'API, le frontal et la base ne publient aucun port sur la machine, ils sont uniquement joignables depuis ce réseau interne. La supervision vit dans sa propre stack Compose et ne rejoint `resilience-net` que pour interroger l'API. Cette séparation limite ce qu'un attaquant peut atteindre directement, et elle laisse l'équipe infrastructure faire évoluer la supervision sans toucher à l'application.

## Composants déployés

Le tableau ci-dessous reprend les conteneurs relevés sur la VM le 22 octobre (`docker ps`), avec leur exposition réelle. C'est la colonne « Exposition » qui compte pour la sécurité : tout ce qui n'est pas « interne » est joignable depuis le réseau du lab.

| Composant | Conteneur | Rôle | Exposition |
|---|---|---|---|
| WAF | `security-waf` (ModSecurity + OWASP CRS) | Filtre toutes les requêtes et les transmet à l'API | :80 |
| Proxy TLS et DNS | `edge-caddy`, `edge-dns` (CoreDNS) | HTTPS et noms internes du lab | :443, :53 |
| API métier | `app-api` (FastAPI) | Comptes, jetons JWT, dons, paiement simulé | interne |
| Frontal | `app-frontend` (React + Tailwind, Nginx) | Interface de don | interne (vue dev sur :8081) |
| Base de données | `app-db` (PostgreSQL 17) | Comptes et dons, volume persistant | interne |
| Supervision | Prometheus, Loki, Promtail, Grafana, node-exporter, cAdvisor | Métriques, journaux, tableaux de bord | :9090, :3100, :3000, :9100, :8080 |
| Détection ML | `monitoring-ml-detector` | Score des fenêtres de 15 s | interne |
| Assistant RAG | PC IA (assistant, Ollama, Qdrant) | Diagnostic d'aide à l'opérateur | :8100 sur Tailscale |

## Comment circulent les requêtes et les signaux

Une requête d'utilisateur arrive sur le port 80 du WAF, qui l'inspecte puis la transmet à l'API. Le frontal n'est pas encore routé par le WAF : l'équipe le consulte par une vue de développement sur le port 8081, et il appelle l'API sur sa propre origine (`/api/...`), ce qui évite toute configuration CORS. L'API dialogue avec PostgreSQL au travers de SQLAlchemy. Le schéma de la base est appliqué automatiquement par Alembic à chaque démarrage du conteneur, ce qui rend un redéploiement sans étape manuelle.

Côté observation, Prometheus interroge toutes les quinze secondes la route `/metrics` de l'API, cAdvisor pour les conteneurs, les node-exporters des quatre machines et le détecteur ML. L'API écrit une ligne JSON par événement sur sa sortie standard (un don traité, une connexion refusée…). Promtail récupère ces lignes avec celles de tous les autres conteneurs, dont les accès du WAF, et les range dans Loki. Toutes les quinze secondes, le détecteur ML relit ces deux sources, calcule ses indicateurs et publie un score que Prometheus compare aux règles d'alerte. L'assistant RAG reste à l'écart de ce circuit : l'opérateur l'interroge à la demande, par Tailscale.

L'API expose peu de routes, regroupées en deux familles. Les routes `/auth` permettent de créer un compte et d'obtenir un jeton valable une heure. Les routes `/donations` permettent de consulter les montants proposés, de faire un don et de relire ses propres dons (détail en annexe B). Un don est d'abord enregistré avec le statut `pending`, puis le paiement est simulé et le statut passe à `succeeded` ou `failed`. Ainsi, une tentative interrompue par une panne reste traçable en base. Le paiement simulé reconnaît trois cartes de test (acceptée, refusée, fonds insuffisants) et ajoute une latence aléatoire de 0,1 à 0,6 seconde pour que les courbes ressemblent à un vrai trafic. Seuls les quatre derniers chiffres de la carte sont conservés.

## Réseaux prévus et réseaux réels

L'architecture initiale prévoyait quatre réseaux Docker : `edge` pour les services exposés, `backend` en mode interne pour isoler l'API et la base, `resilience-net` pour la supervision, et `remediation` pour le moteur et le détecteur. Seul `resilience-net` a été mis en place, et il porte aujourd'hui à la fois l'application, le WAF, la base, Prometheus et Caddy. La base reste inaccessible depuis l'extérieur puisqu'elle ne publie aucun port, mais tout conteneur de ce réseau peut la joindre. Le cloisonnement fin prévu reste donc une étape à franchir. Il demande de modifier la configuration commune du socle, partagée par toutes les équipes, et n'a pas été engagé pendant le sprint.
