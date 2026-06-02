# Tutoriel pgvector — Recherche vectorielle avec PostgreSQL & Python

**Durée estimée : 2h** · **Niveau : intermédiaire** (Python + SQL de base)

---

## Prérequis : lancer l'environnement

```bash
# Lancer PostgreSQL avec pgvector via Docker
docker run --name pgvec -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=vectordb -p 5432:5432 -d pgvector/pgvector:pg16

# Installer les dépendances Python (très léger)
uv add psycopg2-binary pgvector numpy
```

Vérifiez que le conteneur tourne :
```bash
docker ps   # vous devez voir "pgvec" dans la liste
```

---

## Partie 1 — Setup & connexion Python (20 min)

### Objectifs
- Se connecter à PostgreSQL depuis Python
- Activer l'extension pgvector
- Créer une table avec une colonne vectorielle
- Insérer et lire des vecteurs

---

### 1.1 — Se connecter et activer l'extension

`pgvector` est une extension PostgreSQL. Elle doit être activée **une seule fois** par base de données avec `CREATE EXTENSION`. La bibliothèque Python `pgvector` permet ensuite d'envoyer des tableaux numpy directement comme si c'était un type SQL natif.

```python
#import psycopg2
from pgvector.psycopg2 import register_vector

# Connexion à PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="vectordb",
    user="postgres",
    password="secret"
)

conn.autocommit = True
cur = conn.cursor()

# 1. Activer l'extension AVANT register_vector
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
print("✅ Extension pgvector activée")

# 2. Maintenant pgvector existe dans PostgreSQL
register_vector(conn)

# Vérifier la version
cur.execute("""
    SELECT extversion
    FROM pg_extension
    WHERE extname = 'vector';
""")

version = cur.fetchone()[0]
print(f"Version pgvector : {version}")

cur.close()
conn.close()
```

> **À retenir :** `register_vector(conn)` est indispensable. Sans lui, psycopg2 ne sait pas
> que les tableaux numpy doivent être convertis en type `vector` SQL.

---

### 1.2 — Créer une table avec une colonne `vector`

Le type `vector(N)` représente un vecteur de N dimensions. N doit être précisé à la création.
En production, N est typiquement 384, 768 ou 1536 selon le modèle d'embedding utilisé.
Ici on utilise N=3 pour rester lisible.

```python
# ex01_table.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Création d'une table "produits" avec 3 colonnes :
# - id : clé primaire auto-incrémentée
# - nom : le nom du produit
# - caracteristiques : vecteur de dimension 3
#   Chaque dimension représente une propriété :
#   [sucré (0-1), épicé (0-1), exotique (0-1)]
cur.execute("""
    DROP TABLE IF EXISTS produits;
    CREATE TABLE produits (
        id               SERIAL PRIMARY KEY,
        nom              TEXT NOT NULL,
        caracteristiques vector(3)
    );
""")
print("✅ Table 'produits' créée")

# Afficher la structure de la table
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'produits'
    ORDER BY ordinal_position;
""")
print("\nStructure de la table :")
for col, dtype in cur.fetchall():
    print(f"  {col:25s} {dtype}")

cur.close()
conn.close()
```

---

### 1.3 — Insérer des vecteurs

On peut insérer un vecteur comme une liste Python ou un tableau numpy.
`pgvector` convertit automatiquement grâce à `register_vector`.

```python
# ex01_insert.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

# Données : [sucré, épicé, exotique]
produits = [
    ("mangue",       np.array([0.9, 0.1, 0.95])),
    ("piment",       np.array([0.1, 0.95, 0.6])),
    ("fraise",       np.array([0.85, 0.05, 0.2])),
    ("curry",        np.array([0.2, 0.9, 0.7])),
    ("vanille",      np.array([0.95, 0.02, 0.3])),
    ("wasabi",       np.array([0.05, 0.98, 0.55])),
    ("ananas",       np.array([0.8, 0.08, 0.88])),
]

# Insertion un par un
for nom, vec in produits:
    cur.execute(
        "INSERT INTO produits (nom, caracteristiques) VALUES (%s, %s)",
        (nom, vec)  # numpy array → pgvector sait le convertir
    )

print(f"✅ {len(produits)} produits insérés")

# Vérification : lire les données insérées
cur.execute("SELECT id, nom, caracteristiques FROM produits ORDER BY id;")
print("\nProduits en base :")
for id_, nom, vec in cur.fetchall():
    print(f"  [{id_}] {nom:12s} → {np.round(vec, 2)}")

cur.close()
conn.close()
```

---

### 🏋️ Exercice 1

**Ajoutez 3 produits de votre choix** à la table. Définissez vous-même leurs valeurs sur les 3 dimensions (sucré, épicé, exotique). Chaque valeur doit être entre 0 et 1.

Vérifiez ensuite avec un `SELECT COUNT(*) FROM produits;` que vous avez bien 10 lignes au total.

