import unittest
from unittest.mock import patch

from algorithmes.defi import (
    ALGORITHMES_JOUABLES,
    DELAI_RAPIDITE_SECONDES,
    DIFFICULTES_DEFI,
    TYPES_DEFI,
    creer_defi,
    defi_termine,
    etat_defi,
    progression_defi,
    reinitialiser_defi,
    utiliser_indice,
    valider_action,
)
from algorithmes.tri import ALGORITHMES


def _reponse_correcte(tache):
    return {"action": tache["action"], **tache["attendu"]}


def _terminer_avec_trace(defi):
    while not defi_termine(defi):
        tache = defi["taches"][defi["curseur"]]
        assert valider_action(defi, _reponse_correcte(tache)) == "correcte"


class TestsDefiInteractif(unittest.TestCase):
    def test_les_six_tris_sont_jouables_depuis_leurs_traces(self):
        self.assertEqual(set(ALGORITHMES_JOUABLES), set(ALGORITHMES))
        for nom in ALGORITHMES:
            with self.subTest(algorithme=nom):
                defi = creer_defi(nom, "Débutant", seed=1)
                self.assertTrue(defi["taches"])

    def test_comparaison_invalide_ne_fait_pas_avancer_le_defi(self):
        defi = creer_defi("Tri par sélection", "Débutant", nombres=[4, 1, 3, 2])
        self.assertEqual(defi["taches"][0]["action"], "comparer")
        self.assertEqual(defi["taches"][0]["etape"]["indices"], (1, 0))
        avant = etat_defi(defi)

        resultat = valider_action(
            defi, {"action": "comparer", "indices": (1, 2)}
        )

        self.assertEqual(resultat, "incorrecte")
        self.assertEqual(defi["curseur"], 0)
        self.assertEqual(etat_defi(defi), avant)
        self.assertIn("suffixe", defi["feedback"]["texte"])

    def test_bulles_valide_comparaison_puis_echange_exact(self):
        defi = creer_defi("Tri à bulles", "Débutant", nombres=[2, 1])
        self.assertEqual(
            valider_action(defi, {"action": "comparer", "indices": (0, 1)}),
            "correcte",
        )
        self.assertEqual(defi["taches"][defi["curseur"]]["action"], "echanger")
        self.assertEqual(
            valider_action(defi, {"action": "echanger", "indices": (1, 0)}),
            "correcte",
        )
        self.assertTrue(defi_termine(defi))
        self.assertEqual(etat_defi(defi), [1, 2])
        self.assertEqual(progression_defi(defi)["score"], 100)

    def test_insertion_valide_cle_decalage_et_insertion(self):
        defi = creer_defi("Tri par insertion", "Débutant", nombres=[3, 1, 2])
        self.assertEqual(defi["taches"][0]["action"], "choisir_cle")
        self.assertEqual(
            valider_action(defi, {"action": "choisir_cle", "indice": 0}),
            "incorrecte",
        )
        self.assertEqual(
            valider_action(defi, {"action": "choisir_cle", "indice": 1}),
            "correcte",
        )
        self.assertEqual(defi["taches"][defi["curseur"]]["action"], "comparer")
        _terminer_avec_trace(defi)
        self.assertEqual(etat_defi(defi), [1, 2, 3])
        self.assertTrue(defi["feedback"]["correcte"])

    def test_traces_reelles_couvrent_doublons_negatifs_et_tableaux_courts(self):
        entrees = ([4, 1, 4, -2], [7], [2, 1], [3, 3, 3], [-5, 0, -5, 2])
        for nom in ALGORITHMES:
            for entree in entrees:
                with self.subTest(algorithme=nom, entree=entree):
                    defi = creer_defi(nom, "Débutant", nombres=list(entree))
                    self.assertEqual(defi["entree"], list(entree))
                    _terminer_avec_trace(defi)
                    self.assertEqual(etat_defi(defi), sorted(entree))
                    self.assertEqual(defi["actions"], len(defi["taches"]))

    def test_fusion_demande_division_fusion_tampon_et_ecritures(self):
        defi = creer_defi("Tri fusion", "Débutant", nombres=[4, 1, 3, 2])
        actions = [tache["action"] for tache in defi["taches"]]
        for action in ("diviser", "fusionner", "choisir_fusion", "placer_tampon", "ecrire_fusion"):
            self.assertIn(action, actions)

        tache = defi["taches"][defi["curseur"]]
        attendu = _reponse_correcte(tache)
        mauvais = {**attendu, "milieu": attendu["milieu"] + 1}
        avant = etat_defi(defi)
        self.assertEqual(valider_action(defi, mauvais), "incorrecte")
        self.assertEqual(defi["curseur"], 0)
        self.assertEqual(etat_defi(defi), avant)
        _terminer_avec_trace(defi)
        self.assertEqual(etat_defi(defi), [1, 2, 3, 4])

    def test_rapide_valide_pivot_partition_relations_et_segments(self):
        defi = creer_defi("Tri rapide", "Débutant", nombres=[3, 1, 2, 3])
        actions = [tache["action"] for tache in defi["taches"]]
        for action in (
            "choisir_pivot", "initialiser_partition", "classer_partition",
            "avancer_partition", "echanger_partition", "confirmer_partition",
            "choisir_segment",
        ):
            self.assertIn(action, actions)

        while defi["taches"][defi["curseur"]]["action"] != "classer_partition":
            tache = defi["taches"][defi["curseur"]]
            valider_action(defi, _reponse_correcte(tache))
        tache = defi["taches"][defi["curseur"]]
        attendu = _reponse_correcte(tache)
        mauvais = {**attendu, "relation": "egal" if attendu["relation"] != "egal" else "gauche"}
        curseur = defi["curseur"]
        avant = etat_defi(defi)
        self.assertEqual(valider_action(defi, mauvais), "incorrecte")
        self.assertEqual(defi["curseur"], curseur)
        self.assertEqual(etat_defi(defi), avant)
        _terminer_avec_trace(defi)
        self.assertEqual(etat_defi(defi), sorted(defi["entree"]))

    def test_tas_valide_tamisage_extraction_reduction_et_invariants(self):
        defi = creer_defi("Tri par tas", "Débutant", nombres=[3, -1, 4, 2])
        actions = [tache["action"] for tache in defi["taches"]]
        for action in (
            "initialiser_tas", "tamiser_tas", "comparer_tas", "confirmer_tas",
            "echanger_tas", "reduire_tas",
        ):
            self.assertIn(action, actions)

        while defi["taches"][defi["curseur"]]["action"] != "reduire_tas":
            tache = defi["taches"][defi["curseur"]]
            valider_action(defi, _reponse_correcte(tache))
        tache = defi["taches"][defi["curseur"]]
        attendu = _reponse_correcte(tache)
        mauvais = {**attendu, "taille_tas": attendu["taille_tas"] + 1}
        curseur = defi["curseur"]
        avant = etat_defi(defi)
        self.assertEqual(valider_action(defi, mauvais), "incorrecte")
        self.assertEqual(defi["curseur"], curseur)
        self.assertEqual(etat_defi(defi), avant)
        _terminer_avec_trace(defi)
        self.assertEqual(etat_defi(defi), [-1, 2, 3, 4])

    def test_indices_progressifs_score_et_bilan_reflètent_les_actions(self):
        defi = creer_defi("Tri à bulles", "Débutant", nombres=[2, 1])
        premier = utiliser_indice(defi)
        second = utiliser_indice(defi)
        self.assertIsNotNone(premier)
        self.assertIsNotNone(second)
        self.assertNotEqual(premier, second)
        self.assertIsNone(utiliser_indice(defi))

        valider_action(defi, {"action": "comparer", "indices": (1, 0)})
        valider_action(defi, {"action": "comparer", "indices": (0, 1)})
        _terminer_avec_trace(defi)
        bilan = progression_defi(defi)
        self.assertEqual(bilan["actions"], len(defi["taches"]))
        self.assertEqual(bilan["erreurs"], 1)
        self.assertEqual(bilan["indices"], 2)
        self.assertEqual(bilan["score"], 67)
        self.assertTrue(bilan["reussite"])

    def test_deux_indices_sont_disponibles_pour_les_six_algorithmes(self):
        for nom in ALGORITHMES:
            with self.subTest(algorithme=nom):
                defi = creer_defi(nom, "Débutant", seed=8)
                premier = utiliser_indice(defi)
                second = utiliser_indice(defi)
                self.assertTrue(premier)
                self.assertTrue(second)
                self.assertNotEqual(premier, second)
                self.assertIsNone(utiliser_indice(defi))
                self.assertEqual(defi["indices_utilises"], 2)

    def test_reinitialisation_rejoue_la_meme_entree_sans_historique(self):
        defi = creer_defi("Tri par insertion", "Intermédiaire", seed=4)
        entree = defi["entree"]
        utiliser_indice(defi)
        _terminer_avec_trace(defi)

        nouveau = reinitialiser_defi(defi)

        self.assertEqual(nouveau["entree"], entree)
        self.assertEqual(nouveau["curseur"], 0)
        self.assertEqual(nouveau["actions"], 0)
        self.assertEqual(nouveau["erreurs"], 0)
        self.assertEqual(nouveau["indices_utilises"], 0)
        self.assertNotEqual(nouveau["id"], defi["id"])

    def test_reinitialisation_des_trois_algorithmes_composites(self):
        for nom in ("Tri fusion", "Tri rapide", "Tri par tas"):
            with self.subTest(algorithme=nom):
                defi = creer_defi(nom, "Débutant", nombres=[3, -1, 3, 0])
                valider_action(defi, _reponse_correcte(defi["taches"][0]))
                nouveau = reinitialiser_defi(defi)
                self.assertEqual(nouveau["entree"], defi["entree"])
                self.assertEqual(nouveau["curseur"], 0)
                self.assertEqual(nouveau["actions"], 0)
                self.assertEqual(nouveau["erreurs"], 0)

    def test_defi_genere_une_entree_adaptee_au_niveau(self):
        tailles = {"Débutant": 3, "Intermédiaire": 4, "Avancé": 5}
        for difficulte, taille in tailles.items():
            defi = creer_defi("Tri à bulles", difficulte, seed=5)
            self.assertEqual(len(defi["entree"]), taille)
            self.assertTrue(all(isinstance(valeur, int) for valeur in defi["entree"]))

    def test_formats_quiz_sont_valides_reproductibles_et_explicatifs(self):
        for type_defi in TYPES_DEFI[1:]:
            for difficulte in DIFFICULTES_DEFI:
                with self.subTest(type_defi=type_defi, difficulte=difficulte):
                    premier = creer_defi(
                        "Tri à bulles", difficulte, seed=19, type_defi=type_defi
                    )
                    second = creer_defi(
                        "Tri à bulles", difficulte, seed=19, type_defi=type_defi
                    )
                    self.assertTrue(premier["taches"])
                    consignes = [tache["consigne"] for tache in premier["taches"]]
                    self.assertEqual(len(consignes), len(set(consignes)))
                    self.assertEqual(
                        [(t["action"], t["attendu"], t["schema"]) for t in premier["taches"]],
                        [(t["action"], t["attendu"], t["schema"]) for t in second["taches"]],
                    )
                    for tache in premier["taches"]:
                        self.assertTrue(tache["schema"]["champs"])
                        self.assertTrue(
                            tache.get("explication")
                            or tache["etape"].get("explication")
                        )
                        for champ in tache["schema"]["champs"]:
                            self.assertTrue(champ["options"])
                            self.assertIn(champ["type"], ("radio", "selectbox"))
                            if "partie" not in champ and "correspondances" not in champ:
                                self.assertIn(
                                    tache["attendu"][champ["reponse"]], champ["options"]
                                )

    def test_formats_quiz_acceptent_bonne_reponse_et_corrigent_la_mauvaise(self):
        for type_defi in TYPES_DEFI[1:]:
            with self.subTest(type_defi=type_defi):
                defi = creer_defi(
                    "Tri par sélection", "Intermédiaire", seed=31,
                    type_defi=type_defi,
                )
                premiere = defi["taches"][0]
                champ = premiere["schema"]["champs"][0]
                cle = champ.get("reponse")
                attendu = premiere["attendu"][cle]
                mauvaise = next(
                    valeur for valeur in champ["options"] if valeur != attendu
                )
                self.assertEqual(
                    valider_action(defi, {"action": premiere["action"], cle: mauvaise}),
                    "incorrecte",
                )
                self.assertIn("texte", defi["feedback"])
                self.assertEqual(defi["curseur"], 1)
                while not defi_termine(defi):
                    tache = defi["taches"][defi["curseur"]]
                    self.assertEqual(
                        valider_action(defi, _reponse_correcte(tache)), "correcte"
                    )
                self.assertEqual(progression_defi(defi)["erreurs"], 1)
                self.assertEqual(
                    progression_defi(defi)["score"],
                    round(100 * (len(defi["taches"]) - 1) / len(defi["taches"])),
                )

    def test_difficulte_limites_taille_et_mode_rapide_expire(self):
        for difficulte, taille in (("Débutant", 3), ("Intermédiaire", 4), ("Avancé", 5)):
            defi = creer_defi("Tri à bulles", difficulte, seed=8, type_defi="Rapidité")
            self.assertEqual(len(defi["entree"]), taille)
            self.assertEqual(defi["limite_secondes"], DELAI_RAPIDITE_SECONDES)
            self.assertLessEqual(len(defi["taches"]), 5)

        with patch("algorithmes.defi.time.monotonic", return_value=100):
            rapide = creer_defi(
                "Tri à bulles", "Débutant", seed=8, type_defi="Rapidité"
            )
        with patch(
            "algorithmes.defi.time.monotonic",
            return_value=100 + DELAI_RAPIDITE_SECONDES + 1,
        ):
            self.assertTrue(defi_termine(rapide))
            self.assertTrue(progression_defi(rapide)["temps_ecoule"])

    def test_prediction_refuse_une_entree_sans_transition(self):
        with self.assertRaisesRegex(ValueError, "question valide"):
            creer_defi(
                "Tri à bulles", "Débutant", nombres=[7], type_defi="Prédiction"
            )


if __name__ == "__main__":
    unittest.main()