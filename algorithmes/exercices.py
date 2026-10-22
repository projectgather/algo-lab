"""Génération et correction déterministes des exercices AlgoLab."""

from __future__ import annotations

import random
import re
import uuid
from typing import Any

from algorithmes.tri import ALGORITHMES


DIFFICULTES = ("Débutant", "Intermédiaire", "Avancé")
TOUS_LES_ALGORITHMES = "Tous les algorithmes"
ALGORITHMES_DEBUTANT = tuple(ALGORITHMES)


def algorithmes_disponibles(difficulte: str) -> tuple[str, ...]:
    if difficulte == "Débutant":
        return ALGORITHMES_DEBUTANT
    if difficulte in ("Intermédiaire", "Avancé"):
        return tuple(ALGORITHMES)
    raise ValueError(f"Difficulté inconnue : {difficulte}")


def _format_evenement(etape: dict[str, Any]) -> str:
    action = etape["action"]
    details = etape["details"]
    indices = etape["indices"]
    valeurs = etape["valeurs"]
    if action == "comparaison" and valeurs is not None:
        return f"Comparer {valeurs[0]} et {valeurs[1]} (positions {indices[0]} et {indices[1]})"
    if action == "echange" and valeurs is not None:
        return f"Échanger les positions {indices[0]} et {indices[1]} ({valeurs[0]} et {valeurs[1]})"
    if action in ("placement", "ecriture", "insertion") and valeurs is not None:
        destination = details.get("destination")
        if destination is None and indices:
            destination = indices[0]
        return f"Placer {valeurs[0]} à la position {destination}"
    if action == "pivot":
        return f"Choisir {details['pivot_value']} en position {details['pivot_index']} comme pivot"
    if action == "division":
        zones = details.get("zones", ())
        if len(zones) == 2:
            return f"Diviser en [{zones[0][0]}..{zones[0][1]}] et [{zones[1][0]}..{zones[1][1]}]"
    if action == "reduction_tas":
        return f"Réduire le tas actif à {details['heap_size']} éléments"
    if action == "recursion":
        gauche, droite = details.get("zone_active", (0, -1))
        return f"Traiter récursivement [{gauche}..{droite}]"
    if action == "partition" and details.get("zones"):
        return f"Terminer la partition autour de {details['pivot_value']}"
    return f"{action.capitalize()} : {etape['explication']}"


def _answer_text(etape: dict[str, Any]) -> tuple[str, str] | None:
    action = etape["action"]
    indices = etape["indices"]
    valeurs = etape["valeurs"]
    details = etape["details"]
    if action == "comparaison" and valeurs is not None:
        return "valeurs", f"{valeurs[0]}, {valeurs[1]}"
    if action == "echange" and indices is not None and len(indices) == 2:
        return "indices", f"{indices[0]}, {indices[1]}"
    if action in ("placement", "ecriture", "insertion") and valeurs is not None:
        destination = details.get("destination")
        if destination is None and indices:
            destination = indices[0]
        return "valeur@position", f"{valeurs[0]}@{destination}"
    if action == "pivot":
        return "pivot", str(details["pivot_value"])
    if action == "reduction_tas":
        return "taille", str(details["heap_size"])
    return None


def _normaliser_reponse(reponse: str) -> str:
    return re.sub(r"\s+", "", str(reponse)).casefold()


