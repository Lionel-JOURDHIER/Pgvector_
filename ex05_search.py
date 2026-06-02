import sys

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError
from sentence_transformers import SentenceTransformer

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log


def recherche_semantique(cur, model, requete_texte, limite=3):
    """
    Transforme une requête textuelle en embedding et cherche les vêtements
    les plus proches sémantiquement dans la base de données.
    """
    # 1. Générer l'embedding de la requête (liste de 384 floats)
    embedding_requete = model.encode(requete_texte).tolist()

    # 2. Requête SQL corrigée avec le cast ::vector
    cur.execute(
        """
        SELECT id, titre, style, saisons, type, (titre_vector <=> %s::vector) AS distance
        FROM vetements
        ORDER BY titre_vector <=> %s::vector
        LIMIT %s;
        """,
        (embedding_requete, embedding_requete, limite),
    )

    return cur.fetchall()


def main():
    try:
        # Chargement du modèle (doit être le même que pour l'insertion !)
        log("Chargement du modèle de recherche sémantique...", "PROGRESS")
        model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        # Connexion à la BDD
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            register_vector(conn)

            with conn.cursor() as cur:
                # Les requêtes de test (sans aucun mot-clé du catalogue)
                requetes_test = [
                    "tenue pour un entretien d'embauche",
                    "vêtements pour partir à la montagne",
                    "habit confortable pour rester à la maison",
                    "tenue pour une soirée chic",
                ]

                print("\n" + "=" * 60)
                print(" 🚀 RECHERCHE SÉMANTIQUE TRADUCTION DE SENS (PGVECTOR)")
                print("=" * 60)

                for requete in requetes_test:
                    print(f"\n🔍 Requête : « {requete} »")
                    print("-" * 50)

                    resultats = recherche_semantique(cur, model, requete, limite=5)

                    for v_id, titre, style, saisons, v_type, distance in resultats:
                        # Calcul du score de similitude (1 - distance) pour affichage plus intuitif
                        score_similitude = (1 - distance) * 100
                        print(
                            f"   • [{score_similitude:.1f}%] {titre} ({v_type} | {style} | {saisons})"
                        )

                print("\n" + "=" * 60)

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