---

## Partie 2 — Vecteurs & similarité cosinus (35 min)

### Objectifs
- Comprendre concrètement ce que mesure la distance cosinus
- Utiliser les opérateurs `<=>`, `<->`, `<#>`
- Trier les résultats par similarité
- Combiner filtres SQL et distance vectorielle

---

### 2.1 — Comprendre la distance cosinus à la main

Avant d'utiliser SQL, calculons la distance cosinus manuellement pour bien comprendre ce que pgvector fait. La distance cosinus mesure **l'angle** entre deux vecteurs — pas leur longueur.

```python
# ex02_cosinus.py

import numpy as np

def distance_cosinus(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calcule la distance cosinus entre deux vecteurs.
    Formule : 1 - (a · b) / (|a| × |b|)
    
    Résultat :
    - 0.0 → vecteurs identiques (même direction)
    - 1.0 → vecteurs orthogonaux (perpendiculaires)
    - 2.0 → vecteurs opposés
    """
    # Produit scalaire
    dot = np.dot(a, b)
    # Normes
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    # Similarité cosinus (entre -1 et 1)
    similarite = dot / (norm_a * norm_b)
    # Distance cosinus (entre 0 et 2)
    return 1 - similarite

# Nos vecteurs [sucré, épicé, exotique]
mangue   = np.array([0.9, 0.1, 0.95])
ananas   = np.array([0.8, 0.08, 0.88])
piment   = np.array([0.1, 0.95, 0.6])
vanille  = np.array([0.95, 0.02, 0.3])

print("Distances cosinus calculées manuellement :")
print(f"  mangue  ↔ ananas  : {distance_cosinus(mangue, ananas):.4f}  (proches : tous deux sucrés/exotiques)")
print(f"  mangue  ↔ piment  : {distance_cosinus(mangue, piment):.4f}  (éloignés : sucré vs épicé)")
print(f"  mangue  ↔ vanille : {distance_cosinus(mangue, vanille):.4f}  (moyens : sucrés mais exotique différent)")
print(f"  piment  ↔ vanille : {distance_cosinus(piment, vanille):.4f}  (très éloignés)")

# Illustrer l'effet de la magnitude (la distance cosinus ne change pas)
mangue_x10 = mangue * 10
print(f"\n  mangue × 10 ↔ ananas : {distance_cosinus(mangue_x10, ananas):.4f}")
print("  → La distance cosinus est insensible à la magnitude !")

# En comparaison, la distance L2 change
print(f"\nDistance L2 (Euclidienne) pour comparaison :")
print(f"  mangue  ↔ ananas  : {np.linalg.norm(mangue - ananas):.4f}")
print(f"  mangue × 10 ↔ ananas : {np.linalg.norm(mangue_x10 - ananas):.4f}")
print("  → La distance L2 est sensible à la magnitude !")
```

**Résultat attendu :**
```
Distances cosinus calculées manuellement :
  mangue  ↔ ananas  : 0.0014  (proches : tous deux sucrés/exotiques)
  mangue  ↔ piment  : 0.4237  (éloignés : sucré vs épicé)
  mangue  ↔ vanille : 0.0724  (moyens : sucrés mais exotique différent)
  piment  ↔ vanille : 0.6821  (très éloignés)

  mangue × 10 ↔ ananas : 0.0014
  → La distance cosinus est insensible à la magnitude !
```

---

### 2.2 — Les opérateurs SQL pgvector

pgvector ajoute 4 opérateurs à PostgreSQL. Ils s'utilisent directement dans un `ORDER BY`.

```python
# ex02_operateurs.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

# Vecteur de requête : je cherche quelque chose de "sucré et exotique"
query = np.array([1.0, 0.0, 1.0])  # sucré max, pas épicé, exotique max

print("="*55)
print(f"Requête : sucré=1.0, épicé=0.0, exotique=1.0")
print("="*55)

# ── Opérateur <=> : distance cosinus ──────────────────────
print("\n🔵 <=> Distance cosinus (recommandé pour textes)")
cur.execute("""
    SELECT nom,
           ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 4) AS similarite,
           caracteristiques::text AS vec
    FROM produits
    ORDER BY caracteristiques <=> %s::vector
    LIMIT 4;
""", (query.tolist(), query.tolist()))
for nom, sim, vec in cur.fetchall():
    print(f"  {nom:12s}  sim={sim}  {vec}")

# ── Opérateur <-> : distance L2 (Euclidienne) ─────────────
print("\n🟢 <-> Distance L2 / Euclidienne (sensible à la magnitude)")
cur.execute("""
    SELECT nom,
           ROUND((caracteristiques <-> %s::vector)::numeric, 4) AS distance_l2
    FROM produits
    ORDER BY caracteristiques <-> %s::vector
    LIMIT 4;
""", (query.tolist(), query.tolist()))
for nom, dist in cur.fetchall():
    print(f"  {nom:12s}  dist_L2={dist}")

# ── Comparaison : même résultats ? ────────────────────────
print("\n💡 Même classement ? Les deux opérateurs donnent souvent")
print("   des résultats proches, mais pas toujours identiques.")
print("   Pour des embeddings texte normalisés, <=> est standard.")

cur.close()
conn.close()
```

