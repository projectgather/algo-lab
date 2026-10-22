import unittest

from algorithmes.exercices import (
    ALGORITHMES_DEBUTANT,
    TOUS_LES_ALGORITHMES,
    _format_evenement,
    algorithmes_disponibles,
    creer_session,
    reponse_correcte,
    statistiques_session,
    utiliser_indice,
    valider_reponse,
)
from algorithmes.tri import ALGORITHMES


class TestsExercices(unittest.TestCase):
    def test_difficulte_change_algorithmes_taille_et_formats(self):
        debutant = creer_session(TOUS_LES_ALGORITHMES, "Débutant", 6, seed=3)
        intermediaire = creer_session(TOUS_LES_ALGORITHMES, "Intermédiaire", 6, seed=3)
        avance = creer_session(TOUS_LES_ALGORITHMES, "Avancé", 6, seed=3)

        self.assertEqual(len(debutant["entree"]), 5)
        self.assertEqual(len(intermediaire["entree"]), 8)
        self.assertEqual(len(avance["entree"]), 10)
        self.assertEqual(set(ALGORITHMES_DEBUTANT), set(ALGORITHMES))
        self.assertEqual(set(algorithmes_disponibles("Débutant")), set(ALGORITHMES))
        self.assertEqual(
            {q["nom_algorithme"] for q in debutant["questions"]}, set(ALGORITHMES)
        )
        self.assertEqual(set(q["nom_algorithme"] for q in intermediaire["questions"]), set(ALGORITHMES))
        self.assertTrue(all(q["format"] == "choix" for q in debutant["questions"]))
        for question in debutant["questions"]:
            self.assertIn(question["reponse_attendue"], question["choix"])
            if question["type"] == "etat":
                self.assertEqual(
                    question["reponse_attendue"],
                    question["historique"][question["index_etape"]]["apres"],
                )
            else:
                historique = question["historique"]
                self.assertEqual(historique[-1]["liste"], sorted(debutant["entree"]))
                self.assertEqual(
                    question["reponse_attendue"],
                    _format_evenement(historique[question["index_suivant"]]),
                )
        self.assertTrue(any(q["format"] == "ordre" for q in intermediaire["questions"]))
        self.assertTrue(any(q["format"] == "texte" for q in avance["questions"]))

    def test_prediction_est_issue_de_levenement_suivant_reel(self):
        for nom in ALGORITHMES:
            with self.subTest(algorithme=nom):
                session = creer_session(
                    nom, "Intermédiaire", 6, seed=25,
                    nombres=[-2, 4, -2, 1, 3],
                )
                question = next(q for q in session["questions"] if q["type"] == "prediction")
                suivante = question["historique"][question["index_suivant"]]
                self.assertEqual(question["explication"], suivante["explication"])
                self.assertEqual(
                    question["index_suivant"], question["index_courant"] + 1
                )
                if question["format"] == "texte":
                    self.assertTrue(reponse_correcte(question, question["reponse_attendue"]))
                else:
                    self.assertIn(question["reponse_attendue"], question["choix"])

    def test_ordre_propose_repris_de_la_trace(self):
        session = creer_session("Tri fusion", "Intermédiaire", 6, seed=12)
        question = next(q for q in session["questions"] if q["format"] == "ordre")
        historique = question["historique"]
        labels = [
            historique[index]["action"]
            for index in question["indices_evenements"]
        ]
        self.assertEqual(len(question["indices_evenements"]), 3)
        self.assertEqual(sorted(question["indices_evenements"]), question["indices_evenements"])
        self.assertEqual(question["ordre_correct"], [
            _format_evenement(historique[index])
            for index in question["indices_evenements"]
        ])
        self.assertTrue(all(labels))

    def test_score_tentatives_doublons_et_indices(self):
        session = creer_session("Tri à bulles", "Débutant", 3, seed=4)
        premiere, seconde, troisieme = session["questions"]

        self.assertTrue(utiliser_indice(premiere))
        self.assertFalse(utiliser_indice(premiere))
        self.assertEqual(valider_reponse(premiere, premiere["reponse_attendue"]), "correcte")
        self.assertEqual(premiere["points"], 100)
        self.assertEqual(valider_reponse(premiere, premiere["reponse_attendue"]), "resolue")

        mauvaise = next(choix for choix in seconde["choix"] if choix != seconde["reponse_attendue"])
        self.assertEqual(valider_reponse(seconde, mauvaise), "nouvel_essai")
        self.assertEqual(valider_reponse(seconde, mauvaise), "doublon")
        self.assertEqual(seconde["tentatives"], 1)
        self.assertEqual(valider_reponse(seconde, seconde["reponse_attendue"]), "correcte")
        self.assertEqual(seconde["reponses"], [mauvaise, seconde["reponse_attendue"]])
        self.assertEqual(seconde["points"], 50)

        mauvaise_a = next(choix for choix in troisieme["choix"] if choix != troisieme["reponse_attendue"])
        mauvaise_b = next(choix for choix in troisieme["choix"] if choix not in (troisieme["reponse_attendue"], mauvaise_a))
        self.assertEqual(valider_reponse(troisieme, mauvaise_a), "nouvel_essai")
        self.assertEqual(valider_reponse(troisieme, mauvaise_b), "incorrecte_finale")
        self.assertEqual(troisieme["points"], 0)
        self.assertEqual(troisieme["reponses"], [mauvaise_a, mauvaise_b])
        self.assertFalse(utiliser_indice(troisieme))

        stats = statistiques_session(session)
        self.assertEqual(stats["terminees"], 3)
        self.assertEqual(stats["reussies"], 2)
        self.assertEqual(stats["premier_essai"], 1)
        self.assertEqual(stats["score"], 150)
        self.assertEqual(stats["pourcentage"], 67)
        self.assertEqual(stats["indices"], 1)

    def test_reponse_saisie_et_entree_avec_doublons_negatifs(self):
        session = creer_session(
            "Tri rapide", "Avancé", 6, seed=5,
            nombres=[-3, 2, -3, 1, 5, 0],
        )
        self.assertEqual(session["entree"], [-3, 2, -3, 1, 5, 0])
        question = next(q for q in session["questions"] if q["format"] == "texte")
        self.assertTrue(reponse_correcte(question, question["reponse_attendue"]))
        self.assertEqual(valider_reponse(question, question["reponse_attendue"]), "correcte")

    def test_questions_etat_sans_ambiguite_sur_les_six_algorithmes(self):
        for nom in ALGORITHMES:
            with self.subTest(algorithme=nom):
                session = creer_session(
                    nom, "Débutant", 1, seed=11, nombres=[5, 1, 5, 2, 3]
                )
                question = session["questions"][0]
                self.assertEqual(question["type"], "etat")
                self.assertEqual(len(question["choix"]), 4)
                self.assertEqual(len({tuple(choix) for choix in question["choix"]}), 4)
                self.assertEqual(question["reponse_attendue"], question["apres"])
                self.assertTrue(reponse_correcte(question, question["apres"]))
                self.assertEqual(valider_reponse(question, question["apres"]), "correcte")
                self.assertEqual(question["avant"], question["historique"][question["index_etape"]]["avant"])

    def test_listes_courtes_ou_sans_mutation_replient_vers_prediction(self):
        for nom in ALGORITHMES:
            for nombres in ([7], [2, 1], [3, 3, 3]):
                with self.subTest(algorithme=nom, nombres=nombres):
                    session = creer_session(
                        nom, "Débutant", 1, seed=2, nombres=list(nombres)
                    )
                    question = session["questions"][0]
                    self.assertEqual(question["type"], "prediction")
                    self.assertIn(question["reponse_attendue"], question["choix"])


def _label_evenement(etape):
    action = etape["action"]
    indices = etape["indices"]
    valeurs = etape["valeurs"]
    details = etape["details"]
    if action == "comparaison" and valeurs is not None:
        return f"Comparer {valeurs[0]} et {valeurs[1]} (positions {indices[0]} et {indices[1]})"
    if action == "echange" and valeurs is not None:
        return f"Échanger les positions {indices[0]} et {indices[1]} ({valeurs[0]} et {valeurs[1]})"
    if action == "division":
        zones = details["zones"]
        return f"Diviser en [{zones[0][0]}..{zones[0][1]}] et [{zones[1][0]}..{zones[1][1]}]"
    return f"{action.capitalize()} : {etape['explication']}"


if __name__ == "__main__":
    unittest.main()