# Résultats des essais

## Chronologie

Les essais se sont enchaînés sur deux jours. Le tableau ci-dessous les reprend dans l'ordre, avec la source qui permet de vérifier chaque résultat.

| Date et heure | Essai | Résultat | Source |
|---|---|---|---|
| 21/10, 12:10–13:25 | Enregistrement de la baseline saine | 249 fenêtres exploitables, premier modèle à 71 indicateurs | `IA/ml/README.md` |
| 21/10, 15:37–15:56 | 4 floods ApacheBench depuis la Kali | Le WAF renvoie des 502 dès le premier flood | `IA/export_attaque/` |
| 22/10, matin | Correctifs du détecteur | Modèle à 63 indicateurs, repli si Loki ne répond pas | `IA/ml/train.py`, `detector.py` |
| 22/10, 11:25 | Scan sqlmap non annoncé | Bloqué en 403 par le WAF, détecté en 15 à 30 s | journaux du WAF, détecteur |
| 22/10, 21:59–22:37 | Floods depuis la Kali | Trois épisodes détectés et expliqués, flood rejeté en 403 à 22:28 | figures 3 et 4 |

Cette progression a été voulue. Le premier run d'attaque a servi à vérifier que l'attaque avait un effet visible et que la collecte tenait la charge. Les correctifs du lendemain matin ont été faits à partir de ce que ce run et la première nuit de production avaient révélé. Les essais du soir ont ensuite été lancés sur le modèle corrigé, avec le dashboard Grafana pour montrer l'avant, le pendant et l'après.

## Résultats face aux objectifs

Pour la détection, le résultat le plus net est le scan sqlmap du 22 octobre : bloqué par le WAF et signalé par le modèle en 15 à 30 secondes, alors que l'API ne l'avait pas vu. Les floods du soir sont détectés dans la même minute que le pic de trafic sur le WAF, et le panneau d'explication pointe les bons indicateurs : réseau du WAF et débit HTTP pendant le flood, taille des requêtes quand le trafic légitime disparaît. Le délai exact, à la seconde, reste à extraire des journaux du détecteur.

Les fausses alertes restent le point sensible. 5,2 % des fenêtres saines sont jugées anormales lors de la validation hors échantillon. En exigeant deux fenêtres consécutives, une alerte ne part que lorsque l'anomalie dure. Ce taux reste trop élevé pour brancher le modèle seul sur une action corrective, comme expliqué en section 6.

La remédiation Ansible est active. Le délai de reprise de bout en bout reste à mesurer sur un run complet pour être comparé à l'objectif de deux minutes. Pour la perte de données, nous n'avons pas fait de test de restauration. Le choix d'enregistrer chaque don en `pending` avant le paiement garantit néanmoins qu'une tentative interrompue par une panne reste visible en base, au lieu de disparaître.

## Problèmes rencontrés et corrections

Le premier modèle s'est mis à alerter en continu le 22 octobre au matin. En cherchant pourquoi, nous avons constaté que la mémoire du WAF était passée de 115 à 288 Mo en 21 heures, sans attaque : le modèle prenait le vieillissement normal d'un conteneur pour une anomalie. Les jauges mémoire ont été retirées. Le même examen a montré une erreur syslog toutes les 90 secondes environ, émise par la VM, qui produisait de fausses alertes régulières. Cet indicateur a lui aussi été retiré.

Pendant un flood, Loki a saturé et mettait plus de 30 secondes à répondre. Le détecteur perdait alors des fenêtres au moment précis où il devait voir l'attaque. Il bascule désormais sur les seules métriques Prometheus quand Loki ne répond pas en 8 secondes, et signale ce mode dégradé dans Grafana.

Nous avons aussi découvert que chaque connexion SSH sur la VM produisait une à trois fenêtres anormales, parce que le journal d'authentification fait partie des indicateurs. Plutôt que de retirer cet indicateur, utile pour repérer une intrusion, nous avons adopté une règle d'exploitation : personne ne se connecte au serveur pendant une démonstration.

Enfin, l'export des journaux du run du 21 octobre s'est arrêté à 15:39:22, plafonné à exactement 5 000 lignes, la limite d'une requête Loki. Les journaux des floods sont donc presque absents de cet export. L'outil d'export du dépôt (`IA/ml/export.py`) récupère les journaux par tranches de cinq minutes et pagine les résultats. Il est à utiliser pour les prochains runs, afin de ne plus atteindre cette limite.