---

### 2.3 — Filtrage hybride : SQL + distance vectorielle

Un des grands avantages de pgvector est de pouvoir combiner une clause `WHERE` SQL classique avec un tri vectoriel. Les deux s'appliquent dans la même requête.

```python
# ex02_filtrage.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

# Ajouter une colonne "categorie" pour l'exercice
cur.execute("ALTER TABLE produits ADD COLUMN IF NOT EXISTS categorie TEXT;")
# Mettre à jour les catégories
categories = {
    "mangue": "fruit", "fraise": "fruit", "vanille": "fruit",
    "ananas": "fruit", "piment": "epice", "curry": "epice", "wasabi": "epice"
}
for nom, cat in categories.items():
    cur.execute("UPDATE produits SET categorie = %s WHERE nom = %s", (cat, nom))

print("Catégories mises à jour\n")

query = np.array([0.8, 0.5, 0.6])  # requête équilibrée

# Recherche sans filtre
print("🔍 Sans filtre — top 4 tous produits :")
cur.execute("""
    SELECT nom, categorie,
           ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 3) AS sim
    FROM produits
    ORDER BY caracteristiques <=> %s::vector
    LIMIT 4;
""", (query.tolist(), query.tolist()))
for nom, cat, sim in cur.fetchall():
    print(f"  [{sim}] {nom:12s}  ({cat})")

# Recherche filtrée : fruits uniquement
print("\n🔍 Filtré sur categorie='fruit' — top 3 :")
cur.execute("""
    SELECT nom, categorie,
           ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 3) AS sim
    FROM produits
    WHERE categorie = 'fruit'           -- filtre SQL classique
    ORDER BY caracteristiques <=> %s::vector
    LIMIT 3;
""", (query.tolist(), query.tolist()))
for nom, cat, sim in cur.fetchall():
    print(f"  [{sim}] {nom:12s}  ({cat})")

# Filtre sur seuil de similarité minimum
print("\n🔍 Seuil de similarité > 0.95 :")
cur.execute("""
    SELECT nom,
           ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 3) AS sim
    FROM produits
    WHERE (1 - (caracteristiques <=> %s::vector)) > 0.95
    ORDER BY sim DESC;
""", (query.tolist(), query.tolist()))
rows = cur.fetchall()
if rows:
    for nom, sim in rows:
        print(f"  [{sim}] {nom}")
else:
    print("  (aucun résultat avec ce seuil)")

cur.close()
conn.close()
```

---

### 🏋️ Exercice 2

**Partie A** — Modifiez le vecteur de requête pour trouver le produit le plus "épicé et exotique" (peu sucré). Vérifiez que `piment`, `curry` ou `wasabi` remontent en premier.

**Partie B** — Écrivez une fonction Python `chercher(conn, query_vec, top_k=3)` qui prend une connexion, un vecteur numpy, et retourne une liste de dictionnaires `{"nom": ..., "sim": ...}`.

**Partie C** — Ajoutez un paramètre `categorie=None` à votre fonction. Si `categorie` est fourni, le filtre SQL s'applique. Sinon, on cherche dans tous les produits.

---

## Partie 3 — Index HNSW & performances (25 min)

### Objectifs
- Comprendre pourquoi les index sont nécessaires
- Créer un index HNSW
- Observer la différence de vitesse
- Comprendre le paramètre `ef_search`

---

### 3.1 — Pourquoi un index ?

Sans index, pgvector lit toute la table (sequential scan) et calcule la distance pour chaque ligne. C'est exact, mais O(n). Pour 1 000 lignes, c'est imperceptible. Pour 1 000 000 de lignes, c'est plusieurs secondes.

Un index **ANN** (Approximate Nearest Neighbor) construit une structure de données qui permet de trouver les voisins proches sans tout parcourir. Il est **approximatif** : il peut manquer quelques résultats très rares, mais il est 10 à 100× plus rapide.

