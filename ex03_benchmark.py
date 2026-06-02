# ex03_benchmark.py

import sys
import time

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
                # ── Créer une table avec plus de données ────────────────────
                cur.execute("""
                    DROP TABLE IF EXISTS bench;
                    CREATE TABLE bench (
                        id        SERIAL PRIMARY KEY,
                        label     TEXT,
                        embedding vector(10)
                    );
                """)

                # Générer 5000 vecteurs aléatoires (dim=10)
                print("Génération de 5000 vecteurs aléatoires...")
                np.random.seed(42)
                n = 20000

                vecs = np.random.rand(n, 10).astype(np.float32)
                vecs = vecs / np.linalg.norm(
                    vecs, axis=1, keepdims=True
                )  # normalisation L2

                data = [(f"item_{i}", vecs[i].tolist()) for i in range(n)]
                cur.executemany(
                    "INSERT INTO bench (label, embedding) VALUES (%s, %s)", data
                )
                print(f"✅ {n} lignes insérées\n")

                # Vecteur de requête
                query = vecs[0]  # on cherche les voisins du premier vecteur

                def mesurer_query(label: str, repetitions: int = 10) -> float:
                    """Exécute la requête N fois et retourne le temps moyen en ms."""
                    temps = []
                    for _ in range(repetitions):
                        t0 = time.perf_counter()
                        cur.execute(
                            """
                            SELECT label FROM bench
                            ORDER BY embedding <=> %s::vector
                            LIMIT 5;
                        """,
                            (query.tolist(),),
                        )
                        cur.fetchall()
                        temps.append((time.perf_counter() - t0) * 1000)
                    moy = sum(temps) / len(temps)
                    print(
                        f"  {label:30s} : {moy:6.1f} ms  (moy sur {repetitions} requêtes)"
                    )
                    return moy

                # ── Sans index ───────────────────────────────────────────────
                cur.execute("SET enable_indexscan = OFF;")
                t_seq = mesurer_query("Sequential scan (sans index)")

                # ── Création du HNSW ─────────────────────────────────────────
                print("\nCréation de l'index HNSW...")
                t0 = time.perf_counter()
                cur.execute("""
                    CREATE INDEX bench_hnsw_idx ON bench
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
                print(f"Index créé en {time.perf_counter() - t0:.2f}s\n")

                # ── Avec index HNSW ──────────────────────────────────────────
                cur.execute("SET enable_indexscan = ON;")
                cur.execute("SET hnsw.ef_search = 40;")
                t_hnsw = mesurer_query("HNSW (ef_search=40)")

                # Effet de ef_search sur la précision/vitesse
                print("\nEffet de ef_search (compromis vitesse ↔ précision) :")
                for ef in [10, 20, 40, 80, 160]:
                    cur.execute(f"SET hnsw.ef_search = {ef};")
                    mesurer_query(f"  HNSW ef_search={ef}")

                print(f"\n→ Gain de vitesse HNSW vs seq scan : ×{t_seq / t_hnsw:.1f}")
                print("→ ef_search plus bas = plus rapide mais moins précis")

                cur.execute("SET hnsw.ef_search = 40;")
                cur.execute("SELECT pg_size_pretty(pg_indexes_size('bench'))")
                taille_hnsw = cur.fetchall()[0][0]

                print(f"taille hnsw = {taille_hnsw}")

                print("Plan d'exécution avec index :")
                cur.execute(
                    """
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT label FROM bench
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5;
                """,
                    (query.tolist(),),
                )

                for (ligne,) in cur.fetchall():
                    print(" ", ligne)

                # ── Création de l'index IVFFlat ──────────────────────────────
                print("\nCréation de l'index IVFFlat...")
                t0 = time.perf_counter()
                cur.execute("""
                    CREATE INDEX bench_ivfflat_idx ON bench
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 50);
                """)
                print(f"Index créé en {time.perf_counter() - t0:.2f}s\n")

                # ── Avec index IVFFlat ───────────────────────────────────────
                cur.execute("SET enable_indexscan = ON;")
                cur.execute("SET ivfflat.probes = 10;")
                t_ivfflat = mesurer_query("IVFFlat (probes=10)")

                # Effet de ivfflat.probes sur la précision/vitesse
                print("\nEffet de probes (compromis vitesse ↔ précision) :")
                # On teste différentes valeurs de sondage (maximum 50 puisque lists=50)
                for probes in [1, 5, 10, 20, 50]:
                    cur.execute(f"SET ivfflat.probes = {probes};")
                    mesurer_query(f"  IVFFlat probes={probes}")

                print(
                    f"\n→ Gain de vitesse IVFFlat vs seq scan : ×{t_seq / t_ivfflat:.1f}"
                )
                print(
                    "→ probes plus bas = plus rapide mais moins précis (1 = très approximatif)"
                )

                # Réinitialisation à une valeur équilibrée pour le plan d'exécution
                cur.execute("SET ivfflat.probes = 10;")
                cur.execute("SELECT pg_size_pretty(pg_indexes_size('bench'))")
                taille_ivfflat = cur.fetchall()[0][0]

                print(f"\ntaille ivfflat = {taille_ivfflat}")

                print("\nPlan d'exécution avec index IVFFlat :")
                cur.execute(
                    """
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT label FROM bench
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5;
                """,
                    (query.tolist(),),
                )

                for (ligne,) in cur.fetchall():
                    print(" ", ligne)

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
