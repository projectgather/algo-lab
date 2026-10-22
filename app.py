
from pathlib import Path
from streamlit_shortcuts import shortcut_button
from datetime import datetime, timedelta
import random
import sqlite3
import time
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from algorithmes.tri import (
    ALGORITHMES,
    INFORMATIONS_ALGORITHMES,
    PSEUDOCODES,
    calculer_statistiques,
)
from algorithmes.analyse import analyser_differences_distributions, analyser_mesures
from algorithmes.experience import (
    REPETITIONS_MAX_EXPERIENCE,
    TAILLE_MAX_EXPERIENCE,
    TYPES_DONNEES,
    mesurer_evolution,
    generer_donnees,
    mesurer_tri as mesurer_tri_mediane,
)
from algorithmes.exercices import (
    DIFFICULTES,
    TOUS_LES_ALGORITHMES,
    algorithmes_disponibles,
    creer_session,
    statistiques_session,
    utiliser_indice,
    valider_reponse,
)
from algorithmes.entrainement import (
    DIFFICULTES_ENTRAINEMENT,
    TAILLE_SESSION_ENTRAINEMENT,
    creer_session_entrainement,
    passer_question_suivante,
    statistiques_session_entrainement,
    valider_reponse_entrainement,
)
from algorithmes.defi import (
    ALGORITHMES_JOUABLES,
    DIFFICULTES_DEFI,
    TYPES_DEFI,
    DELAI_RAPIDITE_SECONDES,
    consigne_defi,
    contexte_defi,
    creer_defi,
    defi_termine,
    etat_defi,
    progression_defi,
    reinitialiser_defi,
    utiliser_indice as utiliser_indice_defi,
    valider_action as valider_action_defi,
)
from algorithmes.manipulation import (
    ALGORITHMES_MANIPULATION,
    DIFFICULTES_MANIPULATION,
    INTERVALLES_TAILLE,
    TYPES_TABLEAU,
    creer_partie,
    utiliser_indice as utiliser_indice_manipulation,
    valider_action as valider_action_manipulation,
)
from algorithmes.progression import (
    ProgressionAccessGuard,
    ProgressionStore,
    SUCCES,
)

COULEURS_GRAPHIQUES = (
    "#B7A1FF",
    "#55D6A3",
    "#FFC76A",
    "#72C8F2",
    "#FF8290",
    "#A7C978",
)


def charger_style():
    chemin_style = Path(__file__).resolve().parent / ".streamlit" / "style.css"
    with chemin_style.open(encoding="utf-8") as fichier:
        css = fichier.read()

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True
    )

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AlgoLab — Visualiseur d'algorithmes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)
charger_style()

try:
    progression_store = ProgressionAccessGuard(
        ProgressionStore(),
        lambda: st.session_state.get("profil_jeton"),
    )
except (OSError, sqlite3.Error) as erreur_stockage:
    progression_store = None
    st.session_state["progression_erreur"] = str(erreur_stockage)


def enregistrer_progression(operation, *arguments):
    if progression_store is None:
        return None
    try:
        return operation(*arguments)
    except (OSError, sqlite3.Error, ValueError, PermissionError) as erreur_stockage:
        st.session_state["progression_erreur"] = str(erreur_stockage)
        return None


def _effacer_session_profil():
    for cle in (
        "profil_nom", "profil_jeton", "exercices_session",
        "entrainement_session", "defi_interactif",
        "manipulation_partie", "defi_abandon_confirmation",
    ):
        st.session_state.pop(cle, None)
    st.session_state["profil_auth_epoch"] = st.session_state.get(
        "profil_auth_epoch", 0
    ) + 1
    st.session_state["navigation_page"] = "Accueil"


def verrouiller_profil():
    _effacer_session_profil()


def _creer_profil(nom, pin, confirmation):
    try:
        jeton = progression_store.create_profile(nom, pin, confirmation)
        st.session_state["profil_nom"] = nom.strip()
        st.session_state["profil_jeton"] = jeton
        st.session_state.pop("profil_auth_erreur", None)
        st.rerun()
    except (OSError, sqlite3.Error, ValueError) as erreur:
        st.session_state["profil_auth_erreur"] = str(erreur)


def _definir_code_historique(nom, pin, confirmation):
    try:
        jeton = progression_store.set_initial_pin(nom, pin, confirmation)
        st.session_state["profil_nom"] = nom
        st.session_state["profil_jeton"] = jeton
        st.session_state.pop("profil_auth_erreur", None)
        st.rerun()
    except (OSError, sqlite3.Error, ValueError) as erreur:
        st.session_state["profil_auth_erreur"] = str(erreur)


def _deverrouiller_profil(nom, pin):
    try:
        jeton = progression_store.verify_pin(nom, pin)
        if jeton is None:
            st.session_state["profil_auth_erreur"] = (
                "Code incorrect ou accès temporairement verrouillé."
            )
            return
        st.session_state["profil_nom"] = nom
        st.session_state["profil_jeton"] = jeton
        st.session_state.pop("profil_auth_erreur", None)
        st.rerun()
    except (OSError, sqlite3.Error, ValueError):
        st.session_state["profil_auth_erreur"] = (
            "Impossible de vérifier ce profil pour le moment."
        )


def afficher_ecran_authentification():
    if progression_store is None:
        st.error("Progression indisponible : le stockage local n'a pas pu être ouvert.")
        return

    st.title("Accéder à un profil")
    st.caption("Chaque progression est protégée par un code personnel.")
    profils = progression_store.profile_names()
    choix = ["Créer un profil"] if not profils else ["Se connecter", "Créer un profil"]
    mode = st.radio("Accès", choix, horizontal=True, key="profil_auth_mode")

    if mode == "Créer un profil":
        with st.form("profil_creation_form", clear_on_submit=True):
            nom_creation = st.text_input("Nom du profil", max_chars=32)
            pin_creation = st.text_input(
                "Code personnel à 6 chiffres",
                type="password",
                max_chars=6,
            )
            confirmation_creation = st.text_input(
                "Confirmer le code personnel",
                type="password",
                max_chars=6,
            )
            creation_soumise = st.form_submit_button(
                "Créer et ouvrir le profil", type="primary",
            )
        if creation_soumise:
            _creer_profil(nom_creation, pin_creation, confirmation_creation)
    else:
        cle_selection = f"profil_selection_{st.session_state.get('profil_auth_epoch', 0)}"
        st.selectbox(
            "Profil",
            profils,
            index=None,
            placeholder="Choisir un profil",
            key=cle_selection,
        )
        nom = st.session_state.get(cle_selection)
        if nom is None:
            st.caption("Choisissez un profil pour continuer.")
        elif progression_store.profile_has_pin(nom):
            with st.form("profil_connexion_form", clear_on_submit=True):
                pin_connexion = st.text_input(
                    "Code personnel",
                    type="password",
                    max_chars=6,
                )
                connexion_soumise = st.form_submit_button(
                    "Déverrouiller", type="primary",
                )
            if connexion_soumise:
                _deverrouiller_profil(nom, pin_connexion)
        else:
            st.warning(
                "Ce profil historique n'a pas encore de code. Définissez-en un "
                "pour le protéger. Cette installation locale ne peut pas vérifier "
                "rétroactivement l'identité de son propriétaire."
            )
            with st.form("profil_historique_form", clear_on_submit=True):
                pin_historique = st.text_input(
                    "Nouveau code personnel à 6 chiffres",
                    type="password",
                    max_chars=6,
                )
                confirmation_historique = st.text_input(
                    "Confirmer le code personnel",
                    type="password",
                    max_chars=6,
                )
                code_historique_soumis = st.form_submit_button(
                    "Définir le code et ouvrir le profil", type="primary",
                )
            if code_historique_soumis:
                _definir_code_historique(
                    nom, pin_historique, confirmation_historique
                )

    erreur = st.session_state.pop("profil_auth_erreur", None)
    if erreur:
        st.error(erreur)


def afficher_profil_sidebar(nom_profil):
    st.sidebar.divider()
    st.sidebar.subheader("Profil")
    st.sidebar.caption(nom_profil)
    st.sidebar.button(
        "Verrouiller le profil",
        key="profil_verrouiller",
        on_click=verrouiller_profil,
    )

    if progression_store is None:
        st.sidebar.warning(
            "Progression indisponible : le stockage local n'a pas pu être ouvert."
        )
        return nom_profil

    try:
        profil = progression_store.profile(nom_profil)
    except (OSError, sqlite3.Error, ValueError, PermissionError):
        st.sidebar.warning("Progression indisponible ou profil verrouillé.")
        return

    st.sidebar.markdown(f"**Niveau {profil['niveau_index']} · {profil['niveau']}**")
    st.sidebar.metric("Expérience", f"{profil['xp']} XP")
    if profil["seuil_suivant"] is None:
        st.sidebar.progress(1.0)
        st.sidebar.caption("Niveau maximal atteint")
    else:
        xp_niveau = profil["xp"] - profil["seuil_actuel"]
        largeur_niveau = profil["seuil_suivant"] - profil["seuil_actuel"]
        st.sidebar.progress(profil["progression_niveau"])
        st.sidebar.caption(
            f"{xp_niveau} / {largeur_niveau} XP · prochain niveau à "
            f"{profil['seuil_suivant']} XP"
        )
    if profil["titre"]:
        st.sidebar.caption(f"Titre : {profil['titre']}")

    erreur_precedente = st.session_state.pop("progression_erreur", None)
    if erreur_precedente:
        st.sidebar.warning("Progression non enregistrée.")


def profil_authentifie():
    nom_profil = st.session_state.get("profil_nom")
    jeton = st.session_state.get("profil_jeton")
    if progression_store is not None and progression_store.is_authorized(nom_profil, jeton):
        return nom_profil
    if nom_profil is not None or jeton is not None:
        _effacer_session_profil()
    return None


def naviguer_vers_page(page_cible):
    st.session_state["navigation_page"] = page_cible


def ouvrir_recommandation(nom_profil, recommandation):
    page_cible = recommandation["page"]
    st.session_state["navigation_page"] = page_cible
    if page_cible == "Exercices":
        session = creer_session(
            recommandation["algorithme"],
            recommandation["difficulte"],
            nombre_questions=6,
        )
        question = next(
            (item for item in session["questions"]
             if item["type"] == recommandation["type_question"]),
            None,
        )
        if question is not None:
            session["questions"] = [question]
            session["index_question"] = 0
            session["profil_nom"] = nom_profil
            st.session_state["exercices_session"] = session
    elif page_cible == "Entraînement":
        session = creer_session_entrainement(
            recommandation["difficulte"],
            nombre_questions=1,
            type_question_initial=recommandation["type_question"],
            notion_initiale=recommandation["notion"],
        )
        session["profil_nom"] = nom_profil
        st.session_state["entrainement_session"] = session


