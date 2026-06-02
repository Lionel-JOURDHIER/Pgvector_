# ex01_table.py
import sys

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def main():
    log("Démarrage du script de configuration de la table...", "INFO")
    try:
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True

            with conn.cursor() as cur:
                # 1. CRUCIAL : On active l'extension D'ABORD
                log("Vérification de l'extension 'vector'...", "PROGRESS")

                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # 2. Maintenant que le type existe à coup sûr, on l'enregistre dans Python
                log(
                    "Enregistrement du type 'vector' dans le pilote Python...",
                    "PROGRESS",
                )

                register_vector(conn)

                # Requête pour vérifier l'existence de la table
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'produits'
                    );
                """)
                table_existe = cur.fetchone()[0]

                if table_existe:
                    log("La table 'produits' existe déjà en base de données !", "WARN")
                    # Ici, tu choisis quoi faire : ne rien faire, ou ajouter des données...
                else:
                    log(
                        "La table 'produits' n'existe pas. Création en cours...",
                        "PROGRESS",
                    )
                    # 2. Création de la table

                    # Création d'une table "produits" avec 3 colonnes :
                    # - id : clé primaire auto-incrémentée
                    # - nom : le nom du produit
                    # - caracteristiques : vecteur de dimension 3
                    #   Chaque dimension représente une propriété :
                    #   [sucré (0-1), épicé (0-1), exotique (0-1)]
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS produits (
                            id               SERIAL PRIMARY KEY,
                            nom              TEXT NOT NULL,
                            caracteristiques vector(3)
                        );
                    """)
                    log(
                        "Table 'produits' recréée avec succès (Dimension : 3).",
                        "SUCCESS",
                    )

                # 4. Inspection de la structure pour confirmation
                log("Fouille de l'information_schema...", "PROGRESS")
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'produits'
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()

                # Un affichage un peu plus sexy pour le terminal
                print("\n📊 STRUCTURE DE LA TABLE GENERÉE :")
                print("=" * 50)
                for col, dtype in columns:
                    print(f"  🔹 {col:18s} ➔   Type : {dtype}")
                print("=" * 50 + "\n")

    except OperationalError as e:
        log(f"Impossible de se connecter à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)

    log("Script terminé. Prêt pour l'insertion de données !", "SUCCESS")


if __name__ == "__main__":
    main()
