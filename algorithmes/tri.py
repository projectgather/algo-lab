"""Moteurs de tri pédagogiques.

Les comparaisons comptent uniquement les tests entre deux valeurs. Les
échanges comptent les permutations réelles de deux cases. Les déplacements
comptent les écritures de décalage et d'insertion du tri par insertion.
"""

from __future__ import annotations

from typing import Any


PSEUDOCODES = {
    "Tri à bulles": (
        "pour chaque passage tant qu'un échange a lieu",
        "pour chaque paire voisine non triée",
        "comparer A[j] et A[j + 1]",
        "si A[j] > A[j + 1]",
        "échanger A[j] et A[j + 1]",
        "arrêter si le passage n'a fait aucun échange",
        "terminer le tri",
    ),
    "Tri par sélection": (
        "pour i de 0 à n - 2",
        "minimum = i",
        "pour j de i + 1 à n - 1",
        "comparer A[j] et A[minimum]",
        "si A[j] < A[minimum], minimum = j",
        "si minimum != i",
        "échanger A[i] et A[minimum]",
        "terminer le tri",
    ),
    "Tri par insertion": (
        "pour i de 1 à n - 1",
        "clé = A[i] ; j = i - 1",
        "tant que j >= 0",
        "comparer A[j] et clé",
        "si A[j] > clé, décaler A[j] à droite",
        "insérer la clé en A[j + 1]",
        "terminer le tri",
    ),
    "Tri fusion": (
        "fusionner(A, gauche, droite)",
        "si gauche >= droite, terminer ce sous-tableau",
        "milieu = (gauche + droite) // 2",
        "trier A[gauche..milieu]",
        "trier A[milieu + 1..droite]",
        "copier les deux moitiés dans des tampons",
        "comparer les premières valeurs disponibles",
        "placer la plus petite valeur dans le tampon fusionné",
        "placer les valeurs restantes dans le tampon",
        "recopier le tampon fusionné dans A[gauche..droite]",
        "terminer le tri",
    ),
    "Tri rapide": (
        "quicksort(A, gauche, droite)",
        "si gauche >= droite, terminer ce sous-tableau",
        "pivot = A[(gauche + droite) // 2]",
        "initialiser gauche, courant et droite de partition",
        "comparer A[courant] au pivot",
        "si A[courant] < pivot, échanger vers la zone gauche",
        "sinon si A[courant] > pivot, échanger vers la zone droite",
        "sinon, avancer le curseur dans la zone égale",
        "répéter tant que courant <= droite",
        "trier récursivement les valeurs < pivot",
        "trier récursivement les valeurs > pivot",
        "terminer le tri",
    ),
    "Tri par tas": (
        "pour parent de n // 2 - 1 à 0",
        "rétablir la propriété de max-heap",
        "comparer le parent à son enfant gauche",
        "comparer le plus grand à l'enfant droit",
        "échanger avec le plus grand enfant si nécessaire",
        "échanger la racine avec la fin du tas actif",
        "réduire la zone active du tas",
        "rétablir le max-heap depuis la racine",
        "terminer le tri",
    ),
}

INFORMATIONS_ALGORITHMES = {
    "Tri à bulles": {"anglais": "Bubble Sort", "meilleur": "O(n)", "moyen": "O(n²)", "pire": "O(n²)", "memoire": "O(1)"},
    "Tri par sélection": {"anglais": "Selection Sort", "meilleur": "O(n²)", "moyen": "O(n²)", "pire": "O(n²)", "memoire": "O(1)"},
    "Tri par insertion": {"anglais": "Insertion Sort", "meilleur": "O(n)", "moyen": "O(n²)", "pire": "O(n²)", "memoire": "O(1)"},
    "Tri fusion": {"anglais": "Merge Sort", "meilleur": "O(n log n)", "moyen": "O(n log n)", "pire": "O(n log n)", "memoire": "O(n)"},
    "Tri rapide": {"anglais": "Quick Sort", "meilleur": "O(n log n)", "moyen": "O(n log n)", "pire": "O(n²)", "memoire": "O(log n) moyen, O(n) pire"},
    "Tri par tas": {"anglais": "Heap Sort", "meilleur": "O(n log n)", "moyen": "O(n log n)", "pire": "O(n log n)", "memoire": "O(1)"},
}


