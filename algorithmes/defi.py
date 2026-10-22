"""Défis interactifs validés à partir des traces des tris existants."""

from __future__ import annotations

import random
import time
import uuid
from typing import Any

from algorithmes.tri import ALGORITHMES


DIFFICULTES_DEFI = ("Débutant", "Intermédiaire", "Avancé")
TAILLES_DEFI = {"Débutant": 3, "Intermédiaire": 4, "Avancé": 5}
TYPES_DEFI = (
    "Étapes", "Prédiction", "Identification", "Remise en ordre", "Rapidité", "Maîtrise",
)
ALGORITHMES_JOUABLES = tuple(ALGORITHMES)
DELAI_RAPIDITE_SECONDES = 120

_INDICES_ALGORITHMES = {
    "Tri à bulles": "Parcourt les voisins dans l'ordre et pousse progressivement les grandes valeurs vers la droite.",
    "Tri par sélection": "Cherche le minimum du suffixe non traité puis le place au début de ce suffixe.",
    "Tri par insertion": "Maintient un préfixe trié et insère la prochaine clé à sa place.",
    "Tri fusion": "Divise en sous-tableaux puis fusionne les moitiés triées en ordre.",
    "Tri rapide": "Partitionne autour d'un pivot en zones inférieure, égale et supérieure.",
    "Tri par tas": "Construit un max-heap et extrait son maximum vers le suffixe trié.",
}

_ETAPES_ORDONNABLES = {
    "Tri à bulles": (
        "Comparer deux voisins", "Échanger s'ils sont dans le mauvais ordre",
        "Avancer d'une position", "Recommencer sur le suffixe restant",
    ),
    "Tri par sélection": (
        "Initialiser le minimum provisoire", "Parcourir le suffixe non trié",
        "Comparer chaque candidat au minimum", "Placer le minimum au début du suffixe",
    ),
    "Tri par insertion": (
        "Choisir la prochaine clé", "Comparer la clé aux valeurs du préfixe",
        "Décaler les valeurs plus grandes", "Insérer la clé dans la case libre",
    ),
    "Tri fusion": (
        "Diviser le segment en deux", "Trier chaque moitié", "Comparer les têtes disponibles",
        "Écrire les valeurs dans l'ordre fusionné",
    ),
    "Tri rapide": (
        "Choisir un pivot", "Classer les valeurs autour du pivot", "Valider la partition",
        "Trier récursivement les segments restants",
    ),
    "Tri par tas": (
        "Construire un max-heap", "Comparer parent et enfants", "Échanger pour rétablir le tas",
        "Extraire le maximum et réduire le tas actif",
    ),
}


def _champ(
    label: str,
    options: list[Any] | range,
    reponse: str | None = None,
    partie: int | None = None,
    correspondances: dict[str, int] | None = None,
    libelles: dict[Any, str] | None = None,
    type_widget: str = "selectbox",
) -> dict[str, Any]:
    champ = {"label": label, "options": list(options), "type": type_widget}
    if reponse is not None:
        champ["reponse"] = reponse
    if partie is not None:
        champ["partie"] = partie
    if correspondances is not None:
        champ["correspondances"] = correspondances
    if libelles is not None:
        champ["libelles"] = libelles
    return champ


def _tache(
    action: str,
    etape: dict[str, Any],
    consigne: str,
    attendu: dict[str, Any],
    champs: list[dict[str, Any]],
    indices_non_ordonnes: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "action": action,
        "etape": etape,
        "consigne": consigne,
        "attendu": attendu,
        "schema": {"champs": champs},
        "indices_non_ordonnes": indices_non_ordonnes,
    }


def _tache_quiz(
    action: str,
    consigne: str,
    attendu: dict[str, Any],
    options: list[Any],
    explication: str,
    libelles: dict[Any, str] | None = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "etape": None,
        "consigne": consigne,
        "attendu": attendu,
        "schema": {"champs": [_champ(
            "Choisis une réponse", options, "reponse",
            libelles=libelles, type_widget="radio",
        )]},
        "indices_non_ordonnes": (),
        "explication": explication,
    }


