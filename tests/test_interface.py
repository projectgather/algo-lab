from pathlib import Path
import secrets
import sqlite3

from algorithmes.defi import creer_defi, defi_termine
from algorithmes.exercices import creer_session, statistiques_session
from algorithmes.analyse import analyser_mesures
from algorithmes.progression import ProgressionStore
from algorithmes.tri import ALGORITHMES, INFORMATIONS_ALGORITHMES
from streamlit.testing.v1 import AppTest as _StreamlitAppTest

_CODE_TEST = f"{secrets.randbelow(1_000_000):06d}"


def _creer_profil_test(app, nom):
    mode = next(radio for radio in app.radio if radio.label == "Accès")
    profils = next(
        (select.options for select in app.selectbox if select.label == "Profil"),
        [],
    )
    if nom in profils:
        if mode.value != "Se connecter":
            mode.set_value("Se connecter").run()
        next(select for select in app.selectbox if select.label == "Profil").set_value(nom).run()
        if any(field.label == "Code personnel" for field in app.text_input):
            next(field for field in app.text_input if field.label == "Code personnel").set_value(_CODE_TEST)
            next(button for button in app.button if button.label == "Déverrouiller").click().run()
        else:
            recovery_code = ProgressionStore().issue_recovery_code(nom)
            next(field for field in app.text_input if field.label == "Code de récupération à usage unique").set_value(recovery_code)
            next(field for field in app.text_input if field.label == "Nouveau code personnel à 6 chiffres").set_value(_CODE_TEST)
            next(field for field in app.text_input if field.label == "Confirmer le code personnel").set_value(_CODE_TEST)
            next(button for button in app.button if button.label == "Définir le code et ouvrir le profil").click().run()
        return
    if mode.value != "Créer un profil":
        mode.set_value("Créer un profil").run()
    next(field for field in app.text_input if field.label == "Nom du profil").set_value(nom)
    next(field for field in app.text_input if "Code personnel à 6 chiffres" in field.label).set_value(_CODE_TEST)
    next(field for field in app.text_input if field.label == "Confirmer le code personnel").set_value(_CODE_TEST)
    next(button for button in app.button if button.label == "Créer et ouvrir le profil").click().run()


class AppTest:
    @staticmethod
    def from_file(path, **kwargs):
        app = _StreamlitAppTest.from_file(path).run(timeout=10, **kwargs)
        if not any(radio.label == "Navigation" for radio in app.radio):
            _creer_profil_test(app, "Joueur")
        return app


def _changer_profil(app, nom):
    if any(button.label == "Verrouiller le profil" for button in app.button):
        next(button for button in app.button if button.label == "Verrouiller le profil").click().run()
    mode = next(radio for radio in app.radio if radio.label == "Accès")
    options = next((select.options for select in app.selectbox if select.label == "Profil"), [])
    if nom not in options:
        _creer_profil_test(app, nom)
        return
    if mode.value != "Se connecter":
        mode.set_value("Se connecter").run()
    next(select for select in app.selectbox if select.label == "Profil").set_value(nom).run()
    if any(field.label == "Code personnel" for field in app.text_input):
        next(field for field in app.text_input if field.label == "Code personnel").set_value(_CODE_TEST)
        next(button for button in app.button if button.label == "Déverrouiller").click().run()
    else:
        recovery_code = ProgressionStore().issue_recovery_code(nom)
        next(field for field in app.text_input if field.label == "Code de récupération à usage unique").set_value(recovery_code)
        next(field for field in app.text_input if field.label == "Nouveau code personnel à 6 chiffres").set_value(_CODE_TEST)
        next(field for field in app.text_input if field.label == "Confirmer le code personnel").set_value(_CODE_TEST)
        next(button for button in app.button if button.label == "Définir le code et ouvrir le profil").click().run()


def _ouvrir_page(app, nom_page):
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        nom_page
    ).run()


def _terminer_defi_interface(app):
    defi_initial = app.session_state["defi_interactif"]
    for _ in range(len(defi_initial["taches"]) + 1):
        if defi_termine(app.session_state["defi_interactif"]):
            return
        defi = app.session_state["defi_interactif"]
        tache = defi["taches"][defi["curseur"]]
        attendu = tache["attendu"]
        for champ in tache["schema"]["champs"]:
            if "partie" in champ:
                valeur = attendu[champ["reponse"]][champ["partie"]]
            elif "correspondances" in champ:
                cles = sorted(champ["correspondances"], key=champ["correspondances"].get)
                valeur = tuple(attendu[cle] for cle in cles)
            else:
                valeur = attendu[champ["reponse"]]
            widgets = app.radio if champ["type"] == "radio" else app.selectbox
            next(widget for widget in widgets if widget.label == champ["label"]).set_value(valeur)
        libelle = (
            "Valider l'opération"
            if defi.get("type_defi", "Étapes") == "Étapes"
            else "Valider ma réponse"
        )
        next(button for button in app.button if button.label == libelle).click().run()
        assert not app.exception
    assert defi_termine(app.session_state["defi_interactif"])


def _terminer_manipulation_interface(app):
    while not app.session_state["manipulation_partie"]["completee"]:
        partie = app.session_state["manipulation_partie"]
        phase = partie["phase"]
        if phase == "choisir_cle":
            label, valeur = "Position de la clé", partie["index"]
        elif phase == "comparer":
            label, valeur = "Indice à comparer", partie["curseur"]
        elif phase == "deplacer":
            next(select for select in app.selectbox if select.label == "Position source").set_value(partie["curseur"])
            next(select for select in app.selectbox if select.label == "Position de destination").set_value(partie["curseur"] + 1)
            label = None
        elif phase == "inserer":
            label, valeur = "Position d'insertion", partie["curseur"] + 1
        elif phase == "choisir_minimum":
            label, valeur = "Indice du minimum", partie["minimum"]
        elif phase == "echanger":
            next(select for select in app.selectbox if select.label == "Position du début non trié").set_value(partie["index"])
            next(select for select in app.selectbox if select.label == "Position du minimum").set_value(partie["minimum"])
            label = None
        else:
            label = None
        if label is not None:
            next(select for select in app.selectbox if select.label == label).set_value(valeur)
        label_bouton = "Confirmer sans échange" if phase == "confirmer" else "Valider l'étape"
        next(button for button in app.button if button.label == label_bouton).click().run()
        assert not app.exception


def test_chargement_css_independant_du_repertoire_courant(tmp_path, monkeypatch):
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app_racine = AppTest.from_file(str(app_path)).run()
    style_racine = next(
        str(item.value) for item in app_racine.markdown if "<style>" in str(item.value)
    )

    monkeypatch.chdir(tmp_path)
    app_autre_repertoire = AppTest.from_file(str(app_path)).run()
    style_autre_repertoire = next(
        str(item.value)
        for item in app_autre_repertoire.markdown
        if "<style>" in str(item.value)
    )

    assert style_autre_repertoire == style_racine
    assert ".stApp" in style_autre_repertoire
    assert not app_racine.exception
    assert not app_autre_repertoire.exception


