"""Issue a one-time recovery code to a verified legacy-profile owner.

Run only on the machine hosting the local SQLite database, from a private
interactive terminal. The code is printed once and is never written to logs or
to a file by this tool. Deliver it to the verified owner through a separate,
private channel. Do not redirect output or run with terminal transcription.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from algorithmes.progression import ProgressionStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profil", help="Nom exact du profil historique vérifié")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Invalide un code de récupération précédent avant d'en émettre un nouveau",
    )
    arguments = parser.parse_args()

    if not sys.stdout.isatty():
        parser.error("exécuter dans un terminal privé interactif, sans redirection")

    try:
        code = ProgressionStore().issue_recovery_code(
            arguments.profil,
            replace_existing=arguments.replace,
        )
    except (OSError, sqlite3.Error, ValueError) as erreur:
        print(f"Attribution impossible : {erreur}", file=sys.stderr)
        return 1

    print("Code à usage unique — à transmettre directement au propriétaire vérifié :")
    print(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