def _question_prediction(
    nom: str,
    entree: list[int],
    historique: list[dict[str, Any]],
    difficulte: str,
    rng: random.Random,
) -> dict[str, Any]:
    choix_saisie = difficulte == "Avancé"
    candidats = [
        index
        for index, _ in enumerate(historique[:-1])
        if historique[index + 1]["action"] not in ("initialisation", "fin")
        and (not choix_saisie or _answer_text(historique[index + 1]) is not None)
    ]
    if not candidats:
        candidats = list(range(max(1, len(historique) - 1)))
    index_courant = rng.choice(candidats)
    index_suivant = index_courant + 1
    etape_suivante = historique[index_suivant]
    reponse = _answer_text(etape_suivante)

    if choix_saisie and reponse is not None:
        type_reponse, attendue = reponse
        formats = {
            "valeurs": "valeur1, valeur2",
            "indices": "indice1, indice2",
            "valeur@position": "valeur@position",
            "pivot": "valeur du pivot",
            "taille": "nombre entier",
        }
        question = {
            "format": "texte",
            "prompt": {
                "valeurs": "Quelles seront les deux valeurs comparées ?",
                "indices": "Quelles positions seront échangées ?",
                "valeur@position": "Quelle valeur sera placée et à quelle position ?",
                "pivot": "Quelle valeur sera choisie comme pivot ?",
                "taille": "Quelle sera la taille du tas actif après cette étape ?",
            }[type_reponse],
            "format_reponse": formats[type_reponse],
            "reponse_attendue": attendue,
            "acceptees": (_normaliser_reponse(attendue),),
        }
    else:
        attendue = _format_evenement(etape_suivante)
        alternatives = []
        for etape in historique[index_suivant + 1:]:
            option = _format_evenement(etape)
            if option != attendue and option not in alternatives:
                alternatives.append(option)
        alternatives.extend((
            "Terminer sans autre comparaison ni mutation",
            "Conserver toutes les valeurs à leur position actuelle",
            "Traiter un autre segment avant cette opération",
        ))
        choix = [attendue]
        for option in alternatives:
            if option not in choix:
                choix.append(option)
            if len(choix) == 4:
                break
        rng.shuffle(choix)
        question = {
            "format": "choix",
            "prompt": "Quelle opération précise l'algorithme va-t-il effectuer ensuite ?",
            "choix": choix,
            "reponse_attendue": attendue,
            "acceptees": (attendue,),
        }

    question.update({
        "type": "prediction",
        "nom_algorithme": nom,
        "entree": entree.copy(),
        "historique": historique,
        "index_courant": index_courant,
        "index_suivant": index_suivant,
        "indice": "Observe les indices orange et le pseudo-code actif; cherche les opérandes encore disponibles.",
        "explication": etape_suivante["explication"],
    })
    return question


def _question_etat(
    nom: str,
    entree: list[int],
    historique: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, Any] | None:
    mutations = [
        (index, etape)
        for index, etape in enumerate(historique)
        if etape["action"] in ("echange", "deplacement", "insertion", "ecriture")
        and etape["avant"] is not None
        and etape["apres"] != etape["avant"]
    ]
    etats = {}
    for etape in historique:
        for etat in (etape["liste"], etape["apres"]):
            if etat is not None:
                etats.setdefault(tuple(etat), etat.copy())

    if not mutations or len(etats) < 4:
        return None

    index_etape, etape = rng.choice(mutations)
    attendue = etape["apres"].copy()
    distracteurs = [etat.copy() for cle, etat in etats.items() if cle != tuple(attendue)]
    choix = [attendue, *rng.sample(distracteurs, 3)]
    rng.shuffle(choix)
    return {
        "type": "etat",
        "format": "choix",
        "prompt": (
            f"Après l'étape « {_format_evenement(etape)} », "
            "quel sera le tableau ?"
        ),
        "nom_algorithme": nom,
        "entree": entree.copy(),
        "historique": historique,
        "index_etape": index_etape,
        "avant": etape["avant"].copy(),
        "apres": attendue.copy(),
        "choix": choix,
        "reponse_attendue": attendue,
        "indice": "Suis la mutation indiquée et vérifie quelles positions changent réellement.",
        "explication": (
            f"{etape['explication']} Avant l'étape : {etape['avant']}. "
            f"Après l'étape : {attendue}."
        ),
    }


def _etiquette_ordre(etape: dict[str, Any]) -> str:
    return _format_evenement(etape)


def _question_ordre(
    nom: str,
    entree: list[int],
    historique: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, Any]:
    sequence = []
    indices_sequence = []
    for index, etape in enumerate(historique):
        if etape["action"] in ("initialisation", "fin", "base"):
            continue
        label = _etiquette_ordre(etape)
        if label not in sequence:
            sequence.append(label)
            indices_sequence.append(index)
    if len(sequence) < 3:
        return _question_prediction(nom, entree, historique, "Intermédiaire", rng)

    depart = rng.randrange(len(sequence) - 2)
    ordre_correct = sequence[depart:depart + 3]
    options = ordre_correct.copy()
    rng.shuffle(options)
    return {
        "type": "ordre",
        "format": "ordre",
        "prompt": "Remets ces trois événements dans l'ordre d'exécution.",
        "nom_algorithme": nom,
        "entree": entree.copy(),
        "historique": historique,
        "evenements": options,
        "ordre_correct": ordre_correct,
        "indices_evenements": indices_sequence[depart:depart + 3],
        "reponse_attendue": ordre_correct,
        "acceptees": (tuple(ordre_correct),),
        "indice": "Repère les dépendances : une opération peut nécessiter une comparaison, une division ou une extraction préalable.",
        "explication": "Ordre réel de ces événements dans l'historique produit par l'algorithme : " + " → ".join(ordre_correct),
    }


