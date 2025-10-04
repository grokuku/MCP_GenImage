#### Fichier : project_context.md
#### Date de dernière mise à jour : 2025-10-04
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

### 1-26. (Sessions Précédentes)
*   **Résumé :** Voir versions précédentes du document.

### 27. Correction de Cohérence et Bug de Régression sur la Page de Test (Session du 2025-10-04)
*   **Résumé :** Cette session a été dédiée à la validation et à la correction de l'interface utilisateur pour l'outil `generate_prompt`.
    1.  **Incohérence des Styles :** Une analyse a révélé une incohérence : la page de test affichait tous les styles actifs pour le `generate_prompt`, alors que l'outil ne doit utiliser que les styles spécifiquement autorisés dans sa propre configuration.
    2.  **Correction en Deux Étapes :** La correction a été implémentée en modifiant d'abord la route `test_generation` dans `app/web/web_routes.py` pour qu'elle récupère et transmette la liste correcte des styles autorisés. Ensuite, le template `app/web/templates/test_generation.html` a été mis à jour pour utiliser cette nouvelle liste.
    3.  **Découverte et Résolution d'un Bug de Régression :** Suite à la première correction, un bug a été identifié : le résultat du test pour `generate_prompt` affichait 'undefined'.
    4.  **Analyse et Correction du Bug :** L'analyse a montré que la fonction JavaScript `sendSyncMcpRequest` attendait un format de réponse JSON obsolète et non conforme au protocole MCP. La fonction a été corrigée pour parser correctement la structure de réponse standard (`result.content[0].text`), résolvant ainsi le bug.
*   **État à la fin :** L'interface de test est désormais entièrement cohérente avec la logique de l'outil `generate_prompt` et le bug d'affichage est corrigé. L'application est stable.

---

## 10. État Actuel et Plan d'Action

### État Actuel (Points Forts)
*   **Périmètre Fonctionnel Complet :** Les outils `generate_image`, `upscale_image`, `describe_image` et `generate_prompt` sont entièrement implémentés et stables.
*   **Configuration Robuste :** La configuration des services externes (ComfyUI, Ollama) et des outils est entièrement gérée via l'interface web.
*   **Haute Disponibilité et Scalabilité :** Le système peut gérer plusieurs instances ComfyUI et répartir la charge de travail entre elles.
*   **Interface de Test Cohérente :** La page de test reflète désormais fidèlement la configuration et la logique de chaque outil.

### Problèmes Connus
*   Aucun bug critique connu.

### Plan d'Action Détaillé

*   **Phase 1 à 12 :** ✅ **Terminé**