def test_modes_decouverte_analyse_modifient_le_contenu():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")
    next(button for button in app.button if "Calculer" in button.label).click().run()

    mode = next(radio for radio in app.radio if radio.label == "Mode")
    assert mode.value == "Découverte"
    assert not any("Action :" in str(caption.value) for caption in app.caption)

    mode.set_value("Analyse").run()
    assert any("Action :" in str(caption.value) for caption in app.caption)

    index_comparaison = next(
        index
        for index, etape in enumerate(app.session_state["etapes"])
        if etape["action"] == "comparaison"
    )
    next(
        slider for slider in app.slider if "Parcourir" in slider.label
    ).set_value(index_comparaison).run()
    assert any("Avant :" in str(caption.value) for caption in app.caption)
    assert any("Après :" in str(caption.value) for caption in app.caption)

    next(radio for radio in app.radio if radio.label == "Mode").set_value(
        "Découverte"
    ).run()
    assert not any("Action :" in str(caption.value) for caption in app.caption)
    assert not any("Avant :" in str(caption.value) for caption in app.caption)


def test_navigation_manipulation_conserve_la_partie_et_valide_une_action():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=10)
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Manipulation"
    ).run(timeout=10)
    next(button for button in app.button if button.label == "Commencer").click().run(timeout=10)

    partie = app.session_state["manipulation_partie"]
    assert partie["algorithme"] == "Tri par insertion"
    assert partie["phase"] == "choisir_cle"
    valeur_cle = partie["tableau"][1]
    next(select for select in app.selectbox if select.label == "Position de la clé").set_value(1)
    next(button for button in app.button if button.label == "Valider l'étape").click().run(timeout=10)

    assert app.session_state["manipulation_partie"]["phase"] == "comparer"
    assert app.session_state["manipulation_partie"]["cle"] == valeur_cle
    assert "case libre" in "\n".join(str(item.value) for item in app.markdown)
    assert not app.exception


def test_page_manipulation_selection_persiste_apres_rerun():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=10)
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Manipulation"
    ).run(timeout=10)
    next(button for button in app.button if button.label == "Commencer").click().run(timeout=10)
    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri par sélection"
    ).run(timeout=10)
    partie = app.session_state["manipulation_partie"]
    identifiant_partie = partie["id"]
    next(button for button in app.button if "Démarrer avec ces paramètres" in button.label).click().run(timeout=10)

    partie = app.session_state["manipulation_partie"]
    assert partie["id"] != identifiant_partie
    assert partie["algorithme"] == "Tri par sélection"
    assert partie["phase"] == "comparer"
    assert partie["curseur"] == 1
    next(select for select in app.selectbox if select.label == "Indice à comparer").set_value(1)
    next(button for button in app.button if button.label == "Valider l'étape").click().run(timeout=10)

    assert app.session_state["manipulation_partie"]["curseur"] == 2
    assert app.session_state["manipulation_partie"]["id"] == partie["id"]
    assert app.session_state["manipulation_partie"]["etapes"] == 1
    contenu = "\n".join(str(item.value) for item in app.markdown)
    assert "array-cell-selected" in contenu
    assert "array-cell-compare" in contenu
    assert not app.exception


def test_changement_profil_verrouille_et_efface_manipulation_en_cours():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Manipulation"
    ).run()
    next(button for button in app.button if button.label == "Commencer").click().run()
    _changer_profil(app, "Lin")
    store = ProgressionStore()
    assert "manipulation_partie" not in app.session_state
    assert store.profile("Joueur")["xp"] == 0
    assert store.profile("Lin")["xp"] == 0
    assert app.session_state["profil_nom"] == "Lin"
    assert store.profile("Joueur")["xp"] == 0
    assert store.profile("Lin")["xp"] == 0


def test_abandon_manipulation_ne_genere_pas_de_recompense():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Manipulation"
    ).run()
    next(button for button in app.button if button.label == "Commencer").click().run()
    next(button for button in app.button if button.label == "Abandonner").click().run()

    assert "manipulation_partie" not in app.session_state
    assert ProgressionStore().profile("Joueur")["xp"] == 0
    assert not app.exception


def test_visualisation_fusion_affiche_sources_tampon_et_destination():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")
    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri fusion"
    ).run()
    next(
        field for field in app.text_input if "Nombres séparés" in field.label
    ).set_value("4, 1, 3, 2").run()
    next(button for button in app.button if "Calculer" in button.label).click().run()
    next(radio for radio in app.radio if radio.label == "Mode").set_value(
        "Analyse"
    ).run()

    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "Tableau d'entrée" in contenu

    index_comparaison = next(
        index
        for index, etape in enumerate(app.session_state["etapes"])
        if etape["action"] == "comparaison"
        and etape["details"].get("tampon_gauche") == [1, 4]
    )
    next(
        slider for slider in app.slider if "Parcourir" in slider.label
    ).set_value(index_comparaison).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "Moitié gauche" in contenu
    assert "Moitié droite" in contenu
    assert "Tampon → A[0..3]" in contenu
    assert "fusion-active" in contenu
    assert "fusion-cible" in contenu
    assert not app.exception


def test_visualisation_legende_explications_controles_et_invalidation():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=10)
    _ouvrir_page(app, "Visualiser")
    next(button for button in app.button if "Calculer" in button.label).click().run(timeout=10)

    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(1).run(timeout=10)
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "array-visualisation" in contenu
    assert "array-cell-compare" in contenu
    assert "array-legend" in contenu
    assert "5 > 2" in contenu

    next(button for button in app.button if "Suivante" in button.label).click().run(timeout=10)
    assert app.session_state["curseur_etape"] == 2
    next(button for button in app.button if "Précédente" in button.label).click().run(timeout=10)
    assert app.session_state["curseur_etape"] == 1
    assert any(button.label == "▶ Reprendre l'animation" for button in app.button)
    next(button for button in app.button if button.label == "Recommencer").click().run(timeout=10)
    assert app.session_state["curseur_etape"] == 0
    next(button for button in app.button if "Lire l'animation" in button.label).click().run(timeout=10)
    assert app.session_state["animation_active"]
    next(button for button in app.button if "Mettre en pause" in button.label).click().run(timeout=10)
    assert not app.session_state["animation_active"]

    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri par sélection"
    ).run(timeout=10)
    next(button for button in app.button if "Calculer" in button.label).click().run(timeout=10)
    index_comparaison = next(
        index for index, etape in enumerate(app.session_state["etapes"])
        if etape["action"] == "comparaison"
    )
    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(
        index_comparaison
    ).run(timeout=10)
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "array-cell-selected" in contenu
    assert "array-cell-compare" in contenu

    next(field for field in app.text_input if "Nombres séparés" in field.label).set_value(
        "2, 1"
    ).run(timeout=10)
    assert "etapes" not in app.session_state
    assert not app.exception


