# ex04_recommandation.py
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log

# ── Connexion ────────────────────────────────────────────────
conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()


# ── Fonctions utilitaires ────────────────────────────────────


def creer_profil(
    action=0.0, comedie=0.0, drame=0.0, romance=0.0, scifi=0.0
) -> np.ndarray:
    """
    Crée un vecteur de profil utilisateur.
    Chaque valeur est entre 0 (pas intéressé) et 1 (très intéressé).
    """
    return np.array([action, comedie, drame, romance, scifi], dtype=np.float32)


def recommander(
    profil_user: np.ndarray,
    top_k: int = 5,
    note_min: float = 0.0,
    annee_min: int = 1900,
) -> list[dict]:
    """
    Recommande des films similaires au profil utilisateur.

    Paramètres :
    - profil_user : vecteur numpy [action, comédie, drame, romance, sci-fi]
    - top_k : nombre de films à retourner
    - note_min : note IMDb minimale (filtre SQL)
    - annee_min : année de sortie minimale (filtre SQL)

    Retourne une liste de dicts avec titre, annee, note, similarite.
    """
    cur.execute(
        """
        SELECT titre,
               annee,
               note,
               ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
        FROM films
        WHERE note >= %s
          AND annee >= %s
        ORDER BY profil <=> %s::vector
        LIMIT %s;
    """,
        (profil_user.tolist(), note_min, annee_min, profil_user.tolist(), top_k),
    )

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
    cur.execute(
        """
        SELECT titre,
               annee,
               ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
        FROM films
        WHERE titre != %s
        ORDER BY profil <=> %s::vector
        LIMIT %s;
    """,
        (profil_ref, titre_ref, profil_ref, top_k),
    )

    return [
        {"titre": row[0], "annee": row[1], "sim": float(row[2])}
        for row in cur.fetchall()
    ]


def afficher(titre: str, resultats: list[dict]):
    """Affiche les résultats proprement."""
    print(f"\n{'=' * 50}")
    print(f"  {titre}")
    print(f"{'=' * 50}")
    for r in resultats:
        if "note" in r:
            print(f"  [{r['sim']:.3f}]  {r['titre']:35s}  ({r['annee']})  ★{r['note']}")
        else:
            print(f"  [{r['sim']:.3f}]  {r['titre']:35s}  ({r['annee']})")


# ── Scénarios de recommandation ───────────────────────────────


def main():
    try:
        # Profil 1 : fan d'action/sci-fi
        profil_action_scifi = creer_profil(action=0.9, scifi=0.85, drame=0.3)
        afficher("Fan d'action et sci-fi", recommander(profil_action_scifi))

        # Profil 2 : amateur de comédies romantiques
        profil_comedie_romance = creer_profil(comedie=0.85, romance=0.80, drame=0.4)
        afficher("Amateur de comédies romantiques", recommander(profil_comedie_romance))

        # Profil 3 : drames récents bien notés
        profil_drame = creer_profil(drame=0.9, romance=0.5)
        afficher(
            "Drames bien notés depuis 2000 (note ≥ 8.0)",
            recommander(profil_drame, note_min=8.0, annee_min=2000),
        )

        # Films similaires
        afficher("Films similaires à 'Inception'", films_similaires("Inception"))
        afficher("Films similaires à 'La La Land'", films_similaires("La La Land"))

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
