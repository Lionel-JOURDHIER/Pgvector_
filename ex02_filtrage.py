# ex02_filtrage.py
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


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

            with conn.cursor() as cur:
                # 1. ÉVOLUTION DU SCHÉMA : Ajouter une colonne "categorie" pour l'exercice
                log(
                    "Vérification / Ajout de la colonne 'categorie'...",
                    "PROGRESS",
                )
                cur.execute(
                    "ALTER TABLE produits ADD COLUMN IF NOT EXISTS categorie TEXT;"
                )

                # 2. ENRICHISSEMENT DES MÉTADONNÉES
                log("Mise à jour des métadonnées du catalogue...", "PROGRESS")
                categories = {
                    "mangue": "fruit",
                    "fraise": "fruit",
                    "vanille": "epice",
                    "ananas": "fruit",
                    "piment": "epice",
                    "curry": "epice",
                    "wasabi": "epice",
                    "fruit de la passion": "fruit",
                    "safran": "epice",
                    "clou de girofle": "epice",
                }
                for nom, cat in categories.items():
                    cur.execute(
                        "UPDATE produits SET categorie = %s WHERE nom = %s", (cat, nom)
                    )

                log(
                    f"Structure et {len(categories)} catégories synchronisées.",
                    "SUCCESS",
                )

                # Configuration de la requête cibl
                query = np.array([0.8, 0.5, 0.6])  # requête équilibrée
                print("\n" + "=" * 55)
                print("🎯 Requête cible : sucré=0.8, épicé=0.5, exotique=0.6")
                print("=" * 55)

                # ── RECHERCHE 1 : SANS FILTRE ─────────────────────────────
                log(
                    "Exécution de la recherche vectorielle globale...",
                    "PROGRESS",
                )
                print("\n🔍 Sans filtre — top 4 tous produits :")
                cur.execute(
                    """
                    SELECT nom, categorie,
                        ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 3) AS sim
                    FROM produits
                    ORDER BY caracteristiques <=> %s::vector
                    LIMIT 4;
                """,
                    (query.tolist(), query.tolist()),
                )
                results_all = cur.fetchall()
                for nom, cat, sim in results_all:
                    print(f"  🔹 [{sim}] {nom:20s} ({cat})")
                log("Top 4 global récupéré.", "SUCCESS")

                # ── RECHERCHE 2 : FILTRE MÉTADONNÉES ──────────────────────
                log(
                    "Exécution de la recherche filtrée par catégorie ('fruit')...",
                    "PROGRESS",
                )
                print("\n🔍 Filtré sur categorie='fruit' — top 4 :")
                cur.execute(
                    """
                    SELECT nom, categorie,
                        ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 4) AS sim
                    FROM produits
                    WHERE categorie = 'fruit'           -- filtre SQL classique
                    ORDER BY caracteristiques <=> %s::vector
                    LIMIT 4;
                """,
                    (query.tolist(), query.tolist()),
                )

                results_filtered = cur.fetchall()
                for nom, cat, sim in results_filtered:
                    print(f"  🔹 [{sim}] {nom:20s} ({cat})")
                log("Top 4 filtré par métadonnée récupéré.", "SUCCESS")

                # ── RECHERCHE 3 : FILTRE PAR SEUIL ────────────────────────
                log(
                    "Exécution du filtrage par seuil de similarité (> 0.95)...",
                    "PROGRESS",
                )
                print("\n🔍 Seuil de similarité > 0.95 :")
                cur.execute(
                    """
                    SELECT nom,
                        ROUND((1 - (caracteristiques <=> %s::vector))::numeric, 3) AS sim
                    FROM produits
                    WHERE (1 - (caracteristiques <=> %s::vector)) > 0.95
                    ORDER BY sim DESC;
                """,
                    (query.tolist(), query.tolist()),
                )
                rows_seuil = cur.fetchall()
                if rows_seuil:
                    for nom, sim in rows_seuil:
                        print(f"  🔹 [{sim}] {nom}")
                else:
                    print(
                        "  ❌ (aucun résultat avec ce seuil), veuillez baisser la valeur du seuil."
                    )
                log("Filtrage par seuil terminé.", "SUCCESS")

                print("\n" + "─" * 55)
                log("Toutes les analyses de filtrage sont terminées.", "SUCCESS")
                print("─" * 55 + "\n")

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
