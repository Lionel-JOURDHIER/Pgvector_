# ex04_films_setup.py
import sys

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
                log("Vérification de l'extension pgvector...", "PROGRESS")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                log("Création de la table 'vetements'...", "PROGRESS")
                # Schéma : boutique avec profil vectoriel + métadonnées
                cur.execute("""
                    DROP TABLE IF EXISTS vetements;
                    CREATE TABLE vetements (
                        id      SERIAL PRIMARY KEY,
                        titre   TEXT NOT NULL,
                        style   TEXT,
                        saisons TEXT,
                        type    TEXT,
                        activites vector(10)
                    );
                """)

                # Ci jointle vecteur pour l'activité
                # 1. Quotidien / Casual
                # 2. Bureau / Pro
                # 3. Soirée / Sortie
                # 4. Cérémonie / Gala
                # 5. Détente / Maison
                # 6. Sport / Fitness
                # 7. Outdoor / Randonnée
                # 8. Grand Froid / Ski
                # 9. Plage / Soleil
                # 10. Voyage / Transit

                # Catalogue des Vetement avec le style, la saison, ke type

                catalogue = [
                    {
                        "titre": "T-shirt blanc en coton",
                        "style": "Casual",
                        "saisons": "Été/Printemps",
                        "type": "Haut",
                        "activites": [1.0, 0.2, 0.3, 0.0, 0.8, 0.1, 0.2, 0.0, 0.7, 0.6],
                    },
                    {
                        "titre": "Pull en laine pour l'hiver",
                        "style": "Casual",
                        "saisons": "Hiver",
                        "type": "Haut",
                        "activites": [0.8, 0.4, 0.3, 0.0, 0.7, 0.0, 0.4, 0.9, 0.0, 0.5],
                    },
                    {
                        "titre": "Jean bleu coupe droite",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [1.0, 0.5, 0.5, 0.0, 0.5, 0.0, 0.3, 0.2, 0.0, 0.7],
                    },
                    {
                        "titre": "Robe élégante noire",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Robe",
                        "activites": [0.2, 0.4, 1.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.2, 0.4],
                    },
                    {
                        "titre": "Veste imperméable de randonnée",
                        "style": "Sport",
                        "saisons": "Automne/Printemps",
                        "type": "Veste",
                        "activites": [0.3, 0.0, 0.0, 0.0, 0.1, 0.5, 1.0, 0.6, 0.0, 0.7],
                    },
                    {
                        "titre": "Chaussures de sport légères",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [0.7, 0.1, 0.1, 0.0, 0.4, 1.0, 0.6, 0.0, 0.3, 0.8],
                    },
                    {
                        "titre": "Manteau chaud en duvet",
                        "style": "Casual",
                        "saisons": "Hiver",
                        "type": "Veste",
                        "activites": [0.7, 0.3, 0.2, 0.0, 0.2, 0.1, 0.6, 1.0, 0.0, 0.6],
                    },
                    {
                        "titre": "Chemise blanche professionnelle",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.4, 1.0, 0.6, 0.6, 0.1, 0.0, 0.0, 0.0, 0.0, 0.5],
                    },
                    {
                        "titre": "Short de sport respirant",
                        "style": "Sport",
                        "saisons": "Été",
                        "type": "Bas",
                        "activites": [0.4, 0.0, 0.0, 0.0, 0.6, 1.0, 0.4, 0.0, 0.8, 0.4],
                    },
                    {
                        "titre": "Baskets pour courir",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [0.6, 0.0, 0.0, 0.0, 0.3, 1.0, 0.5, 0.0, 0.2, 0.6],
                    },
                    {
                        "titre": "Sweat à capuche gris heather",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.9, 0.1, 0.3, 0.0, 0.9, 0.4, 0.4, 0.3, 0.0, 0.8],
                    },
                    {
                        "titre": "Pantalon chino beige",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.9, 0.7, 0.6, 0.0, 0.4, 0.0, 0.2, 0.1, 0.4, 0.8],
                    },
                    {
                        "titre": "Veste en jean délavé",
                        "style": "Casual",
                        "saisons": "Printemps/Automne",
                        "type": "Veste",
                        "activites": [0.9, 0.3, 0.6, 0.0, 0.2, 0.0, 0.3, 0.0, 0.2, 0.7],
                    },
                    {
                        "titre": "Jupe en jean boutonnée",
                        "style": "Casual",
                        "saisons": "Été/Printemps",
                        "type": "Bas",
                        "activites": [0.9, 0.2, 0.6, 0.0, 0.3, 0.0, 0.1, 0.0, 0.6, 0.5],
                    },
                    {
                        "titre": "Top à rayures (marinière)",
                        "style": "Casual",
                        "saisons": "Été/Printemps",
                        "type": "Haut",
                        "activites": [0.9, 0.4, 0.5, 0.0, 0.6, 0.0, 0.2, 0.0, 0.7, 0.7],
                    },
                    {
                        "titre": "Cardigan en maille torsadée",
                        "style": "Casual",
                        "saisons": "Hiver/Automne",
                        "type": "Haut",
                        "activites": [0.8, 0.5, 0.4, 0.0, 0.8, 0.0, 0.2, 0.4, 0.0, 0.6],
                    },
                    {
                        "titre": "Bottines en cuir marron",
                        "style": "Casual",
                        "saisons": "Hiver/Automne",
                        "type": "Chaussures",
                        "activites": [0.8, 0.6, 0.7, 0.1, 0.1, 0.0, 0.4, 0.3, 0.0, 0.7],
                    },
                    {
                        "titre": "Short en jean taille haute",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Bas",
                        "activites": [0.9, 0.0, 0.5, 0.0, 0.4, 0.0, 0.2, 0.0, 0.9, 0.6],
                    },
                    {
                        "titre": "Casquette de baseball classique",
                        "style": "Sport",
                        "saisons": "Été/Printemps",
                        "type": "Accessoire",
                        "activites": [0.8, 0.0, 0.2, 0.0, 0.3, 0.7, 0.6, 0.1, 0.8, 0.7],
                    },
                    {
                        "titre": "Pantalon cargo kaki",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.8, 0.1, 0.3, 0.0, 0.5, 0.2, 0.8, 0.2, 0.2, 0.8],
                    },
                    {
                        "titre": "Chemise en flanelle à carreaux",
                        "style": "Casual",
                        "saisons": "Hiver/Automne",
                        "type": "Haut",
                        "activites": [0.9, 0.2, 0.4, 0.0, 0.7, 0.1, 0.5, 0.4, 0.0, 0.7],
                    },
                    {
                        "titre": "Blouson bomber noir",
                        "style": "Casual",
                        "saisons": "Printemps/Automne",
                        "type": "Veste",
                        "activites": [0.9, 0.4, 0.7, 0.0, 0.3, 0.0, 0.2, 0.1, 0.1, 0.8],
                    },
                    {
                        "titre": "Polo bleu marine en piqué",
                        "style": "Casual",
                        "saisons": "Été/Printemps",
                        "type": "Haut",
                        "activites": [0.8, 0.6, 0.5, 0.0, 0.4, 0.2, 0.3, 0.0, 0.6, 0.7],
                    },
                    {
                        "titre": "Salopette en jean bleu",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Ensemble",
                        "activites": [0.9, 0.1, 0.4, 0.0, 0.6, 0.0, 0.3, 0.0, 0.4, 0.6],
                    },
                    {
                        "titre": "Sneakers blanches en cuir",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [1.0, 0.5, 0.6, 0.0, 0.4, 0.3, 0.3, 0.1, 0.5, 0.9],
                    },
                    {
                        "titre": "Jupe midi plissée",
                        "style": "Chic",
                        "saisons": "Printemps/Été",
                        "type": "Bas",
                        "activites": [0.7, 0.6, 0.7, 0.2, 0.3, 0.0, 0.0, 0.0, 0.5, 0.6],
                    },
                    {
                        "titre": "T-shirt graphique imprimé",
                        "style": "Casual",
                        "saisons": "Été/Printemps",
                        "type": "Haut",
                        "activites": [0.9, 0.0, 0.5, 0.0, 0.7, 0.1, 0.1, 0.0, 0.6, 0.6],
                    },
                    {
                        "titre": "Pantalon en lin blanc",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Bas",
                        "activites": [0.8, 0.3, 0.6, 0.1, 0.6, 0.0, 0.1, 0.0, 1.0, 0.8],
                    },
                    {
                        "titre": "Sweat-shirt col rond basique",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.9, 0.2, 0.3, 0.0, 0.9, 0.3, 0.4, 0.2, 0.1, 0.7],
                    },
                    {
                        "titre": "Sandales en cuir confortables",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Chaussures",
                        "activites": [0.9, 0.2, 0.5, 0.0, 0.5, 0.0, 0.2, 0.0, 0.9, 0.7],
                    },
                    {
                        "titre": "Blazer noir cintré",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Veste",
                        "activites": [0.6, 1.0, 0.8, 0.4, 0.1, 0.0, 0.0, 0.0, 0.1, 0.7],
                    },
                    {
                        "titre": "Pantalon de costume ajusté",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.4, 1.0, 0.7, 0.5, 0.1, 0.0, 0.0, 0.0, 0.1, 0.6],
                    },
                    {
                        "titre": "Jupe crayon bleu marine",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.4, 1.0, 0.6, 0.4, 0.1, 0.0, 0.0, 0.0, 0.1, 0.5],
                    },
                    {
                        "titre": "Mocassins en cuir noir",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [0.7, 0.9, 0.6, 0.3, 0.2, 0.0, 0.1, 0.0, 0.2, 0.7],
                    },
                    {
                        "titre": "Chemisier en soie ivoire",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.5, 0.9, 0.8, 0.6, 0.1, 0.0, 0.0, 0.0, 0.2, 0.6],
                    },
                    {
                        "titre": "Tailleur pantalon gris anthracite",
                        "style": "Formel",
                        "saisons": "Hiver/Automne",
                        "type": "Ensemble",
                        "activites": [0.3, 1.0, 0.6, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6],
                    },
                    {
                        "titre": "Trench-coat beige classique",
                        "style": "Chic",
                        "saisons": "Printemps/Automne",
                        "type": "Veste",
                        "activites": [0.8, 0.9, 0.7, 0.3, 0.1, 0.0, 0.1, 0.0, 0.2, 0.9],
                    },
                    {
                        "titre": "Robe portefeuille de bureau",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Robe",
                        "activites": [0.6, 0.9, 0.7, 0.3, 0.3, 0.0, 0.0, 0.0, 0.3, 0.6],
                    },
                    {
                        "titre": "Cravate en soie bleue unie",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.1, 1.0, 0.5, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4],
                    },
                    {
                        "titre": "Derby en cuir marron",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [0.6, 1.0, 0.6, 0.4, 0.1, 0.0, 0.0, 0.0, 0.1, 0.6],
                    },
                    {
                        "titre": "Ceinture en cuir noire fine",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.7, 0.9, 0.7, 0.5, 0.2, 0.0, 0.1, 0.0, 0.2, 0.7],
                    },
                    {
                        "titre": "Pull col en V en cachemire",
                        "style": "Chic",
                        "saisons": "Hiver/Automne",
                        "type": "Haut",
                        "activites": [0.7, 0.8, 0.6, 0.3, 0.7, 0.0, 0.1, 0.2, 0.0, 0.7],
                    },
                    {
                        "titre": "Cardigan fin noir boutonné",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.7, 0.9, 0.5, 0.2, 0.5, 0.0, 0.1, 0.1, 0.1, 0.7],
                    },
                    {
                        "titre": "Pantalon carotte ceinturé",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.7, 0.9, 0.7, 0.2, 0.3, 0.0, 0.0, 0.0, 0.2, 0.6],
                    },
                    {
                        "titre": "Sac de travail en cuir rigide",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.5, 1.0, 0.4, 0.2, 0.0, 0.0, 0.0, 0.0, 0.1, 0.8],
                    },
                    {
                        "titre": "Robe de soirée longue pailletée",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Robe",
                        "activites": [0.0, 0.1, 0.9, 1.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.3],
                    },
                    {
                        "titre": "Costume de gala trois pièces",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Ensemble",
                        "activites": [0.0, 0.3, 0.7, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4],
                    },
                    {
                        "titre": "Smoking noir satiné",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Ensemble",
                        "activites": [0.0, 0.1, 0.6, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3],
                    },
                    {
                        "titre": "Escarpins vernis à talons aiguilles",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [0.2, 0.4, 1.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.2, 0.4],
                    },
                    {
                        "titre": "Pochette de soirée dorée",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.1, 0.1, 1.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.2, 0.4],
                    },
                    {
                        "titre": "Chemise de soirée col cassé",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.0, 0.4, 0.6, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3],
                    },
                    {
                        "titre": "Nœud papillon en velours noir",
                        "style": "Formel",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.0, 0.1, 0.6, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2],
                    },
                    {
                        "titre": "Top asymétrique en satin",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.5, 0.3, 1.0, 0.6, 0.1, 0.0, 0.0, 0.0, 0.4, 0.5],
                    },
                    {
                        "titre": "Combinaison pantalon chic noire",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Ensemble",
                        "activites": [0.5, 0.7, 0.9, 0.8, 0.1, 0.0, 0.0, 0.0, 0.3, 0.6],
                    },
                    {
                        "titre": "Jupe en similicuir noire",
                        "style": "Casual",
                        "saisons": "Automne/Hiver",
                        "type": "Bas",
                        "activites": [0.7, 0.2, 0.9, 0.4, 0.1, 0.0, 0.0, 0.0, 0.1, 0.5],
                    },
                    {
                        "titre": "Veste de blazer en velours",
                        "style": "Chic",
                        "saisons": "Hiver/Automne",
                        "type": "Veste",
                        "activites": [0.5, 0.5, 0.9, 0.7, 0.1, 0.0, 0.0, 0.0, 0.0, 0.5],
                    },
                    {
                        "titre": "Robe de cocktail rouge",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Robe",
                        "activites": [0.3, 0.2, 1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.3, 0.4],
                    },
                    {
                        "titre": "Sandales à talons argentées",
                        "style": "Chic",
                        "saisons": "Été/Printemps",
                        "type": "Chaussures",
                        "activites": [0.3, 0.2, 1.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.5, 0.4],
                    },
                    {
                        "titre": "Haut en dentelle fine",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.5, 0.4, 0.9, 0.6, 0.1, 0.0, 0.0, 0.0, 0.3, 0.4],
                    },
                    {
                        "titre": "Bustier élégant en soie",
                        "style": "Chic",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.2, 0.1, 0.9, 0.7, 0.0, 0.0, 0.0, 0.0, 0.3, 0.3],
                    },
                    {
                        "titre": "Pyjama en satin soyeux",
                        "style": "Loungewear",
                        "saisons": "Toutes",
                        "type": "Ensemble",
                        "activites": [0.2, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.2, 0.5],
                    },
                    {
                        "titre": "Pantalon de jogging en molleton",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.8, 0.0, 0.1, 0.0, 1.0, 0.5, 0.3, 0.2, 0.1, 0.7],
                    },
                    {
                        "titre": "Peignoir de bain en éponge épais",
                        "style": "Loungewear",
                        "saisons": "Hiver/Automne",
                        "type": "Veste",
                        "activites": [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.1, 0.2],
                    },
                    {
                        "titre": "Chaussettes épaisses en laine",
                        "style": "Loungewear",
                        "saisons": "Hiver",
                        "type": "Accessoire",
                        "activites": [0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.2, 0.6, 0.0, 0.4],
                    },
                    {
                        "titre": "Chaussons fourrés peau de mouton",
                        "style": "Loungewear",
                        "saisons": "Hiver",
                        "type": "Chaussures",
                        "activites": [0.1, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.3, 0.0, 0.1],
                    },
                    {
                        "titre": "Legging de détente en coton souple",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.8, 0.1, 0.1, 0.0, 1.0, 0.4, 0.2, 0.1, 0.3, 0.7],
                    },
                    {
                        "titre": "Débardeur côtelé confortable",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Haut",
                        "activites": [0.8, 0.0, 0.2, 0.0, 0.9, 0.3, 0.2, 0.0, 0.8, 0.5],
                    },
                    {
                        "titre": "Short de nuit en coton léger",
                        "style": "Loungewear",
                        "saisons": "Été",
                        "type": "Bas",
                        "activites": [0.3, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.7, 0.3],
                    },
                    {
                        "titre": "Kimono fluide imprimé",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Veste",
                        "activites": [0.7, 0.0, 0.4, 0.0, 0.9, 0.0, 0.0, 0.0, 0.8, 0.6],
                    },
                    {
                        "titre": "Brassière sans coutures confort",
                        "style": "Loungewear",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.6, 0.1, 0.1, 0.0, 1.0, 0.5, 0.2, 0.1, 0.4, 0.6],
                    },
                    {
                        "titre": "Legging de compression technique",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.5, 0.0, 0.0, 0.0, 0.6, 1.0, 0.5, 0.3, 0.2, 0.5],
                    },
                    {
                        "titre": "Brassière de sport maintien supérieur",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.3, 0.0, 0.0, 0.0, 0.5, 1.0, 0.4, 0.2, 0.3, 0.4],
                    },
                    {
                        "titre": "Maillot de football respirant",
                        "style": "Sport",
                        "saisons": "Été/Printemps",
                        "type": "Haut",
                        "activites": [0.6, 0.0, 0.1, 0.0, 0.4, 1.0, 0.3, 0.0, 0.5, 0.4],
                    },
                    {
                        "titre": "Short de running fendu",
                        "style": "Sport",
                        "saisons": "Été",
                        "type": "Bas",
                        "activites": [0.2, 0.0, 0.0, 0.0, 0.3, 1.0, 0.4, 0.0, 0.7, 0.3],
                    },
                    {
                        "titre": "T-shirt de sport anti-transpiration",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Haut",
                        "activites": [0.5, 0.0, 0.0, 0.0, 0.5, 1.0, 0.6, 0.2, 0.5, 0.5],
                    },
                    {
                        "titre": "Chaussettes de course anti-ampoules",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.4, 0.0, 0.0, 0.0, 0.3, 1.0, 0.7, 0.3, 0.3, 0.5],
                    },
                    {
                        "titre": "Coupe-vent de course ultra-léger",
                        "style": "Sport",
                        "saisons": "Printemps/Automne",
                        "type": "Veste",
                        "activites": [0.5, 0.0, 0.0, 0.0, 0.1, 1.0, 0.7, 0.3, 0.1, 0.7],
                    },
                    {
                        "titre": "Survêtement de sport zippé",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Ensemble",
                        "activites": [0.7, 0.0, 0.1, 0.0, 0.7, 1.0, 0.4, 0.2, 0.1, 0.7],
                    },
                    {
                        "titre": "Casquette technique perforée",
                        "style": "Sport",
                        "saisons": "Été",
                        "type": "Accessoire",
                        "activites": [0.5, 0.0, 0.0, 0.0, 0.1, 1.0, 0.7, 0.1, 0.8, 0.5],
                    },
                    {
                        "titre": "Gants de fitness musculation",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Accessoire",
                        "activites": [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.2, 0.0, 0.0, 0.1],
                    },
                    {
                        "titre": "Pantalon de randonnée convertible",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.4, 0.0, 0.0, 0.0, 0.2, 0.4, 1.0, 0.5, 0.4, 0.7],
                    },
                    {
                        "titre": "Polaire technique demi-zip",
                        "style": "Sport",
                        "saisons": "Hiver/Automne",
                        "type": "Haut",
                        "activites": [0.6, 0.1, 0.1, 0.0, 0.7, 0.4, 1.0, 0.8, 0.0, 0.7],
                    },
                    {
                        "titre": "Chaussures de trekking Gore-Tex",
                        "style": "Sport",
                        "saisons": "Toutes",
                        "type": "Chaussures",
                        "activites": [0.3, 0.0, 0.0, 0.0, 0.1, 0.5, 1.0, 0.7, 0.1, 0.6],
                    },
                    {
                        "titre": "Veste de ski imperméable",
                        "style": "Sport",
                        "saisons": "Hiver",
                        "type": "Veste",
                        "activites": [0.3, 0.0, 0.1, 0.0, 0.1, 0.3, 0.7, 1.0, 0.0, 0.6],
                    },
                    {
                        "titre": "Pantalon de ski doublé thermique",
                        "style": "Sport",
                        "saisons": "Hiver",
                        "type": "Bas",
                        "activites": [0.1, 0.0, 0.0, 0.0, 0.1, 0.2, 0.5, 1.0, 0.0, 0.4],
                    },
                    {
                        "titre": "Bonnet en laine doublé polaire",
                        "style": "Casual",
                        "saisons": "Hiver",
                        "type": "Accessoire",
                        "activites": [0.8, 0.1, 0.3, 0.0, 0.4, 0.3, 0.7, 1.0, 0.0, 0.6],
                    },
                    {
                        "titre": "Gants de ski renforcés",
                        "style": "Sport",
                        "saisons": "Hiver",
                        "type": "Accessoire",
                        "activites": [0.1, 0.0, 0.0, 0.0, 0.0, 0.2, 0.5, 1.0, 0.0, 0.3],
                    },
                    {
                        "titre": "Haut thermique laine mérinos",
                        "style": "Sport",
                        "saisons": "Hiver",
                        "type": "Haut",
                        "activites": [0.4, 0.1, 0.0, 0.0, 0.7, 0.5, 0.9, 1.0, 0.0, 0.6],
                    },
                    {
                        "titre": "Collant thermique mérinos",
                        "style": "Sport",
                        "saisons": "Hiver",
                        "type": "Bas",
                        "activites": [0.2, 0.0, 0.0, 0.0, 0.7, 0.5, 0.9, 1.0, 0.0, 0.5],
                    },
                    {
                        "titre": "Chaussettes de ski épaisses",
                        "style": "Sport",
                        "saisons": "Hiver",
                        "type": "Accessoire",
                        "activites": [0.3, 0.0, 0.0, 0.0, 0.5, 0.3, 0.7, 1.0, 0.0, 0.4],
                    },
                    {
                        "titre": "Maillot de bain deux pièces floral",
                        "style": "Sport",
                        "saisons": "Été",
                        "type": "Haut",
                        "activites": [0.3, 0.0, 0.2, 0.0, 0.2, 0.4, 0.1, 0.0, 1.0, 0.4],
                    },
                    {
                        "titre": "Short de bain séchage rapide",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Bas",
                        "activites": [0.6, 0.0, 0.3, 0.0, 0.4, 0.5, 0.2, 0.0, 1.0, 0.5],
                    },
                    {
                        "titre": "Robe de plage en crochet",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Robe",
                        "activites": [0.7, 0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.5],
                    },
                    {
                        "titre": "Chapeau de paille grand bord",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Accessoire",
                        "activites": [0.6, 0.0, 0.4, 0.1, 0.1, 0.0, 0.1, 0.0, 1.0, 0.6],
                    },
                    {
                        "titre": "Lunettes de soleil polarisées",
                        "style": "Casual",
                        "saisons": "Été/Printemps",
                        "type": "Accessoire",
                        "activites": [0.9, 0.4, 0.6, 0.2, 0.1, 0.5, 0.7, 0.5, 1.0, 0.8],
                    },
                    {
                        "titre": "Claquettes de plage légères",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Chaussures",
                        "activites": [0.8, 0.0, 0.3, 0.0, 0.7, 0.1, 0.1, 0.0, 1.0, 0.6],
                    },
                    {
                        "titre": "T-shirt anti-UV à manches courtes",
                        "style": "Sport",
                        "saisons": "Été",
                        "type": "Haut",
                        "activites": [0.4, 0.0, 0.0, 0.0, 0.2, 0.6, 0.4, 0.0, 1.0, 0.5],
                    },
                    {
                        "titre": "Robe longue bohème fleurie",
                        "style": "Casual",
                        "saisons": "Été",
                        "type": "Robe",
                        "activites": [0.9, 0.2, 0.7, 0.2, 0.5, 0.0, 0.1, 0.0, 0.9, 0.7],
                    },
                    {
                        "titre": "Pantalon de voyage anti-froissage",
                        "style": "Casual",
                        "saisons": "Toutes",
                        "type": "Bas",
                        "activites": [0.8, 0.6, 0.5, 0.1, 0.6, 0.1, 0.3, 0.1, 0.5, 1.0],
                    },
                    {
                        "titre": "Veste saharienne multi-poches",
                        "style": "Casual",
                        "saisons": "Printemps/Automne",
                        "type": "Veste",
                        "activites": [0.8, 0.4, 0.4, 0.0, 0.2, 0.1, 0.6, 0.0, 0.4, 1.0],
                    },
                ]

                log(
                    f"Insertion de {len(catalogue)} vêtements dans la base...",
                    "PROGRESS",
                )
                for item in catalogue:
                    cur.execute(
                        "INSERT INTO vetements (titre, style, saisons, type, activites) VALUES (%s, %s, %s, %s, %s)",
                        (
                            item["titre"],
                            item["style"],
                            item["saisons"],
                            item["type"],
                            item[
                                "activites"
                            ],  # Plus besoin de np.array(), pgvector digère les listes Python direct
                        ),
                    )

                # Créer un index HNSW pour la colonne profil
                log(
                    "Création de l'index HNSW sur les profils d'activités...",
                    "PROGRESS",
                )
                cur.execute("""
                    CREATE INDEX ON vetements
                    USING hnsw (activites vector_cosine_ops)
                    WITH (m = 8, ef_construction = 40);
                """)

                log(
                    f"{len(catalogue)} vêtements insérés et indexés avec succès !",
                    "SUCCESS",
                )

    except OperationalError as e:
        log(f"Erreur de connexion à la base de données :\n{e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"Une erreur inattendue est survenue :\n{e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