```python
# ex03_benchmark.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np
import time

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

# ── Créer une table avec plus de données ────────────────────
cur.execute("""
    DROP TABLE IF EXISTS bench;
    CREATE TABLE bench (
        id        SERIAL PRIMARY KEY,
        label     TEXT,
        embedding vector(10)
    );
""")

# Générer 5000 vecteurs aléatoires (dim=10)
print("Génération de 5000 vecteurs aléatoires...")
np.random.seed(42)
n = 5000
vecs = np.random.rand(n, 10).astype(np.float32)
vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)  # normalisation L2

data = [(f"item_{i}", vecs[i].tolist()) for i in range(n)]
cur.executemany(
    "INSERT INTO bench (label, embedding) VALUES (%s, %s)",
    data
)
print(f"✅ {n} lignes insérées\n")

# Vecteur de requête
query = vecs[0]  # on cherche les voisins du premier vecteur

def mesurer_query(label: str, repetitions: int = 10) -> float:
    """Exécute la requête N fois et retourne le temps moyen en ms."""
    temps = []
    for _ in range(repetitions):
        t0 = time.perf_counter()
        cur.execute("""
            SELECT label FROM bench
            ORDER BY embedding <=> %s::vector
            LIMIT 5;
        """, (query.tolist(),))
        cur.fetchall()
        temps.append((time.perf_counter() - t0) * 1000)
    moy = sum(temps) / len(temps)
    print(f"  {label:30s} : {moy:6.1f} ms  (moy sur {repetitions} requêtes)")
    return moy

# ── Sans index ───────────────────────────────────────────────
cur.execute("SET enable_indexscan = OFF;")
t_seq = mesurer_query("Sequential scan (sans index)")

# ── Création du HNSW ─────────────────────────────────────────
print("\nCréation de l'index HNSW...")
t0 = time.perf_counter()
cur.execute("""
    CREATE INDEX bench_hnsw_idx ON bench
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
""")
print(f"Index créé en {time.perf_counter()-t0:.2f}s\n")

# ── Avec index HNSW ──────────────────────────────────────────
cur.execute("SET enable_indexscan = ON;")
cur.execute("SET hnsw.ef_search = 40;")
t_hnsw = mesurer_query("HNSW (ef_search=40)")

# Effet de ef_search sur la précision/vitesse
print("\nEffet de ef_search (compromis vitesse ↔ précision) :")
for ef in [10, 20, 40, 80, 160]:
    cur.execute(f"SET hnsw.ef_search = {ef};")
    mesurer_query(f"  HNSW ef_search={ef}")

print(f"\n→ Gain de vitesse HNSW vs seq scan : ×{t_seq/t_hnsw:.1f}")
print("→ ef_search plus bas = plus rapide mais moins précis")

cur.close()
conn.close()
```

**Ce que vous devriez observer :**
- Le sequential scan prend ~5-15 ms sur 5000 lignes
- HNSW est 2-5× plus rapide sur une petite table
- Sur des millions de lignes, le gain devient spectaculaire
- ef_search=10 est rapide mais peut rater quelques vrais voisins

---

### 3.2 — Vérifier si l'index est utilisé

PostgreSQL a `EXPLAIN ANALYZE` pour inspecter le plan d'exécution d'une requête.

```python
# ex03_explain.py
# (suite du script précédent, avec la même connexion)

cur.execute("SET hnsw.ef_search = 40;")

print("Plan d'exécution avec index :")
cur.execute("""
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT label FROM bench
    ORDER BY embedding <=> %s::vector
    LIMIT 5;
""", (query.tolist(),))

for (ligne,) in cur.fetchall():
    print(" ", ligne)
    
# Chercher "Index Scan" dans le plan
# Si on voit "Seq Scan" à la place, l'index n'est pas utilisé
```

> **À chercher dans la sortie :** `Index Scan using bench_hnsw_idx` confirme que
> l'index est bien utilisé. `Seq Scan` signifie que PostgreSQL préfère le scan séquentiel
> (ce qui peut arriver sur de très petites tables).

---

### 🏋️ Exercice 3

**Partie A** — Comparez `HNSW` et `IVFFlat` sur la même table `bench` :

```sql
-- Index IVFFlat à créer
CREATE INDEX ON bench
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
```

Quel est le plus rapide ? Lequel prend plus de place ?
***sur des petites quantité de ligne (< 10 000), ils sont equivalants en vitesst au dela de 10 000 lignes IVFFlat est plus rapide mais prend plus de place.***
```sql
SELECT pg_size_pretty(pg_indexes_size('bench'));
```

**Partie B** — À partir de combien de lignes l'index HNSW devient-il clairement avantageux ?
Testez avec 500, 1000, 5000 lignes. Tracez (ou affichez) les temps. 
***à partir de 2000 ligne le HNSW est plus rapide***

---

## Partie 4 — Mini-projet : moteur de recommandation de films (40 min)

### Objectifs
- Construire un pipeline complet d'ingestion + recherche
- Utiliser des vecteurs qui représentent des "profils"
- Combiner filtres métier et similarité vectorielle
- Encapsuler le tout dans des fonctions réutilisables

---

### Contexte

On va construire un moteur de recommandation simple pour des films. Chaque film est représenté par un vecteur de 5 dimensions définissant son "profil" :

```
[action, comédie, drame, romance, science-fiction]
```

Chaque dimension va de 0 à 1. Un film peut mélanger plusieurs genres (ex : comédie romantique = [0, 0.8, 0.2, 0.9, 0]).

