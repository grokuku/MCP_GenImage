#### Fichier : project_context.md
#### Date de dernière mise à jour : 2025-09-15
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

## 6. Documentation : Le Standard Model Context Protocol (MCP)

*   **Source de Vérité :** [Dépôt GitHub Officiel](https://github.com/modelcontextprotocol/modelcontextprotocol) et [Documentation](https://modelcontextprotocol.info/docs/)

*(Section inchangée, toujours pertinente)*

---

## 9. SESSIONS DE DÉVELOPPEMENT (Historique)

### 1-11. (Sessions Précédentes)
*   **Résumé :** Les sessions précédentes ont permis de construire un service MCP robuste, entièrement configurable via une interface web, avec une gestion avancée des styles et des workflows, une intégration de LLM, une journalisation complète et une conformité totale au standard MCP. L'architecture a été solidifiée et de nombreux bugs ont été résolus pour fiabiliser la génération d'images.

### 12. Amélioration de la Page de Statistiques et Débogage de la Migration de Base de Données (Session du 2025-09-15)
*   **Résumé :** Cette session a débuté avec l'objectif d'améliorer la page de statistiques pour y inclure des données agrégées. L'implémentation a révélé que des champs manquaient dans le modèle `GenerationLog`. Après une réinitialisation et une migration propre de la base de données, il a été découvert que la logique d'écriture dans `mcp_routes.py` n'avait pas été mise à jour pour sauvegarder les nouvelles données.
*   **État à la fin :** La base de données est propre, le schéma est correct. La page de statistiques est prête, mais les nouvelles données ne sont pas encore écrites.

### 13. Correction de la Journalisation et Implémentation des Styles par Défaut (Session du 2025-09-15)
*   **Résumé :** La session a commencé par la correction du bug de journalisation. Les fichiers `schemas.py` et `mcp_routes.py` ont été mis à jour pour assurer que toutes les métadonnées de génération (type de rendu, styles, etc.) sont correctement sauvegardées. Ensuite, la fonctionnalité des "styles par défaut" a été implémentée. Cela a impliqué une modification du modèle `Style` pour y ajouter un booléen `is_default`, la création et la correction d'une migration Alembic (gestion d'une `OperationalError` de SQLite), la mise à jour du CRUD, des routes web et du template HTML pour gérer ce nouvel état, et enfin l'adaptation de la logique métier dans `mcp_routes.py` pour appliquer ces styles si aucun n'est fourni par l'utilisateur.
*   **État à la fin :** La journalisation est 100% fonctionnelle et la page de statistiques affiche des données complètes. La fonctionnalité des styles par défaut est terminée et opérationnelle.

---

## 10. État Actuel et Plan d'Action

### État Actuel (Points Forts)
*   **Fondation Extensible :** L'architecture modulaire continue de prouver sa robustesse.
*   **Base de Données Évolutive :** Le projet est connecté à une base de données et les migrations de schéma sont gérées proprement par Alembic.
*   **Schéma de Données Corrigé et Robuste :** Le schéma de la base de données est complet et correct, incluant tous les champs nécessaires à la journalisation détaillée.
*   **Configuration Centralisée en Base de Données :** L'application est indépendante de toute configuration par fichier (`.env`) et est entièrement gérée via son interface web.
*   **CRUD Web Fonctionnel et Amélioré :** Le service dispose d'une interface web permettant de créer, lister, supprimer et maintenant **éditer** les entités de configuration.
*   **Journalisation et Statistiques Complètes :** L'historique des générations est consultable via une interface web et toutes les métadonnées pertinentes sont maintenant correctement enregistrées et affichées.
*   **Styles par Défaut :** Le système peut appliquer automatiquement des styles prédéfinis aux requêtes qui n'en spécifient aucun, améliorant la qualité des générations simples.
*   **Gestion de Workflows Dynamique :** La logique de génération peut sélectionner dynamiquement des workflows, et le workflow par défaut est configurable depuis l'interface web.
*   **Pipeline de Traitement de Prompts Intelligent :** L'application des styles et l'amélioration optionnelle via un LLM (Ollama) sont fonctionnelles.
*   **Logique de Compatibilité des Styles :** Le système prévient les erreurs en validant la compatibilité entre les styles et les types de rendu.
*   **Conformité MCP Complète :** L'API `tools/call` retourne une réponse 100% conforme au standard.

### Plan d'Action Détaillé
Le développement se fera en suivant les phases ci-dessous pour une progression logique et maîtrisée.

*   **Phase 1 à 3.5 : Fondations, Workflows, Styles, Configuration Dynamique**
    *   **Statut :** ✅ **Terminé**

*   **Phase 4 : Statistiques et Maintenance**
    *   **Objectif :** Enregistrer chaque génération dans la base de données. Créer une page de statistiques. Implémenter une tâche de fond pour le nettoyage.
    *   **Statut :** ✅ **Terminé** (Tâche de nettoyage reportée)
        *   Créer une page de statistiques dans l'interface web : ✅ **Terminé**
        *   Mettre à jour la logique d'écriture des logs (`mcp_routes.py` et `schemas.py`) : ✅ **Terminé**
        *   Implémenter une tâche de fond planifiée pour supprimer les anciennes images : ⏳ **À faire (reporté)**

*   **Phase 4.5 : Améliorations d'Ergonomie**
    *   **Objectif :** Permettre de définir un ou plusieurs styles par défaut qui seront appliqués si aucune sélection n'est faite par l'utilisateur.
    *   **Statut :** ✅ **Terminé**

*   **Phase 5 : Gestion Multi-ComfyUI (Priorité Actuelle)**
    *   **Objectif :** Permettre de configurer plusieurs serveurs ComfyUI dans l'interface. Implémenter une stratégie de répartition de charge (ex: round-robin) dans le `comfyui_client`.
    *   **Statut :** 🕒 À faire