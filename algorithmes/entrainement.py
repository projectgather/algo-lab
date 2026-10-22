"""Sessions d'entraînement courtes fondées sur les tris AlgoLab."""

from __future__ import annotations

import random
import uuid
from typing import Any

from algorithmes.exercices import _question_etat
from algorithmes.tri import ALGORITHMES


DIFFICULTES_ENTRAINEMENT = ("Débutant", "Intermédiaire", "Avancé")
TAILLE_SESSION_ENTRAINEMENT = 6
_TAILLES_ENTREE = {"Débutant": 5, "Intermédiaire": 6, "Avancé": 8}
_CHOIX_ALGORITHMES = tuple(ALGORITHMES)
_SCENARIOS_ALGORITHME = (
    {
        "algorithme": "Tri fusion",
        "prompt": (
            "Tu dois trier 100 000 fiches, conserver l'ordre initial des fiches "
            "ayant la même clé et garantir O(n log n) dans le pire cas. "
            "La mémoire auxiliaire O(n) est disponible. Quel tri répond à ces contraintes ?"
        ),
        "explication": (
            "Le tri fusion est stable et sa complexité théorique est O(n log n) "
            "dans le pire cas. La mémoire O(n) est acceptée ici. Cela décrit des "
            "garanties théoriques, pas une durée d'exécution mesurée."
        ),
        "notion": "Stabilité et complexité garantie",
    },
    {
        "algorithme": "Tri par tas",
        "prompt": (
            "Tu dois trier 100 000 nombres, la stabilité n'est pas requise, "
            "la mémoire auxiliaire doit rester O(1) et le pire cas doit être "
            "garanti en O(n log n). Quel tri satisfait ces contraintes parmi les choix ?"
        ),
        "explication": (
            "Le tri par tas a une complexité théorique O(n log n) dans le pire cas "
            "et utilise O(1) mémoire auxiliaire dans cette implémentation. "
            "Le tri rapide n'offre pas cette garantie dans le pire cas."
        ),
        "notion": "Mémoire auxiliaire et pire cas",
    },
    {
        "algorithme": "Tri fusion",
        "prompt": (
            "Un export contient 20 000 commandes. Les commandes de même priorité "
            "doivent garder leur ordre d'arrivée; une mémoire temporaire O(n) est "
            "acceptable et le pire cas doit être O(n log n). Quel tri convient ?"
        ),
        "explication": (
            "Le tri fusion est stable et garantit O(n log n) dans le pire cas. "
            "La contrainte de stabilité et la mémoire disponible rendent ce choix "
            "adapté; cela ne signifie pas qu'il est toujours le plus rapide."
        ),
        "notion": "Stabilité et complexité garantie",
    },
    {
        "algorithme": "Tri par tas",
        "prompt": (
            "Un appareil doit trier un grand tableau en place : seules O(1) cases "
            "auxiliaires sont disponibles. La stabilité n'importe pas et le "
            "pire cas doit rester O(n log n). Quel tri convient ?"
        ),
        "explication": (
            "Le tri par tas respecte O(1) mémoire auxiliaire et O(n log n) dans "
            "le pire cas. Le tri fusion a besoin de O(n) mémoire et le tri rapide "
            "peut atteindre O(n²) dans son pire cas."
        ),
        "notion": "Mémoire auxiliaire et pire cas",
    },
)


def _question_prediction(difficulte: str, rng: random.Random) -> dict[str, Any]:
    taille = _TAILLES_ENTREE[difficulte]
    for _ in range(50):
        nom = rng.choice(_CHOIX_ALGORITHMES)
        entree = rng.sample(range(-20, 40), taille)
        historique = ALGORITHMES[nom](entree.copy())
        question = _question_etat(nom, entree, historique, rng)
        if question is not None:
            question.update({
                "type": "prediction_entrainement",
                "notion": "Suivre une mutation",
            })
            return question
    raise RuntimeError("Impossible de générer une mutation de tri exploitable.")


