"""
Historique des appels — Étape 6, point 1 de la méthode.

ElevenLabs envoie un webhook ("post_call_transcription") à la fin de
chaque conversation. Le format a été vérifié sur un vrai payload (voir
_extraire_tracabilite) : la charge utile est bien enveloppée dans une
clé "data", et donnees_brutes conserve malgré tout la charge complète
telle que reçue, au cas où un futur type d'appel (téléphonique plutôt
que widget, par exemple) aurait une structure différente.
"""

import json

from assistant.outils.db import connexion_app, horodatage


def _extraire_tracabilite(donnees):
    """Traçabilité par appel (CLAUDE.md, contrainte non négociable) :
    durée, coût réel, minutes ASR/TTS, détail des modèles/tokens, outils
    utilisés — tout est déjà dans le webhook ElevenLabs, vérifié sur un
    vrai payload le 19/08/2026 (voir docs/prochaines-etapes.md).

    Ne lève jamais d'exception : un champ absent ou un format différent
    (ex. appel téléphonique plutôt que widget) donne simplement des
    valeurs manquantes, jamais une perte de l'appel entier."""
    metadata = donnees.get("metadata") or {}
    charging = metadata.get("charging") or {}
    asr = charging.get("asr_usage") or {}
    tts = charging.get("tts_usage") or {}
    llm_usage = (
        (charging.get("llm_usage") or {})
        .get("irreversible_generation") or {}
    ).get("model_usage") or {}

    tokens_total = 0
    for modele, categories in llm_usage.items():
        for cle_categorie, valeurs in categories.items():
            tokens_total += (valeurs or {}).get("tokens", 0)

    outils = set()
    for tour in donnees.get("transcript") or []:
        for appel_outil in tour.get("tool_calls") or []:
            nom = appel_outil.get("tool_name")
            if nom:
                outils.add(nom)

    voix = sorted({
        v["voice_id"] for v in (tts.get("per_voice_usage") or []) if v.get("voice_id")
    })

    return {
        "duree_secs": metadata.get("call_duration_secs"),
        "cout_usd": metadata.get("cost_fiat"),
        "minutes_asr": (asr.get("total_audio_input_seconds") / 60) if asr.get("total_audio_input_seconds") is not None else None,
        "minutes_tts": (tts.get("total_audio_output_seconds") / 60) if tts.get("total_audio_output_seconds") is not None else None,
        "modeles_llm": json.dumps(llm_usage, ensure_ascii=False) if llm_usage else None,
        "tokens_llm": tokens_total or None,
        "outils_utilises": json.dumps(sorted(outils), ensure_ascii=False) if outils else None,
        "voix_utilisees": json.dumps(voix, ensure_ascii=False) if voix else None,
    }


def enregistrer_appel(charge_brute: dict):
    """Insère (ou met à jour si déjà vu) un appel à partir de la charge
    du webhook ElevenLabs. Ne lève jamais d'exception sur un format
    inattendu : un appel dont on ne reconnaît aucun champ est quand
    même stocké, pour ne perdre aucune donnée reçue."""
    donnees = charge_brute.get("data", charge_brute) if isinstance(charge_brute, dict) else {}
    conversation_id = donnees.get("conversation_id")
    agent_id = donnees.get("agent_id")
    statut = donnees.get("status")
    tracabilite = _extraire_tracabilite(donnees)

    conn = connexion_app()
    conn.execute(
        """
        INSERT INTO appels (
            cree_le, conversation_id, agent_id, statut, donnees_brutes,
            duree_secs, cout_usd, minutes_asr, minutes_tts, modeles_llm,
            tokens_llm, outils_utilises, voix_utilisees
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            statut = excluded.statut,
            donnees_brutes = excluded.donnees_brutes,
            duree_secs = excluded.duree_secs,
            cout_usd = excluded.cout_usd,
            minutes_asr = excluded.minutes_asr,
            minutes_tts = excluded.minutes_tts,
            modeles_llm = excluded.modeles_llm,
            tokens_llm = excluded.tokens_llm,
            outils_utilises = excluded.outils_utilises,
            voix_utilisees = excluded.voix_utilisees
        """,
        (
            horodatage(),
            conversation_id, agent_id, statut,
            json.dumps(charge_brute, ensure_ascii=False),
            tracabilite["duree_secs"], tracabilite["cout_usd"],
            tracabilite["minutes_asr"], tracabilite["minutes_tts"],
            tracabilite["modeles_llm"], tracabilite["tokens_llm"],
            tracabilite["outils_utilises"], tracabilite["voix_utilisees"],
        ),
    )
    conn.commit()
    conn.close()


