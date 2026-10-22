"""Synthèses de mesures de tri, limitées à des protocoles comparables."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from numbers import Real
from typing import Any


CRITERES = (
    ("Comparaisons", "comparaisons"),
    ("Opérations", "opérations"),
    ("Autres opérations", "autres opérations"),
    ("Total des compteurs", "total des compteurs"),
    ("Temps médian (ms)", "temps médian"),
)
_CONTEXTE = ("Distribution", "Taille", "Graine", "Répétitions")


def _valeur_numerique(valeur: Any) -> bool:
    return (
        isinstance(valeur, Real)
        and not isinstance(valeur, bool)
        and math.isfinite(valeur)
    )


def _contexte(ligne: Mapping[str, Any]) -> tuple[Any, ...]:
    distribution = ligne.get("Distribution", ligne.get("Type de données"))
    taille = ligne.get("Taille")
    if distribution is None or taille is None:
        raise ValueError("Chaque mesure doit préciser sa distribution et sa taille.")
    return (distribution, taille, ligne.get("Graine"), ligne.get("Répétitions"))


def _analyser_critere(
    lignes: list[Mapping[str, Any]], cle: str, libelle: str
) -> dict[str, Any] | None:
    if not any(cle in ligne for ligne in lignes):
        return {
            "cle": cle,
            "libelle": libelle,
            "disponible": False,
            "raison": "Cette mesure n'a pas été collectée dans ce protocole.",
        }

    disponibles = [
        (ligne["Algorithme"], ligne[cle])
        for ligne in lignes
        if cle in ligne and _valeur_numerique(ligne[cle])
    ]
    if not disponibles:
        return {
            "cle": cle,
            "libelle": libelle,
            "disponible": False,
            "raison": "Aucune valeur numérique n'est disponible.",
        }
    if len(disponibles) < 2:
        return {
            "cle": cle,
            "libelle": libelle,
            "disponible": False,
            "raison": "Une seule valeur comparable est disponible ; aucun minimum ne peut être départagé.",
            "nombre_disponible": len(disponibles),
            "nombre_total": len(lignes),
        }

    minimum = min(valeur for _, valeur in disponibles)
    gagnants = [nom for nom, valeur in disponibles if valeur == minimum]
    details = []
    for nom, valeur in disponibles:
        ecart = valeur - minimum
        details.append({
            "algorithme": nom,
            "valeur": valeur,
            "ecart_absolu": ecart,
            "ecart_pourcent": (ecart / minimum * 100) if minimum != 0 else None,
        })

    return {
        "cle": cle,
        "libelle": libelle,
        "disponible": True,
        "minimum": minimum,
        "gagnants": gagnants,
        "egalite": len(gagnants) > 1,
        "details": details,
        "nombre_disponible": len(disponibles),
        "nombre_total": len(lignes),
    }


def analyser_mesures(resultats: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Analyse séparément chaque taille et distribution, sans mélanger les protocoles."""
    groupes: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for ligne in resultats:
        if "Algorithme" not in ligne:
            raise ValueError("Chaque mesure doit nommer son algorithme.")
        groupes[_contexte(ligne)].append(ligne)

    analyses = []
    for contexte, lignes in groupes.items():
        if len({ligne["Algorithme"] for ligne in lignes}) != len(lignes):
            raise ValueError("Un algorithme ne peut apparaître qu'une fois par protocole.")
        criteres = {
            cle: resultat
            for cle, libelle in CRITERES
            if (resultat := _analyser_critere(lignes, cle, libelle)) is not None
        }
        analyses.append({
            "distribution": contexte[0],
            "taille": contexte[1],
            "graine": contexte[2],
            "repetitions": contexte[3],
            "criteres": criteres,
        })
    return analyses


def analyser_differences_distributions(
    resultats: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Compare les mêmes algorithmes et tailles entre distributions mesurées."""
    groupes: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for ligne in resultats:
        if "Algorithme" not in ligne:
            raise ValueError("Chaque mesure doit nommer son algorithme.")
        distribution, taille, graine, repetitions = _contexte(ligne)
        groupes[(ligne["Algorithme"], taille, graine, repetitions)].append(ligne)

    differences = []
    for (algorithme, taille, graine, repetitions), lignes in groupes.items():
        if len(lignes) < 2:
            continue
        distributions = [
            ligne.get("Distribution", ligne.get("Type de données"))
            for ligne in lignes
        ]
        criteres = {
            cle: resultat
            for cle, libelle in CRITERES
            if (resultat := _analyser_critere(
                [dict(ligne, Algorithme=distribution) for ligne, distribution in zip(lignes, distributions)],
                cle,
                libelle,
            )) is not None
        }
        differences.append({
            "algorithme": algorithme,
            "taille": taille,
            "graine": graine,
            "repetitions": repetitions,
            "criteres": criteres,
        })
    return differences