def test_visualisation_parametres_et_fin_sans_evenement_de_progression():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")

    algorithmes = next(select for select in app.selectbox if select.label == "Algorithme")
    assert len(algorithmes.options) == len(ALGORITHMES)
    assert all(nom in option for nom, option in zip(ALGORITHMES, algorithmes.options))
    assert any(radio.label == "Source des données" for radio in app.radio)
    assert any(field.label == "Nombres séparés par des virgules" for field in app.text_input)

    next(button for button in app.button if "Calculer" in button.label).click().run()
    assert app.session_state["etapes"][0]["liste"] == [5, 2, 4, 1, 3]
    assert any("Prêt à démarrer" in str(caption.value) for caption in app.caption)
    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(1).run()
    assert app.session_state["curseur_etape"] == 1
    next(button for button in app.button if button.label == "Recommencer").click().run()
    assert app.session_state["curseur_etape"] == 0
    assert any("Visualisation réinitialisée" in str(caption.value) for caption in app.caption)

    next(radio for radio in app.radio if radio.label == "Source des données").set_value(
        "Liste aléatoire"
    ).run()
    next(slider for slider in app.slider if slider.label == "Nombre de valeurs").set_value(5)
    next(field for field in app.number_input if field.label == "Valeur minimale").set_value(3)
    next(field for field in app.number_input if field.label == "Valeur maximale").set_value(7)
    next(button for button in app.button if "Calculer" in button.label).click().run()

    entrees = app.session_state["etapes"][0]["liste"]
    assert len(entrees) == 5
    assert all(3 <= valeur <= 7 for valeur in entrees)
    derniere = len(app.session_state["etapes"]) - 1
    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(derniere).run()
    assert any("Tri terminé" in str(caption.value) for caption in app.caption)
    assert next(button for button in app.button if "Suivante" in button.label).disabled

    store = ProgressionStore()
    assert store.profile("Joueur")["xp"] == 0
    assert store.activity_history("Joueur", limit=10) == []
    assert not app.exception


def test_visualisation_distingue_zones_placees_et_prefixe_trie():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")
    texte = next(field for field in app.text_input if "Nombres séparés" in field.label)
    texte.set_value("4, 3, 2, 1").run()
    bouton_calcul = next(button for button in app.button if "Calculer" in button.label)
    bouton_calcul.click().run()

    etapes = app.session_state["etapes"]
    index_place = next(
        index for index, etape in enumerate(etapes)
        if etape["action"] == "comparaison"
        and etape["details"].get("zone_placee") == (3, 3)
    )
    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(
        index_place
    ).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "array-cell-placed" in contenu
    assert "placé définitivement" in contenu

    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri par sélection"
    ).run()
    texte.set_value("1, 2, 3").run()
    next(button for button in app.button if "Calculer" in button.label).click().run()
    etapes = app.session_state["etapes"]
    index_decision = next(
        index for index, etape in enumerate(etapes)
        if etape["action"] == "decision"
        and etape["details"].get("zone_placee") == (0, 0)
    )
    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(
        index_decision
    ).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "array-cell-placed" in contenu

    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri par insertion"
    ).run()
    texte.set_value("3, 1, 2").run()
    next(button for button in app.button if "Calculer" in button.label).click().run()
    etapes = app.session_state["etapes"]
    index_prefixe = next(
        index for index, etape in enumerate(etapes)
        if etape["action"] == "comparaison"
        and etape["indices"][1] == 2
    )
    next(slider for slider in app.slider if "Parcourir" in slider.label).set_value(
        index_prefixe
    ).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    assert "array-cell-sorted" in contenu
    assert "préfixe trié" in contenu
    assert "array-key" in contenu
    assert "Clé en cours" in contenu
    assert not app.exception


def test_visualisation_presente_complexites_et_compteurs_pour_les_six_tris():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")
    choix = next(select for select in app.selectbox if select.label == "Algorithme")
    bouton = next(button for button in app.button if "Calculer" in button.label)

    for nom in ALGORITHMES:
        choix.set_value(nom).run()
        bouton.click().run()
        captions = "\n".join(str(caption.value) for caption in app.caption)
        assert "Complexité temporelle (meilleur / moyen / pire)" in captions
        information = INFORMATIONS_ALGORITHMES[nom]
        assert (
            f"{information['meilleur']} / {information['moyen']} / "
            f"{information['pire']}"
        ) in captions
        assert "opérations = échanges + déplacements" in captions
        assert {metric.label for metric in app.metric} >= {
            "Comparaisons", "Échanges", "Déplacements / écritures", "Étape"
        }
        assert app.session_state["etapes"][-1]["action"] == "fin"
        assert not app.exception


def test_visualisation_rapide_affiche_pivot_et_zones_partitionnees():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")
    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri rapide"
    ).run()
    next(button for button in app.button if "Calculer" in button.label).click().run()

    index_comparaison = next(
        index
        for index, etape in enumerate(app.session_state["etapes"])
        if etape["action"] == "comparaison"
        and etape["details"].get("pivot_index") is not None
    )
    next(
        slider for slider in app.slider if "Parcourir" in slider.label
    ).set_value(index_comparaison).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    captions = "\n".join(str(caption.value) for caption in app.caption)
    assert "Partition trois voies" in contenu
    assert "Segment actif [" in captions
    assert "pivot" in captions
    assert "partition-compare" in contenu
    assert "partition-pivot" in contenu

    index_partition = next(
        index
        for index, etape in enumerate(app.session_state["etapes"])
        if etape["action"] == "partition" and etape["details"].get("zones")
    )
    next(
        slider for slider in app.slider if "Parcourir" in slider.label
    ).set_value(index_partition).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    captions = "\n".join(str(caption.value) for caption in app.caption)
    assert "partition-moins" in contenu
    assert "partition-egal" in contenu
    assert "partition-plus" in contenu
    assert "partition est terminée" in captions
    assert not app.exception


def test_visualisation_tas_synchronise_arbre_et_suffixe_trie():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Visualiser")
    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri par tas"
    ).run()
    next(button for button in app.button if "Calculer" in button.label).click().run()

    etapes = app.session_state["etapes"]
    index_heap_valide = next(
        index
        for index, etape in enumerate(etapes)
        if etape["details"].get("heap_valid")
    )
    next(
        slider for slider in app.slider if "Parcourir" in slider.label
    ).set_value(index_heap_valide).run()
    assert any("Max-heap valide" in str(caption.value) for caption in app.caption)

    index_extraction = next(
        index
        for index, etape in enumerate(etapes)
        if etape["action"] == "echange"
        and etape["details"].get("maximum_place") is not None
    )
    next(
        slider for slider in app.slider if "Parcourir" in slider.label
    ).set_value(index_extraction).run()
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    captions = "\n".join(str(caption.value) for caption in app.caption)
    assert any("Arbre binaire du max-heap" in expander.label for expander in app.expander)
    assert "Tableau et zone active" in contenu
    assert "suffixe trié" in captions
    assert "tas-echange" in contenu
    assert not app.exception


def test_visualisation_tas_passe_en_tableau_pour_grande_taille():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=10)
    _ouvrir_page(app, "Visualiser")
    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri par tas"
    ).run(timeout=10)
    next(
        field for field in app.text_input if "Nombres séparés" in field.label
    ).set_value(", ".join(str(value) for value in range(32))).run(timeout=10)
    next(button for button in app.button if "Calculer" in button.label).click().run(timeout=10)
    contenu = "\n".join(str(markdown.value) for markdown in app.markdown)
    captions = "\n".join(str(caption.value) for caption in app.caption)
    assert "l'arbre complet serait trop dense" in captions
    assert "Enfants" in str(app.dataframe[0].value)
    assert not app.exception


