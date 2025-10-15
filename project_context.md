#### Fichier : project_context.md
    #### Date de dernière mise à jour : 2025-10-13
    #### Ce fichier sert de référence unique et doit être fourni en intégralité au début de chaque session.
    
    ---
    ### AXIOMES FONDAMENTAUX DE LA SESSION ###
    ---
    
    #### **AXIOME 1 : COMPORTEMENTAL (L'Esprit de Collaboration)**
    
    *   **Posture d'Expert** : J'agis en tant qu'expert en développement logiciel, méticuleux et proactif. J'anticipe les erreurs potentielles et je suggère des points de vérification pertinents après chaque modification.
    *   **Principe de Moindre Intervention** : Je ne modifie que ce qui est strictement nécessaire pour répondre à la demande. Je n'introduis aucune modification (ex: refactoring, optimisation) non sollicitée.
    *   **Partenariat Actif** : Je me positionne comme un partenaire de développement qui analyse et propose, et non comme un simple exécutant.
    *   **Gestion des Ambiguïtés** : Si une demande est ambiguë ou si des informations nécessaires à sa bonne exécution sont manquantes, je demanderai des clarifications avant de proposer une solution.
    
    #### **AXIOME 2 : ANALYSE ET SÉCURITÉ (Aucune Action Aveugle)**
    
    *   **Connaissance de l'État Actuel** : Avant TOUTE modification de fichier, si je ne dispose pas de son contenu intégral et à jour dans notre session, je dois impérativement vous le demander. Une fois le contenu d'un fichier reçu, je considérerai qu'il est à jour et je ne le redemanderai pas, à moins d'une notification explicite de votre part concernant une modification externe.
    *   **Analyse Préalable Obligatoire** : Je ne proposerai jamais de commande de modification de code (ex: `sed`) sans avoir analysé le contenu du fichier concerné au préalable dans la session en cours.
    *   **Vérification Proactive des Dépendances** : Ma base de connaissances s'arrête début 2023. Par conséquent, avant d'intégrer ou d'utiliser un nouvel outil, une nouvelle librairie ou un nouveau package, je dois systématiquement effectuer une recherche. Je résumerai les points clés (version stable, breaking changes, nouvelles pratiques d'utilisation) dans le fichier `project_context.md`.
    *   **Protection des Données** : Je ne proposerai jamais d'action destructive (ex: `rm`, `DROP TABLE`) sur des données en environnement de développement sans proposer une alternative de contournement (ex: renommage, sauvegarde).
    
    #### **AXIOME 3 : RESTITUTION DU CODE (Clarté et Fiabilité)**
    
    *   **Méthode 1 - Modification Atomique par `sed`** :
        *   **Usage** : Uniquement pour une modification simple, ciblée sur une seule ligne (modification de contenu, ajout ou suppression), et sans aucun risque d'erreur de syntaxe ou de contexte.
        *   **Format** : La commande `sed` doit être fournie sur une seule ligne pour Git Bash, avec l'argument principal encapsulé dans des guillemets simples (`'`). Le nouveau contenu du fichier ne sera pas affiché.
        *   **Exclusivité** : Aucun autre outil en ligne de commande (`awk`, `patch`, `tee`, etc.) ne sera utilisé pour la modification de fichiers.
    *   **Méthode 2 - Fichier Complet (Par Défaut)** :
        *   **Usage** : C'est la méthode par défaut. Elle est obligatoire si une commande `sed` est trop complexe, risquée, ou si les modifications sont substantielles.
        *   **Format** : Je fournis le contenu intégral et mis à jour du fichier.
    *   **Formatage des Blocs de Restitution** :
        *   **Fichiers Markdown (`.md`)** : J'utiliserai un bloc de code markdown (```md) non indenté. Le contenu intégral du fichier sera systématiquement indenté de quatre espaces à l'intérieur de ce bloc.
        *   **Autres Fichiers (Code, Config, etc.)** : J'utiliserai un bloc de code standard (```langue). Les balises d'ouverture et de fermeture ne seront jamais indentées, mais le code à l'intérieur le sera systématiquement de quatre espaces.
    
    #### **AXIOME 4 : WORKFLOW (Un Pas Après l'Autre)**
    
    1.  **Validation Explicite** : Après chaque proposition de modification (que ce soit par `sed` ou par fichier complet), je marque une pause. J'attends votre accord explicite ("OK", "Appliqué", "Validé", etc.) avant de passer à un autre fichier ou à une autre tâche.
    2.  **Documentation Continue des Dépendances** : Si la version d'une dépendance s'avère plus récente que ma base de connaissances, je consigne son numéro de version et les notes d'utilisation pertinentes dans le fichier `project_context.md`.
    3.  **Documentation de Fin de Fonctionnalité** : À la fin du développement d'une fonctionnalité majeure et après votre validation finale, je proposerai de manière proactive la mise à jour des fichiers de suivi du projet, notamment `project_context.md` et `features.md`.
    
    #### **AXIOME 5 : LINGUISTIQUE (Bilinguisme Strict)**
    
    *   **Nos Interactions** : Toutes nos discussions, mes explications et mes questions se déroulent exclusivement en **français**.
    *   **Le Produit Final** : Absolument tout le livrable (code, commentaires, docstrings, noms de variables, logs, textes d'interface, etc.) est rédigé exclusivement en **anglais**.
    
    ---
    ### FIN DES AXIOMES FONDAMENTAUX ###
    ---
    
    
    ## 1. Vision et Objectifs du Projet "MCP_GenImage"
    
    Le projet "MCP_GenImage" a évolué de sa conception initiale de simple serveur d'outils MCP pour devenir un **Hub de Génération d'Images** complet et configurable. Son objectif principal est de fournir une interface centralisée, intelligente et robuste pour piloter un ou plusieurs services ComfyUI, tout en exposant des fonctionnalités standardisées (MCP) et une interface de gestion web.
    
    ### Fonctionnalités Clés Implémentées :
    1.  **Interface de Gestion Web Complète :** Une interface utilisateur robuste permet de configurer, gérer et surveiller l'ensemble des fonctionnalités du service.
    2.  **Gestion Multi-ComfyUI et Répartition de Charge :** L'application gère un parc de plusieurs serveurs ComfyUI. Les demandes de génération sont réparties intelligemment vers l'instance compatible la moins chargée, assurant performance et haute disponibilité.
    3.  **Intelligence de Prompt Augmentée :** Un serveur LLM local (via Ollama) est intégré pour manipuler et améliorer les prompts des utilisateurs avant la génération.
    4.  **Gestion Fine des Styles et des Workflows :** Les administrateurs peuvent créer des styles (fragments de prompts) et mapper des "types de rendu" à des fichiers de workflow ComfyUI spécifiques.
    5.  **Conformité MCP et Streaming :** Le service respecte le Standard Model Context Protocol, y compris le streaming asynchrone via WebSockets pour les tâches longues, assurant une intégration transparente avec les clients programmatiques (ex: GroBot).
    6.  **Architecture Multi-Outils :** Des outils distincts et spécialisés (`generate_image`, `upscale_image`, `describe_image`) sont exposés via l'API MCP pour une clarté et une intégration simplifiées.
    7.  **Générateur de Prompts Créatifs :** Un outil intelligent (`generate_prompt`) qui utilise un LLM pour construire des prompts complexes et cohérents à partir d'entrées minimales (sujet, éléments contextuels), gérant l'idéation, la sélection et le raffinement de manière autonome.
    
    ### Vision des Fonctionnalités Futures :
    1.  **Administration et Maintenance :** Intégrer des outils pour la maintenance, comme le nettoyage automatique des anciennes images, et fournir des statistiques d'utilisation encore plus détaillées.
    2.  **Architecture Multi-Outils Étendue :**
        *   **`detailer`** : Outil de retouche ciblée (inpainting) pour des zones spécifiques d'une image (visages, mains, etc.) en utilisant des workflows ComfyUI dédiés.
        *   **`edit`** : Outil d'édition d'image par instruction (instruct-pix2pix) en utilisant un modèle comme Qwen-VL via ComfyUI.
    
    ---
    
    ## 2. Principes d'Architecture Fondamentaux
    
    1.  **Isolation et Déploiement via Docker :** Le service est entièrement conteneurisé, garantissant une isolation complète des dépendances et une reproductibilité parfaite de l'environnement de production.
    2.  **Architecture Modulaire :** Le code est structuré en modules distincts par responsabilité (API, services, base de données, web) pour garantir la maintenabilité et faciliter l'ajout de nouvelles fonctionnalités sans refontes majeures.
    3.  **Persistance des Données :** Une base de données (SQLite pour sa simplicité) est utilisée pour stocker de manière persistante la configuration et les données d'exécution. Les migrations de schéma sont gérées par Alembic.
    4.  **Interface de Commande et de Gestion Séparées :** L'application expose deux types d'interfaces : une API JSON-RPC pour les commandes machine (MCP) et une interface web (HTML/Jinja2) pour la gestion et la configuration par un humain.
    5.  **Configuration Hybride :** La configuration critique de l'environnement (ex: URL de la base de données) est gérée par les variables d'environnement. La configuration des services applicatifs (instances ComfyUI, Ollama, paramètres des outils) est gérée dynamiquement via l'interface web et persistée en base de données.
    
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
      │        ├─ 📄 manage_description.html
      │        ├─ 📄 manage_ollama.html
      │        ├─ 📄 manage_prompt_generator.html
      │        ├─ 📄 manage_render_types.html
      │        ├─ 📄 manage_styles.html
      │        ├─ 📄 settings_general.html
      │        ├─ 📄 statistics.html
      │        └─ 📄 test_generation.html
      │
      ├─ 📁 data/
      ├─ 📁 outputs/
      └─ 📁 workflows/
    ```
    
    ---
    
    ## 9. SESSIONS DE DÉVELOPPEMENT (Historique)
    
    ### 1-28. (Sessions Précédentes)
    *   **Résumé :** Voir versions précédentes du document.
    
    ### 29. Débogage et Amélioration de la Flexibilité et du Contrôle de l'Outil `generate_prompt` (Session du 2025-10-13)
    *   **Résumé :** Cette session a été consacrée à la résolution d'une série de bugs subtils mais critiques dans l'outil `generate_prompt` et à l'amélioration de son comportement.
        1.  **Diagnostic Initial :** L'outil échouait systématiquement à générer des sujets et des éléments, affichant des warnings `LLM returned an empty or invalid list`.
        2.  **Débogage par Ajout de Logs :** L'ajout de logs a révélé que le LLM ne renvoyait pas une liste brute (`[...]`), mais un dictionnaire JSON contenant une liste (`{'subjects': [...]}`). La logique de validation existante, trop stricte, rejetait cette réponse pourtant valide.
        3.  **Correction de la Flexibilité :** Le code de `app/api/mcp_routes.py` a été modifié pour accepter indifféremment une liste brute ou un dictionnaire contenant une liste. Cette correction a été appliquée à la fois à la génération des sujets et à la proposition des éléments contextuels, résolvant les pannes en cascade.
        4.  **Correction du Contrôle du Sujet :** Un bug de logique a été identifié : le sujet fourni par l'utilisateur était ignoré au profit de nouvelles propositions aléatoires. Une logique conditionnelle a été implémentée : si un sujet est fourni, le LLM est désormais instruit de générer des *variations* de ce sujet ; sinon, il conserve son comportement de génération aléatoire.
        5.  **Amélioration de la Créativité :** Pour répondre à une demande de contrôle créatif, le prompt demandant des variations a été enrichi pour encourager le LLM à explorer divers univers (SF, fantasy, etc.) tout en respectant le sujet de base.
    *   **État à la fin :** L'outil `generate_prompt` est désormais robuste, flexible dans le traitement des réponses du LLM, et son comportement est plus intuitif et contrôlable par l'utilisateur. L'application est stable et prête pour les tests de validation.
    
    ---
    
    ## 10. État Actuel et Plan d'Action
    
    ### État Actuel (Points Forts)
    *   **Périmètre Fonctionnel Complet :** Les outils `generate_image`, `upscale_image`, `describe_image` et `generate_prompt` sont entièrement implémentés et stables.
    *   **Configuration Robuste :** La configuration des services externes (ComfyUI, Ollama) et des outils est entièrement gérée via l'interface web.
    *   **Haute Disponibilité et Scalabilité :** Le système peut gérer plusieurs instances ComfyUI et répartir la charge de travail entre elles.
    *   **Générateur de Prompt Fiable :** L'outil `generate_prompt` a été intensivement débogué pour être plus robuste face aux formats de réponse du LLM et plus respectueux des intentions de l'utilisateur.
    
    ### Problèmes Connus
    *   Aucun bug critique connu.
    
    ### Plan d'Action Détaillé
    
    *   **Phase 1 à 12 :** ✅ **Terminé**