---

### 4.1 — Ingestion : créer et remplir la base de films

```python
# ex04_films_setup.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Schéma : films avec profil vectoriel + métadonnées
cur.execute("""
    DROP TABLE IF EXISTS films;
    CREATE TABLE films (
        id      SERIAL PRIMARY KEY,
        titre   TEXT NOT NULL,
        annee   INT,
        note    NUMERIC(3,1),
        -- profil : [action, comedie, drame, romance, scifi]
        profil  vector(5)
    );
""")

# Catalogue de films avec leur profil
# Dimensions : [action, comédie, drame, romance, sci-fi]
catalogue = [
    ("Avengers: Endgame",  2019, 8.4, [0.95, 0.15, 0.35, 0.10, 0.6]),
    ("La La Land",         2016, 8.0, [0.05, 0.30, 0.55, 0.90, 0.0]),
    ("Inception",          2010, 8.8, [0.70, 0.05, 0.50, 0.20, 0.9]),
    ("Le Diable s'habille en Prada", 2006, 6.9, [0.05, 0.65, 0.45, 0.40, 0.0]),
    ("Mad Max: Fury Road",  2015, 8.1, [0.98, 0.02, 0.20, 0.05, 0.4]),
    ("Eternal Sunshine",   2004, 8.3, [0.00, 0.20, 0.75, 0.90, 0.2]),
    ("Interstellar",       2014, 8.6, [0.45, 0.05, 0.70, 0.20, 0.95]),
    ("Superbad",           2007, 7.6, [0.10, 0.92, 0.30, 0.25, 0.0]),
    ("The Dark Knight",    2008, 9.0, [0.88, 0.05, 0.65, 0.10, 0.3]),
    ("Amélie",             2001, 8.3, [0.05, 0.55, 0.60, 0.75, 0.1]),
    ("Aliens",             1986, 8.4, [0.80, 0.08, 0.40, 0.05, 0.95]),
    ("Forrest Gump",       1994, 8.8, [0.20, 0.40, 0.85, 0.60, 0.0]),
    ("John Wick",          2014, 7.4, [0.98, 0.05, 0.15, 0.05, 0.1]),
    ("The Notebook",       2004, 7.9, [0.02, 0.15, 0.60, 0.95, 0.0]),
    ("Ex Machina",         2014, 7.7, [0.15, 0.02, 0.55, 0.15, 0.95]),
]

for titre, annee, note, profil in catalogue:
    cur.execute(
        "INSERT INTO films (titre, annee, note, profil) VALUES (%s, %s, %s, %s)",
        (titre, annee, note, np.array(profil))
    )

# Créer un index HNSW pour la colonne profil
cur.execute("""
    CREATE INDEX ON films
    USING hnsw (profil vector_cosine_ops)
    WITH (m = 8, ef_construction = 40);
""")

print(f"✅ {len(catalogue)} films insérés et indexés")
print("\nDimensions du profil : [action, comédie, drame, romance, sci-fi]")

cur.close()
conn.close()
```

---

### 4.2 — Moteur de recommandation

