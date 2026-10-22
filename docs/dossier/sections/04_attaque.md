# Scénario d'attaque

## Attaque principale : déni de service applicatif

Nous avons retenu comme attaque principale le scénario le plus critique de notre analyse de risques, SS1, coté gravité 5 et vraisemblance 4. Il s'agit d'un flood HTTP lancé depuis la VM `attacker-kali` (192.168.137.10) contre le WAF, qui est la seule entrée du système. Le but de l'attaquant est simple : rendre le paiement indisponible. Ce choix a deux avantages pour une démonstration. L'effet se voit immédiatement sur les courbes, et l'attaque se rejoue à l'identique, ce qui permet de comparer les essais entre eux.

Un premier run a été enregistré le 21 octobre. Le générateur de trafic légitime a démarré à 15:37, puis quatre floods ont été lancés depuis la Kali à 15:39, 15:42, 15:45 et 15:48. L'export Prometheus couvre 15:35 à 15:56, soit 846 860 points. Les journaux du WAF montrent que l'outil utilisé est ApacheBench 2.3, qui martèle la page `GET /`. En 21 secondes, le WAF a renvoyé 268 réponses 404 et 257 réponses 502. Ces 502 sont le signe que le WAF n'obtenait plus de réponse exploitable de l'API. Les dons légitimes, eux, continuaient de passer. L'export des journaux de ce run s'arrête malheureusement à 15:39:22, plafonné à 5 000 lignes par Loki, ce qui empêche d'en tirer une analyse complète.

D'autres floods ont été joués le 22 octobre au soir, autour de 22:00, 22:25 et 22:28. Ils sont visibles sur les captures de la section 5.

## Attaques secondaires

Les injections SQL ont été testées de deux façons. Des requêtes forgées à la main, du type `' OR 1=1--`, et un scan automatisé sqlmap ont tous reçu un 403 de la part des règles OWASP CRS. Le 22 octobre à 11:25, un scan sqlmap non annoncé a même été lancé depuis la Kali. Le WAF l'a bloqué, et le détecteur ML l'a signalé en 15 à 30 secondes, alors que l'API n'en avait rien vu, puisque les requêtes n'arrivaient jamais jusqu'à elle. Derrière le WAF, l'API reste protégée par conception : toutes ses requêtes SQL passent par l'ORM SQLAlchemy, qui les paramètre. Une sonde XSS (`<script>alert(1)</script>`) envoyée pendant le run du 21 octobre a, elle aussi, été bloquée en 403.

Enfin, la route `GET /donations/all` laisse tout utilisateur connecté lire les dons de tous les autres. Cette faille de contrôle d'accès (OWASP API1) a été laissée volontairement, pour donner à l'équipe SOC un cas d'exfiltration à détecter.

## Disponibilité ou compromission : deux réponses différentes

Le sujet demande de ne pas confondre le retour de la disponibilité avec le traitement d'une compromission, et nos réponses prévues sont effectivement de nature différente.

Face à une saturation, l'objectif est de retrouver un service qui répond et traite des dons. Il faut d'abord filtrer la source au WAF, puis redémarrer l'API si elle ne répond plus, et enfin vérifier par une vraie transaction de test. L'ordre compte : redémarrer sans filtrer ferait retomber le service aussitôt, et l'automate entrerait dans une boucle de redémarrages (voir l'AMDEC en section 10).

Face à une injection, l'enjeu n'est plus la disponibilité mais l'intégrité des données. On renforce la règle du WAF, puis on contrôle la cohérence de la base, quitte à la restaurer si des données ont été altérées.

Face à une compromission (jeton volé, secret divulgué, abus de `/donations/all`), un redémarrage ne sert à rien, car les secrets compromis restent valides. Il faut isoler le conteneur, changer la clé de signature JWT, ce qui invalide tous les jetons en circulation, redéployer depuis une image saine et conserver les journaux pour l'enquête.