def _etape(
    liste: list[int],
    action: str,
    explication: str,
    ligne: int,
    comparaisons: int,
    echanges: int,
    deplacements: int,
    indices: tuple[int, ...] | None = None,
    valeurs: tuple[int, ...] | None = None,
    avant: list[int] | None = None,
    valeur_en_cours: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit une etape autonome avec un instantane immuable par copie."""
    etape = {
        "liste": liste.copy(),
        "action": action,
        "indices": indices,
        "valeurs": valeurs,
        "avant": avant.copy() if avant is not None else None,
        "apres": liste.copy() if avant is not None else None,
        "valeur_en_cours": valeur_en_cours,
        "explication": explication,
        "ligne_pseudocode": ligne,
        "comparaison": indices,
        "echange": action == "echange",
        "comparaisons": comparaisons,
        "echanges": echanges,
        "deplacements": deplacements,
        "operations": echanges + deplacements,
        "details": details.copy() if details is not None else {},
    }
    return etape


def _initiale(liste: list[int]) -> dict[str, Any]:
    return _etape(
        liste, "initialisation", "La liste est prête ; aucun élément n'a encore été comparé.",
        1, 0, 0, 0,
    )


def _terminee(
    liste: list[int], comparaisons: int, echanges: int, deplacements: int,
    ligne: int,
) -> dict[str, Any]:
    return _etape(
        liste, "fin", "Le tri est terminé : la liste est ordonnée.",
        ligne, comparaisons, echanges, deplacements,
    )


def tri_a_bulles(nombres: list[int]) -> list[dict[str, Any]]:
    liste = nombres.copy()
    etapes = [_initiale(liste)]
    comparaisons = echanges = 0

    for passage in range(len(liste) - 1):
        echange_pendant_passage = False
        for indice in range(len(liste) - passage - 1):
            avant = liste.copy()
            gauche, droite = liste[indice], liste[indice + 1]
            comparaisons += 1
            doit_echanger = gauche > droite
            details = (
                {"zone_placee": (len(liste) - passage, len(liste) - 1)}
                if passage else None
            )
            etapes.append(_etape(
                liste, "comparaison",
                f"{gauche} {'>' if doit_echanger else '<='} {droite} : "
                f"{'un échange est nécessaire' if doit_echanger else 'la paire reste en place'}.",
                3, comparaisons, echanges, 0, (indice, indice + 1),
                (gauche, droite), avant, details=details,
            ))
            if doit_echanger:
                liste[indice], liste[indice + 1] = droite, gauche
                echanges += 1
                echange_pendant_passage = True
                etapes.append(_etape(
                    liste, "echange",
                    f"Les valeurs {gauche} et {droite} sont échangées pour placer "
                    "la plus petite à gauche.",
                    5, comparaisons, echanges, 0, (indice, indice + 1),
                    (gauche, droite), avant, details=details,
                ))
        if not echange_pendant_passage:
            break

    etapes.append(_terminee(liste, comparaisons, echanges, 0, 7))
    return etapes


def tri_par_selection(nombres: list[int]) -> list[dict[str, Any]]:
    liste = nombres.copy()
    etapes = [_initiale(liste)]
    comparaisons = echanges = 0

    for debut in range(len(liste) - 1):
        indice_min = debut
        for indice in range(debut + 1, len(liste)):
            avant = liste.copy()
            candidat, minimum = liste[indice], liste[indice_min]
            comparaisons += 1
            nouveau_minimum = candidat < minimum
            details = {"zone_placee": (0, debut - 1)} if debut else None
            etapes.append(_etape(
                liste, "comparaison",
                f"{candidat} {'<' if nouveau_minimum else '>='} {minimum} : "
                f"{'le minimum provisoire devient la position ' + str(indice) if nouveau_minimum else 'le minimum reste en position ' + str(indice_min)}.",
                4, comparaisons, echanges, 0, (indice, indice_min),
                (candidat, minimum), avant, details=details,
            ))
            if nouveau_minimum:
                indice_min = indice

        if indice_min != debut:
            avant = liste.copy()
            gauche, droite = liste[debut], liste[indice_min]
            liste[debut], liste[indice_min] = droite, gauche
            echanges += 1
            etapes.append(_etape(
                liste, "echange",
                f"Le minimum {droite} est placé en position {debut} par échange "
                f"avec {gauche} en position {indice_min}.",
                7, comparaisons, echanges, 0, (debut, indice_min),
                (gauche, droite), avant,
                details={"zone_placee": (0, debut - 1)} if debut else None,
            ))
        else:
            etapes.append(_etape(
                liste, "decision",
                f"La valeur en position {debut} est déjà le minimum ; aucun échange.",
                6, comparaisons, echanges, 0, (debut,), (liste[debut],),
                details={"zone_placee": (0, debut)},
            ))

    etapes.append(_terminee(liste, comparaisons, echanges, 0, 8))
    return etapes


def tri_par_insertion(nombres: list[int]) -> list[dict[str, Any]]:
    liste = nombres.copy()
    etapes = [_initiale(liste)]
    comparaisons = deplacements = 0

    for indice in range(1, len(liste)):
        valeur = liste[indice]
        position = indice - 1
        etapes.append(_etape(
            liste, "initialisation",
            f"La valeur {valeur} est prise comme clé ; la partie gauche est déjà triée.",
            2, comparaisons, 0, deplacements, (indice,), (valeur,),
            valeur_en_cours=valeur,
            details={"prefixe_trie": (0, indice - 1)} if indice > 0 else {},
        ))

        while position >= 0:
            avant = liste.copy()
            precedente = liste[position]
            comparaisons += 1
            doit_decaler = precedente > valeur
            etapes.append(_etape(
                liste, "comparaison",
                f"{precedente} {'>' if doit_decaler else '<='} {valeur} : "
                f"{'la valeur doit être décalée' if doit_decaler else 'la clé peut être insérée après cette valeur'}.",
                4, comparaisons, 0, deplacements, (position, indice),
                (precedente, valeur), avant, valeur,
                details={"prefixe_trie": (0, indice - 1)} if indice > 0 else {},
            ))
            if not doit_decaler:
                break

            liste[position + 1] = precedente
            deplacements += 1
            etapes.append(_etape(
                liste, "deplacement",
                f"{precedente} est décalé de la position {position} à la position {position + 1} ; "
                f"la clé {valeur} reste en mémoire temporaire.",
                5, comparaisons, 0, deplacements, (position, position + 1),
                (precedente, valeur), avant, valeur,
                details={"prefixe_trie": (0, indice - 1)} if indice > 0 else {},
            ))
            position -= 1

        avant = liste.copy()
        destination = position + 1
        liste[destination] = valeur
        deplacements += 1
        etapes.append(_etape(
            liste, "insertion",
            f"La clé {valeur} est insérée en position {destination}.",
            6, comparaisons, 0, deplacements, (destination,), (valeur,),
            avant, details={"prefixe_trie": (0, indice)},
        ))

    etapes.append(_terminee(liste, comparaisons, 0, deplacements, 7))
    return etapes


def tri_fusion(nombres: list[int]) -> list[dict[str, Any]]:
    liste = nombres.copy()
    etapes = [_initiale(liste)]
    comparaisons = deplacements = 0

    def trier_segment(gauche: int, droite: int, profondeur: int) -> None:
        nonlocal comparaisons, deplacements
        if gauche >= droite:
            etapes.append(_etape(
                liste, "base", f"Le sous-tableau [{gauche}..{droite}] contient au plus une valeur : il est déjà trié.",
                2, comparaisons, 0, deplacements, (gauche,) if gauche == droite else None,
                details={"zone_active": (gauche, droite), "profondeur": profondeur},
            ))
            return

        milieu = (gauche + droite) // 2
        etapes.append(_etape(
            liste, "division",
            f"Le segment [{gauche}..{droite}] est divisé en [{gauche}..{milieu}] et [{milieu + 1}..{droite}].",
            3, comparaisons, 0, deplacements,
            details={
                "zone_active": (gauche, droite),
                "zones": ((gauche, milieu, "gauche"), (milieu + 1, droite, "droite")),
                "profondeur": profondeur,
            },
        ))
        etapes.append(_etape(
            liste, "recursion", f"On trie récursivement la moitié gauche [{gauche}..{milieu}].",
            4, comparaisons, 0, deplacements,
            details={"zone_active": (gauche, milieu), "profondeur": profondeur + 1},
        ))
        trier_segment(gauche, milieu, profondeur + 1)
        etapes.append(_etape(
            liste, "recursion", f"On trie récursivement la moitié droite [{milieu + 1}..{droite}].",
            5, comparaisons, 0, deplacements,
            details={"zone_active": (milieu + 1, droite), "profondeur": profondeur + 1},
        ))
        trier_segment(milieu + 1, droite, profondeur + 1)

        tampon_gauche = liste[gauche:milieu + 1]
        tampon_droit = liste[milieu + 1:droite + 1]
        etapes.append(_etape(
            liste, "fusion",
            "Les deux sous-tableaux triés sont copiés dans des tampons pour être fusionnés sans perdre de valeur.",
            6, comparaisons, 0, deplacements,
            details={
                "zone_active": (gauche, droite),
                "zones": ((gauche, milieu, "gauche"), (milieu + 1, droite, "droite")),
                "tampon": [],
                "tampon_gauche": tampon_gauche.copy(),
                "tampon_droit": tampon_droit.copy(),
                "curseur_gauche": 0,
                "curseur_droit": 0,
                "destination": gauche,
                "profondeur": profondeur,
            },
        ))

        fusion: list[int] = []
        indice_gauche = indice_droit = 0
        while indice_gauche < len(tampon_gauche) and indice_droit < len(tampon_droit):
            index_a = gauche + indice_gauche
            index_b = milieu + 1 + indice_droit
            valeur_a, valeur_b = tampon_gauche[indice_gauche], tampon_droit[indice_droit]
            comparaisons += 1
            choisir_gauche = valeur_a <= valeur_b
            etapes.append(_etape(
                liste, "comparaison",
                f"{valeur_a} {'<=' if choisir_gauche else '>'} {valeur_b} : "
                f"on prend {'la valeur de gauche' if choisir_gauche else 'la valeur de droite'} en premier.",
                7, comparaisons, 0, deplacements, (index_a, index_b),
                (valeur_a, valeur_b), liste,
                details={
                    "zone_active": (gauche, droite),
                    "zones": ((gauche, milieu, "gauche"), (milieu + 1, droite, "droite")),
                    "tampon": fusion.copy(),
                    "tampon_gauche": tampon_gauche.copy(),
                    "tampon_droit": tampon_droit.copy(),
                    "curseur_gauche": indice_gauche,
                    "curseur_droit": indice_droit,
                    "destination": gauche + len(fusion),
                    "profondeur": profondeur,
                },
            ))
            if choisir_gauche:
                valeur, source = valeur_a, index_a
                indice_gauche += 1
            else:
                valeur, source = valeur_b, index_b
                indice_droit += 1
            fusion.append(valeur)
            deplacements += 1
            etapes.append(_etape(
                liste, "placement",
                f"La valeur {valeur} de la position {source} est écrite dans le tampon, à la place {gauche + len(fusion) - 1}.",
                8, comparaisons, 0, deplacements, (source,), (valeur,), liste,
                details={
                    "zone_active": (gauche, droite),
                    "zones": ((gauche, milieu, "gauche"), (milieu + 1, droite, "droite")),
                    "destination": gauche + len(fusion) - 1,
                    "destination_suivante": gauche + len(fusion),
                    "tampon": fusion.copy(),
                    "tampon_gauche": tampon_gauche.copy(),
                    "tampon_droit": tampon_droit.copy(),
                    "curseur_gauche": indice_gauche,
                    "curseur_droit": indice_droit,
                    "source": source,
                    "profondeur": profondeur,
                },
            ))

        while indice_gauche < len(tampon_gauche):
            valeur = tampon_gauche[indice_gauche]
            source = gauche + indice_gauche
            indice_gauche += 1
            fusion.append(valeur)
            deplacements += 1
            etapes.append(_etape(
                liste, "placement",
                f"La valeur restante {valeur} de la moitié gauche est copiée dans le tampon.",
                9, comparaisons, 0, deplacements, (source,), (valeur,), liste,
                details={
                    "zone_active": (gauche, droite),
                    "zones": ((gauche, milieu, "gauche"), (milieu + 1, droite, "droite")),
                    "tampon": fusion.copy(),
                    "tampon_gauche": tampon_gauche.copy(),
                    "tampon_droit": tampon_droit.copy(),
                    "curseur_gauche": indice_gauche,
                    "curseur_droit": indice_droit,
                    "destination": gauche + len(fusion) - 1,
                    "destination_suivante": gauche + len(fusion),
                    "source": source,
                    "profondeur": profondeur,
                },
            ))
        while indice_droit < len(tampon_droit):
            valeur = tampon_droit[indice_droit]
            source = milieu + 1 + indice_droit
            indice_droit += 1
            fusion.append(valeur)
            deplacements += 1
            etapes.append(_etape(
                liste, "placement",
                f"La valeur restante {valeur} de la moitié droite est copiée dans le tampon.",
                9, comparaisons, 0, deplacements, (source,), (valeur,), liste,
                details={
                    "zone_active": (gauche, droite),
                    "zones": ((gauche, milieu, "gauche"), (milieu + 1, droite, "droite")),
                    "tampon": fusion.copy(),
                    "tampon_gauche": tampon_gauche.copy(),
                    "tampon_droit": tampon_droit.copy(),
                    "curseur_gauche": indice_gauche,
                    "curseur_droit": indice_droit,
                    "destination": gauche + len(fusion) - 1,
                    "destination_suivante": gauche + len(fusion),
                    "source": source,
                    "profondeur": profondeur,
                },
            ))

        for decalage, valeur in enumerate(fusion):
            indice = gauche + decalage
            avant = liste.copy()
            liste[indice] = valeur
            deplacements += 1
            etapes.append(_etape(
                liste, "ecriture",
                f"La valeur {valeur} du tampon est recopiée à la position {indice} du tableau.",
                10, comparaisons, 0, deplacements, (indice,), (valeur,), avant,
                details={
                    "zone_active": (gauche, droite),
                    "tampon": fusion.copy(),
                    "tampon_gauche": tampon_gauche.copy(),
                    "tampon_droit": tampon_droit.copy(),
                    "destination": indice,
                    "destination_suivante": indice + 1,
                    "profondeur": profondeur,
                },
            ))

    if liste:
        trier_segment(0, len(liste) - 1, 0)
    etapes.append(_terminee(liste, comparaisons, 0, deplacements, 11))
    return etapes


def tri_rapide(nombres: list[int]) -> list[dict[str, Any]]:
    liste = nombres.copy()
    identites = list(range(len(liste)))
    etapes = [_initiale(liste)]
    comparaisons = echanges = 0

    def enregistrer_echange(
        premier: int, second: int, pivot_identite: int, gauche: int,
        droite: int, moins: int, courant: int, plus: int, ligne: int,
        pivot_index: int,
    ) -> int:
        nonlocal echanges
        avant = liste.copy()
        valeur_a, valeur_b = liste[premier], liste[second]
        liste[premier], liste[second] = valeur_b, valeur_a
        identites[premier], identites[second] = identites[second], identites[premier]
        echanges += 1
        if premier == pivot_index:
            pivot_index = second
        elif second == pivot_index:
            pivot_index = premier
        etapes.append(_etape(
            liste, "echange",
            f"{valeur_a} et {valeur_b} sont échangés pour les placer dans leur zone de partition.",
            ligne, comparaisons, echanges, 0, (premier, second),
            (valeur_a, valeur_b), avant,
            details={
                "zone_active": (gauche, droite),
                "pivot_value": liste[pivot_index],
                "pivot_index": pivot_index,
                "partition": (moins, courant, plus),
            },
        ))
        return pivot_index

    def trier_segment(gauche: int, droite: int, profondeur: int) -> None:
        nonlocal comparaisons
        if gauche > droite:
            etapes.append(_etape(
                liste, "base", f"Le sous-tableau [{gauche}..{droite}] est vide : il n'y a rien à trier.",
                2, comparaisons, echanges, 0,
                details={"zone_active": (gauche, droite), "profondeur": profondeur},
            ))
            return
        if gauche == droite:
            etapes.append(_etape(
                liste, "base", f"La valeur en position {gauche} forme un sous-tableau déjà trié.",
                2, comparaisons, echanges, 0, (gauche,), (liste[gauche],),
                details={"zone_active": (gauche, droite), "profondeur": profondeur},
            ))
            return

        pivot_index = (gauche + droite) // 2
        pivot_value = liste[pivot_index]
        pivot_identite = identites[pivot_index]
        etapes.append(_etape(
            liste, "pivot", f"La valeur {pivot_value}, au milieu du segment, est choisie comme pivot.",
            3, comparaisons, echanges, 0, (pivot_index,), (pivot_value,),
            details={
                "zone_active": (gauche, droite), "pivot_value": pivot_value,
                "pivot_index": pivot_index, "profondeur": profondeur,
            },
        ))

        moins = courant = gauche
        plus = droite
        etapes.append(_etape(
            liste, "partition", f"On parcourt [{gauche}..{droite}] en séparant les valeurs inférieures, égales et supérieures à {pivot_value}.",
            4, comparaisons, echanges, 0,
            details={
                "zone_active": (gauche, droite), "pivot_value": pivot_value,
                "pivot_index": pivot_index, "partition": (moins, courant, plus),
                "profondeur": profondeur,
            },
        ))

        while courant <= plus:
            valeur = liste[courant]
            comparaisons += 1
            est_inferieure = valeur < pivot_value
            etapes.append(_etape(
                liste, "comparaison",
                f"{valeur} {'<' if est_inferieure else '>='} {pivot_value} : "
                f"{'la valeur rejoint la zone gauche' if est_inferieure else 'elle reste à classer'}.",
                5, comparaisons, echanges, 0, (courant, pivot_index),
                (valeur, pivot_value), liste,
                details={
                    "zone_active": (gauche, droite), "pivot_value": pivot_value,
                    "pivot_index": pivot_index, "partition": (moins, courant, plus),
                    "profondeur": profondeur,
                },
            ))
            if est_inferieure:
                if courant != moins:
                    pivot_index = enregistrer_echange(
                        courant, moins, pivot_identite, gauche, droite,
                        moins, courant, plus, 6, pivot_index,
                    )
                else:
                    etapes.append(_etape(
                        liste, "decision", f"{valeur} est déjà à la frontière de la zone inférieure au pivot.",
                        6, comparaisons, echanges, 0, (courant,), (valeur,),
                        details={"zone_active": (gauche, droite), "pivot_value": pivot_value,
                                 "pivot_index": pivot_index,
                                 "partition": (moins, courant, plus), "profondeur": profondeur},
                    ))
                moins += 1
                courant += 1
                continue

            comparaisons += 1
            est_superieure = valeur > pivot_value
            etapes.append(_etape(
                liste, "comparaison",
                f"{valeur} {'>' if est_superieure else '=='} {pivot_value} : "
                f"{'la valeur rejoint la zone droite' if est_superieure else 'elle rejoint la zone égale'}.",
                5, comparaisons, echanges, 0, (courant, pivot_index),
                (valeur, pivot_value), liste,
                details={
                    "zone_active": (gauche, droite), "pivot_value": pivot_value,
                    "pivot_index": pivot_index, "partition": (moins, courant, plus),
                    "profondeur": profondeur,
                },
            ))
            if est_superieure:
                if courant != plus:
                    pivot_index = enregistrer_echange(
                        courant, plus, pivot_identite, gauche, droite,
                        moins, courant, plus, 7, pivot_index,
                    )
                else:
                    etapes.append(_etape(
                        liste, "decision", f"{valeur} est déjà à la frontière de la zone supérieure au pivot.",
                        7, comparaisons, echanges, 0, (courant,), (valeur,),
                        details={"zone_active": (gauche, droite), "pivot_value": pivot_value,
                                 "pivot_index": pivot_index,
                                 "partition": (moins, courant, plus), "profondeur": profondeur},
                    ))
                plus -= 1
            else:
                etapes.append(_etape(
                    liste, "decision", f"{valeur} est égale au pivot et reste dans la zone centrale.",
                    8, comparaisons, echanges, 0, (courant,), (valeur,),
                    details={"zone_active": (gauche, droite), "pivot_value": pivot_value,
                             "pivot_index": pivot_index,
                             "partition": (moins, courant, plus), "profondeur": profondeur},
                ))
                courant += 1

        etapes.append(_etape(
            liste, "partition", f"Partition terminée : positions {gauche} à {moins - 1} < {pivot_value}, "
            f"{moins} à {plus} = {pivot_value}, et {plus + 1} à {droite} > {pivot_value}.",
            9, comparaisons, echanges, 0,
            details={
                "zone_active": (gauche, droite), "pivot_value": pivot_value,
                "pivot_index": pivot_index,
                "zones": ((gauche, moins - 1, "gauche"), (moins, plus, "pivot"),
                          (plus + 1, droite, "droite")),
                "profondeur": profondeur,
            },
        ))

        etapes.append(_etape(
            liste, "recursion", f"On trie la zone inférieure [{gauche}..{moins - 1}].",
            10, comparaisons, echanges, 0,
            details={"zone_active": (gauche, moins - 1), "profondeur": profondeur + 1},
        ))
        trier_segment(gauche, moins - 1, profondeur + 1)
        etapes.append(_etape(
            liste, "recursion", f"On trie la zone supérieure [{plus + 1}..{droite}].",
            11, comparaisons, echanges, 0,
            details={"zone_active": (plus + 1, droite), "profondeur": profondeur + 1},
        ))
        trier_segment(plus + 1, droite, profondeur + 1)

    if liste:
        trier_segment(0, len(liste) - 1, 0)
    etapes.append(_terminee(liste, comparaisons, echanges, 0, 12))
    return etapes


def tri_par_tas(nombres: list[int]) -> list[dict[str, Any]]:
    liste = nombres.copy()
    taille = len(liste)
    etapes = [_initiale(liste)]
    comparaisons = echanges = 0

    def details_tas(
        taille_tas: int, phase: str, heap_valid: bool = False,
    ) -> dict[str, Any]:
        return {
            "heap_size": taille_tas,
            "zone_active": (0, taille_tas - 1),
            "zone_triee": (taille_tas, taille - 1),
            "phase_tas": phase,
            "heap_valid": heap_valid,
        }

    def tamiser(racine: int, taille_tas: int, ligne_appel: int, phase: str) -> None:
        nonlocal comparaisons, echanges
        while True:
            plus_grand = racine
            gauche = 2 * racine + 1
            droite = gauche + 1

            if gauche < taille_tas:
                avant = liste.copy()
                parent, enfant = liste[plus_grand], liste[gauche]
                comparaisons += 1
                choisir_enfant = enfant > parent
                etapes.append(_etape(
                    liste, "comparaison",
                    f"L'enfant gauche {enfant} {'>' if choisir_enfant else '<='} au parent {parent}.",
                    3, comparaisons, echanges, 0, (plus_grand, gauche),
                    (parent, enfant), avant,
                    details={**details_tas(taille_tas, phase), "racine": racine},
                ))
                if choisir_enfant:
                    plus_grand = gauche

            if droite < taille_tas:
                avant = liste.copy()
                parent, enfant = liste[plus_grand], liste[droite]
                comparaisons += 1
                choisir_enfant = enfant > parent
                etapes.append(_etape(
                    liste, "comparaison",
                    f"L'enfant droit {enfant} {'>' if choisir_enfant else '<='} au plus grand candidat {parent}.",
                    4, comparaisons, echanges, 0, (plus_grand, droite),
                    (parent, enfant), avant,
                    details={**details_tas(taille_tas, phase), "racine": racine},
                ))
                if choisir_enfant:
                    plus_grand = droite

            if plus_grand == racine:
                etapes.append(_etape(
                    liste, "decision",
                    f"La valeur {liste[racine]} est déjà supérieure ou égale à ses enfants : le max-heap est respecté ici.",
                    ligne_appel, comparaisons, echanges, 0, (racine,),
                    (liste[racine],), details={**details_tas(taille_tas, phase), "racine": racine},
                ))
                return

            avant = liste.copy()
            valeur_racine, valeur_enfant = liste[racine], liste[plus_grand]
            liste[racine], liste[plus_grand] = valeur_enfant, valeur_racine
            echanges += 1
            etapes.append(_etape(
                liste, "echange",
                f"{valeur_enfant}, le plus grand des trois éléments, remonte à la position {racine}.",
                5, comparaisons, echanges, 0, (racine, plus_grand),
                (valeur_racine, valeur_enfant), avant,
                details={**details_tas(taille_tas, phase), "racine": racine},
            ))
            racine = plus_grand

    if taille:
        etapes.append(_etape(
            liste, "construction_tas", "On commence la construction d'un max-heap à partir des derniers nœuds parents.",
            1, comparaisons, echanges, 0,
            details=details_tas(taille, "construction"),
        ))
        for parent in range(taille // 2 - 1, -1, -1):
            etapes.append(_etape(
                liste, "tas", f"On rétablit la propriété de tas depuis le parent en position {parent}.",
                2, comparaisons, echanges, 0, (parent,), (liste[parent],),
                details={**details_tas(taille, "construction"), "racine": parent},
            ))
            tamiser(parent, taille, 2, "construction")
            if parent == 0:
                etapes[-1]["details"]["heap_valid"] = True

        if taille == 1:
            etapes[-1]["details"]["heap_valid"] = True

        for fin in range(taille - 1, 0, -1):
            avant = liste.copy()
            maximum, dernier = liste[0], liste[fin]
            liste[0], liste[fin] = dernier, maximum
            echanges += 1
            etapes.append(_etape(
                liste, "echange",
                f"Le maximum {maximum}, à la racine, est échangé avec la dernière valeur {dernier} de la zone active.",
                6, comparaisons, echanges, 0, (0, fin), (maximum, dernier), avant,
                details={**details_tas(fin, "extraction"), "maximum_place": fin},
            ))
            etapes.append(_etape(
                liste, "reduction_tas",
                f"La position {fin} est maintenant triée ; la taille du tas actif passe de {fin + 1} à {fin}.",
                7, comparaisons, echanges, 0, (fin,), (maximum,),
                details={**details_tas(fin, "extraction"), "maximum_place": fin},
            ))
            etapes.append(_etape(
                liste, "tas", "On rétablit le max-heap depuis sa nouvelle racine.",
                8, comparaisons, echanges, 0, (0,), (liste[0],),
                details={**details_tas(fin, "extraction"), "racine": 0},
            ))
            tamiser(0, fin, 8, "extraction")
            etapes[-1]["details"]["heap_valid"] = True

    etapes.append(_terminee(liste, comparaisons, echanges, 0, 9))
    return etapes


ALGORITHMES = {
    "Tri à bulles": tri_a_bulles,
    "Tri par sélection": tri_par_selection,
    "Tri par insertion": tri_par_insertion,
    "Tri fusion": tri_fusion,
    "Tri rapide": tri_rapide,
    "Tri par tas": tri_par_tas,
}


def calculer_statistiques(nom: str, nombres: list[int]) -> dict[str, Any]:
    """Trie sans historique et renvoie les mêmes compteurs que les moteurs visuels."""
    liste = nombres.copy()
    comparaisons = echanges = deplacements = 0

    if nom == "Tri à bulles":
        for passage in range(len(liste) - 1):
            echange_pendant_passage = False
            for indice in range(len(liste) - passage - 1):
                comparaisons += 1
                if liste[indice] > liste[indice + 1]:
                    liste[indice], liste[indice + 1] = liste[indice + 1], liste[indice]
                    echanges += 1
                    echange_pendant_passage = True
            if not echange_pendant_passage:
                break
    elif nom == "Tri par sélection":
        for debut in range(len(liste) - 1):
            indice_min = debut
            for indice in range(debut + 1, len(liste)):
                comparaisons += 1
                if liste[indice] < liste[indice_min]:
                    indice_min = indice
            if indice_min != debut:
                liste[debut], liste[indice_min] = liste[indice_min], liste[debut]
                echanges += 1
    elif nom == "Tri par insertion":
        for indice in range(1, len(liste)):
            valeur = liste[indice]
            position = indice - 1
            while position >= 0:
                comparaisons += 1
                if liste[position] <= valeur:
                    break
                liste[position + 1] = liste[position]
                deplacements += 1
                position -= 1
            liste[position + 1] = valeur
            deplacements += 1
    elif nom == "Tri fusion":
        def fusionner(gauche: int, droite: int) -> None:
            nonlocal comparaisons, deplacements
            if droite - gauche < 1:
                return
            milieu = (gauche + droite) // 2
            fusionner(gauche, milieu)
            fusionner(milieu + 1, droite)
            tampon_gauche = liste[gauche:milieu + 1]
            tampon_droit = liste[milieu + 1:droite + 1]
            fusion = []
            indice_gauche = indice_droit = 0
            while indice_gauche < len(tampon_gauche) and indice_droit < len(tampon_droit):
                comparaisons += 1
                if tampon_gauche[indice_gauche] <= tampon_droit[indice_droit]:
                    fusion.append(tampon_gauche[indice_gauche])
                    indice_gauche += 1
                else:
                    fusion.append(tampon_droit[indice_droit])
                    indice_droit += 1
                deplacements += 1
            while indice_gauche < len(tampon_gauche):
                fusion.append(tampon_gauche[indice_gauche])
                indice_gauche += 1
                deplacements += 1
            while indice_droit < len(tampon_droit):
                fusion.append(tampon_droit[indice_droit])
                indice_droit += 1
                deplacements += 1
            liste[gauche:droite + 1] = fusion
            deplacements += len(fusion)

        if liste:
            fusionner(0, len(liste) - 1)
    elif nom == "Tri rapide":
        def partitionner(gauche: int, droite: int) -> None:
            nonlocal comparaisons, echanges
            if gauche >= droite:
                return
            pivot = liste[(gauche + droite) // 2]
            moins = courant = gauche
            plus = droite
            while courant <= plus:
                comparaisons += 1
                if liste[courant] < pivot:
                    if courant != moins:
                        liste[courant], liste[moins] = liste[moins], liste[courant]
                        echanges += 1
                    moins += 1
                    courant += 1
                    continue
                comparaisons += 1
                if liste[courant] > pivot:
                    if courant != plus:
                        liste[courant], liste[plus] = liste[plus], liste[courant]
                        echanges += 1
                    plus -= 1
                else:
                    courant += 1
            partitionner(gauche, moins - 1)
            partitionner(plus + 1, droite)

        if liste:
            partitionner(0, len(liste) - 1)
    elif nom == "Tri par tas":
        def tamiser(racine: int, taille_tas: int) -> None:
            nonlocal comparaisons, echanges
            while True:
                plus_grand = racine
                gauche = 2 * racine + 1
                droite = gauche + 1
                if gauche < taille_tas:
                    comparaisons += 1
                    if liste[gauche] > liste[plus_grand]:
                        plus_grand = gauche
                if droite < taille_tas:
                    comparaisons += 1
                    if liste[droite] > liste[plus_grand]:
                        plus_grand = droite
                if plus_grand == racine:
                    return
                liste[racine], liste[plus_grand] = liste[plus_grand], liste[racine]
                echanges += 1
                racine = plus_grand

        taille_tas = len(liste)
        for parent in range(taille_tas // 2 - 1, -1, -1):
            tamiser(parent, taille_tas)
        for fin in range(taille_tas - 1, 0, -1):
            liste[0], liste[fin] = liste[fin], liste[0]
            echanges += 1
            tamiser(0, fin)
    else:
        raise ValueError(f"Algorithme inconnu : {nom}")

    return {
        "liste": liste,
        "comparaisons": comparaisons,
        "echanges": echanges,
        "deplacements": deplacements,
        "operations": echanges + deplacements,
    }