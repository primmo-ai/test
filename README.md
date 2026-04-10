# Test technique -- Lead IA/LLM

## Contexte

Tu rejoins une startup qui developpe un outil pour les etudes notariales. L'equipe souhaite mettre en place un agent conversationnel capable de repondre aux questions des notaires et collaborateurs a partir des pieces d'un dossier de vente.

## Base documentaire

Le dossier `documents/` contient les resultats OCR (format Google Vision API) des pieces de **3 dossiers de vente immobiliere** :

| Dossier | Nombre de pieces |
|---------|-----------------|
| `dossier_1/` | 9 documents |
| `dossier_2/` | 6 documents |
| `dossier_3/` | 6 documents |

Chaque dossier contient :

| Type | Exemples | Format |
|------|----------|--------|
| Pieces d'identite | CNI | JSON (OCR Google Vision) |
| Compromis de vente | Compromis sous seing prive | JSON (OCR Google Vision) |
| Justificatifs de domicile | Facture EDF, avis d'imposition | JSON (OCR Google Vision) |
| DPE | Diagnostic de performance energetique | JSON (OCR Google Vision) |

**~21 fichiers au total.**

Les fichiers JSON suivent le format de reponse de l'API Google Cloud Vision (`fullTextAnnotation` avec `pages`, `blocks`, `words`, `symbols` et scores de `confidence`).

## Objectif

Developper une API permettant :

1. **D'interroger la base documentaire via un LLM** -- un utilisateur doit pouvoir poser des questions en langage naturel et obtenir des reponses basees sur les documents des dossiers.

2. **D'evaluer le cout, latence et la pertinence des reponses** -- un endpoint ou un outil permettant de mesurer et suivre la qualite, le cout et la latence des interactions.

La conception de l'API (endpoints, format des requetes/reponses, architecture) est libre -- c'est au candidat de proposer le design qu'il juge le plus adapte.

## Contraintes techniques

- Python 3.11+
- FastAPI
- LLM : **OpenRouter** (clé API fournie, budget plafonné a €20)
- Toute lib RAG/embedding/vectorstore autorisee
- Le code doit tourner avec `docker compose up` ou `make run`
- `README.md` expliquant les choix techniques et d'architecture


## Exemples de questions que l'agent doit savoir traiter

