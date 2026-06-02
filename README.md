# 👕 VestisSearch - Recherche Sémantique de Vêtements

Ce projet implémente un moteur de recherche sémantique pour un catalogue de vêtements.
Il utilise **PostgreSQL** avec l'extension **pgvector** et un modèle de Deep Learning.

## 🚀 Fonctionnalités
- **Embeddings 384D** : Indexation sémantique des titres de vêtements.
- **Recherche d'intention** : Compréhension du sens profond (ex: "montagne" -> "randonnée").
- **Indexation HNSW** : Recherche ultra-rapide par voisinage sur de grands volumes.

## 🛠️ Prérequis
- Python 3.10 ou supérieur
- PostgreSQL avec l'extension `pgvector` activée (`CREATE EXTENSION vector;`)

## 📦 Installation
Installez les dépendances nécessaires pour faire tourner le projet :
```bash
pip install psycopg2-binary sentence-transformers pgvector
```

## ⚙️ Configuration
1. Choix des identifiants d'accès à la base de données dans un fichier `.env` :
Créez un fichier .env contenant vos accès à la base de données :
```python
DB_HOST = "localhost"
DB_NAME = "vetements_db"
DB_USER = "postgres"
DB_PASS = "secret"
```
2. Exécution des scripts d'initialisation : 
```python
uv run ex05_setup.py
```

## 🏁 Utilisation
1. Évolution du schéma et Vectorisation
Calcule les embeddings du catalogue et configure l'indexation accélérée :
```python
uv run ex05_films_embeddings.py
```

2. Interrogation Sémantique
Exécutez le script de recherche pour tester la traduction de sens en direct :
```python
uv run ex05_films_search.py
```

## 🧠 Modèle IA
Propulsé par paraphrase-multilingual-MiniLM-L12-v2 de SentenceTransformers.
Ce modèle gère le français nativement et produit des vecteurs denses.

## 🔍 Exemples de requêtes magiques
« habit confortable pour rester à la maison » ➔ Trouve les pyjamas/joggings.

« tenue pour une soirée chic » ➔ Sort les costumes et robes de gala.