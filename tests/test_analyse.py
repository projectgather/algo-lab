import pytest

from algorithmes.analyse import analyser_differences_distributions, analyser_mesures


def _ligne(nom, **mesures):
    return {
        "Algorithme": nom,
        "Distribution": "Aléatoires",
        "Taille": 100,
        "Graine": 7,
        **mesures,
    }


@pytest.mark.parametrize(
    ("critere", "valeurs", "gagnant"),
    [
        ("Comparaisons", (8, 3, 5), "B"),
        ("Opérations", (9, 2, 6), "B"),
        ("Autres opérations", (7, 1, 4), "B"),
        ("Total des compteurs", (12, 10, 20), "B"),
        ("Temps médian (ms)", (3.2, 1.1, 2.4), "B"),
    ],
)
def test_detecte_le_minimum_de_chaque_critere(critere, valeurs, gagnant):
    lignes = [_ligne(nom, **{critere: valeur}) for nom, valeur in zip("ABC", valeurs)]

    analyse = analyser_mesures(lignes)[0]["criteres"][critere]

    assert analyse["gagnants"] == [gagnant]
    assert analyse["minimum"] == min(valeurs)


def test_signale_les_egalites_sans_creer_un_classement_arbitraire():
    analyse = analyser_mesures([
        _ligne("A", **{"Comparaisons": 4}),
        _ligne("B", **{"Comparaisons": 4}),
        _ligne("C", **{"Comparaisons": 8}),
    ])[0]["criteres"]["Comparaisons"]

    assert analyse["gagnants"] == ["A", "B"]
    assert analyse["egalite"]


def test_ecarts_absolus_et_pourcentages_sont_references_au_minimum():
    analyse = analyser_mesures([
        _ligne("A", **{"Comparaisons": 20}),
        _ligne("B", **{"Comparaisons": 10}),
    ])[0]["criteres"]["Comparaisons"]

    details = {ligne["algorithme"]: ligne for ligne in analyse["details"]}
    assert details["A"]["ecart_absolu"] == 10
    assert details["A"]["ecart_pourcent"] == 100
    assert details["B"]["ecart_absolu"] == 0
    assert details["B"]["ecart_pourcent"] == 0


def test_valeurs_nulles_absentes_et_zero_ne_provoquent_pas_de_division_par_zero():
    analyses = analyser_mesures([
        _ligne("A", **{"Temps médian (ms)": 0}),
        _ligne("B", **{"Temps médian (ms)": 1}),
        _ligne("C", **{"Temps médian (ms)": None}),
    ])
    temps = analyses[0]["criteres"]["Temps médian (ms)"]

    assert temps["gagnants"] == ["A"]
    assert temps["details"][0]["ecart_pourcent"] is None
    assert temps["nombre_disponible"] == 2
    assert temps["nombre_total"] == 3


def test_analyses_separement_tailles_distributions_et_protocoles():
    lignes = [
        _ligne("A", **{"Comparaisons": 4}),
        {**_ligne("B", **{"Comparaisons": 2}), "Taille": 200},
        {**_ligne("C", **{"Comparaisons": 3}), "Distribution": "Déjà triées"},
        {**_ligne("D", **{"Comparaisons": 5}), "Graine": 8},
    ]

    analyses = analyser_mesures(lignes)

    assert len(analyses) == 4
    assert {(a["distribution"], a["taille"], a["graine"]) for a in analyses} == {
        ("Aléatoires", 100, 7), ("Aléatoires", 200, 7),
        ("Déjà triées", 100, 7), ("Aléatoires", 100, 8),
    }
    assert all(
        not analyse["criteres"]["Comparaisons"]["disponible"]
        for analyse in analyses
    )


def test_un_seul_algorithme_ne_peut_pas_etre_declare_minimum():
    resultat = analyser_mesures([
        _ligne("A", **{"Comparaisons": 0}),
    ])[0]["criteres"]["Comparaisons"]

    assert not resultat["disponible"]
    assert "Une seule valeur" in resultat["raison"]


def test_mesure_non_collectee_est_signalee_explicitement():
    criteres = analyser_mesures([
        _ligne("A", **{"Comparaisons": 2}),
        _ligne("B", **{"Comparaisons": 3}),
    ])[0]["criteres"]

    assert not criteres["Temps médian (ms)"]["disponible"]
    assert "n'a pas été collectée" in criteres["Temps médian (ms)"]["raison"]


def test_refuse_mesures_sans_contexte_ou_dupliquees():
    with pytest.raises(ValueError, match="distribution et sa taille"):
        analyser_mesures([{"Algorithme": "A", "Taille": 10}])
    with pytest.raises(ValueError, match="qu'une fois"):
        analyser_mesures([_ligne("A"), _ligne("A")])


def test_compare_les_distributions_a_taille_et_algorithme_identiques():
    lignes = [
        _ligne("Tri insertion", **{"Comparaisons": 40}),
        {**_ligne("Tri insertion", **{"Comparaisons": 10}), "Distribution": "Déjà triées"},
        {**_ligne("Tri fusion", **{"Comparaisons": 15}), "Taille": 200},
    ]

    differences = analyser_differences_distributions(lignes)

    assert len(differences) == 1
    comparaison = differences[0]["criteres"]["Comparaisons"]
    assert comparaison["gagnants"] == ["Déjà triées"]
    insertion = {detail["algorithme"]: detail for detail in comparaison["details"]}
    assert insertion["Aléatoires"]["ecart_absolu"] == 30
    assert insertion["Aléatoires"]["ecart_pourcent"] == 300