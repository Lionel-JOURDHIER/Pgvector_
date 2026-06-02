import numpy as np


def distance_cosinus(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calcule la distance cosinus entre deux vecteurs.
    Formule : 1 - (a · b) / (|a| × |b|)

    Résultat :
    - 0.0 → vecteurs identiques (même direction)
    - 1.0 → vecteurs orthogonaux (perpendiculaires)
    - 2.0 → vecteurs opposés
    """
    # Produit scalaire
    dot = np.dot(a, b)
    # Normes
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    # Similarité cosinus (entre -1 et 1)
    similarite = dot / (norm_a * norm_b)
    # Distance cosinus (entre 0 et 2)
    return 1 - similarite


# Nos vecteurs [sucré, épicé, exotique]
mangue = np.array([0.9, 0.1, 0.95])
ananas = np.array([0.8, 0.08, 0.88])
piment = np.array([0.1, 0.95, 0.6])
vanille = np.array([0.95, 0.02, 0.3])

print("Distances cosinus calculées manuellement :")
print(
    f"  mangue  ↔ ananas  : {distance_cosinus(mangue, ananas):.4f}  (proches : tous deux sucrés/exotiques)"
)
print(
    f"  mangue  ↔ piment  : {distance_cosinus(mangue, piment):.4f}  (éloignés : sucré vs épicé)"
)
print(
    f"  mangue  ↔ vanille : {distance_cosinus(mangue, vanille):.4f}  (moyens : sucrés mais exotique différent)"
)
print(f"  piment  ↔ vanille : {distance_cosinus(piment, vanille):.4f}  (très éloignés)")

# Illustrer l'effet de la magnitude (la distance cosinus ne change pas)
mangue_x10 = mangue * 10
print(f"\n  mangue × 10 ↔ ananas : {distance_cosinus(mangue_x10, ananas):.4f}")
print("  → La distance cosinus est insensible à la magnitude !")

# En comparaison, la distance L2 change
print("\nDistance L2 (Euclidienne) pour comparaison :")
print(f"  mangue  ↔ ananas  : {np.linalg.norm(mangue - ananas):.4f}")
print(f"  mangue × 10 ↔ ananas : {np.linalg.norm(mangue_x10 - ananas):.4f}")
print("  → La distance L2 est sensible à la magnitude !")