```python
# ex04_recommandation.py

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

# ── Connexion ────────────────────────────────────────────────
conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()


# ── Fonctions utilitaires ────────────────────────────────────

def creer_profil(action=0.0, comedie=0.0, drame=0.0,
                 romance=0.0, scifi=0.0) -> np.ndarray:
    """
    Crée un vecteur de profil utilisateur.
    Chaque valeur est entre 0 (pas intéressé) et 1 (très intéressé).
    """
    return np.array([action, comedie, drame, romance, scifi], dtype=np.float32)


def recommander(profil_user: np.ndarray,
                top_k: int = 5,
                note_min: float = 0.0,
                annee_min: int = 1900) -> list[dict]:
    """
    Recommande des films similaires au profil utilisateur.
    
    Paramètres :
    - profil_user : vecteur numpy [action, comédie, drame, romance, sci-fi]
    - top_k : nombre de films à retourner
    - note_min : note IMDb minimale (filtre SQL)
    - annee_min : année de sortie minimale (filtre SQL)
    
    Retourne une liste de dicts avec titre, annee, note, similarite.
    """
    cur.execute("""
        SELECT titre,
               annee,
               note,
               ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
        FROM films
        WHERE note >= %s
          AND annee >= %s
        ORDER BY profil <=> %s::vector
        LIMIT %s;
    """, (profil_user.tolist(), note_min, annee_min,
          profil_user.tolist(), top_k))
    
    return [
        {"titre": row[0], "annee": row[1], "note": float(row[2]), "sim": float(row[3])}
        for row in cur.fetchall()
    ]


def films_similaires(titre_ref: str, top_k: int = 4) -> list[dict]:
    """
    Trouve les films les plus similaires à un film de référence.
    Utile pour le mode "parce que vous avez aimé X...".
    """
    # Récupérer le profil du film de référence
    cur.execute("SELECT profil FROM films WHERE titre = %s", (titre_ref,))
    row = cur.fetchone()
    if not row:
        print(f"Film '{titre_ref}' non trouvé.")
        return []
    
    profil_ref = row[0]
    
    # Trouver les similaires (en excluant le film lui-même)
    cur.execute("""
        SELECT titre,
               annee,
               ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
        FROM films
        WHERE titre != %s
        ORDER BY profil <=> %s::vector
        LIMIT %s;
    """, (profil_ref, titre_ref, profil_ref, top_k))
    
    return [
        {"titre": row[0], "annee": row[1], "sim": float(row[2])}
        for row in cur.fetchall()
    ]


def afficher(titre: str, resultats: list[dict]):
    """Affiche les résultats proprement."""
    print(f"\n{'='*50}")
    print(f"  {titre}")
    print(f"{'='*50}")
    for r in resultats:
        if "note" in r:
            print(f"  [{r['sim']:.3f}]  {r['titre']:35s}  ({r['annee']})  ★{r['note']}")
        else:
            print(f"  [{r['sim']:.3f}]  {r['titre']:35s}  ({r['annee']})")


# ── Scénarios de recommandation ───────────────────────────────

# Profil 1 : fan d'action/sci-fi
profil_action_scifi = creer_profil(action=0.9, scifi=0.85, drame=0.3)
afficher("Fan d'action et sci-fi", recommander(profil_action_scifi))

# Profil 2 : amateur de comédies romantiques
profil_comedie_romance = creer_profil(comedie=0.85, romance=0.80, drame=0.4)
afficher("Amateur de comédies romantiques", recommander(profil_comedie_romance))

# Profil 3 : drames récents bien notés
profil_drame = creer_profil(drame=0.9, romance=0.5)
afficher("Drames bien notés depuis 2000 (note ≥ 8.0)",
         recommander(profil_drame, note_min=8.0, annee_min=2000))

# Films similaires
afficher("Films similaires à 'Inception'", films_similaires("Inception"))
afficher("Films similaires à 'La La Land'", films_similaires("La La Land"))

cur.close()
conn.close()
```

**Sortie attendue (extrait) :**
```
==================================================
  Fan d'action et sci-fi
==================================================
  [0.024]  Aliens                               (1986)  ★8.4
  [0.031]  Interstellar                         (2014)  ★8.6
  [0.058]  Inception                            (2010)  ★8.8
  ...

==================================================
  Films similaires à 'Inception'
==================================================
  [0.082]  Interstellar                         (2014)
  [0.102]  The Dark Knight                      (2008)
  ...
```

---

### 4.3 — Interface interactive simple

```python
# ex04_interface.py
# (nécessite d'avoir exécuté ex04_films_setup.py avant)

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()

DIMS = ["action", "comédie", "drame", "romance", "sci-fi"]

def saisir_profil() -> np.ndarray:
    """Demande à l'utilisateur de noter chaque genre de 0 à 10."""
    print("\n📝 Notez chaque genre de 0 (pas du tout) à 10 (adore) :")
    valeurs = []
    for dim in DIMS:
        while True:
            try:
                v = float(input(f"  {dim:12s} : "))
                if 0 <= v <= 10:
                    valeurs.append(v / 10.0)  # normaliser entre 0 et 1
                    break
                print("  ⚠️  Entrez une valeur entre 0 et 10")
            except ValueError:
                print("  ⚠️  Entrez un nombre")
    return np.array(valeurs, dtype=np.float32)

def recommander_interactif(profil: np.ndarray, top_k=5):
    cur.execute("""
        SELECT titre, annee, note,
               ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
        FROM films
        ORDER BY profil <=> %s::vector
        LIMIT %s;
    """, (profil.tolist(), profil.tolist(), top_k))
    
    print(f"\n🎬 Recommandations pour votre profil :")
    print(f"   [{', '.join(f'{v:.1f}' for v in profil)}]")
    print()
    for titre, annee, note, sim in cur.fetchall():
        barre = "█" * int(sim * 20)
        print(f"  {barre:20s}  {sim:.3f}  {titre} ({annee}) ★{note}")


if __name__ == "__main__":
    print("🎬 Moteur de recommandation de films")
    print("   Basé sur pgvector — recherche vectorielle")
    
    while True:
        print("\n" + "-"*40)
        print("1. Créer un profil et obtenir des recommandations")
        print("2. Trouver des films similaires à un titre")
        print("3. Quitter")
        
        choix = input("\nVotre choix : ").strip()
        
        if choix == "1":
            profil = saisir_profil()
            recommander_interactif(profil)
        
        elif choix == "2":
            cur.execute("SELECT titre FROM films ORDER BY titre;")
            titres = [r[0] for r in cur.fetchall()]
            print("\nFilms disponibles :")
            for i, t in enumerate(titres, 1):
                print(f"  {i:2d}. {t}")
            try:
                idx = int(input("Numéro du film : ")) - 1
                titre_ref = titres[idx]
                cur.execute("""
                    SELECT titre, annee,
                           ROUND((1 - (profil <=> (
                               SELECT profil FROM films WHERE titre = %s
                           )))::numeric, 3) AS sim
                    FROM films WHERE titre != %s
                    ORDER BY profil <=> (SELECT profil FROM films WHERE titre = %s)
                    LIMIT 4;
                """, (titre_ref, titre_ref, titre_ref))
                print(f"\nFilms similaires à '{titre_ref}' :")
                for t, a, s in cur.fetchall():
                    print(f"  [{s}]  {t} ({a})")
            except (ValueError, IndexError):
                print("Numéro invalide")
        
        elif choix == "3":
            break

    cur.close()
    conn.close()
    print("Au revoir !")
```