def test_session_exercices_score_indice_bilan_et_reinitialisation():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    next(select for select in app.selectbox if select.label == "Difficulté").set_value(
        "Débutant"
    )
    next(slider for slider in app.slider if slider.label == "Nombre de questions").set_value(3)
    next(button for button in app.button if "Lancer la session" in button.label).click().run()

    session = app.session_state["exercices_session"]
    assert len(session["questions"]) == 3
    assert ProgressionStore().profile("Joueur")["xp"] == 0
    assert ProgressionStore().activity_history("Joueur", limit=10) == []

    question = session["questions"][0]
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in app.button if "Valider ma réponse" in button.label).click().run()
    session = app.session_state["exercices_session"]
    assert session["questions"][0]["points"] == 100
    assert not app.exception
    next(button for button in app.button if button.label == "Question suivante").click().run()

    question = app.session_state["exercices_session"]["questions"][1]
    mauvaise = next(choix for choix in question["choix"] if choix != question["reponse_attendue"])
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(mauvaise)
    next(button for button in app.button if "Valider ma réponse" in button.label).click().run()
    question = app.session_state["exercices_session"]["questions"][1]
    self_tentatives = question["tentatives"]
    assert self_tentatives == 1 and not question["resolue"]

    next(button for button in app.button if "Afficher un indice" in button.label).click().run()
    question = app.session_state["exercices_session"]["questions"][1]
    assert question["indices_utilises"] == 1
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in app.button if "Valider ma réponse" in button.label).click().run()
    question = app.session_state["exercices_session"]["questions"][1]
    assert question["points"] == 50 and question["tentatives"] == 2
    next(button for button in app.button if button.label == "Question suivante").click().run()

    question = app.session_state["exercices_session"]["questions"][2]
    mauvaises = [choix for choix in question["choix"] if choix != question["reponse_attendue"]]
    for mauvaise in mauvaises[:2]:
        next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(mauvaise)
        next(button for button in app.button if "Valider ma réponse" in button.label).click().run()
    question = app.session_state["exercices_session"]["questions"][2]
    assert question["resolue"] and question["points"] == 0
    next(button for button in app.button if button.label == "Voir le bilan").click().run()
    stats = statistiques_session(app.session_state["exercices_session"])
    assert stats["score"] == 150 and stats["terminees"] == 3
    assert stats["premier_essai"] == 1 and stats["indices"] == 1
    next(button for button in app.button if button.label == "Nouvelle session").click().run()
    assert "exercices_session" not in app.session_state
    assert not app.exception


def test_niveau_debutant_propose_les_six_algorithmes():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    next(select for select in app.selectbox if select.label == "Difficulté").set_value(
        "Débutant"
    ).run()

    algorithmes = next(select for select in app.selectbox if select.label == "Algorithme")
    assert set(ALGORITHMES).issubset(set(algorithmes.options))


def test_changement_profil_efface_la_session_exercices_en_cours():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    next(button for button in app.button if "Lancer la session" in button.label).click().run()

    _changer_profil(app, "Lin")

    store = ProgressionStore()
    assert "exercices_session" not in app.session_state
    assert store.profile("Joueur")["xp"] == 0
    assert store.profile("Lin")["xp"] == 0


def test_mode_entrainement_cache_la_correction_jusqua_validation_et_affiche_le_bilan(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(tmp_path / "progression.sqlite3"))
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Entraînement"
    ).run()
    next(button for button in app.button if button.label == "Lancer l'entraînement").click().run()

    session = app.session_state["entrainement_session"]
    question = session["questions"][0]
    texte_avant_validation = "\n".join(
        [str(item.value) for item in app.markdown]
        + [str(item.value) for item in app.caption]
    )
    assert "Question 1 sur" in texte_avant_validation
    assert "Réponse attendue" not in texte_avant_validation
    assert question["explication"] not in texte_avant_validation

    mauvaise = next(choix for choix in question["choix"] if choix != question["reponse_attendue"])
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(mauvaise)
    next(button for button in app.button if button.label == "Valider ma réponse").click().run()
    assert session["questions"][0]["resolue"]
    assert not session["questions"][0]["correcte"]
    texte_apres_validation = "\n".join(str(item.value) for item in app.markdown)
    assert "Réponse attendue" in texte_apres_validation
    assert question["explication"] in texte_apres_validation

    next(button for button in app.button if button.label == "Question suivante").click().run()
    assert app.session_state["entrainement_session"]["index_question"] == 1
    assert not app.exception


def test_recompense_entrainement_reste_au_profil_de_depart_apres_changement():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Entraînement"
    ).run()
    next(button for button in app.button if button.label == "Lancer l'entraînement").click().run()
    question = app.session_state["entrainement_session"]["questions"][0]

    _changer_profil(app, "Lin")
    assert "entrainement_session" not in app.session_state

    store = ProgressionStore()
    assert store.profile("Joueur")["xp"] == 0
    assert store.profile("Lin")["xp"] == 0


def test_question_etat_revele_la_correction_apres_validation():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    session = creer_session(
        "Tri à bulles", "Débutant", 1, seed=11, nombres=[5, 1, 5, 2, 3]
    )
    question = session["questions"][0]
    app.session_state["exercices_session"] = session
    app.run()

    captions = "\n".join(str(caption.value) for caption in app.caption)
    assert "État après : à déterminer" in captions

    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in app.button if button.label == "Valider ma réponse").click().run()
    captions = "\n".join(str(caption.value) for caption in app.caption)
    assert f"État après : {question['reponse_attendue']}" in captions
    assert not app.exception


def test_comparer_presente_les_etats_vide_et_echec(monkeypatch):
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Comparer"
    ).run()

    assert any(
        "Aucune comparaison pour le moment" in str(item.value)
        for item in app.info
    )

    def echouer(algorithme, entree):
        if algorithme and entree:
            raise RuntimeError("échec simulé")
        raise AssertionError("Le test attend une entrée calculable.")

    monkeypatch.setattr("algorithmes.tri.calculer_statistiques", echouer)
    app.session_state["comparaison_resultats"] = [{"Algorithme": "Ancien résultat"}]
    app.session_state["comparaison_evolution"] = []
    next(
        button for button in app.button
        if "Comparer les six algorithmes" in button.label
    ).click().run()

    assert any(
        "La comparaison n'a pas abouti" in str(item.value)
        for item in app.error
    )
    assert any(
        "Détail technique" in item.label
        for item in app.expander
    )
    assert "RuntimeError : échec simulé" in app.session_state["comparaison_erreur"]
    assert "comparaison_resultats" not in app.session_state
    assert not app.exception