def _taches_prediction(trace: list[dict[str, Any]], nombre: int, rng: random.Random):
    candidats = []
    deja_vus = set()
    precedent = None
    for etape in trace:
        apres = tuple(etape["liste"])
        avant = etape["avant"]
        avant = tuple(avant) if avant is not None else precedent
        precedent = apres
        if avant is None or avant == apres:
            continue
        signature = (etape["action"], avant, apres)
        if signature in deja_vus:
            continue
        deja_vus.add(signature)
        choix = {avant, apres}
        for gauche in range(len(apres)):
            for droite in range(gauche + 1, len(apres)):
                variante = list(apres)
                variante[gauche], variante[droite] = variante[droite], variante[gauche]
                choix.add(tuple(variante))
        options = list(choix - {apres})
        rng.shuffle(options)
        options = options[:3] + [apres]
        rng.shuffle(options)
        candidats.append((etape, avant, options))
    rng.shuffle(candidats)
    taches = []
    for etape, avant, options in candidats[:nombre]:
        attendu = tuple(etape["liste"])
        if attendu not in options:
            continue
        libelles = {option: str(list(option)) for option in options}
        taches.append(_tache_quiz(
            "prediction_etat",
            f"Tableau avant : {list(avant)}. Après l'étape « {etape['action']} », quel est l'état du tableau ?",
            {"reponse": attendu}, options,
            f"{etape['explication']} L'état obtenu est {list(attendu)}.", libelles,
        ))
    return taches


def _taches_identification(nombre: int, rng: random.Random):
    algorithmes = list(ALGORITHMES)
    melanges = algorithmes.copy()
    rng.shuffle(melanges)
    taches = []
    for nom in melanges[:nombre]:
        options = algorithmes.copy()
        rng.shuffle(options)
        taches.append(_tache_quiz(
            "identifier_algorithme",
            f"{_INDICES_ALGORITHMES[nom]} Quel algorithme est décrit ?",
            {"reponse": nom}, options,
            f"Il s'agit du {nom.lower()} : {_INDICES_ALGORITHMES[nom]}",
        ))
    return taches


def _tache_ordre(nom_algorithme: str, difficulte: str, rng: random.Random):
    etapes = list(_ETAPES_ORDONNABLES[nom_algorithme])
    if difficulte == "Débutant":
        etapes = etapes[:3]
    melange = etapes.copy()
    rng.shuffle(melange)
    champs = []
    attendu = {}
    for rang, description in enumerate(etapes, start=1):
        cle = f"rang_{description}"
        attendu[cle] = rang
        champs.append(_champ(description, range(1, len(etapes) + 1), cle))
    return {
        "action": "remettre_ordre",
        "etape": None,
        "consigne": f"Replace les étapes du {nom_algorithme.lower()} dans leur ordre d'exécution.",
        "attendu": attendu,
        "schema": {"champs": [
            next(champ for champ in champs if champ["label"] == description)
            for description in melange
        ]},
        "indices_non_ordonnes": (),
        "explication": "L'ordre correct est : " + " → ".join(etapes) + ".",
    }


def _creer_taches_mode(
    type_defi: str, nom_algorithme: str, difficulte: str,
    trace: list[dict[str, Any]], rng: random.Random,
):
    nombre = TAILLES_DEFI[difficulte]
    if type_defi == "Prédiction":
        return _taches_prediction(trace, nombre, rng)
    if type_defi == "Identification":
        return _taches_identification(nombre, rng)
    if type_defi == "Remise en ordre":
        return [_tache_ordre(nom_algorithme, difficulte, rng)]
    if type_defi == "Rapidité":
        return _taches_identification(nombre, rng)
    if type_defi == "Maîtrise":
        taches = _taches_prediction(trace, 1, rng)
        taches.extend(_taches_identification(1, rng))
        taches.append(_tache_ordre(nom_algorithme, "Avancé", rng))
        return taches
    return _taches_depuis_trace(nom_algorithme, trace)


def _positions_paire(taille: int, premier: str, second: str, reponse: str = "indices"):
    return [
        _champ(premier, range(taille), reponse=reponse, partie=0),
        _champ(second, range(taille), reponse=reponse, partie=1),
    ]


