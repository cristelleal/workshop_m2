# Remédiation automatique et preuve de reprise

## Une chaîne de reprise sans intervention humaine

La remédiation est active. Elle repose sur des playbooks Ansible exécutés depuis la VM Host-Docker (192.168.137.20), dédiée à Ansible et distincte du serveur applicatif. Lorsqu'un incident est détecté, ces playbooks agissent sur la plateforme, et le service est ensuite contrôlé par des requêtes réelles envoyées à travers le WAF. La chaîne enchaîne donc trois étapes. Le détecteur ML repère l'anomalie et lève l'alerte `MLAnomalieDetectee` après deux fenêtres anormales consécutives. Ansible applique la correction. Enfin, des requêtes HTTP confirment que l'API répond de nouveau.

Ce découpage répond à une exigence centrale du sujet : un redémarrage ne prouve rien tant que le parcours métier ne fonctionne pas. La vérification ne se limite donc pas à l'état d'un conteneur. Elle passe par les mêmes routes que les utilisateurs, à travers le même WAF.

## Principes retenus

Les actions de remédiation sont déterministes. Ansible n'exécute que des playbooks écrits à l'avance. Aucun modèle de langage n'intervient dans la décision : l'assistant RAG n'a aucun accès à Ansible ni à Docker, et la réponse d'un LLM, par nature non reproductible, n'a pas sa place dans une action sur la production.

La remédiation est séparée de ce qu'elle protège. Comme Ansible tourne sur sa propre VM, un attaquant qui prend pied sur le serveur applicatif n'obtient pas pour autant les moyens d'agir sur toute la plateforme. Ce choix répond directement au scénario SS4 de l'analyse de risques, la compromission de la remédiation, coté gravité 5.

Chaque action laisse une trace. Les requêtes émises par Ansible passent par le WAF et apparaissent dans ses journaux, centralisés dans Loki. On peut ainsi reconstituer après coup ce qui a été fait, et à quel moment.

## Ce que montrent les essais du 22 octobre

Les captures de la section 5 (figures 3 et 4) et les journaux du WAF permettent de suivre un cycle complet. Vers 22:27, un flood ApacheBench part de la Kali (192.168.137.10), et le trafic reçu par le WAF monte brusquement. Le détecteur passe en anomalie dans la minute qui suit. À 22:28:20, les requêtes d'ApacheBench sont rejetées en 403 par le WAF : la source est filtrée à l'entrée. Neuf secondes plus tard, à 22:28:29, une requête émise par Ansible (`ansible-httpget`) depuis la VM Host-Docker interroge la route d'inscription de l'API à travers le WAF. Elle obtient une réponse 409, qui signifie que le compte de test existe déjà : l'API et la base répondent. Les dons légitimes reprennent vers 22:36, et le détecteur revient à l'état normal vers 22:37, comme le montre la chronologie de la figure 3.

Cette séquence montre ce que le sujet demande de voir : l'état avant l'attaque, l'anomalie détectée et expliquée, la réaction, puis le retour du trafic métier.

## Maîtriser les risques de l'automate

Un automate qui agit seul peut aussi provoquer l'incident qu'il cherche à éviter. Notre AMDEC relève deux risques de ce type : un faux positif peut déclencher une action sur un service sain, et une attaque qui continue peut entraîner une boucle d'actions. Deux mécanismes du détecteur réduisent le premier risque. Une alerte n'est levée qu'après deux fenêtres anormales consécutives, ce qui écarte les pics isolés. L'alerte `MLDetecteurMuet` signale un détecteur arrêté, pour qu'une panne de la détection ne passe pas pour du calme. Contre le second risque, le filtrage de la source au WAF, observé le 22 octobre, évite qu'une attaque toujours en cours sature de nouveau le service.

Avec 5,2 % de fenêtres saines jugées anormales, le taux de fausses alertes reste le point de vigilance. L'équipe a discuté de deux façons de relier la détection à l'action. Dans la première, le ML déclenche l'action, à condition que deux fenêtres consécutives soient anormales et que du trafic légitime soit présent. Dans la seconde, le ML surveille et explique, tandis que l'action part de règles explicites (erreurs 5xx, `/healthz`, débit du WAF).

## Budget de reprise

L'objectif de reprise du paiement est de deux minutes. Nous l'avons découpé en quatre étapes : au plus 30 secondes pour détecter, 10 pour décider, 60 pour exécuter le playbook et 20 pour vérifier. Sur les captures du 22 octobre, l'alerte apparaît dans la même minute que le pic de trafic du WAF, ce qui est conforme au budget de détection. Le filtrage de la source et la première vérification Ansible se suivent à neuf secondes d'écart. Le délai total, de la première fenêtre anormale au retour complet des dons légitimes, est la mesure à suivre d'un essai à l'autre pour le comparer à l'objectif de deux minutes.