def retraiter_tracabilite():
    """Recalcule les champs de traçabilité des appels déjà enregistrés,
    à partir de leur donnees_brutes déjà stockée — sans dépendre d'un
    nouveau webhook. Utile après avoir déployé _extraire_tracabilite
    (ou une amélioration future) : les appels reçus avant ce
    déploiement ont leur JSON brut, mais pas encore les colonnes
    dérivées. Renvoie le nombre d'appels mis à jour."""
    conn = connexion_app()
    appels = conn.execute("SELECT id, donnees_brutes FROM appels").fetchall()
    n = 0
    for a in appels:
        try:
            charge_brute = json.loads(a["donnees_brutes"])
        except json.JSONDecodeError:
            continue
        donnees = charge_brute.get("data", charge_brute) if isinstance(charge_brute, dict) else {}
        t = _extraire_tracabilite(donnees)
        conn.execute(
            """
            UPDATE appels SET
                duree_secs = ?, cout_usd = ?, minutes_asr = ?, minutes_tts = ?,
                modeles_llm = ?, tokens_llm = ?, outils_utilises = ?, voix_utilisees = ?
            WHERE id = ?
            """,
            (
                t["duree_secs"], t["cout_usd"], t["minutes_asr"], t["minutes_tts"],
                t["modeles_llm"], t["tokens_llm"], t["outils_utilises"], t["voix_utilisees"],
                a["id"],
            ),
        )
        n += 1
    conn.commit()
    conn.close()
    return n


def lister_appels(limite=100):
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT id, cree_le, conversation_id, agent_id, statut FROM appels "
        "ORDER BY id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(l) for l in lignes]


