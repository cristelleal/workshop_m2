---saut---

# Annexe E : compte rendu d'arbitrage de la Consigne Additionnelle 1

## Objet et décision

La Consigne Additionnelle 1 (CA1) a été reçue le mercredi 21 octobre 2026 à 15h, la veille du gel du code. Elle demande deux évolutions. La première est une authentification par reconnaissance faciale pour le back-office, avec une caméra USB installée sur le poste hôte et une gestion complète des habilitations. La seconde est un objet connecté ESP8266, piloté par le back-office, dont le premier usage est une LED bicolore.

Après analyse, la CA1 n'est pas intégrée au Lot 1, livré le jeudi 22 octobre à 23h59. Elle est requalifiée en demande de changement et reportée au Lot 2, dont l'ouverture dépend des réponses aux questions listées en fin de compte rendu et d'un chiffrage validé. Le sujet demande d'expliquer les compromis retenus (§1) et les arbitrages proposés à une direction (§3.5). Ce compte rendu en fait partie.

## Écarts avec le périmètre de référence

Le périmètre de référence est le cahier des charges remis le lundi 19 octobre et l'architecture validée par les coachs au lancement (§6). Le tableau suivant indique, pour chaque exigence du sujet concernée, ce que la CA1 modifie.

| Exigence du sujet | Réf. | Modification apportée par la CA1 |
|---|---|---|
| Détecter un incident et rétablir le service sans intervention humaine | §1, §2 | Ajoute une fonction d'authentification forte, sans rôle dans la détection ni dans la reprise |
| Microservices : base, API, authentification, frontal web | §3.1 | Suppose un back-office doté d'une page de connexion, que le sujet ne définit pas |
| Technologies prescrites (FastAPI, React, Compose, Ansible, Prometheus, Grafana, Loki) | §3.1 à §3.4 | Ajoute un modèle de vision, du C++ embarqué, PlatformIO et un IDE imposé (CLion) |
| Matériel : poste hôte, poste attaquant, poste IA facultatif | §4 | Ajoute une caméra USB, un ESP8266 et une LED bicolore, non fournis |
| Données intégralement fictives | §1 | Nécessite les visages réels de membres de l'équipe |
| Liberté d'architecture laissée à l'équipe | §1 | Impose l'emplacement physique de la caméra et l'outil de développement |
| Grille du jury local (5 critères, 20 points) | §8.2 | Aucun critère ne porte sur la CA1 |

La CA1 se présente elle-même comme une évolution : l'ESP8266 est demandé « pour prévoir l'avenir », avec un premier usage limité à une LED. Cette formulation correspond au contenu d'un lot ultérieur plutôt qu'à une correction du lot en cours.

## Impact sur le délai

Entre la réception de la CA1 et le gel du code, l'équipe disposait d'environ 11 heures ouvrées, déjà affectées aux activités prévues par le sujet.

| Plage | Heures ouvrées | Activité prévue par le sujet (§6) |
|---|---|---|
| Mercredi 21/10, de 15h à 18h | 3 h | Intégration WAF et SIEM, détection, remédiation, dashboard, premiers tests de restauration |
| Jeudi 22/10, de 9h à 17h | 8 h | Recette, injection de défaillances, Clip Chrono, gel du code à 17h |
| Jeudi 22/10, de 17h à 23h59 | 0 h de code | Dossier, présentation, archive et dépôt des rendus |

Cette capacité représente 55 heures·personne, soit environ 7 jours·homme. La CA1 en demande 17 à 26 selon le chiffrage ci-dessous. Elle ne pouvait donc pas être réalisée avant le gel du code, même en suspendant toutes les autres activités.

Trois contraintes s'ajoutent à ce calcul. Le matériel demandé (caméra, ESP8266, LED et composants) ne fait pas partie de l'équipement prévu au §4, et le sujet précise qu'aucun environnement spécifique n'est fourni (§5) : un approvisionnement aurait demandé au moins une journée. Modifier l'authentification à la veille de la livraison touchait par ailleurs le parcours que le jury utilise pour observer la reprise, alors que le critère « démonstration en direct et remédiation autonome » est noté sur 5 points et ramené à 0 en cas d'intervention humaine (§8.2). Enfin, le Clip Chrono doit être tourné sur le système final avant le dépôt (§7.3), ce qui suppose un système stable le jeudi après-midi.

En entreprise, une demande reçue à la veille d'une livraison suit le circuit de gestion des changements : analyse d'impact sur le délai, le coût et le risque, décision d'un comité, puis avenant au planning. C'est ce circuit que nous avons appliqué.

