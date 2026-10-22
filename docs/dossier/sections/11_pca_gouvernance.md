# Continuité, conformité et gouvernance

## Objectifs de reprise

Les objectifs de reprise découlent directement des valeurs métier de l'analyse de risques. Le tableau met en regard la cible de chaque valeur et ce qui est démontré aujourd'hui.

| Valeur métier | RTO | RPO | Mécanisme prévu | Démontré |
|---|---|---|---|---|
| Paiements (WAF, API, frontal) | ≤ 2 min | 0 | Détection ML, playbook Ansible, transaction de test | Détection et remédiation actives, délai à mesurer |
| Authentification | ≤ 2 min | 0 | Redémarrage, réinjection des secrets | Non |
| Intégrité des données | ≤ 5 min | ≤ 5 min | Restauration et contrôle de cohérence | Non |
| Observabilité | ≤ 10 min | ≤ 1 h | Redéploiement Compose, volumes dédiés | Non testé |
| Remédiation autonome | ≤ 5 min | n.a. | Redéploiement, modèle versionné | Détecteur redéployable en une commande |
| Assistant | ≤ 1 h | ≤ 24 h | Reconstruction de l'index | Non testé |

Le paiement porte l'objectif le plus exigeant : deux minutes d'interruption au plus et aucune transaction validée perdue. Ce délai est court, mais il reste atteignable par un automate, à condition qu'aucune étape n'attende un humain. C'est pour cette raison que la reprise doit être automatique. L'assistant, à l'inverse, peut attendre une heure, car son absence ne bloque aucun paiement.

## PCA et PRA du démonstrateur

Le plan distingue ce que l'on fait pendant l'incident pour continuer à servir (continuité) et ce que l'on fait ensuite pour revenir à l'état nominal (reprise). Face à un déni de service, la continuité passe par le blocage de la source au WAF, qui préserve le trafic légitime. La reprise passe par le redémarrage de l'API si elle ne répond plus, puis par trois dons de test. C'est au moteur de remédiation de s'en charger, et à défaut à l'opérateur. Face à une injection ou à une altération de données, on renforce la règle du WAF, puis l'opérateur contrôle la cohérence de la base et restaure si nécessaire, avec une validation métier. Face à une compromission, l'équipe cyber isole le conteneur, change la clé JWT, redéploie l'image saine et conserve les journaux. Si la VM entière est perdue, l'équipe infrastructure recrée les machines sur Proxmox et redéploie l'application avec la procédure de `docs/deploimentAuto.md`. Enfin, si le détecteur ML tombe, l'alerte « détecteur muet » prévient l'opérateur, qui garde la supervision classique de Grafana le temps de redéployer le conteneur.

Les rôles sont répartis ainsi. L'opérateur reçoit les alertes et valide les escalades. L'automate exécute le catalogue fermé de playbooks. L'équipe infrastructure maintient les VM, l'équipe cyber gère les secrets et le WAF, et l'équipe IA maintient le modèle, qu'elle doit réentraîner après tout changement dans la collecte. Deux consignes protègent la base pendant une intervention : ne jamais lancer `docker compose down -v` dans `/opt/resilience/app`, car cette commande supprime le volume de données, et ne jamais changer le mot de passe PostgreSQL sur une base existante.

Pour ce prototype, plusieurs risques résiduels sont acceptés : un seul hôte sans redondance, un délai de reprise de bout en bout encore à mesurer, une supervision exposée sur le réseau du lab, des secrets hors coffre, et environ 5 % de fenêtres faussement anormales.

## NIS2 et DORA

Un prototype de quatre jours ne peut pas prétendre à la conformité, mais il peut montrer qu'il produit les preuves que ces textes demandent. Le tableau sépare ce qui est démontré de ce qui reste hors de portée.

| Exigence | Démontré par le prototype | Hors de portée en 4 jours |
|---|---|---|
| DORA : gestion des incidents TIC | Détection, journaux centralisés, alertes horodatées et expliquées | Classification réglementaire, rapport aux autorités |
| DORA : tests de résilience | Runs d'attaque reproductibles et enregistrés, contrôles synthétiques | Tests TLPT par un tiers, programme annuel |
| DORA : risque lié aux tiers | Dépendances auditées en CI | Registre et contrats des prestataires |
| NIS2 : gestion des risques | EBIOS RM, cloisonnement de l'API et de la base, WAF, supervision | Coffre à secrets, sauvegardes testées, durcissement complet |
| NIS2 : notification | Chronologie complète dans Loki et Prometheus | Notification sous 24 h et 72 h |
| Gouvernance | Rôles du PCA définis | Validation par la direction, formation |

Pour DORA, le point fort est la traçabilité. Chaque alerte est horodatée, expliquée par ses indicateurs et conservée avec les journaux qui l'entourent. C'est la matière première d'un rapport d'incident, et l'assistant RAG peut aider à le rédiger. Pour NIS2, le prototype montre des mesures techniques concrètes (cloisonnement, filtrage, supervision). Il ne couvre ni les obligations de notification ni la responsabilité de la direction, qui relèvent de l'organisation et non de l'outillage.

## Arbitrage de périmètre : Consigne Additionnelle 1

Le mercredi 21 octobre à 15h, soit la veille du gel du code, le commanditaire a transmis une Consigne Additionnelle (CA1). Elle demande une authentification par reconnaissance faciale pour le back-office, avec une caméra USB sur le poste hôte et une gestion des habilitations, ainsi qu'un objet connecté ESP8266 piloté par le back-office. Après analyse, le consortium a décidé de ne pas l'intégrer au Lot 1 et de la requalifier en demande de changement, reportée au Lot 2 sous réserve de clarifications et d'un chiffrage validé.

Cette décision repose sur quatre constats. Le délai d'abord : environ 11 heures ouvrées séparaient la réception du gel du code, et elles étaient déjà affectées à l'intégration, à la recette et aux rendus prévus par le sujet. Le périmètre ensuite : la CA1 introduit deux sous-projets nouveaux, la biométrie et l'objet connecté, qui ne participent ni à la détection d'un incident ni au rétablissement du service, et qu'aucun critère de la grille d'évaluation ne couvre. L'infrastructure aussi : il faudrait du matériel non fourni, un nouvel équipement sur le réseau du lab et un accès à une caméra USB depuis un conteneur exécuté dans une VM distante. La sécurité et la conformité enfin : le traitement de visages réels contredit la règle des données intégralement fictives, et le verrouillage demandé ouvre un nouveau risque de déni de service sur le back-office. Le chiffrage indicatif du Lot 2 s'élève à 17 à 26 jours·homme, soit davantage que la charge totale du workshop.

Le compte rendu complet, avec l'analyse d'impact, le chiffrage par sous-lot et les questions à trancher avant d'ouvrir le Lot 2, figure en annexe E.
