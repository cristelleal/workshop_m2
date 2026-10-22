# Limites et passage à l'échelle industrielle

## Limites du démonstrateur

La première limite tient à la mesure de la reprise : la boucle détection, action, vérification fonctionne, mais son délai de bout en bout reste à chronométrer et à fiabiliser sur des runs répétés. La deuxième limite tient à l'infrastructure. Application, WAF, supervision et détecteur partagent une même VM de 8 Go, si bien qu'un flood dégrade aussi les outils chargés de l'observer, comme on l'a vu quand Loki a saturé. La troisième concerne le modèle. Il a appris un « normal » très étroit, avec un seul client et une charge constante, et il ne voit pas la couche TCP. Enfin, plusieurs éléments de l'architecture initiale manquent encore : le service d'authentification séparé et la signature RS256, le ledger en partie double avec son contrôle d'intégrité, les réseaux `backend` et `remediation`, et le dashboard opérateur.

## Ce qui changerait en contexte industriel

Passer de ce prototype à un service réel ne demande pas seulement plus de machines. Plusieurs choix de conception changent de nature, comme le résume le tableau suivant.

| Domaine | Prototype | Cible industrielle |
|---|---|---|
| Disponibilité | 1 VM, sans redondance | Plusieurs instances, base répliquée (RPO proche de 0), plusieurs zones |
| Protection DoS | WAF applicatif seul | Anti-DDoS en amont, limitation de débit par client |
| Détection | Modèle statique, baseline d'1 h | Baseline de plusieurs semaines, réentraînement planifié, couplage avec le SIEM |
| Remédiation | Playbooks Ansible depuis une VM dédiée | Orchestrateur pour les redémarrages, automate réservé aux actions métier |
| Secrets | `.env` sur la VM | Coffre, rotation automatique, identité par service |
| Supervision | Ports ouverts sur le lab | Accès par SSO, réseau d'administration séparé |

Deux évolutions méritent d'être soulignées. D'abord, une partie de la remédiation que nous avons écrite avec Ansible est déjà fournie par un orchestrateur comme Kubernetes : redémarrer un conteneur qui ne répond plus est le rôle de ses sondes de vivacité. Un automate maison n'aurait alors à porter que les actions qui demandent une connaissance du métier, comme bloquer une source ou restaurer des données. Ensuite, un modèle de détection en production doit être surveillé comme n'importe quel service. Sa dérive se mesure, son réentraînement se planifie, et chaque nouvelle version doit être validée sur des attaques rejouées avant d'être déployée.