## Impact sur l'infrastructure

La CA1 ne s'ajoute pas simplement à l'architecture existante : elle touche le poste hôte, le réseau et la chaîne de déploiement.

Le premier point concerne l'accès à la caméra. Dans notre infrastructure, le poste hôte est une VM Ubuntu hébergée sur un serveur Proxmox, et les services tournent dans des conteneurs Docker. Pour qu'un service conteneurisé lise une caméra USB, celle-ci devrait être branchée physiquement sur le serveur Proxmox, transmise à la VM, puis exposée au conteneur. Dans l'environnement prévu par le sujet (Docker Desktop sous WSL2), la difficulté est comparable : le noyau WSL2 standard n'inclut pas les pilotes vidéo nécessaires, et il faudrait le recompiler. Les solutions de contournement placent la capture hors des conteneurs, donc hors du déploiement Compose et Ansible exigé (§3.2).

Le deuxième point est fonctionnel. Le back-office est une interface web accessible sur le réseau, alors que la caméra est imposée sur le poste hôte. Soit la connexion n'est possible que devant ce poste, et il ne s'agit plus d'un back-office web. Soit le visage présenté au poste hôte valide une session ouverte depuis un autre poste, et le contrôle biométrique n'est alors plus lié à la personne qui se connecte. La consigne ne précise pas lequel de ces deux fonctionnements est attendu.

Le troisième point concerne le réseau. L'ESP8266 ne fonctionne qu'en Wi-Fi 2,4 GHz. Il devrait rejoindre le réseau du lab, où se trouve aussi la machine attaquante (§4), avec un protocole de commande à concevoir et un chiffrement TLS coûteux pour ce microcontrôleur.

Le quatrième point concerne les ressources. Notre serveur dispose de 8 Go de mémoire et porte déjà l'application, le WAF, la supervision et le détecteur ML. Le sujet écarte lui-même la suite Elastic pour des raisons de charge mémoire (§3.2). Un modèle de vision supplémentaire entrerait en concurrence directe avec la supervision.

Enfin, le C++ embarqué, PlatformIO et CLion ne figurent pas dans les technologies prescrites (§3.1), et leur build, leur déploiement et leurs tests ne relèvent ni de Compose ni d'Ansible. La gestion complète des habilitations (enrôlement, mise à jour et suppression des gabarits faciaux, rôles, traçabilité, mode dégradé) constitue à elle seule un produit.

## Impact sur la sécurité et la conformité

L'analyse de la consigne telle qu'elle est rédigée fait apparaître plusieurs points de sécurité à clarifier avant toute réalisation.

| Point | Constat | Conséquence |
|---|---|---|
| Données biométriques | Un visage traité pour identifier une personne est une donnée sensible (RGPD, art. 9), dont le traitement impose une analyse d'impact (art. 35) | Incompatible avec la règle des données intégralement fictives (§1) et avec l'interdiction de fournir des données personnelles réelles aux outils d'IA (§5) |
| Verrouillage par identifiant | Deux échecs de reconnaissance bloquent le compte 5 minutes | Toute personne connaissant un identifiant peut bloquer l'administrateur de façon répétée, ce qui crée un risque de déni de service sur le back-office |
| Échec du mot de passe | Aucun verrouillage n'est prévu | La politique est plus stricte sur le facteur biométrique que sur le mot de passe |
| Usurpation | Une IA légère sans détection du vivant accepte une photo ou un écran | La protection contre l'usurpation physique visée n'est pas assurée |
| Point unique de défaillance | Le back-office dépend d'un périphérique USB | Une caméra débranchée ou défaillante rend le back-office inaccessible, sans mode dégradé prévu |
| LED de l'ESP8266 | L'objet reçoit son état depuis le réseau partagé avec la machine attaquante | Un attaquant pourrait afficher un faux état « vert ». Le sujet met en garde contre les interfaces accessibles à n'importe quel composant (§3.4) |

Certains points de la consigne restent par ailleurs à préciser : la suite de la politique de verrouillage (le « etc. »), l'enchaînement entre les 30 secondes de LED rouge et l'extinction de la caméra, le cas de plusieurs visages devant la caméra, et la personne habilitée à réaliser les enrôlements.

## Impact sur la détection et la démonstration

