# ex04_films_setup.py
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def main():
    try:
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True
            register_vector(conn)
            with conn.cursor() as cur:
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
                    ("Avengers: Endgame", 2019, 8.4, [0.95, 0.15, 0.35, 0.10, 0.6]),
                    ("La La Land", 2016, 8.0, [0.05, 0.30, 0.55, 0.90, 0.0]),
                    ("Inception", 2010, 8.8, [0.70, 0.05, 0.50, 0.20, 0.9]),
                    (
                        "Le Diable s'habille en Prada",
                        2006,
                        6.9,
                        [0.05, 0.65, 0.45, 0.40, 0.0],
                    ),
                    ("Mad Max: Fury Road", 2015, 8.1, [0.98, 0.02, 0.20, 0.05, 0.4]),
                    ("Eternal Sunshine", 2004, 8.3, [0.00, 0.20, 0.75, 0.90, 0.2]),
                    ("Interstellar", 2014, 8.6, [0.45, 0.05, 0.70, 0.20, 0.95]),
                    ("Superbad", 2007, 7.6, [0.10, 0.92, 0.30, 0.25, 0.0]),
                    ("The Dark Knight", 2008, 9.0, [0.88, 0.05, 0.65, 0.10, 0.3]),
                    ("Amélie", 2001, 8.3, [0.05, 0.55, 0.60, 0.75, 0.1]),
                    ("Aliens", 1986, 8.4, [0.80, 0.08, 0.40, 0.05, 0.95]),
                    ("Forrest Gump", 1994, 8.8, [0.20, 0.40, 0.85, 0.60, 0.0]),
                    ("John Wick", 2014, 7.4, [0.98, 0.05, 0.15, 0.05, 0.1]),
                    ("The Notebook", 2004, 7.9, [0.02, 0.15, 0.60, 0.95, 0.0]),
                    ("Ex Machina", 2014, 7.7, [0.15, 0.02, 0.55, 0.15, 0.95]),
                ]

                for titre, annee, note, profil in catalogue:
                    cur.execute(
                        "INSERT INTO films (titre, annee, note, profil) VALUES (%s, %s, %s, %s)",
                        (titre, annee, note, np.array(profil)),
                    )

                # Créer un index HNSW pour la colonne profil
                cur.execute("""
                    CREATE INDEX ON films
                    USING hnsw (profil vector_cosine_ops)
                    WITH (m = 8, ef_construction = 40);
                """)

                print(f"✅ {len(catalogue)} films insérés et indexés")
                print(
                    "\nDimensions du profil : [action, comédie, drame, romance, sci-fi]"
                )

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
