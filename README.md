# AlgoLab — Visualiseur d'algorithmes

Application Streamlit en français pour explorer six algorithmes de tri : tri à bulles, sélection, insertion, fusion, rapide et par tas.

## Prérequis

- Python 3.11 ou plus récent
- Windows PowerShell

## Installation et lancement

Depuis le dossier du projet, crée l'environnement puis installe les dépendances :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Démarre l'application depuis ce même dossier :

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit affiche l'adresse locale à ouvrir dans le navigateur, généralement `http://localhost:8501`.

## Pages

- **Accueil** : choisir une première visualisation, reprendre une recommandation issue de l'historique ou ouvrir un atelier.
- **Visualiser** : parcourir les étapes, mettre l'animation en lecture ou en pause, et consulter le pseudo-code synchronisé.
- **Comparer** : comparer les six algorithmes sur une même liste.
- **Expérimenter** : formuler une hypothèse et étudier, de façon reproductible, l'évolution des compteurs et des durées médianes selon la taille et l'ordre initial des tableaux.
- **Exercices** : s'entraîner aux niveaux débutant, intermédiaire et avancé.
- **Défi interactif** : effectuer et valider les étapes des six tris.
- **Manipulation** : agir sur le tableau pour appliquer les tris par insertion et par sélection, avec une difficulté et une distribution choisies.
- **Profil** : consulter le niveau, l'expérience, les succès débloqués, les titres équipés, les réussites enregistrées et l'historique de progression.

Le mode **Étapes** réutilise les traces des moteurs existants et vérifie l'opération ainsi que ses positions à chaque étape. Les autres modes ont des mécaniques dédiées : **Prédiction** choisit un état après une mutation réelle, **Identification** reconnaît un algorithme à son invariant, **Remise en ordre** ordonne ses étapes, **Rapidité** enchaîne des questions en 120 secondes et **Maîtrise** combine prédiction, identification et ordre. Les questions sont générées à partir d'une graine reproductible, avec corrections et indices; la série rapide récompense d'abord les bonnes réponses, pas le temps brut.

Les niveaux génèrent des tableaux de 3, 4 ou 5 valeurs; les tailles saisies manuellement restent limitées à 8. Les scores de précision sont conservés par profil et type de défi. Une expiration rapide conserve son score partiel sans XP ni réussite enregistrée. La table des meilleurs scores est ajoutée dans le SQLite existant et ne modifie pas les événements historiques.

Pour le tri fusion, le mode Étapes demande les divisions, les moitiés à fusionner, les valeurs à placer dans le tampon puis les écritures dans le tableau. Pour le tri rapide, il fait identifier le pivot central choisi par le moteur, classer les valeurs dans les trois zones et sélectionner les segments récursifs. Pour le tri par tas, il pilote le tamisage du max-heap, les comparaisons parent-enfant, les échanges et la réduction du tas actif.

Les tailles générées sont de 3, 4 et 5 valeurs selon le niveau. Le score de précision est le pourcentage d'actions validées parmi toutes les actions soumises (`actions validées / (actions validées + erreurs)`). Le détail d'une session en cours, ses erreurs et les indices affichés restent en mémoire Streamlit.

## Progression persistante

La barre latérale affiche le profil local, le niveau et l'expérience. La page **Profil** présente aussi la progression vers le prochain niveau, les succès débloqués avec leur date, les titres équipables, les défis validés enregistrés, les algorithmes réussis et l'historique des événements de progression. La section **Mon parcours** estime les compétences à partir des réussites enregistrées et propose des objectifs vers les exercices et défis existants. Elle n'accorde ni XP ni succès et ne crée aucun historique distinct. Les tentatives échouées, expériences et comparaisons ne sont pas persistées; les compétences théoriques ou de choix d'algorithme restent donc non évaluées. Les seuils sont **Débutant** (0 XP), **Apprenti** (100), **Pratiquant** (250), **Expert** (500) et **Maître** (800, niveau maximal).

- Une réponse correcte rapporte 10 XP, avec 5 XP de bonus si elle est juste au premier essai et 5 XP si aucun indice n'a été utilisé.
- Un défi terminé rapporte 20 XP en Débutant, 35 en Intermédiaire ou 50 en Avancé; terminer sans erreur ajoute 10 XP, sans indice 5 XP.
- Une manipulation terminée rapporte les mêmes paliers en Facile, Intermédiaire ou Difficile; les bonus sans erreur et sans indice suivent les mêmes règles. Chaque nouvelle manipulation réussie est admissible, mais une même partie ne rapporte qu'une fois.
- Chaque question réussie d'une session d'exercices et chaque défi terminé sont récompensés une fois par activité. Une nouvelle session, un nouveau défi ou la réinitialisation d'un défi constitue une nouvelle activité; répéter la validation ou provoquer un rerun ne crédite pas deux fois la même activité.
- Les succès uniques rapportent aussi des XP : 40 pour les six algorithmes, 25 pour une réussite sans erreur, 25 sans indice et 35 pour un défi Avancé. Chaque succès débloque un titre affichable dans le profil.

