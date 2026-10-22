import sqlite3
from pathlib import Path
import secrets

import pytest
from streamlit.testing.v1 import AppTest

import algorithmes.progression as progression_module
from algorithmes.progression import ProgressionAccessGuard, ProgressionStore

def _nouveau_pin():
    return f"{secrets.randbelow(1_000_000):06d}"


_PIN_ADA = _nouveau_pin()
_PIN_LIN = _nouveau_pin()
while _PIN_LIN == _PIN_ADA:
    _PIN_LIN = _nouveau_pin()
_PIN_INCORRECT = _nouveau_pin()
while _PIN_INCORRECT in (_PIN_ADA, _PIN_LIN):
    _PIN_INCORRECT = _nouveau_pin()


def _chemin_app():
    return str(Path(__file__).resolve().parents[1] / "app.py")


def _connecter(app, nom, pin):
    mode = next(radio for radio in app.radio if radio.label == "Accès")
    if mode.value != "Se connecter":
        mode.set_value("Se connecter").run()
    next(select for select in app.selectbox if select.label == "Profil").set_value(nom).run()
    next(field for field in app.text_input if field.label == "Code personnel").set_value(pin)
    next(button for button in app.button if button.label == "Déverrouiller").click().run()


def test_creation_profil_et_code_valide(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")

    jeton = store.create_profile("Ada", _PIN_ADA, _PIN_ADA)

    assert store.profile_has_pin("Ada")
    assert store.is_authorized("ada", jeton)


def test_creation_refuse_deux_codes_differents(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")

    with pytest.raises(ValueError, match="ne correspondent pas"):
        store.create_profile("Ada", _PIN_ADA, _PIN_LIN)

    assert store.profile_names() == []


def test_creation_refuse_code_sans_six_chiffres(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")

    with pytest.raises(ValueError, match="exactement 6 chiffres"):
        store.create_profile("Ada", _PIN_ADA[:-1], _PIN_ADA[:-1])

    assert store.profile_names() == []


def test_connexion_et_refus_code_incorrect(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)

    assert store.verify_pin("Ada", _PIN_INCORRECT) is None
    jeton = store.verify_pin("Ada", _PIN_ADA)
    assert store.is_authorized("Ada", jeton)


def test_acces_et_ecriture_exigent_une_autorisation_du_profil(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")
    jeton_ada = store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    store.create_profile("Lin", _PIN_LIN, _PIN_LIN)
    acces = ProgressionAccessGuard(store, lambda: jeton_ada)

    with pytest.raises(PermissionError):
        acces.profile("Lin")
    with pytest.raises(PermissionError):
        acces.record_exercise_success(
            "Lin",
            "Débutant",
            {"nom_algorithme": "Tri à bulles", "type": "etat", "correcte": True},
        )
    assert store.profile("Lin")["xp"] == 0


def test_acces_direct_lecture_et_ecriture_refuses_sans_jeton(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    acces = ProgressionAccessGuard(store, lambda: None)

    with pytest.raises(PermissionError):
        acces.profile("Ada")
    with pytest.raises(PermissionError):
        acces.activity_history("Ada")
    with pytest.raises(PermissionError):
        acces.record_exercise_success(
            "Ada",
            "Débutant",
            {"nom_algorithme": "Tri à bulles", "type": "etat", "correcte": True},
        )
    assert store.profile("Ada")["xp"] == 0


def test_profil_verrouille_et_changement_de_profil_invalident_le_jeton(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")
    jeton_ada = store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    store.create_profile("Lin", _PIN_LIN, _PIN_LIN)

    assert not store.is_authorized("Ada", None)
    assert not store.is_authorized("Lin", jeton_ada)
    assert not store.is_authorized("Ada", jeton_ada + "x")


def test_limitation_des_tentatives(tmp_path):
    store = ProgressionStore(tmp_path / "profils.sqlite3")
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)

    for _ in range(5):
        assert store.verify_pin("Ada", _PIN_INCORRECT) is None
    assert store.verify_pin("Ada", _PIN_ADA) is None


def test_code_correct_redevient_valide_apres_expiration_du_verrou(tmp_path, monkeypatch):
    store = ProgressionStore(tmp_path / "profils.sqlite3")
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    horloge = [1_000]
    monkeypatch.setattr(progression_module.time, "time", lambda: horloge[0])

    for _ in range(5):
        assert store.verify_pin("Ada", _PIN_INCORRECT) is None
    assert store.verify_pin("Ada", _PIN_ADA) is None

    horloge[0] += progression_module._PIN_VERROU_SECONDES + 1
    jeton = store.verify_pin("Ada", _PIN_ADA)
    assert store.is_authorized("Ada", jeton)


def test_migration_ancienne_base_preserve_historique(tmp_path):
    chemin = tmp_path / "ancienne.sqlite3"
    with sqlite3.connect(chemin) as connection:
        connection.execute(
            "CREATE TABLE profiles (profile_id TEXT PRIMARY KEY, "
            "display_name TEXT NOT NULL, active_title TEXT NOT NULL DEFAULT '')"
        )
        connection.execute(
            "CREATE TABLE progress_events (profile_id TEXT NOT NULL, event_key TEXT "
            "NOT NULL, xp INTEGER NOT NULL, activity TEXT NOT NULL, algorithm TEXT "
            "NOT NULL, difficulty TEXT NOT NULL, metadata TEXT NOT NULL, "
            "created_at TEXT NOT NULL, PRIMARY KEY (profile_id, event_key))"
        )
        connection.execute(
            "CREATE TABLE unlocked_achievements (profile_id TEXT NOT NULL, "
            "achievement_id TEXT NOT NULL, unlocked_at TEXT NOT NULL, "
            "PRIMARY KEY (profile_id, achievement_id))"
        )
        connection.execute(
            "CREATE TABLE challenge_best_scores (profile_id TEXT NOT NULL, "
            "challenge_type TEXT NOT NULL, best_score INTEGER NOT NULL, "
            "updated_at TEXT NOT NULL, PRIMARY KEY (profile_id, challenge_type))"
        )
        connection.execute("INSERT INTO profiles VALUES ('ada', 'Ada', 'Titre')")
        connection.execute(
            "INSERT INTO progress_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("ada", "legacy", 27, "exercise", "Tri à bulles", "Débutant", "{}", "2020-01-01"),
        )
        connection.execute(
            "INSERT INTO unlocked_achievements VALUES (?, ?, ?)",
            ("ada", "sans_erreur", "2020-01-02"),
        )
        connection.execute(
            "INSERT INTO challenge_best_scores VALUES (?, ?, ?, ?)",
            ("ada", "Identification", 92, "2020-01-03"),
        )

    store = ProgressionStore(chemin)
    assert not store.profile_has_pin("Ada")
    jeton = store.set_initial_pin("Ada", _PIN_ADA, _PIN_ADA)
    assert store.is_authorized("Ada", jeton)
    assert store.profile("Ada")["xp"] == 27
    profil = store.profile("Ada")
    assert profil["titre"] == "Titre"
    assert next(succes for succes in profil["succes"] if succes["id"] == "sans_erreur")["debloque"]
    assert store.best_challenge_score("Ada", "Identification") == 92
    assert store.activity_history("Ada")[0]["date"] == "2020-01-01"


def test_code_en_clair_absent_de_la_base(tmp_path):
    chemin = tmp_path / "profils.sqlite3"
    store = ProgressionStore(chemin)
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)

    with sqlite3.connect(chemin) as connection:
        verifier = connection.execute(
            "SELECT pin_verifier FROM profiles WHERE profile_id = 'ada'"
        ).fetchone()[0]

    assert verifier.startswith("scrypt$")
    assert _PIN_ADA not in verifier


def test_verificateur_scrypt_valide_reste_compatible():
    verifier = ProgressionStore._deriver_verificateur_pin(_PIN_ADA)

    assert ProgressionStore._verifier_pin(_PIN_ADA, verifier)
    assert not ProgressionStore._verifier_pin(_PIN_INCORRECT, verifier)


@pytest.mark.parametrize(
    "verifier",
    [
        "scrypt$1073741824$8$1$" + "00" * 16 + "$" + "00" * 32,
        "scrypt$16384$2147483647$1$" + "00" * 16 + "$" + "00" * 32,
        "scrypt$16384$8$2147483647$" + "00" * 16 + "$" + "00" * 32,
        "scrypt$16384$8$1$00$" + "00" * 32,
        "scrypt$16384$8$1$" + "00" * 16 + "$00",
        "scrypt$" + "9" * 1000 + "$8$1$" + "00" * 16 + "$" + "00" * 32,
        "verifier malformé",
    ],
)
def test_verificateur_scrypt_invalide_refuse_avant_derivation(verifier, monkeypatch):
    def derivation_interdite(*args, **kwargs):
        pytest.fail("scrypt ne doit pas être appelé pour un vérificateur invalide")

    monkeypatch.setattr(progression_module.hashlib, "scrypt", derivation_interdite)

    assert not ProgressionStore._verifier_pin(_PIN_ADA, verifier)


def test_creation_interface_ne_conserve_pas_le_code_en_session(tmp_path):
    app = AppTest.from_file(_chemin_app()).run(timeout=10)
    next(field for field in app.text_input if field.label == "Nom du profil").set_value("Ada")
    next(field for field in app.text_input if "Code personnel à 6 chiffres" in field.label).set_value(_PIN_ADA)
    next(field for field in app.text_input if field.label == "Confirmer le code personnel").set_value(_PIN_ADA)
    next(button for button in app.button if button.label == "Créer et ouvrir le profil").click().run(timeout=10)

    assert any(radio.label == "Navigation" for radio in app.radio)
    assert all(value != _PIN_ADA for value in app.session_state.values())
    assert not app.exception


def test_interface_refuse_code_incorrect_et_ne_devoile_pas_la_progression(tmp_path):
    store = ProgressionStore(tmp_path / "progression.sqlite3")
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    store.record_exercise_success(
        "Ada", "Débutant", {"nom_algorithme": "Tri à bulles", "type": "etat", "correcte": True}
    )
    app = AppTest.from_file(_chemin_app()).run(timeout=10)

    _connecter(app, "Ada", _PIN_INCORRECT)

    assert not any(radio.label == "Navigation" for radio in app.radio)
    assert any("Code incorrect" in item.value for item in app.error)
    assert not any(metric.label == "Expérience" for metric in app.metric)
    assert all(value != _PIN_INCORRECT for value in app.session_state.values())
    assert store.profile("Ada")["xp"] > 0
    assert not app.exception


def test_session_modifiee_ne_peut_pas_changer_le_profil_autorise(tmp_path):
    store = ProgressionStore(tmp_path / "progression.sqlite3")
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    store.create_profile("Lin", _PIN_LIN, _PIN_LIN)
    app = AppTest.from_file(_chemin_app()).run(timeout=10)
    _connecter(app, "Ada", _PIN_ADA)

    app.session_state["profil_nom"] = "Lin"
    app.run(timeout=10)

    assert not any(radio.label == "Navigation" for radio in app.radio)
    assert "profil_jeton" not in app.session_state
    assert not any(metric.label == "Expérience" for metric in app.metric)
    assert not app.exception


def test_deconnexion_verrouille_le_profil_et_les_pages(tmp_path):
    ProgressionStore(tmp_path / "progression.sqlite3").create_profile(
        "Ada", _PIN_ADA, _PIN_ADA
    )
    app = AppTest.from_file(_chemin_app()).run(timeout=10)
    _connecter(app, "Ada", _PIN_ADA)
    assert any(radio.label == "Navigation" for radio in app.radio)
    app.session_state["defi_abandon_confirmation"] = "ancien-defi"
    app.session_state["defi_interactif"] = {"profil_nom": "Ada"}

    next(button for button in app.button if button.label == "Verrouiller le profil").click().run(timeout=10)

    assert "profil_nom" not in app.session_state
    assert "profil_jeton" not in app.session_state
    assert not any(value == "Ada" for value in app.session_state.values())
    assert "defi_abandon_confirmation" not in app.session_state
    assert "defi_interactif" not in app.session_state
    assert not any(radio.label == "Navigation" for radio in app.radio)
    assert not app.exception


def test_navigation_entre_pages_ne_modifie_pas_la_progression(tmp_path):
    chemin = tmp_path / "progression.sqlite3"
    store = ProgressionStore(chemin)
    store.create_profile("Ada", _PIN_ADA, _PIN_ADA)
    app = AppTest.from_file(_chemin_app()).run(timeout=10)
    _connecter(app, "Ada", _PIN_ADA)

    for page in (
        "Accueil", "Visualiser", "Comparer", "Expérimenter", "Exercices",
        "Entraînement", "Défi interactif", "Manipulation", "Profil",
    ):
        next(radio for radio in app.radio if radio.label == "Navigation").set_value(page).run(timeout=10)
        assert not app.exception

    with sqlite3.connect(chemin) as connection:
        assert connection.execute("SELECT COUNT(*) FROM progress_events").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM unlocked_achievements").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM challenge_best_scores").fetchone()[0] == 0


def test_migration_interface_protege_profil_historique_sans_perte_xp(tmp_path):
    chemin = tmp_path / "progression.sqlite3"
    store = ProgressionStore(chemin)
    store.record_exercise_success(
        "Ada", "Débutant", {"nom_algorithme": "Tri à bulles", "type": "etat", "correcte": True}
    )
    xp_avant = store.profile("Ada")["xp"]
    app = AppTest.from_file(_chemin_app()).run(timeout=10)
    next(select for select in app.selectbox if select.label == "Profil").set_value("Ada").run()

    assert any("profil historique" in item.value for item in app.warning)
    next(field for field in app.text_input if field.label == "Nouveau code personnel à 6 chiffres").set_value(_PIN_LIN)
    next(field for field in app.text_input if field.label == "Confirmer le code personnel").set_value(_PIN_LIN)
    next(button for button in app.button if button.label == "Définir le code et ouvrir le profil").click().run(timeout=10)

    assert store.profile_has_pin("Ada")
    assert store.profile("Ada")["xp"] == xp_avant
    assert all(value != _PIN_LIN for value in app.session_state.values())
    assert not app.exception
