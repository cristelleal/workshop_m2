# Analyse de risques EBIOS RM

L'analyse suit la méthode EBIOS RM sur ses trois premiers ateliers, et elle a été validée par les coachs. La version complète se trouve dans `VaultObsidian/matriceRisque.md`. Chaque scénario est coté en gravité et en vraisemblance, de 1 à 5, et sa criticité est le produit des deux.

## Atelier 1 : ce qu'il faut protéger

Nous avons identifié six valeurs métier. La première est le traitement des paiements, porté par le frontal, le WAF et l'API : c'est le cœur du service. Viennent ensuite l'authentification, qui conditionne qui peut payer, et l'intégrité des données en base, car une transaction perdue ou dupliquée après une reprise signifie que le service n'est pas vraiment rétabli. L'observabilité est aussi une valeur métier à part entière : sans métriques ni journaux, il n'y a ni détection ni enquête possibles. Nous y avons ajouté la capacité de remédiation autonome, exigée par le sujet, et l'aide à l'opérateur, qui reste une valeur d'appui.

Les événements redoutés les plus graves, cotés 5, sont un paiement indisponible au-delà de l'objectif de reprise, une transaction perdue ou dupliquée après la reprise, et le détournement du moteur de remédiation, qui dispose de droits élevés sur les conteneurs. Juste en dessous, cotés 4, figurent la compromission d'un compte, l'aveuglement de la supervision, la fuite de secrets et l'échec de la reprise pendant la démonstration.

## Atelier 2 : qui pourrait attaquer, et pourquoi

Six sources de risque ont été retenues. Un attaquant externe opportuniste cherche à perturber le service par un déni de service, et c'est le rôle que joue le PC attaquant. Un cybercriminel motivé par l'argent viserait plutôt l'injection SQL ou la fraude. Un compte compromis ou un initié malveillant chercherait à élever ses privilèges jusqu'au moteur de remédiation. Nous avons aussi retenu trois sources sans intention de nuire, mais tout aussi réelles : une défaillance interne (erreur de configuration, faux positif du ML), la chaîne d'approvisionnement (images Docker, bibliothèques, code généré par IA), et l'exposition accidentelle d'un service sur le réseau du lab.

## Atelier 3 : scénarios stratégiques

Le tableau classe les onze scénarios par criticité décroissante. La dernière colonne indique ce que le démonstrateur met réellement en face de chacun.

| ID | Scénario | G | V | C | Mesure dans le démonstrateur |
|---|---|---|---|---|---|
| SS1 | DoS applicatif sur l'API via le WAF | 5 | 4 | **20** | WAF, détection ML, remédiation Ansible |
| SS8 | Surcharge de l'hôte, reprise qui échoue en démo | 4 | 4 | 16 | Ollama délesté sur le PC IA ; limites mémoire à poser |
| SS2 | Injection SQL sur l'API | 4 | 3 | 12 | ORM paramétré, CRS 403, détection ML |
| SS3 | Force brute sur l'authentification | 4 | 3 | 12 | Échecs journalisés ; pas de verrouillage |
| SS7 | Secrets en clair dans le dépôt | 4 | 3 | 12 | gitleaks en CI ; identifiants du lab encore dans la doc |
| SS10 | Exposition de la base ou de la supervision | 4 | 3 | 12 | Base non exposée ; supervision exposée |
| SS4 | Compromission du moteur de remédiation | 5 | 2 | 10 | Ansible sur une VM dédiée, liste blanche de playbooks |
| SS5 | Faux positif ML qui coupe un service sain | 3 | 3 | 9 | 2 fenêtres consécutives, alerte « détecteur muet » |
| SS6 | Saturation ou effacement des journaux | 4 | 2 | 8 | Repli du détecteur si Loki sature |
| SS9 | Image ou bibliothèque compromise | 4 | 2 | 8 | Audits de dépendances ; images non figées |
| SS11 | Injection de prompt dans l'index RAG | 2 | 3 | 6 | Corpus interne, assistant sans droits |

Le déni de service ressort seul en zone critique (score de 20 sur 25), ce qui justifie d'en avoir fait l'attaque principale. Les quatre scénarios à 12 forment un second groupe homogène, sur lequel le démonstrateur répond surtout par le WAF et l'intégration continue. Une remarque s'impose sur SS8 : il a été coté pour un PC hôte de 16 Go. Sur la VM de 8 Go réellement utilisée, sa vraisemblance est plutôt plus forte, et l'épisode de saturation de Loki pendant un flood en a donné un avant-goût.

## AMDEC du scénario principal

Pour le déni de service, nous avons poussé l'analyse jusqu'aux modes de défaillance de nos propres défenses, avec une criticité égale au produit de la probabilité, de la gravité et de la détectabilité (1 = très détectable, 5 = indétectable).

| Mode de défaillance | P | G | D | C | État au 22/10 |
|---|---|---|---|---|---|
| Le WAF ne bloque pas le flood | 3 | 5 | 2 | 30 | Le flood atteint l'API le 21/10 (502) ; il est rejeté en 403 le 22/10 |
| Le ML ne détecte pas l'anomalie | 3 | 4 | 3 | **36** | Détecteur en production, floods du 22/10 détectés |
| Redémarrage fait, service toujours KO | 3 | 5 | 2 | 30 | Vérification par transaction à mesurer sur un run complet |
| Boucle de remédiation | 2 | 4 | 3 | 24 | Garde-fous spécifiés (section 6) |

Le mode le plus critique était l'échec de la détection, parce qu'un modèle mal entraîné ne se voit pas tant qu'une vraie attaque ne l'a pas mis en défaut. C'est là que nous avons mis le plus d'effort, et c'est le seul mode réellement couvert aujourd'hui. Les deux modes à 30 concernent le filtrage et la vérification de la reprise. Le premier a progressé entre les deux runs. Le second attend la sonde de transaction.