def _tache_depuis_etape(
    nom: str, etape: dict[str, Any], relation_rapide: str | None = None,
) -> dict[str, Any] | None:
    action = etape["action"]
    details = etape["details"]
    indices = etape["indices"] or ()
    taille = len(etape["liste"])
    positions = list(range(taille))
    bornes_segment = details.get("zone_active") or (0, taille - 1)

    if nom == "Tri fusion":
        if action == "division":
            debut, fin = details["zone_active"]
            milieu = details["zones"][0][1]
            return _tache(
                "diviser", etape,
                "Choisis le début, le milieu et la fin du segment à séparer.",
                {"debut": debut, "milieu": milieu, "fin": fin},
                [
                    _champ("Début du segment", range(taille), "debut"),
                    _champ("Dernière position gauche", range(taille), "milieu"),
                    _champ("Fin du segment", range(taille), "fin"),
                ],
            )
        if action == "fusion":
            debut, fin = details["zone_active"]
            milieu = details["zones"][0][1]
            return _tache(
                "fusionner", etape,
                "Identifie les deux moitiés triées à fusionner.",
                {"debut": debut, "milieu": milieu, "fin": fin},
                [
                    _champ("Début du segment", range(taille), "debut"),
                    _champ("Frontière des moitiés", range(taille), "milieu"),
                    _champ("Fin du segment", range(taille), "fin"),
                ],
            )
        if action == "comparaison" and "tampon_gauche" in details:
            attendu = "gauche" if etape["valeurs"][0] <= etape["valeurs"][1] else "droite"
            return _tache(
                "choisir_fusion", etape,
                "Choisis la moitié dont la première valeur disponible doit sortir ensuite.",
                {"cote": attendu},
                [_champ(
                    "Valeur à prendre", ("gauche", "droite"), "cote",
                    libelles={"gauche": "Tête de la moitié gauche", "droite": "Tête de la moitié droite"},
                    type_widget="radio",
                )],
            )
        if action == "placement":
            destination = details["destination"]
            source = indices[0]
            return _tache(
                "placer_tampon", etape,
                "Choisis la valeur source et sa destination dans le tampon fusionné.",
                {"source": source, "destination": destination},
                [
                    _champ("Position source", positions, "source"),
                    _champ("Place dans le tampon", range(taille), "destination"),
                ],
            )
        if action == "ecriture":
            debut, fin = details["zone_active"]
            options = [
                (valeur, destination)
                for destination, valeur in enumerate(details["tampon"], start=debut)
            ]
            attendu = {"valeur": etape["valeurs"][0], "destination": details["destination"]}
            return _tache(
                "ecrire_fusion", etape,
                "Recopie une valeur du tampon vers la position correspondante du tableau.",
                attendu,
                [_champ(
                    "Valeur et position", options,
                    correspondances={"valeur": 0, "destination": 1},
                    libelles={valeur: f"{valeur[0]} → position {valeur[1]}" for valeur in options},
                )],
            )
        return None

    if nom == "Tri rapide":
        if action == "pivot":
            debut, fin = bornes_segment
            return _tache(
                "choisir_pivot", etape,
                f"Choisis la position du pivot dans le segment [{debut}..{fin}].",
                {"indice": indices[0]},
                [_champ("Position du pivot", range(debut, fin + 1), "indice")],
            )
        if action == "partition" and details.get("zones"):
            zones = details["zones"]
            return _tache(
                "confirmer_partition", etape,
                "Délimite la zone égale au pivot; les valeurs voisines forment les zones inférieure et supérieure.",
                {"debut_egal": zones[1][0], "fin_egal": zones[1][1]},
                [
                    _champ("Début de la zone égale", range(taille), "debut_egal"),
                    _champ("Fin de la zone égale", range(taille), "fin_egal"),
                ],
            )
        if action == "partition":
            moins, courant, plus = details["partition"]
            debut, fin = details["zone_active"]
            return _tache(
                "initialiser_partition", etape,
                "Place les trois frontières au début de la partition trois voies.",
                {"moins": moins, "courant": courant, "plus": plus},
                [
                    _champ("Frontière gauche", range(debut, fin + 1), "moins"),
                    _champ("Curseur courant", range(debut, fin + 1), "courant"),
                    _champ("Frontière droite", range(debut, fin + 1), "plus"),
                ],
            )
        if action == "comparaison":
            if relation_rapide is None:
                return None
            return _tache(
                "classer_partition", etape,
                "Classe la valeur courante par rapport au pivot.",
                {"relation": relation_rapide},
                [_champ(
                    "Relation au pivot", ("gauche", "egal", "droite"), "relation",
                    libelles={"gauche": "Inférieure", "egal": "Égale", "droite": "Supérieure"},
                    type_widget="radio",
                )],
            )
        if action == "decision":
            valeur = etape["valeurs"][0]
            pivot = details["pivot_value"]
            zone = "egal" if valeur == pivot else "frontiere_gauche" if valeur < pivot else "frontiere_droite"
            return _tache(
                "avancer_partition", etape,
                "Indique la zone qui est validée sans échange à cette étape.",
                {"zone": zone},
                [_champ(
                    "Décision", ("frontiere_gauche", "egal", "frontiere_droite"), "zone",
                    libelles={
                        "frontiere_gauche": "Déjà à la frontière gauche",
                        "egal": "Reste dans la zone égale",
                        "frontiere_droite": "Déjà à la frontière droite",
                    },
                    type_widget="radio",
                )],
            )
        if action == "echange":
            return _tache(
                "echanger_partition", etape,
                "Échange la valeur courante avec la frontière de sa zone.",
                {"indices": tuple(indices)},
                _positions_paire(taille, "Position courante", "Position frontière"),
                ("indices",),
            )
        if action == "recursion":
            debut, fin = details["zone_active"]
            return _tache(
                "choisir_segment", etape,
                "Choisis le segment restant à trier récursivement.",
                {"debut": debut, "fin": fin},
                [
                    _champ("Début du segment", range(taille + 1), "debut"),
                    _champ("Fin du segment", range(-1, taille), "fin"),
                ],
            )
        return None

    if nom == "Tri par tas":
        if action == "construction_tas":
            return _tache(
                "initialiser_tas", etape,
                "Définis la taille de la zone à transformer en max-heap.",
                {"taille_tas": taille},
                [_champ("Taille initiale du tas", range(1, taille + 1), "taille_tas")],
            )
        if action == "tas":
            return _tache(
                "tamiser_tas", etape,
                "Choisis la racine et la taille du tas actif à rétablir.",
                {"racine": details["racine"], "taille_tas": details["heap_size"]},
                [
                    _champ("Racine", positions, "racine"),
                    _champ("Taille du tas actif", range(1, taille + 1), "taille_tas"),
                ],
            )
        if action == "comparaison":
            return _tache(
                "comparer_tas", etape,
                "Choisis le parent et l'enfant comparés pendant le tamisage.",
                {"indices": tuple(indices)},
                _positions_paire(taille, "Parent ou candidat", "Enfant comparé"),
            )
        if action == "decision":
            return _tache(
                "confirmer_tas", etape,
                "Indique le parent dont la propriété de max-heap est maintenant vérifiée.",
                {"racine": details["racine"]},
                [_champ("Parent validé", positions, "racine")],
            )
        if action == "echange":
            return _tache(
                "echanger_tas", etape,
                "Échange la racine avec le plus grand enfant, ou place le maximum en fin de tas.",
                {"indices": tuple(indices)},
                _positions_paire(taille, "Première position", "Seconde position"),
                ("indices",),
            )
        if action == "reduction_tas":
            return _tache(
                "reduire_tas", etape,
                "Réduis le tas actif après avoir placé son maximum dans le suffixe trié.",
                {"taille_tas": details["heap_size"]},
                [_champ("Nouvelle taille du tas", range(1, taille + 1), "taille_tas")],
            )
        return None

    if action == "initialisation" and etape["valeur_en_cours"] is not None:
        return _tache(
            "choisir_cle", etape,
            "Choisis la position de la prochaine clé à insérer dans le préfixe trié.",
            {"indice": indices[0]},
            [_champ("Position de la clé", positions, "indice")],
        )
    if action == "comparaison":
        return _tache(
            "comparer", etape,
            "Choisis les deux positions que l'algorithme doit comparer maintenant.",
            {"indices": tuple(indices)},
            _positions_paire(taille, "Première position", "Seconde position"),
        )
    if action == "echange":
        return _tache(
            "echanger", etape,
            "Choisis les deux positions que l'algorithme doit échanger maintenant.",
            {"indices": tuple(indices)},
            _positions_paire(taille, "Première position", "Seconde position"),
            ("indices",),
        )
    if action == "decision":
        return _tache(
            "decision", etape,
            "Décide si un échange est nécessaire à cette étape.",
            {"echange": False},
            [_champ(
                "Décision", (False, True), "echange",
                libelles={False: "Conserver sans échange", True: "Échanger"},
                type_widget="radio",
            )],
        )
    if action == "deplacement":
        return _tache(
            "deplacer", etape,
            "Choisis la valeur à décaler et sa position de destination.",
            {"source": indices[0], "destination": indices[1]},
            [
                _champ("Position source", positions, "source"),
                _champ("Position de destination", positions, "destination"),
            ],
        )
    if action == "insertion":
        return _tache(
            "inserer", etape,
            "Choisis la position où insérer la clé.",
            {"destination": indices[0]},
            [_champ("Position d'insertion", positions, "destination")],
        )
    return None


