import sys
from datetime import datetime

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import OperationalError

from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER


def log(message, level="INFO"):
    """Fonction utilitaire pour formater les logs dans le terminal"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "INFO": "💡",
        "SUCCESS": "✅",
        "PROGRESS": "⏳",
        "ERROR": "❌",
        "WARN": "⚠️",
    }
    print(f"[{timestamp}] {prefix.get(level, '•')} {message}")


def main():
    log(
        f"Tentative de connexion à postgres://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}...",
        "PROGRESS",
    )

    try:
        # Utilisation de 'with' pour fermer automatiquement la connexion à la fin
        with psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
        ) as conn:
            conn.autocommit = True
            log("Connexion réseau établie avec succès.", "SUCCESS")

            # Utilisation de 'with' pour le curseur également
            with conn.cursor() as cur:
                # Information bonus : Version de PostgreSQL
                cur.execute("SELECT version();")
                db_version = cur.fetchone()[0].split(",")[0]
                log(f"Version du serveur PostgreSQL : {db_version}", "INFO")

                # 1. Activation de l'extension
                log(
                    "Vérification / Création de l'extension 'vector'...",
                    "PROGRESS",
                )
                # On vide les anciens messages pour être sûr
                del conn.notices[:]

                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                deja_existante = any(
                    "already exists" in notice.lower() for notice in conn.notices
                )

                if deja_existante:
                    log("L'extension 'vector' existait déjà. Rien à faire !", "SUCCESS")
                else:
                    log(
                        "L'extension 'vector' n'existait pas. Elle vient d'être créée !",
                        "SUCCESS",
                    )

                # 2. Enregistrement du type dans psycopg2
                log(
                    "Enregistrement du type 'vector' dans le pilote Python...",
                    "PROGRESS",
                )
                register_vector(conn)
                log("Type 'vector' enregistré avec succès.", "SUCCESS")

                # 3. Double vérification de la version installée
                cur.execute(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
                )
                result = cur.fetchone()

                if result:
                    log(
                        f"Validation finale : pgvector v{result[0]} est prêt à l'emploi !",
                        "SUCCESS",
                    )
                else:
                    log(
                        "L'extension semble active mais sa version n'a pas pu être récupérée.",
                        "ERROR",
                    )

    except OperationalError as e:
        log(
            f"Erreur critique lors de la connexion à la base de données :\n{e}",
            "ERROR",
        )
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)

    log("Script terminé proprement. Connexions fermées.", "INFO")


if __name__ == "__main__":
    main()