def test_comparer_et_experimenter_affichent_leurs_resultats():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Comparer"
    ).run()
    next(button for button in app.button if "Comparer les six algorithmes" in button.label).click().run()

    resultats = app.session_state["comparaison_resultats"]
    entree = app.session_state["comparaison_liste"]
    assert len(resultats) == len(ALGORITHMES)
    assert len(entree) == 60
    assert all(ligne["Résultat correct"] for ligne in resultats)
    assert all(
        ligne["Opérations"] == ligne["Échanges"] + ligne["Déplacements"]
        for ligne in resultats
    )
    assert all(ligne["Temps médian (ms)"] >= 0 for ligne in resultats)
    assert len(app.session_state["comparaison_evolution"]) > len(ALGORITHMES)
    analyse = analyser_mesures(resultats)[0]
    minimum_comparaisons = analyse["criteres"]["Comparaisons"]["minimum"]
    gagnants_comparaisons = analyse["criteres"]["Comparaisons"]["gagnants"]
    contenu = "\n".join(str(element.value) for element in app.markdown)
    assert "Analyse automatique" in contenu
    assert (
        f"Minimum de comparaisons :** {', '.join(gagnants_comparaisons)} "
        f"({minimum_comparaisons})" in contenu
    )
    assert not app.exception

    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Expérimenter"
    ).run()
    next(
        slider for slider in app.slider if slider.label == "Taille initiale (n)"
    ).set_value(20).run()
    next(
        slider for slider in app.slider
        if slider.label == "Taille maximale testée"
    ).set_value(40).run()
    next(button for button in app.button if "Lancer l'expérience" in button.label).click().run()

    assert len(app.session_state["resultats_experience"]) == 2 * len(ALGORITHMES)
    resultats_experience = app.session_state["resultats_experience"]
    assert sorted({ligne["Taille"] for ligne in resultats_experience}) == [20, 40]
    assert all(ligne["Résultat correct"] for ligne in resultats_experience)
    assert all("Facteur d'évolution" in ligne for ligne in resultats_experience)
    assert all(ligne["Temps médian (ms)"] >= 0 for ligne in resultats_experience)
    assert all(ligne["Répétitions"] == 5 for ligne in resultats_experience)
    assert any(
        "#### 4. Conclusion" in str(element.value)
        for element in app.markdown
    )
    assert any(
        "ne permet pas d'établir une complexité" in str(element.value)
        for element in app.caption
    )
    assert not app.exception


def test_defi_interactif_navigation_action_indice_reinitialisation_et_suivant():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Défi interactif"
    ).run()
    assert not any(
        "Visualiseur d'algorithmes" in str(element.value) for element in app.title
    )
    store = ProgressionStore()
    assert store.profile("Joueur")["xp"] == 0
    assert store.statistics("Joueur")["defis_valides_enregistres"] == 0
    assert not any(
        evenement["activite"] == "challenge"
        for evenement in store.activity_history("Joueur")
    )

    choix_algorithmes = next(select for select in app.selectbox if select.label == "Algorithme")
    assert set(ALGORITHMES).issubset(set(choix_algorithmes.options))
    defi = app.session_state["defi_interactif"]
    assert defi["curseur"] == 0
    assert len(defi["entree"]) == 3

    tache = defi["taches"][0]
    positions = tache["etape"]["indices"]
    next(select for select in app.selectbox if select.label == "Première position").set_value(
        positions[0]
    )
    next(select for select in app.selectbox if select.label == "Seconde position").set_value(
        positions[1]
    )
    next(button for button in app.button if button.label == "Valider l'opération").click().run()
    assert app.session_state["defi_interactif"]["curseur"] == 1
    assert app.session_state["defi_interactif"]["actions"] == 1

    next(button for button in app.button if button.label == "Indice progressif").click().run()
    assert app.session_state["defi_interactif"]["indices_utilises"] == 1
    next(button for button in app.button if button.label == "Réinitialiser").click().run()
    defi_reinitialise = app.session_state["defi_interactif"]
    assert defi_reinitialise["curseur"] == 0
    assert defi_reinitialise["actions"] == 0
    assert defi_reinitialise["indices_utilises"] == 0

    ancien_id = defi_reinitialise["id"]
    assert not any(button.label == "Défi suivant" for button in app.button)
    assert any(button.label == "Abandonner le défi" for button in app.button)
    xp_avant_abandon = store.profile("Joueur")["xp"]
    defis_avant_abandon = store.statistics("Joueur")["defis_valides_enregistres"]

    next(button for button in app.button if button.label == "Abandonner le défi").click().run()
    assert app.session_state["defi_interactif"]["id"] == ancien_id
    assert app.session_state["defi_interactif"]["curseur"] == 0
    assert any("aucune récompense" in str(item.value) for item in app.warning)
    next(button for button in app.button if button.label == "Confirmer l'abandon").click().run()
    assert app.session_state["defi_interactif"]["curseur"] == 0
    assert app.session_state["defi_interactif"]["id"] != ancien_id
    assert store.profile("Joueur")["xp"] == xp_avant_abandon
    assert store.statistics("Joueur")["defis_valides_enregistres"] == defis_avant_abandon
    assert not any(
        evenement["activite"] == "challenge"
        for evenement in store.activity_history("Joueur")
    )

    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri fusion"
    ).run()
    assert app.session_state["defi_interactif"]["nom_algorithme"] == "Tri fusion"
    assert any(select.label == "Dernière position gauche" for select in app.selectbox)
    assert not app.exception


def test_defi_termine_peut_etre_remplace_sans_recompense_supplementaire():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Défi interactif"
    ).run()
    _terminer_defi_interface(app)

    defi_termine_id = app.session_state["defi_interactif"]["id"]
    store = ProgressionStore()
    xp_apres_reussite = store.profile("Joueur")["xp"]
    defis_apres_reussite = store.statistics("Joueur")["defis_valides_enregistres"]
    assert any(button.label == "Défi suivant" for button in app.button)

    next(button for button in app.button if button.label == "Défi suivant").click().run()

    assert app.session_state["defi_interactif"]["id"] != defi_termine_id
    assert app.session_state["defi_interactif"]["curseur"] == 0
    assert store.profile("Joueur")["xp"] == xp_apres_reussite
    assert store.statistics("Joueur")["defis_valides_enregistres"] == defis_apres_reussite
    assert not app.exception


def test_defi_interactif_soumet_toutes_les_actions_composites():
    cas = (
        ("Tri fusion", [4, 1, 3, 2]),
        ("Tri rapide", [3, 1, 2, 3]),
        ("Tri par tas", [3, -1, 4, 2]),
    )
    for algorithme, entree in cas:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run()
        next(radio for radio in app.radio if radio.label == "Navigation").set_value(
            "Défi interactif"
        ).run()
        next(select for select in app.selectbox if select.label == "Algorithme").set_value(
            algorithme
        ).run()
        app.session_state["defi_interactif"] = creer_defi(
            algorithme, "Débutant", seed=17, nombres=entree
        )
        app.run()

        while not defi_termine(app.session_state["defi_interactif"]):
            defi = app.session_state["defi_interactif"]
            curseur = defi["curseur"]
            tache = defi["taches"][curseur]
            attendu = tache["attendu"]
            for index_champ, champ in enumerate(tache["schema"]["champs"]):
                if "partie" in champ:
                    valeur = attendu[champ["reponse"]][champ["partie"]]
                elif "correspondances" in champ:
                    clefs = sorted(champ["correspondances"], key=champ["correspondances"].get)
                    valeur = tuple(attendu[cle] for cle in clefs)
                else:
                    valeur = attendu[champ["reponse"]]

                if champ["type"] == "radio":
                    next(widget for widget in app.radio if widget.label == champ["label"]).set_value(valeur)
                else:
                    next(widget for widget in app.selectbox if widget.label == champ["label"]).set_value(valeur)

            next(button for button in app.button if button.label == "Valider l'opération").click().run()
            assert app.session_state["defi_interactif"]["curseur"] == curseur + 1, (
                algorithme, tache["action"], app.warning
            )
            assert not app.exception

        assert app.session_state["defi_interactif"]["actions"] == len(
            app.session_state["defi_interactif"]["taches"]
        )
        assert app.session_state["defi_interactif"]["erreurs"] == 0