def _question_algorithme(
    rng: random.Random, notion: str | None = None
) -> dict[str, Any]:
    scenarios = [
        scenario for scenario in _SCENARIOS_ALGORITHME
        if notion is None or scenario["notion"] == notion
    ] or list(_SCENARIOS_ALGORITHME)
    scenario = rng.choice(scenarios)
    return {
        "type": "choix_algorithme_entrainement",
        "format": "choix",
        "prompt": scenario["prompt"],
        "nom_algorithme": scenario["algorithme"],
        "choix": list(_CHOIX_ALGORITHMES),
        "reponse_attendue": scenario["algorithme"],
        "explication": scenario["explication"],
        "notion": scenario["notion"],
    }


def _creer_question(
    type_question: str,
    difficulte: str,
    seed: int,
    notion: str | None = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    if type_question == "prediction_entrainement":
        question = _question_prediction(difficulte, rng)
    elif type_question == "choix_algorithme_entrainement":
        question = _question_algorithme(rng, notion)
    else:
        raise ValueError(f"Type de question inconnu : {type_question}")
    question.update({
        "id": uuid.uuid4().hex,
        "tentatives": 0,
        "resolue": False,
        "correcte": False,
        "points": 0,
        "indices_utilises": 0,
        "reponses": [],
    })
    return question


def creer_session_entrainement(
    difficulte: str = "Débutant",
    nombre_questions: int = TAILLE_SESSION_ENTRAINEMENT,
    seed: int | None = None,
    type_question_initial: str = "prediction_entrainement",
    notion_initiale: str | None = None,
) -> dict[str, Any]:
    if difficulte not in DIFFICULTES_ENTRAINEMENT:
        raise ValueError(f"Difficulté inconnue : {difficulte}")
    if nombre_questions < 1:
        raise ValueError("Une session doit contenir au moins une question.")
    if type_question_initial not in (
        "prediction_entrainement", "choix_algorithme_entrainement",
    ):
        raise ValueError(f"Type de question inconnu : {type_question_initial}")
    if seed is None:
        seed = random.SystemRandom().randrange(2**32)
    return {
        "id": uuid.uuid4().hex,
        "seed": seed,
        "difficulte": difficulte,
        "nombre_questions": nombre_questions,
        "questions": [_creer_question(
            type_question_initial, difficulte, seed, notion_initiale
        )],
        "index_question": 0,
        "terminee": False,
        "progression_succes": [],
    }


def valider_reponse_entrainement(question: dict[str, Any], reponse: Any) -> str:
    """Évalue une réponse une fois et ne modifie pas une question déjà résolue."""
    if question["resolue"]:
        return "deja_validee"
    question["tentatives"] += 1
    question.setdefault("reponses", []).append(
        reponse.copy() if isinstance(reponse, list) else reponse
    )
    question["correcte"] = reponse == question["reponse_attendue"]
    question["resolue"] = True
    question["points"] = 100 if question["correcte"] else 0
    return "correcte" if question["correcte"] else "incorrecte"


def passer_question_suivante(session: dict[str, Any]) -> bool:
    """Avance après validation; une erreur répète la notion, une réussite alterne."""
    if session["terminee"]:
        return False
    question = session["questions"][session["index_question"]]
    if not question["resolue"]:
        return False
    if session["index_question"] + 1 >= session["nombre_questions"]:
        session["terminee"] = True
        return True

    if question["correcte"]:
        type_suivant = (
            "choix_algorithme_entrainement"
            if question["type"] == "prediction_entrainement"
            else "prediction_entrainement"
        )
    else:
        type_suivant = question["type"]
    index_suivant = session["index_question"] + 1
    session["questions"].append(_creer_question(
        type_suivant,
        session["difficulte"],
        session["seed"] + index_suivant,
    ))
    session["index_question"] = index_suivant
    return True


def statistiques_session_entrainement(session: dict[str, Any]) -> dict[str, Any]:
    questions = session["questions"]
    reussies = [question for question in questions if question["correcte"]]
    notions = sorted({
        question["notion"]
        for question in questions
        if question["resolue"] and not question["correcte"]
    })
    return {
        "terminees": sum(question["resolue"] for question in questions),
        "reussies": len(reussies),
        "score": sum(question["points"] for question in questions),
        "notions_a_retravailler": notions,
        "pourcentage": round(100 * len(reussies) / len(questions)) if questions else 0,
    }