*(Ces exemples illustrent le type de questions attendues -- l'agent doit pouvoir repondre a des questions similaires, pas uniquement a celles-ci)*

- Dans quel dossier monsieur ... est-il vendeur?
- Qui sont les acheteurs et les vendeurs sur le dossier ...?
- Quel est le bien concerne par la transaction de Paris ?
- Les pieces d'identite sont-elles en ordre ?
- Le DPE est-il present et correspond-il au bien ?
- Les justificatifs de domicile sont-ils conformes ?
- Y a-t-il des incoherences entre les documents du dossier ... ?

## Criteres d'evaluation

- L'agent repond de facon pertinente sur la base documentaire fournie
- Le cout, la latence et la pertinence des reponses sont mesurables
- Le code est lisible et bien structure
- Le projet se lance en une commande
- Les choix techniques sont documentes dans le README: y compris une explication des arbitrages réalisés compte tenu des délais impartis, et suggestions pour aller plus loin.

## Duree

Pour discussion 4-5 jours après réception du test.

---

# Solution technique

## Lancement rapide

**Avec OpenRouter (Claude 3.5 Sonnet) :**

```bash
cp .env.example .env
# Editer .env et renseigner OPENROUTER_API_KEY
make run
```

**Avec Ollama (test local, gratuit) :**

```bash
ollama pull mistral
make run-ollama
```

Attendre que les logs affichent `Ingestion complete`. Le health check indique `ready` quand c'est pret :
```bash
curl http://localhost:8000/api/health
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client     │────>│  FastAPI App  │────>│  OpenRouter  │
│  (curl/UI)   │<────│              │<────│ Claude 3.5   │
└─────────────┘     │              │     │  Sonnet      │
                    │  ┌────────┐  │     └─────────────┘
                    │  │Metrics │  │
                    │  │(SQLite)│  │
                    │  └────────┘  │
                    │       │      │
                    │  ┌────v────┐ │
                    │  │ Qdrant  │ │
                    │  │(vectors)│ │
                    │  └─────────┘ │
                    └──────────────┘
```

**Flux d'une requete** : Question utilisateur -> extraction de filtres (dossier, type doc, noms) -> recherche vectorielle Qdrant -> construction du contexte -> appel LLM via OpenRouter -> reponse avec sources et metriques.

### Composants

| Composant | Technologie | Role |
|-----------|------------|------|
| API | FastAPI | Endpoints REST, validation, health check |
| LLM | Claude 3.5 Sonnet via OpenRouter | Generation des reponses |
| Embedding | `intfloat/multilingual-e5-base` (local) | Vectorisation des documents et requetes |
| Vector DB | Qdrant | Stockage et recherche vectorielle avec filtres metadata |
| Metriques | SQLite | Tracking cout, latence, tokens par requete |

## Endpoints

### `POST /api/query` -- Poser une question

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qui sont les vendeurs du dossier 1?"}'
```

Parametres optionnels : `dossier` (forcer un dossier), `doc_types` (filtrer par type).

Reponse : `answer` + `sources` (documents utilises) + `metrics` (latence, tokens, cout).

### `GET /api/documents` -- Lister les documents ingeres

### `GET /api/metrics` -- Statistiques d'utilisation

Retourne le nombre de requetes, latence moyenne, cout total, budget restant.

### `GET /api/health` -- Etat du service

Retourne le statut d'ingestion (`ingesting`/`ready`/`error`), nombre de documents et chunks.

## Choix techniques et arbitrages

### Qdrant comme base vectorielle

**Choix** : Qdrant plutot que ChromaDB, FAISS, ou Pinecone.

**Pourquoi** : Qdrant offre un bon equilibre entre simplicite et fonctionnalites. Contrairement a ChromaDB (in-memory, risque de perte), Qdrant est un service a part entiere avec persistance native. Son systeme de filtrage par payload (metadata) est plus riche que FAISS (qui ne fait que du nearest-neighbor pur). L'image Docker officielle est legere et ne necessite aucune configuration. Cote scalabilite, Qdrant supporte le sharding et la replication -- largement suffisant pour un passage en production.

**Arbitrage** : ChromaDB aurait ete plus simple (pas de service Docker separee), mais moins representatif d'une architecture production. Pinecone (cloud) aurait ajoute une dependance externe et un cout supplementaire.

### Embedding local vs API

**Choix** : `intfloat/multilingual-e5-base` execute localement dans le conteneur Docker.

**Pourquoi** : Gratuit (pas de cout par requete), pas de dependance externe au-dela d'OpenRouter, excellent support du francais. Le modele E5 est specifiquement entraine pour le retrieval (prefixes `query:`/`passage:`) ce qui donne une meilleure qualite de recherche que des modeles generalistes comme camemBERT ou FlauBERT. Avec seulement ~60 chunks, meme le modele base est largement suffisant.

**Arbitrage** : Le modele `large` (1024 dims) aurait donne des embeddings legerement meilleurs mais double la taille de l'image Docker (~2.5 GB vs ~1.5 GB). Pour 60 chunks, la difference de qualite est negligeable. Un modele d'embedding via API (OpenAI, Cohere) aurait ete plus leger mais aurait ajoute un cout et une dependance.

### Classification par regles vs LLM

**Choix** : Classification basee sur des patterns regex dans les headers des documents.

**Pourquoi** : Les documents OCR ont des headers clairs et distincts (`COMPROMIS DE VENTE`, `CARTE NATIONALE D'IDENTITE`, `EDF`, `DIAGNOSTIC DE PERFORMANCE ENERGETIQUE`, `AVIS D'IMPOSITION`). Utiliser un LLM pour classifier couterait du budget et ajouterait de la latence sans ameliorer la precision. Les regles gerent meme les erreurs OCR (`CARTE MATIONALE D'IDTITE`) grace a des patterns tolerants. Un fallback sur le nom de fichier couvre les cas limites.

**Arbitrage** : Si les documents etaient moins structures ou de types plus varies, un classificateur LLM ou un modele fine-tune serait justifie. Ici, c'est de la complexite inutile.

### Chunking semantique vs taille fixe

**Choix** : Decoupage par section `ARTICLE N` pour les compromis de vente, document entier pour les petits documents (<700 caracteres).

**Pourquoi** : Les compromis font ~6000 caracteres avec 13 articles bien structures. Un chunking par taille fixe (ex: 500 tokens) couperait au milieu d'un article et perdrait le contexte juridique. Le decoupage par article preserve la coherence semantique : chaque chunk correspond a un sujet precis (designation du bien, prix, conditions suspensives, etc.).

**Detail important** : Chaque chunk d'article est prefixe avec un en-tete contenant les noms des parties (vendeur/acquereur) extraits du preambule. Cela permet au retrieval de retrouver les bonnes informations meme quand un article ne mentionne pas explicitement les noms.

Les petits documents (identite, DPE, EDF, impots) font tous moins de 700 caracteres -- les decouper n'apporterait rien et fragmenterait l'information.

### Strategie de retrieval a deux phases

**Choix** : Analyse de requete (regex) pour extraire des filtres + recherche vectorielle filtree + fallback sans filtre.

**Pourquoi** : Trois cas d'usage distincts necessitent trois strategies :

1. **Question ciblee** ("Qui sont les acheteurs du dossier 2?") : le dossier est identifie par regex, la recherche vectorielle est filtree sur ce dossier. Cela evite de remonter des chunks d'autres dossiers qui seraient semantiquement proches mais hors sujet.

2. **Question cross-dossier** ("Dans quel dossier M. MOREAU est-il vendeur?") : pas de dossier identifiable, la recherche se fait sans filtre sur tous les chunks. Si un filtre avait ete applique a tort (ex: mauvaise extraction), le fallback (< 3 resultats -> retry sans filtre) rattrape le cas.

3. **Question de coherence** ("Y a-t-il des incoherences dans le dossier 1?") : detectee par des mots-cles (incohérence, conforme, en ordre). Recuperation de TOUS les chunks du dossier, pas juste les top-k. Le LLM a besoin de voir l'ensemble des documents pour comparer noms, adresses, dates entre pieces.

### Prompt engineering notarial

**Choix** : System prompt en francais avec des regles metier explicites.

**Pourquoi** : Le domaine notarial a des regles de verification specifiques qui ne sont pas du "bon sens" pour un LLM generaliste :
- Une piece d'identite doit etre non expiree et correspondre au nom du compromis
- Un DPE doit correspondre a l'adresse et la surface du bien, et etre valide 10 ans
- Un justificatif de domicile doit etre recent (< 3 mois avant la date du compromis)

Ces regles sont injectees dans le system prompt pour que le LLM les applique automatiquement lors des questions de conformite. Le prompt demande aussi de signaler les documents avec un score OCR faible (< 0.8) et de citer systematiquement les sources.

### SQLite pour les metriques vs time-series DB

**Choix** : SQLite avec un fichier persiste via volume Docker.

**Pourquoi** : Pas de service supplementaire a gerer, suffisant pour le volume attendu (~centaines de requetes). Les requetes d'agregation sont simples (COUNT, AVG, SUM). La base se cree automatiquement au demarrage et persiste entre les redemarrages.

**Arbitrage** : Pour un usage production avec des milliers de requetes/jour, Prometheus (metriques) + PostgreSQL (traces) serait plus adapte. Ici, SQLite evite de complexifier l'infrastructure pour le test.

### Structure du code

**Choix** : Separation en 4 modules (`ingestion`, `rag`, `metrics`, `routers`) avec des responsabilites claires.

**Pourquoi** : Chaque module a un role unique :
- `ingestion/` : parsing OCR, classification, chunking -- ne connait pas Qdrant ni le LLM
- `rag/` : embedding, stockage vectoriel, retrieval, appel LLM -- ne connait pas le format des documents OCR
- `metrics/` : tracking SQLite -- independant du reste
- `routers/` : endpoints FastAPI -- orchestre les appels entre modules

Cette separation permet de modifier un composant sans impacter les autres (ex: changer de base vectorielle ne touche que `rag/vectorstore.py`).

### API OpenAI-compatible

**Choix** : Appeler le LLM via l'API OpenAI-compatible (`/v1/chat/completions`) plutot qu'un SDK specifique.

**Pourquoi** : OpenRouter, Ollama, vLLM, et la plupart des providers LLM exposent cette meme API. Un simple changement de `OPENROUTER_BASE_URL` et `OPENROUTER_MODEL` permet de switcher de provider sans toucher au code. Cela a ete valide en testant avec OpenRouter (Claude) et Ollama (Mistral) sans modification.

### Cout estime

Avec Claude 3.5 Sonnet via OpenRouter :
- ~2000 tokens input (system prompt + 8 chunks de contexte), ~500 tokens output
- ~1.2 centimes par requete
- Budget de 20 EUR -> ~1500 requetes possibles

Avec Ollama (Mistral 7B) : cout nul, mais latence plus elevee (~15-75s vs ~2s).

## Pistes d'amelioration

Ci-dessous les ameliorations prioritaires pour une mise en production, classees par impact :

### Haute priorite

- **Evaluation automatique** : Creer un jeu de paires question/reponse de reference et mesurer la pertinence avec RAGAS ou LLM-as-judge. Indispensable pour valider les evolutions du RAG sans regression.
- **Streaming SSE** : Les reponses longues (~75s avec Ollama, ~2s avec Claude) beneficieraient d'un streaming pour ameliorer l'UX. FastAPI supporte nativement `StreamingResponse`.
- **Multi-turn** : Ajouter un historique de conversation pour les follow-ups ("Et pour le dossier 2?"). Stocker les derniers messages et les inclure dans le contexte LLM.

### Moyenne priorite

- **Re-ranking** : Ajouter un cross-encoder (ex: `cross-encoder/ms-marco-MiniLM-L-6-v2`) apres la recherche vectorielle. Le bi-encoder (E5) est rapide mais approximatif ; un cross-encoder re-evalue chaque paire (query, chunk) pour un classement plus precis.
- **Cache semantique** : Cacher les reponses par embedding de la question (cosine > 0.95 -> meme reponse). Reduit les couts et la latence pour les questions repetitives.
- **OCR quality gate** : Rejeter ou flagger les documents avec un score OCR trop bas (< 0.5) au lieu de les inclure silencieusement. Alerter l'utilisateur qu'un re-scan est necessaire.

### Basse priorite (production)

- **UI web** : Interface Gradio ou Streamlit pour les demos et l'usage quotidien des collaborateurs.
- **Observabilite** : Prometheus + Grafana pour le monitoring, OpenTelemetry pour le tracing distribue.
- **Auth** : Ajouter une authentification (API key ou OAuth) pour securiser les endpoints.
- **Batch ingestion** : Supporter l'ajout de nouveaux dossiers sans redemarrer le service.