---

### 🏋️ Exercice 4

**Partie A** — Ajoutez 5 films de votre choix au catalogue avec leurs profils. Testez si vos recommandations changent.

**Partie B** — Implémentez une fonction `trouver_contraire(titre)` qui retourne les films les **moins** similaires (ORDER BY ... DESC au lieu de ASC).

**Partie C** — Ajoutez un score de recommandation combiné :
```
score_final = 0.7 × similarite + 0.3 × (note / 10)
```
Réécrivez la requête SQL pour trier par ce score combiné.

---

## Récapitulatif

### Les opérateurs pgvector

| Opérateur | Mesure          | Quand l'utiliser               |
|-----------|-----------------|--------------------------------|
| `<=>`     | Cosine distance | Textes, NLP, embeddings (défaut) |
| `<->`     | Euclidean (L2)  | Images, vectors non normalisés |
| `<#>`     | Inner product   | Modèles bi-encodeurs           |
| `<+>`     | Manhattan (L1)  | Vectors épars                  |

### Les index

| Index    | Points forts                          | Points faibles              |
|----------|---------------------------------------|-----------------------------|
| HNSW     | Très rapide en query, bon recall      | Plus de RAM                 |
| IVFFlat  | Moins de RAM, bonne scalabilité       | Nécessite des données avant |
| (aucun)  | Résultats exacts à 100%               | Lent au-delà de ~10 000 lignes |

### Pattern de base en Python

```python
import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect(host="localhost", dbname="vectordb",
                        user="postgres", password="secret")
register_vector(conn)  # indispensable

cur = conn.cursor()
cur.execute("""
    SELECT titre, 1 - (profil <=> %s::vector) AS sim
    FROM films
    ORDER BY profil <=> %s::vector
    LIMIT 5;
""", (mon_vecteur.tolist(), mon_vecteur.tolist()))

for titre, sim in cur.fetchall():
    print(f"{titre} → {sim:.3f}")
```

### Pour aller plus loin

- **Embeddings réels** : `pip install sentence-transformers` → modèle `all-MiniLM-L6-v2` ou `paraphrase-multilingual-MiniLM-L12-v2` 
- **Avec SQLAlchemy** : `pip install pgvector sqlalchemy` → colonne `Vector(384)`
- **Documentation pgvector** : https://github.com/pgvector/pgvector


 # 🏋️ Exercice 5 — Recherche sémantique de vêtements avec des embeddings

## Contexte

Vous travaillez pour une boutique de vêtements en ligne.

Le catalogue contient uniquement des descriptions textuelles des produits. Votre objectif est de mettre en place un moteur de recherche capable de comprendre l'intention de l'utilisateur et de retrouver les vêtements les plus pertinents, même lorsque les mots utilisés dans la requête ne sont pas présents dans les descriptions.

L'objectif de cet exercice est de découvrir comment les embeddings permettent d'effectuer une recherche basée sur le sens plutôt que sur la simple correspondance de mots-clés.

---

## Partie A — Préparer le catalogue

Voici un premier catalogue de vêtements représentant différents styles, usages et saisons :

```python
vetements = [
    "T-shirt blanc en coton",
    "Pull en laine pour l'hiver",
    "Jean bleu coupe droite",
    "Robe élégante noire",
    "Veste imperméable de randonnée",
    "Chaussures de sport légères",
    "Manteau chaud en duvet",
    "Chemise blanche professionnelle",
    "Short de sport respirant",
    "Baskets pour courir"
]
```

Vous pouvez enrichir ce catalogue en ajoutant de nouveaux produits. Essayez de varier :

* les styles (casual, professionnel, élégant, sportif, etc.) ;
* les saisons ;
* les activités (randonnée, bureau, soirée, voyage, sport, plage, montagne, etc.) ;
* les types de vêtements et d'accessoires.

Plus votre catalogue sera varié, plus les résultats seront intéressants à analyser.

