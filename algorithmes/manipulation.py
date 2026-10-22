"""Règles du mode où l'apprenant manipule réellement les tableaux."""

from __future__ import annotations

import random
import uuid
from typing import Any


ALGORITHMES_MANIPULATION = ("Tri par insertion", "Tri par sélection")
DIFFICULTES_MANIPULATION = ("Facile", "Intermédiaire", "Difficile")
INTERVALLES_TAILLE = {
    "Facile": (4, 6),
    "Intermédiaire": (7, 9),
    "Difficile": (10, 12),
}
INDICES_PAR_DIFFICULTE = {"Facile": 3, "Intermédiaire": 2, "Difficile": 1}
TYPES_TABLEAU = ("Aléatoire", "Presque trié", "Ordre inverse")


def creer_partie(
    algorithme: str = "Tri par insertion",
    difficulte: str = "Facile",
    taille: int | None = None,
    type_tableau: str = "Aléatoire",
    seed: int | None = None,
    nombres: list[int] | None = None,
) -> dict[str, Any]:
    """Crée une partie indépendante de Streamlit, reproductible avec une graine."""
    if algorithme not in ALGORITHMES_MANIPULATION:
        raise ValueError(f"Algorithme non pris en charge : {algorithme}")
    if difficulte not in DIFFICULTES_MANIPULATION:
        raise ValueError(f"Difficulté inconnue : {difficulte}")
    minimum, maximum = INTERVALLES_TAILLE[difficulte]
    taille = taille if taille is not None else minimum
    if not isinstance(taille, int) or isinstance(taille, bool) or not 1 <= taille <= maximum:
        raise ValueError(f"La taille doit être comprise entre 1 et {maximum}.")
    if nombres is None and taille < minimum:
        raise ValueError(f"La taille doit être comprise entre {minimum} et {maximum}.")
    if type_tableau not in TYPES_TABLEAU:
        raise ValueError(f"Type de tableau inconnu : {type_tableau}")

    if nombres is None:
        generateur = random.Random(seed)
        if type_tableau == "Aléatoire":
            entree = [generateur.randint(1, 30) for _ in range(taille)]
        elif type_tableau == "Presque trié":
            entree = list(range(1, taille + 1))
            for _ in range(max(1, taille // 5)):
                gauche, droite = generateur.sample(range(taille), 2)
                entree[gauche], entree[droite] = entree[droite], entree[gauche]
        else:
            entree = list(range(taille, 0, -1))
    else:
        entree = list(nombres)
        if len(entree) != taille or any(not isinstance(valeur, int) for valeur in entree):
            raise ValueError("Le tableau doit contenir exactement la taille choisie en entiers.")

    selection = algorithme == "Tri par sélection"
    partie = {
        "id": uuid.uuid4().hex,
        "algorithme": algorithme,
        "difficulte": difficulte,
        "taille": taille,
        "type_tableau": type_tableau,
        "entree": entree.copy(),
        "tableau": entree.copy(),
        "phase": "comparer" if selection and taille > 1 else "choisir_minimum" if selection else "choisir_cle",
        "index": 0 if selection else 1,
        "curseur": 1 if selection else None,
        "minimum": 0 if selection else None,
        "compares": [],
        "cle": None,
        "etapes": 0,
        "erreurs": 0,
        "erreurs_etape": 0,
        "indices_utilises": 0,
        "journal": [],
        "completee": False,
        "reussite": False,
        "feedback": None,
        "indice_affiche": None,
    }
    if selection and taille == 1:
        partie["curseur"] = 1
    if taille == 1:
        partie["phase"] = "terminee"
        partie["completee"] = True
        partie["reussite"] = True
    return partie


def _erreur(partie: dict[str, Any], texte: str) -> str:
    partie["erreurs"] += 1
    partie["erreurs_etape"] += 1
    if partie["erreurs_etape"] == 3:
        texte += " Indice : reprends la frontière entre la zone traitée et celle à examiner."
    elif partie["erreurs_etape"] >= 5:
        texte += " Vérifie les indices affichés et respecte l'ordre des opérations du tri."
    partie["feedback"] = {"correcte": False, "texte": texte}
    return "incorrecte"


def _valider_transition(
    partie: dict[str, Any], action: str, reponse: dict[str, Any]
) -> None:
    partie["etapes"] += 1
    partie["erreurs_etape"] = 0
    partie["indice_affiche"] = None
    partie["journal"].append({"action": action, "reponse": reponse.copy()})


def _terminer_selection_si_necessaire(partie: dict[str, Any]) -> None:
    if partie["index"] >= len(partie["tableau"]) - 1:
        tableau = partie["tableau"]
        partie["completee"] = True
        partie["reussite"] = (
            all(valeur is not None for valeur in tableau)
            and tableau == sorted(partie["entree"])
            and sorted(tableau) == sorted(partie["entree"])
        )
        partie["phase"] = "terminee"
        partie["feedback"] = {
            "correcte": partie["reussite"],
            "texte": "Le tableau est trié et chaque minimum a été placé par sélection." if partie["reussite"] else "La démarche est terminée, mais le résultat ne respecte pas le tri attendu.",
        }


def valider_action(
    partie: dict[str, Any], action: str, reponse: dict[str, Any]
) -> str:
    """Valide une action de l'algorithme courant; une erreur ne mute pas le tableau."""
    if partie["completee"]:
        return "terminee"

    tableau = partie["tableau"]
    taille = len(tableau)
    phase = partie["phase"]
    insertion = partie["algorithme"] == "Tri par insertion"

    if insertion:
        if phase == "choisir_cle" and action == "choisir_cle":
            if reponse.get("indice") != partie["index"]:
                return _erreur(partie, "La clé est le prochain élément après le préfixe déjà trié.")
            partie["cle"] = tableau[partie["index"]]
            tableau[partie["index"]] = None
            partie["curseur"] = partie["index"] - 1
            partie["phase"] = "comparer"
            _valider_transition(partie, action, reponse)
            partie["feedback"] = {"correcte": True, "texte": f"Clé {partie['cle']} isolée. Compare-la à partir de la droite du préfixe trié."}
            return "correcte"

        if phase == "comparer" and action == "comparer":
            curseur = partie["curseur"]
            indice = reponse.get("indice")
            if curseur is None or indice != curseur:
                return _erreur(partie, "La comparaison doit porter sur l'élément immédiatement à gauche de la clé.")
            valeur = tableau[curseur]
            if valeur is None:
                return _erreur(partie, "Cette case est le trou laissé par la clé; compare la case précédente.")
            doit_decaler = valeur > partie["cle"]
            partie["phase"] = "deplacer" if doit_decaler else "inserer"
            _valider_transition(partie, action, reponse)
            partie["feedback"] = {
                "correcte": True,
                "texte": (
                    f"{valeur} est supérieur à la clé : il faut le décaler d'une case vers la droite."
                    if doit_decaler else f"{valeur} est inférieur ou égal à la clé : insère-la juste après cette valeur."
                ),
            }
            return "correcte"

        if phase == "deplacer" and action == "deplacer":
            source, destination = partie["curseur"], partie["curseur"] + 1
            if (reponse.get("source"), reponse.get("destination")) != (source, destination):
                return _erreur(partie, "Un seul élément se déplace à la fois, vers la case immédiatement à sa droite.")
            valeur = tableau[source]
            if valeur is None or not 0 <= destination < taille:
                return _erreur(partie, "Le déplacement demandé sort du tableau ou ne part pas d'une valeur disponible.")
            tableau[destination] = valeur
            tableau[source] = None
            partie["curseur"] -= 1
            partie["phase"] = "comparer" if partie["curseur"] >= 0 else "inserer"
            _valider_transition(partie, action, reponse)
            partie["feedback"] = {"correcte": True, "texte": f"{valeur} a été décalé d'une case. La clé reste conservée jusqu'à son insertion."}
            return "correcte"

        if phase == "inserer" and action == "inserer":
            destination = partie["curseur"] + 1
            if reponse.get("destination") != destination:
                return _erreur(partie, "Insère la clé à la première position qui respecte l'ordre du préfixe.")
            if not 0 <= destination < taille or tableau[destination] is not None:
                return _erreur(partie, "La destination doit être la case libre créée par les décalages.")
            cle = partie["cle"]
            tableau[destination] = cle
            partie["cle"] = None
            _valider_transition(partie, action, reponse)
            partie["index"] += 1
            if partie["index"] >= taille:
                partie["completee"] = True
                partie["reussite"] = tableau == sorted(partie["entree"])
                partie["phase"] = "terminee"
                texte = "Toutes les clés ont été insérées dans le préfixe trié."
            else:
                partie["phase"] = "choisir_cle"
                texte = f"La clé {cle} est insérée. Le préfixe trié contient maintenant {partie['index']} élément(s)."
            partie["feedback"] = {"correcte": True, "texte": texte}
            return "correcte"

        return _erreur(partie, "Cette action ne correspond pas à l'étape actuelle du tri par insertion.")

    if phase == "comparer" and action == "comparer":
        indice = reponse.get("indice")
        if indice != partie["curseur"] or not isinstance(indice, int) or not 0 <= indice < taille:
            return _erreur(partie, "Examine les candidats dans l'ordre, de gauche à droite, sans sauter d'indice.")
        if tableau[indice] < tableau[partie["minimum"]]:
            partie["minimum"] = indice
        partie["compares"].append(indice)
        partie["curseur"] += 1
        if partie["curseur"] >= taille:
            partie["phase"] = "choisir_minimum"
        _valider_transition(partie, action, reponse)
        partie["feedback"] = {"correcte": True, "texte": "Valeur examinée. Garde en mémoire le plus petit élément rencontré."}
        return "correcte"

    if phase == "choisir_minimum" and action == "choisir_minimum":
        indice_minimum = partie["minimum"]
        if reponse.get("indice") != indice_minimum:
            return _erreur(partie, "Le minimum doit être choisi parmi toute la zone examinée, pas seulement la dernière valeur.")
        partie["phase"] = "echanger" if indice_minimum != partie["index"] else "confirmer"
        _valider_transition(partie, action, reponse)
        partie["feedback"] = {"correcte": True, "texte": f"Le minimum de la zone non triée est en position {indice_minimum}."}
        return "correcte"

    if phase == "echanger" and action == "echanger":
        debut, minimum = partie["index"], partie["minimum"]
        if (reponse.get("source"), reponse.get("destination")) != (debut, minimum):
            return _erreur(partie, "Échange le minimum avec le premier élément de la zone non triée.")
        tableau[debut], tableau[minimum] = tableau[minimum], tableau[debut]
        _valider_transition(partie, action, reponse)
        partie["feedback"] = {"correcte": True, "texte": f"Le minimum est placé en position {debut}; la zone triée s'agrandit d'une case."}
        partie["index"] += 1
        partie["minimum"] = partie["index"]
        partie["curseur"] = partie["index"] + 1
        partie["compares"] = []
        _terminer_selection_si_necessaire(partie)
        if not partie["completee"]:
            partie["phase"] = "comparer" if partie["curseur"] < taille else "choisir_minimum"
        return "correcte"

    if phase == "confirmer" and action == "confirmer":
        if partie["minimum"] != partie["index"]:
            return _erreur(partie, "Un échange est nécessaire, car le minimum n'est pas au début de la zone.")
        _valider_transition(partie, action, reponse)
        partie["feedback"] = {"correcte": True, "texte": f"La valeur en position {partie['index']} est déjà minimale : aucun échange n'est nécessaire."}
        partie["index"] += 1
        partie["minimum"] = partie["index"]
        partie["curseur"] = partie["index"] + 1
        partie["compares"] = []
        _terminer_selection_si_necessaire(partie)
        if not partie["completee"]:
            partie["phase"] = "comparer" if partie["curseur"] < taille else "choisir_minimum"
        return "correcte"

    return _erreur(partie, "Cette action ne correspond pas à l'étape actuelle du tri par sélection.")


def utiliser_indice(partie: dict[str, Any]) -> str | None:
    """Affiche un indice progressif, dans la limite prévue par la difficulté."""
    limite = INDICES_PAR_DIFFICULTE[partie["difficulte"]]
    if partie["completee"] or partie["indices_utilises"] >= limite:
        return None
    partie["indices_utilises"] += 1
    phase = partie["phase"]
    indices = {
        "choisir_cle": "Pour l'insertion, la clé est le premier élément qui n'appartient pas encore au préfixe trié.",
        "comparer": "Le parcours se fait depuis la frontière de la zone non triée; ne saute aucun élément.",
        "deplacer": "L'insertion décale une valeur trop grande d'une seule position vers la droite.",
        "inserer": "La clé rejoint la case libre, juste après les valeurs qui lui sont inférieures ou égales.",
        "choisir_minimum": "En sélection, compare les valeurs examinées à la valeur minimale mémorisée depuis le début du passage.",
        "echanger": "Le minimum trouvé rejoint le début de la zone non triée par un échange.",
        "confirmer": "Si le début de la zone est déjà le minimum, le tri par sélection n'effectue aucun échange.",
    }
    partie["indice_affiche"] = indices[phase]
    return partie["indice_affiche"]


def progression_partie(partie: dict[str, Any]) -> dict[str, int | bool]:
    total = len(partie["entree"])
    return {
        "terminees": min(partie["index"], total),
        "total": total,
        "erreurs": partie["erreurs"],
        "etapes": partie["etapes"],
        "reussite": partie["reussite"],
    }


def verifier_reussite(partie: dict[str, Any]) -> bool:
    """Rejoue le journal pour confirmer le résultat et la démarche complète."""
    if not partie.get("completee") or not partie.get("reussite"):
        return False
    try:
        replay = creer_partie(
            partie["algorithme"],
            partie["difficulte"],
            len(partie["entree"]),
            partie["type_tableau"],
            nombres=partie["entree"],
        )
        for transition in partie["journal"]:
            if valider_action(replay, transition["action"], transition["reponse"]) != "correcte":
                return False
    except (KeyError, TypeError, ValueError):
        return False
    return (
        replay["completee"]
        and replay["reussite"]
        and replay["tableau"] == partie.get("tableau")
        and replay["tableau"] == sorted(partie["entree"])
    )