#### Fichier : project_context.md
#### Date de dernière mise à jour : 2025-09-21
#### Ce fichier sert de référence unique et doit être fourni en intégralité au début de chaque session.

---
### AXIOMES FONDAMENTAUX DE LA SESSION ###
---

#### **AXIOME 1 : COMPORTEMENTAL (L'Esprit de Collaboration)**

*   **Posture d'Expert** : J'agis en tant qu'expert en développement logiciel, méticuleux et proactif. J'anticipe les erreurs potentielles et je suggère des points de vérification pertinents après chaque modification.
*   **Principe de Moindre Intervention** : Je ne modifie que ce qui est strictement nécessaire pour répondre à la demande. Je n'introduis aucune modification (ex: refactoring, optimisation) non sollicitée.
*   **Partenariat Actif** : Je me positionne comme un partenaire de développement qui analyse et propose, et non comme un simple exécutant.

#### **AXIOME 2 : ANALYSE ET SÉCURITÉ (Aucune Action Aveugle)**

*   **Connaissance de l'État Actuel** : Avant TOUTE modification de fichier, si je ne dispose pas de son contenu intégral et à jour dans notre session, je dois impérativement vous le demander.
*   **Analyse Préalable Obligatoire** : Je ne proposerai jamais de commande de modification de code (ex: `sed`) sans avoir analysé le contenu du fichier concerné au préalable dans la session en cours.
*   **Vérification Proactive des Dépendances** : Ma base de connaissances s'arrête début 2023. Par conséquent, avant d'intégrer ou d'utiliser un nouvel outil, une nouvelle librairie ou un nouveau package, je dois systématiquement effectuer une recherche pour :
    1.  Déterminer la version stable la plus récente.
    2.  Consulter sa documentation pour identifier tout changement majeur (*breaking change*) ou toute nouvelle pratique d'utilisation par rapport à ma base de connaissances.
*   **Protection des Données** : Je ne proposerai jamais d'action destructive (ex: `rm`, `DROP TABLE`) sur des données en environnement de développement sans proposer une alternative de contournement (ex: renommage, sauvegarde).

#### **AXIOME 3 : RESTITUTION DU CODE (Clarté et Fiabilité)**

*   **Méthode 1 - Modification Atomique par `sed`** :
    *   **Usage** : Uniquement pour une modification simple, sur une seule ligne, et sans aucun risque d'erreur de syntaxe ou de contexte.
    *   **Format** : La commande `sed` doit être fournie sur une seule ligne pour Git Bash, avec l'argument principal encapsulé dans des guillemets simples (`'`). Le nouveau contenu du fichier ne sera pas affiché.
    *   **Exclusivité** : Aucun autre outil en ligne de commande (`awk`, `patch`, `tee`, etc.) ne sera utilisé pour la modification de fichiers.
*   **Méthode 2 - Fichier Complet (Par Défaut)** :
    *   **Usage** : C'est la méthode par défaut. Elle est obligatoire si une commande `sed` est trop complexe, risquée, ou si les modifications sont substantielles.
    *   **Format** : Je fournis le contenu intégral et mis à jour du fichier.
*   **Formatage des Blocs de Restitution** :
    *   **Fichiers Markdown (`.md`)** : Le contenu intégral du fichier sera systématiquement indenté de quatre espaces.
    *   **Autres Fichiers (Code, Config, etc.)** : J'utiliserai un bloc de code standard. Les balises d'ouverture et de fermeture (```) ne seront jamais indentées, mais le code à l'intérieur le sera systématiquement de quatre espaces.

#### **AXIOME 4 : WORKFLOW (Un Pas Après l'Autre)**

1.  **Validation Explicite** : Après chaque proposition de modification (que ce soit par `sed` ou par fichier complet), je marque une pause. J'attends votre accord explicite ("OK", "Appliqué", "Validé", etc.) avant de passer à un autre fichier ou à une autre tâche.
2.  **Documentation Continue des Dépendances** : Si la version d'une dépendance s'avère plus récente que ma base de connaissances, je consigne son numéro de version et les notes d'utilisation pertinentes (liens, exemples de code si la syntaxe a changé) dans le fichier `project_context.md`.
3.  **Documentation de Fin de Fonctionnalité** : À la fin du développement d'une fonctionnalité majeure et après votre validation finale, je proposerai de manière proactive la mise à jour des fichiers de suivi du projet, notamment `project_context.md` et `features.md`.

#### **AXIOME 5 : LINGUISTIQUE (Bilinguisme Strict)**

