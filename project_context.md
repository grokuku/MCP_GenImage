#### Fichier : project_context.md
#### Date de dernière mise à jour : 2025-09-23
#### Ce fichier sert de référence unique et doit être fourni en intégralité au début de chaque session.

---
### AXIOMES FONDAMENTAUX DE LA SESSION ###
---

#### **AXIOME 1 : COMPORTEMENTAL (L'Esprit de Collaboration)**

*   **Posture d'Expert** : J'agis en tant qu'expert en développement logiciel, méticuleux et proactif. J'anticipe les erreurs potentielles et je suggère des points de vérification pertinents après chaque modification.
*   **Principe de Moindre Intervention** : Je ne modifie que ce qui est strictement nécessaire pour répondre à la demande. Je n'introduis aucune modification (ex: refactoring, optimisation) non sollicitée.
*   **Partenariat Actif** : Je me positionne comme un partenaire de développement qui analyse et propose, et non comme un simple exécutant.

#### **AXIOME 2 : ANALYSE ET SÉCURITÉ (Aucune Action Avele)**

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
7.  **Architecture Multi-Outils :** Exposer des outils distincts et spécialisés (ex: `generate_image`, `upscale_image`, `describe_image`) via l'API MCP pour une meilleure clarté et une intégration simplifiée avec les agents LLM.
8.  **Architecture Multi-Outils Étendue (Vision Future) :**
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

### 1-23. (Sessions Précédentes)
*   **Résumé :** Voir versions précédentes du document.

### 24. Finalisation de `describe`, Correction de Régression et Amélioration UX Ollama (Session du 2025-09-23)
*   **Résumé :** Cette session a finalisé l'outil `describe` et corrigé des problèmes liés à la refonte de la gestion d'Ollama.
    1.  **Implémentation Backend de `describe` :** L'outil `describe_image` a été rendu fonctionnel en ajoutant sa définition dans `schemas.py` et en implémentant la logique d'appel (y compris la gestion des WebSockets) dans `api/mcp_routes.py`.
    2.  **Intégration Frontend de `describe` :** L'interface de test a été mise à jour (`test_generation.html`) pour inclure un onglet et un formulaire dédiés au nouvel outil.
    3.  **Correction de Régression :** La disparition de l'interface de configuration pour l'amélioration des prompts a été identifiée comme une régression. Cette configuration a été réintégrée dans la page "General Settings".
    4.  **Amélioration de l'UX :** Pour éviter les erreurs de saisie, les pages de configuration "General Settings" et "Describe Tool" ont été améliorées pour lister dynamiquement les modèles disponibles sur l'instance Ollama sélectionnée, remplaçant un champ de texte par un menu déroulant.
*   **État à la fin :** Les fonctionnalités sont complètes, mais un bug critique a été découvert lors des tests.

### 25. Résolution du Bug de Connectivité Ollama en Tâche de Fond (Session du 2025-09-23)
*   **Résumé :** Cette session a été consacrée à la résolution du bug critique qui empêchait les appels à Ollama depuis les tâches de fond de FastAPI.
    1.  **Diagnostic :** L'analyse a révélé que les requêtes HTTP vers Ollama n'étaient pas envoyées, pointant vers un problème de gestion du client HTTP dans le contexte d'exécution des `BackgroundTasks`.
    2.  **Correction :** Le `OllamaClient` (`app/services/ollama_client.py`) a été refactorisé pour implémenter le protocole de gestionnaire de contexte asynchrone (`__aenter__`, `__aexit__`).
    3.  **Implémentation :** Les appels au `OllamaClient` dans `app/api/mcp_routes.py` ont été modifiés pour utiliser la syntaxe `async with`, garantissant ainsi que le cycle de vie du client `httpx` sous-jacent est géré de manière robuste et fiable par le framework asynchrone.
    4.  **Résultat :** Le bug est résolu. Les outils `describe_image` et `generate_image` (avec amélioration de prompt) sont maintenant pleinement fonctionnels.
*   **État à la fin :** Application stable et fonctionnelle.

---

## 10. État Actuel et Plan d'Action

### État Actuel (Points Forts)
*   **Périmètre Fonctionnel Complet :** Les outils `generate_image`, `upscale_image` et `describe_image` sont entièrement implémentés et stables, tant au niveau du backend que de l'interface de test.
*   **Configuration Robuste :** La configuration des services externes (ComfyUI, Ollama) est entièrement gérée via l'interface web avec une expérience utilisateur améliorée (listes dynamiques).

### Problèmes Connus
*   Aucun bug critique connu.

### Plan d'Action Détaillé

*   **Phase 1 à 10 :** ✅ **Terminé**

*   **Phase 11 : Débogage de la Connectivité Ollama en Tâche de Fond**
    *   **Objectif :** Résoudre le bug de timeout pour rendre les outils dépendant d'Ollama pleinement opérationnels.
    *   **Étapes Clés :**
        1.  **Diagnostic Avancé :** ✅ Terminé.
        2.  **Isoler le Problème :** ✅ Terminé.
        3.  **Appliquer le Correctif :** ✅ Terminé. Le bug a été résolu en refactorisant le `OllamaClient` pour utiliser un gestionnaire de contexte asynchrone (`async with`).
    *   **Statut :** ✅ **Terminé**