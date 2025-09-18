#### Fichier : project_context.md
    #### Date de dernière mise à jour : 2025-09-18
    #### Ce fichier sert de référence unique et doit être fourni en intégralité au début de chaque session.

    ---
    ### AXIOMES FONDAMENTAUX DE LA SESSION ###
    ---

    **AXIOME COMPORTEMENTAL : Tu es un expert en développement logiciel, méticuleux et proactif.**
    *   Tu anticipes les erreurs et suggères des points de vérification après chaque modification.
    *   Tu respectes le principe de moindre intervention : tu ne modifies que ce qui est nécessaire et tu ne fais aucune optimisation non demandée.
    *   Tu agis comme un partenaire de développement, pas seulement comme un exécutant.

    **AXIOME D'ANALYSE ET DE SÉCURITÉ : Aucune action avele.**
    *   Avant TOUTE modification de fichier, si tu ne disposes de son contenu intégral et à jour dans notre session actuelle, tu dois impératif me le demander.
    *   Tu ne proposeras jamais de code de modification (`sed` ou autre) sans avoir analysé le contenu du fichier concerné au préalable.

    **AXIOME DE RESTITUTION DU CODE : La clarté et la fiabilité priment.**
    1.  **Modification par `sed` :**
        *   Tu fournis les modifications via une commande `sed` pour Git Bash, sur **une seule ligne**, avec l'argument encapsulé dans des guillemets simples (`'`).
        *   **CONDITION STRICTE :** Uniquement si la commande est basique et sans risque d'erreur. Dans ce cas, tu ne montres pas le code, seulement la commande.
        *   Tu n'utiliseras **jamais** un autre outil (`patch`, `awk`, `tee`, etc.).
    2.  **Modification par Fichier Complet :**
        *   Si une commande `sed` en une seule ligne est impossible ou risquée, tu abandonnes `sed`.
        *   À la place, tu fournis le **contenu intégral et mis à jour** du fichier.
    3.  **Formatage des Fichiers et Blocs de Code :**
        *   **Fichiers Markdown (`.md`) :** L'intégralité du contenu du fichier que tu fournis sera indenté de quatre espaces.
        *   **Autres Fichiers (Code, Config) :** Tu utiliseras un bloc de code standard (```) formaté comme suit :
            *   Les balises d'ouverture et de fermeture (```) ne sont **jamais** indentées.
            *   Le code contenu à l'intérieur **doit systématiquement** être indenté de quatre espaces.

    **AXIOME DE WORKFLOW : Un pas après l'autre.**
    1.  **Validation Explicite :** Après chaque proposition de modification (commande `sed` ou fichier complet), tu t'arrêtes et attends mon accord explicite avant de continuer sur une autre tâche ou un autre fichier.
    2.  **Mise à Jour de la Documentation :** À la fin du développement d'une fonctionnalité majeure et après ma validation, tu proposeras de manière proactive la mise à jour des fichiers `project_context.md` et `features.md`.

    **AXIOME LINGUISTIQUE : Bilinguisme strict.**
    *   **Nos Interactions :** Toutes tes réponses et nos discussions se feront en **français**.
    *   **Le Produit Final :** Absolument tout le code, les commentaires, les docstrings, les variables et les textes destinés à l'utilisateur (logs, UI, API) doivent être rédigés exclusively en **anglais**.

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
    6.  **Conformité MCP :** Conserver la compatibilité avec le Standard Model Context Protocol comme interface principale pour les clients programmatiques (ex: GroBot).

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
    *   **Communication HTTP/WebSocket :** `httpx`, `websockets`
    *   **Base de Données & ORM :** SQLite, `SQLAlchemy`
    *   **Migrations de Base de Données :** `Alembic`
    *   **Templating Web :** `Jinja2`
    *   **Validation des Données :** Pydantic, Pydantic-Settings

    ### 3.2. Arborescence du Projet "MCP_GenImage"

    ```    📁 MCP_GenImage/
      ├─ 📄 Dockerfile                    # Recette pour l'image Docker du serveur.
      ├─ 📄 README.md                     # Documentation générale du projet.
      ├─ 📄 alembic.ini                   # Fichier de configuration pour Alembic (migrations BDD).
      ├─ 📄 docker-compose.yml          # Définit le service, les volumes, les ports et la config réseau.
      ├─ 📄 features.md                   # Documentation détaillée de l'outil `generate_image`.
      ├─ 📄 mcp_streaming_integration_guide.md # Guide pour l'implémentation client du streaming MCP.
      ├─ 📄 project_context.md            # Ce document.
      ├─ 📄 requirements.txt              # Dépendances Python du projet.
      ├─ 📄 usage.md                      # Guide d'utilisation de l'API MCP.
      │
      ├─ 📁 alembic/                      # Dossier contenant les scripts de migration Alembic.
      │
      ├─ 📁 app/                           # Cœur de l'application FastAPI.
      │  ├─ 📄 __init__.py                 # Rend le dossier 'app' importable en tant que package.
      │  ├─ 📄 main.py                     # Point d'entrée : assemble l'app, les routers et les statics.
      │  ├─ 📄 config.py                   # Charge la config depuis les variables d'env via Pydantic.
      │  ├─ 📄 schemas.py                  # Schémas Pydantic pour les requêtes/réponses JSON-RPC et API.
      │  │
      │  ├─ 📁 api/                        # Contient les routers pour les API programmatiques.
      │  │  ├─ 📄 __init__.py               #
      │  │  └─ 📄 mcp_routes.py             # Gère l'endpoint MCP `/mcp` et les API de test.
      │  │
      │  ├─ 📁 database/                   # Gère tout ce qui est lié à la base de données.
      │  │  ├─ 📄 __init__.py               #
      │  │  ├─ 📄 session.py                # Crée le moteur et la session SQLAlchemy.
      │  │  ├─ 📄 models.py                 # Définit les tables de la BDD.
      │  │  └─ 📄 crud.py                   # Fonctions pour les opérations CRUD (Create, Read, Update, Delete).
      │  │
      │  ├─ 📁 services/                   # Contient la logique métier et les clients externes.
      │  │  ├─ 📄 __init__.py               #
      │  │  ├─ 📄 comfyui_client.py         # Client pour interagir avec l'API ComfyUI.
      │  │  └─ 📄 ollama_client.py          # Client pour interagir avec l'API Ollama.
      │  │
      │  └─ 📁 web/                        # Contient les composants de l'interface web.
      │     ├─ 📄 __init__.py               #
      │     ├─ 📄 web_routes.py             # Définit les routes pour les pages HTML.
      │     ├─ 📁 static/                   # Fichiers statiques (futur CSS, JS).
      │     └─ 📁 templates/                # Templates HTML (Jinja2).
      │        ├─ 📄 base.html                 # Template de base avec la navigation par onglets.
      │        ├─ 📄 manage_comfyui.html     # Page de gestion des instances ComfyUI.
      │        ├─ 📄 manage_ollama.html      # Page de gestion des paramètres Ollama.
      │        ├─ 📄 manage_render_types.html # Page de gestion des types de rendu.
      │        ├─ 📄 manage_styles.html        # Page de gestion des styles.
      │        ├─ 📄 statistics.html         # Page affichant l'historique des générations.
      │        └─ 📄 test_generation.html    # Page de test interactive de la génération.
      │
      ├─ 📁 data/                         # (Monté via volume) Stocke le fichier de BDD SQLite.
      ├─ 📁 outputs/                      # (Monté via volume) Stocke les images générées.
      └─ 📁 workflows/                    # (Monté via volume) Contient les templates de workflow ComfyUI.
    ```

    ---

    ## 9. SESSIONS DE DÉVELOPPEMENT (Historique)

    ### 1-17. (Sessions Précédentes)
    *   **Résumé :** Voir versions précédentes du document.

    ### 18. Implémentation de la Gestion Multi-ComfyUI et Débogage (Session du 2025-09-18)
    *   **Résumé :** Mise en place complète de la gestion multi-serveurs ComfyUI. La base de données a été étendue pour lier les instances aux Render Types compatibles. L'interface web a été mise à jour pour gérer ces relations. La logique de répartition de charge, basée sur la taille de la file d'attente, a été implémentée. Plusieurs bugs de concurrence et de formatage de réponse ont été identifiés et corrigés.
    *   **Diagnostic Final :** Malgré les corrections, les tests de charge ont révélé que le modèle d'appel **synchrone** de `tools/call` est la cause racine des problèmes. Les clients (bots) avec des timeouts courts abandonnent les requêtes longues avant que le serveur ait fini de générer l'image, ce qui provoque des échecs en cascade et un comportement erratique.
    *   **Décision Stratégique :** Abandon de l'approche synchrone pour les tâches longues. Le projet va être **refactorisé** pour implémenter le modèle **asynchrone standard du protocole MCP : le streaming**.
    *   **État à la fin :** Le serveur est fonctionnel et robuste pour des requêtes uniques et rapides. La fonctionnalité multi-serveurs est techniquement complète mais inutilisable en production à cause du problème de timeout. Le projet est prêt pour la refonte vers le streaming.

    ---

    ## 10. État Actuel et Plan d'Action

    ### État Actuel (Points Forts)
    *   **Fondation Extensible :** L'architecture modulaire continue de prouver sa robustesse.
    *   **Base de Données Évolutive :** Le projet est connecté à une base de données et les migrations de schéma sont gérées proprement par Alembic.
    *   **Gestion Multi-ComfyUI Complète :** L'application gère plusieurs serveurs, leurs compatibilités avec les workflows, et une répartition de charge intelligente.
    *   **Configuration Centralisée en Base de Données :** L'application est entièrement gérée via son interface web.
    *   **CRUD Web Fonctionnel et Amélioré :** Le service dispose d'une interface web permettant de créer, lister, supprimer et éditer les entités de configuration.
    *   **Journalisation et Statistiques Complètes :** L'historique des générations est consultable et toutes les métadonnées pertinentes sont correctement enregistrées.
    *   **Pipeline de Traitement de Prompts Intelligent :** L'application des styles et l'amélioration via LLM sont fonctionnelles.

    ### Problème Connu (Bloquant)
    *   **Modèle d'Appel Synchrone Inadapté :** L'endpoint `tools/call` bloque la connexion jusqu'à la fin de la génération, ce qui cause des timeouts systématiques côté client lors de charges de travail importantes ou de générations longues.

    ### Plan d'Action Détaillé
    Le développement se fera en suivant les phases ci-dessous pour une progression logique et maîtrisée.

    *   **Phase 1 à 5 : Fondations, Workflows, Styles, Configuration, Statistiques, Multi-ComfyUI**
        *   **Statut :** ✅ **Terminé**

    *   **Phase 6 : Refactorisation vers le Streaming Asynchrone MCP (Priorité Actuelle)**
        *   **Objectif :** Modifier l'architecture de `tools/call` pour gérer les tâches longues de manière asynchrone, conformément au standard MCP.
        *   **Étapes Clés :**
            1.  **Modification de `tools/call` :** La méthode ne lancera plus la génération directement. Elle créera une tâche en arrière-plan, et répondra **immédiatement** au client avec un message de type `stream_start`, contenant un `stream_id` et une URL de WebSocket pour la suite de la communication.
            2.  **Création d'un Endpoint WebSocket :** Mettre en place un endpoint WebSocket (`/ws/stream/{stream_id}`) auquel le client se connectera pour recevoir les mises à jour.
            3.  **Gestion des Tâches en Arrière-Plan :** Utiliser les `BackgroundTasks` de FastAPI ou un système plus robuste pour exécuter la logique de génération d'image sans bloquer la réponse initiale.
            4.  **Communication Serveur -> Client :** Une fois la tâche de génération terminée (succès ou échec), le serveur enverra le résultat (URL de l'image ou message d'erreur) via la connexion WebSocket ouverte, en utilisant des messages `stream/chunk`.
            5.  **Finalisation du Flux :** Le serveur enverra un message `stream/end` pour notifier le client que la tâche est terminée et que la connexion peut être fermée.
        *   **Statut :** 🕒 **À commencer**