Le détecteur d'anomalies a été entraîné sur une baseline enregistrée le 21 octobre de 12:10 à 13:25. Sa procédure impose de ne rien changer à la collecte entre la baseline et les essais d'attaque : toute modification des exporters, des labels ou des conteneurs oblige à enregistrer une nouvelle baseline. Un service de vision ajouterait à chaque connexion des pics de CPU et de trafic sur le serveur. Comme la baseline est construite sur une charge régulière d'environ 7,25 requêtes par seconde, le modèle jugerait ces pics anormaux. Les taux de fausses alertes mesurés (5,2 % des fenêtres hors échantillon) et les évaluations sur attaques réelles ne seraient plus valables sur une plateforme modifiée après coup.

Côté démonstration, l'équipe dispose de 5 minutes pour présenter et démontrer (§8.2), et le Clip Chrono doit montrer en 60 secondes une séquence continue : attaque, anomalie, réaction, service rétabli (§7.3). Une connexion biométrique en deux étapes ajouterait un point de défaillance (éclairage, reconnaissance manquée) sur le parcours qui prouve la reprise, et consommerait du temps sans démontrer la résilience.

## Chiffrage indicatif du Lot 2

Le Lot 2 est estimé à 17 à 26 jours·homme, soit 4 à 5 jours ouvrés pour une équipe de cinq personnes, et 10 200 à 15 600 € HT au taux journalier retenu.

| Sous-lot | Contenu | Charge (j·h) |
|---|---|---|
| 2.1 Cadrage et conformité | Spécification clarifiée, analyse d'impact RGPD, mise à jour de l'EBIOS RM (nouveau bien support : gabarits biométriques) | 2 à 3 |
| 2.2 Infrastructure | Accès à la caméra depuis la VM et le conteneur, réseau Wi-Fi 2,4 GHz isolé, secrets dans un coffre | 2 à 3 |
| 2.3 Service de reconnaissance faciale | Choix du modèle, enrôlement, API, détection du vivant, réglage des taux de fausse acceptation et de faux rejet | 4 à 6 |
| 2.4 Back-office | Connexion en deux étapes, verrouillages, gestion des habilitations et des gabarits, journalisation vers le SIEM | 3 à 5 |
| 2.5 Objet connecté | Firmware ESP8266 (CLion et PlatformIO), états de la LED, canal de commande authentifié | 2 à 3 |
| 2.6 Sécurité | Modèle de menace, tests d'usurpation (photo, rejeu), durcissement | 2 à 3 |
| 2.7 Recette | Nouvelle baseline ML, non-régression de la démonstration, documentation, PCA/PRA | 2 à 3 |
| **Total** | | **17 à 26** |

Ce chiffrage repose sur un taux journalier moyen de 600 € HT, valeur fictive à ajuster, et n'inclut pas le matériel, de l'ordre de 50 € (caméra, ESP8266, LED et composants). À titre de comparaison, l'ensemble du workshop représente 20 jours·homme.

## Proposition et conditions d'ouverture du Lot 2

Nous proposons d'acter le report et d'ouvrir le Lot 2 une fois les questions ci-dessous tranchées par le commanditaire. Dans le Lot 1, sans modifier le code gelé, l'équipe livre ce compte rendu, intégré au dossier et repris dans la présentation. Elle livre aussi une architecture cible pour le Lot 2 : un service biométrique isolé, un objet connecté sur un réseau séparé de la machine attaquante, et un mode dégradé permettant d'accéder au back-office sans caméra. Un scénario « usurpation d'accès au back-office » sera ajouté à l'analyse EBIOS RM au moment de l'ouverture du Lot 2.

| N° | Question à trancher avant tout développement |
|---|---|
| 1 | Quelle base légale et quel consentement pour les visages, alors que les données du projet doivent être fictives ? |
| 2 | Quel est le périmètre exact du back-office visé, non défini dans le sujet ? |
| 3 | La connexion doit-elle se faire uniquement depuis le poste hôte ? |
| 4 | Quelle politique de verrouillage complète, y compris en cas d'échec du mot de passe ? |
| 5 | Quel mode dégradé si la caméra ou l'ESP8266 est indisponible ? |
| 6 | Quel niveau de protection contre l'usurpation est exigé ? |
| 7 | Le matériel est-il fourni par l'école ? |
| 8 | Comment la CA1 est-elle prise en compte dans la grille d'évaluation ? |

## Sources

Sujet du workshop national Bac+5 « Project Resilience-Alpha », EPSI, octobre 2026. Consigne Additionnelle 1, Workshop 2026-27 M2, reçue le 21/10/2026 à 15h. README `resilience-ml` et documentation du notebook de détection (dépôt du projet). Documentation communautaire sur l'accès aux caméras USB sous WSL2 (vertec-io, Deep-Live-Cam).
