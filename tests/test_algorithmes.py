import unittest
import random

from algorithmes.tri import (
    ALGORITHMES,
    PSEUDOCODES,
    calculer_statistiques,
)


class TestsTriPedagogiques(unittest.TestCase):
    cas = (
        [],
        [7],
        [1, 2, 3, 4],
        [4, 3, 2, 1],
        [-5, -1, -3, 0],
        [3, 1, 3, 2, 1],
        [8, 3, 5, 1, 9, 2, 7, 4, 6],
    )

    def test_resultat_final_et_entree_preservee(self):
        for nom, trier in ALGORITHMES.items():
            for nombres in self.cas:
                with self.subTest(algorithme=nom, nombres=nombres):
                    entree = nombres.copy()
                    etapes = trier(nombres)
                    self.assertEqual(etapes[-1]["liste"], sorted(entree))
                    self.assertEqual(nombres, entree)
                    self.assertEqual(etapes[-1]["action"], "fin")

    def test_compteurs_monotones_et_finaux_coherents(self):
        for nom, trier in ALGORITHMES.items():
            for nombres in self.cas:
                with self.subTest(algorithme=nom, nombres=nombres):
                    etapes = trier(nombres)
                    for precedente, courante in zip(etapes, etapes[1:]):
                        for compteur in ("comparaisons", "echanges", "deplacements"):
                            self.assertGreaterEqual(
                                courante[compteur], precedente[compteur]
                            )
                        self.assertEqual(
                            courante["operations"],
                            courante["echanges"] + courante["deplacements"],
                        )
                    self.assertEqual(
                        etapes[-1]["echanges"],
                        sum(etape["action"] == "echange" for etape in etapes),
                    )
                    self.assertEqual(
                        etapes[-1]["comparaisons"],
                        sum(etape["action"] == "comparaison" for etape in etapes),
                    )
                    self.assertEqual(
                        etapes[-1]["operations"],
                        etapes[-1]["echanges"] + etapes[-1]["deplacements"],
                    )

    def test_comparaisons_de_selection_tracent_les_operandes_reels(self):
        etapes = ALGORITHMES["Tri par sélection"]([4, 1, 3, 2])
        comparaison = next(
            etape for etape in etapes if etape["action"] == "comparaison"
        )
        gauche, minimum = comparaison["indices"]
        self.assertEqual(comparaison["valeurs"], (
            comparaison["avant"][gauche], comparaison["avant"][minimum]
        ))
        self.assertEqual(comparaison["indices"], (1, 0))

    def test_explications_refletent_les_decisions_et_mutations(self):
        for etape in ALGORITHMES["Tri à bulles"]([3, 1, 2]):
            if etape["action"] == "comparaison":
                gauche, droite = etape["valeurs"]
                decision = (
                    "un échange est nécessaire"
                    if gauche > droite else "la paire reste en place"
                )
                self.assertIn(decision, etape["explication"])

        for etape in ALGORITHMES["Tri par sélection"]([4, 1, 3]):
            if etape["action"] == "comparaison":
                candidat, minimum = etape["valeurs"]
                decision = (
                    "devient la position"
                    if candidat < minimum else "reste en position"
                )
                self.assertIn(decision, etape["explication"])

        for etape in ALGORITHMES["Tri par insertion"]([3, 1, 2]):
            if etape["action"] == "comparaison":
                precedente, cle = etape["valeurs"]
                decision = (
                    "la valeur doit être décalée"
                    if precedente > cle else "la clé peut être insérée"
                )
                self.assertIn(decision, etape["explication"])
            elif etape["action"] == "deplacement":
                source, destination = etape["indices"]
                self.assertEqual(etape["avant"][source], etape["valeurs"][0])
                self.assertIsNotNone(etape["valeur_en_cours"])
            elif etape["action"] == "insertion":
                (destination,) = etape["indices"]
                self.assertEqual(etape["apres"][destination], etape["valeurs"][0])

    def test_etats_avant_apres_et_lignes_de_pseudocode(self):
        for nom, trier in ALGORITHMES.items():
            for nombres in self.cas:
                etapes = trier(nombres)
                for precedente, etape in zip(etapes, etapes[1:]):
                    if etape["avant"] is not None:
                        self.assertEqual(etape["avant"], precedente["liste"])
                        self.assertEqual(etape["apres"], etape["liste"])
                for etape in etapes:
                    self.assertIn(etape["ligne_pseudocode"], range(
                        1, len(PSEUDOCODES[nom]) + 1
                    ))
                    self.assertTrue(etape["explication"].strip())

    def test_actions_associees_aux_lignes_exactes(self):
        lignes = {
            "Tri à bulles": {
                "initialisation": 1, "comparaison": 3, "echange": 5, "fin": 7,
            },
            "Tri par sélection": {
                "initialisation": 1, "comparaison": 4, "decision": 6,
                "echange": 7, "fin": 8,
            },
            "Tri par insertion": {
                "comparaison": 4, "deplacement": 5, "insertion": 6, "fin": 7,
            },
            "Tri fusion": {
                "initialisation": 1, "base": 2, "division": 3, "fusion": 6,
                "comparaison": 7, "ecriture": 10, "fin": 11,
            },
            "Tri rapide": {
                "initialisation": 1, "base": 2, "pivot": 3,
                "comparaison": 5, "fin": 12,
            },
            "Tri par tas": {
                "initialisation": 1, "construction_tas": 1,
                "reduction_tas": 7, "fin": 9,
            },
        }
        for nom, trier in ALGORITHMES.items():
            for etape in trier([3, 1, 2]):
                if nom == "Tri fusion" and etape["action"] in ("recursion", "placement"):
                    lignes_valides = (4, 5) if etape["action"] == "recursion" else (8, 9)
                    self.assertIn(etape["ligne_pseudocode"], lignes_valides)
                    continue
                if nom == "Tri rapide" and etape["action"] in (
                    "partition", "decision", "echange", "recursion"
                ):
                    lignes_valides = {
                        "partition": (4, 9),
                        "decision": (6, 7, 8),
                        "echange": (6, 7),
                        "recursion": (10, 11),
                    }[etape["action"]]
                    self.assertIn(etape["ligne_pseudocode"], lignes_valides)
                    continue
                if nom == "Tri par tas" and etape["action"] in (
                    "tas", "comparaison", "decision", "echange"
                ):
                    lignes_valides = {
                        "tas": (2, 8),
                        "comparaison": (3, 4),
                        "decision": (2, 8),
                        "echange": (5, 6),
                    }[etape["action"]]
                    self.assertIn(etape["ligne_pseudocode"], lignes_valides)
                    continue
                if etape["action"] == "initialisation":
                    ligne = (
                        2 if nom == "Tri par insertion"
                        and etape["valeur_en_cours"] is not None else 1
                    )
                else:
                    ligne = lignes[nom][etape["action"]]
                self.assertEqual(etape["ligne_pseudocode"], ligne)

    def test_insertion_distingue_comparaison_deplacement_et_insertion(self):
        etapes = ALGORITHMES["Tri par insertion"]([3, 1, 2])
        actions = [etape["action"] for etape in etapes]
        self.assertIn("comparaison", actions)
        self.assertIn("deplacement", actions)
        self.assertIn("insertion", actions)
        deplacement = next(
            etape for etape in etapes if etape["action"] == "deplacement"
        )
        self.assertIsNotNone(deplacement["valeur_en_cours"])
        self.assertIn("décalé", deplacement["explication"])

    def test_traces_signalent_les_zones_ordonnees_avec_leur_portee(self):
        bulles = ALGORITHMES["Tri à bulles"]([4, 3, 2, 1])
        comparaison_bulles = next(
            etape for etape in bulles
            if etape["action"] == "comparaison"
            and etape["details"].get("zone_placee") == (3, 3)
        )
        self.assertEqual(comparaison_bulles["liste"][3], 4)

        selection = ALGORITHMES["Tri par sélection"]([3, 1, 2])
        comparaison_selection = next(
            etape for etape in selection
            if etape["action"] == "comparaison"
            and etape["details"].get("zone_placee") == (0, 0)
        )
        self.assertEqual(comparaison_selection["liste"][0], 1)

        insertion = ALGORITHMES["Tri par insertion"]([3, 1, 2])
        comparaison_insertion = next(
            etape for etape in insertion
            if etape["action"] == "comparaison"
            and etape["indices"][1] == 1
        )
        self.assertEqual(comparaison_insertion["details"]["prefixe_trie"], (0, 0))

        comparaison_insertion = next(
            etape for etape in insertion
            if etape["action"] == "comparaison"
            and etape["indices"][1] == 2
        )
        self.assertEqual(comparaison_insertion["details"]["prefixe_trie"], (0, 1))
        self.assertEqual(
            comparaison_insertion["liste"][:2],
            sorted(comparaison_insertion["liste"][:2]),
        )

    def test_statistiques_attendues_sur_les_cas_de_reference(self):
        bulle = ALGORITHMES["Tri à bulles"]([1, 2, 3, 4])[-1]
        self.assertEqual((bulle["comparaisons"], bulle["echanges"]), (3, 0))

        selection = ALGORITHMES["Tri par sélection"]([4, 3, 2, 1])[-1]
        self.assertEqual((selection["comparaisons"], selection["echanges"]), (6, 2))

        insertion = ALGORITHMES["Tri par insertion"]([4, 3, 2, 1])[-1]
        self.assertEqual((insertion["comparaisons"], insertion["deplacements"]), (6, 9))

    def test_statistiques_sans_historique_identiques_aux_historiques(self):
        cles = ("liste", "comparaisons", "echanges", "deplacements")
        for nom, trier in ALGORITHMES.items():
            for nombres in self.cas:
                with self.subTest(algorithme=nom, nombres=nombres):
                    historique = trier(nombres)[-1]
                    statistiques = calculer_statistiques(nom, nombres)
                    self.assertEqual(
                        tuple(statistiques[cle] for cle in cles),
                        tuple(historique[cle] for cle in cles),
                    )

    def test_fusion_trace_les_moities_le_tampon_et_les_ecritures(self):
        etapes = ALGORITHMES["Tri fusion"]([4, 1, 3, 2])
        fusion_finale = next(
            etape for etape in etapes
            if etape["action"] == "fusion"
            and etape["details"]["zone_active"] == (0, 3)
        )
        self.assertEqual(fusion_finale["details"]["tampon_gauche"], [1, 4])
        self.assertEqual(fusion_finale["details"]["tampon_droit"], [2, 3])

        placements = [etape for etape in etapes if etape["action"] == "placement"]
        ecritures = [etape for etape in etapes if etape["action"] == "ecriture"]
        self.assertTrue(placements)
        self.assertEqual(len(ecritures), 8)
        for etape in etapes:
            if etape["action"] == "comparaison":
                self.assertEqual(
                    tuple(etape["avant"][indice] for indice in etape["indices"]),
                    etape["valeurs"],
                )
                self.assertEqual(
                    etape["details"]["destination"],
                    etape["details"]["zone_active"][0] + len(etape["details"]["tampon"]),
                )
                self.assertEqual(
                    etape["valeurs"][0],
                    etape["details"]["tampon_gauche"][etape["details"]["curseur_gauche"]],
                )
                self.assertEqual(
                    etape["valeurs"][1],
                    etape["details"]["tampon_droit"][etape["details"]["curseur_droit"]],
                )
                self.assertEqual(
                    etape["indices"],
                    (
                        etape["details"]["zone_active"][0]
                        + etape["details"]["curseur_gauche"],
                        etape["details"]["zone_active"][0]
                        + len(etape["details"]["tampon_gauche"])
                        + etape["details"]["curseur_droit"],
                    ),
                )
            elif etape["action"] == "placement":
                self.assertEqual(etape["avant"], etape["apres"])
                self.assertEqual(etape["details"]["tampon"], sorted(etape["details"]["tampon"]))
                self.assertEqual(etape["details"]["tampon"][-1], etape["valeurs"][0])
                self.assertEqual(
                    etape["avant"][etape["details"]["source"]], etape["valeurs"][0]
                )
                self.assertEqual(
                    etape["details"]["destination"],
                    etape["details"]["zone_active"][0] + len(etape["details"]["tampon"]) - 1,
                )
            elif etape["action"] == "ecriture":
                indice = etape["indices"][0]
                self.assertEqual(etape["apres"][indice], etape["valeurs"][0])
                self.assertEqual(etape["details"]["destination"], indice)
                self.assertEqual(etape["details"]["tampon"][indice - etape["details"]["zone_active"][0]], etape["valeurs"][0])

        self.assertEqual(etapes[-1]["liste"], [1, 2, 3, 4])
        self.assertEqual(etapes[-1]["comparaisons"], 5)
        self.assertEqual(etapes[-1]["deplacements"], 16)

    def test_indices_et_operandes_des_comparaisons_sont_valides(self):
        for nom, trier in ALGORITHMES.items():
            for etape in trier([4, 1, 3, 2, -1]):
                if etape["action"] != "comparaison":
                    continue
                self.assertIsNotNone(etape["avant"])
                self.assertIsNotNone(etape["indices"])
                self.assertEqual(len(etape["indices"]), len(etape["valeurs"]))
                for indice in etape["indices"]:
                    self.assertIn(indice, range(len(etape["avant"])))
                if nom == "Tri par insertion":
                    self.assertEqual(etape["avant"][etape["indices"][0]], etape["valeurs"][0])
                    self.assertEqual(etape["valeur_en_cours"], etape["valeurs"][1])
                else:
                    self.assertEqual(
                        tuple(etape["avant"][indice] for indice in etape["indices"]),
                        etape["valeurs"],
                    )

    def test_plusieurs_entrees_aleatoires_et_permutations(self):
        generateur = random.Random(20261016)
        entrees = [
            [generateur.randint(-20, 20) for _ in range(taille)]
            for taille in range(0, 25)
        ]
        for nom, trier in ALGORITHMES.items():
            for entree in entrees:
                with self.subTest(algorithme=nom, entree=entree):
                    copie = entree.copy()
                    etapes = trier(entree)
                    self.assertEqual(etapes[-1]["liste"], sorted(copie))
                    self.assertEqual(sorted(etapes[-1]["liste"]), sorted(copie))
                    self.assertEqual(entree, copie)

    def test_tri_rapide_garde_un_comportement_equilibre_sur_entree_triee(self):
        statistiques = calculer_statistiques("Tri rapide", list(range(256)))
        self.assertEqual(statistiques["liste"], list(range(256)))
        self.assertLess(statistiques["comparaisons"], 10 * 256 * 8)

    def test_tas_zone_active_et_racine_sont_coherentes(self):
        etapes = ALGORITHMES["Tri par tas"]([5, 2, 4, 1, 3])
        extractions = [
            etape for etape in etapes
            if etape["action"] == "echange"
            and etape["details"].get("maximum_place") is not None
        ]
        self.assertTrue(extractions)
        for etape in extractions:
            maximum_place = etape["details"]["maximum_place"]
            self.assertEqual(etape["details"]["heap_size"], maximum_place)
            self.assertEqual(etape["liste"][maximum_place], etape["valeurs"][0])
            self.assertEqual(etape["details"]["zone_triee"][0], maximum_place)

        for etape in etapes:
            if not etape["details"].get("heap_valid"):
                continue
            taille_tas = etape["details"]["heap_size"]
            for parent in range(taille_tas):
                for enfant in (2 * parent + 1, 2 * parent + 2):
                    if enfant < taille_tas:
                        self.assertGreaterEqual(
                            etape["liste"][parent], etape["liste"][enfant]
                        )

    def test_tri_rapide_frontieres_et_zones_correspondent_aux_valeurs(self):
        etapes = ALGORITHMES["Tri rapide"]([4, 1, 3, 2, 5, 3])
        for etape in etapes:
            details = etape["details"]
            if etape["action"] == "comparaison":
                indice_courant, indice_pivot = etape["indices"]
                self.assertEqual(etape["avant"][indice_courant], etape["valeurs"][0])
                self.assertEqual(etape["avant"][indice_pivot], details["pivot_value"])
                moins, courant, plus = details["partition"]
                gauche, droite = details["zone_active"]
                self.assertLessEqual(gauche, moins)
                self.assertLessEqual(moins, courant)
                self.assertLessEqual(courant, plus + 1)
                self.assertLessEqual(plus, droite)

            if etape["action"] == "partition" and details.get("zones"):
                valeur_pivot = details["pivot_value"]
                for gauche, droite, role in details["zones"]:
                    for indice in range(gauche, droite + 1):
                        valeur = etape["liste"][indice]
                        if role == "gauche":
                            self.assertLess(valeur, valeur_pivot)
                        elif role == "pivot":
                            self.assertEqual(valeur, valeur_pivot)
                        elif role == "droite":
                            self.assertGreater(valeur, valeur_pivot)


if __name__ == "__main__":
    unittest.main()