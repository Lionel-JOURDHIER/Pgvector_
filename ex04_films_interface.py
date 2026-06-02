# ex04_interface.py
# (nécessite d'avoir exécuté ex04_films_setup.py avant)
import sys

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
from register_pg_vector import log

DIMS = ["action", "comédie", "drame", "romance", "sci-fi"]


def main():
    try:
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        ) as conn:
            conn.autocommit = True
            register_vector(conn)
            with conn.cursor() as cur:
                print("🎬 Moteur de recommandation de films")
                print("   Basé sur pgvector — recherche vectorielle")

                while True:
                    print("\n" + "-" * 40)
                    print("1. Créer un profil et obtenir des recommandations")
                    print("2. Trouver des films similaires à un titre")
                    print("3. Trouver le film le moins similaire à un titre ")
                    print("4. Quitter")

                    choix = input("\nVotre choix : ").strip()

                    if choix == "1":
                        profil = saisir_profil()
                        recommander_interactif(cur, profil)

                    elif choix == "2":
                        log(
                            "Extraction de la liste des films disponibles...",
                            "PROGRESS",
                        )
                        cur.execute("SELECT titre FROM films ORDER BY titre;")
                        titres = [r[0] for r in cur.fetchall()]
                        print("\n🎬 Films disponibles dans le catalogue :")
                        for i, t in enumerate(titres, 1):
                            print(f"  {i:2d}. {t}")
                        try:
                            idx = int(input("Numéro du film : ")) - 1
                            if idx < 0 or idx >= len(titres):
                                raise IndexError

                            titre_ref = titres[idx]
                            cur.execute(
                                "SELECT profil FROM films WHERE titre = %s;",
                                (titre_ref,),
                            )
                            row_profil = cur.fetchone()

                            if row_profil:
                                profil_list = (
                                    row_profil[0].tolist()
                                    if hasattr(row_profil[0], "tolist")
                                    else row_profil[0]
                                )

                                log(
                                    "Étape 1 : Récupération du Top 20 vectoriel via PostgreSQL...",
                                    "PROGRESS",
                                )
                                # La requête SQL redevenant simple, elle utilise l'index HNSW à 100%
                                cur.execute(
                                    """
                                    SELECT titre, annee, note,
                                        ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
                                    FROM films 
                                    WHERE titre != %s
                                    ORDER BY profil <=> %s::vector
                                    LIMIT 20;  -- On prend un pool large de candidats à re-classer
                                """,
                                    (profil_list, titre_ref, profil_list),
                                )
                                candidates = cur.fetchall()

                                log(
                                    "Étape 2 : Application du score hybride et tri en Python...",
                                    "PROGRESS",
                                )
                                recommandations = []

                                for titre, annee, note, sim in candidates:
                                    # 🧠 Appel de ta fonction isolée
                                    score_final = calculer_score_hybride(sim, note)

                                    recommandations.append(
                                        {
                                            "titre": titre,
                                            "annee": annee,
                                            "note": note,
                                            "sim": sim,
                                            "score": score_final,
                                        }
                                    )

                                # Tri de la liste de dictionnaires par la clé 'score' de manière décroissante
                                recommandations.sort(
                                    key=lambda x: x["score"], reverse=True
                                )

                                # On extrait notre Top 4 final après re-ranking
                                top_4 = recommandations[:4]

                                # Affichage des résultats
                                print(
                                    f"\n✨ Recommandations hybrides (Re-ranked) pour '{titre_ref}' :"
                                )
                                print(
                                    f"   {'Film':25s} | {'Note':5s} | {'Sim. Vec':8s} | {'Score Final':s}"
                                )
                                print("   " + "─" * 60)

                                for item in top_4:
                                    film_label = f"{item['titre']} ({item['annee']})"
                                    print(
                                        f"   {film_label:25s} | ★{item['note']:<4.1f} | {item['sim']:<8.3f} | 🔥 {item['score']:.3f}"
                                    )

                                log("Re-ranking terminé avec succès.", "SUCCESS")
                            else:
                                log(
                                    f"Impossible de trouver le profil de '{titre_ref}'",
                                    "ERROR",
                                )
                        except (ValueError, IndexError):
                            print("Numéro invalide")
                    elif choix == "3":
                        cur.execute("SELECT titre FROM films ORDER BY titre;")
                        titres = [r[0] for r in cur.fetchall()]
                        print("\nFilms disponibles :")
                        for i, t in enumerate(titres, 1):
                            print(f"  {i:2d}. {t}")
                        try:
                            idx = int(input("Numéro du film : ")) - 1
                            titre_ref = titres[idx]
                            trouver_contraire(cur, titre_ref)
                        except (ValueError, IndexError):
                            print("Numéro invalide")
                    elif choix == "4":
                        break

                print("Au revoir !")
    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


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


def calculer_score_hybride(similarity, note) -> float:
    """Calcule le score combiné : 70% similarité vectorielle + 30% note du film."""
    # 🧠 Sécurité totale : on force le passage en float pour les deux valeurs
    sim_float = float(similarity)
    note_float = float(note)

    score = (0.7 * sim_float) + (0.3 * (note_float / 10.0))
    return round(score, 3)


def recommander_interactif(cur, profil: np.ndarray, top_k=5):
    cur.execute(
        """
        SELECT titre, annee, note,
               ROUND((1 - (profil <=> %s::vector))::numeric, 3) AS sim
        FROM films
        ORDER BY profil <=> %s::vector
        LIMIT %s;
    """,
        # Partie B :ORDER BY profil <=> %s::vector DESC
        (profil.tolist(), profil.tolist(), top_k),
    )

    print("\n🎬 Recommandations pour votre profil :")
    print(f"   [{', '.join(f'{v:.1f}' for v in profil)}]")
    print()
    for titre, annee, note, sim in cur.fetchall():
        barre = "█" * int(sim * 20)
        print(f"  {barre:20s}  {sim:.3f}  {titre} ({annee}) ★{note}")


def trouver_contraire(cur, titre_ref, top_k=5):
    cur.execute(
        """
        SELECT titre, annee,
            ROUND((1 - (profil <=> (
                SELECT profil FROM films WHERE titre = %s
            )))::numeric, 3) AS sim
        FROM films WHERE titre != %s
        ORDER BY profil <=> (SELECT profil FROM films WHERE titre = %s) DESC
        LIMIT 4;
    """,
        (titre_ref, titre_ref, titre_ref),
    )
    print(f"\nFilms le moins similaire à '{titre_ref}' :")
    for t, a, s in cur.fetchall():
        print(f"  [{s}]  {t} ({a})")


if __name__ == "__main__":
    main()