def afficher_page_accueil(nom_profil):
    historique = []
    recommandation = None
    if progression_store is not None:
        try:
            historique = progression_store.activity_history(nom_profil, limit=1)
            if historique:
                recommandation = progression_store.parcours_pedagogique(
                    nom_profil
                )["recommandation"]
        except (OSError, sqlite3.Error, ValueError) as erreur_stockage:
            st.warning("Progression indisponible : " + str(erreur_stockage))

    with st.container(key="accueil_hero"):
        colonne_texte, colonne_schema = st.columns([1.2, 0.8], gap="large")
        with colonne_texte:
            st.markdown(
                '<p class="accueil-kicker">ALGORITHMES · COMPRENDRE EN PRATIQUANT</p>',
                unsafe_allow_html=True,
            )
            st.title("Comprendre les algorithmes, pas à pas.")
            st.markdown(
                '<p class="accueil-lead">Observe comment un tri transforme une liste, '
                'puis vérifie ta compréhension par la pratique.</p>',
                unsafe_allow_html=True,
            )
            st.button(
                "Lancer une visualisation",
                type="primary",
                key="accueil_visualiser",
                on_click=naviguer_vers_page,
                args=("Visualiser",),
            )
            st.markdown(
                '<div class="accueil-points-forts">'
                '<span><strong>06</strong> algorithmes de tri</span>'
                '<span><strong>Pas à pas</strong> avec pseudo-code</span>'
                '<span><strong>En pratique</strong> exercices et défis</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with colonne_schema:
            st.markdown(
                '<div class="accueil-schema" aria-label="Observer, suivre les étapes, vérifier">'
                '<div class="accueil-schema-head"><span>UNE EXÉCUTION</span>'
                '<span>EN TROIS TEMPS</span></div>'
                '<div class="accueil-schema-row"><span class="accueil-schema-index">01</span>'
                '<span>Observer l’état</span><span class="accueil-schema-mark">●</span></div>'
                '<div class="accueil-schema-row"><span class="accueil-schema-index">02</span>'
                '<span>Suivre la règle</span><span class="accueil-schema-mark">↗</span></div>'
                '<div class="accueil-schema-row"><span class="accueil-schema-index">03</span>'
                '<span>Vérifier le résultat</span><span class="accueil-schema-mark">✓</span></div>'
                '<div class="accueil-schema-foot">De l’intuition à l’explication</div></div>',
                unsafe_allow_html=True,
            )

    with st.container(key="accueil_reprise"):
        if recommandation:
            st.markdown(
                '<p class="accueil-kicker">POUR CONTINUER</p>'
                '<h2 class="accueil-reprise-title">Reprends là où tu peux progresser</h2>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**{recommandation['competence']}** · {recommandation['exercice']}"
            )
            st.caption(recommandation["raison"])
            st.button(
                "Continuer avec la recommandation",
                type="primary",
                key="accueil_recommandation",
                on_click=ouvrir_recommandation,
                args=(nom_profil, recommandation),
            )
        elif not historique:
            st.markdown(
                '<p class="accueil-kicker">PREMIÈRE ÉTAPE</p>'
                '<h2 class="accueil-reprise-title">Commence par observer un tri.</h2>',
                unsafe_allow_html=True,
            )
            st.markdown(
                "Aucun historique pour ce profil. Une visualisation te permettra de "
                "découvrir les étapes avant de passer aux exercices."
            )
        else:
            st.info("La progression de ce profil n’est pas disponible pour le moment.")

    st.markdown(
        '<div class="accueil-section-heading"><p class="accueil-kicker">À EXPLORER</p>'
        '<h2>Choisis ta prochaine étape</h2></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="accueil_destinations"):
        colonnes = st.columns(3, gap="medium")
        destinations = (
            (
                "Visualiser",
                "Observe les changements de la liste et le pseudo-code synchronisé.",
                "Ouvrir la visualisation",
                "Visualiser",
            ),
            (
                "Exercices",
                "Prédiction, compréhension et remise en ordre, avec corrections et indices.",
                "Aller aux exercices",
                "Exercices",
            ),
            (
                "Comparer",
                "Compare les six tris sur une même entrée et examine leurs opérations.",
                "Comparer les tris",
                "Comparer",
            ),
        )
        for index, (colonne, (titre, description, libelle, page_cible)) in enumerate(
            zip(colonnes, destinations), start=1
        ):
            with colonne:
                st.markdown(
                    f'<div class="accueil-destination">'
                    f'<span class="accueil-destination-index">{index:02}</span>'
                    f'<h3>{titre}</h3><p>{description}</p></div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    libelle,
                    key=f"accueil_vers_{page_cible.casefold()}",
                    on_click=naviguer_vers_page,
                    args=(page_cible,),
                )

    st.markdown(
        '<div class="accueil-ateliers-heading"><h3>Autres ateliers</h3>'
        '<p>Change de format pour approfondir ou expérimenter.</p></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="accueil_ateliers"):
        colonnes_ateliers = st.columns(4, gap="small")
        ateliers = (
            ("Entraînement", "Séances guidées"),
            ("Défi interactif", "Résoudre les étapes"),
            ("Manipulation", "Agir sur le tableau"),
            ("Expérimenter", "Tester des distributions"),
        )
        for colonne, (page_cible, description) in zip(colonnes_ateliers, ateliers):
            with colonne:
                st.markdown(
                    f'<div class="accueil-atelier"><strong>{page_cible}</strong>'
                    f'<span>{description}</span></div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    f"Ouvrir {page_cible.casefold()}",
                    key=f"accueil_atelier_{page_cible.casefold().replace(' ', '_')}",
                    on_click=naviguer_vers_page,
                    args=(page_cible,),
                )


def afficher_page_profil(nom_profil):
    st.title("Profil")
    st.caption("Profil local protégé par un code personnel · données conservées sur cette installation.")
    if progression_store is None:
        st.warning("Progression indisponible : le stockage local n'a pas pu être ouvert.")
        return

    try:
        profil = progression_store.profile(nom_profil)
        profil_id = profil["profile_id"]
    except (OSError, sqlite3.Error, ValueError) as erreur_stockage:
        st.warning("Progression indisponible : " + str(erreur_stockage))
        return

    with st.container(key="profil_hero"):
        colonne_identite, colonne_niveau = st.columns([2, 1])
        with colonne_identite:
            st.caption("PROFIL ACTIF")
            st.subheader(profil["display_name"])
            st.markdown(
                f"Niveau **{profil['niveau_index']} · {profil['niveau']}** · "
                f"Titre actif : **{profil['titre'] or 'aucun'}**"
            )
        with colonne_niveau:
            st.metric("Expérience totale", f"{profil['xp']} XP")
            if profil["seuil_suivant"] is None:
                st.progress(1.0)
                st.caption("Niveau maximal atteint")
            else:
                st.progress(profil["progression_niveau"])
                st.caption(
                    f"{profil['xp'] - profil['seuil_actuel']} / "
                    f"{profil['seuil_suivant'] - profil['seuil_actuel']} XP dans ce niveau"
                )

    with st.container(key="profil_filtres"):
        colonnes_filtres = st.columns(3)
        periode = colonnes_filtres[0].selectbox(
            "Période",
            ("Toutes les dates", "7 derniers jours", "30 derniers jours", "90 derniers jours"),
            key=f"profil_periode_{profil_id}",
        )
        algorithme_filtre = colonnes_filtres[1].selectbox(
            "Algorithme",
            ("Tous les algorithmes", *ALGORITHMES),
            key=f"profil_algorithme_{profil_id}",
        )
        activite_labels = {
            "Toutes les activités": None,
            "Exercices": "exercise",
            "Défis": "challenge",
            "Manipulations": "manipulation",
        }
        activite_label = colonnes_filtres[2].selectbox(
            "Type d'activité",
            tuple(activite_labels),
            key=f"profil_activite_{profil_id}",
        )
        duree = {"7 derniers jours": 7, "30 derniers jours": 30, "90 derniers jours": 90}.get(periode)
        date_debut = (
            (datetime.now().date() - timedelta(days=duree)).isoformat()
            if duree else None
        )

    try:
        tableau = progression_store.dashboard_data(
            nom_profil,
            date_debut=date_debut,
            algorithme=None if algorithme_filtre == "Tous les algorithmes" else algorithme_filtre,
            activite=activite_labels[activite_label],
            limite_historique=100,
        )
        parcours = progression_store.parcours_pedagogique(nom_profil)
    except (OSError, sqlite3.Error, ValueError) as erreur_stockage:
        st.warning("Progression indisponible : " + str(erreur_stockage))
        return

    if not tableau["profil_a_des_donnees"]:
        with st.container(border=True):
            st.subheader("Ton parcours commence ici")
            st.write("Aucune activité n'est encore enregistrée pour ce profil.")
            st.button(
                "Commencer un exercice",
                key=f"profil_demarrer_{profil_id}",
                on_click=naviguer_vers_page,
                args=("Exercices",),
            )
    else:
        meilleur_record = max(
            tableau["records"].items(), key=lambda item: item[1], default=None
        )
        competences_maitrisees = sum(
            competence["statut"] == "maîtrisée" for competence in tableau["competences"]
        )
        with st.container(key="profil_indicateurs"):
            st.subheader("Activité et réussite")
            colonnes = st.columns(4)
            colonnes[0].metric("Activités terminées", tableau["activites_terminees"])
            colonnes[1].metric(
                "Défis validés enregistrés", tableau["defis_valides_enregistres"]
            )
            taux = tableau["taux_reussite"]
            colonnes[2].metric("Réussite aux questions", "—" if taux is None else f"{taux:.0%}")
            colonnes[3].metric(
                "Compétences maîtrisées",
                f"{competences_maitrisees} / {len(tableau['competences'])}",
            )
            st.caption("Ces indicateurs suivent les filtres sélectionnés.")
            st.subheader("Réussites et record")
            st.caption("Les réussites suivent les filtres; le record est conservé tous temps pour le profil.")
            colonnes = st.columns(2)
            colonnes[0].metric(
                "Algorithmes réussis",
                f"{len(tableau['algorithmes_reussis'])} / {len(ALGORITHMES)}",
            )
            colonnes[1].metric(
                "Meilleur record (un mode)",
                "—" if meilleur_record is None else f"{meilleur_record[1]} · {meilleur_record[0]}",
            )
            st.caption(
                "Une activité est une réponse d'exercice finalisée, un défi validé ou une "
                "manipulation réussie. Le taux porte uniquement sur les réponses d'exercice "
                "finalisées dont la correction est enregistrée."
            )

    st.header("Progrès")
    st.caption("Les résultats par question et compétences ci-dessous suivent les filtres sélectionnés.")
    gauche, droite = st.columns(2)
    if tableau["evolution"]:
        figure = go.Figure(go.Scatter(
            x=[item["date"] for item in tableau["evolution"]],
            y=[item["taux"] * 100 for item in tableau["evolution"]],
            customdata=[item["evaluees"] for item in tableau["evolution"]],
            mode="lines+markers",
            line=dict(color=COULEURS_GRAPHIQUES[1], width=3),
            hovertemplate="%{x}<br>%{y:.0f}% · %{customdata} réponse(s)<extra></extra>",
        ))
        styliser_figure(figure, hauteur=250)
        figure.update_layout(title="Réussite dans le temps", yaxis_title="Réponses correctes (%)")
        figure.update_xaxes(tickformat="%d %b", dtick=86400000)
        figure.update_yaxes(range=[0, 100])
        gauche.plotly_chart(figure, width="stretch")
    else:
        gauche.info("Aucune réponse d'exercice évaluable sur cette période.")

    performances_algorithmes = tableau["par_algorithme"]
    if performances_algorithmes:
        figure = go.Figure(go.Bar(
            x=[item["taux"] * 100 for item in performances_algorithmes],
            y=[item["nom"] for item in performances_algorithmes],
            customdata=[item["evaluees"] for item in performances_algorithmes],
            orientation="h",
            marker_color=COULEURS_GRAPHIQUES[3],
            hovertemplate="%{y}<br>%{x:.0f}% · %{customdata} réponse(s)<extra></extra>",
        ))
        styliser_figure(figure, hauteur=max(210, 30 * len(performances_algorithmes)))
        figure.update_layout(title="Réussite par algorithme", xaxis_title="Réponses correctes (%)")
        figure.update_xaxes(range=[0, 100])
        droite.plotly_chart(figure, width="stretch")
    else:
        droite.info("Aucune réponse évaluable par algorithme.")

    noms_types = {
        "etat": "État du tableau", "prediction": "Prédiction",
        "prediction_choix": "Prédiction à choix", "prediction_texte": "Prédiction rédigée",
        "ordre": "Ordre des étapes", "comprehension": "Compréhension",
        "choix_algorithme_entrainement": "Choix d'algorithme",
    }
    colonne_types, colonne_competences = st.columns(2)
    colonne_types.subheader("Résultats par type de question")
    performances_types = tableau["par_type_question"]
    if performances_types:
        figure = go.Figure(go.Bar(
            x=[noms_types.get(item["nom"], item["nom"]) for item in performances_types],
            y=[item["taux"] * 100 for item in performances_types],
            customdata=[item["evaluees"] for item in performances_types],
            marker_color=COULEURS_GRAPHIQUES[2],
            hovertemplate="%{x}<br>%{y:.0f}% · %{customdata} réponse(s)<extra></extra>",
        ))
        styliser_figure(figure, hauteur=250)
        figure.update_layout(yaxis_title="Réponses correctes (%)")
        figure.update_yaxes(range=[0, 100])
        colonne_types.plotly_chart(figure, width="stretch")
    else:
        colonne_types.info("Aucun type de question n'a encore été évalué dans ce filtre.")

    competences = tableau["competences"]
    statuts_competences = ("maîtrisée", "en cours", "à revoir", "non évaluée")
    couleurs_statuts = {"maîtrisée": "#55D6A3", "en cours": "#FFC76A", "à revoir": "#FF8290", "non évaluée": "#72798E"}
    comptes_statuts = {
        statut: sum(item["statut"] == statut for item in competences)
        for statut in statuts_competences
    }
    if tableau["profil_a_des_donnees"]:
        figure = go.Figure(go.Bar(
            x=list(comptes_statuts), y=list(comptes_statuts.values()),
            marker_color=[couleurs_statuts[statut] for statut in comptes_statuts],
            hovertemplate="%{x} · %{y} compétence(s)<extra></extra>",
        ))
        styliser_figure(figure, hauteur=220)
        figure.update_layout(title="État des compétences", yaxis_title="Nombre de compétences")
        figure.update_yaxes(dtick=1, rangemode="tozero")
        colonne_competences.plotly_chart(figure, width="stretch")
    else:
        colonne_competences.info("Les compétences apparaîtront ici après les premières réponses évaluées.")
    colonne_competences.subheader("Compétences observées")
    for competence in competences:
        st.markdown(
            f"**{competence['nom']}** · {competence['statut']} · "
            f"{competence['reussites']} réussite(s) / "
            f"{competence['observations']} réponse(s) évaluée(s)"
        )

    st.header("Points à travailler")
    difficultes = []
    for libelle, resultats in (
        ("algorithme", tableau["par_algorithme"]),
        ("type de question", tableau["par_type_question"]),
    ):
        for resultat in resultats:
            erreurs = resultat["evaluees"] - resultat["reussites"]
            if erreurs:
                nom = resultat["nom"]
                if libelle == "type de question":
                    nom = noms_types.get(nom, nom)
                niveau = "difficulté récurrente" if erreurs >= 2 else "erreur ponctuelle"
                difficultes.append(f"{nom} : {erreurs} erreur(s), {niveau}.")
    if difficultes:
        for difficulte in difficultes:
            st.write("• " + difficulte)
    elif tableau["questions_evaluees"]:
        st.write("Aucune erreur enregistrée dans les réponses évaluées par ces filtres.")
    else:
        st.write("Pas encore assez de réponses évaluables pour repérer une difficulté.")
    for competence in competences:
        if competence["statut"] in ("à revoir", "en cours"):
            st.caption(
                f"{competence['nom']} · {competence['statut']} · "
                f"{competence['erreurs']} erreur(s) observée(s)."
            )

    st.header("Mon parcours")
    st.caption("Cette vue pédagogique s'appuie sur l'ensemble de l'historique, indépendamment des filtres.")
    st.caption(parcours["limite_historique"])
    st.subheader("Compétences évaluées")
    for competence in parcours["competences_detaillees"]:
        st.markdown(f"**{competence['nom']}** · {competence['statut']}")
        st.caption(competence["detail"])
    st.caption(parcours["autonomie"]["detail"])

    recommandation = parcours["recommandation"]
    st.subheader("À travailler ensuite")
    st.markdown(f"**{recommandation['competence']}** · {recommandation['exercice']}")
    st.caption(recommandation["raison"])
    st.caption("Cette recommandation s'appuie sur l'ensemble du parcours, indépendamment des filtres ci-dessus.")
    st.button(
        "Lancer l'exercice recommandé",
        key=f"recommandation_{profil['profile_id']}",
        on_click=ouvrir_recommandation,
        args=(nom_profil, recommandation),
    )

    st.subheader("Objectifs")
    for objectif in parcours["objectifs"]:
        colonne_texte, colonne_action = st.columns([4, 1])
        with colonne_texte:
            st.markdown(f"**{objectif['nom']}** · {objectif['statut']}")
            st.caption(f"{objectif['progression']} · {objectif['raison']}")
        if objectif["statut"] != "termine":
            colonne_action.button(
                objectif["bouton"],
                key=f"objectif_{objectif['id']}_{profil['profile_id']}",
                on_click=naviguer_vers_page,
                args=(objectif["page"],),
            )

    prochaine_activite = parcours["prochaine_activite"]
    st.subheader("Prochaine activité")
    st.info(f"{prochaine_activite['nom']} · {prochaine_activite['raison']}")
    st.button(
        prochaine_activite["bouton"],
        key=f"prochaine_activite_{profil['profile_id']}",
        on_click=naviguer_vers_page,
        args=(prochaine_activite["page"],),
    )

    with st.container(key="profil_recompenses"):
        st.header("Récompenses")
        if tableau["records"]:
            st.subheader("Records par mode de défi")
            st.caption("Records tous temps du profil. Chaque mode a ses propres règles : les scores ne sont pas comparables entre eux.")
            colonnes_records = st.columns(min(3, len(tableau["records"])))
            for index, (mode, score) in enumerate(sorted(tableau["records"].items())):
                colonnes_records[index % len(colonnes_records)].metric(mode, f"{score} / 100")

        st.subheader("Succès débloqués")
        succes_debloques = [succes for succes in profil["succes"] if succes["debloque"]]
        st.caption(f"{len(succes_debloques)} sur {len(profil['succes'])}")
        if not succes_debloques:
            st.info("Aucun succès débloqué pour le moment.")
        else:
            for debut in range(0, len(succes_debloques), 2):
                colonnes = st.columns(2)
                for colonne, succes in zip(colonnes, succes_debloques[debut:debut + 2]):
                    with colonne:
                        with st.container(border=True):
                            st.subheader(succes["nom"])
                            st.write(succes["condition"])
                            if succes["date"]:
                                try:
                                    date = datetime.fromisoformat(succes["date"])
                                    date_affichee = date.strftime("%d/%m/%Y à %H:%M")
                                except ValueError:
                                    date_affichee = succes["date"]
                                st.caption("Débloqué le " + date_affichee)
                            if succes["titre"]:
                                st.caption("Titre obtenu · " + succes["titre"])

        st.subheader("Titres")
        titres = [
            succes["titre"]
            for succes in succes_debloques
            if succes["titre"]
        ]
        if titres:
            titre_selectionne = st.selectbox(
                "Titre actif",
                ["Aucun titre", *titres],
                index=(titres.index(profil["titre"]) + 1 if profil["titre"] in titres else 0),
                key=f"titre_profil_{profil['profile_id']}",
            )
            if st.button("Équiper le titre", key=f"equiper_titre_{profil['profile_id']}"):
                try:
                    progression_store.set_title(
                        nom_profil,
                        "" if titre_selectionne == "Aucun titre" else titre_selectionne,
                    )
                    st.rerun()
                except (OSError, sqlite3.Error, ValueError) as erreur_stockage:
                    st.warning("Titre non modifié : " + str(erreur_stockage))
        else:
            st.info("Les titres se débloquent avec les succès.")

    st.header("Activités récentes")
    st.caption("Les 100 événements les plus récents au maximum sont affichés.")
    historique = tableau["historique"]
    with st.container(key="profil_historique"):
        if not historique:
            st.info("Aucune activité ne correspond à ces filtres.")
        else:
            libelles = {
                "exercise": "Exercice",
                "challenge": "Défi validé",
                "manipulation": "Manipulation",
                "achievement": "Succès débloqué",
            }
            for evenement in historique:
                if evenement["activite"] == "achievement":
                    succes_id = evenement["metadata"].get("achievement")
                    nom = SUCCES.get(succes_id, {}).get("nom", succes_id or "Succès")
                    description = f"{libelles['achievement']} · {nom}"
                else:
                    description = libelles.get(evenement["activite"], evenement["activite"])
                    description += f" · {evenement['algorithme']} · {evenement['difficulte']}"
                    if evenement["type_question"]:
                        description += (
                            f" · {noms_types.get(evenement['type_question'], evenement['type_question'])}"
                        )
                try:
                    date = datetime.fromisoformat(evenement["date"])
                    date_affichee = date.strftime("%d/%m/%Y à %H:%M")
                except (TypeError, ValueError):
                    date_affichee = evenement["date"]
                details = [date_affichee]
                metadata = evenement["metadata"]
                if evenement["activite"] == "exercise":
                    correcte = metadata.get("correcte")
                    resultat = (
                        "réussite" if correcte is True else
                        "à revoir" if correcte is False else "résultat ancien non détaillé"
                    )
                    details.append(resultat)
                elif evenement["activite"] != "achievement":
                    details.append("réussi" if evenement["reussie"] else "non validé")
                if isinstance(metadata.get("tentatives"), int):
                    details.append(f"{metadata['tentatives']} tentative(s)")
                indices = metadata.get("indices_utilises")
                if isinstance(indices, int):
                    details.append(f"{indices} indice(s)")
                elif metadata.get("no_hint") is False:
                    details.append("indice utilisé")
                details.append(f"+{evenement['xp']} XP")
                st.markdown(f"**{description}** · " + " · ".join(details))

# =========================================================
# FONCTIONS D'AFFICHAGE ET DE CALCUL
# =========================================================

def lire_liste(saisie):
    """Convertit une saisie comme '5, 2, 4, 1' en liste d'entiers."""
    morceaux = saisie.split(",")

    if not morceaux or any(not morceau.strip() for morceau in morceaux):
        raise ValueError("Saisie vide ou séparateur incorrect.")

    return [int(morceau.strip()) for morceau in morceaux]


def arreter_animation():
    st.session_state["animation_active"] = False
    st.session_state["animation_dernier_tick"] = None
    st.session_state["visualisation_reinitialisee"] = False


def demarrer_animation():
    etapes = st.session_state.get("etapes", [])
    curseur = st.session_state.get("curseur_etape", 0)
    if curseur < len(etapes) - 1:
        st.session_state["animation_active"] = True
        st.session_state["animation_dernier_tick"] = None
        st.session_state["visualisation_reinitialisee"] = False


def pauser_animation():
    st.session_state["animation_active"] = False
    st.session_state["animation_dernier_tick"] = None
    st.session_state["visualisation_reinitialisee"] = False


def deplacer_curseur_visualisation(delta):
    etapes = st.session_state.get("etapes", [])
    if not etapes:
        return
    dernier = len(etapes) - 1
    curseur = st.session_state.get("curseur_etape", 0)
    st.session_state["curseur_etape"] = max(0, min(curseur + delta, dernier))
    st.session_state["animation_active"] = False
    st.session_state["animation_dernier_tick"] = None
    st.session_state["visualisation_reinitialisee"] = False


def reinitialiser_lecture_visualisation():
    st.session_state["curseur_etape"] = 0
    st.session_state["animation_active"] = False
    st.session_state["animation_dernier_tick"] = None
    st.session_state["visualisation_reinitialisee"] = True


def invalider_visualisation():
    st.session_state["animation_active"] = False
    st.session_state["animation_dernier_tick"] = None
    st.session_state.pop("etapes", None)
    st.session_state.pop("curseur_etape", None)
    st.session_state.pop("visualisation_reinitialisee", None)


def afficher_definitions_compteurs():
    st.caption(
        "Compteurs cumulés : comparaisons = tests entre valeurs; échanges = "
        "permutations de deux cases; déplacements/écritures = décalages et copies. "
        "Fusion compte les copies vers les tampons puis vers le tableau. "
        "Une étape est un instantané, pas une opération; opérations = échanges + déplacements."
    )


def styliser_figure(figure, hauteur=380):
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(
            family="Aptos, Segoe UI, sans-serif",
            color="#E8E5F2",
            size=13,
        ),
        colorway=COULEURS_GRAPHIQUES,
        margin=dict(l=18, r=22, t=32, b=42),
        height=hauteur,
        hoverlabel=dict(
            bgcolor="#1D2232",
            bordercolor="#B7A1FF",
            font=dict(color="#F4F2FA", size=13),
        ),
    )
    figure.update_xaxes(
        automargin=True,
        showgrid=False,
        zeroline=False,
        tickfont=dict(color="#AAA8B9"),
        title_font=dict(color="#C5C1D2"),
    )
    figure.update_yaxes(
        automargin=True,
        gridcolor="rgba(190, 184, 216, 0.13)",
        zeroline=False,
        tickfont=dict(color="#AAA8B9"),
        title_font=dict(color="#C5C1D2"),
    )
    return figure



def afficher_barres(etape, est_final=False, nom_algorithme=None):
    valeurs = etape["liste"]
    indices = etape["indices"]
    action = etape["action"]
    details = etape["details"]
    zones = details.get("zones", ())
    indices_actifs = indices or ()
    couleurs = {
        "repos": "#72798E",
        "compare": "#FFC76A",
        "mutation": "#FF8290",
        "selection": "#B7A1FF",
        "pivot": "#72C8F2",
        "place": "#55D6A3",
        "gauche": "#B7A1FF",
        "droite": "#72C8F2",
        "zone_pivot": "#55D6A3",
        "prefixe_trie": "#72C8F2",
    }
    classes = {
        "repos": "array-cell-idle",
        "compare": "array-cell-compare",
        "mutation": "array-cell-mutation",
        "selection": "array-cell-selected",
        "pivot": "array-cell-pivot",
        "place": "array-cell-placed",
        "gauche": "array-cell-left",
        "droite": "array-cell-right",
        "zone_pivot": "array-cell-pivot-zone",
        "prefixe_trie": "array-cell-sorted",
    }
    statuts = {
        "repos": "à traiter",
        "compare": "comparé",
        "mutation": "modifié",
        "selection": "sélectionné",
        "pivot": "pivot",
        "place": "placé définitivement",
        "gauche": "moitié gauche",
        "droite": "moitié droite",
        "zone_pivot": "égal au pivot",
        "prefixe_trie": "préfixe trié",
    }

    roles = ["repos"] * len(valeurs)
    if (
        nom_algorithme == "Tri par insertion"
        and action == "comparaison"
        and indices_actifs
    ):
        indices_actifs = (indices_actifs[0],)
    for indice in range(len(valeurs)):
        role = "repos"
        if est_final:
            role = "place"
        elif details.get("heap_size") is not None and indice >= details["heap_size"]:
            role = "place"
        elif action in ("echange", "deplacement", "insertion", "ecriture") and indice in indices_actifs:
            role = "mutation"
        elif (
            nom_algorithme == "Tri par sélection"
            and action == "comparaison"
            and len(indices_actifs) > 1
            and indice == indices_actifs[1]
        ):
            role = "selection"
        elif action == "comparaison" and indice in indices_actifs:
            role = "compare"
            if indice == details.get("pivot_index"):
                role = "pivot"
        elif indice == details.get("pivot_index"):
            role = "pivot"
        elif details.get("zone_placee") is not None and (
            details["zone_placee"][0] <= indice <= details["zone_placee"][1]
        ):
            role = "place"
        elif details.get("prefixe_trie") is not None and (
            details["prefixe_trie"][0] <= indice <= details["prefixe_trie"][1]
        ):
            role = "prefixe_trie"
        elif action == "initialisation" and indices is not None and indice in indices_actifs:
            role = "selection"
        elif details.get("partition") is not None:
            moins, courant, plus = details["partition"]
            if indice < moins:
                role = "gauche"
            elif indice < courant:
                role = "zone_pivot"
            elif indice > plus:
                role = "droite"
        elif action == "partition":
            for debut, fin, zone in zones:
                if debut <= indice <= fin:
                    role = {"gauche": "gauche", "droite": "droite", "pivot": "zone_pivot"}.get(zone, "repos")
                    break
        elif action in ("fusion", "placement", "ecriture", "comparaison"):
            for debut, fin, zone in zones:
                if debut <= indice <= fin:
                    role = zone if zone in ("gauche", "droite") else "repos"
                    break
        roles[indice] = role

    couleurs_cellules = [couleurs[role] for role in roles]

    figure = go.Figure(
        data=[
            go.Bar(
                x=list(range(len(valeurs))),
                y=valeurs,
                marker_color=couleurs_cellules,
                text=valeurs if len(valeurs) <= 18 else None,
                textposition="auto" if len(valeurs) <= 18 else "none",
                textfont=dict(color="#E8E5F2", size=11),
                hovertemplate=(
                    "Position : %{x}<br>"
                    "Valeur : %{y}<extra></extra>"
                ),
            )
        ]
    )

    
    styliser_figure(figure, hauteur=390)
    figure.update_layout(
        bargap=0.22,
        showlegend=False,
        transition_duration=200,
    )
    figure.update_xaxes(
        title_text="Position dans la liste",
        dtick=max(1, (len(valeurs) + 11) // 12),
    )
    figure.update_yaxes(title_text="Valeur", rangemode="tozero")

    st.plotly_chart(
        figure,
        width="stretch",
        key="graphique_tri",
    )

    cellules = "".join(
        f'<div class="array-cell {classes[role]}" title="Position {indice} : {statuts[role]}">'
        f"<small>{indice} · {statuts[role]}</small><strong>{valeur}</strong></div>"
        for indice, (valeur, role) in enumerate(zip(valeurs, roles))
    )
    cle_en_cours = ""
    if (
        nom_algorithme == "Tri par insertion"
        and etape["valeur_en_cours"] is not None
        and action in ("initialisation", "comparaison", "deplacement")
    ):
        cle_en_cours = (
            '<div class="array-key" title="Valeur conservée hors du tableau">'
            f'<small>Clé en cours</small><strong>{etape["valeur_en_cours"]}</strong></div>'
        )
    st.markdown(
        f'<div class="array-visualisation" aria-label="Tableau à trier">{cellules}{cle_en_cours}</div>',
        unsafe_allow_html=True,
    )


def afficher_legende_tableau():
    st.markdown(
        '<div class="array-legend">'
        '<span><i class="legend-compare"></i>Comparé</span>'
        '<span><i class="legend-mutation"></i>Échangé ou modifié</span>'
        '<span><i class="legend-selection"></i>Sélectionné</span>'
        '<span><i class="legend-pivot"></i>Pivot</span>'
        '<span><i class="legend-placed"></i>Placé définitivement / résultat final</span>'
        '<span><i class="legend-sorted"></i>Préfixe trié (insertion)</span>'
        '<span><i class="legend-zones"></i>Zone ou moitié de travail</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def afficher_vue_fusion(etape):
    details = etape["details"]
    valeurs = etape["liste"]
    action = etape["action"]
    debut, fin = details.get("zone_active", (0, len(valeurs) - 1))
    profondeur = details.get("profondeur", 0)

    def cellule_fusion(valeur, indice, classe=""):
        contenu = "·" if valeur is None else str(valeur)
        etiquette = "" if indice is None else f"<small>{indice}</small>"
        return (
            f'<div class="fusion-cell {classe}">'
            f"{etiquette}<strong>{contenu}</strong></div>"
        )

    st.markdown("#### Découpage et fusion")
    st.caption(f"Segment actif [{debut}..{fin}] · niveau récursif {profondeur}")

    if action in ("initialisation", "fin"):
        titre = "Tableau d'entrée" if action == "initialisation" else "Tableau trié"
        classe = "fusion-place" if action == "fin" else ""
        cellules = "".join(
            cellule_fusion(valeur, indice, classe)
            for indice, valeur in enumerate(valeurs)
        )
        st.markdown(
            f'<div class="fusion-visualisation"><div class="fusion-row">'
            f'<span class="fusion-label">{titre}</span>'
            f'<div class="fusion-cells">{cellules}</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    if action in ("division", "recursion", "base"):
        zones = details.get("zones", ((debut, fin, "gauche"),))
        lignes = []
        for gauche, droite, role in zones:
            if droite < gauche:
                continue
            cellules = "".join(
                cellule_fusion(valeurs[indice], indice, role)
                for indice in range(gauche, droite + 1)
            )
            lignes.append(
                f'<div class="fusion-row"><span class="fusion-label">'
                f"Sous-tableau {role}</span><div class=\"fusion-cells\">{cellules}</div></div>"
            )
        st.markdown(
            f'<div class="fusion-visualisation">{"".join(lignes)}</div>',
            unsafe_allow_html=True,
        )
        return

    gauche = details.get("tampon_gauche", [])
    droite = details.get("tampon_droit", [])
    tampon = details.get("tampon", [])
    curseur_gauche = details.get("curseur_gauche", 0)
    curseur_droit = details.get("curseur_droit", 0)
    destination = details.get("destination")
    source = details.get("source")
    indices_comparaison = etape["indices"] if action == "comparaison" else ()

    def ligne_source(nom, donnees, offset, curseur, couleur):
        cellules = []
        for position, valeur in enumerate(donnees):
            indice = offset + position
            if indice in indices_comparaison:
                classe = "fusion-active"
            elif action == "placement" and indice == source:
                classe = "fusion-mutation"
            elif position < curseur:
                classe = "fusion-place"
            else:
                classe = couleur
            cellules.append(cellule_fusion(valeur, indice, classe))
        return (
            f'<div class="fusion-row"><span class="fusion-label">{nom}</span>'
            f'<div class="fusion-cells">{"".join(cellules)}</div></div>'
        )

    sources = (
        ligne_source("Moitié gauche", gauche, debut, curseur_gauche, "fusion-gauche")
        + ligne_source("Moitié droite", droite, debut + len(gauche), curseur_droit, "fusion-droite")
    )
    cellules_tampon = []
    for position in range(fin - debut + 1):
        indice = debut + position
        valeur = tampon[position] if position < len(tampon) else None
        classe = "fusion-cible" if indice == destination else "fusion-place"
        if valeur is None:
            classe = "fusion-vide fusion-cible" if indice == destination else "fusion-vide"
        cellules_tampon.append(cellule_fusion(valeur, indice, classe))
    sortie = (
        f'<div class="fusion-row"><span class="fusion-label">'
        f"Tampon → A[{debut}..{fin}]</span>"
        f'<div class="fusion-cells">{"".join(cellules_tampon)}</div></div>'
    )
    st.markdown(
        f'<div class="fusion-visualisation">{sources}{sortie}</div>',
        unsafe_allow_html=True,
    )


def afficher_vue_rapide(etape):
    details = etape["details"]
    valeurs = etape["liste"]
    gauche, droite = details.get("zone_active", (0, len(valeurs) - 1))
    pivot = details.get("pivot_value")
    indice_pivot = details.get("pivot_index")
    partition = details.get("partition")
    zones_finales = details.get("zones", ())
    indices = etape["indices"] or ()

    st.markdown("#### Partition trois voies")
    if pivot is not None:
        st.caption(f"Segment actif [{gauche}..{droite}] · pivot {pivot} en position {indice_pivot}")
    else:
        st.caption(f"Sous-tableau récursif actif [{gauche}..{droite}]")

    cellules = []
    for indice in range(max(0, gauche), min(droite, len(valeurs) - 1) + 1):
        classe = "partition-inconnu"
        role = "à examiner"
        if any(debut <= indice <= fin for debut, fin, _ in zones_finales):
            role = next(role for debut, fin, role in zones_finales if debut <= indice <= fin)
            classe = {
                "gauche": "partition-moins",
                "pivot": "partition-egal",
                "droite": "partition-plus",
            }[role]
        elif partition is not None:
            moins, courant, plus = partition
            if indice < moins:
                role, classe = "< pivot", "partition-moins"
            elif indice < courant:
                role, classe = "= pivot", "partition-egal"
            elif indice > plus:
                role, classe = "> pivot", "partition-plus"

        if etape["action"] == "echange" and indice in indices:
            role, classe = "échangé", "partition-echange"
        elif (
            etape["action"] == "comparaison"
            and indice == details.get("pivot_index")
        ):
            role, classe = "pivot", "partition-pivot"
        elif etape["action"] == "comparaison" and indice in indices:
            role, classe = "comparé", "partition-compare"
        elif indice == details.get("pivot_index"):
            role, classe = "pivot", "partition-pivot"

        cellules.append(
            f'<div class="partition-cell {classe}"><small>{indice} · {role}</small>'
            f"<strong>{valeurs[indice]}</strong></div>"
        )

    st.markdown(
        f'<div class="partition-visualisation">{"".join(cellules)}</div>',
        unsafe_allow_html=True,
    )
    if partition is not None:
        moins, courant, plus = partition
        st.caption(
            f"< pivot : [{gauche}..{moins - 1}] · = pivot : [{moins}..{courant - 1}] · "
            f"à examiner : [{courant}..{plus}] · > pivot : [{plus + 1}..{droite}]"
        )
    elif zones_finales:
        st.caption("La partition est terminée; les zones inférieure, égale et supérieure sont fixées.")


def afficher_arbre_tas(etape):
    valeurs = etape["liste"]
    details = etape["details"]
    taille_tas = 0 if etape["action"] == "fin" else details.get(
        "heap_size", len(valeurs)
    )
    indices_actifs = etape["indices"] or ()
    if taille_tas == 0:
        st.caption("Le tas actif est vide; toutes les valeurs sont placées.")
        return
    if taille_tas > 31:
        st.caption(
            f"Tas de {taille_tas} nœuds : l'arbre complet serait trop dense; "
            "les liens parent/enfants sont listés par indice."
        )
        st.dataframe(
            [
                {
                    "Indice": indice,
                    "Valeur": valeurs[indice],
                    "Parent": None if indice == 0 else (indice - 1) // 2,
                    "Enfants": ", ".join(
                        str(enfant)
                        for enfant in (2 * indice + 1, 2 * indice + 2)
                        if enfant < taille_tas
                    ) or "aucun",
                }
                for indice in range(taille_tas)
            ],
            width="stretch",
            height=260,
            hide_index=True,
            key="tas_indices_larges",
        )
        return

    positions = {}
    for indice in range(taille_tas):
        niveau = (indice + 1).bit_length() - 1
        debut_niveau = (1 << niveau) - 1
        position_niveau = indice - debut_niveau
        largeur_niveau = 1 << niveau
        positions[indice] = (
            2 * (position_niveau + 0.5) / largeur_niveau - 1,
            -niveau,
        )

    lignes_x = []
    lignes_y = []
    for indice in range(1, taille_tas):
        parent = (indice - 1) // 2
        lignes_x.extend((positions[parent][0], positions[indice][0], None))
        lignes_y.extend((positions[parent][1], positions[indice][1], None))

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=lignes_x,
        y=lignes_y,
        mode="lines",
        line=dict(color="rgba(148, 163, 184, 0.55)", width=2),
        hoverinfo="skip",
        showlegend=False,
    ))
    action = etape["action"]
    racine_valide = details.get("heap_valid", taille_tas <= 1)
    couleurs = []
    for indice in range(taille_tas):
        if action == "echange" and indice in indices_actifs:
            couleurs.append("#EF4444")
        elif action == "comparaison" and indice in indices_actifs:
            couleurs.append("#F59E0B")
        elif indice == 0:
            couleurs.append("#38BDF8")
        else:
            couleurs.append("#8B5CF6")
    figure.add_trace(go.Scatter(
        x=[positions[indice][0] for indice in range(taille_tas)],
        y=[positions[indice][1] for indice in range(taille_tas)],
        mode="markers+text",
        text=[f"{valeurs[indice]}<br>{indice}" for indice in range(taille_tas)],
        textposition="middle center",
        marker=dict(
            size=38,
            color=couleurs,
            line=dict(color="#C4B5FD", width=1),
        ),
        customdata=list(range(taille_tas)),
        hovertemplate="Indice : %{customdata}<br>Valeur : %{text}<extra></extra>",
        showlegend=False,
    ))
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#111827",
        font=dict(color="#E2E8F0", size=12),
        margin=dict(l=10, r=10, t=10, b=10),
        height=max(220, min(420, 120 + (taille_tas.bit_length() - 1) * 70)),
        xaxis=dict(visible=False, range=[-1.1, 1.1]),
        yaxis=dict(visible=False, autorange=True),
    )
    st.plotly_chart(figure, width="stretch", key="arbre_tas_tri")
    if racine_valide:
        st.caption(f"Max-heap valide · racine {valeurs[0]} = maximum de la zone active")
    else:
        st.caption(f"Racine courante : {valeurs[0]} · propriété du max-heap en cours de rétablissement")


def afficher_vue_tas(etape):
    valeurs = etape["liste"]
    details = etape["details"]
    taille_tas = 0 if etape["action"] == "fin" else details.get(
        "heap_size", len(valeurs)
    )
    indices_actifs = etape["indices"] or ()
    cellules = []
    for indice, valeur in enumerate(valeurs):
        if etape["action"] == "echange" and indice in indices_actifs:
            classe = "tas-echange"
            statut = "échange"
        elif etape["action"] == "comparaison" and indice in indices_actifs:
            classe = "tas-comparaison"
            statut = "comparé"
        elif indice == 0 and details.get("heap_valid"):
            classe = "tas-racine"
            statut = "maximum"
        elif indice < taille_tas:
            classe = "tas-actif"
            statut = "tas actif"
        else:
            classe = "tas-place"
            statut = "trié"
        cellules.append(
            f'<div class="tas-cell {classe}"><small>{indice} · {statut}</small>'
            f"<strong>{valeur}</strong></div>"
        )
    st.markdown("#### Tableau et zone active")
    st.markdown(
        f'<div class="tas-visualisation">{"".join(cellules)}</div>',
        unsafe_allow_html=True,
    )
    if taille_tas < len(valeurs):
        st.caption(
            f"Tas actif : indices 0 à {taille_tas - 1} · "
            f"suffixe trié : indices {taille_tas} à {len(valeurs) - 1}"
        )


def afficher_pseudocode(nom, etape, mode):
    st.markdown("#### Pseudo-code synchronisé")
    ligne_active = etape["ligne_pseudocode"]

    for numero, ligne in enumerate(PSEUDOCODES[nom], start=1):
        classe = "pseudo-code-ligne active" if numero == ligne_active else "pseudo-code-ligne"
        st.markdown(
            f'<div class="{classe}"><span>{numero:02}</span><code>{ligne}</code></div>',
            unsafe_allow_html=True,
        )

    if mode == "Analyse":
        st.caption(
            f"Action : {etape['action']} · Ligne exécutée : {ligne_active} · "
            f"Indices : {etape['indices'] if etape['indices'] is not None else 'aucun'}"
        )
        details = etape["details"]
        if details.get("pivot_value") is not None:
            st.caption(
                f"Pivot : {details['pivot_value']} en position {details.get('pivot_index')}"
            )
        if details.get("heap_size") is not None:
            st.caption(f"Taille du tas actif : {details['heap_size']}")
        if details.get("tampon") is not None:
            st.caption(f"Tampon de fusion : {details['tampon']}")
        if details.get("tampon_gauche") is not None:
            st.caption(
                f"Sous-tableaux sources : gauche {details['tampon_gauche']} · "
                f"droite {details['tampon_droit']}"
            )



def creer_liste(mode, saisie, taille, minimum, maximum):
    if mode == "Liste personnalisée":
        nombres = lire_liste(saisie)
    else:
        if minimum > maximum:
            raise ValueError(
                "La valeur minimale doit être inférieure au maximum."
            )

        nombres = [
            random.randint(minimum, maximum)
            for _ in range(taille)
        ]

    if not nombres:
        raise ValueError("La liste doit contenir au moins un nombre.")

    if len(nombres) > 50:
        raise ValueError(
            "Limite la liste à 50 nombres pour la visualisation."
        )

    return nombres


def _minimum_mesure(resultats, colonne):
    valeurs = [
        (ligne["Algorithme"], ligne[colonne])
        for ligne in resultats
        if isinstance(ligne.get(colonne), (int, float))
    ]
    if len(valeurs) < 2:
        return None, []

    minimum = min(valeur for _, valeur in valeurs)
    gagnants = [nom for nom, valeur in valeurs if valeur == minimum]
    return minimum, gagnants


def afficher_resume_comparaison(resultats):
    st.subheader("Synthèse de l’entrée commune")
    colonnes_resume = st.columns(4)
    indicateurs = [
        ("Temps médian le plus bas", "Temps médian (ms)", "ms"),
        ("Moins de comparaisons", "Comparaisons", ""),
        ("Moins d'échanges", "Échanges", ""),
        ("Moins d'opérations", "Opérations", ""),
    ]
    for colonne_ui, (titre, cle, unite) in zip(colonnes_resume, indicateurs):
        minimum, gagnants = _minimum_mesure(resultats, cle)
        with colonne_ui:
            if minimum is None:
                st.metric(titre, "Non comparable")
                st.caption("Deux mesures numériques au moins sont nécessaires.")
                continue

            valeur = f"{minimum:.4f} ms" if unite else f"{minimum:,}"
            st.metric(titre, valeur)
            st.caption("Minimum observé · " + ", ".join(gagnants))

    st.caption(
        "Le temps est la médiane expérimentale du tri seul. Ces minima décrivent "
        "cette entrée commune; ils ne désignent pas un meilleur algorithme en général."
    )


def afficher_resultats_comparaison(resultats, evolution):
    if not resultats:
        st.info("Aucun résultat à afficher. Lance une comparaison pour commencer.")
        return

    afficher_resume_comparaison(resultats)
    st.subheader("Tableau comparatif")
    st.caption(
        "Compteurs issus des statistiques des algorithmes; temps = médiane "
        "des répétitions, tri seul."
    )

    st.dataframe(
        resultats,
        width="stretch",
        height=310,
        hide_index=True,
        column_config={
            "Algorithme": st.column_config.TextColumn("Algorithme", width="medium"),
            "Distribution": st.column_config.TextColumn("Données", width="small"),
            "Taille": st.column_config.NumberColumn("n", width="small"),
            "Graine": st.column_config.NumberColumn("Graine", width="small"),
            "Répétitions": st.column_config.NumberColumn("Rép.", width="small"),
            "Nom anglais": st.column_config.TextColumn("Nom anglais", width="medium"),
            "Comparaisons": st.column_config.NumberColumn("Compar.", width="small"),
            "Échanges": st.column_config.NumberColumn("Échanges", width="small"),
            "Déplacements": st.column_config.NumberColumn("Dépl.", width="small"),
            "Opérations": st.column_config.NumberColumn("Opér.", width="small"),
            "Temps médian (ms)": st.column_config.NumberColumn(
                "Temps méd. (ms)", format="%.4f", width="small"
            ),
            "Résultat correct": st.column_config.CheckboxColumn("Tri correct", width="small"),
        },
    )
    afficher_definitions_compteurs()

    st.subheader("Opérations sur l’entrée commune")
    st.caption(
        "Comparaisons, échanges, déplacements et opérations (échanges + déplacements) "
        "pour l'entrée mesurée."
    )
    graphiques_compteurs = [
        ("Comparaisons", "Comparaisons entre valeurs"),
        ("Échanges", "Permutations de deux cases"),
        ("Déplacements", "Décalages et écritures"),
        ("Opérations", "Échanges + déplacements"),
    ]
    colonnes_compteurs = st.columns(2)
    for index, (cle, titre) in enumerate(graphiques_compteurs):
        with colonnes_compteurs[index % 2]:
            st.markdown(f"#### {titre}")
            figure = go.Figure(
                data=[
                    go.Bar(
                        x=[ligne[cle] for ligne in resultats],
                        y=[ligne["Algorithme"] for ligne in resultats],
                        orientation="h",
                        text=[ligne[cle] for ligne in resultats],
                        textposition="outside",
                        marker_color=COULEURS_GRAPHIQUES,
                        cliponaxis=False,
                    )
                ]
            )
            styliser_figure(figure, hauteur=330)
            figure.update_layout(
                xaxis_title=titre,
                yaxis_title=None,
                showlegend=False,
                bargap=0.34,
                margin=dict(l=145, r=40, t=18, b=42),
            )
            figure.update_yaxes(autorange="reversed")
            st.plotly_chart(figure, width="stretch")

    st.subheader("Évolution avec la taille du tableau")
    st.caption(
        "Les courbes montrent comment les compteurs augmentent lorsque la taille "
        "du tableau grandit."
    )
    if not evolution:
        st.info("L'évolution ne peut pas être tracée : aucune mesure par taille n'est disponible.")
    else:
        colonnes_evolution = st.columns(2)
        for index, (cle, titre) in enumerate([
            ("Comparaisons", "Nombre de comparaisons"),
            ("Opérations", "Échanges + déplacements"),
        ]):
            figure = go.Figure()
            for couleur, nom in zip(COULEURS_GRAPHIQUES, ALGORITHMES):
                lignes = [
                    ligne for ligne in evolution
                    if ligne["Algorithme"] == nom
                ]
                if lignes:
                    figure.add_trace(
                        go.Scatter(
                            x=[ligne["Taille"] for ligne in lignes],
                            y=[ligne[cle] for ligne in lignes],
                            mode="lines+markers",
                            name=nom,
                            line=dict(color=couleur),
                            marker=dict(size=5),
                        )
                    )
            styliser_figure(figure, hauteur=390)
            figure.update_layout(
                xaxis_title="Taille du tableau",
                yaxis_title=titre,
                hovermode="x unified",
                legend_title="Algorithme",
                legend=dict(
                    orientation="h",
                    y=-0.32,
                    x=0,
                    yanchor="top",
                    font=dict(size=10),
                    entrywidth=108,
                    entrywidthmode="pixels",
                ),
                margin=dict(l=12, r=12, t=20, b=126),
            )
            with colonnes_evolution[index]:
                st.markdown(f"#### {titre}")
                if figure.data:
                    st.plotly_chart(figure, width="stretch")
                else:
                    st.info("Aucune courbe disponible pour ce compteur.")

def afficher_temps_comparaison(resultats, repetitions):
    st.subheader("Temps d'exécution mesuré")
    st.caption(
        f"Médiane de {repetitions} répétitions du tri seul, hors génération, copie "
        "et animation. Les durées dépendent de l'environnement d'exécution."
    )
    temps = [
        ligne for ligne in resultats
        if isinstance(ligne.get("Temps médian (ms)"), (int, float))
    ]
    if not temps:
        st.info("Aucun temps mesuré ne permet de produire ce graphique.")
        return

    figure = go.Figure(
        data=[
            go.Bar(
                    x=[ligne["Temps médian (ms)"] for ligne in temps],
                    y=[ligne["Algorithme"] for ligne in temps],
                    orientation="h",
                text=[ligne["Temps médian (ms)"] for ligne in temps],
                textposition="outside",
                marker_color=COULEURS_GRAPHIQUES[:len(temps)],
                cliponaxis=False,
            )
        ]
    )
    styliser_figure(figure, hauteur=315)
    figure.update_layout(
        xaxis_title="Temps médian (ms)",
        yaxis_title=None,
        showlegend=False,
        bargap=0.34,
        margin=dict(l=145, r=40, t=18, b=42),
    )
    figure.update_yaxes(autorange="reversed")
    st.plotly_chart(figure, width="stretch")


def afficher_complexites_theoriques():
    st.subheader("Complexités théoriques")
    st.caption(
        "Ordres de grandeur asymptotiques, distincts des temps mesurés et des "
        "compteurs observés. Le meilleur, le moyen et le pire cas dépendent de "
        "l'algorithme et de l'ordre initial."
    )
    st.dataframe(
        [
            {
                "Algorithme": nom,
                "Meilleur cas": informations["meilleur"],
                "Cas moyen": informations["moyen"],
                "Pire cas": informations["pire"],
                "Mémoire": informations["memoire"],
            }
            for nom, informations in INFORMATIONS_ALGORITHMES.items()
        ],
        width="stretch",
        hide_index=True,
    )


def _calculer_resultats_comparaison(type_donnees, taille, graine, repetitions):
    nombres = generer_donnees(type_donnees, taille, int(graine))
    pas = max(1, taille // 20)
    tailles = sorted(set(range(pas, taille + 1, pas)) | {taille})
    evolution = []
    resultats_par_algorithme = {}

    for taille_courante in tailles:
        liste_test = (
            nombres
            if taille_courante == taille
            else generer_donnees(type_donnees, taille_courante, int(graine))
        )
        for nom in ALGORITHMES:
            statistiques = calculer_statistiques(nom, liste_test)
            ligne = {
                "Taille": taille_courante,
                "Distribution": type_donnees,
                "Graine": int(graine),
                "Répétitions": int(repetitions),
                "Algorithme": nom,
                "Comparaisons": statistiques["comparaisons"],
                "Échanges": statistiques["echanges"],
                "Déplacements": statistiques["deplacements"],
                "Opérations": statistiques["operations"],
            }
            evolution.append(ligne)
            if taille_courante == taille:
                resultats_par_algorithme[nom] = statistiques

    lignes = []
    for nom in ALGORITHMES:
        statistiques = resultats_par_algorithme[nom]
        lignes.append({
            "Algorithme": nom,
            "Distribution": type_donnees,
            "Taille": taille,
            "Graine": int(graine),
            "Répétitions": int(repetitions),
            "Nom anglais": INFORMATIONS_ALGORITHMES[nom]["anglais"],
            "Comparaisons": statistiques["comparaisons"],
            "Échanges": statistiques["echanges"],
            "Déplacements": statistiques["deplacements"],
            "Opérations": statistiques["operations"],
            "Temps médian (ms)": round(
                mesurer_tri_mediane(
                    TRIS_RAPIDES[nom], nombres, repetitions=int(repetitions)
                ),
                4,
            ),
            "Résultat correct": statistiques["liste"] == sorted(nombres),
        })

    return lignes, evolution, nombres


def _valeur_analyse(valeur):
    if isinstance(valeur, float):
        return f"{valeur:.4f}" if valeur < 1 else f"{valeur:.2f}"
    return str(valeur)


def _details_analyse(criteres):
    lignes = []
    for resultat in criteres.values():
        if not resultat["disponible"]:
            continue
        for detail in resultat["details"]:
            lignes.append({
                "Mesure": resultat["cle"],
                "Algorithme / distribution": detail["algorithme"],
                "Valeur": detail["valeur"],
                "Écart au minimum": detail["ecart_absolu"],
                "Écart au minimum (%)": (
                    round(detail["ecart_pourcent"], 2)
                    if detail["ecart_pourcent"] is not None
                    else "Non calculable (référence nulle)"
                ),
            })
    return lignes


def afficher_analyse_automatique(resultats):
    analyses = analyser_mesures(resultats)
    st.markdown("#### Analyse automatique")
    if not analyses:
        st.info("Aucune mesure disponible pour cette analyse.")
        return

    for analyse in analyses:
        criteres = analyse["criteres"]
        st.markdown(
            f"**Synthèse — {analyse['distribution']}, "
            f"{analyse['taille']} éléments**"
        )
        for cle, resultat in criteres.items():
            if not resultat["disponible"]:
                st.write(f"{cle} : {resultat['raison']}")
                continue
            gagnants = resultat["gagnants"]
            if len(gagnants) == 1:
                resume = f"{gagnants[0]} ({_valeur_analyse(resultat['minimum'])})"
            else:
                resume = (
                    f"égalité entre {', '.join(gagnants)} "
                    f"({_valeur_analyse(resultat['minimum'])})"
                )
            st.write(f"**Minimum de {resultat['libelle']} :** {resume}.")
            if resultat["nombre_disponible"] < resultat["nombre_total"]:
                st.caption(
                    f"Mesure disponible pour {resultat['nombre_disponible']} "
                    f"algorithme(s) sur {resultat['nombre_total']} ; les valeurs "
                    "absentes ne sont pas assimilées à zéro."
                )

        with st.expander("Détails et interprétation"):
            st.markdown("**Ce que les mesures montrent**")
            st.caption(
                "Les écarts sont calculés par rapport au minimum de chaque "
                "critère, dans cette distribution et à cette taille."
            )
            details = _details_analyse(criteres)
            if details:
                st.dataframe(details, width="stretch", hide_index=True)
            else:
                st.write("Aucun compteur comparable n'est disponible.")

            st.markdown("**Ce que la théorie permet d'expliquer**")
            distribution = analyse["distribution"]
            insertion = criteres.get("Comparaisons") or criteres.get("Opérations")
            if (
                distribution == "Presque triées"
                and insertion
                and insertion["disponible"]
                and "Tri par insertion" in insertion["gagnants"]
            ):
                st.write(
                    "Ici, le tri par insertion minimise ce compteur sur des données "
                    "presque triées. Cela concorde avec son comportement sensible "
                    "à l'ordre initial : il déplace peu d'éléments quand ils sont "
                    "déjà proches de leur place."
                )
            comparaisons = criteres.get("Comparaisons")
            temps = criteres.get("Temps médian (ms)")
            if (
                comparaisons and temps
                and comparaisons["disponible"] and temps["disponible"]
                and set(comparaisons["gagnants"]) != set(temps["gagnants"])
            ):
                st.write(
                    "Le minimum de comparaisons et le minimum de temps ne sont pas "
                    "obtenus par le même algorithme. Le chronomètre inclut aussi "
                    "les autres opérations et le coût propre de l'implémentation."
                )
            quadratiques = {"Tri à bulles", "Tri par sélection", "Tri par insertion"}
            nlogn = {"Tri fusion", "Tri rapide", "Tri par tas"}
            operations = criteres.get("Opérations") or criteres.get("Total des compteurs")
            valeurs = {
                detail["algorithme"]: detail["valeur"]
                for detail in operations.get("details", [])
            } if operations and operations["disponible"] else {}
            reference_nlogn = [valeurs[nom] for nom in nlogn if nom in valeurs]
            ecart_quadratique_observe = (
                analyse["taille"] >= 50 and reference_nlogn
                and any(valeurs[nom] >= 2 * min(reference_nlogn)
                        for nom in quadratiques if nom in valeurs)
            )
            if ecart_quadratique_observe:
                st.write(
                    "L'écart observé entre un tri quadratique et un tri en "
                    "O(n log n) est cohérent avec leurs ordres de croissance "
                    "théoriques sur ces entrées; cet échantillon ne démontre pas "
                    "à lui seul ces complexités."
                )
            insertion_presque_triee_observe = (
                distribution == "Presque triées"
                and insertion is not None
                and insertion["disponible"]
                and "Tri par insertion" in insertion["gagnants"]
            )
            divergence_temps_observee = (
                comparaisons is not None and temps is not None
                and comparaisons["disponible"] and temps["disponible"]
                and set(comparaisons["gagnants"]) != set(temps["gagnants"])
            )
            if not any((insertion_presque_triee_observe,
                        divergence_temps_observee, ecart_quadratique_observe)):
                st.write(
                    "Les mesures disponibles ne déclenchent pas ici d'explication "
                    "théorique spécifique."
                )

            st.markdown("**Ce que l'expérience ne permet pas de conclure**")
            st.write(
                "Ce résultat décrit uniquement les algorithmes exécutés, cette "
                "distribution et cette taille. Il ne désigne pas un meilleur tri "
                "dans l'absolu et ne constitue pas une preuve de complexité."
            )


def afficher_differences_distributions(resultats, taille):
    lignes_taille = [ligne for ligne in resultats if ligne["Taille"] == taille]
    differences = analyser_differences_distributions(lignes_taille)
    st.markdown("#### Différences observées entre distributions")
    if not differences:
        st.info(
            "Une seule distribution a été mesurée pour cette taille ; "
            "aucun écart entre distributions ne peut être établi."
        )
        return

    st.caption(
        f"Comparaison à taille {taille}, algorithme et graine identiques. "
        "Les pourcentages prennent pour référence le minimum observé entre "
        "les distributions pour chaque critère."
    )
    for difference in differences:
        st.markdown(f"**{difference['algorithme']}**")
        details = _details_analyse(difference["criteres"])
        if details:
            st.dataframe(details, width="stretch", hide_index=True)

    st.markdown("**Ce que la théorie permet d'expliquer**")
    insertion = next(
        (difference for difference in differences
         if difference["algorithme"] == "Tri par insertion"),
        None,
    )
    if insertion:
        for cle in ("Comparaisons", "Autres opérations", "Total des compteurs"):
            critere = insertion["criteres"].get(cle)
            if not critere or not critere["disponible"]:
                continue
            valeurs = {detail["algorithme"]: detail["valeur"] for detail in critere["details"]}
            if (
                "Presque triées" in valeurs and "Aléatoires" in valeurs
                and valeurs["Presque triées"] < valeurs["Aléatoires"]
            ):
                st.write(
                    "Pour le tri par insertion, le compteur choisi est plus faible "
                    "sur les données presque triées que sur les aléatoires. C'est "
                    "compatible avec un coût qui dépend de l'ordre initial."
                )
                break
    if not insertion or not any(
        critere.get("disponible")
        and {detail["algorithme"] for detail in critere["details"]}
        >= {"Presque triées", "Aléatoires"}
        and next(
            detail["valeur"] for detail in critere["details"]
            if detail["algorithme"] == "Presque triées"
        ) < next(
            detail["valeur"] for detail in critere["details"]
            if detail["algorithme"] == "Aléatoires"
        )
        for critere in insertion["criteres"].values()
    ):
        st.write(
            "Les mesures ne font pas apparaître ici de contraste qui justifie "
            "une explication théorique plus précise."
        )
    st.markdown("**Ce que l'expérience ne permet pas de conclure**")
    st.write(
        "Ces observations ne couvrent que les distributions, tailles et graines "
        "mesurées. Elles ne prouvent pas un comportement général et ne permettent "
        "pas de comparer les durées entre des entrées différentes."
    )


def mesurer_tri(fonction, nombres):
    """Mesure le temps de tri, sans construire l'historique visuel."""
    liste = nombres.copy()

    debut = time.perf_counter()
    fonction(liste)
    return (time.perf_counter() - debut) * 1000


def tri_bulles_simple(liste):
    for i in range(len(liste)):
        echange = False

        for j in range(len(liste) - i - 1):
            if liste[j] > liste[j + 1]:
                liste[j], liste[j + 1] = liste[j + 1], liste[j]
                echange = True

        if not echange:
            break


def tri_selection_simple(liste):
    for i in range(len(liste) - 1):
        indice_min = i

        for j in range(i + 1, len(liste)):
            if liste[j] < liste[indice_min]:
                indice_min = j

        if indice_min != i:
            liste[i], liste[indice_min] = liste[indice_min], liste[i]


def tri_insertion_simple(liste):
    for i in range(1, len(liste)):
        valeur = liste[i]
        j = i - 1

        while j >= 0 and liste[j] > valeur:
            liste[j + 1] = liste[j]
            j -= 1

        liste[j + 1] = valeur


def tri_fusion_simple(liste):
    def fusionner(partie):
        if len(partie) < 2:
            return partie
        milieu = len(partie) // 2
        gauche = fusionner(partie[:milieu])
        droite = fusionner(partie[milieu:])
        fusion = []
        indice_gauche = indice_droit = 0
        while indice_gauche < len(gauche) and indice_droit < len(droite):
            if gauche[indice_gauche] <= droite[indice_droit]:
                fusion.append(gauche[indice_gauche])
                indice_gauche += 1
            else:
                fusion.append(droite[indice_droit])
                indice_droit += 1
        fusion.extend(gauche[indice_gauche:])
        fusion.extend(droite[indice_droit:])
        return fusion

    liste[:] = fusionner(liste)


def tri_rapide_simple(liste):
    def partitionner(gauche, droite):
        if gauche >= droite:
            return
        pivot = liste[(gauche + droite) // 2]
        moins = courant = gauche
        plus = droite
        while courant <= plus:
            if liste[courant] < pivot:
                if courant != moins:
                    liste[courant], liste[moins] = liste[moins], liste[courant]
                moins += 1
                courant += 1
            elif liste[courant] > pivot:
                if courant != plus:
                    liste[courant], liste[plus] = liste[plus], liste[courant]
                plus -= 1
            else:
                courant += 1
        partitionner(gauche, moins - 1)
        partitionner(plus + 1, droite)

    partitionner(0, len(liste) - 1)


def tri_tas_simple(liste):
    def tamiser(racine, taille_tas):
        while True:
            plus_grand = racine
            enfant_gauche = 2 * racine + 1
            enfant_droit = enfant_gauche + 1
            if enfant_gauche < taille_tas and liste[enfant_gauche] > liste[plus_grand]:
                plus_grand = enfant_gauche
            if enfant_droit < taille_tas and liste[enfant_droit] > liste[plus_grand]:
                plus_grand = enfant_droit
            if plus_grand == racine:
                return
            liste[racine], liste[plus_grand] = liste[plus_grand], liste[racine]
            racine = plus_grand

    taille_tas = len(liste)
    for parent in range(taille_tas // 2 - 1, -1, -1):
        tamiser(parent, taille_tas)
    for fin in range(taille_tas - 1, 0, -1):
        liste[0], liste[fin] = liste[fin], liste[0]
        tamiser(0, fin)


TRIS_RAPIDES = {
    "Tri à bulles": tri_bulles_simple,
    "Tri par sélection": tri_selection_simple,
    "Tri par insertion": tri_insertion_simple,
    "Tri fusion": tri_fusion_simple,
    "Tri rapide": tri_rapide_simple,
    "Tri par tas": tri_tas_simple,
}


def afficher_visualisation_exercice(question, mode, correction=False):
    historique = question["historique"]
    if question["type"] == "prediction":
        cle = "index_suivant" if correction else "index_courant"
        index_etape = question[cle]
    elif question["type"] == "etat":
        index_etape = question["index_etape"]
    elif question["type"] == "ordre" and correction:
        index_etape = question["indices_evenements"][-1]
    else:
        index_etape = 0

    etape = historique[index_etape]
    if question["type"] == "etat" and not correction:
        etape = {**etape, "liste": question["avant"]}
    with st.container(key="exercices_trace"):
        titre = "Étape révélée" if correction else "État à analyser"
        st.markdown(f"#### {titre}")
        if question["type"] == "prediction" and correction:
            avant, apres = st.columns(2)
            avant.caption(f"État avant : {historique[question['index_courant']]['liste']}")
            apres.caption(f"État après : {etape['liste']}")
        elif question["type"] == "etat":
            avant, apres = st.columns(2)
            avant.caption(f"État avant : {question['avant']}")
            if correction:
                apres.caption(f"État après : {question['apres']}")
            else:
                apres.caption("État après : à déterminer")

        graphique, pseudo = st.columns([2, 1])
        with graphique:
            afficher_barres(
                etape,
                est_final=(etape["action"] == "fin"),
                nom_algorithme=question["nom_algorithme"],
            )
            afficher_legende_tableau()
            if question["nom_algorithme"] == "Tri fusion":
                afficher_vue_fusion(etape)
            elif question["nom_algorithme"] == "Tri rapide":
                afficher_vue_rapide(etape)
            elif question["nom_algorithme"] == "Tri par tas":
                with st.expander("Arbre binaire du max-heap", expanded=True):
                    afficher_arbre_tas(etape)
                    afficher_vue_tas(etape)
        with pseudo:
            with st.container(border=True):
                afficher_pseudocode(question["nom_algorithme"], etape, mode)

    return etape


def afficher_bilan_exercices(session):
    stats = statistiques_session(session)
    st.header("Bilan de la session")
    st.caption(f"Niveau : {session['difficulte']} · Algorithme : {session['algorithme_choisi']}")
    colonnes = st.columns(5)
    colonnes[0].metric("Score", f"{stats['score']} pts")
    colonnes[1].metric("Questions réussies", f"{stats['reussies']} / {stats['terminees']}")
    colonnes[2].metric("Réussies du premier coup", stats["premier_essai"])
    colonnes[3].metric("Taux de réussite", f"{stats['pourcentage']} %")
    colonnes[4].metric("Indices utilisés", stats["indices"])

    resultats_types = []
    for type_question, libelle in (
        ("prediction", "Prédiction"),
        ("ordre", "Ordre des étapes"),
        ("comprehension", "Compréhension"),
    ):
        groupe = [q for q in session["questions"] if q["type"] == type_question]
        resolues = [q for q in groupe if q["resolue"]]
        if resolues:
            resultats_types.append({
                "Type": libelle,
                "Réussies": sum(q["correcte"] for q in resolues),
                "Terminées": len(resolues),
            })
    if resultats_types:
        st.dataframe(resultats_types, width="stretch", hide_index=True)

    erreurs = sorted({
        q["nom_algorithme"]
        for q in session["questions"]
        if q["resolue"] and not q["correcte"]
    })
    if erreurs:
        st.info("À retravailler : " + ", ".join(erreurs) + ". Rejoue ces tris dans Visualiser en observant les étapes concernées.")
    else:
        st.success("Aucune réponse finale incorrecte : tu peux augmenter la difficulté ou varier les algorithmes.")
    st.caption("Les succès, l'expérience et le niveau sont enregistrés dans le profil local.")
    for succes_id in session.get("progression_succes", ()):
        st.success(
            f"Succès débloqué · {SUCCES[succes_id]['nom']} "
            f"(+{SUCCES[succes_id]['xp']} XP)"
        )
    if st.button("Nouvelle session", type="primary", key="exercices_nouvelle_session_bilan"):
        st.session_state.pop("exercices_session", None)
        st.rerun()


def afficher_page_exercices():
    with st.container(key="exercices_page"):
        with st.container(key="exercices_intro"):
            st.markdown(
                '<p class="exercices-kicker">APPRENDRE EN PRATIQUANT</p>',
                unsafe_allow_html=True,
            )
            st.header("Exercices")
            st.write(
                "Observe une trace réelle, prédis l'étape suivante et comprends "
                "le raisonnement de chaque tri."
            )
        _afficher_contenu_page_exercices()


def _afficher_contenu_page_exercices():

    session = st.session_state.get("exercices_session")
    if session is None:
        recommandation = None
        if progression_store is not None:
            try:
                if progression_store.activity_history(profil_nom, limit=1):
                    recommandation = progression_store.parcours_pedagogique(
                        profil_nom
                    )["recommandation"]
            except (OSError, sqlite3.Error, ValueError):
                recommandation = None
        if recommandation and recommandation["page"] == "Exercices":
            with st.container(key="exercices_recommandation"):
                st.markdown("#### À reprendre ensuite")
                st.markdown(
                    f"**{recommandation['competence']}** · "
                    f"{recommandation['exercice']}"
                )
                st.caption(recommandation["raison"])
                st.button(
                    "Lancer cette recommandation",
                    key=f"exercices_recommandation_{profil_nom}",
                    on_click=ouvrir_recommandation,
                    args=(profil_nom, recommandation),
                )

        with st.container(key="exercices_configuration"):
            st.markdown("#### Choisir un exercice")
            st.caption("Définis le niveau, le tri à explorer et la durée de la session.")
            colonnes = st.columns(2)
            difficulte = colonnes[0].selectbox(
                "Difficulté", DIFFICULTES, key="exercice_difficulte"
            )
            choix_algorithmes = (
                TOUS_LES_ALGORITHMES, *algorithmes_disponibles(difficulte)
            )
            algorithme = colonnes[1].selectbox(
                "Algorithme",
                choix_algorithmes,
                key=f"exercice_algorithme_{difficulte}",
            )
            nombre_questions = st.slider(
                "Nombre de questions",
                min_value=3,
                max_value=10,
                value=6,
                key="exercice_nombre_questions",
            )
            lancer = st.button(
                "Lancer la session", type="primary", width="stretch"
            )
            st.caption(
                "Les réponses réussies peuvent rapporter de l'XP selon les règles "
                "du profil; consulter un exercice ne rapporte rien."
            )
        if lancer:
            session = creer_session(
                algorithme, difficulte, int(nombre_questions)
            )
            session["profil_nom"] = profil_nom
            st.session_state["exercices_session"] = session
            st.rerun()
        return

    if st.button("Nouvelle session", key=f"exercices_nouvelle_{session['id']}"):
        st.session_state.pop("exercices_session", None)
        st.rerun()

    stats = statistiques_session(session)
    total = len(session["questions"])
    with st.container(key="exercices_progression"):
        st.caption("SESSION EN COURS")
        st.progress(stats["terminees"] / total)
        compteurs = st.columns(4)
        compteurs[0].metric("Questions traitées", f"{stats['terminees']} / {total}")
        compteurs[1].metric("Bonnes réponses", stats["reussies"])
        compteurs[2].metric("Score de session", f"{stats['score']} pts")
        compteurs[3].metric("Indices utilisés", stats["indices"])
        st.caption("Ces chiffres concernent cette session; l'historique du profil est dans Profil.")
    mode = st.radio(
        "Mode pédagogique",
        ("Découverte", "Analyse"),
        horizontal=True,
        key="mode_pedagogique_exercices",
    )

    if session["terminee"]:
        afficher_bilan_exercices(session)
        return

    index_question = session["index_question"]
    question = session["questions"][index_question]
    st.markdown(
        f"### Question {index_question + 1} sur {total} · "
        f"{question['nom_algorithme']}"
    )
    st.caption(
        f"{session['difficulte']} · {question['type'].capitalize()} · "
        f"Données : {question['entree']}"
    )
    with st.container(key="exercices_enonce"):
        st.caption("À résoudre")
        st.markdown(f"#### {question['prompt']}")
    afficher_visualisation_exercice(question, mode, correction=question["resolue"])

    statut = None
    if not question["resolue"]:
        indices_session = sum(
            item["indices_utilises"] for item in session["questions"]
        )
        if question["indices_utilises"]:
            st.info("Indice : " + question["indice"])
        elif session["difficulte"] == "Avancé" and indices_session >= 1:
            st.caption("L'indice unique du niveau avancé a déjà été utilisé dans cette session.")
        elif st.button("Afficher un indice", key=f"indice_{session['id']}_{index_question}"):
            utiliser_indice(question)
            st.session_state["exercices_session"] = session
            st.rerun()

    afficher_suite_question_exercice(session, question, index_question, total, statut)


def afficher_bilan_entrainement(session):
    stats = statistiques_session_entrainement(session)
    with st.container(key="entrainement_bilan"):
        st.subheader("Bilan de la session")
        colonnes = st.columns(4)
        colonnes[0].metric("Réponses correctes", f"{stats['reussies']} / {session['nombre_questions']}")
        colonnes[1].metric("Erreurs", stats["terminees"] - stats["reussies"])
        colonnes[2].metric("Score", f"{stats['score']} pts")
        colonnes[3].metric("Taux de réussite", f"{stats['pourcentage']} %")
        if stats["notions_a_retravailler"]:
            st.info(
                "Notions rencontrées avec une réponse incorrecte : "
                + " · ".join(stats["notions_a_retravailler"])
            )
        else:
            st.success("Aucune erreur enregistrée au cours de cette session.")
            st.caption("Ce bilan décrit cette session et ne suffit pas à déclarer une notion maîtrisée durablement.")
        for succes_id in session.get("progression_succes", ()):
            st.success(
                f"Succès débloqué · {SUCCES[succes_id]['nom']} "
                f"(+{SUCCES[succes_id]['xp']} XP)"
            )
        st.caption("Les réponses finalisées sont enregistrées dans le profil de départ; chaque question ne peut être récompensée qu'une fois.")
        if st.button("Nouvelle session", type="primary", key=f"entrainement_nouveau_bilan_{session['id']}"):
            st.session_state.pop("entrainement_session", None)
            st.rerun()


def afficher_page_entrainement():
    with st.container(key="entrainement_page"):
        with st.container(key="entrainement_intro"):
            st.markdown(
                '<p class="entrainement-kicker">APPRENDRE EN SITUATION</p>',
                unsafe_allow_html=True,
            )
            st.header("Entraînement")
            st.write(
                "Prédire les étapes d’un tri et choisir un algorithme adapté, "
                "avec une correction après chaque réponse."
            )
        _afficher_contenu_page_entrainement()


def _afficher_contenu_page_entrainement():
    session = st.session_state.get("entrainement_session")
    if session is None:
        with st.container(key="entrainement_configuration"):
            st.markdown("#### Préparer une session")
            st.caption(
                "Session adaptative : une bonne réponse alterne les formats; "
                "une erreur propose une nouvelle question du même format."
            )
            st.markdown("**Formats de question**")
            formats = st.columns(2)
            formats[0].markdown("**Prédiction**")
            formats[0].caption("Prévoir l’état du tableau après une mutation réelle du tri.")
            formats[1].markdown("**Choix d’algorithme**")
            formats[1].caption("Associer des contraintes de stabilité, mémoire et complexité à un tri.")
            colonnes_configuration = st.columns(2)
            difficulte = colonnes_configuration[0].selectbox(
                "Niveau", DIFFICULTES_ENTRAINEMENT, key="entrainement_difficulte"
            )
            nombre_questions = colonnes_configuration[1].slider(
                "Questions", min_value=3, max_value=8,
                value=TAILLE_SESSION_ENTRAINEMENT,
                key="entrainement_nombre_questions",
            )
            lancer = st.button("Lancer l'entraînement", type="primary", width="stretch")
            st.caption(
                "Seules les réponses validées sont enregistrées. Une consultation "
                "ou une session quittée avant validation ne rapporte pas d’XP."
            )
        if lancer:
            session = creer_session_entrainement(
                difficulte, int(nombre_questions)
            )
            session["profil_nom"] = profil_nom
            st.session_state["entrainement_session"] = session
            st.rerun()
        return

    if st.button("Nouvelle session", key=f"entrainement_nouveau_{session['id']}"):
        st.session_state.pop("entrainement_session", None)
        st.rerun()

    stats = statistiques_session_entrainement(session)
    total = session["nombre_questions"]
    index_question = session["index_question"]
    with st.container(key="entrainement_progression"):
        st.caption("SESSION EN COURS")
        st.progress(stats["terminees"] / total)
        colonnes = st.columns(4)
        colonnes[0].metric("Question", f"{index_question + 1} / {total}")
        colonnes[1].metric("Bonnes réponses", stats["reussies"])
        colonnes[2].metric("Erreurs", stats["terminees"] - stats["reussies"])
        colonnes[3].metric("Score", f"{stats['score']} pts")

    if session["terminee"]:
        afficher_bilan_entrainement(session)
        return

    question = session["questions"][index_question]
    with st.container(key="entrainement_zone_travail"):
        st.caption(
            f"Question {index_question + 1} sur {total} · "
            f"{session['difficulte']} · {question['notion']}"
        )
        st.markdown(f"### {question['prompt']}")
        if question["type"] == "prediction_entrainement":
            st.caption(f"Algorithme : {question['nom_algorithme']}")
            st.markdown("**Données de départ**")
            st.write(question["entree"])

        if not question["resolue"]:
            with st.form(f"entrainement_reponse_{session['id']}_{index_question}"):
                reponse = st.radio(
                    "Choisis une réponse",
                    question["choix"],
                    index=None,
                    format_func=lambda valeur: ", ".join(map(str, valeur)) if isinstance(valeur, list) else str(valeur),
                    key=f"entrainement_choix_{session['id']}_{index_question}",
                )
                soumettre = st.form_submit_button("Valider ma réponse", type="primary")
            if soumettre:
                if reponse is None:
                    st.warning("Choisis une réponse avant de valider.")
                else:
                    statut = valider_reponse_entrainement(question, reponse)
                    if statut in ("correcte", "incorrecte") and progression_store is not None:
                        question["progression_resultat"] = enregistrer_progression(
                            progression_store.record_exercise_result,
                            session.get("profil_nom", profil_nom),
                            session["difficulte"],
                            question,
                        )
                    st.session_state["entrainement_session"] = session
                    st.rerun()

        if question["resolue"]:
            with st.container(key="entrainement_retour"):
                resultat_progression = question.get("progression_resultat") or {}
                if question["correcte"]:
                    st.success(f"Bonne réponse · +{resultat_progression.get('xp_gagnes', 0)} XP")
                    for succes_id in resultat_progression.get("nouveaux_succes", ()):
                        st.success(
                            f"Succès débloqué · {SUCCES[succes_id]['nom']} "
                            f"(+{SUCCES[succes_id]['xp']} XP)"
                        )
                else:
                    st.error("Réponse incorrecte.")
                st.markdown("**Réponse attendue**")
                attendue = question["reponse_attendue"]
                st.write(", ".join(map(str, attendue)) if isinstance(attendue, list) else attendue)
                st.markdown("**Explication**")
                st.write(question["explication"])
                texte_suivant = "Terminer la session" if index_question + 1 == total else "Question suivante"
                if st.button(texte_suivant, type="primary", key=f"entrainement_suivant_{session['id']}_{index_question}"):
                    if passer_question_suivante(session) and session["terminee"] and progression_store is not None:
                        session["progression_succes"] = enregistrer_progression(
                            progression_store.complete_exercise_session,
                            session.get("profil_nom", profil_nom),
                            session,
                        ) or []
                    st.session_state["entrainement_session"] = session
                    st.rerun()


def afficher_page_defi_interactif():
    with st.container(key="defis_page"):
        _afficher_contenu_page_defi_interactif()


def _afficher_contenu_page_defi_interactif():
    with st.container(key="defis_intro"):
        st.markdown(
            '<p class="defis-kicker">APPRENDRE EN AGISSANT</p>',
            unsafe_allow_html=True,
        )
        st.header("Défis")
        st.write(
            "Mets à l’épreuve ta compréhension des tris, de leurs opérations "
            "à leurs invariants."
        )

    with st.container(key="defis_configuration"):
        st.markdown("#### Préparer un défi")
        colonnes_configuration = st.columns(3)
        type_defi = colonnes_configuration[0].selectbox(
            "Mode de défi", TYPES_DEFI, key="defi_type"
        )
        algorithme = colonnes_configuration[1].selectbox(
            "Algorithme", list(ALGORITHMES), key="defi_algorithme"
        )
        difficulte = colonnes_configuration[2].selectbox(
            "Difficulté", DIFFICULTES_DEFI, key="defi_difficulte"
        )
    regles = {
        "Étapes": "Effectue les opérations réelles du tri et respecte ses invariants.",
        "Prédiction": "Prédit l'état du tableau après une opération réelle du moteur de tri.",
        "Identification": "Reconnais l'algorithme à partir de son invariant et de son fonctionnement.",
        "Remise en ordre": "Replace les étapes structurantes de l'algorithme dans leur ordre logique.",
        "Rapidité": f"Réponds à une série de questions en moins de {DELAI_RAPIDITE_SECONDES} secondes; le score valorise d'abord les bonnes réponses.",
        "Maîtrise": "Enchaîne une prédiction, une identification et une remise en ordre de difficulté croissante.",
    }
    with st.container(key="defis_objectif"):
        st.caption("OBJECTIF DU MODE")
        st.write(regles[type_defi])
        st.caption(f"Niveau : {difficulte}")
    if algorithme not in ALGORITHMES_JOUABLES:
        defi_courant = st.session_state.get("defi_interactif")
        if defi_courant is not None and (
            defi_courant["nom_algorithme"] != algorithme
            or defi_courant["difficulte"] != difficulte
            or defi_courant.get("type_defi", "Étapes") != type_defi
        ):
            st.session_state.pop("defi_interactif", None)
        st.info(
            "Ce tri est sélectionnable, mais ses opérations interactives ne sont pas encore prises en charge. "
            "Les défis jouables actuellement sont : bulles, sélection et insertion."
        )
        return

    defi = st.session_state.get("defi_interactif")
    if (
        defi is None
        or defi["nom_algorithme"] != algorithme
        or defi["difficulte"] != difficulte
        or defi.get("type_defi", "Étapes") != type_defi
    ):
        st.session_state.pop("defi_abandon_confirmation", None)
        defi = creer_defi(algorithme, difficulte, type_defi=type_defi)
        defi["profil_nom"] = profil_nom
        st.session_state["defi_interactif"] = defi

    def lancer_defi_suivant():
        nouveau_defi = creer_defi(algorithme, difficulte, type_defi=type_defi)
        nouveau_defi["profil_nom"] = profil_nom
        st.session_state["defi_interactif"] = nouveau_defi
        st.session_state.pop("defi_abandon_confirmation", None)

    if type_defi == "Rapidité" and not defi_termine(defi):
        st_autorefresh(interval=1000, key=f"defi_timer_{defi['id']}")
    bilan = progression_defi(defi)
    progression = bilan["terminees"] / bilan["total"] if bilan["total"] else 1.0
    with st.container(key="defis_progression"):
        if defi_termine(defi):
            statut = "Réussi · défi validé" if bilan["reussite"] else "Échec · temps écoulé"
            style_statut = "reussi" if bilan["reussite"] else "echoue"
        elif defi["tentatives"] or defi["indices_utilises"]:
            statut = "En cours"
            style_statut = "en-cours"
        else:
            statut = "À commencer"
            style_statut = "attente"
        st.markdown(
            f'<p class="defis-status defis-status-{style_statut}" role="status">'
            f'{statut}</p>',
            unsafe_allow_html=True,
        )
        st.progress(progression)
        colonnes = st.columns(4)
        colonnes[0].metric("Étapes", f"{bilan['terminees']} / {bilan['total']}")
        colonnes[1].metric("Précision", f"{bilan['score']} %")
        colonnes[2].metric("Erreurs", bilan["erreurs"])
        colonnes[3].metric("Indices", bilan["indices"])
        st.caption(
            "Score de précision = actions validées ÷ actions soumises. "
            "Une même partie ne peut attribuer sa récompense qu’une seule fois."
        )
        if type_defi == "Rapidité" and not defi_termine(defi):
            restant = max(0, DELAI_RAPIDITE_SECONDES - int(bilan["temps_secondes"]))
            st.caption(f"Temps restant : {restant} s")
        if progression_store is not None and not defi_termine(defi):
            profil_defi = defi.get("profil_nom", profil_nom)
            meilleur = enregistrer_progression(
                progression_store.best_challenge_score, profil_defi, type_defi
            )
            st.caption(
                f"Meilleur score · {meilleur} %" if meilleur is not None
                else "Aucun score enregistré pour ce mode."
            )

    if defi_termine(defi):
        if "progression_resultat" not in defi and progression_store is not None:
            resultat_progression = enregistrer_progression(
                progression_store.record_challenge_success,
                defi.get("profil_nom", profil_nom),
                defi,
            )
            if resultat_progression is not None:
                defi["progression_resultat"] = resultat_progression
                st.session_state["defi_interactif"] = defi
                st.rerun()
        if bilan.get("temps_ecoule"):
            st.error("Temps écoulé. Le défi est échoué, mais son bilan reste disponible.")
        else:
            st.success("Défi réussi. Voici ton bilan de la série.")
        resultat_progression = defi.get("progression_resultat")
        if resultat_progression is not None:
            if resultat_progression["xp_gagnes"]:
                st.caption(
                    f"Récompense de progression : +{resultat_progression['xp_gagnes']} XP"
                )
            if resultat_progression.get("record_battu"):
                st.success(
                    f"Nouveau meilleur score pour ce mode : "
                    f"{resultat_progression['meilleur_score']} %"
                )
            elif resultat_progression.get("meilleur_score") is not None:
                st.caption(
                    f"Meilleur score enregistré : "
                    f"{resultat_progression['meilleur_score']} %"
                )
            for succes_id in resultat_progression["nouveaux_succes"]:
                st.success(
                    f"Succès débloqué · {SUCCES[succes_id]['nom']} "
                    f"(+{SUCCES[succes_id]['xp']} XP)"
                )
        with st.container(key="defis_bilan"):
            st.markdown("#### Bilan du défi")
            colonnes = st.columns(4)
            colonnes[0].metric("Réussite", "Oui" if bilan["reussite"] else "Non")
            colonnes[1].metric("Actions validées", bilan["actions"])
            colonnes[2].metric("Erreurs", bilan["erreurs"])
            colonnes[3].metric("Indices utilisés", bilan["indices"])
            st.metric("Score de précision", f"{bilan['score']} %")
            if type_defi == "Rapidité":
                st.metric("Temps", f"{bilan['temps_secondes']} s")
            st.caption(
                "Compétences travaillées : "
                + ", ".join({
                    "Étapes": ("suivre un invariant", "raisonner sur les opérations"),
                    "Prédiction": ("simuler un état", "suivre les mutations"),
                    "Identification": ("reconnaître les invariants", "comparer les algorithmes"),
                    "Remise en ordre": ("structurer un algorithme", "ordonner les opérations"),
                    "Rapidité": ("récupérer les connaissances", "répondre avec précision"),
                    "Maîtrise": ("prédire", "identifier", "ordonner"),
                }[type_defi])
            )
            if type_defi == "Étapes":
                st.markdown("**Tableau trié**")
                st.write(etat_defi(defi))
        if st.button("Réinitialiser", key=f"defi_rejouer_{defi['id']}"):
            defi_reinitialise = reinitialiser_defi(defi)
            defi_reinitialise["profil_nom"] = defi.get("profil_nom", profil_nom)
            st.session_state["defi_interactif"] = defi_reinitialise
            st.rerun()
        st.button(
            "Exercices recommandés",
            key=f"defi_exercices_{defi['id']}",
            on_click=ouvrir_recommandation,
            args=(defi.get("profil_nom", profil_nom), {
                "page": "Exercices",
                "algorithme": algorithme,
                "difficulte": difficulte,
                "type_question": "etat",
            }),
        )
    else:
        tache_courante = defi["taches"][defi["curseur"]]
        with st.container(key="defis_consigne"):
            st.markdown(f"#### Question {bilan['terminees'] + 1} / {bilan['total']} · {type_defi}")
            st.write(consigne_defi(defi))
            contexte = contexte_defi(defi)
            if contexte:
                st.caption(contexte)

        if type_defi == "Étapes":
            tableau = etat_defi(defi)
            cellules = "".join(
                f'<div class="array-cell array-cell-idle"><small>Position {index}</small>'
                f"<strong>{valeur}</strong></div>"
                for index, valeur in enumerate(tableau)
            )
            st.markdown(
                f'<div class="array-visualisation" aria-label="Tableau du défi">{cellules}</div>',
                unsafe_allow_html=True,
            )
        if defi.get("indice_affiche"):
            st.info("Indice : " + defi["indice_affiche"])
        if defi.get("feedback"):
            with st.container(key="defis_retour"):
                if defi["feedback"]["correcte"]:
                    st.success(defi["feedback"]["texte"])
                else:
                    st.error("Réponse incorrecte")
                    st.markdown("**Explication**")
                    st.write(defi["feedback"]["texte"])
                    if "reponse_attendue" in defi["feedback"]:
                        st.markdown("**Réponse attendue**")
                        st.write(defi["feedback"]["reponse_attendue"])

        action = defi["taches"][defi["curseur"]]["action"]
        schema = defi["taches"][defi["curseur"]]["schema"]
        with st.form(f"defi_action_{defi['id']}_{defi['curseur']}"):
            colonnes_champs = st.columns(min(2, len(schema["champs"])))
            valeurs_champs = []
            for index_champ, champ in enumerate(schema["champs"]):
                colonne = colonnes_champs[index_champ % len(colonnes_champs)]
                format_func = lambda valeur, libelles=champ.get("libelles", {}): (
                    libelles.get(valeur, str(valeur))
                )
                if champ["type"] == "radio":
                    valeur_champ = colonne.radio(
                        champ["label"], champ["options"], index=None,
                        format_func=format_func,
                        key=f"defi_champ_{defi['id']}_{defi['curseur']}_{index_champ}",
                    )
                else:
                    valeur_champ = colonne.selectbox(
                        champ["label"], champ["options"], index=None,
                        placeholder="Choisir",
                        format_func=format_func,
                        key=f"defi_champ_{defi['id']}_{defi['curseur']}_{index_champ}",
                    )
                valeurs_champs.append(valeur_champ)

            reponse = {"action": action}
            groupes = {}
            formulaire_complet = True
            for champ, valeur_champ in zip(schema["champs"], valeurs_champs):
                if valeur_champ is None:
                    formulaire_complet = False
                    continue
                if "partie" in champ:
                    groupes.setdefault(champ["reponse"], {})[champ["partie"]] = valeur_champ
                elif "correspondances" in champ:
                    for cle, position in champ["correspondances"].items():
                        reponse[cle] = valeur_champ[position]
                else:
                    reponse[champ["reponse"]] = valeur_champ
            for cle, parties in groupes.items():
                if len(parties) != 2:
                    formulaire_complet = False
                else:
                    reponse[cle] = tuple(parties[index] for index in range(2))
            if not formulaire_complet:
                reponse = None
            libelle_validation = (
                "Valider l'opération" if type_defi == "Étapes" else "Valider ma réponse"
            )
            soumettre = st.form_submit_button(libelle_validation, type="primary")

        commandes = st.columns(2)
        indice_disabled = defi["indices_etape"] >= 2
        if commandes[0].button(
            "Indice progressif", key=f"defi_indice_{defi['id']}_{defi['curseur']}",
            disabled=indice_disabled,
        ):
            defi["indice_affiche"] = utiliser_indice_defi(defi)
            st.session_state["defi_interactif"] = defi
            st.rerun()
        if commandes[1].button("Réinitialiser", key=f"defi_reinitialiser_{defi['id']}"):
            defi_reinitialise = reinitialiser_defi(defi)
            defi_reinitialise["profil_nom"] = defi.get("profil_nom", profil_nom)
            st.session_state["defi_interactif"] = defi_reinitialise
            st.rerun()

        if soumettre:
            if reponse is None:
                st.warning("Choisis toutes les positions ou une décision avant de valider.")
            else:
                valider_action_defi(defi, reponse)
                defi["indice_affiche"] = None
                st.session_state["defi_interactif"] = defi
                st.rerun()

    if defi_termine(defi):
        if st.button("Défi suivant", key=f"defi_suivant_{defi['id']}"):
            lancer_defi_suivant()
            st.rerun()
    else:
        if st.button("Abandonner le défi", key=f"defi_abandonner_{defi['id']}"):
            st.session_state["defi_abandon_confirmation"] = defi["id"]
            st.rerun()
        if st.session_state.get("defi_abandon_confirmation") == defi["id"]:
            st.warning(
                "Abandonner ce défi ? Sa progression sera perdue et aucune récompense ne sera attribuée."
            )
            colonne_confirmer, colonne_continuer = st.columns(2)
            if colonne_confirmer.button(
                "Confirmer l'abandon", key=f"defi_confirmer_abandon_{defi['id']}"
            ):
                lancer_defi_suivant()
                st.rerun()
            if colonne_continuer.button(
                "Continuer le défi", key=f"defi_continuer_{defi['id']}"
            ):
                st.session_state.pop("defi_abandon_confirmation", None)
def afficher_page_manipulation():
    st.title("Manipulation")
    st.caption("Agis sur le tableau et respecte les opérations réelles du tri choisi.")

    colonnes_configuration = st.columns(2)
    algorithme = colonnes_configuration[0].selectbox(
        "Algorithme",
        ALGORITHMES_MANIPULATION,
        key="manipulation_algorithme",
    )
    difficulte = colonnes_configuration[1].selectbox(
        "Difficulté",
        DIFFICULTES_MANIPULATION,
        key="manipulation_difficulte",
    )
    minimum, maximum = INTERVALLES_TAILLE[difficulte]
    taille = st.slider(
        "Taille du tableau",
        min_value=minimum,
        max_value=maximum,
        value=(minimum + maximum) // 2,
        key=f"manipulation_taille_{difficulte}",
    )
    type_tableau = st.selectbox(
        "Type de données",
        TYPES_TABLEAU,
        key="manipulation_type_tableau",
    )
    configuration = (algorithme, difficulte, taille, type_tableau)
    partie = st.session_state.get("manipulation_partie")

    if partie is None:
        st.info("Choisis les paramètres, puis démarre une nouvelle manipulation.")
        if st.button("Commencer", type="primary", key="manipulation_commencer"):
            partie = creer_partie(
                algorithme, difficulte, taille, type_tableau
            )
            partie["profil_nom"] = profil_nom
            st.session_state["manipulation_partie"] = partie
            st.rerun()
        return

    configuration_partie = (
        partie["algorithme"], partie["difficulte"],
        partie["taille"], partie["type_tableau"],
    )
    if configuration != configuration_partie:
        st.warning("Les paramètres ont changé. La partie actuelle reste intacte jusqu'au démarrage de la suivante.")
        if st.button("Démarrer avec ces paramètres", key=f"manipulation_nouvelle_{partie['id']}"):
            nouvelle_partie = creer_partie(
                algorithme, difficulte, taille, type_tableau
            )
            nouvelle_partie["profil_nom"] = profil_nom
            st.session_state["manipulation_partie"] = nouvelle_partie
            st.rerun()

    insertion = partie["algorithme"] == "Tri par insertion"
    tableau = partie["tableau"]
    taille_tableau = len(tableau)
    roles = ["idle"] * taille_tableau
    for indice in range(taille_tableau):
        if tableau[indice] is None:
            roles[indice] = "mutation"
        elif partie["completee"]:
            roles[indice] = "placed"
        elif indice < partie["index"]:
            roles[indice] = "sorted"

    if insertion:
        phase = partie["phase"]
        if phase == "choisir_cle":
            roles[partie["index"]] = "selected"
        elif phase == "comparer":
            roles[partie["curseur"]] = "compare"
        elif phase == "deplacer":
            roles[partie["curseur"]] = "mutation"
            roles[partie["curseur"] + 1] = "mutation"
        elif phase == "inserer":
            roles[partie["curseur"] + 1] = "mutation"
    else:
        minimum_courant = partie["minimum"]
        roles[minimum_courant] = "selected"
        for indice in partie["compares"]:
            if indice != minimum_courant:
                roles[indice] = "compare"
        if partie["phase"] == "comparer":
            roles[partie["curseur"]] = "compare"
        elif partie["phase"] == "echanger":
            roles[partie["index"]] = "mutation"
            roles[partie["minimum"]] = "mutation"

    classes = {
        "idle": "array-cell-idle",
        "sorted": "array-cell-sorted",
        "compare": "array-cell-compare",
        "selected": "array-cell-selected",
        "mutation": "array-cell-mutation",
        "placed": "array-cell-placed",
    }
    etiquettes = {
        "idle": "à examiner",
        "sorted": "zone triée",
        "compare": "comparaison",
        "selected": "minimum / clé",
        "mutation": "déplacement / échange",
        "placed": "trié",
    }
    cellules = "".join(
        f'<div class="array-cell {classes[role]}"><small>{indice} · '
        f'{etiquettes[role] if valeur is not None else "case libre"}</small>'
        f"<strong>{'·' if valeur is None else valeur}</strong></div>"
        for indice, (valeur, role) in enumerate(zip(tableau, roles))
    )
    cle = ""
    if insertion and partie["cle"] is not None:
        cle = (
            '<div class="array-key"><small>Clé conservée</small>'
            f"<strong>{partie['cle']}</strong></div>"
        )
    st.markdown(
        f'<div class="array-visualisation" aria-label="Tableau manipulable">{cellules}{cle}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Bleu : zone triée · jaune : élément comparé · violet : clé ou minimum · rose : opération à effectuer · vert : placé.")

    if insertion:
        progression = max(0, partie["index"] - 1) / max(1, taille_tableau - 1)
    else:
        progression = partie["index"] / max(1, taille_tableau - 1)
    if partie["completee"]:
        progression = 1.0
    st.progress(progression)
    colonnes_indicateurs = st.columns(3)
    colonnes_indicateurs[0].metric("Étapes", partie["etapes"])
    colonnes_indicateurs[1].metric("Erreurs", partie["erreurs"])
    colonnes_indicateurs[2].metric("Indices", partie["indices_utilises"])

    if partie["difficulte"] == "Facile":
        st.caption("Facile · les zones et l'élément actif sont indiqués; jusqu'à trois indices progressifs.")
    elif partie["difficulte"] == "Intermédiaire":
        st.caption("Intermédiaire · poursuis le tableau avec deux indices disponibles.")
    else:
        st.caption("Difficile · aide réduite à un indice; les opérations doivent suivre exactement le tri.")

    actions = {
        "choisir_cle": "Identifie la prochaine clé dans le tableau.",
        "comparer": "Choisis le prochain élément à examiner.",
        "deplacer": "Déplace cette valeur d'une case vers la droite.",
        "inserer": "Insère la clé dans la case libérée.",
        "choisir_minimum": "Sélectionne l'indice du minimum de la zone examinée.",
        "echanger": "Échange le minimum avec le début de la zone non triée.",
        "confirmer": "Le minimum est déjà au début : confirme l'absence d'échange.",
    }

    if partie["completee"]:
        if partie["reussite"]:
            if "progression_resultat" not in partie and progression_store is not None:
                resultat = enregistrer_progression(
                    progression_store.record_manipulation_success,
                    partie.get("profil_nom", profil_nom),
                    partie,
                )
                if resultat is not None:
                    partie["progression_resultat"] = resultat
                    st.session_state["manipulation_partie"] = partie
            st.success("Réussite : le tableau est trié et les opérations ont respecté l'algorithme.")
            resultat = partie.get("progression_resultat")
            if resultat is not None:
                st.caption(f"Récompense de progression : +{resultat['xp_gagnes']} XP")
                for succes_id in resultat["nouveaux_succes"]:
                    st.success(f"Succès débloqué · {SUCCES[succes_id]['nom']} (+{SUCCES[succes_id]['xp']} XP)")
        else:
            st.error("La partie est terminée, mais le tableau ne valide pas le tri attendu.")
        st.markdown("#### Bilan")
        colonnes_bilan = st.columns(4)
        colonnes_bilan[0].metric("Résultat", "Réussi" if partie["reussite"] else "À vérifier")
        colonnes_bilan[1].metric("Étapes validées", partie["etapes"])
        colonnes_bilan[2].metric("Erreurs", partie["erreurs"])
        colonnes_bilan[3].metric("Indices utilisés", partie["indices_utilises"])
        st.write(partie["tableau"])
    else:
        phase = partie["phase"]
        st.markdown(f"#### Étape suivante · {partie['algorithme']}")
        st.write(actions[phase])
        if phase == "comparer" and insertion:
            st.caption(f"Clé {partie['cle']} · élément à examiner en position {partie['curseur']}")
        elif not insertion and phase == "comparer":
            st.caption(f"Minimum provisoire : position {partie['minimum']} · candidat courant : position {partie['curseur']}")

        cle_partie = partie["id"]
        with st.form(f"manipulation_action_{cle_partie}_{partie['etapes']}"):
            reponse = {}
            if phase == "choisir_cle":
                choix = st.selectbox(
                    "Position de la clé",
                    range(taille_tableau),
                    index=None,
                    format_func=lambda indice: f"Position {indice} · {tableau[indice]}",
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_cle",
                )
                if choix is not None:
                    reponse["indice"] = choix
            elif phase == "comparer":
                options = range(partie["curseur"] + 1) if insertion else range(partie["curseur"], taille_tableau)
                choix = st.selectbox(
                    "Indice à comparer",
                    options,
                    index=None,
                    format_func=lambda indice: f"Position {indice} · {tableau[indice]}",
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_comparaison",
                )
                if choix is not None:
                    reponse["indice"] = choix
            elif phase == "deplacer":
                colonnes_action = st.columns(2)
                source = colonnes_action[0].selectbox(
                    "Position source", range(taille_tableau), index=None,
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_source",
                )
                destination = colonnes_action[1].selectbox(
                    "Position de destination", range(taille_tableau), index=None,
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_destination",
                )
                if source is not None:
                    reponse["source"] = source
                if destination is not None:
                    reponse["destination"] = destination
            elif phase == "inserer":
                destination = st.selectbox(
                    "Position d'insertion", range(taille_tableau), index=None,
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_insertion",
                )
                if destination is not None:
                    reponse["destination"] = destination
            elif phase == "choisir_minimum":
                choix = st.selectbox(
                    "Indice du minimum", range(partie["index"], taille_tableau), index=None,
                    format_func=lambda indice: f"Position {indice} · {tableau[indice]}",
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_minimum",
                )
                if choix is not None:
                    reponse["indice"] = choix
            elif phase == "echanger":
                colonnes_action = st.columns(2)
                source = colonnes_action[0].selectbox(
                    "Position du début non trié", range(taille_tableau), index=None,
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_echange_source",
                )
                destination = colonnes_action[1].selectbox(
                    "Position du minimum", range(taille_tableau), index=None,
                    key=f"manipulation_champ_{cle_partie}_{partie['etapes']}_echange_destination",
                )
                if source is not None:
                    reponse["source"] = source
                if destination is not None:
                    reponse["destination"] = destination

            texte_validation = "Confirmer sans échange" if phase == "confirmer" else "Valider l'étape"
            soumettre = st.form_submit_button(texte_validation, type="primary")

        if soumettre:
            champs_requis = {
                "choisir_cle": ("indice",), "comparer": ("indice",),
                "deplacer": ("source", "destination"), "inserer": ("destination",),
                "choisir_minimum": ("indice",), "echanger": ("source", "destination"),
                "confirmer": (),
            }[phase]
            if any(champ not in reponse for champ in champs_requis):
                st.warning("Complète les positions demandées avant de valider.")
            else:
                valider_action_manipulation(partie, phase, reponse)
                st.session_state["manipulation_partie"] = partie
                st.rerun()

        commandes = st.columns(3)
        if commandes[0].button(
            "Obtenir un indice",
            key=f"manipulation_indice_{cle_partie}",
            disabled=partie["indices_utilises"] >= {
                "Facile": 3, "Intermédiaire": 2, "Difficile": 1,
            }[partie["difficulte"]],
        ):
            utiliser_indice_manipulation(partie)
            st.session_state["manipulation_partie"] = partie
            st.rerun()
        if commandes[1].button("Recommencer", key=f"manipulation_recommencer_{cle_partie}"):
            nouvelle_partie = creer_partie(
                partie["algorithme"], partie["difficulte"], partie["taille"],
                partie["type_tableau"], nombres=partie["entree"],
            )
            nouvelle_partie["profil_nom"] = partie.get("profil_nom", profil_nom)
            st.session_state["manipulation_partie"] = nouvelle_partie
            st.rerun()
        if commandes[2].button("Abandonner", key=f"manipulation_abandonner_{cle_partie}"):
            st.session_state.pop("manipulation_partie", None)
            st.rerun()

        if partie.get("indice_affiche"):
            st.info("Indice : " + partie["indice_affiche"])
        if partie.get("feedback"):
            if partie["feedback"]["correcte"]:
                st.success(partie["feedback"]["texte"])
            else:
                st.warning(partie["feedback"]["texte"])


def afficher_suite_question_exercice(session, question, index_question, total, statut):
    if not question["resolue"]:
        with st.form(f"reponse_{session['id']}_{index_question}"):
            if question["format"] == "choix":
                reponse = st.radio(
                    "Choisis une réponse",
                    question["choix"],
                    index=None,
                    key=f"choix_{session['id']}_{index_question}",
                )
            elif question["format"] == "texte":
                st.caption(f"Format attendu : {question['format_reponse']}")
                reponse = st.text_input(
                    "Ta réponse",
                    key=f"texte_{session['id']}_{index_question}",
                )
            else:
                reponse = [
                    st.selectbox(
                        f"Position {position + 1}",
                        question["evenements"],
                        index=None,
                        placeholder="Choisir un événement",
                        key=f"ordre_{session['id']}_{index_question}_{position}",
                    )
                    for position in range(3)
                ]
            soumettre = st.form_submit_button("Valider ma réponse", type="primary")

        if soumettre:
            vide = (
                reponse is None
                or reponse == ""
                or (isinstance(reponse, list) and any(element is None for element in reponse))
            )
            if vide:
                st.warning("Choisis ou saisis une réponse avant de valider.")
            else:
                statut = valider_reponse(question, reponse)
                if statut in ("correcte", "incorrecte_finale") and progression_store is not None:
                    question["progression_resultat"] = enregistrer_progression(
                        progression_store.record_exercise_result,
                        session.get("profil_nom", profil_nom),
                        session["difficulte"],
                        question,
                    )
                st.session_state["exercices_session"] = session
                if statut == "nouvel_essai":
                    st.warning("Cette proposition ne correspond pas encore à la trace. Il te reste un essai; la correction reste masquée.")
                elif statut == "doublon":
                    st.info("Cette même réponse a déjà été évaluée; choisis une autre proposition pour utiliser ton second essai.")
                elif statut in ("correcte", "incorrecte_finale"):
                    st.rerun()

        if question["tentatives"]:
            st.markdown("**Ta dernière réponse**")
            derniere_reponse = question["derniere_reponse"]
            st.write(
                " → ".join(map(str, derniere_reponse))
                if isinstance(derniere_reponse, list)
                else derniere_reponse
            )
        if question["tentatives"] == 1 and not question["resolue"] and statut is None:
            st.caption("Une tentative reste; la réponse attendue sera révélée après validation du second essai.")

    if question["resolue"]:
        if question["correcte"]:
            recompense = question.get("progression_resultat") or {}
            st.success(
                f"Bonne réponse · {question['points']} points · "
                f"+{recompense.get('xp_gagnes', 0)} XP"
            )
            for succes_id in recompense.get("nouveaux_succes", ()):
                st.success(
                    f"Succès débloqué · {SUCCES[succes_id]['nom']} "
                    f"(+{SUCCES[succes_id]['xp']} XP)"
                )
        else:
            st.error("La réponse finale est incorrecte · 0 point")
        st.markdown("**Ta réponse**")
        derniere_reponse = question["derniere_reponse"]
        st.write(
            " → ".join(map(str, derniere_reponse))
            if isinstance(derniere_reponse, list)
            else derniere_reponse
        )
        st.markdown("**Réponse attendue**")
        if question["format"] == "ordre":
            for position, (label, index) in enumerate(zip(question["ordre_correct"], question["indices_evenements"]), start=1):
                st.write(f"{position}. {label} — {question['historique'][index]['explication']}")
        else:
            st.write(question["reponse_attendue"])
        st.markdown("**Explication**")
        st.write(question["explication"])
        if question["type"] == "comprehension":
            st.caption("Les choix incorrects ne correspondent pas à la règle d'exécution décrite ci-dessus.")

        texte_suivant = "Voir le bilan" if index_question + 1 == total else "Question suivante"
        if st.button(texte_suivant, type="primary", key=f"suivant_{session['id']}_{index_question}"):
            if index_question + 1 == total:
                session["terminee"] = True
                if progression_store is not None:
                    session["progression_succes"] = enregistrer_progression(
                        progression_store.complete_exercise_session,
                        session.get("profil_nom", profil_nom),
                        session,
                    ) or []
            else:
                session["index_question"] += 1
            st.session_state["exercices_session"] = session
            st.rerun()


# =========================================================
# NAVIGATION
# =========================================================

st.sidebar.title("📊 AlgoLab")
st.sidebar.caption("Laboratoire d'algorithmique")
st.sidebar.divider()

profil_nom = profil_authentifie()
if profil_nom is None:
    afficher_ecran_authentification()
    st.stop()

page = st.sidebar.radio(
    "Navigation",
    ["Accueil", "Visualiser", "Comparer", "Expérimenter", "Exercices", "Entraînement", "Défi interactif", "Manipulation", "Profil"],
    key="navigation_page",
)

st.sidebar.divider()
st.sidebar.caption("Apprendre · Observer · Comparer")
afficher_profil_sidebar(profil_nom)

if page not in (
    "Accueil", "Profil", "Manipulation", "Visualiser", "Comparer", "Exercices", "Entraînement", "Défi interactif"
):
    st.title("Visualiseur d'algorithmes")
    st.caption(
        "Explore, observe et compare les algorithmes de tri, étape par étape."
    )


# =========================================================
# PAGE 1 — VISUALISER
# =========================================================

if page == "Accueil":
    afficher_page_accueil(profil_nom)

elif page == "Profil":
    afficher_page_profil(profil_nom)

elif page == "Visualiser":
    st.title("Visualiser un algorithme")
    st.caption("Choisis une entrée, puis observe comment le tri évolue à chaque étape.")

    with st.container(border=True, key="visualisation_configuration"):
        st.markdown("#### Paramètres de la visualisation")
        choix = st.columns([1.1, 1])
        with choix[0]:
            algorithme = st.selectbox(
                "Algorithme",
                list(ALGORITHMES.keys()),
                format_func=lambda nom: (
                    f"{nom} ({INFORMATIONS_ALGORITHMES[nom]['anglais']})"
                ),
                key="algo_visualisation",
                on_change=invalider_visualisation,
            )
        with choix[1]:
            mode = st.radio(
                "Source des données",
                ["Liste personnalisée", "Liste aléatoire"],
                key="mode_visualisation",
                horizontal=True,
                on_change=invalider_visualisation,
            )

        if mode == "Liste personnalisée":
            saisie = st.text_input(
                "Nombres séparés par des virgules",
                value="5, 2, 4, 1, 3",
                key="saisie_visualisation",
                on_change=invalider_visualisation,
            )
            taille = 10
            minimum = 1
            maximum = 50
        else:
            reglages = st.columns(3)
            with reglages[0]:
                taille = st.slider(
                    "Nombre de valeurs",
                    5, 30, 10,
                    key="taille_visualisation",
                    on_change=invalider_visualisation,
                )
            with reglages[1]:
                minimum = st.number_input(
                    "Valeur minimale",
                    value=1,
                    step=1,
                    key="minimum_visualisation",
                    on_change=invalider_visualisation,
                )
            with reglages[2]:
                maximum = st.number_input(
                    "Valeur maximale",
                    value=50,
                    step=1,
                    key="maximum_visualisation",
                    on_change=invalider_visualisation,
                )
            saisie = ""

        lancer = st.button(
            "Calculer les étapes",
            type="primary",
            width="stretch",
        )

    information = INFORMATIONS_ALGORITHMES[algorithme]
    with st.expander("Repères théoriques et mémoire"):
        st.caption(
            f"{information['anglais']} · Complexité temporelle (meilleur / moyen / pire) : "
            f"{information['meilleur']} / {information['moyen']} / "
            f"{information['pire']} · Mémoire : {information['memoire']}"
        )
        if algorithme == "Tri rapide":
            st.caption(
                "Pivot : élément central de chaque segment; partition en trois zones "
                "pour traiter efficacement les doublons."
            )


    if lancer:
        try:
            nombres = creer_liste(
                mode, saisie, taille, int(minimum), int(maximum)
            )

            st.session_state["etapes"] = ALGORITHMES[algorithme](nombres)
            st.session_state["algorithme_actuel"] = algorithme
            st.session_state["curseur_etape"] = 0
            st.session_state["animation_active"] = False
            st.session_state["animation_dernier_tick"] = None
            st.session_state["visualisation_reinitialisee"] = False

        except ValueError:
            st.error(
                "Vérifie ta saisie : utilise des nombres entiers séparés "
                "par des virgules et respecte les limites indiquées."
            )

    if "etapes" not in st.session_state:
        st.info(
            "Choisis ton algorithme et tes valeurs ci-dessus, puis clique "
            "sur « Calculer les étapes »."
        )

    else:
        etapes = st.session_state["etapes"]
        derniere = len(etapes) - 1

        # Sécurité si un historique précédent est plus court.
        curseur = min(
            st.session_state.get("curseur_etape", 0),
            derniere,
        )
        st.session_state["curseur_etape"] = curseur
        st.subheader(
            f"Visualisation — {st.session_state['algorithme_actuel']}"
        )

        with st.container(border=True, key="visualisation_controls"):
            st.markdown("#### Contrôle de la lecture")

            vitesse = st.select_slider(
                "Vitesse de l'animation",
                options=["Lente", "Normale", "Rapide"],
                value="Normale",
                key="vitesse_animation",
            )

            delais = {
                "Lente": 1000,
                "Normale": 500,
                "Rapide": 150,
            }

            col_a, col_b = st.columns(2)

            with col_a:
                libelle_lecture = (
                    "▶ Lire l'animation" if curseur == 0 else "▶ Reprendre l'animation"
                )
                st.button(
                    libelle_lecture,
                    width="stretch",
                    disabled=curseur >= derniere or st.session_state["animation_active"],
                    on_click=demarrer_animation,
                )

            with col_b:
                st.button(
                    "⏸ Mettre en pause",
                    width="stretch",
                    disabled=not st.session_state["animation_active"],
                    on_click=pauser_animation,
                )

            if st.session_state["animation_active"]:
                if curseur < derniere:
                    tick = st_autorefresh(
                        interval=delais[vitesse],
                        key="actualisation_animation",
                    )
                    dernier_tick = st.session_state.get("animation_dernier_tick")
                    if dernier_tick is None:
                        st.session_state["animation_dernier_tick"] = tick
                    elif tick != dernier_tick:
                        curseur = min(curseur + 1, derniere)
                        st.session_state["curseur_etape"] = curseur
                        st.session_state["animation_dernier_tick"] = tick
                        if curseur == derniere:
                            st.session_state["animation_active"] = False
                else:
                    st.session_state["animation_active"] = False

            st.divider()

            col1, col2, col3 = st.columns(3)

            with col1:
                if curseur == 0:
                    st.button("← Précédente", width="stretch", disabled=True)
                else:
                    shortcut_button(
                        "← Précédente",
                        "arrowleft",
                        hint=False,
                        key="etape_precedente",
                        on_click=deplacer_curseur_visualisation,
                        args=(-1,),
                    )

            with col2:
                st.button(
                    "Recommencer",
                    width="stretch",
                    disabled=curseur == 0,
                    on_click=reinitialiser_lecture_visualisation,
                )

            with col3:
                if curseur == derniere:
                    st.button("Suivante →", width="stretch", disabled=True)
                else:
                    shortcut_button(
                        "Suivante →",
                        "arrowright",
                        hint=False,
                        key="etape_suivante",
                        on_click=deplacer_curseur_visualisation,
                        args=(1,),
                    )


        with st.container(key="visualisation_progression"):
            st.markdown("### Étape à étudier")
            mode_apprentissage = st.radio(
                "Mode",
                ["Découverte", "Analyse"],
                horizontal=True,
                key="mode_apprentissage",
            )
            numero = st.slider(
                "Parcourir les étapes",
                min_value=0,
                max_value=derniere,
                key="curseur_etape",
                on_change=arreter_animation,
            )

            etape = etapes[numero]
            terminee = numero == derniere
            if terminee:
                libelle_etat = "Tri terminé"
            elif st.session_state.get("visualisation_reinitialisee"):
                libelle_etat = "Visualisation réinitialisée"
            elif numero == 0:
                libelle_etat = "Prêt à démarrer"
            elif st.session_state["animation_active"]:
                libelle_etat = "Animation en cours"
            else:
                libelle_etat = "Tri en cours · lecture en pause"
            with st.container(key="visualisation_state"):
                st.caption(f"{libelle_etat} · étape {numero + 1} sur {len(etapes)}")
            st.progress(numero / derniere if derniere else 1.0, text="Progression du tri")
            st.markdown(f"#### {etape['action'].capitalize()}")
            st.write(etape["explication"])

            compteurs = st.columns(4)
            compteurs[0].metric("Comparaisons", etape["comparaisons"])
            compteurs[1].metric("Échanges", etape["echanges"])
            compteurs[2].metric("Déplacements / écritures", etape["deplacements"])
            compteurs[3].metric("Étape", f"{numero + 1} / {len(etapes)}")
            with st.expander("Comment lire les compteurs"):
                afficher_definitions_compteurs()

        graphique, pseudocode = st.columns([1.7, 1])
        with graphique:
            st.markdown("#### État du tableau")
            afficher_barres(
                etape,
                est_final=(numero == derniere),
                nom_algorithme=st.session_state["algorithme_actuel"],
            )
            if st.session_state["algorithme_actuel"] == "Tri fusion":
                afficher_vue_fusion(etape)
            elif st.session_state["algorithme_actuel"] == "Tri rapide":
                afficher_vue_rapide(etape)
            st.caption(
                "Les barres montrent les valeurs; les cellules indiquent leur position et leur rôle."
            )
            afficher_legende_tableau()
            if st.session_state["algorithme_actuel"] == "Tri par tas":
                with st.expander("Arbre binaire du max-heap", expanded=True):
                    afficher_arbre_tas(etape)
                    afficher_vue_tas(etape)

        with pseudocode:
            with st.container(key="visualisation_pseudocode"):
                afficher_pseudocode(
                    st.session_state["algorithme_actuel"], etape, mode_apprentissage
                )

        with st.container(key="visualisation_resultat"):
            if mode_apprentissage == "Analyse" and etape["avant"] is not None:
                avant, apres = st.columns(2)
                avant.caption(f"Avant : {etape['avant']}")
                apres.caption(f"Après : {etape['apres']}")
                if etape["valeur_en_cours"] is not None:
                    st.caption(
                        f"Valeur temporairement conservée : {etape['valeur_en_cours']}"
                    )

            if numero == derniere:
                st.success(f"Résultat final : {etape['liste']}")




# =========================================================
# PAGE 2 — COMPARER
# =========================================================

elif page == "Comparer":
    st.header("Comparer les algorithmes")
    st.write(
        "Observe six tris sur une même entrée et distingue les mesures "
        "expérimentales des ordres de grandeur théoriques."
    )


    with st.container(border=True, key="comparaison_configuration"):
        st.markdown("#### Protocole de comparaison")
        st.caption(
            "Chaque algorithme reçoit une copie exacte du même tableau initial."
        )

        colonnes_configuration = st.columns([1.3, 1, 1, 1.2])
        with colonnes_configuration[0]:
            type_donnees = st.selectbox(
                "Données initiales",
                TYPES_DONNEES,
                key="comparaison_type_donnees",
            )
        with colonnes_configuration[1]:
            taille = st.slider(
                "Taille du tableau",
                min_value=1,
                max_value=500,
                value=60,
                step=1,
                key="comparaison_taille",
            )
        with colonnes_configuration[2]:
            graine = st.number_input(
                "Graine aléatoire",
                value=42,
                step=1,
                key="comparaison_graine",
                help="Une même graine et les mêmes paramètres reproduisent le tableau.",
            )
        with colonnes_configuration[3]:
            repetitions = st.slider(
                "Répétitions du chronométrage",
                min_value=3,
                max_value=9,
                value=5,
                step=2,
                key="comparaison_repetitions",
            )

        st.caption(
            "Limite : 500 éléments. Au-delà, les algorithmes quadratiques "
            "(bulle, sélection, insertion) peuvent ralentir l'interface. "
            "Le chronométrage répète le tri seul et exclut génération, copie "
            "du tableau et animation."
        )

        lancer_comparaison = st.button(
            "Comparer les six algorithmes",
            type="primary",
            width="stretch",
        )


    if lancer_comparaison:
        for cle_session in (
            "comparaison_resultats",
            "comparaison_evolution",
            "comparaison_liste",
            "comparaison_type_resultat",
            "comparaison_graine_resultat",
            "comparaison_nombre_repetitions",
        ):
            st.session_state.pop(cle_session, None)
        st.session_state.pop("comparaison_erreur", None)
        try:
            lignes, evolution, nombres = _calculer_resultats_comparaison(
                type_donnees, taille, graine, repetitions
            )
        except Exception as erreur:
            st.session_state["comparaison_erreur"] = (
                f"{type(erreur).__name__} : {erreur}"
            )
        else:
            st.session_state["comparaison_resultats"] = lignes
            st.session_state["comparaison_evolution"] = evolution
            st.session_state["comparaison_liste"] = nombres
            st.session_state["comparaison_type_resultat"] = type_donnees
            st.session_state["comparaison_graine_resultat"] = int(graine)
            st.session_state["comparaison_nombre_repetitions"] = int(repetitions)

    if "comparaison_erreur" in st.session_state:
        st.error(
            "La comparaison n'a pas abouti. Vérifie les paramètres puis relance-la."
        )
        with st.expander("Détail technique"):
            st.code(st.session_state["comparaison_erreur"])
    elif (
        "comparaison_resultats" in st.session_state
        and "comparaison_evolution" in st.session_state
    ):
        resultats = st.session_state["comparaison_resultats"]
        evolution = st.session_state["comparaison_evolution"]
        repetitions_mesure = st.session_state["comparaison_nombre_repetitions"]
        with st.expander("Entrée commune et protocole"):
            st.caption(
                f"{st.session_state['comparaison_type_resultat']}, graine "
                f"{st.session_state['comparaison_graine_resultat']} : "
                f"{st.session_state['comparaison_liste']}"
            )

        with st.container(key="comparaison_mesures"):
            st.markdown(
                '<p class="comparaison-kicker">MESURES OBSERVÉES</p>',
                unsafe_allow_html=True,
            )
            afficher_resultats_comparaison(resultats, evolution)
            afficher_temps_comparaison(resultats, repetitions_mesure)
        afficher_analyse_automatique(resultats)
        with st.container(key="comparaison_theorie"):
            st.markdown(
                '<p class="comparaison-kicker">REPÈRES THÉORIQUES</p>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Les compteurs décrivent des opérations exécutées; la complexité "
                "asymptotique décrit leur croissance lorsque n augmente."
            )
            afficher_complexites_theoriques()
    else:
        st.info(
            "Aucune comparaison pour le moment. Choisis un protocole puis "
            "lance les six tris pour afficher les résultats."
        )


# =========================================================
# PAGE 3 — EXPÉRIMENTER
# =========================================================

elif page == "Expérimenter":
    st.header("Expérimenter")
    st.write("Que devient le nombre d'opérations d'un algorithme de tri lorsque la taille du tableau double ?")


    with st.container(border=True):
        st.markdown("#### 1. Hypothèse")
        hypothese = st.text_area(
            "Que prévois-tu d'observer ?",
            placeholder="Par exemple : le nombre de comparaisons va-t-il doubler ou davantage ?",
            key="hypothese_experience",
        )

        st.markdown("#### 2. Protocole")
        st.caption(
            "Les tableaux ont les tailles n, 2n, 4n... jusqu'à la limite choisie. "
            "Chaque taille est générée une fois, puis la même entrée est donnée "
            "à chaque algorithme sélectionné."
        )
        colonnes_configuration = st.columns(2)
        with colonnes_configuration[0]:
            noms_algorithmes = st.multiselect(
                "Algorithmes à étudier",
                list(ALGORITHMES),
                default=list(ALGORITHMES),
                key="experience_algorithmes",
            )
            types_donnees = st.multiselect(
                "Distributions à comparer",
                TYPES_DONNEES,
                default=[TYPES_DONNEES[0]],
                key="experience_type_donnees",
            )
            taille_initiale = st.slider(
                "Taille initiale (n)",
                min_value=10,
                max_value=250,
                value=10,
                step=10,
                key="experience_taille_initiale",
            )
        with colonnes_configuration[1]:
            taille_max = st.slider(
                "Taille maximale testée",
                min_value=taille_initiale * 2,
                max_value=TAILLE_MAX_EXPERIENCE,
                value=max(taille_initiale * 2, 80),
                step=10,
                key="experience_taille_max",
            )
            graine = st.number_input(
                "Graine aléatoire",
                value=42,
                step=1,
                key="experience_graine",
                help="La même graine et les mêmes paramètres reproduisent les entrées.",
            )
            repetitions_experience = st.slider(
                "Répétitions du chronométrage",
                min_value=3,
                max_value=REPETITIONS_MAX_EXPERIENCE,
                value=5,
                step=2,
                key="experience_repetitions",
            )

        st.caption(
            f"Limite de sécurité : {TAILLE_MAX_EXPERIENCE} éléments, comme dans Comparer. "
            "Les tris quadratiques peuvent ralentir au-delà. Les compteurs sont "
            "comptés séparément; les temps sont la médiane des tris seuls, hors copie."
        )
        lancer_experience = st.button(
            "Lancer l'expérience", type="primary", width="stretch"
        )

    if lancer_experience:
        try:
            if not types_donnees:
                raise ValueError("Sélectionne au moins une distribution.")
            resultats_experience = [
                ligne
                for distribution in types_donnees
                for ligne in mesurer_evolution(
                    noms_algorithmes,
                    distribution,
                    taille_initiale,
                    taille_max,
                    graine=int(graine),
                    repetitions=int(repetitions_experience),
                    fonctions_tri=TRIS_RAPIDES,
                )
            ]
            st.session_state["resultats_experience"] = resultats_experience
            st.session_state["types_experience"] = types_donnees.copy()
            st.session_state["tailles_experience"] = sorted({
                ligne["Taille"] for ligne in resultats_experience
            })
            st.session_state["algorithmes_experience"] = noms_algorithmes.copy()
            st.session_state["graine_experience"] = int(graine)
            st.session_state["hypothese_resultat_experience"] = hypothese
        except (ValueError, RuntimeError) as erreur_experience:
            for cle in (
                "resultats_experience",
                "types_experience",
                "tailles_experience",
                "algorithmes_experience",
                "graine_experience",
                "hypothese_resultat_experience",
            ):
                st.session_state.pop(cle, None)
            st.error(str(erreur_experience))

    if (
        "resultats_experience" in st.session_state
        and "algorithmes_experience" in st.session_state
    ):
        resultats = st.session_state["resultats_experience"]
        noms_resultat = st.session_state["algorithmes_experience"]
        tailles_resultat = st.session_state["tailles_experience"]
        types_resultat = st.session_state["types_experience"]
        st.markdown("#### 3. Résultats")
        st.caption(
            f"{', '.join(types_resultat)} · graine "
            f"{st.session_state['graine_experience']} · tailles "
            f"{', '.join(map(str, tailles_resultat))}"
        )
        st.dataframe(
            resultats, width="stretch", hide_index=True
        )
        afficher_definitions_compteurs()
        st.caption(
            "Autres opérations = échanges + déplacements. Le total des compteurs "
            "additionne comparaisons et autres opérations; aucun temps n'est inclus."
        )

        figure = go.Figure()
        for distribution in types_resultat:
            for nom in noms_resultat:
                lignes = [
                    ligne for ligne in resultats
                    if ligne["Algorithme"] == nom
                    and ligne["Distribution"] == distribution
                ]
                figure.add_trace(
                    go.Scatter(
                        x=[ligne["Taille"] for ligne in lignes],
                        y=[ligne["Total des compteurs"] for ligne in lignes],
                        mode="lines+markers",
                        name=f"{nom} · {distribution}",
                    )
                )
        styliser_figure(figure, hauteur=420)
        figure.update_layout(
            xaxis_title="Taille du tableau",
            yaxis_title="Comparaisons + autres opérations",
            hovermode="x unified",
            legend_title="Algorithme",
        )
        st.plotly_chart(figure, width="stretch")

        st.subheader("Temps de tri mesuré")
        colonnes_temps = st.columns(2)
        with colonnes_temps[0]:
            taille_temps = st.selectbox(
                "Taille pour comparer les temps",
                tailles_resultat,
                index=len(tailles_resultat) - 1,
                key="experience_temps_taille",
            )
        with colonnes_temps[1]:
            distribution_temps = st.selectbox(
                "Distribution pour comparer les temps",
                types_resultat,
                key="experience_temps_distribution",
            )
        lignes_temps = [
            ligne for ligne in resultats
            if ligne["Taille"] == taille_temps
            and ligne["Distribution"] == distribution_temps
        ]
        figure_temps = go.Figure(
            data=[go.Bar(
                x=[ligne["Algorithme"] for ligne in lignes_temps],
                y=[ligne["Temps médian (ms)"] for ligne in lignes_temps],
                text=[ligne["Temps médian (ms)"] for ligne in lignes_temps],
                textposition="outside",
            )]
        )
        styliser_figure(figure_temps, hauteur=370)
        figure_temps.update_layout(
            xaxis_title="Algorithme",
            yaxis_title="Temps médian (ms)",
            showlegend=False,
            bargap=0.34,
        )
        st.plotly_chart(figure_temps, width="stretch")
        st.caption(
            f"Médiane de {repetitions_experience} tris. La copie est exclue du chronométrage; "
            "chaque algorithme reçoit la même entrée. Pour de petits tableaux, le bruit "
            "de mesure peut être du même ordre que le temps observé."
        )
        st.write(
            "Sur des données déjà ou presque triées, les tris à bulles et par insertion "
            "peuvent profiter du faible nombre de décalages ou d'échanges. Les tris "
            "fusion et par tas ont généralement une croissance plus régulière; le tri "
            "rapide dépend aussi de la forme des partitions. Ce sont des tendances, pas "
            "une garantie pour chaque petite mesure."
        )

        st.markdown("#### Rapport entre n et 2n")
        for distribution in types_resultat:
            st.markdown(f"**{distribution}**")
            colonnes_rapports = st.columns(min(3, len(noms_resultat)))
            for index, nom in enumerate(noms_resultat):
                lignes = [
                    ligne for ligne in resultats
                    if ligne["Algorithme"] == nom
                    and ligne["Distribution"] == distribution
                ]
                facteur = lignes[1]["Facteur d'évolution"] if len(lignes) > 1 else None
                valeur = f"× {facteur:.2f}" if facteur is not None else "Non calculable"
                colonnes_rapports[index % len(colonnes_rapports)].metric(
                    f"{nom} · total des compteurs", valeur
                )

        st.markdown("#### Analyse des mesures")
        taille_analyse = st.selectbox(
            "Taille analysée",
            tailles_resultat,
            index=len(tailles_resultat) - 1,
            key="experience_taille_analyse",
        )
        resultats_taille = [
            ligne for ligne in resultats if ligne["Taille"] == taille_analyse
        ]
        afficher_analyse_automatique(resultats_taille)
        afficher_differences_distributions(resultats, taille_analyse)

        st.markdown("#### 4. Conclusion")
        hypothese_resultat = st.session_state.get(
            "hypothese_resultat_experience", ""
        )
        if hypothese_resultat:
            st.write(f"**Ton hypothèse :** {hypothese_resultat}")

        for distribution in types_resultat:
            for nom in noms_resultat:
                lignes = [
                    ligne for ligne in resultats
                    if ligne["Algorithme"] == nom
                    and ligne["Distribution"] == distribution
                ]
                facteur = lignes[1]["Facteur d'évolution"] if len(lignes) > 1 else None
                if facteur is None:
                    observation = (
                        "Le facteur n'est pas calculable, car le total mesuré à n est nul."
                    )
                elif 3.5 <= facteur <= 4.5:
                    observation = (
                        f"Sur ces tailles, le total mesuré est multiplié par {facteur:.2f} "
                        "lorsque la taille double. C'est compatible avec une tendance "
                        "quadratique sur les entrées testées, sans la prouver."
                    )
                elif 1.7 <= facteur <= 2.3:
                    observation = (
                        f"Sur ces tailles, le total mesuré est multiplié par {facteur:.2f} "
                        "lorsque la taille double; cette observation limitée ne suffit "
                        "pas à établir une croissance linéaire."
                    )
                else:
                    observation = (
                        f"Sur ces tailles, le total mesuré est multiplié par {facteur:.2f} "
                        "lorsque la taille double. Cette expérience ne montre pas un "
                        "facteur proche de deux ou de quatre."
                    )
                st.markdown(
                    f"**{nom} · {distribution} — observation :** {observation}"
                )
        st.caption(
            "Ces résultats décrivent uniquement les tailles et les entrées testées. "
            "Un rapport 2n/n, à lui seul, ne permet pas d'établir une complexité."
        )

        st.markdown("#### Repères théoriques, séparés des résultats")
        for nom in noms_resultat:
            information = INFORMATIONS_ALGORITHMES[nom]
            st.write(
                f"**{nom}** : meilleur {information['meilleur']}, moyen "
                f"{information['moyen']}, pire {information['pire']}. "
                "Ce sont des complexités théoriques, pas les mesures de cette expérience."
            )


elif page == "Exercices":
    afficher_page_exercices()

elif page == "Défi interactif":
    afficher_page_defi_interactif()

elif page == "Manipulation":
    afficher_page_manipulation()

elif page == "Entraînement":
    afficher_page_entrainement()
