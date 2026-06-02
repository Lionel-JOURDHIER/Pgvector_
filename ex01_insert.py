# ex01_insert.py
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError
from psycopg2.extras import execute_batch

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def main():
    log("Démarrage du script d'ensertion de vecteurs dans la table...", "INFO")
    try:
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True

            # Enregistrement du type vector
            register_vector(conn)

            with conn.cursor() as cur:
                # 1. SÉCURITÉ : On crée un index UNIQUE si ce n'est pas déjà fait
                # Cela empêche techniquement Postgres d'accepter deux fois le même nom
                log(
                    "Vérification de la contrainte d'unicité sur le nom...",
                    "PROGRESS",
                )
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS produits_nom_idx ON produits (nom);
                """)
                # 2. PRÉPARATION DES DONNÉES
                # Données : [sucré, épicé, exotique]
                produits = [
                    ("mangue", np.array([0.9, 0.1, 0.95])),
                    ("piment", np.array([0.1, 0.95, 0.6])),
                    ("fraise", np.array([0.85, 0.05, 0.2])),
                    ("curry", np.array([0.2, 0.9, 0.7])),
                    ("vanille", np.array([0.95, 0.02, 0.3])),
                    ("wasabi", np.array([0.05, 0.98, 0.55])),
                    ("ananas", np.array([0.8, 0.08, 0.88])),
                ]
                log(
                    "Traitement des produits terminé (Ajouts / Mises à jour effectués).",
                    "SUCCESS",
                )

                # 3. Insertion un par un
                for nom, vec in produits:
                    cur.execute(
                        """INSERT INTO produits (nom, caracteristiques) 
                            VALUES (%s, %s)
                            ON CONFLICT (nom) 
                            DO UPDATE SET caracteristiques = EXCLUDED.caracteristiques;""",
                        (nom, vec),  # numpy array → pgvector sait le convertir
                    )

                log(f" {len(produits)} produits insérés", "SUCCESS")

                # 3.b INSERTION GROUPÉE (Bulk Insert)
                produits2 = [
                    ("fruit de la passion", np.array([0.85, 0.05, 0.95])),
                    ("safran", np.array([0.15, 0.65, 0.80])),
                    ("clou de girofle", np.array([0.20, 0.85, 0.40])),
                ]
                log(
                    f"Insertion groupée de {len(produits2)} produits...",
                    "PROGRESS",
                )
                query = """INSERT INTO produits (nom, caracteristiques) 
                            VALUES (%s, %s)
                            ON CONFLICT (nom) 
                            DO UPDATE SET caracteristiques = EXCLUDED.caracteristiques;"""

                # execute_batch est beaucoup plus rapide qu'une boucle for classique
                execute_batch(cur, query, produits2)
                log(
                    f"{len(produits) + len(produits2)} produits traités avec succès.",
                    "SUCCESS",
                )

                # Vérification : lire les données insérées
                cur.execute(
                    "SELECT id, nom, caracteristiques FROM produits ORDER BY id;"
                )

                donnees = cur.fetchall()

                print("\n📊 DONNEE INSEREE DANS LA TABLE :")
                print("=" * 50)
                for id_, nom, vec in donnees:
                    print(f"  [{id_}] {nom:12s} → {np.round(vec, 2)}")

                print("=" * 50 + "\n")

                # Vérification : taille de la table
                cur.execute("SELECT COUNT(*) FROM produits;")
                taille_table = cur.fetchall()

                log(f"{taille_table} produits présents dans la table.", "SUCCESS")

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)

    log("Script d'insertion terminé proprement.", "SUCCESS")


if __name__ == "__main__":
    main()
