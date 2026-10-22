import pytest

from algorithmes import experience
from algorithmes.experience import (
    TYPES_DONNEES,
    calculer_facteur_evolution,
    creer_tailles_experience,
    generer_donnees,
    mesurer_evolution,
    mesurer_tri,
)
from algorithmes.tri import ALGORITHMES, calculer_statistiques


@pytest.mark.parametrize("type_donnees", TYPES_DONNEES)
def test_generation_reproductible_et_taille_exacte(type_donnees):
    premiere = generer_donnees(type_donnees, 40, graine=17)
    seconde = generer_donnees(type_donnees, 40, graine=17)

    assert premiere == seconde
    assert len(premiere) == 40
    if type_donnees == "Déjà triées":
        assert premiere == sorted(premiere)
    elif type_donnees == "Triées en ordre inverse":
        assert premiere == sorted(premiere, reverse=True)


def test_mesure_mediane_repetee_hors_copie_et_entree_inchangee(monkeypatch):
    instants = iter((0, 0.001, 1, 1.004, 2, 2.002))
    monkeypatch.setattr(experience.time, "perf_counter", lambda: next(instants))
    entree = [3, 1, 2]
    appels = []

    def trier(liste):
        appels.append(liste)
        liste.sort()

    duree = mesurer_tri(trier, entree, repetitions=3)

    assert duree == pytest.approx(2)
    assert len(appels) == 3
    assert all(liste == [1, 2, 3] for liste in appels)
    assert entree == [3, 1, 2]
    assert len({id(liste) for liste in appels}) == 3


def test_mesure_evolution_chronometre_des_copies_communes_et_verifie_la_mediane(monkeypatch):
    instants = iter((0, 0.001, 1, 1.003, 2, 2.002, 3, 3.001, 4, 4.003, 5, 5.002))
    monkeypatch.setattr(experience.time, "perf_counter", lambda: next(instants))
    entree_initiale = generer_donnees("Aléatoires", 12, graine=17)
    appels = {nom: [] for nom in ("Tri à bulles", "Tri fusion")}

    def fonction_pour(nom):
        def trier(liste):
            appels[nom].append((liste, liste.copy()))
            liste.sort()
        return trier

    resultats = mesurer_evolution(
        list(appels), "Aléatoires", 12, 12, graine=17, repetitions=3,
        fonctions_tri={nom: fonction_pour(nom) for nom in appels},
    )

    assert all(ligne["Résultat correct"] for ligne in resultats)
    assert all(ligne["Temps médian (ms)"] == pytest.approx(2) for ligne in resultats)
    assert all(ligne["Répétitions"] == 3 for ligne in resultats)
    assert all(
        tableau == entree_initiale
        for observations in appels.values()
        for _, tableau in observations
    )
    assert len({id(liste) for observations in appels.values() for liste, _ in observations}) == 6


def test_mesure_mediane_refuse_un_tri_incorrect():
    with pytest.raises(RuntimeError, match="n'a pas correctement trié"):
        mesurer_tri(lambda liste: liste.clear(), [2, 1], repetitions=1)


def test_generation_et_mesure_acceptent_les_cas_limites():
    assert generer_donnees("Presque triées", 0) == []
    assert mesurer_tri(list.sort, []) >= 0
    with pytest.raises(ValueError):
        generer_donnees("Aléatoires", -1)
    with pytest.raises(ValueError):
        generer_donnees("Aléatoires", 1.5)
    with pytest.raises(ValueError):
        generer_donnees("Aléatoires", 1, graine=True)
    with pytest.raises(ValueError):
        mesurer_tri(list.sort, [1], repetitions=0)
    with pytest.raises(ValueError):
        mesurer_tri(list.sort, [1], repetitions=10)


def test_tailles_dedoublees_respectent_les_limites():
    assert creer_tailles_experience(10, 80) == [10, 20, 40, 80]
    assert creer_tailles_experience(30, 100) == [30, 60]
    with pytest.raises(ValueError):
        creer_tailles_experience(0, 100)
    with pytest.raises(ValueError):
        creer_tailles_experience(20, 10)
    with pytest.raises(ValueError):
        creer_tailles_experience(10, 501)
    with pytest.raises(ValueError):
        creer_tailles_experience(10.5, 100)


def test_facteur_evolution_gere_le_zero_et_les_compteurs_invalides():
    assert calculer_facteur_evolution(10, 40) == 4
    assert calculer_facteur_evolution(0, 40) is None
    with pytest.raises(ValueError):
        calculer_facteur_evolution(-1, 4)


def test_mesures_reproductibles_valides_et_tries():
    premiere = mesurer_evolution(
        ["Tri à bulles", "Tri fusion"], "Aléatoires", 10, 40, graine=13
    )
    seconde = mesurer_evolution(
        ["Tri à bulles", "Tri fusion"], "Aléatoires", 10, 40, graine=13
    )

    assert premiere == seconde
    assert [ligne["Taille"] for ligne in premiere[:3]] == [10, 20, 40]
    assert all(ligne["Résultat correct"] for ligne in premiere)
    assert all(
        ligne["Autres opérations"] == ligne["Échanges"] + ligne["Déplacements"]
        for ligne in premiere
    )
    assert premiere[0]["Facteur d'évolution"] is None
    assert premiere[1]["Facteur d'évolution"] == (
        premiere[1]["Total des compteurs"] / premiere[0]["Total des compteurs"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ([], "Aléatoires", 10, 20, 42),
        (["Tri inexistant"], "Aléatoires", 10, 20, 42),
        (["Tri fusion"], "Inconnues", 10, 20, 42),
    ],
)
def test_mesure_evolution_refuse_les_entrees_invalides(arguments):
    with pytest.raises(ValueError):
        mesurer_evolution(*arguments)


@pytest.mark.parametrize("repetitions", [0, 10, 1.5, True])
def test_mesure_evolution_refuse_les_repetitions_invalides(repetitions):
    with pytest.raises(ValueError):
        mesurer_evolution(
            ["Tri fusion"], "Aléatoires", 10, 10, repetitions=repetitions
        )


def test_mesure_evolution_refuse_les_algorithmes_dupliques():
    with pytest.raises(ValueError, match="qu'une fois"):
        mesurer_evolution(
            ["Tri fusion", "Tri fusion"], "Aléatoires", 10, 10
        )


def test_mesure_evolution_refuse_une_fonction_de_tri_non_appelable():
    with pytest.raises(ValueError, match="non appelable"):
        mesurer_evolution(
            ["Tri fusion"], "Aléatoires", 10, 10,
            fonctions_tri={"Tri fusion": None},
        )


def test_les_six_tris_utilisent_une_entree_commune_et_des_compteurs_coherents():
    entree = generer_donnees("Presque triées", 60, graine=9)
    entree_initiale = entree.copy()

    for nom in ALGORITHMES:
        statistiques = calculer_statistiques(nom, entree)
        assert statistiques["liste"] == sorted(entree_initiale)
        assert statistiques["operations"] == (
            statistiques["echanges"] + statistiques["deplacements"]
        )
        assert statistiques["comparaisons"] >= 0

    assert entree == entree_initiale