"""Règles et stockage SQLite de la progression AlgoLab."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import base64
import binascii
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import unicodedata
from typing import Any, Iterator

from algorithmes.exercices import DIFFICULTES
from algorithmes.tri import ALGORITHMES
from algorithmes.manipulation import verifier_reussite


NIVEAUX = (
    ("Débutant", 0),
    ("Apprenti", 100),
    ("Pratiquant", 250),
    ("Expert", 500),
    ("Maître", 800),
)

SUCCES = {
    "six_algorithmes": {
        "nom": "Panorama complet",
        "condition": "Réussir au moins une activité sur chacun des six tris.",
        "titre": "Architecte des tris",
        "xp": 40,
    },
    "sans_erreur": {
        "nom": "Sans faute",
        "condition": "Terminer une session d'exercices ou un défi sans réponse incorrecte.",
        "titre": "Précision absolue",
        "xp": 25,
    },
    "sans_indice": {
        "nom": "En autonomie",
        "condition": "Terminer une session d'exercices ou un défi réussi sans indice.",
        "titre": "Autonome",
        "xp": 25,
    },
    "defi_avance": {
        "nom": "Défi avancé",
        "condition": "Terminer un défi de difficulté Avancé.",
        "titre": "Maître des défis",
        "xp": 35,
    },
}

RECOMPENSE_EXERCICE = 10
BONUS_PREMIER_ESSAI = 5
BONUS_EXERCICE_SANS_INDICE = 5
RECOMPENSE_DEFI = {"Débutant": 20, "Intermédiaire": 35, "Avancé": 50}
BONUS_DEFI_SANS_ERREUR = 10
BONUS_DEFI_SANS_INDICE = 5
_PIN_NOMBRE_ESSAIS_MAX = 5
_PIN_VERROU_SECONDES = 30
_JETON_DUREE_SECONDES = 12 * 60 * 60
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_AUTH_SECRET = secrets.token_bytes(32)


def _valider_difficulte_exercice(difficulte: str | None) -> None:
    if difficulte not in DIFFICULTES:
        raise ValueError(f"Difficulté d'exercice inconnue ou manquante : {difficulte}.")


class ProgressionAccessGuard:
    """Vérifie le jeton lié au profil avant tout accès sensible au store."""

    _METHODES_PROTEGEES = {
        "profile", "statistics", "activity_history", "dashboard_data",
        "parcours_pedagogique", "best_challenge_score", "best_challenge_scores",
        "achievements", "set_title", "record_exercise_success",
        "record_exercise_result", "complete_exercise_session",
        "record_challenge_success", "record_manipulation_success",
    }

    def __init__(self, store: Any, jeton_courant: Any):
        self._store = store
        self._jeton_courant = jeton_courant

    def __getattr__(self, nom_methode: str) -> Any:
        methode = getattr(self._store, nom_methode)
        if nom_methode not in self._METHODES_PROTEGEES:
            return methode

        def methode_protegee(*args: Any, **kwargs: Any) -> Any:
            nom_profil = args[0] if args else kwargs.get("nom")
            jeton = self._jeton_courant()
            if not self._store.is_authorized(nom_profil, jeton):
                raise PermissionError("Profil verrouillé ou autorisation expirée.")
            return methode(*args, **kwargs)

        return methode_protegee


def _competences_question(question_type: str, notion: Any = None) -> list[str]:
    competences = []
    if question_type in ("etat", "prediction_entrainement"):
        competences.append("etat_suivant")
    if question_type in (
        "prediction", "prediction_choix", "prediction_texte", "ordre",
    ):
        competences.append("etapes_algorithme")
    if question_type == "comprehension":
        competences.append("comparaisons_echanges")
    if question_type == "choix_algorithme_entrainement":
        competences.append("choix_algorithme")
        notion_texte = str(notion or "").casefold()
        if any(mot in notion_texte for mot in ("complexité", "pire cas", "mémoire")):
            competences.append("complexite")
    return competences


def _reussite_evenement(evenement: dict[str, Any]) -> bool:
    metadata = evenement.get("metadata", {})
    if evenement.get("activite") == "exercise":
        return metadata.get("correcte", True) is not False
    return evenement.get("activite") in ("challenge", "manipulation")


def _lire_metadata(valeur: str) -> dict[str, Any]:
    try:
        metadata = json.loads(valeur)
    except (TypeError, ValueError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def chemin_base() -> Path:
    """Retourne le chemin local configurable de la base de progression."""
    chemin_configure = os.environ.get("ALGOLAB_DB_PATH")
    if chemin_configure:
        return Path(chemin_configure).expanduser()
    return Path(__file__).resolve().parents[1] / ".algolab" / "progression.sqlite3"


def normaliser_profil(nom: str) -> tuple[str, str]:
    affichage = unicodedata.normalize("NFKC", str(nom)).strip()
    if not affichage or len(affichage) > 32:
        raise ValueError("Le nom du profil doit contenir de 1 à 32 caractères.")
    return affichage.casefold(), affichage


class ProgressionStore:
    """Stocke événements et succès avec unicité par profil et activité."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else chemin_base()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    active_title TEXT NOT NULL DEFAULT '',
                    pin_verifier TEXT,
                    pin_failures INTEGER NOT NULL DEFAULT 0,
                    pin_locked_until REAL NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS progress_events (
                    profile_id TEXT NOT NULL,
                    event_key TEXT NOT NULL,
                    xp INTEGER NOT NULL CHECK (xp >= 0),
                    activity TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (profile_id, event_key),
                    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
                );
                CREATE TABLE IF NOT EXISTS unlocked_achievements (
                    profile_id TEXT NOT NULL,
                    achievement_id TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (profile_id, achievement_id),
                    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
                );
                CREATE TABLE IF NOT EXISTS challenge_best_scores (
                    profile_id TEXT NOT NULL,
                    challenge_type TEXT NOT NULL,
                    best_score INTEGER NOT NULL CHECK (best_score BETWEEN 0 AND 100),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (profile_id, challenge_type),
                    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
                );
                """
            )
            colonnes_profil = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(profiles)")
            }
            for nom_colonne, definition in (
                ("pin_verifier", "TEXT"),
                ("pin_failures", "INTEGER NOT NULL DEFAULT 0"),
                ("pin_locked_until", "REAL NOT NULL DEFAULT 0"),
            ):
                if nom_colonne not in colonnes_profil:
                    connection.execute(
                        f"ALTER TABLE profiles ADD COLUMN {nom_colonne} {definition}"
                    )
            connection.commit()
        self._auth_secret = _AUTH_SECRET

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _ensure_profile(connection: sqlite3.Connection, profile_id: str, display_name: str) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO profiles (profile_id, display_name) VALUES (?, ?)",
            (profile_id, display_name),
        )

    def ensure_profile(self, nom: str) -> str:
        profile_id, display_name = normaliser_profil(nom)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
        return profile_id

    @staticmethod
    def _valider_pin(pin: str, confirmation: str | None = None) -> None:
        if not isinstance(pin, str) or re.fullmatch(r"[0-9]{6}", pin) is None:
            raise ValueError("Le code personnel doit contenir exactement 6 chiffres.")
        if confirmation is not None and (
            not isinstance(confirmation, str)
            or not hmac.compare_digest(pin, confirmation)
        ):
            raise ValueError("Les deux codes personnels ne correspondent pas.")

    @staticmethod
    def _deriver_verificateur_pin(pin: str) -> str:
        sel = secrets.token_bytes(16)
        empreinte = hashlib.scrypt(
            pin.encode("ascii"),
            salt=sel,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=32,
            maxmem=64 * 1024 * 1024,
        )
        return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${sel.hex()}${empreinte.hex()}"

    @staticmethod
    def _verifier_pin(pin: str, verifier: str) -> bool:
        try:
            # Reject oversized or non-canonical records before parsing/deriving.
            if not isinstance(verifier, str) or len(verifier) > 128:
                return False
            algorithme, n, r, p, sel_hex, empreinte_hex = verifier.split("$")
            if (
                algorithme != "scrypt"
                or n != str(_SCRYPT_N)
                or r != str(_SCRYPT_R)
                or p != str(_SCRYPT_P)
                or re.fullmatch(r"[0-9a-f]{32}", sel_hex) is None
                or re.fullmatch(r"[0-9a-f]{64}", empreinte_hex) is None
            ):
                return False
            empreinte = hashlib.scrypt(
                pin.encode("ascii"),
                salt=bytes.fromhex(sel_hex),
                n=_SCRYPT_N,
                r=_SCRYPT_R,
                p=_SCRYPT_P,
                dklen=32,
                maxmem=64 * 1024 * 1024,
            )
            return hmac.compare_digest(empreinte.hex(), empreinte_hex)
        except (ValueError, TypeError, UnicodeEncodeError, OverflowError):
            return False

    def _creer_jeton(self, profile_id: str) -> str:
        contenu = json.dumps(
            [profile_id, int(time.time()) + _JETON_DUREE_SECONDES, secrets.token_hex(16)],
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.new(self._auth_secret, contenu, hashlib.sha256).digest()
        return (
            base64.urlsafe_b64encode(contenu).decode("ascii").rstrip("=")
            + "."
            + base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        )

    def is_authorized(self, nom: str, jeton: str | None) -> bool:
        if not isinstance(jeton, str) or "." not in jeton:
            return False
        try:
            contenu_encode, signature_encode = jeton.split(".", 1)
            contenu = base64.urlsafe_b64decode(contenu_encode + "=" * (-len(contenu_encode) % 4))
            signature = base64.urlsafe_b64decode(signature_encode + "=" * (-len(signature_encode) % 4))
            signature_attendue = hmac.new(
                self._auth_secret, contenu, hashlib.sha256
            ).digest()
            profile_id, expiration, _ = json.loads(contenu)
            id_demande, _ = normaliser_profil(nom)
        except (ValueError, TypeError, json.JSONDecodeError, binascii.Error):
            return False
        return (
            hmac.compare_digest(signature, signature_attendue)
            and profile_id == id_demande
            and isinstance(expiration, int)
            and expiration >= int(time.time())
        )

    def profile_names(self) -> list[str]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT display_name FROM profiles ORDER BY display_name COLLATE NOCASE"
            ).fetchall()
        return [row["display_name"] for row in rows]

    def profile_has_pin(self, nom: str) -> bool:
        profile_id, _ = normaliser_profil(nom)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT pin_verifier FROM profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        return row is not None and row["pin_verifier"] is not None

    def create_profile(self, nom: str, pin: str, confirmation: str) -> str:
        profile_id, display_name = normaliser_profil(nom)
        self._valider_pin(pin, confirmation)
        verifier = self._deriver_verificateur_pin(pin)
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM profiles WHERE profile_id = ?", (profile_id,)
            ).fetchone():
                raise ValueError("Ce profil existe déjà.")
            connection.execute(
                "INSERT INTO profiles (profile_id, display_name, pin_verifier) "
                "VALUES (?, ?, ?)",
                (profile_id, display_name, verifier),
            )
        return self._creer_jeton(profile_id)

    def set_initial_pin(self, nom: str, pin: str, confirmation: str) -> str:
        profile_id, display_name = normaliser_profil(nom)
        self._valider_pin(pin, confirmation)
        verifier = self._deriver_verificateur_pin(pin)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            row = connection.execute(
                "SELECT pin_verifier FROM profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row["pin_verifier"] is not None:
                raise ValueError("Ce profil possède déjà un code personnel.")
            connection.execute(
                "UPDATE profiles SET pin_verifier = ?, pin_failures = 0, "
                "pin_locked_until = 0 WHERE profile_id = ?",
                (verifier, profile_id),
            )
        return self._creer_jeton(profile_id)

    def verify_pin(self, nom: str, pin: str) -> str | None:
        profile_id, _ = normaliser_profil(nom)
        if not isinstance(pin, str) or re.fullmatch(r"[0-9]{6}", pin) is None:
            return None
        maintenant = time.time()
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT pin_verifier, pin_failures, pin_locked_until "
                "FROM profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row is None or row["pin_verifier"] is None:
                hashlib.scrypt(
                    pin.encode("ascii"),
                    salt=bytes(16),
                    n=_SCRYPT_N,
                    r=_SCRYPT_R,
                    p=_SCRYPT_P,
                    dklen=32,
                    maxmem=64 * 1024 * 1024,
                )
                return None
            if row["pin_locked_until"] > maintenant:
                self._verifier_pin(pin, row["pin_verifier"])
                return None
            if self._verifier_pin(pin, row["pin_verifier"]):
                connection.execute(
                    "UPDATE profiles SET pin_failures = 0, pin_locked_until = 0 "
                    "WHERE profile_id = ?",
                    (profile_id,),
                )
                return self._creer_jeton(profile_id)
            tentatives = row["pin_failures"] + 1
            verrou = (
                maintenant + _PIN_VERROU_SECONDES
                if tentatives >= _PIN_NOMBRE_ESSAIS_MAX
                else 0
            )
            connection.execute(
                "UPDATE profiles SET pin_failures = ?, pin_locked_until = ? "
                "WHERE profile_id = ?",
                (tentatives, verrou, profile_id),
            )
        return None

    @staticmethod
    def _record_event(
        connection: sqlite3.Connection,
        profile_id: str,
        event_key: str,
        xp: int,
        activity: str,
        algorithm: str,
        difficulty: str,
        metadata: dict[str, Any],
    ) -> bool:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO progress_events
               (profile_id, event_key, xp, activity, algorithm, difficulty, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id, event_key, xp, activity, algorithm, difficulty,
                json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            ),
        )
        return cursor.rowcount == 1

    @staticmethod
    def _unlock(
        connection: sqlite3.Connection, profile_id: str, achievement_id: str
    ) -> bool:
        achievement = SUCCES[achievement_id]
        cursor = connection.execute(
            "INSERT OR IGNORE INTO unlocked_achievements (profile_id, achievement_id) VALUES (?, ?)",
            (profile_id, achievement_id),
        )
        if cursor.rowcount != 1:
            return False
        ProgressionStore._record_event(
            connection,
            profile_id,
            f"achievement:{achievement_id}",
            achievement["xp"],
            "achievement",
            "",
            "",
            {"achievement": achievement_id},
        )
        return True

    @staticmethod
    def _unlock_six_algorithms(connection: sqlite3.Connection, profile_id: str) -> bool:
        rows = connection.execute(
            "SELECT DISTINCT algorithm FROM progress_events WHERE profile_id = ? AND activity IN ('exercise', 'challenge', 'manipulation')",
            (profile_id,),
        ).fetchall()
        if set(ALGORITHMES).issubset({row["algorithm"] for row in rows}):
            return ProgressionStore._unlock(connection, profile_id, "six_algorithmes")
        return False

    def record_exercise_success(self, nom: str, difficulty: str, question: dict[str, Any]) -> dict[str, Any]:
        _valider_difficulte_exercice(difficulty)
        if not question.get("correcte"):
            return {"xp_gagnes": 0, "nouveaux_succes": []}
        algorithm = question["nom_algorithme"]
        question_type = question["type"]
        profile_id, display_name = normaliser_profil(nom)
        tentatives = question.get("tentatives")
        indices = question.get("indices_utilises", 0)
        first_try = tentatives == 1
        no_hint = indices == 0
        xp = RECOMPENSE_EXERCICE
        xp += BONUS_PREMIER_ESSAI if first_try else 0
        xp += BONUS_EXERCICE_SANS_INDICE if no_hint else 0
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            activity_id = question.get("progression_id") or question.get("id")
            event_key = (
                f"exercise:{activity_id}:{algorithm}:{difficulty}:{question_type}"
                if isinstance(activity_id, str) and activity_id
                else f"exercise:{algorithm}:{difficulty}:{question_type}"
            )
            inserted = self._record_event(
                connection,
                profile_id,
                event_key,
                xp,
                "exercise",
                algorithm,
                difficulty,
                {
                    "correcte": True,
                    "tentatives": tentatives,
                    "indices_utilises": indices,
                    "reponses": question.get("reponses", []),
                    "reponse_attendue": question.get("reponse_attendue"),
                    "notion": question.get("notion"),
                    "competences": _competences_question(
                        question_type, question.get("notion")
                    ),
                    "erreurs": max(0, tentatives - 1) if isinstance(tentatives, int) else 0,
                    "first_try": first_try,
                    "no_hint": no_hint,
                },
            )
            nouveaux = []
            if inserted and self._unlock_six_algorithms(connection, profile_id):
                nouveaux.append("six_algorithmes")
        xp_gagnes = xp if inserted else 0
        xp_gagnes += sum(SUCCES[succes_id]["xp"] for succes_id in nouveaux)
        return {"xp_gagnes": xp_gagnes, "nouveaux_succes": nouveaux}

    def record_exercise_result(
        self, nom: str, difficulty: str, question: dict[str, Any]
    ) -> dict[str, Any]:
        """Persists a finalized answer; only successful answers can earn XP."""
        _valider_difficulte_exercice(difficulty)
        if "correcte" not in question:
            return {"xp_gagnes": 0, "nouveaux_succes": []}
        if question.get("correcte"):
            return self.record_exercise_success(nom, difficulty, question)

        algorithm = question.get("nom_algorithme", "")
        question_type = question.get("type", "")
        profile_id, display_name = normaliser_profil(nom)
        activity_id = question.get("progression_id") or question.get("id")
        event_key = (
            f"exercise:{activity_id}:{algorithm}:{difficulty}:{question_type}"
            if isinstance(activity_id, str) and activity_id
            else f"exercise:{algorithm}:{difficulty}:{question_type}"
        )
        tentatives = question.get("tentatives")
        tentatives_connues = (
            tentatives if isinstance(tentatives, int) and tentatives >= 0 else None
        )
        indices = question.get("indices_utilises", 0)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            self._record_event(
                connection,
                profile_id,
                event_key,
                0,
                "exercise",
                algorithm,
                difficulty,
                {
                    "correcte": False,
                    "tentatives": tentatives_connues,
                    "indices_utilises": indices,
                    "reponses": question.get("reponses", []),
                    "reponse_attendue": question.get("reponse_attendue"),
                    "notion": question.get("notion"),
                    "competences": _competences_question(
                        question_type, question.get("notion")
                    ),
                    "erreurs": max(1, tentatives_connues or 0),
                    "first_try": False,
                    "no_hint": indices == 0,
                },
            )
        return {"xp_gagnes": 0, "nouveaux_succes": []}

    def complete_exercise_session(self, nom: str, session: dict[str, Any]) -> list[str]:
        questions = session.get("questions")
        if not session.get("terminee") or not questions or not all(q.get("correcte") for q in questions):
            return []
        profile_id, display_name = normaliser_profil(nom)
        sans_erreur = all(q.get("tentatives") == 1 for q in questions)
        sans_indice = all(q.get("indices_utilises", 0) == 0 for q in questions)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            nouveaux = []
            if sans_erreur and self._unlock(connection, profile_id, "sans_erreur"):
                nouveaux.append("sans_erreur")
            if sans_indice and self._unlock(connection, profile_id, "sans_indice"):
                nouveaux.append("sans_indice")
            if self._unlock_six_algorithms(connection, profile_id):
                nouveaux.append("six_algorithmes")
        return nouveaux

    def record_challenge_success(self, nom: str, defi: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(defi, dict):
            raise ValueError("Le défi fourni n'est pas un dictionnaire valide.")
        challenge_type = defi.get("type_defi", "Étapes")
        termine = defi.get("curseur") == len(defi.get("taches", ()))
        chrono_expire = (
            challenge_type == "Rapidité"
            and defi.get("temps_ecoule")
            and defi.get("tentatives", 0) > 0
        )
        if not termine and not chrono_expire:
            return {"xp_gagnes": 0, "nouveaux_succes": [], "record_battu": False}
        algorithm = defi.get("nom_algorithme")
        difficulty = defi.get("difficulte")
        if algorithm is None or difficulty is None:
            raise ValueError("Le défi doit préciser son algorithme et sa difficulté.")
        if difficulty not in RECOMPENSE_DEFI:
            raise ValueError(f"Difficulté de défi inconnue : {difficulty}.")
        errors = defi.get("erreurs", 0)
        if not isinstance(errors, int) or errors < 0:
            raise ValueError("Le nombre d'erreurs du défi doit être un entier positif.")
        no_hint = defi.get("indices_utilises", 0) == 0
        tentatives = max(1, defi.get("tentatives", defi.get("actions", 0) + errors))
        score = round(100 * defi.get("actions", 0) / tentatives)
        xp = (
            RECOMPENSE_DEFI[difficulty]
            + (BONUS_DEFI_SANS_ERREUR if errors == 0 else 0)
            + (BONUS_DEFI_SANS_INDICE if no_hint else 0)
            if termine else 0
        )
        profile_id, display_name = normaliser_profil(nom)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            inserted = False
            if termine:
                activity_id = defi.get("id")
                event_key = (
                    f"challenge:{activity_id}:{algorithm}:{difficulty}"
                    if isinstance(activity_id, str) and activity_id
                    else f"challenge:{algorithm}:{difficulty}"
                )
                inserted = self._record_event(
                    connection,
                    profile_id,
                    event_key,
                    xp,
                    "challenge",
                    algorithm,
                    difficulty,
                    {
                        "errors": errors,
                        "no_hint": no_hint,
                        "challenge_type": challenge_type,
                        "score": score,
                        "competences": [challenge_type.casefold().replace(" ", "_")],
                    },
                )
            record_battu = self._mettre_a_jour_meilleur_score(
                connection, profile_id, challenge_type, score
            ) if inserted or chrono_expire else False
            nouveaux = []
            if termine:
                if errors == 0 and self._unlock(connection, profile_id, "sans_erreur"):
                    nouveaux.append("sans_erreur")
                if no_hint and self._unlock(connection, profile_id, "sans_indice"):
                    nouveaux.append("sans_indice")
                if difficulty == "Avancé" and self._unlock(connection, profile_id, "defi_avance"):
                    nouveaux.append("defi_avance")
                if self._unlock_six_algorithms(connection, profile_id):
                    nouveaux.append("six_algorithmes")
        xp_gagnes = xp if inserted else 0
        xp_gagnes += sum(SUCCES[succes_id]["xp"] for succes_id in nouveaux)
        return {
            "xp_gagnes": xp_gagnes,
            "nouveaux_succes": nouveaux,
            "score": score,
            "meilleur_score": self.best_challenge_score(nom, challenge_type),
            "record_battu": record_battu,
        }

    @staticmethod
    def _mettre_a_jour_meilleur_score(
        connection: sqlite3.Connection,
        profile_id: str,
        challenge_type: str,
        score: int,
    ) -> bool:
        precedent = connection.execute(
            "SELECT best_score FROM challenge_best_scores "
            "WHERE profile_id = ? AND challenge_type = ?",
            (profile_id, challenge_type),
        ).fetchone()
        if precedent is not None and score <= precedent["best_score"]:
            return False
        connection.execute(
            "INSERT INTO challenge_best_scores "
            "(profile_id, challenge_type, best_score) VALUES (?, ?, ?) "
            "ON CONFLICT(profile_id, challenge_type) DO UPDATE SET "
            "best_score = excluded.best_score, updated_at = CURRENT_TIMESTAMP",
            (profile_id, challenge_type, score),
        )
        return True

    def best_challenge_score(self, nom: str, challenge_type: str) -> int | None:
        """Retourne le meilleur score du profil pour un type de défi."""
        profile_id, _ = normaliser_profil(nom)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT best_score FROM challenge_best_scores "
                "WHERE profile_id = ? AND challenge_type = ?",
                (profile_id, challenge_type),
            ).fetchone()
        return row["best_score"] if row is not None else None

    def best_challenge_scores(self, nom: str) -> dict[str, int]:
        """Retourne les meilleurs scores de défi du profil, par type."""
        profile_id, _ = normaliser_profil(nom)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT challenge_type, best_score FROM challenge_best_scores "
                "WHERE profile_id = ? ORDER BY challenge_type",
                (profile_id,),
            ).fetchall()
        return {row["challenge_type"]: row["best_score"] for row in rows}

    def record_manipulation_success(
        self, nom: str, partie: dict[str, Any]
    ) -> dict[str, Any]:
        """Récompense une manipulation terminée après rejeu des actions validées."""
        if not isinstance(partie, dict):
            raise ValueError("La partie fournie n'est pas un dictionnaire valide.")
        algorithme = partie.get("algorithme")
        difficulte = partie.get("difficulte")
        if algorithme is None or difficulte is None:
            raise ValueError("La partie doit préciser son algorithme et sa difficulté.")
        correspondance_difficulte = {
            "Facile": "Débutant",
            "Intermédiaire": "Intermédiaire",
            "Difficile": "Avancé",
        }
        if difficulte not in correspondance_difficulte:
            raise ValueError(f"Difficulté de manipulation inconnue : {difficulte}.")
        if not verifier_reussite(partie):
            return {"xp_gagnes": 0, "nouveaux_succes": []}
        difficulte_recompense = correspondance_difficulte[difficulte]
        errors = partie.get("erreurs", 0)
        if not isinstance(errors, int) or errors < 0:
            raise ValueError("Le nombre d'erreurs de la partie doit être un entier positif.")
        no_hint = partie.get("indices_utilises", 0) == 0
        etapes = partie.get("etapes", 0)
        xp = RECOMPENSE_DEFI[difficulte_recompense]
        xp += BONUS_DEFI_SANS_ERREUR if errors == 0 else 0
        xp += BONUS_DEFI_SANS_INDICE if no_hint else 0
        profile_id, display_name = normaliser_profil(nom)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            activity_id = partie.get("id")
            event_key = (
                f"manipulation:{activity_id}:{algorithme}:{difficulte}"
                if isinstance(activity_id, str) and activity_id
                else f"manipulation:{algorithme}:{difficulte}"
            )
            inserted = self._record_event(
                connection,
                profile_id,
                event_key,
                xp,
                "manipulation",
                algorithme,
                difficulte,
                {
                    "errors": errors,
                    "no_hint": no_hint,
                    "steps": etapes,
                },
            )
            nouveaux = []
            if inserted and self._unlock_six_algorithms(connection, profile_id):
                nouveaux.append("six_algorithmes")
        xp_gagnes = xp if inserted else 0
        xp_gagnes += sum(SUCCES[succes_id]["xp"] for succes_id in nouveaux)
        return {"xp_gagnes": xp_gagnes, "nouveaux_succes": nouveaux}

    def achievements(self, nom: str) -> list[dict[str, Any]]:
        profile_id, _ = normaliser_profil(nom)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT achievement_id, unlocked_at FROM unlocked_achievements WHERE profile_id = ?",
                (profile_id,),
            ).fetchall()
        unlocked = {row[0]: row[1] for row in rows}
        return [
            {
                "id": achievement_id,
                **achievement,
                "debloque": achievement_id in unlocked,
                "date": unlocked.get(achievement_id),
            }
            for achievement_id, achievement in SUCCES.items()
        ]

    def set_title(self, nom: str, titre: str) -> None:
        profile_id, display_name = normaliser_profil(nom)
        with self._transaction() as connection:
            self._ensure_profile(connection, profile_id, display_name)
            titres = {
                item["titre"]
                for item in self.achievements(nom)
                if item["debloque"] and item["titre"]
            }
            if titre and titre not in titres:
                raise ValueError("Ce titre n'a pas été débloqué.")
            connection.execute(
                "UPDATE profiles SET active_title = ? WHERE profile_id = ?",
                (titre, profile_id),
            )

    def profile(self, nom: str) -> dict[str, Any]:
        profile_id, display_name = normaliser_profil(nom)
        self.ensure_profile(nom)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT active_title FROM profiles WHERE profile_id = ?", (profile_id,)
            ).fetchone()
            xp = connection.execute(
                "SELECT COALESCE(SUM(xp), 0) FROM progress_events WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()[0]
        level_index = max(index for index, (_, seuil) in enumerate(NIVEAUX) if xp >= seuil)
        level_name, current_threshold = NIVEAUX[level_index]
        next_threshold = NIVEAUX[level_index + 1][1] if level_index + 1 < len(NIVEAUX) else None
        progress = 1.0 if next_threshold is None else (xp - current_threshold) / (next_threshold - current_threshold)
        title = row[0]
        return {
            "profile_id": profile_id,
            "display_name": display_name,
            "xp": xp,
            "niveau": level_name,
            "niveau_index": level_index + 1,
            "seuil_actuel": current_threshold,
            "seuil_suivant": next_threshold,
            "progression_niveau": progress,
            "titre": title,
            "succes": self.achievements(nom),
        }

    def statistics(self, nom: str) -> dict[str, Any]:
        """Retourne les statistiques calculables depuis les réussites enregistrées."""
        profile_id, _ = normaliser_profil(nom)
        with self._connection() as connection:
            challenges = connection.execute(
                "SELECT COUNT(*) FROM progress_events "
                "WHERE profile_id = ? AND activity = 'challenge'",
                (profile_id,),
            ).fetchone()[0]
            algorithms = connection.execute(
                "SELECT activity, algorithm, metadata FROM progress_events "
                "WHERE profile_id = ? AND activity IN ('exercise', 'challenge', 'manipulation') "
                "ORDER BY algorithm",
                (profile_id,),
            ).fetchall()
        algorithmes_reussis = sorted({
            row["algorithm"]
            for row in algorithms
            if row["algorithm"] and _reussite_evenement({
                "activite": row["activity"],
                "metadata": _lire_metadata(row["metadata"]),
            })
        })
        return {
            "defis_valides_enregistres": challenges,
            "algorithmes_reussis": algorithmes_reussis,
        }

    def activity_history(
        self, nom: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Retourne l'historique récent, du plus récent au plus ancien."""
        profile_id, _ = normaliser_profil(nom)
        limite_sql = ""
        arguments: tuple[Any, ...] = (profile_id,)
        if limit is not None:
            if limit < 0:
                raise ValueError("La limite d'historique doit être positive ou nulle.")
            limite_sql = " LIMIT ?"
            arguments = (profile_id, limit)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT event_key, activity, algorithm, difficulty, xp, metadata, created_at "
                "FROM progress_events WHERE profile_id = ? "
                "ORDER BY created_at DESC, event_key DESC" + limite_sql,
                arguments,
            ).fetchall()
        evenements = []
        for row in rows:
            evenement = {
                "activite": row["activity"],
                "algorithme": row["algorithm"],
                "difficulte": row["difficulty"],
                "type_question": (
                    row["event_key"].rsplit(":", 1)[-1]
                    if row["activity"] == "exercise"
                    else None
                ),
                "xp": row["xp"],
                "metadata": _lire_metadata(row["metadata"]),
                "date": row["created_at"],
            }
            evenement["reussie"] = _reussite_evenement(evenement)
            evenements.append(evenement)
        return evenements

    def dashboard_data(
        self,
        nom: str,
        date_debut: str | None = None,
        algorithme: str | None = None,
        activite: str | None = None,
        limite_historique: int = 100,
    ) -> dict[str, Any]:
        """Agrège les activités du profil et ne charge que la chronologie récente."""
        profile_id, _ = normaliser_profil(nom)
        activites_connues = ("exercise", "challenge", "manipulation")
        if activite not in (None, *activites_connues):
            raise ValueError("Type d'activité inconnu.")
        if limite_historique < 0:
            raise ValueError("La limite d'historique doit être positive ou nulle.")

        conditions = ["profile_id = ?", "activity IN ('exercise', 'challenge', 'manipulation')"]
        arguments: list[Any] = [profile_id]
        if date_debut:
            conditions.append("created_at >= ?")
            arguments.append(date_debut)
        if algorithme:
            conditions.append("algorithm = ?")
            arguments.append(algorithme)
        if activite:
            conditions.append("activity = ?")
            arguments.append(activite)
        where = " AND ".join(conditions)

        definitions_competences = (
            ("etat_suivant", "Prédire l'état suivant"),
            ("etapes_algorithme", "Comprendre l'ordre des étapes"),
            ("comparaisons_echanges", "Comprendre comparaisons et échanges"),
            ("choix_algorithme", "Choisir un algorithme adapté"),
            ("complexite", "Interpréter les complexités théoriques"),
        )
        competences = {
            identifiant: {"id": identifiant, "nom": nom_competence,
                          "observations": 0, "reussites": 0, "erreurs": 0,
                          "dernier_resultat": None}
            for identifiant, nom_competence in definitions_competences
        }
        algorithmes = {}
        types_questions = {}
        evolution = {}
        total_activites = xp_gagnes = questions_evaluees = bonnes_reponses = 0
        defis_valides = 0
        algorithmes_reussis = set()

        with self._connection() as connection:
            requete = (
                "SELECT event_key, activity, algorithm, difficulty, xp, metadata, created_at "
                "FROM progress_events WHERE " + where + " ORDER BY created_at DESC, event_key DESC"
            )
            for row in connection.execute(requete, arguments):
                total_activites += 1
                xp_gagnes += row["xp"]
                if row["activity"] == "challenge":
                    defis_valides += 1
                metadata = _lire_metadata(row["metadata"])
                if row["algorithm"] and _reussite_evenement({
                    "activite": row["activity"], "metadata": metadata,
                }):
                    algorithmes_reussis.add(row["algorithm"])
                if row["activity"] != "exercise":
                    continue

                if not isinstance(metadata.get("correcte"), bool):
                    continue
                correcte = metadata["correcte"]
                question_type = row["event_key"].rsplit(":", 1)[-1]
                algorithme_nom = row["algorithm"]
                questions_evaluees += 1
                bonnes_reponses += int(correcte)
                for groupes, cle in ((algorithmes, algorithme_nom), (types_questions, question_type)):
                    groupe = groupes.setdefault(cle or "Non précisé", {"evaluees": 0, "reussites": 0})
                    groupe["evaluees"] += 1
                    groupe["reussites"] += int(correcte)

                try:
                    jour = row["created_at"][:10]
                    date.fromisoformat(jour)
                except (TypeError, ValueError):
                    jour = None
                if jour:
                    groupe_jour = evolution.setdefault(jour, {"evaluees": 0, "reussites": 0})
                    groupe_jour["evaluees"] += 1
                    groupe_jour["reussites"] += int(correcte)

                competences_observees = metadata.get("competences") or _competences_question(
                    question_type, metadata.get("notion")
                )
                erreurs = metadata.get("erreurs")
                try:
                    erreurs = max(0, int(erreurs)) if erreurs is not None else 0
                except (TypeError, ValueError):
                    erreurs = 0
                if not correcte and not erreurs:
                    erreurs = 1
                for competence_id in competences_observees:
                    competence = competences.get(competence_id)
                    if competence is None:
                        continue
                    competence["observations"] += 1
                    competence["reussites"] += int(correcte)
                    competence["erreurs"] += erreurs
                    if competence["dernier_resultat"] is None:
                        competence["dernier_resultat"] = correcte

            scores = {
                row["challenge_type"]: row["best_score"]
                for row in connection.execute(
                    "SELECT challenge_type, best_score FROM challenge_best_scores "
                    "WHERE profile_id = ? ORDER BY challenge_type", (profile_id,)
                )
            }
            profil_a_des_donnees = connection.execute(
                "SELECT 1 FROM progress_events WHERE profile_id = ? LIMIT 1",
                (profile_id,),
            ).fetchone() is not None or bool(scores)
            requete_historique = (
                "SELECT event_key, activity, algorithm, difficulty, xp, metadata, created_at "
                "FROM progress_events WHERE profile_id = ?"
            )
            historique_args: list[Any] = [profile_id]
            historique_conditions = []
            if date_debut:
                historique_conditions.append("created_at >= ?")
                historique_args.append(date_debut)
            if algorithme:
                historique_conditions.append("(algorithm = ? OR activity = 'achievement')")
                historique_args.append(algorithme)
            if activite:
                historique_conditions.append("activity = ?")
                historique_args.append(activite)
            if historique_conditions:
                requete_historique += " AND " + " AND ".join(historique_conditions)
            requete_historique += " ORDER BY created_at DESC, event_key DESC LIMIT ?"
            historique_args.append(limite_historique)
            lignes_historique = connection.execute(
                requete_historique, historique_args
            ).fetchall()

        def resultats_groupes(groupes: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
            return [
                {"nom": cle, **valeurs,
                 "taux": valeurs["reussites"] / valeurs["evaluees"]}
                for cle, valeurs in sorted(groupes.items())
            ]

        competences_detaillees = []
        for competence in competences.values():
            if not competence["observations"]:
                statut = "non évaluée"
            elif competence["dernier_resultat"] is False:
                statut = "à revoir"
            elif competence["reussites"] >= 2 and competence["erreurs"] == 0:
                statut = "maîtrisée"
            else:
                statut = "en cours"
            competences_detaillees.append({**competence, "statut": statut})

        recent = []
        for row in lignes_historique:
            evenement = {
                "activite": row["activity"], "algorithme": row["algorithm"],
                "difficulte": row["difficulty"], "type_question": (
                    row["event_key"].rsplit(":", 1)[-1]
                    if row["activity"] == "exercise" else None
                ),
                "xp": row["xp"], "metadata": _lire_metadata(row["metadata"]),
                "date": row["created_at"],
            }
            evenement["reussie"] = _reussite_evenement(evenement)
            recent.append(evenement)

        return {
            "activites_terminees": total_activites,
            "defis_valides_enregistres": defis_valides,
            "algorithmes_reussis": sorted(algorithmes_reussis),
            "questions_evaluees": questions_evaluees,
            "bonnes_reponses": bonnes_reponses,
            "taux_reussite": bonnes_reponses / questions_evaluees if questions_evaluees else None,
            "xp_activites": xp_gagnes,
            "par_algorithme": resultats_groupes(algorithmes),
            "par_type_question": resultats_groupes(types_questions),
            "evolution": [
                {"date": jour, **valeurs,
                 "taux": valeurs["reussites"] / valeurs["evaluees"]}
                for jour, valeurs in sorted(evolution.items())
            ],
            "competences": competences_detaillees,
            "records": scores,
            "profil_a_des_donnees": profil_a_des_donnees,
            "historique": recent,
        }

    def parcours_pedagogique(self, nom: str) -> dict[str, Any]:
        """Construit un parcours uniquement depuis les réussites persistées."""
        historique = self.activity_history(nom)
        activites = [
            evenement for evenement in historique
            if evenement["activite"] in ("exercise", "challenge", "manipulation")
        ]
        activites_reussies = [
            evenement for evenement in activites if _reussite_evenement(evenement)
        ]
        algorithmes_reussis = {
            evenement["algorithme"] for evenement in activites_reussies
            if evenement["algorithme"]
        }
        types_exercices = {
            evenement["type_question"] for evenement in activites_reussies
            if evenement["activite"] == "exercise"
        }
        types_visualisation = set()
        if "etat" in types_exercices:
            types_visualisation.add("etat")
        if types_exercices & {"prediction", "prediction_choix", "prediction_texte"}:
            types_visualisation.add("prediction")
        types_operations = set()
        if types_visualisation and "prediction" in types_visualisation:
            types_operations.add("prediction")
        if "ordre" in types_exercices:
            types_operations.add("ordre")

        def statut_competence(observes: set[str], requis: set[str]) -> str:
            if not observes:
                return "non évaluée"
            if requis.issubset(observes):
                return "validée"
            return "en cours d'acquisition"

        competences = [
            {
                "id": "fonctionnement_tris",
                "nom": "Fonctionnement des six algorithmes",
                "statut": (
                    "non évaluée" if not algorithmes_reussis
                    else "validée" if set(ALGORITHMES).issubset(algorithmes_reussis)
                    else "en cours d'acquisition"
                ),
                "detail": f"{len(set(ALGORITHMES) & algorithmes_reussis)} / {len(ALGORITHMES)} tris avec une réussite enregistrée.",
            },
            {
                "id": "visualisation",
                "nom": "Lire et interpréter une visualisation",
                "statut": statut_competence(
                    types_visualisation,
                    {"etat", "prediction"},
                ),
                "detail": "Évaluée par les exercices d'état du tableau et de prédiction d'étape.",
            },
            {
                "id": "operations",
                "nom": "Interpréter l'ordre des comparaisons et opérations",
                "statut": statut_competence(
                    types_operations,
                    {"ordre", "prediction"},
                ),
                "detail": "Les exercices évaluent l'ordre et l'étape suivante, pas les compteurs mesurés.",
            },
            {
                "id": "complexites",
                "nom": "Interpréter les complexités théoriques",
                "statut": "non évaluée",
                "detail": "Aucune réussite d'exercice dédiée aux complexités n'est enregistrée.",
            },
            {
                "id": "choix_algorithme",
                "nom": "Choisir un algorithme selon une situation",
                "statut": "non évaluée",
                "detail": "Aucune activité persistée ne mesure encore ce choix.",
            },
        ]

        definitions_competences = (
            ("etat_suivant", "Prédire l'état suivant"),
            ("etapes_algorithme", "Comprendre l'ordre des étapes"),
            ("comparaisons_echanges", "Comprendre les comparaisons et les échanges"),
            ("choix_algorithme", "Choisir un algorithme adapté"),
            ("complexite", "Interpréter les complexités théoriques"),
        )
        resultats_exercices = [
            evenement for evenement in historique
            if evenement["activite"] == "exercise"
        ]

        def competences_evenement(evenement: dict[str, Any]) -> list[str]:
            metadata = evenement["metadata"]
            return metadata.get("competences") or _competences_question(
                evenement["type_question"], metadata.get("notion")
            )

        def erreurs_evenement(evenement: dict[str, Any]) -> int:
            metadata = evenement["metadata"]
            if "erreurs" in metadata:
                try:
                    return max(0, int(metadata["erreurs"]))
                except (TypeError, ValueError):
                    return 0
            if not evenement["reussie"]:
                try:
                    return max(1, int(metadata.get("tentatives", 1)))
                except (TypeError, ValueError):
                    return 1
            return 0

        def entier_metadata(metadata: dict[str, Any], cle: str) -> int:
            try:
                return max(0, int(metadata.get(cle, 0) or 0))
            except (TypeError, ValueError):
                return 0

        competences_detaillees = []
        evenements_par_competence = {}
        for competence_id, nom_competence in definitions_competences:
            observes = [
                evenement for evenement in resultats_exercices
                if competence_id in competences_evenement(evenement)
            ]
            evenements_par_competence[competence_id] = observes
            reussites = [evenement for evenement in observes if evenement["reussie"]]
            erreurs = sum(erreurs_evenement(evenement) for evenement in observes)
            if not observes:
                statut = "non évaluée"
            elif not observes[0]["reussie"]:
                statut = "à retravailler"
            elif len(reussites) >= 2 and erreurs == 0:
                statut = "maîtrisée"
            else:
                statut = "en progression"
            competences_detaillees.append({
                "id": competence_id,
                "nom": nom_competence,
                "statut": statut,
                "detail": (
                    f"{len(reussites)} réussite(s), {erreurs} erreur(s) observée(s) "
                    f"sur {len(observes)} réponse(s) finalisée(s)."
                    if observes else "Aucune réponse enregistrée pour cette compétence."
                ),
            })

        statuts_compatibles = {
            "non évaluée": "non évaluée",
            "en progression": "en cours d'acquisition",
            "maîtrisée": "validée",
            "à retravailler": "à retravailler",
        }
        competence_par_id = {item["id"]: item for item in competences}
        for competence_id in ("choix_algorithme", "complexites"):
            detail_id = "complexite" if competence_id == "complexites" else competence_id
            detail = next(item for item in competences_detaillees if item["id"] == detail_id)
            competence_par_id[competence_id]["statut"] = statuts_compatibles[detail["statut"]]
            competence_par_id[competence_id]["detail"] = detail["detail"]

        indices_exercices = sum(
            entier_metadata(evenement["metadata"], "indices_utilises")
            if "indices_utilises" in evenement["metadata"]
            else 0 if evenement["metadata"].get("no_hint", True) else 1
            for evenement in resultats_exercices
        )
        essais_avec_donnees = [
            evenement for evenement in resultats_exercices
            if "tentatives" in evenement["metadata"] or "first_try" in evenement["metadata"]
        ]
        premieres_reussites = sum(
            bool(evenement["metadata"].get(
                "first_try",
                evenement["reussie"] and evenement["metadata"].get("tentatives") == 1,
            ))
            for evenement in essais_avec_donnees
        )
        autonomie = {
            "mesuree": bool(essais_avec_donnees),
            "reussites_premier_essai": premieres_reussites,
            "reponses_mesurees": len(essais_avec_donnees),
            "indices_utilises": indices_exercices,
            "detail": (
                f"{premieres_reussites} réussite(s) au premier essai sur "
                f"{len(essais_avec_donnees)} réponse(s) mesurée(s); "
                f"{indices_exercices} indice(s) utilisé(s). Les indices ne diminuent pas "
                "le statut des compétences."
                if essais_avec_donnees else
                "Non mesurée : aucune réponse d'exercice avec données de tentative."
            ),
        }

        erreurs_par_competence = {}
        for competence_id, observes in evenements_par_competence.items():
            erreurs_par_competence[competence_id] = [
                evenement for evenement in observes
                if erreurs_evenement(evenement) or not evenement["reussie"]
            ]
        competence_a_revoir = max(
            (
                competence_id for competence_id, erreurs in erreurs_par_competence.items()
                if erreurs
            ),
            key=lambda competence_id: (
                len(erreurs_par_competence[competence_id]),
                -resultats_exercices.index(erreurs_par_competence[competence_id][0]),
            ),
            default=None,
        )
        if competence_a_revoir is None:
            niveaux_progression = ("Débutant", "Intermédiaire", "Avancé")
            competence_a_revoir = next((
                competence_id
                for competence_id, _ in definitions_competences
                if len(evenements_par_competence[competence_id]) >= 2
                and all(
                    evenement["reussie"]
                    for evenement in evenements_par_competence[competence_id][:2]
                )
                and any(
                    evenement["difficulte"] in niveaux_progression[:-1]
                    for evenement in evenements_par_competence[competence_id][:2]
                )
            ), None)
            if competence_a_revoir is None:
                competence_a_revoir = next(
                    (
                        competence_id for competence_id, _ in definitions_competences
                        if not evenements_par_competence[competence_id]
                    ),
                    "etapes_algorithme",
                )
        competence_nom = next(
            nom_competence for competence_id, nom_competence in definitions_competences
            if competence_id == competence_a_revoir
        )
        observes_competence = evenements_par_competence[competence_a_revoir]
        evenements_en_erreur = erreurs_par_competence[competence_a_revoir]
        evenement_cible = (
            evenements_en_erreur[0] if evenements_en_erreur
            else observes_competence[0] if observes_competence
            else None
        )
        type_source = evenement_cible["type_question"] if evenement_cible else None
        recommandation = {
            "competence": competence_nom,
            "page": "Exercices",
            "difficulte": "Débutant",
            "type_question": "etat",
            "raison": "Commence par une activité de suivi d'état; aucune réponse n'est encore enregistrée.",
            "notion": None,
            "algorithme": None,
        }
        if competence_a_revoir == "etapes_algorithme":
            recommandation.update({
                "difficulte": (
                    evenement_cible["difficulte"]
                    if evenement_cible and evenement_cible["difficulte"] in ("Débutant", "Intermédiaire", "Avancé")
                    else "Intermédiaire"
                ),
                "type_question": "ordre" if type_source == "ordre" else "prediction",
                "raison": "Une erreur a été enregistrée sur les étapes; entraîne-toi à prédire l'opération suivante ou à remettre la trace en ordre.",
            })
        elif competence_a_revoir == "comparaisons_echanges":
            recommandation.update({
                "difficulte": (
                    evenement_cible["difficulte"]
                    if evenement_cible and evenement_cible["difficulte"] in ("Intermédiaire", "Avancé")
                    else "Intermédiaire"
                ),
                "type_question": "comprehension",
                "raison": "Une réponse de compréhension est à reprendre à partir des règles concrètes du tri.",
            })
        elif competence_a_revoir in ("choix_algorithme", "complexite"):
            recommandation.update({
                "page": "Entraînement",
                "difficulte": (
                    evenement_cible["difficulte"]
                    if evenement_cible and evenement_cible["difficulte"] in ("Débutant", "Intermédiaire", "Avancé")
                    else "Débutant"
                ),
                "type_question": "choix_algorithme_entrainement",
                "notion": (
                    evenement_cible["metadata"].get("notion")
                    if evenement_cible and evenement_cible["metadata"].get("notion") in (
                        "Stabilité et complexité garantie",
                        "Mémoire auxiliaire et pire cas",
                    ) else "Stabilité et complexité garantie"
                ),
                "raison": "Une mise en situation de choix d'algorithme est à reprendre; la notion affichée précise la contrainte évaluée.",
            })

        if evenement_cible and evenement_cible["activite"] == "exercise":
            recommandation["algorithme"] = evenement_cible["algorithme"]
        elif evenement_cible:
            recommandation["algorithme"] = evenement_cible["algorithme"] or None
        if evenement_cible and evenements_en_erreur:
            recommandation["raison"] = (
                f"{len(evenements_en_erreur)} résultat(s) avec erreur pour « {competence_nom} »; "
                f"reprends {evenement_cible['type_question']} en {recommandation['difficulte']}. "
                "L'indice utilisé, s'il y en a un, n'est pas compté comme un échec."
            )

        derniers_resultats = observes_competence[:2]
        niveaux = ("Débutant", "Intermédiaire", "Avancé")
        if (
            len(derniers_resultats) == 2
            and all(evenement["reussie"] for evenement in derniers_resultats)
            and competence_a_revoir != "etat_suivant"
            and recommandation["difficulte"] in niveaux
        ):
            niveau = max(
                (niveaux.index(evenement["difficulte"])
                 for evenement in derniers_resultats if evenement["difficulte"] in niveaux),
                default=0,
            )
            if niveau < len(niveaux) - 1:
                recommandation["difficulte"] = niveaux[niveau + 1]
                recommandation["raison"] = (
                    f"Deux réponses récentes sur « {competence_nom} » sont correctes; "
                    f"passe au niveau {niveaux[niveau + 1]}. L'usage d'un indice ne réduit pas cette progression."
                )

        if recommandation["page"] == "Exercices":
            type_recommande = recommandation["type_question"]
            algorithme_source = (
                evenement_cible["algorithme"] if evenement_cible else None
            )
            compte_exercices = {
                algorithme: sum(
                    evenement["algorithme"] == algorithme
                    and evenement["type_question"] == type_recommande
                    and evenement["difficulte"] == recommandation["difficulte"]
                    for evenement in resultats_exercices
                )
                for algorithme in ALGORITHMES
            }
            recommandation["algorithme"] = min(
                ALGORITHMES,
                key=lambda algorithme: (
                    compte_exercices[algorithme],
                    algorithme == algorithme_source,
                ),
            )
        recommandation["exercice"] = (
            f"{recommandation['type_question']} · {recommandation['difficulte']}"
            + (f" · {recommandation['algorithme']}" if recommandation["algorithme"] else "")
            + (f" · {recommandation['notion']}" if recommandation["notion"] else "")
        )

        algorithmes_manquants = [
            algorithme for algorithme in ALGORITHMES
            if algorithme not in algorithmes_reussis
        ]
        a_etat = "etat" in types_exercices
        a_prediction = bool(
            types_exercices & {"prediction", "prediction_choix", "prediction_texte"}
        )
        types_visuels_manquants = []
        if not a_etat:
            types_visuels_manquants.append("un exercice d'état")
        if not a_prediction:
            types_visuels_manquants.append("une prédiction d'étape")
        objectifs = [
            {
                "id": "six_algorithmes",
                "nom": "Réussir une activité sur chacun des six tris",
                "statut": "termine" if not algorithmes_manquants else "à faire",
                "progression": f"{len(set(ALGORITHMES) & algorithmes_reussis)} / {len(ALGORITHMES)}",
                "page": "Exercices",
                "bouton": "Ouvrir les exercices",
                "raison": (
                    f"{algorithmes_manquants[0]} n'apparaît pas encore dans les réussites enregistrées."
                    if algorithmes_manquants else "Les six tris ont une activité réussie enregistrée."
                ),
                "algorithme": algorithmes_manquants[0] if algorithmes_manquants else None,
            },
            {
                "id": "visualisation",
                "nom": "Lire un état et prédire une étape",
                "statut": "termine" if a_etat and a_prediction else "à faire",
                "progression": f"{int(a_etat)} / 1 état · {int(a_prediction)} / 1 prédiction",
                "page": "Exercices",
                "bouton": "Ouvrir les exercices",
                "raison": (
                    "Il manque " + " et ".join(types_visuels_manquants) + "."
                    if types_visuels_manquants
                    else "Les deux types de réussite sont enregistrés."
                ),
                "algorithme": None,
            },
            {
                "id": "comprehension",
                "nom": "Réussir un exercice de compréhension",
                "statut": "termine" if "comprehension" in types_exercices else "à faire",
                "progression": "1 / 1" if "comprehension" in types_exercices else "0 / 1",
                "page": "Exercices",
                "bouton": "Ouvrir les exercices",
                "raison": "Aucune réussite d'exercice de compréhension n'est enregistrée." if "comprehension" not in types_exercices else "Une réussite de compréhension est enregistrée.",
                "algorithme": None,
            },
        ]

        difficultes = tuple(RECOMPENSE_DEFI)
        defis = [evenement for evenement in activites if evenement["activite"] == "challenge"]
        defis_avances = any(evenement["difficulte"] == "Avancé" for evenement in defis)
        niveau_actuel = max(
            (difficultes.index(evenement["difficulte"]) for evenement in defis if evenement["difficulte"] in difficultes),
            default=-1,
        )
        difficulte_cible = difficultes[min(niveau_actuel + 1, len(difficultes) - 1)]
        algorithmes_defis_cibles = {
            evenement["algorithme"] for evenement in defis
            if evenement["difficulte"] == difficulte_cible
        }
        algorithme_defi = next(
            (algorithme for algorithme in ALGORITHMES if algorithme not in algorithmes_defis_cibles),
            next(iter(ALGORITHMES)),
        )
        objectifs.append({
            "id": "defi_progressif",
            "nom": "Progresser vers un défi avancé",
            "statut": "termine" if defis_avances else "à faire",
            "progression": (
                "Défi avancé terminé"
                if defis_avances
                else f"Prochain niveau conseillé : {difficulte_cible} avec {algorithme_defi}"
            ),
            "page": "Défi interactif",
            "bouton": "Ouvrir les défis",
            "raison": (
                "Le profil n'a pas encore validé de défi avancé."
                if not defis_avances else "Le succès avancé est déjà enregistré."
            ),
            "algorithme": algorithme_defi,
            "difficulte": difficulte_cible,
        })

        prochain_objectif = next(
            (objectif for objectif in objectifs if objectif["statut"] != "termine"),
            None,
        )
        prochaine_activite = (
            {
                "nom": prochain_objectif["nom"],
                "page": prochain_objectif["page"],
                "raison": prochain_objectif["raison"],
                "bouton": prochain_objectif["bouton"],
            }
            if prochain_objectif else {
                "nom": "Comparer deux algorithmes",
                "page": "Comparer",
                "raison": "Les objectifs suivis sont terminés; cette activité de découverte n'est pas enregistrée dans le profil.",
                "bouton": "Ouvrir la comparaison",
            }
        )
        return {
            "competences": competences,
            "competences_detaillees": competences_detaillees,
            "autonomie": autonomie,
            "recommandation": recommandation,
            "objectifs": objectifs,
            "prochaine_activite": prochaine_activite,
            "limite_historique": (
                "Les réponses finalisées, y compris les échecs, sont conservées dans ce profil; les expériences et les comparaisons ne sont pas suivies."
            ),
        }

    def list_profiles(self) -> list[str]:
        with self._connection() as connection:
            return [row[0] for row in connection.execute(
                "SELECT display_name FROM profiles ORDER BY display_name COLLATE NOCASE"
            )]