def test_formats_defi_sont_jouables_dans_streamlit_et_presentent_un_bilan():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=10)
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Défi interactif"
    ).run(timeout=10)
    next(select for select in app.selectbox if select.label == "Mode de défi").set_value(
        "Maîtrise"
    ).run(timeout=10)

    assert app.session_state["defi_interactif"]["type_defi"] == "Maîtrise"
    _terminer_defi_interface(app)
    contenu = "\n".join(str(element.value) for element in app.markdown)
    assert "Bilan du défi" in contenu
    assert not any("Aucun score enregistré" in str(item.value) for item in app.caption)
    assert not app.exception
    next(button for button in app.button if button.label == "Exercices recommandés").click().run()
    assert next(radio for radio in app.radio if radio.label == "Navigation").value == "Exercices"
    assert not app.exception


def test_expiration_defi_rapide_est_un_echec_sans_recompense():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Défi interactif")
    next(select for select in app.selectbox if select.label == "Mode de défi").set_value(
        "Rapidité"
    ).run()

    defi = app.session_state["defi_interactif"]
    defi["temps_ecoule"] = True
    defi["tentatives"] = 1
    app.session_state["defi_interactif"] = defi
    app.run()

    assert next(metric for metric in app.metric if metric.label == "Réussite").value == "Non"
    assert any("Échec · temps écoulé" in str(element.value) for element in app.markdown)
    assert ProgressionStore().profile("Joueur")["xp"] == 0
    assert ProgressionStore().statistics("Joueur")["defis_valides_enregistres"] == 0
    assert not app.exception


def test_meilleur_score_defi_reste_lie_au_profil_de_depart():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _ouvrir_page(app, "Défi interactif")
    next(select for select in app.selectbox if select.label == "Mode de défi").set_value(
        "Identification"
    ).run()
    _terminer_defi_interface(app)

    next(button for button in app.button if button.label == "Réinitialiser").click().run()
    _changer_profil(app, "Lin")

    assert ProgressionStore().best_challenge_score("Joueur", "Identification") == 100
    assert ProgressionStore().best_challenge_score("Lin", "Identification") is None
    assert app.session_state["navigation_page"] == "Accueil"
    assert not any("Meilleur score · 100 %" in str(item.value) for item in app.caption)
    assert not app.exception


def test_session_intermediaire_ordre_et_avance_saisie():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    next(select for select in app.selectbox if select.label == "Difficulté").set_value(
        "Intermédiaire"
    ).run()
    next(select for select in app.selectbox if select.label == "Algorithme").set_value(
        "Tri fusion"
    )
    next(slider for slider in app.slider if slider.label == "Nombre de questions").set_value(3)
    next(button for button in app.button if "Lancer la session" in button.label).click().run()

    question = app.session_state["exercices_session"]["questions"][0]
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in app.button if "Valider ma réponse" in button.label).click().run()
    next(button for button in app.button if button.label == "Question suivante").click().run()

    question = app.session_state["exercices_session"]["questions"][1]
    assert question["format"] == "ordre"
    for position, label in enumerate(question["ordre_correct"], start=1):
        next(select for select in app.selectbox if select.label == f"Position {position}").set_value(label)
    next(button for button in app.button if "Valider ma réponse" in button.label).click().run()
    question = app.session_state["exercices_session"]["questions"][1]
    assert question["correcte"] and question["points"] == 100

    avance = AppTest.from_file(str(app_path)).run()
    next(radio for radio in avance.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    next(select for select in avance.selectbox if select.label == "Difficulté").set_value(
        "Avancé"
    ).run()
    next(select for select in avance.selectbox if select.label == "Algorithme").set_value(
        "Tri rapide"
    )
    next(button for button in avance.button if "Lancer la session" in button.label).click().run()
    question = avance.session_state["exercices_session"]["questions"][0]
    assert question["format"] == "texte"
    next(field for field in avance.text_input if field.label == "Ta réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in avance.button if "Valider ma réponse" in button.label).click().run()
    assert avance.session_state["exercices_session"]["questions"][0]["correcte"]
    assert not avance.exception


def test_reponse_textuelle_reste_visible_apres_un_rerun():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    session = creer_session("Tri rapide", "Avancé", 1, seed=5)
    app.session_state["exercices_session"] = session
    app.session_state["navigation_page"] = "Exercices"
    app.run()

    reponse = "ma réponse à reprendre"
    next(field for field in app.text_input if field.label == "Ta réponse").set_value(reponse)
    next(button for button in app.button if button.label == "Valider ma réponse").click().run()
    app.run()

    question = app.session_state["exercices_session"]["questions"][0]
    assert question["derniere_reponse"] == reponse
    assert next(field for field in app.text_input if field.label == "Ta réponse").value == reponse
    assert reponse in "\n".join(str(item.value) for item in app.markdown)
    assert not app.exception


def test_comprehension_garde_lexplication_jusqua_la_correction():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    session = creer_session("Tri fusion", "Intermédiaire", 3, seed=16)
    session["questions"] = [session["questions"][2]]
    session["index_question"] = 0
    app.session_state["exercices_session"] = session
    app.session_state["navigation_page"] = "Exercices"
    app.run(timeout=10)

    question = app.session_state["exercices_session"]["questions"][0]
    assert question["type"] == "comprehension"
    contenu = "\n".join(str(item.value) for item in app.markdown)
    assert question["prompt"] in contenu
    assert question["explication"] not in contenu

    mauvaise = next(option for option in question["choix"] if option != question["reponse_attendue"])
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(mauvaise)
    next(button for button in app.button if button.label == "Valider ma réponse").click().run(timeout=10)
    question = app.session_state["exercices_session"]["questions"][0]
    assert question["tentatives"] == 1 and not question["resolue"]
    contenu = "\n".join(str(item.value) for item in app.markdown)
    assert question["explication"] not in contenu

    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in app.button if button.label == "Valider ma réponse").click().run(timeout=10)
    question = app.session_state["exercices_session"]["questions"][0]
    contenu = "\n".join(str(item.value) for item in app.markdown)
    assert question["correcte"]
    assert question["explication"] in contenu
    assert question["reponse_attendue"] in contenu
    assert not app.exception


def test_recompenses_interface_et_nouvelle_partie_distincte(tmp_path):
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Exercices"
    ).run()
    next(button for button in app.button if "Lancer la session" in button.label).click().run()

    session_exercice = app.session_state["exercices_session"]
    identifiant_exercice = session_exercice["id"]
    question = session_exercice["questions"][0]
    next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
        question["reponse_attendue"]
    )
    next(button for button in app.button if button.label == "Valider ma réponse").click().run()
    assert app.session_state["exercices_session"]["questions"][0]["correcte"]
    assert app.session_state["exercices_session"]["id"] == identifiant_exercice
    store = ProgressionStore(tmp_path / "progression.sqlite3")
    xp_apres_exercice = store.profile("Joueur")["xp"]
    assert xp_apres_exercice == 20

    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Défi interactif"
    ).run()
    identifiant_defi = app.session_state["defi_interactif"]["id"]

    _terminer_defi_interface(app)
    xp_apres_defi = store.profile("Joueur")["xp"]
    assert xp_apres_defi > xp_apres_exercice
    app.run()
    assert app.session_state["defi_interactif"]["id"] == identifiant_defi
    assert store.profile("Joueur")["xp"] == xp_apres_defi

    next(button for button in app.button if button.label == "Réinitialiser").click().run()
    identifiant_defi_rejoue = app.session_state["defi_interactif"]["id"]
    assert identifiant_defi_rejoue != identifiant_defi
    _terminer_defi_interface(app)
    assert store.profile("Joueur")["xp"] == xp_apres_defi + 35
    assert not app.exception