def lister_appels_avec_details(limite=100):
    """Comme lister_appels, mais avec la charge brute et les évaluations
    de chaque appel déjà chargées — utilisé par la page back-office
    consolidée, qui affiche tout sur un seul écran (accordéon HTML natif,
    sans rechargement de page par appel). satisfaction_client : jointe
    par conversation_id (voir satisfaction_appels dans assistant/outils/db.py) —
    None si l'appelant n'a pas répondu ou si l'outil n'a pas été appelé,
    à distinguer d'un "non" explicite (0)."""
    conn = connexion_app()
    appels = conn.execute(
        "SELECT a.id, a.cree_le, a.conversation_id, a.agent_id, a.statut, a.donnees_brutes, "
        "a.duree_secs, a.outils_utilises, a.voix_utilisees, s.satisfait AS satisfaction_client "
        "FROM appels a LEFT JOIN satisfaction_appels s ON s.conversation_id = a.conversation_id "
        "ORDER BY a.id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    resultat = []
    for a in appels:
        a = dict(a)
        evals = conn.execute(
            "SELECT cree_le, qualite, note FROM evaluations_appels "
            "WHERE appel_id = ? ORDER BY id DESC",
            (a["id"],),
        ).fetchall()
        a["evaluations"] = [dict(e) for e in evals]
        resultat.append(a)
    conn.close()
    return resultat


def compter_appels():
    conn = connexion_app()
    n = conn.execute("SELECT COUNT(*) AS n FROM appels").fetchone()["n"]
    conn.close()
    return n


def resumer_evaluations():
    """Renvoie (nb_bonnes, nb_total) sur la dernière évaluation de chaque
    appel évalué — un appel évalué plusieurs fois ne compte qu'une fois,
    pour son avis le plus récent."""
    conn = connexion_app()
    lignes = conn.execute(
        """
        SELECT qualite FROM evaluations_appels e
        WHERE e.id = (
            SELECT id FROM evaluations_appels e2
            WHERE e2.appel_id = e.appel_id
            ORDER BY id DESC LIMIT 1
        )
        """
    ).fetchall()
    conn.close()
    total = len(lignes)
    bonnes = sum(1 for l in lignes if l["qualite"] == "bonne")
    return bonnes, total


def resumer_satisfaction_client():
    """(nb_satisfaits, nb_total) déclarés par les appelants eux-mêmes —
    à distinguer de resumer_evaluations(), qui est l'avis de l'équipe.
    Une réponse par conversation_id (clé primaire de satisfaction_appels),
    donc pas de risque de double-compte."""
    conn = connexion_app()
    lignes = conn.execute("SELECT satisfait FROM satisfaction_appels").fetchall()
    conn.close()
    total = len(lignes)
    satisfaits = sum(1 for l in lignes if l["satisfait"])
    return satisfaits, total


def resumer_tracabilite():
    """Agrège la traçabilité de tous les appels qui en ont une (les
    appels enregistrés avant ce chantier n'en ont pas, et sont ignorés
    ici plutôt que de fausser une moyenne avec des zéros).

    "Horaire moyen" : moyenne arithmétique simple des minutes depuis
    minuit à partir de cree_le (heure locale du serveur, Europe/Paris —
    voir CLAUDE.md). Pas une moyenne circulaire : pour un réseau qui ne
    fonctionne que le jour, c'est largement suffisant, et beaucoup plus
    simple à lire pour l'équipe CRC."""
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT cree_le, duree_secs, cout_usd, outils_utilises FROM appels "
        "WHERE duree_secs IS NOT NULL"
    ).fetchall()
    conn.close()

    if not lignes:
        return {
            "nb_avec_tracabilite": 0, "duree_moyenne_secs": None,
            "horaire_moyen": None, "cout_total_usd": None,
            "repartition_outils": {},
        }

    durees = [l["duree_secs"] for l in lignes]
    couts = [l["cout_usd"] for l in lignes if l["cout_usd"] is not None]

    minutes_depuis_minuit = []
    for l in lignes:
        try:
            heure, minute = l["cree_le"][11:16].split(":")
            minutes_depuis_minuit.append(int(heure) * 60 + int(minute))
        except (ValueError, IndexError):
            continue

    repartition = {}
    for l in lignes:
        if not l["outils_utilises"]:
            continue
        for outil in json.loads(l["outils_utilises"]):
            repartition[outil] = repartition.get(outil, 0) + 1

    horaire_moyen = None
    if minutes_depuis_minuit:
        m = round(sum(minutes_depuis_minuit) / len(minutes_depuis_minuit))
        horaire_moyen = f"{m // 60:02d}h{m % 60:02d}"

    return {
        "nb_avec_tracabilite": len(lignes),
        "duree_moyenne_secs": round(sum(durees) / len(durees)),
        "horaire_moyen": horaire_moyen,
        "cout_total_usd": round(sum(couts), 4) if couts else None,
        "repartition_outils": repartition,
    }


def obtenir_appel(appel_id):
    conn = connexion_app()
    ligne = conn.execute("SELECT * FROM appels WHERE id = ?", (appel_id,)).fetchone()
    conn.close()
    return dict(ligne) if ligne else None


def enregistrer_evaluation(appel_id, qualite, note=None):
    """qualite vaut 'bonne' ou 'mauvaise'. N'écrase jamais un avis
    précédent : chaque évaluation s'ajoute à l'historique de l'appel."""
    conn = connexion_app()
    conn.execute(
        "INSERT INTO evaluations_appels (appel_id, cree_le, qualite, note) VALUES (?, ?, ?, ?)",
        (appel_id, horodatage(), qualite, note or None),
    )
    conn.commit()
    conn.close()


def lister_evaluations(appel_id):
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT cree_le, qualite, note FROM evaluations_appels "
        "WHERE appel_id = ? ORDER BY id DESC",
        (appel_id,),
    ).fetchall()
    conn.close()
    return [dict(l) for l in lignes]
