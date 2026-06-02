# ex02_operateurs.py
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def main():
    log("Démarrage du script d'analyse des opérateurs vectoriels...", "INFO")
    try:
        log("Connexion à la base de données PostgreSQL...", "PROGRESS")
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True
            log("Enregistrement du type 'vector' dans le pilote...", "PROGRESS")
            register_vector(conn)
            with conn.cursor() as cur:
                # Vecteur de requête : je cherche quelque chose de "sucré et exotique"
                query = np.array([1.0, 0.0, 1.0])  # sucré max, pas épicé, exotique max

                print("=" * 55)
                print("Requête : sucré=1.0, épicé=0.0, exotique=1.0")
                print("=" * 55)

                # ── Opérateur <=> : distance cosinus ──────────────────────
                log(
                    "Exécution de la recherche par Similarité Cosinus (<=>)...",
                    "PROGRESS",
                )
                print("\n🔵 <=> Distance cosinus (recommandé pour textes)")
                cur.execute(
                    """
                    SELECT nom,
                        ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 4) AS similarite,
                        caracteristiques::text AS vec
                    FROM produits
                    ORDER BY caracteristiques <=> %s::vector
                    LIMIT 4;
                """,
                    (query.tolist(), query.tolist()),
                )
                results_cos = cur.fetchall()
                for nom, sim, vec in results_cos:
                    print(f"  {nom:12s}  sim={sim}  {vec}")
                log(
                    f"Top {len(results_cos)} par similarité cosinus récupéré.",
                    "SUCCESS",
                )
                # ── Opérateur <-> : distance L2 (Euclidienne) ─────────────
                log(
                    "Exécution de la recherche par Distance Euclidienne/L2 (<->)...",
                    "PROGRESS",
                )
                print("\n🟢 <-> Distance L2 / Euclidienne (sensible à la magnitude)")
                cur.execute(
                    """
                    SELECT nom,
                        ROUND((caracteristiques <-> %s::vector)::numeric, 4) AS distance_l2
                    FROM produits
                    ORDER BY caracteristiques <-> %s::vector
                    LIMIT 4;
                """,
                    (query.tolist(), query.tolist()),
                )
                results_l2 = cur.fetchall()
                for nom, dist in results_l2:
                    print(f"  {nom:12s}  dist_L2={dist}")

                log(
                    f"Top {len(results_l2)} par distance L2 récupéré.",
                    "SUCCESS",
                )

                # ── Comparaison : même résultats ? ────────────────────────
                print("\n💡 Même classement ? Les deux opérateurs donnent souvent")
                print("   des résultats proches, mais pas toujours identiques.")
                print("   Pour des embeddings texte normalisés, <=> est standard.")

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
