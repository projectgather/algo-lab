from algorithmes.entrainement import (
    creer_session_entrainement,
    passer_question_suivante,
    statistiques_session_entrainement,
    valider_reponse_entrainement,
)
from algorithmes.tri import ALGORITHMES


def test_prediction_attendue_correspond_a_la_trace_et_reponses_sont_verifiables():
    for nom in ALGORITHMES:
        session = creer_session_entrainement(seed=list(ALGORITHMES).index(nom) + 15)
        question = session["questions"][0]
        assert question["nom_algorithme"] in ALGORITHMES
        assert question["type"] == "prediction_entrainement"
        assert question["reponse_attendue"] == question["apres"]
        assert question["historique"][question["index_etape"]]["apres"] == question["apres"]
        assert question["reponse_attendue"] in question["choix"]


def test_reponse_incorrecte_est_finalisee_et_la_double_validation_est_sans_effet():
    session = creer_session_entrainement(nombre_questions=2, seed=31)
    question = session["questions"][0]
    mauvaise = next(choix for choix in question["choix"] if choix != question["reponse_attendue"])

    assert valider_reponse_entrainement(question, mauvaise) == "incorrecte"
    assert question["resolue"] and not question["correcte"]
    assert question["tentatives"] == 1
    assert question["reponses"] == [mauvaise]
    assert valider_reponse_entrainement(question, question["reponse_attendue"]) == "deja_validee"
    assert question["tentatives"] == 1
    assert passer_question_suivante(session)


def test_reussite_alterne_les_formats_et_erreur_propose_une_nouvelle_prediction():
    session = creer_session_entrainement(nombre_questions=3, seed=8)
    premiere = session["questions"][0]
    assert valider_reponse_entrainement(premiere, premiere["reponse_attendue"]) == "correcte"
    assert passer_question_suivante(session)
    assert session["questions"][1]["type"] == "choix_algorithme_entrainement"

    seconde = session["questions"][1]
    assert valider_reponse_entrainement(seconde, "Tri à bulles") == "incorrecte"
    assert passer_question_suivante(session)
    assert session["questions"][2]["type"] == "choix_algorithme_entrainement"
    assert not passer_question_suivante(session)


def test_bilan_compte_les_reussites_et_notions_a_retravailler():
    session = creer_session_entrainement(nombre_questions=2, seed=17)
    premiere = session["questions"][0]
    valider_reponse_entrainement(premiere, premiere["reponse_attendue"])
    passer_question_suivante(session)
    seconde = session["questions"][1]
    valider_reponse_entrainement(seconde, "Tri à bulles")

    bilan = statistiques_session_entrainement(session)
    assert bilan == {
        "terminees": 2,
        "reussies": 1,
        "score": 100,
        "notions_a_retravailler": [seconde["notion"]],
        "pourcentage": 50,
    }


def test_session_se_termine_une_fois_apres_la_derniere_reponse():
    session = creer_session_entrainement(nombre_questions=1, seed=23)
    question = session["questions"][0]
    assert not passer_question_suivante(session)
    valider_reponse_entrainement(question, question["reponse_attendue"])

    assert passer_question_suivante(session)
    assert session["terminee"]
    assert not passer_question_suivante(session)


def test_recommandation_peut_cibler_une_notion_de_complexite():
    session = creer_session_entrainement(
        nombre_questions=1,
        seed=19,
        type_question_initial="choix_algorithme_entrainement",
        notion_initiale="Mémoire auxiliaire et pire cas",
    )

    assert session["questions"][0]["type"] == "choix_algorithme_entrainement"
    assert session["questions"][0]["notion"] == "Mémoire auxiliaire et pire cas"