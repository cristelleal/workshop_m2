# Contexte, périmètre et écarts assumés

## Le sujet

Le sujet demande de prouver en direct la chaîne complète d'un incident. Une attaque contrôlée part d'un second ordinateur. L'incident est détecté par un modèle de machine learning plutôt que par des seuils codés en dur. Le service se répare ensuite seul, grâce à un moteur de remédiation qui pilote des playbooks Ansible. Enfin, une nouvelle transaction fictive réussie prouve que le service est vraiment revenu. Le jury insiste sur ce dernier point : redémarrer un conteneur ne prouve rien si le paiement ne fonctionne toujours pas, d'où l'exigence de montrer l'état avant, pendant et après l'incident. Cinq piliers sont évalués : développement, infrastructure, IA et data, cybersécurité, gouvernance.

## Ce qui a été livré

Le tableau suivant résume, pilier par pilier, ce qui fonctionnait au moment du gel du code. Il sert de fil conducteur au reste du dossier.

| Pilier | État au gel du code |
|---|---|
| Développement | API avec authentification intégrée, frontal et base livrés. Dashboard ops non livré |
| Infrastructure | Docker Compose, supervision (Prometheus, Loki, Grafana) et remédiation Ansible actifs |
| IA / data | Détecteur ML en production. Assistant RAG livré sur une branche, hors `main` |
| Cybersécurité | Attaques réelles depuis la Kali, WAF en place, VM SOC supervisée. Pas de Vault/SOPS, durcissement partiel |
| Gouvernance | EBIOS RM et objectifs RTO/RPO validés. PCA/PRA et analyse NIS2/DORA rédigés dans ce dossier |

Le développement et la supervision ont avancé vite parce qu'ils s'appuyaient sur un socle préparé dès le premier jour sur la VM : réseau Docker partagé, base de données, Prometheus et Loki déjà branchés. La détection ML a pu démarrer dès que du trafic légitime a circulé. La remédiation, elle, dépendait de tout le reste : il fallait une alerte fiable avant de pouvoir automatiser une action. Elle a donc été branchée en dernier, avec Ansible piloté depuis la VM Host-Docker.

## Infrastructure réelle

Le sujet prévoit un PC hôte Windows avec Docker Desktop, d'au moins 16 Go, relié aux autres machines par le hotspot Windows. Nous avons choisi à la place des machines virtuelles Ubuntu sur un serveur Proxmox, avec un accès d'équipe par Tailscale. Le plan d'adressage `192.168.137.0/24` du sujet a été conservé.

| VMID | Machine | Rôle | Adresse |
|---|---|---|---|
| 5010 | `host-resilience` | Serveur du SI : 6 vCPU, 8 Go, Docker | 192.168.137.1 |
| 5011 | `attacker-kali` | PC attaquant | 192.168.137.10 |
| 5012 | `soc-resilience` | VM SOC / SIEM | 192.168.137.2 |
| 5013 | `Host-Docker` | Second hôte Docker, dédié à Ansible | 192.168.137.20 |

Ce choix nous a donné un environnement reproductible, avec des instantanés, sur lequel les cinq membres travaillaient en même temps, et des machines réellement séparées pour l'attaquant et pour le SOC. Il a un coût : avec 8 Go sur le serveur, un modèle de langage ne peut pas tourner à côté de la supervision. L'architecture initiale estimait à 5 ou 6 Go la mémoire d'un modèle de 8 milliards de paramètres. L'assistant RAG a donc été déplacé sur un PC dédié.

## Autres écarts assumés

Le métier simulé est une plateforme de dons plutôt qu'un paiement générique. Le parcours reste le même (compte, montant, paiement simulé, statut), mais le ledger en partie double et le contrôle de cohérence prévus dans l'architecture initiale n'ont pas été implémentés. L'authentification est intégrée à l'API au lieu d'être portée par un service séparé : c'était plus rapide à livrer, mais la connexion tombe désormais en même temps que l'API. Enfin, le code de l'équipe est versionné dans le dépôt GitHub du consortium et déployé sur la VM par `rsync` ou par clone Git. Le dépôt `/opt/resilience` du serveur ne contient que son commit d'initialisation.