def _taches_depuis_trace(nom: str, trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    taches = []
    for index, etape in enumerate(trace):
        relation_rapide = None
        if nom == "Tri rapide" and etape["action"] == "comparaison":
            suivante = trace[index + 1] if index + 1 < len(trace) else None
            meme_test = (
                suivante is not None
                and suivante["action"] == "comparaison"
                and suivante["indices"] == etape["indices"]
                and suivante["valeurs"] == etape["valeurs"]
                and suivante["details"].get("partition") == etape["details"].get("partition")
            )
            if meme_test:
                continue
            valeur, pivot = etape["valeurs"]
            relation_rapide = "gauche" if valeur < pivot else "droite" if valeur > pivot else "egal"

        tache = _tache_depuis_etape(nom, etape, relation_rapide)
        if tache is not None:
            taches.append(tache)
    return taches


def creer_defi(
    nom_algorithme: str,
    difficulte: str,
    seed: int | None = None,
    nombres: list[int] | None = None,
    type_defi: str = "Étapes",
) -> dict[str, Any]:
    """Crée une session de défi avec des questions dérivées des tris existants."""
    if nom_algorithme not in ALGORITHMES_JOUABLES:
        raise ValueError(f"Algorithme pas encore jouable : {nom_algorithme}")
    if difficulte not in DIFFICULTES_DEFI:
        raise ValueError(f"Difficulté inconnue : {difficulte}")
    if type_defi not in TYPES_DEFI:
        raise ValueError(f"Type de défi inconnu : {type_defi}")
    if seed is None:
        seed = random.SystemRandom().randrange(2**32)

    rng = random.Random(seed)
    if nombres is None:
        taille = TAILLES_DEFI[difficulte]
        nombres = [rng.randint(-5, 9) for _ in range(taille)]
        if nombres == sorted(nombres):
            nombres[0], nombres[-1] = nombres[-1], nombres[0]
    elif not nombres or len(nombres) > 8 or any(not isinstance(valeur, int) for valeur in nombres):
        raise ValueError("Le tableau doit contenir de 1 à 8 nombres entiers.")

    entree = nombres.copy()
    trace = ALGORITHMES[nom_algorithme](entree.copy())
    taches = (
        _taches_depuis_trace(nom_algorithme, trace)
        if type_defi == "Étapes"
        else _creer_taches_mode(type_defi, nom_algorithme, difficulte, trace, rng)
    )
    if not taches and type_defi != "Étapes":
        raise ValueError(
            "Impossible de générer une question valide pour cette entrée; choisis un autre tableau."
        )
    defi = {
        "id": uuid.uuid4().hex,
        "nom_algorithme": nom_algorithme,
        "difficulte": difficulte,
        "type_defi": type_defi,
        "seed": seed,
        "entree": entree,
        "trace": trace,
        "taches": taches,
        "curseur": 0,
        "actions": 0,
        "erreurs": 0,
        "indices_utilises": 0,
        "indices_etape": 0,
        "tentatives": 0,
        "feedback": None,
    }
    if type_defi == "Rapidité":
        defi["debut_monotone"] = time.monotonic()
        defi["limite_secondes"] = DELAI_RAPIDITE_SECONDES
        defi["temps_ecoule"] = False
    return defi


def defi_termine(defi: dict[str, Any]) -> bool:
    if defi.get("type_defi") == "Rapidité" and not defi.get("temps_ecoule"):
        if time.monotonic() - defi["debut_monotone"] >= defi["limite_secondes"]:
            defi["temps_ecoule"] = True
    return defi["curseur"] >= len(defi["taches"]) or defi.get("temps_ecoule", False)


def progression_defi(defi: dict[str, Any]) -> dict[str, int | float | bool]:
    total = len(defi["taches"])
    tentatives = defi["actions"] + defi["erreurs"]
    resultat = {
        "terminees": defi["curseur"],
        "total": total,
        "actions": defi["actions"],
        "erreurs": defi["erreurs"],
        "indices": defi["indices_utilises"],
        "reussite": defi["curseur"] == total,
        "score": round(100 * defi["actions"] / tentatives) if tentatives else 0,
    }
    if defi.get("type_defi") == "Rapidité":
        resultat["temps_secondes"] = min(
            defi["limite_secondes"],
            round(time.monotonic() - defi["debut_monotone"], 1),
        )
        resultat["temps_ecoule"] = defi_termine(defi) and defi["temps_ecoule"]
    return resultat


def etat_defi(defi: dict[str, Any]) -> list[int]:
    if defi_termine(defi):
        return defi["trace"][-1]["liste"].copy()
    etape = defi["taches"][defi["curseur"]]["etape"]
    if etape is None:
        return defi["entree"].copy()
    if etape["avant"] is not None:
        return etape["avant"].copy()
    return etape["liste"].copy()


def consigne_defi(defi: dict[str, Any]) -> str:
    if defi_termine(defi):
        return "Défi terminé : le tableau est trié."
    return defi["taches"][defi["curseur"]]["consigne"]


def _reponse_attendue(tache: dict[str, Any]) -> dict[str, Any]:
    return {"action": tache["action"], **tache["attendu"]}


def _reponse_valide(tache: dict[str, Any], reponse: Any) -> bool:
    if not isinstance(reponse, dict):
        return False
    attendue = _reponse_attendue(tache)
    if reponse.get("action") != attendue["action"]:
        return False
    for cle, valeur in attendue.items():
        if cle == "action":
            continue
        actual = reponse.get(cle)
        if cle in tache["indices_non_ordonnes"]:
            if not isinstance(actual, (tuple, list)) or len(actual) != len(valeur):
                return False
            if sorted(actual) != sorted(valeur):
                return False
        elif cle == "indices":
            if not isinstance(actual, (tuple, list)) or tuple(actual) != tuple(valeur):
                return False
        elif actual != valeur:
            return False
    return True


def _explication_incorrecte(nom: str, action: str) -> str:
    principes = {
        "Tri à bulles": "Le tri à bulles compare les voisins dans l'ordre du passage, puis échange seulement si nécessaire.",
        "Tri par sélection": "La sélection examine le suffixe non traité et conserve son minimum provisoire.",
        "Tri par insertion": "L'insertion maintient le préfixe gauche ordonné et déplace la clé jusqu'à sa place.",
        "Tri fusion": "Le tri fusion combine des moitiés triées en conservant leur ordre et toutes leurs valeurs.",
        "Tri rapide": "Le tri rapide maintient les zones inférieure, égale et supérieure autour du pivot.",
        "Tri par tas": "Le tri par tas conserve un max-heap dans la zone active et réduit cette zone après chaque extraction.",
    }
    if action in ("prediction_etat", "identifier_algorithme", "remettre_ordre"):
        return "La réponse attendue est indiquée ci-dessous. "
    operation = {
        "comparer": "Les positions choisies ne correspondent pas à la comparaison attendue.",
        "echanger": "L'échange ne correspond pas à la décision de comparaison qui vient d'être faite.",
        "decision": "Vérifie si le minimum du suffixe est déjà à sa place avant de décider.",
        "choisir_cle": "La clé est le prochain élément non encore intégré au préfixe trié.",
        "deplacer": "Un déplacement d'insertion décale l'élément précédent vers la droite.",
        "inserer": "La clé doit être insérée après tous les éléments plus petits ou égaux du préfixe.",
        "diviser": "La frontière doit séparer le segment en deux sous-tableaux contigus.",
        "fusionner": "Les deux sous-tableaux à fusionner doivent être adjacents et déjà triés.",
        "choisir_fusion": "La prochaine valeur doit être la plus petite tête encore disponible des deux tampons.",
        "placer_tampon": "La source et la destination doivent respecter l'ordre de fusion du tampon.",
        "ecrire_fusion": "La valeur écrite doit correspondre à la case courante du tampon fusionné.",
        "choisir_pivot": "Le pivot doit appartenir au segment actif traité par cette partition.",
        "initialiser_partition": "Les frontières initiales doivent encadrer exactement le segment actif.",
        "classer_partition": "La relation doit être évaluée par rapport à la valeur du pivot.",
        "avancer_partition": "La décision doit respecter la zone déterminée par la comparaison au pivot.",
        "echanger_partition": "L'échange doit utiliser le curseur courant et la frontière de la zone visée.",
        "confirmer_partition": "La zone égale doit être délimitée après le parcours complet du segment.",
        "choisir_segment": "Le segment récursif doit être exactement la zone restante à trier.",
        "initialiser_tas": "La construction commence avec toute la zone non triée.",
        "tamiser_tas": "Le tamisage doit repartir de la racine de la zone active.",
        "comparer_tas": "Le parent et son enfant doivent être comparés selon leur position dans le tas.",
        "confirmer_tas": "La racine n'est validée qu'après avoir vérifié ses enfants actifs.",
        "echanger_tas": "L'échange doit remonter le plus grand enfant ou placer le maximum à la fin.",
        "reduire_tas": "La nouvelle taille exclut uniquement le maximum placé dans le suffixe trié.",
    }[action]
    return f"{operation} {principes[nom]}"


def valider_action(defi: dict[str, Any], reponse: Any) -> str:
    """Valide une action contre le prochain événement réel de la trace."""
    if defi_termine(defi):
        return "termine"
    defi["tentatives"] += 1
    tache = defi["taches"][defi["curseur"]]
    if not _reponse_valide(tache, reponse):
        defi["erreurs"] += 1
        quiz = defi.get("type_defi") in TYPES_DEFI[1:]
        texte_correction = tache.get("explication") or _explication_incorrecte(
            defi["nom_algorithme"], tache["action"]
        )
        defi["feedback"] = {
            "correcte": False,
            "texte": texte_correction,
            "reponse_attendue": tache["attendu"],
        }
        if quiz:
            defi["curseur"] += 1
            defi["indices_etape"] = 0
        return "incorrecte"

    defi["actions"] += 1
    defi["curseur"] += 1
    defi["indices_etape"] = 0
    defi["feedback"] = {
        "correcte": True,
        "texte": tache.get("explication") or tache["etape"]["explication"],
    }
    return "correcte"


def utiliser_indice(defi: dict[str, Any]) -> str | None:
    if defi_termine(defi) or defi["indices_etape"] >= 2:
        return None
    nom = defi["nom_algorithme"]
    tache = defi["taches"][defi["curseur"]]
    action = tache["action"]
    niveau = defi["indices_etape"]
    if defi.get("type_defi") in TYPES_DEFI[1:]:
        indices_quiz = {
            "prediction_etat": (
                "Compare le tableau affiché aux états avant et après l'opération.",
                "L'opération ne change que les positions directement concernées.",
            ),
            "identifier_algorithme": (
                "Repère la structure maintenue : préfixe, suffixe, pivot, tas ou moitiés.",
                "Écarte les algorithmes dont l'invariant ne correspond pas à cette description.",
            ),
            "remettre_ordre": (
                "Commence par l'initialisation, puis place les opérations répétées avant la finalisation.",
                "La dernière étape fixe ou écrit l'élément dans sa position définitive.",
            ),
        }
        texte = indices_quiz[action][niveau]
        defi["indices_etape"] += 1
        defi["indices_utilises"] += 1
        return texte
    indices = {
        "Tri à bulles": (
            "À chaque comparaison, le passage avance de gauche à droite parmi les voisins.",
            "Après une comparaison, un échange n'est requis que si la valeur de gauche est plus grande.",
        ),
        "Tri par sélection": (
            "Le préfixe gauche est fixé; cherche le minimum uniquement dans le suffixe restant.",
            "Compare chaque candidat au minimum provisoire, puis place le minimum au début du suffixe.",
        ),
        "Tri par insertion": (
            "Le préfixe gauche est déjà ordonné; la clé vient du premier élément à sa droite.",
            "Décale vers la droite les valeurs strictement supérieures à la clé, puis insère-la dans le trou.",
        ),
        "Tri fusion": (
            "Chaque division donne deux segments contigus; la fusion ne commence qu'après leur tri.",
            "À chaque choix, compare les premières valeurs encore disponibles dans les deux tampons.",
        ),
        "Tri rapide": (
            "Le pivot choisi reste le repère de la partition, même s'il change de position lors d'un échange.",
            "Les valeurs < pivot vont à gauche, les égales au centre et les > pivot à droite.",
        ),
        "Tri par tas": (
            "Un max-heap place la plus grande valeur à la racine; les enfants sont aux indices 2i+1 et 2i+2.",
            "Après une extraction, le suffixe trié s'agrandit et le tamisage ne touche qu'au tas actif.",
        ),
    }
    action_hints = {
        "comparer": "Repère les rôles des deux opérandes avant de choisir leurs positions.",
        "echanger": "Seule une décision qui améliore l'ordre local autorise cet échange.",
        "decision": "Le minimum provisoire détermine si un échange est utile.",
        "choisir_cle": "La clé est prise juste après la partie déjà ordonnée.",
        "deplacer": "La valeur déplacée laisse temporairement un espace pour la clé.",
        "inserer": "La clé va dans le premier emplacement qui respecte l'ordre du préfixe.",
        "diviser": "Le milieu est le dernier indice de la moitié gauche; la moitié droite commence juste après.",
        "fusionner": "La frontière des tampons doit être identique à celle de la division correspondante.",
        "choisir_fusion": "N'utilise que les têtes non consommées; les valeurs restantes seront copiées ensuite.",
        "placer_tampon": "La position de tampon augmente d'une case à chaque valeur choisie.",
        "ecrire_fusion": "La recopie repart au début du segment et suit l'ordre du tampon.",
        "choisir_pivot": "Le moteur choisit le milieu du segment; son identité est distincte de sa position courante.",
        "initialiser_partition": "Le curseur commence à gauche; la frontière droite commence à la fin du segment.",
        "classer_partition": "Après une valeur >= pivot, le tri rapide distingue encore > de ==.",
        "avancer_partition": "Une valeur égale avance le curseur sans échange; les frontières se déplacent selon la zone.",
        "echanger_partition": "Après un échange avec la frontière droite, le curseur courant ne s'avance pas immédiatement.",
        "confirmer_partition": "La zone centrale contient au moins le pivot et toutes les valeurs égales.",
        "choisir_segment": "Les intervalles vides sont possibles; un segment d'un élément est déjà trié.",
        "initialiser_tas": "La taille initiale comprend toutes les valeurs du tableau.",
        "tamiser_tas": "La racine à traiter est un parent; les indices hors de la taille active ne comptent plus.",
        "comparer_tas": "Le candidat courant est le plus grand entre le parent et les enfants déjà examinés.",
        "confirmer_tas": "L'invariant est local à cette racine et à ses enfants présents dans le tas actif.",
        "echanger_tas": "Le plus grand candidat remonte; lors de l'extraction, la racine rejoint la fin active.",
        "reduire_tas": "La taille diminue d'une case après extraction du maximum.",
    }
    texte = indices[nom][niveau]
    if niveau == 1:
        texte += " " + action_hints[action]
    defi["indices_etape"] += 1
    defi["indices_utilises"] += 1
    return texte


def contexte_defi(defi: dict[str, Any]) -> str:
    if defi_termine(defi):
        return ""
    tache = defi["taches"][defi["curseur"]]
    if tache["etape"] is None:
        return ""
    etape = tache["etape"]
    details = etape["details"]
    nom = defi["nom_algorithme"]
    debut, fin = details.get("zone_active", (0, len(defi["entree"]) - 1))
    if nom == "Tri fusion":
        parties = details.get("zones")
        contexte = f"Segment actif [{debut}..{fin}]"
        if parties:
            contexte += f" · moitiés [{parties[0][0]}..{parties[0][1]}] et [{parties[1][0]}..{parties[1][1]}]"
        if "tampon_gauche" in details:
            contexte += f" · tampons {details['tampon_gauche']} / {details['tampon_droit']}"
            contexte += f" · tampon construit {details['tampon']}"
        return contexte
    if nom == "Tri rapide":
        contexte = f"Segment actif [{debut}..{fin}]"
        if "pivot_value" in details:
            contexte += f" · pivot {details['pivot_value']}"
        if "partition" in details:
            moins, courant, plus = details["partition"]
            contexte += f" · frontières moins/courant/plus : {moins}/{courant}/{plus}"
        return contexte
    if nom == "Tri par tas":
        taille_tas = details.get("heap_size", len(defi["entree"]))
        contexte = f"Tas actif [0..{taille_tas - 1}] · suffixe trié [{taille_tas}..{len(defi['entree']) - 1}]"
        if details.get("phase_tas"):
            contexte += f" · phase {details['phase_tas']}"
        if details.get("racine") is not None:
            contexte += f" · racine {details['racine']}"
        return contexte
    return ""


def reinitialiser_defi(defi: dict[str, Any]) -> dict[str, Any]:
    return creer_defi(
        defi["nom_algorithme"],
        defi["difficulte"],
        seed=defi["seed"],
        nombres=defi["entree"],
        type_defi=defi.get("type_defi", "Étapes"),
    )
