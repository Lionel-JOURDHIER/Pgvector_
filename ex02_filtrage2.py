# ex02_filtrage.py
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def chercher(conn, query_vec: np.ndarray, categorie=None, top_k=3) -> list:
    response = []
    # 1. On prépare la vraie requête SQL avec le paramètre LIMIT
    if categorie:
        query_sql = f"""
        SELECT nom, 
               ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 4) AS sim
        FROM produits
        WHERE categorie = '{categorie}'
        ORDER BY caracteristiques <=> %s::vector
        LIMIT %s;
    """
    else:
        query_sql = """
            SELECT nom, 
                ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 4) AS sim
            FROM produits
            ORDER BY caracteristiques <=> %s::vector
            LIMIT %s;
        """
    with conn.cursor() as cur:
        cur.execute(query_sql, (query_vec.tolist(), query_vec.tolist(), top_k))
        res = cur.fetchall()
        for nom, sim in res:
            response.append({"nom": nom, "sim": sim})
        return response[:top_k]


def main():
    log("Démarrage du script de filtrage hybride...", "INFO")
    try:
        log("Connexion à la base de données PostgreSQL...", "PROGRESS")
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True

            log("Enregistrement du type 'vector'...", "PROGRESS")
            register_vector(conn)

            # Configuration de la requête cible
            query = np.array([0.2, 0.8, 0.7])  # requête peu sucrée
            print("\n" + "=" * 55)
            print("🎯 Requête cible : sucré=0.2, épicé=0.8, exotique=0.7")
            print("=" * 55)

            # ── RECHERCHE 1 : SANS FILTRE ─────────────────────────────
            log(
                "Exécution de la recherche vectorielle globale...",
                "PROGRESS",
            )
            print("\n🔍 Sans filtre — top 4 tous produits :")

            results_all = chercher(conn, query, categorie="fruit", top_k=4)
            print(results_all)

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