def _banque_comprehension(nom: str) -> dict[str, Any]:
    questions = {
        "Tri à bulles": (
            "Pourquoi le tri à bulles peut-il s'arrêter avant le dernier passage ?",
            "Parce qu'un passage sans échange prouve que toutes les paires voisines sont ordonnées.",
            "Parce que la première valeur est toujours le minimum.",
            "Parce que le tableau est divisé en deux.",
            "Parce qu'un pivot a été placé.",
            "Les échanges ne portent que sur des voisins; aucun échange pendant un passage signifie que la liste est déjà triée.",
        ),
        "Tri par sélection": (
            "Quelle propriété n'est pas garantie par cette implémentation du tri par sélection ?",
            "La stabilité : un échange global peut inverser l'ordre relatif de deux valeurs égales.",
            "La correction du résultat croissant.",
            "La terminaison sur une liste finie.",
            "La préservation des occurrences de chaque valeur.",
            "Le minimum trouvé peut être échangé à distance avec le début de la zone; cela peut déplacer une valeur égale avant une autre.",
        ),
        "Tri par insertion": (
            "Comment cette implémentation conserve-t-elle l'ordre des valeurs égales ?",
            "Elle ne décale que les valeurs strictement supérieures à la clé.",
            "Elle échange chaque paire égale.",
            "Elle choisit toujours le dernier élément comme pivot.",
            "Elle place les égalités dans un tas.",
            "La condition est `précédente > clé`; une valeur égale n'est donc pas déplacée devant la clé.",
        ),
        "Tri fusion": (
            "Pourquoi cette fusion est-elle stable ?",
            "En cas d'égalité, elle choisit d'abord la valeur de la moitié gauche.",
            "Elle inverse chaque sous-tableau avant la fusion.",
            "Elle choisit toujours le dernier élément comme pivot.",
            "Elle déplace toutes les valeurs égales à la fin.",
            "Le test `gauche <= droite` prend la valeur gauche en premier lors d'une égalité, préservant leur ordre initial.",
        ),
        "Tri rapide": (
            "Quelle valeur sert de pivot dans la partition actuelle ?",
            "La valeur au milieu de l'intervalle actif.",
            "Toujours la plus petite valeur.",
            "Toujours la dernière valeur.",
            "La moyenne des valeurs du tableau.",
            "Le moteur sélectionne `A[(gauche + droite) // 2]` puis sépare la zone en valeurs inférieures, égales et supérieures.",
        ),
        "Tri par tas": (
            "Que garantit la racine pendant la construction d'un max-heap valide ?",
            "Elle contient le maximum de la zone active du tas.",
            "Elle contient le minimum du tableau complet.",
            "Elle contient toujours la première valeur d'entrée.",
            "Elle est déjà placée dans le suffixe trié.",
            "Dans un max-heap, chaque parent est supérieur ou égal à ses enfants; le maximum de la zone active se trouve donc à la racine.",
        ),
    }
    prompt, correct, wrong_a, wrong_b, wrong_c, explanation = questions[nom]
    return {
        "type": "comprehension",
        "format": "choix",
        "prompt": prompt,
        "choix": [correct, wrong_a, wrong_b, wrong_c],
        "reponse_attendue": correct,
        "acceptees": (correct,),
        "explication": explanation,
        "indice": "Relie ta réponse aux comparaisons et aux affectations réellement utilisées par cet algorithme.",
    }


def _question_comprehension(
    nom: str,
    entree: list[int],
    historique: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, Any]:
    question = _banque_comprehension(nom)
    rng.shuffle(question["choix"])
    question.update({
        "nom_algorithme": nom,
        "entree": entree.copy(),
        "historique": historique,
    })
    return question