def test_recompense_defi_reste_au_profil_de_depart_apres_changement():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Défi interactif"
    ).run()
    store = ProgressionStore()
    assert store.profile("Joueur")["xp"] == 0

    _changer_profil(app, "Lin")
    assert "defi_interactif" not in app.session_state
    assert store.profile("Joueur")["xp"] == 0
    assert store.profile("Lin")["xp"] == 0


def test_reinitialiser_defi_en_cours_conserve_le_profil_de_depart():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Défi interactif"
    ).run()
    identifiant_initial = app.session_state["defi_interactif"]["id"]

    _changer_profil(app, "Lin")
    assert "defi_interactif" not in app.session_state
    store = ProgressionStore()
    assert store.profile("Joueur")["xp"] == 0
    assert store.profile("Lin")["xp"] == 0
    assert not app.exception


def test_parcours_profil_vide_affiche_limites_et_navigation_directe():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Profil"
    ).run()

    contenu = "\n".join(
        [
            *(str(item.value) for item in app.markdown),
            *(str(item.value) for item in app.caption),
            *(str(item.value) for item in app.subheader),
            *(str(item.value) for item in app.header),
            *(str(item.value) for item in app.info),
        ]
    )
    assert "Mon parcours" in contenu
    assert "non évaluée" in contenu
    assert "complexités théoriques" in contenu
    assert "expériences et les comparaisons ne sont pas suivies" in contenu
    assert not app.exception

    next(button for button in app.button if button.label == "Ouvrir les exercices").click().run()
    assert next(radio for radio in app.radio if radio.label == "Navigation").value == "Exercices"
    assert not app.exception


def test_page_profil_affiche_les_donnees_et_equipe_un_titre():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    store = ProgressionStore()
    store.record_exercise_success(
        "Joueur",
        "Débutant",
        {
            "nom_algorithme": "Tri à bulles",
            "type": "etat",
            "correcte": True,
            "tentatives": 1,
            "indices_utilises": 0,
            "progression_id": "profil-type-question",
        },
    )
    store.record_exercise_success(
        "Joueur",
        "Débutant",
        {
            "nom_algorithme": "Tri à bulles",
            "type": "prediction_choix",
            "correcte": True,
            "tentatives": 1,
            "indices_utilises": 0,
            "progression_id": "profil-type-question-lisible",
        },
    )
    store.record_challenge_success(
        "Joueur",
        {
            "curseur": 1,
            "taches": [{}],
            "nom_algorithme": "Tri rapide",
            "difficulte": "Avancé",
            "erreurs": 0,
            "indices_utilises": 0,
        },
    )

    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Profil"
    ).run()

    contenu = "\n".join(
        [
            *(str(item.value) for item in app.markdown),
            *(str(item.value) for item in app.caption),
            *(str(item.value) for item in app.subheader),
            *(str(item.label) for item in app.metric),
            *(str(item.value) for item in app.metric),
        ]
    )
    assert "Joueur" in contenu
    assert "Expérience totale" in contenu
    assert "Défis validés enregistrés" in contenu
    assert "Algorithmes réussis" in contenu
    assert "Défi avancé" in contenu
    assert "Débloqué le" in contenu
    assert "Défi validé · Tri rapide · Avancé" in contenu
    assert "Exercice · Tri à bulles · Débutant · Prédiction à choix" in contenu
    assert not app.exception

    selecteur_titre = next(select for select in app.selectbox if select.label == "Titre actif")
    assert "Maître des défis" in selecteur_titre.options
    selecteur_titre.set_value("Maître des défis")
    next(button for button in app.button if button.label == "Équiper le titre").click().run()

    assert ProgressionStore().profile("Joueur")["titre"] == "Maître des défis"
    assert not app.exception

    historique_initial = store.activity_history("Joueur")
    profil_initial = store.profile("Joueur")
    scores_initiaux = store.best_challenge_scores("Joueur")
    app.run()
    assert store.activity_history("Joueur") == historique_initial
    assert store.profile("Joueur")["xp"] == profil_initial["xp"]
    assert store.profile("Joueur")["succes"] == profil_initial["succes"]
    assert store.best_challenge_scores("Joueur") == scores_initiaux


def test_experimenter_compare_plusieurs_distributions_a_protocole_constant():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Expérimenter"
    ).run()
    next(
        choix for choix in app.multiselect
        if choix.label == "Distributions à comparer"
    ).set_value(["Aléatoires", "Presque triées"]).run()
    next(
        slider for slider in app.slider if slider.label == "Taille initiale (n)"
    ).set_value(20).run()
    next(
        slider for slider in app.slider
        if slider.label == "Taille maximale testée"
    ).set_value(40).run()
    next(button for button in app.button if "Lancer l'expérience" in button.label).click().run()

    resultats = app.session_state["resultats_experience"]
    assert {ligne["Distribution"] for ligne in resultats} == {
        "Aléatoires", "Presque triées"
    }
    assert {ligne["Graine"] for ligne in resultats} == {42}
    assert {ligne["Taille"] for ligne in resultats} == {20, 40}
    assert all(ligne["Répétitions"] == 5 for ligne in resultats)
    assert all(ligne["Temps médian (ms)"] >= 0 for ligne in resultats)
    contenu = "\n".join(str(element.value) for element in app.markdown)
    assert "Différences observées entre distributions" in contenu
    assert any(
        element.value == "Temps de tri mesuré" for element in app.subheader
    )
    assert "chaque algorithme reçoit la même entrée" in "\n".join(
        str(element.value) for element in app.caption
    )
    assert "algorithme et graine identiques" in "\n".join(
        str(element.value) for element in app.caption
    )
    assert ProgressionStore().profile("Joueur")["xp"] == 0
    assert not app.exception


