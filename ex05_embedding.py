import sys

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError
from sentence_transformers import SentenceTransformer

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def main():
    try:
        # 1. Chargement du modèle de Deep Learning
        log("Chargement du modèle SentenceTransformer (384 dimensions)...", "PROGRESS")
        model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        # 2. Connexion à la base de données
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True
            register_vector(conn)

            with conn.cursor() as cur:
                # 3. Évolution du schéma : ajout de la colonne pour l'embedding de texte
                log(
                    "Modification de la table pour ajouter 'titre_vector'...",
                    "PROGRESS",
                )
                cur.execute("""
                    ALTER TABLE vetements 
                    ADD COLUMN IF NOT EXISTS titre_vector vector(384);
                """)

                # 4. Récupération des données existantes
                log("Lecture des titres dans la base de données...", "PROGRESS")
                cur.execute("SELECT id, titre FROM vetements;")
                lignes = cur.fetchall()

                if not lignes:
                    log(
                        "Aucun vêtement trouvé en base de données. Exécute d'abord le script ex05_setup.py.",
                        "ERROR",
                    )
                    sys.exit(1)

                # 5. Boucle de génération et de mise à jour
                log(
                    f"Génération des embeddings pour {len(lignes)} vêtements...",
                    "PROGRESS",
                )
                for v_id, titre in lignes:
                    # Calcul de l'embedding (384 floats)
                    embedding = model.encode(titre).tolist()

                    # Sauvegarde dans la nouvelle colonne
                    cur.execute(
                        """
                        UPDATE vetements 
                        SET titre_vector = %s 
                        WHERE id = %s;
                    """,
                        (embedding, v_id),
                    )

                # 6. Création d'un index HNSW optimisé pour la recherche sémantique
                log(
                    "Création de l'index HNSW sur la colonne 'titre_vector'...",
                    "PROGRESS",
                )
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS vetements_titre_vector_hnsw_idx 
                    ON vetements 
                    USING hnsw (titre_vector vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)

                log(
                    "Base de données mise à jour et indexée avec les embeddings 384D !",
                    "SUCCESS",
                )

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
