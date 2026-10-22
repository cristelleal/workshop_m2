# Sécurité et durcissement

## Mesures en place

La première ligne de défense est le WAF. Toutes les requêtes HTTP passent par ModSecurity et les règles OWASP CRS avant d'atteindre l'API, et les essais ont montré qu'il bloque en 403 les injections SQL, les sondes XSS et le scan sqlmap. Il tient aussi une liste de blocage d'adresses IP (`blocklist.conf`), que le futur moteur de remédiation doit pouvoir alimenter. Derrière lui, aucun service applicatif ne publie de port : l'API, le frontal et la base ne sont joignables que depuis le réseau Docker interne. Un attaquant qui contournerait le WAF n'aurait donc pas de chemin direct vers la base.

L'API a été écrite pour limiter les dégâts si une requête malveillante passait quand même. Les mots de passe sont hachés avec l'algorithme recommandé par la bibliothèque pwdlib (Argon2). Les jetons JWT expirent au bout d'une heure, et l'algorithme accepté à la vérification est fixé, ce qui bloque les attaques par changement d'algorithme. L'API refuse même de démarrer si la clé de signature fait moins de 32 caractères : une clé faible permettrait de forger des jetons. Toutes les requêtes SQL passent par l'ORM, qui les paramètre. Les dons ont des identifiants aléatoires (UUID), impossibles à deviner, et consulter le don d'un autre utilisateur renvoie une erreur 404 plutôt qu'un refus, pour ne pas révéler son existence. Le paiement est simulé, sans aucun prestataire, et seuls les quatre derniers chiffres de la carte sont stockés.

Le détecteur ML montre le niveau de durcissement que nous visons pour tous les conteneurs. Il tourne avec un utilisateur non privilégié, sur un système de fichiers en lecture seule, sans aucune capacité Linux, avec une limite de mémoire et de CPU et sans port publié. L'assistant RAG exige une clé d'API et n'écoute que sur l'adresse Tailscale du PC IA. Enfin, la chaîne d'intégration continue cherche les secrets commités (gitleaks) et les dépendances vulnérables (pip-audit, npm audit).

## Points faibles connus

Plusieurs faiblesses restent ouvertes. Nous les listons parce qu'elles feraient partie des premières corrections avant toute mise en service.

La supervision est trop exposée. Prometheus, Grafana, Loki, node-exporter et cAdvisor sont publiés sur toutes les interfaces de la VM, et Prometheus comme Loki n'ont pas d'authentification. N'importe quelle machine du lab peut donc lire les métriques et les journaux. Il faudrait les limiter à l'interface locale, ou les placer derrière Caddy avec une authentification.

La gestion des secrets est minimale. Ni Vault ni SOPS n'ont été mis en place pendant le sprint. Le mot de passe de la base et la clé JWT sont dans un fichier `.env` lisible par son seul propriétaire. Grafana garde un mot de passe administrateur par défaut si la variable correspondante n'est pas définie, et les identifiants du lab figurent en clair dans la documentation d'onboarding versionnée.

Les conteneurs applicatifs ne sont pas durcis. L'API, le frontal et la base tournent en root, sans système de fichiers en lecture seule ni limite de ressources. Un flood peut donc consommer toute la mémoire du serveur et dégrader aussi la supervision. Les images utilisent l'étiquette `latest` au lieu d'une version figée. Côté supervision, cAdvisor tourne en mode privilégié, et Promtail monte le socket Docker. Ce montage est déclaré en lecture seule, mais cela ne protège rien : le socket reste une interface complète capable de lancer ou d'arrêter des conteneurs. Un composant de supervision compromis pourrait donc prendre la main sur tout le serveur.

D'autres écarts touchent l'application. Un seul rôle PostgreSQL sert à tout, au lieu d'un rôle par service. Les jetons sont signés en HS256 avec une clé partagée, alors que l'architecture prévoyait du RS256, où seul le service d'authentification détient la clé privée. Trois failles ont été laissées volontairement pour l'exercice : `GET /donations/all` expose les dons de tous les utilisateurs, `/metrics` et `/docs` sont publics via le WAF, et `/auth/login` n'a aucune limitation de débit. Enfin, le job de tests de la CI lance `npm` à la racine du dépôt, où il n'y a pas de `package.json`. Il échoue donc et ne protège pas la branche principale.

## Privilèges de la remédiation

La remédiation est le composant le plus puissant du système, puisqu'elle peut agir sur les conteneurs. Le scénario SS4 de notre analyse de risques, sa compromission, est coté gravité 5. Trois choix limitent ce risque. Ansible s'exécute depuis une VM dédiée, distincte du serveur applicatif : compromettre l'application ne donne pas la main sur la remédiation. Seuls des playbooks écrits à l'avance sont exécutés, ce qui exclut toute commande libre. Enfin, l'assistant RAG n'a aucun lien avec la remédiation : il lit des documents, il n'agit pas.
