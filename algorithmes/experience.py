"""Outils de préparation et de mesure des expériences de tri."""

from __future__ import annotations

import random
import statistics
import time
from collections.abc import Callable, Mapping

from .tri import ALGORITHMES, calculer_statistiques


TYPES_DONNEES = (
    "Aléatoires",
    "Déjà triées",
    "Triées en ordre inverse",
    "Presque triées",
)
TAILLE_MAX_EXPERIENCE = 500
REPETITIONS_MAX_EXPERIENCE = 9


def creer_tailles_experience(taille_initiale: int, taille_max: int) -> list[int]:
    """Construit les tailles n, 2n, 4n... sans dépasser la limite autorisée."""
    if (
        not isinstance(taille_initiale, int)
        or isinstance(taille_initiale, bool)
        or not isinstance(taille_max, int)
        or isinstance(taille_max, bool)
    ):
        raise ValueError("Les tailles doivent être des nombres entiers.")
    if taille_initiale < 1:
        raise ValueError("La taille initiale doit être positive.")
    if taille_max < taille_initiale:
        raise ValueError("La taille maximale doit couvrir la taille initiale.")
    if taille_max > TAILLE_MAX_EXPERIENCE:
        raise ValueError(
            f"La taille maximale est limitée à {TAILLE_MAX_EXPERIENCE} éléments."
        )

    tailles = []
    taille = taille_initiale
    while taille <= taille_max:
        tailles.append(taille)
        taille *= 2
    return tailles


def calculer_facteur_evolution(
    valeur_precedente: int, valeur_actuelle: int
) -> float | None:
    """Compare deux compteurs; aucun facteur n'est défini si le premier vaut zéro."""
    if valeur_precedente < 0 or valeur_actuelle < 0:
        raise ValueError("Les compteurs ne peuvent pas être négatifs.")
    if valeur_precedente == 0:
        return None
    return valeur_actuelle / valeur_precedente


def mesurer_evolution(
    noms_algorithmes: list[str],
    type_donnees: str,
    taille_initiale: int,
    taille_max: int,
    graine: int = 42,
    repetitions: int = 5,
    fonctions_tri: Mapping[str, Callable[[list[int]], object]] | None = None,
) -> list[dict[str, int | float | str | bool | None]]:
    """Mesure les compteurs et, si fourni, le temps sur une entrée commune."""
    tailles = creer_tailles_experience(taille_initiale, taille_max)
    if not noms_algorithmes:
        raise ValueError("Sélectionne au moins un algorithme.")
    if len(noms_algorithmes) > len(ALGORITHMES):
        raise ValueError("Le nombre d'algorithmes sélectionnés dépasse la limite autorisée.")
    if len(set(noms_algorithmes)) != len(noms_algorithmes):
        raise ValueError("Un algorithme ne peut être sélectionné qu'une fois.")
    inconnus = set(noms_algorithmes) - set(ALGORITHMES)
    if inconnus:
        raise ValueError(f"Algorithme inconnu : {', '.join(sorted(inconnus))}")
    if type_donnees not in TYPES_DONNEES:
        raise ValueError(f"Type de données inconnu : {type_donnees}")
    if (
        not isinstance(repetitions, int)
        or isinstance(repetitions, bool)
        or not 1 <= repetitions <= REPETITIONS_MAX_EXPERIENCE
    ):
        raise ValueError(
            f"Le nombre de répétitions doit être compris entre 1 et "
            f"{REPETITIONS_MAX_EXPERIENCE}."
        )
    if fonctions_tri is not None:
        manquants = set(noms_algorithmes) - set(fonctions_tri)
        if manquants:
            raise ValueError(f"Fonction de tri manquante : {', '.join(sorted(manquants))}")
        invalides = [nom for nom in noms_algorithmes if not callable(fonctions_tri[nom])]
        if invalides:
            raise ValueError(f"Fonction de tri non appelable : {', '.join(invalides)}")

    donnees_par_taille = {
        taille: generer_donnees(type_donnees, taille, graine)
        for taille in tailles
    }
    resultats = []

    for nom in noms_algorithmes:
        total_precedent = None
        for taille in tailles:
            entree = donnees_par_taille[taille]
            statistiques = calculer_statistiques(nom, entree)
            resultat_correct = statistiques["liste"] == sorted(entree)
            if not resultat_correct:
                raise RuntimeError(f"{nom} n'a pas correctement trié le tableau.")

            autres_operations = statistiques["operations"]
            total_compteurs = statistiques["comparaisons"] + autres_operations
            resultats.append({
                "Taille": taille,
                "Distribution": type_donnees,
                "Graine": graine,
                "Répétitions": repetitions,
                "Algorithme": nom,
                "Comparaisons": statistiques["comparaisons"],
                "Échanges": statistiques["echanges"],
                "Déplacements": statistiques["deplacements"],
                "Autres opérations": autres_operations,
                "Total des compteurs": total_compteurs,
                "Facteur d'évolution": (
                    calculer_facteur_evolution(total_precedent, total_compteurs)
                    if total_precedent is not None
                    else None
                ),
                "Résultat correct": resultat_correct,
            })
            if fonctions_tri is not None:
                resultats[-1]["Temps médian (ms)"] = mesurer_tri(
                    fonctions_tri[nom], entree, repetitions=repetitions
                )
            total_precedent = total_compteurs
    return resultats


def generer_donnees(type_donnees: str, taille: int, graine: int = 42) -> list[int]:
    """Construit un tableau déterministe pour le type et la graine choisis."""
    if not isinstance(taille, int) or isinstance(taille, bool) or taille < 0:
        raise ValueError("La taille doit être positive ou nulle.")
    if not isinstance(graine, int) or isinstance(graine, bool):
        raise ValueError("La graine doit être un nombre entier.")

    generateur = random.Random(graine)
    if type_donnees == "Aléatoires":
        return [generateur.randint(0, 1000) for _ in range(taille)]
    if type_donnees == "Déjà triées":
        return list(range(taille))
    if type_donnees == "Triées en ordre inverse":
        return list(range(taille, 0, -1))
    if type_donnees == "Presque triées":
        nombres = list(range(taille))
        for _ in range(taille // 20):
            premier, second = generateur.sample(range(taille), 2)
            nombres[premier], nombres[second] = nombres[second], nombres[premier]
        return nombres
    raise ValueError(f"Type de données inconnu : {type_donnees}")


def mesurer_tri(
    fonction: Callable[[list[int]], object],
    nombres: list[int],
    repetitions: int = 5,
) -> float:
    """Renvoie la médiane en ms, hors copie du tableau et hors visualisation."""
    if (
        not isinstance(repetitions, int)
        or isinstance(repetitions, bool)
        or not 1 <= repetitions <= REPETITIONS_MAX_EXPERIENCE
    ):
        raise ValueError(
            f"Le nombre de répétitions doit être compris entre 1 et "
            f"{REPETITIONS_MAX_EXPERIENCE}."
        )

    durees = []
    resultat_attendu = sorted(nombres)
    for _ in range(repetitions):
        liste = nombres.copy()
        debut = time.perf_counter()
        fonction(liste)
        durees.append((time.perf_counter() - debut) * 1000)
        if liste != resultat_attendu:
            raise RuntimeError("Un algorithme n'a pas correctement trié le tableau.")
    return statistics.median(durees)