SQLite stocke les profils, les événements de récompense et les succès dans `.algolab/progression.sqlite3`, à côté de l'application. Les transactions atomiques et les clés uniques empêchent les gains en double; une erreur d'écriture annule l'opération et l'interface affiche un avertissement. Le chemin peut être remplacé avec la variable d'environnement `ALGOLAB_DB_PATH`, notamment pour les tests.

Les événements et récompenses de défi ou de manipulation ne sont enregistrés qu'une fois par activité, algorithme et difficulté; les replays ne sont donc pas comptés à nouveau. Les tentatives échouées ne sont pas persistées, ce qui ne permet pas de calculer un taux de réussite global. L'historique du profil reflète uniquement les événements effectivement enregistrés dans SQLite.

Chaque profil est déverrouillé par un code personnel de six chiffres. La base conserve un vérificateur scrypt avec sel aléatoire, jamais le code en clair; cinq essais incorrects entraînent un verrouillage temporaire. Les anciens profils gardent leur progression et doivent définir un code avant de retrouver l'accès. Comme aucun secret n'existait auparavant, la première définition du code ne peut pas vérifier rétroactivement l'identité du propriétaire historique.

L'autorisation est liée au profil dans la session et contrôlée côté serveur avant les lectures et écritures de progression. Le verrouillage efface cette autorisation et les activités en cours. Cette protection convient à une installation locale contrôlée, mais ne remplace pas une authentification serveur : une personne ayant accès au processus ou directement au fichier SQLite peut contourner les contrôles de l'interface et accéder aux données locales. La base n'est pas synchronisée.

## Déploiement public gratuit (Streamlit Community Cloud)

Community Cloud est l'option la plus directe pour cette application Streamlit : l'offre est gratuite, le code est déployé depuis GitHub et la plateforme fournit une URL `*.streamlit.app`. Le projet contient déjà son `requirements.txt`, sa configuration Streamlit et sa feuille de style. Les dépendances sont Python; aucun paquet système supplémentaire n'est requis. L'application et le CSS utilisent des chemins fondés sur `__file__`, et le stockage SQLite est créé automatiquement.

### Avant de publier

1. Créez un dépôt GitHub contenant le code de l'application (`app.py`, `algorithmes/`, `pages/`, `.streamlit/`, `requirements.txt` et ce README). N'ajoutez ni `.algolab/`, ni `.venv/`, ni `.streamlit/secrets.toml` : ils sont exclus par `.gitignore`. Vérifiez le contenu du commit avant de le pousser; la base locale peut contenir des profils et des données de progression.
2. Ouvrez [share.streamlit.io](https://share.streamlit.io/) et connectez le compte GitHub qui a accès au dépôt.
3. Choisissez **Create app**, puis le dépôt, la branche et `app.py` comme fichier d'entrée. Vous pouvez choisir un sous-domaine libre, par exemple `algolab-votre-nom`; sinon Streamlit en attribue un.
4. Dans **Advanced settings**, sélectionnez Python 3.12 (ou une version disponible et compatible). Laissez **Secrets** vide : cette application ne nécessite pas de secret de déploiement.
5. Déployez, attendez la fin du lancement, puis ouvrez l'URL `https://<sous-domaine>.streamlit.app` affichée par Streamlit. Vérifiez les pages principales et la création/connexion d'un profil avec des données de test uniquement.
6. Après validation, dans la configuration de build du portfolio, définissez `PUBLIC_ALGOLAB_URL` à cette URL publique complète (sans guillemets superflus), puis reconstruisez et redéployez le portfolio.

### Limites de stockage et de confidentialité

Community Cloud ne garantit pas la persistance des fichiers locaux. La base `.algolab/progression.sqlite3` peut donc disparaître après un redémarrage ou une reconstruction; profils, codes vérifiés, progression et records pourraient être perdus. L'application n'a pas de service de base de données externe ni de sauvegarde.

L'instance publique partage actuellement un même fichier SQLite entre tous ses visiteurs. Les noms de profils sont énumérés à l'écran d'accès avant la saisie du code. Le code personnel est stocké sous forme de vérificateur scrypt, mais ce mécanisme n'isole pas chaque visiteur dans une base privée. La clé qui signe les autorisations de session est aussi créée en mémoire au démarrage : un redémarrage invalide les sessions ouvertes. Pour ces raisons, ne saisissez pas de données personnelles ou confidentielles et ne considérez pas cette version comme un service de comptes privés ou de progression durable. Une base hébergée persistante et une séparation des profils seraient nécessaires avant cet usage; elles ne sont pas configurées ici.

Les applications gratuites Community Cloud peuvent s'endormir après une période sans visites; le premier accès suivant peut demander un délai de réveil. La région d'hébergement est actuellement les États-Unis.

## Tests

Depuis le dossier du projet :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
