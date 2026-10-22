import pytest

from algorithmes.manipulation import (
    INTERVALLES_TAILLE,
    creer_partie,
    utiliser_indice,
    valider_action,
    verifier_reussite,
)


def _valider(partie, action, **reponse):
    return valider_action(partie, action, reponse)


def _terminer_insertion(partie):
    while not partie["completee"]:
        phase = partie["phase"]
        if phase == "choisir_cle":
            _valider(partie, phase, indice=partie["index"])
        elif phase == "comparer":
            _valider(partie, phase, indice=partie["curseur"])
        elif phase == "deplacer":
            _valider(partie, phase, source=partie["curseur"], destination=partie["curseur"] + 1)
        else:
            _valider(partie, phase, destination=partie["curseur"] + 1)


def _terminer_selection(partie):
    while not partie["completee"]:
        phase = partie["phase"]
        if phase == "comparer":
            _valider(partie, phase, indice=partie["curseur"])
        elif phase == "choisir_minimum":
            _valider(partie, phase, indice=partie["minimum"])
        elif phase == "echanger":
            _valider(partie, phase, source=partie["index"], destination=partie["minimum"])
        else:
            _valider(partie, phase)


@pytest.mark.parametrize("entree", ([4, 1, 3, 2], [1, 2, 3, 4], [4, 3, 2, 1], [3, 1, 1, 2]))
def test_insertion_termine_en_respectant_cles_decalages_et_doublons(entree):
    partie = creer_partie("Tri par insertion", "Facile", len(entree), nombres=list(entree))

    _terminer_insertion(partie)

    assert partie["tableau"] == sorted(entree)
    assert partie["reussite"]
    assert partie["etapes"] > 0


def test_insertion_refuse_indices_invalides_sans_mutation_et_progression():
    partie = creer_partie("Tri par insertion", "Facile", 4, nombres=[4, 1, 3, 2])
    tableau_initial = partie["tableau"].copy()

    assert _valider(partie, "choisir_cle", indice=0) == "incorrecte"
    assert partie["tableau"] == tableau_initial
    assert partie["index"] == 1
    assert _valider(partie, "choisir_cle", indice=1) == "correcte"
    assert partie["tableau"] == [4, None, 3, 2]
    assert _valider(partie, "comparer", indice=1) == "incorrecte"
    assert partie["curseur"] == 0
    assert _valider(partie, "comparer", indice=0) == "correcte"
    assert _valider(partie, "deplacer", source=0, destination=3) == "incorrecte"
    assert partie["tableau"] == [4, None, 3, 2]
    assert _valider(partie, "deplacer", source=0, destination=1) == "correcte"
    assert partie["tableau"] == [None, 4, 3, 2]
    assert partie["phase"] == "inserer"
    assert _valider(partie, "inserer", destination=1) == "incorrecte"
    assert _valider(partie, "inserer", destination=0) == "correcte"


@pytest.mark.parametrize("entree", ([4, 1, 3, 2], [1, 2, 3, 4], [4, 3, 2, 1], [3, 1, 1, 2], [7]))
def test_selection_parcourt_les_minima_et_termine(entree):
    partie = creer_partie("Tri par sélection", "Facile", len(entree), nombres=list(entree))

    _terminer_selection(partie)

    assert partie["tableau"] == sorted(entree)
    assert partie["reussite"]
    assert partie["completee"]


def test_selection_refuse_saut_minimum_et_echange_incoherent():
    partie = creer_partie("Tri par sélection", "Facile", 4, nombres=[4, 1, 3, 2])
    avant = partie["tableau"].copy()

    assert _valider(partie, "comparer", indice=2) == "incorrecte"
    assert partie["tableau"] == avant
    assert partie["curseur"] == 1
    assert _valider(partie, "comparer", indice=1) == "correcte"
    assert _valider(partie, "comparer", indice=2) == "correcte"
    assert _valider(partie, "comparer", indice=3) == "correcte"
    assert _valider(partie, "choisir_minimum", indice=2) == "incorrecte"
    assert partie["minimum"] == 1
    assert _valider(partie, "choisir_minimum", indice=1) == "correcte"
    assert _valider(partie, "echanger", source=0, destination=2) == "incorrecte"
    assert partie["tableau"] == avant
    assert _valider(partie, "echanger", source=0, destination=1) == "correcte"
    assert partie["tableau"] == [1, 4, 3, 2]


def test_difficulte_limite_taille_et_donnees_reproductibles():
    for difficulte, (minimum, maximum) in INTERVALLES_TAILLE.items():
        partie = creer_partie(difficulte=difficulte, taille=minimum, seed=12)
        assert len(partie["entree"]) == minimum
        assert partie["entree"] == creer_partie(difficulte=difficulte, taille=minimum, seed=12)["entree"]
        with pytest.raises(ValueError):
            creer_partie(difficulte=difficulte, taille=maximum + 1)


def test_distributions_aleatoire_presque_triee_et_inverse():
    aleatoire = creer_partie(taille=6, type_tableau="Aléatoire", seed=9)
    presque = creer_partie(taille=6, type_tableau="Presque trié", seed=9)
    inverse = creer_partie(taille=6, type_tableau="Ordre inverse", seed=9)

    assert len(aleatoire["entree"]) == 6
    assert presque["entree"] != list(range(1, 7))
    assert inverse["entree"] == [6, 5, 4, 3, 2, 1]


@pytest.mark.parametrize("algorithme", ("Tri par insertion", "Tri par sélection"))
def test_tableau_d_un_element_est_un_succes_trivial_rejouable(algorithme):
    partie = creer_partie(algorithme, "Facile", 1, nombres=[7])

    assert partie["completee"]
    assert partie["reussite"]
    assert verifier_reussite(partie)


def test_journal_incomplet_ne_certifie_pas_une_reussite():
    partie = creer_partie("Tri par insertion", "Facile", 4, nombres=[4, 3, 2, 1])
    partie["tableau"] = [1, 2, 3, 4]
    partie["completee"] = True
    partie["reussite"] = True

    assert not verifier_reussite(partie)


def test_indices_progressifs_sont_limites_par_difficulte_et_erreurs_escaladent():
    facile = creer_partie(difficulte="Facile", taille=4, seed=2)
    indices = [utiliser_indice(facile) for _ in range(4)]
    assert all(indices[:3])
    assert indices[3] is None
    assert facile["indices_utilises"] == 3

    _valider(facile, "choisir_cle", indice=0)
    _valider(facile, "choisir_cle", indice=0)
    _valider(facile, "choisir_cle", indice=0)
    assert "Indice :" in facile["feedback"]["texte"]


def test_fin_de_partie_refuse_le_resultat_seul_et_verifie_la_demarche():
    partie = creer_partie("Tri par insertion", "Facile", 4, nombres=[3, 1, 2, 4])
    partie["tableau"] = [1, 2, 3, 4]

    assert not partie["completee"]
    assert not partie["reussite"]
    assert _valider(partie, "inserer", destination=3) == "incorrecte"
    assert not partie["completee"]
    _terminer_insertion(partie)
    assert partie["reussite"]
    assert valider_action(partie, "inserer", {"destination": 0}) == "terminee"