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

```bash
# 1. Configurer la clé API OpenRouter
cp .env.example .env
# Editer .env et renseigner OPENROUTER_API_KEY

# 2. Lancer l'application
make run
# ou: docker compose up --build

# 3. Attendre que l'ingestion soit terminée (suivre les logs)
# Le health check indique "ready" quand c'est prêt :
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

### Embedding local vs API

**Choix** : `intfloat/multilingual-e5-base` execute localement dans le conteneur Docker.

**Pourquoi** : Gratuit (pas de cout par requete), pas de dependance externe au-dela d'OpenRouter, excellent support du francais. Le modele E5 est specifiquement entraine pour le retrieval (prefixes `query:`/`passage:`) ce qui donne une meilleure qualite de recherche que des modeles generalistes. Avec seulement ~60 chunks, meme le modele base est largement suffisant.

**Arbitrage** : Le modele `large` (1024 dims) aurait donne des embeddings legerement meilleurs mais double la taille de l'image Docker. Pour 60 chunks, la difference de qualite est negligeable.

### Classification par regles vs LLM

**Choix** : Classification basee sur des patterns regex dans les headers des documents.

**Pourquoi** : Les documents OCR ont des headers clairs (`COMPROMIS DE VENTE`, `CARTE NATIONALE D'IDENTITE`, `EDF`, etc.). Utiliser un LLM pour classifier couterait du budget et ajouterait de la latence sans ameliorer la precision. Les regles gerent meme les erreurs OCR (`CARTE MATIONALE D'IDTITE`).

### Chunking par articles (compromis) vs taille fixe

**Choix** : Decoupage semantique par section `ARTICLE N` pour les compromis de vente, document entier pour les petits documents.

**Pourquoi** : Les compromis font ~6000 caracteres avec 13 articles bien structures. Un chunking par taille fixe couperait au milieu d'un article et perdrait le contexte juridique. Chaque chunk d'article est prefixe avec les noms des parties (vendeur/acquereur) pour maintenir le contexte meme en isolation.

### Strategie de retrieval

**Choix** : Analyse de requete (regex) pour extraire des filtres + recherche vectorielle filtree + fallback sans filtre.

**Pourquoi** :
- Les questions mentionnent souvent un dossier specifique -> filtre Qdrant pour la precision
- Les questions cross-dossier ("Dans quel dossier M. X est-il vendeur?") -> fallback sans filtre si trop peu de resultats
- Les questions de coherence ("Y a-t-il des incoherences?") -> recuperation de TOUS les chunks du dossier pour que le LLM voie l'ensemble

### SQLite pour les metriques vs time-series DB

**Choix** : SQLite avec un fichier persiste via volume Docker.

**Pourquoi** : Pas de service supplementaire a gerer, suffisant pour le volume attendu (~centaines de requetes). Les requetes d'agregation sont simples (COUNT, AVG, SUM).

### Cout estime

~1.2 centimes par requete avec Claude 3.5 Sonnet (~2000 tokens input, ~500 output). Le budget de 20 EUR permet ~1500 requetes.

## Pistes d'amelioration

- **Re-ranking** : Ajouter un modele de re-ranking (ex: `cross-encoder/ms-marco-MiniLM-L-6-v2`) apres la recherche vectorielle pour ameliorer la precision du top-k.
- **Evaluation automatique** : Implementer un benchmark avec des paires question/reponse attendue et mesurer automatiquement la pertinence (RAGAS, LLM-as-judge).
- **Streaming** : Utiliser le streaming SSE pour les reponses longues au lieu d'attendre la reponse complete.
- **Cache** : Cacher les reponses pour les questions frequentes (meme embedding -> meme contexte -> meme reponse).
- **UI** : Ajouter une interface web minimale (Gradio ou Streamlit) pour faciliter les demos.
- **OCR quality gate** : Rejeter ou flagger les documents avec un score OCR trop bas au lieu de les inclure silencieusement.
- **Multi-turn** : Ajouter un historique de conversation pour permettre des follow-up questions ("Et pour le dossier 2?").
- **Observabilite** : Prometheus + Grafana pour monitorer les metriques en production plutot que SQLite.