def test_recommandation_du_profil_lance_le_type_a_retravailler(tmp_path, monkeypatch):
    chemin_db = tmp_path / "recommandation.sqlite3"
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(chemin_db))
    store = ProgressionStore(chemin_db)
    store.record_exercise_result(
        "Ada",
        "Intermédiaire",
        {
            "id": "comprehension-echouee",
            "type": "comprehension",
            "nom_algorithme": "Tri fusion",
            "correcte": False,
            "tentatives": 2,
            "indices_utilises": 1,
            "reponses": ["mauvaise", "encore mauvaise"],
        },
    )

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _changer_profil(app, "Ada")
    next(radio for radio in app.radio if radio.label == "Navigation").set_value(
        "Profil"
    ).run()
    next(
        button for button in app.button
        if button.label == "Lancer l'exercice recommandé"
    ).click().run()

    session = app.session_state["exercices_session"]
    assert app.session_state["navigation_page"] == "Exercices"
    assert session["profil_nom"] == "Ada"
    assert len(session["questions"]) == 1
    assert session["questions"][0]["type"] == "comprehension"
    assert not app.exception


def test_echec_final_exercice_est_enregistre_une_fois_malgre_les_reruns(
    tmp_path, monkeypatch
):
    chemin_db = tmp_path / "echecs.sqlite3"
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(chemin_db))
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _changer_profil(app, "Ada")
    session = creer_session(
        "Tri à bulles", "Débutant", 1, seed=11, nombres=[5, 1, 5, 2, 3]
    )
    app.session_state["exercices_session"] = session
    app.session_state["navigation_page"] = "Exercices"
    app.run()
    question = session["questions"][0]
    mauvaises = [
        choix for choix in question["choix"]
        if choix != question["reponse_attendue"]
    ][:2]

    for mauvaise in mauvaises:
        next(radio for radio in app.radio if radio.label == "Choisis une réponse").set_value(
            mauvaise
        )
        next(button for button in app.button if button.label == "Valider ma réponse").click().run()

    store = ProgressionStore(chemin_db)
    echecs = [
        evenement for evenement in store.activity_history("Ada")
        if evenement["activite"] == "exercise"
    ]
    assert len(echecs) == 1
    assert echecs[0]["reussie"] is False
    assert store.profile("Ada")["xp"] == 0
    app.run()
    assert len([
        evenement for evenement in store.activity_history("Ada")
        if evenement["activite"] == "exercise"
    ]) == 1
    assert not app.exception


def test_tableau_bord_filtre_isole_le_profil_et_ne_reecrit_pas_lhistorique(
    tmp_path, monkeypatch
):
    chemin_db = tmp_path / "tableau-bord-interface.sqlite3"
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(chemin_db))
    store = ProgressionStore(chemin_db)
    for identifiant, correcte, algorithme in (
        ("bonne", True, "Tri à bulles"), ("mauvaise", False, "Tri à bulles"),
    ):
        store.record_exercise_result(
            "Ada", "Débutant", {
                "id": identifiant, "type": "etat", "nom_algorithme": algorithme,
                "correcte": correcte, "tentatives": 1 if correcte else 2,
                "indices_utilises": 0, "reponses": [],
            },
        )
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _changer_profil(app, "Ada")
    next(radio for radio in app.radio if radio.label == "Navigation").set_value("Profil").run()

    assert next(metric for metric in app.metric if metric.label == "Activités terminées").value == "2"
    assert next(metric for metric in app.metric if metric.label == "Réussite aux questions").value == "50%"
    selectbox = next(item for item in app.selectbox if item.label == "Type d'activité")
    selectbox.set_value("Défis").run()
    contenu = "\n".join(str(item.value) for item in app.info)
    assert "Aucune réponse d'exercice évaluable" in contenu
    assert next(metric for metric in app.metric if metric.label == "Activités terminées").value == "0"
    assert next(metric for metric in app.metric if metric.label == "Réussite aux questions").value == "—"

    _changer_profil(app, "Lin")
    _ouvrir_page(app, "Profil")
    assert any(item.value == "Ton parcours commence ici" for item in app.subheader)
    assert len(store.activity_history("Ada")) == 2
    app.run()
    assert len(store.activity_history("Ada")) == 2
    assert not app.exception


def test_tableau_bord_vide_navigue_vers_les_exercices(tmp_path, monkeypatch):
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(tmp_path / "profil-vide.sqlite3"))
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value("Profil").run()
    next(button for button in app.button if button.label == "Commencer un exercice").click().run()

    assert next(radio for radio in app.radio if radio.label == "Navigation").value == "Exercices"
    assert not app.exception


def test_tableau_bord_signale_une_erreur_de_lecture_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(tmp_path / "lecture-en-erreur.sqlite3"))

    def lecture_en_erreur(*args, **kwargs):
        raise sqlite3.OperationalError("lecture interrompue")

    monkeypatch.setattr(ProgressionStore, "dashboard_data", lecture_en_erreur)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    next(radio for radio in app.radio if radio.label == "Navigation").set_value("Profil").run()

    assert any("lecture interrompue" in str(item.value) for item in app.warning)
    assert not app.exception


def test_accueil_vide_affiche_une_premiere_etape_et_navigue_sans_recompenser():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    store = ProgressionStore()

    assert next(radio for radio in app.radio if radio.label == "Navigation").value == "Accueil"
    contenu = "\n".join(str(item.value) for item in app.markdown)
    assert "PREMIÈRE ÉTAPE" in contenu
    assert "Choisis ta prochaine étape" in contenu
    assert "Lancer une visualisation" in [button.label for button in app.button]
    assert "Aller aux exercices" in [button.label for button in app.button]
    assert store.activity_history("Joueur") == []
    assert store.profile("Joueur")["xp"] == 0
    assert not any(item["debloque"] for item in store.profile("Joueur")["succes"])

    app.run()
    assert store.activity_history("Joueur") == []
    assert store.profile("Joueur")["xp"] == 0

    next(button for button in app.button if button.label == "Lancer une visualisation").click().run()
    assert next(radio for radio in app.radio if radio.label == "Navigation").value == "Visualiser"
    assert store.activity_history("Joueur") == []
    assert not app.exception


def test_accueil_avec_historique_propose_une_reprise_sans_nouvel_evenement():
    store = ProgressionStore()
    store.record_exercise_result(
        "Ada",
        "Intermédiaire",
        {
            "id": "accueil-echec-comprehension",
            "type": "comprehension",
            "nom_algorithme": "Tri fusion",
            "correcte": False,
            "tentatives": 2,
            "indices_utilises": 1,
            "reponses": ["réponse incorrecte"],
        },
    )
    historique_initial = store.activity_history("Ada")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()
    _changer_profil(app, "Ada")

    contenu = "\n".join(str(item.value) for item in app.markdown)
    assert "POUR CONTINUER" in contenu
    assert any(button.label == "Continuer avec la recommandation" for button in app.button)
    next(button for button in app.button if button.label == "Continuer avec la recommandation").click().run()

    recommandation = store.parcours_pedagogique("Ada")["recommandation"]
    assert app.session_state["navigation_page"] == recommandation["page"]
    assert store.activity_history("Ada") == historique_initial
    assert store.profile("Ada")["xp"] == 0
    assert not any(item["debloque"] for item in store.profile("Ada")["succes"])
    assert not app.exception