*   **Nos Interactions** : Toutes nos discussions, mes explications et mes questions se déroulent exclusivement en **français**.
*   **Le Produit Final** : Absolument tout le livrable (code, commentaires, docstrings, noms de variables, logs, textes d'interface, etc.) est rédigé exclusivement en **anglais**.

---
### FIN DES AXIOMES FONDAMENTAUX ###
---


## 1. Vision et Objectifs du Projet "MCP_GenImage"

Le projet "MCP_GenImage" a évolué de sa conception initiale de simple serveur d'outils MCP pour devenir un **Hub de Génération d'Images** complet et configurable. Son objectif principal est de fournir une interface centralisée, intelligente et robuste pour piloter un ou plusieurs services ComfyUI, tout en exposant des fonctionnalités standardisées (MCP) et une interface de gestion web.

### Fonctionnalités Clés de la Vision :
1.  **Interface de Gestion Web :** Fournir une interface utilisateur pour configurer, gérer et surveiller l'ensemble des fonctionnalités du service.
2.  **Gestion Multi-ComfyUI :** Permettre la configuration de plusieurs serveurs ComfyUI et répartir les demandes de génération entre eux (load balancing) pour améliorer la performance et la disponibilité.
3.  **Intelligence de Prompt Augmentée :** Intégrer un serveur LLM local (via Ollama) pour manipuler et améliorer les prompts des utilisateurs avant la génération.
4.  **Gestion de Styles et de Workflows :** Permettre aux administrateurs de créer, éditer et supprimer des styles prédéfinis (fragments de prompts) et de mapper différents "types de rendu" (SDXL, Upscale, Vidéo...) à des fichiers de workflow ComfyUI spécifiques.
5.  **Administration et Maintenance :** Intégrer des outils pour la maintenance, comme le nettoyage automatique des anciennes images, et fournir des statistiques d'utilisation détaillées.
6.  **Conformité MCP :** Conserver la compatibilité avec le Standard Model Context Protocol comme interface principale pour les clients programmatiques (ex: GroBot), notamment via le streaming pour les tâches longues.
7.  **Architecture Multi-Outils :** Exposer des outils distincts et spécialisés (ex: `generate_image`, `upscale_image`) via l'API MCP pour une meilleure clarté et une intégration simplifiée avec les agents LLM.

---

## 2. Principes d'Architecture Fondamentaux

1.  **Isolation et Déploiement via Docker :** Le service est entièrement conteneurisé, garantissant une isolation complète des dépendances et une reproductibilité parfaite de l'environnement de production.
2.  **Architecture Modulaire :** Le code est structuré en modules distincts par responsabilité (API, services, base de données, web) pour garantir la maintenabilité et faciliter l'ajout de nouvelles fonctionnalités sans refontes majeures.
3.  **Persistance des Données :** Une base de données (SQLite pour sa simplicité) est utilisée pour stocker de manière persistante la configuration (styles, workflows) et les données d'exécution (statistiques). Les migrations de schéma sont gérées par Alembic.
4.  **Interface de Commande et de Gestion Séparées :** L'application expose deux types d'interfaces : une API JSON-RPC pour les commandes machine (MCP) et une interface web (HTML/Jinja2) pour la gestion et la configuration par un humain.
5.  **Configuration par Variables d'Environnement :** Les paramètres critiques (connexions aux services externes comme ComfyUI) sont gérés via des variables d'environnement et un fichier `.env`, conformément aux bonnes pratiques des "12-factor app".

---

## 3. Architecture et Technologies

### 3.1. Technologies Principales
*   **Orchestration :** Docker, Docker Compose
*   **Serveur API & Web :** FastAPI
*   **Communication HTTP/WebSocket :** `httpx`, `websockets`, `aiohttp`
*   **Base de Données & ORM :** SQLite, `SQLAlchemy`
*   **Migrations de Base de Données :** `Alembic`
*   **Templating Web :** `Jinja2`
*   **Validation des Données :** Pydantic, Pydantic-Settings

### 3.2. Arborescence du Projet "MCP_GenImage"

```    📁 MCP_GenImage/
  ├─ 📄 Dockerfile
  ├─ 📄 README.md
  ├─ 📄 alembic.ini
  ├─ 📄 docker-compose.yml
  ├─ 📄 features.md
  ├─ 📄 mcp_streaming_integration_guide.md
  ├─ 📄 project_context.md
  ├─ 📄 requirements.txt
  ├─ 📄 usage.md
  │
  ├─ 📁 alembic/
  │
  ├─ 📁 app/
  │  ├─ 📄 __init__.py
  │  ├─ 📄 main.py
  │  ├─ 📄 config.py
  │  ├─ 📄 schemas.py
  │  │
  │  ├─ 📁 api/
  │  │  └─ 📄 mcp_routes.py
  │  ├─ 📁 database/
  │  │  ├─ 📄 session.py
  │  │  ├─ 📄 models.py
  │  │  └─ 📄 crud.py
  │  ├─ 📁 services/
  │  │  ├─ 📄 comfyui_client.py
  │  │  └─ 📄 ollama_client.py
  │  └─ 📁 web/
  │     ├─ 📄 web_routes.py
  │     ├─ 📁 static/
  │     └─ 📁 templates/
  │        ├─ 📄 base.html
  │        ├─ 📄 manage_comfyui.html
  │        ├─ 📄 manage_ollama.html
  │        ├─ 📄 manage_render_types.html
  │        ├─ 📄 manage_styles.html
  │        ├─ 📄 statistics.html
  │        └─ 📄 test_generation.html
  │
  ├─ 📁 data/
  ├─ 📁 outputs/
  └─ 📁 workflows/
```

---

## 9. SESSIONS DE DÉVELOPPEMENT (Historique)

### 1-20. (Sessions Précédentes)
*   **Résumé :** Voir versions précédentes du document.

### 21. Refonte vers une Architecture Multi-Outils (Session du 2025-09-21)
*   **Résumé :** Cette session a été consacrée à une refonte architecturale majeure pour intégrer l'upscale en tant qu'outil MCP distinct. L'ensemble du backend (schémas, CRUD, API) et du frontend (gestion, tests) a été adapté pour supporter une liste d'outils dynamique. La base de données a été migrée pour gérer des workflows par défaut spécifiques à chaque mode (`generation`, `upscale`).
*   **État à la fin :** Le développement de la nouvelle architecture est terminé, mais une erreur `AssertionError` au démarrage bloque les tests de validation finaux.

### 22. Débogage et Finalisation de l'Architecture Multi-Outils (Session du 2025-09-21)
*   **Résumé :** Cette session a été dédiée à la stabilisation de la nouvelle architecture.
    1.  **Correction de l'Erreur WebSocket :** L' `AssertionError` a été résolue en corrigeant la logique de construction de l'URL WebSocket dans `mcp_routes.py` pour qu'elle n'inclue pas le chemin des fichiers statiques.
    2.  **Correction du Logging d'Upscale :** Un bug de validation Pydantic qui empêchait de logger les erreurs d'upscale (quand le prompt était `None`) a été corrigé.
    3.  **Correction de l'Upload d'Image :** Une erreur `Session is closed` dans le client ComfyUI a été résolue en corrigeant la portée de la session `aiohttp` pour englober à la fois le téléchargement et l'envoi de l'image.
    4.  **Amélioration de l'Interface de Test :** La page de test a été modifiée pour afficher tous les `RenderTypes` (y compris ceux cachés), facilitant ainsi le débogage pour l'administrateur.
    5.  **Diagnostic de Configuration :** Plusieurs erreurs de type `ValueError` ont été identifiées comme des problèmes de configuration (un `RenderType` non associé à une instance ComfyUI), et les instructions pour les résoudre ont été fournies.
*   **État à la fin :** Tous les bugs identifiés sont résolus. L'architecture multi-outils est pleinement fonctionnelle pour la génération et l'upscale. Le projet est considéré comme stable.

---

## 10. État Actuel et Plan d'Action

### État Actuel (Points Forts)
*   **Architecture Multi-Outils Robuste :** L'API expose des outils clairs et distincts (`generate_image`, `upscale_image`), ce qui est idéal pour les intégrations futures.
*   **Fondation Extensible :** La base de données et la logique métier sont prêtes à accueillir de nouveaux modes (inpainting, etc.) avec un effort minimal.
*   **Gestion Fine des Workflows :** Chaque outil peut avoir son propre ensemble de workflows et son workflow par défaut, configurable via l'interface web.
*   **Pipeline de Traitement Complet :** Le système gère l'ensemble du cycle de vie, de l'application de styles à l'injection de paramètres multiples (seed, denoise, résolution) dans des workflows ComfyUI dynamiques.

### Problèmes Connus
*   Aucun problème bloquant connu. Le service est stable.

### Plan d'Action Détaillé

*   **Phase 1 à 7 :** ✅ **Terminé**

*   **Phase 8 : Refonte vers une Architecture Multi-Outils**
    *   **Objectif :** Remplacer le "super-outil" `generate_image` par des outils MCP distincts et spécialisés pour une meilleure clarté et extensibilité.
    *   **Étapes Clés :**
        1.  **Décision Architecturale :** ✅
        2.  **Migration de la Base de Données (Defaults par Mode) :** ✅
        3.  **Refonte des Schémas Pydantic (Un Schéma par Outil) :** ✅
        4.  **Mise à Jour des CRUD :** ✅
        5.  **Mise à Jour de l'Interface Web (Gestion & Tests) :** ✅
        6.  **Refonte de l'API MCP (`tools/list` dynamique, `tools/call` routeur) :** ✅
        7.  **Mise à Jour du Client ComfyUI :** ✅
        8.  **Débogage des Régressions et Erreurs de Démarrage :** ✅ **Terminé**
    *   **Statut :** ✅ **Terminé**

*   **Phase 9 : Amélioration de l'Expérience Administrateur (UX)**
    *   **Objectif :** Rendre l'interface de gestion plus professionnelle et agréable.
    *   **Étapes Clés :**
        1.  Intégration d'un framework CSS (Bootstrap, etc.).
        2.  Ajout de JavaScript pour une meilleure interactivité (validation, etc.).
        3.  Amélioration de la page de statistiques (graphiques).
    *   **Statut :** 🚧 **À faire**