---

## Partie B — Générer les embeddings

Pour chaque description du catalogue :

1. Générez un embedding à l'aide du modèle multilingue suivant :

```python
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

Ce modèle fonctionne dans de nombreuses langues, dont le français.

Vous pouvez également explorer d'autres modèles disponibles sur Hugging Face afin de comparer leurs performances ou leurs dimensions d'embeddings.

2. Stockez les embeddings dans une structure adaptée.
3. Vérifiez la dimension des vecteurs obtenus.

### Questions

* Quelle est la dimension produite par le modèle ?
***384***
* Tous les produits possèdent-ils un vecteur de même taille ?
***oui***
* Pourquoi est-il important que tous les embeddings aient la même dimension ?
***pour comparer les vecteur ils doivent faire la même dimension***

---

## Partie C — Tester la compréhension sémantique

Effectuez plusieurs recherches en utilisant des requêtes qui ne contiennent aucun mot présent dans les descriptions du catalogue.

Par exemple :

* « tenue pour un entretien d'embauche »
* « vêtements pour partir à la montagne »
* « habit confortable pour rester à la maison »
* « tenue pour une soirée chic »

Pour chaque requête :

1. Prédisez les produits qui devraient être proposés.
2. Exécutez la recherche.
3. Analysez les résultats obtenus.

### Questions

* Les résultats correspondent-ils à vos attentes ?
* Le modèle a-t-il correctement compris l'intention de la requête ?
* Certains résultats vous semblent-ils surprenants ?
***Pantalon de costume ajusté 66.5% pour êtements pour partir à la montagne*** 

---

## Partie D — Recommander des produits similaires

Implémentez une fonction permettant de retrouver les vêtements les plus similaires à un produit donné.

Choisissez un article du catalogue puis affichez les 5 produits les plus proches selon la similarité vectorielle.

### Exemple

Produit de référence :

```text
Pull en laine pour l'hiver
```

Exemple de résultats possibles :

```text
- Manteau chaud en duvet
- Veste imperméable de randonnée
- Chemise blanche professionnelle
...
```

Comparez les résultats avec votre intuition.

### Questions

* Les produits recommandés sont-ils cohérents ?
* Peut-on utiliser cette approche pour construire un système de recommandations ?

---

## Partie E — Trouver les produits les moins similaires

À partir d'un produit donné, recherchez cette fois les vêtements les plus éloignés dans l'espace vectoriel.

Comparez les résultats avec ceux obtenus dans la partie précédente.

### Questions

* Quels produits apparaissent comme les plus opposés ?
* Les résultats sont-ils logiques ?
* Que nous apprend la distance vectorielle sur les relations entre les produits ?

---

## Partie F — Combiner similarité et popularité

Ajoutez une note de popularité comprise entre 1 et 10 à chaque vêtement.

Créez ensuite un score de classement combinant :

```text
score_final = 0.7 × similarité + 0.3 × popularité
```

Utilisez ce score pour trier les résultats.

### Questions

* Quels produits remontent dans le classement ?
* Quels produits perdent des positions ?
* Pourquoi les plateformes e-commerce utilisent-elles souvent plusieurs critères de classement ?

---

## 🤔 Réflexion finale

Répondez aux questions suivantes :

1. Quelle différence observez-vous entre une recherche par mots-clés et une recherche par embeddings ?
***Dans la recherche par embedding, on n'a pas besoin de mot clé le sens suffis***
2. Quels avantages apporte la recherche sémantique ?
***Recherche rapide et plus précise, car on utilise le vocabulaire de l'utilisateur pour identifier les produits qu'il recherche***
3. Quelles limites avez-vous identifiées lors de vos expérimentations ?
***Incohérence de calcul***
4. Le modèle comprend-il toujours correctement l'intention de l'utilisateur ?
***Pas forcement, le modèle interprete l'intention***
5. Dans quels cas les résultats vous ont-ils surpris ?

---

## 🚀 Niveau avancé

Imaginez maintenant que votre catalogue contient :

* 1 000 000 de vêtements ;
* un embedding de 384 dimensions pour chaque produit.

Réfléchissez aux questions suivantes :

1. Pourquoi comparer chaque produit avec tous les autres devient-il rapidement coûteux ?
***trop de calcul à faire***
2. Quel rôle joue une base vectorielle comme PostgreSQL avec pgvector ?
***améliore la réaidité de recherche sémentique***
3. Pourquoi utilise-t-on des index spécialisés comme HNSW ?
***pour limiter le nombre de calcul aux éléments les plus proches***
4. Quels seraient les avantages d'effectuer les recherches directement dans PostgreSQL plutôt que dans une simple liste Python ?
***C'est plus rapide***

### Objectif

Comprendre comment passer d'un moteur de recherche local manipulant quelques dizaines de produits à un véritable système de recommandation capable de gérer des millions d'articles.