def creer_session(
    algorithme: str,
    difficulte: str,
    nombre_questions: int = 6,
    seed: int | None = None,
    nombres: list[int] | None = None,
) -> dict[str, Any]:
    if difficulte not in DIFFICULTES:
        raise ValueError(f"Difficulté inconnue : {difficulte}")
    disponibles = algorithmes_disponibles(difficulte)
    if algorithme != TOUS_LES_ALGORITHMES and algorithme not in disponibles:
        raise ValueError(f"Algorithme indisponible en mode {difficulte} : {algorithme}")
    if nombre_questions < 1:
        raise ValueError("Une session doit contenir au moins une question.")

    if seed is None:
        seed = random.SystemRandom().randrange(2**32)
    rng = random.Random(seed)
    if nombres is None:
        taille = {"Débutant": 5, "Intermédiaire": 8, "Avancé": 10}[difficulte]
        minimum, maximum = (0, 9) if difficulte == "Débutant" else (-9, 20)
        entree = [rng.randint(minimum, maximum) for _ in range(taille)]
    else:
        if not nombres or len(nombres) > 50:
            raise ValueError("La liste d'exercice doit contenir de 1 à 50 nombres.")
        entree = nombres.copy()
    algorithmes_session = (
        list(disponibles)
        if algorithme == TOUS_LES_ALGORITHMES
        else [algorithme]
    )
    historiques = {
        nom: ALGORITHMES[nom](entree.copy())
        for nom in algorithmes_session
    }

    types = {
        "Débutant": ("etat", "prediction_choix"),
        "Intermédiaire": ("prediction_choix", "ordre", "comprehension"),
        "Avancé": ("prediction_texte", "ordre", "comprehension"),
    }[difficulte]
    questions = []
    for index in range(nombre_questions):
        nom = algorithmes_session[index % len(algorithmes_session)]
        historique = historiques[nom]
        type_question = types[index % len(types)]
        if type_question == "etat":
            question = _question_etat(nom, entree, historique, rng)
            if question is None:
                question = _question_prediction(nom, entree, historique, "Intermédiaire", rng)
        elif type_question == "prediction_choix":
            question = _question_prediction(nom, entree, historique, "Intermédiaire", rng)
        elif type_question == "prediction_texte":
            question = _question_prediction(nom, entree, historique, "Avancé", rng)
        elif type_question == "ordre":
            question = _question_ordre(nom, entree, historique, rng)
        else:
            question = _question_comprehension(nom, entree, historique, rng)
        question.update({
            "id": index,
            "tentatives": 0,
            "derniere_reponse": None,
            "reponses": [],
            "resolue": False,
            "correcte": False,
            "points": 0,
            "indices_utilises": 0,
        })
        questions.append(question)

    session_id = uuid.uuid4().hex
    for index, question in enumerate(questions):
        question["progression_id"] = f"{session_id}:{index}"

    return {
        "id": session_id,
        "algorithme_choisi": algorithme,
        "difficulte": difficulte,
        "entree": entree,
        "questions": questions,
        "index_question": 0,
        "terminee": False,
        "seed": seed,
    }


def reponse_correcte(question: dict[str, Any], reponse: Any) -> bool:
    if question["format"] == "ordre":
        return tuple(reponse) == tuple(question["ordre_correct"])
    if question["format"] == "texte":
        return _normaliser_reponse(str(reponse)) in question["acceptees"]
    return reponse == question["reponse_attendue"]


def valider_reponse(question: dict[str, Any], reponse: Any) -> str:
    """Enregistre au plus une tentative identique et attribue les points une fois."""
    if question["resolue"]:
        return "resolue"
    if question["tentatives"] and reponse == question["derniere_reponse"]:
        return "doublon"

    question["tentatives"] += 1
    question["derniere_reponse"] = reponse
    question.setdefault("reponses", []).append(
        reponse.copy() if isinstance(reponse, list) else reponse
    )
    if reponse_correcte(question, reponse):
        question["resolue"] = True
        question["correcte"] = True
        question["points"] = 100 if question["tentatives"] == 1 else 50
        return "correcte"
    if question["tentatives"] >= 2:
        question["resolue"] = True
        question["correcte"] = False
        question["points"] = 0
        return "incorrecte_finale"
    return "nouvel_essai"


def utiliser_indice(question: dict[str, Any]) -> bool:
    if question["resolue"] or question["indices_utilises"]:
        return False
    question["indices_utilises"] = 1
    return True


def statistiques_session(session: dict[str, Any]) -> dict[str, int | float]:
    questions = session["questions"]
    terminees = [question for question in questions if question["resolue"]]
    reussies = [question for question in terminees if question["correcte"]]
    score = sum(question["points"] for question in terminees)
    return {
        "terminees": len(terminees),
        "reussies": len(reussies),
        "premier_essai": sum(question["correcte"] and question["tentatives"] == 1 for question in terminees),
        "indices": sum(question["indices_utilises"] for question in questions),
        "score": score,
        "pourcentage": round(100 * len(reussies) / len(terminees)) if terminees else 0,
    }