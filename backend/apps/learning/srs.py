"""Répétition espacée.

Règles fixes, pas de SM-2 ni de FSRS (D7). Ces algorithmes ajustent une
facilité par carte à partir de l'historique et ont besoin de 6 à 10 révisions
pour se stabiliser ; un parcours de trente jours en donne 4 à 6. Ils
produiraient du bruit, pas de la personnalisation.
"""

import random
from datetime import timedelta

from django.utils import timezone

from .models import MasteryState

NIVEAU_MIN_APRES_ECHEC = MasteryState.Level.DECOUVERTE
NIVEAU_MAX = MasteryState.Level.ACQUISE

# Jours avant la prochaine révision, par niveau atteint.
INTERVALLES = {
    MasteryState.Level.INCONNUE: None,
    MasteryState.Level.DECOUVERTE: 1,
    MasteryState.Level.FRAGILE: 2,
    MasteryState.Level.SOLIDE: 4,
    MasteryState.Level.ACQUISE: 8,
}

# ±10 % : sans cela, toutes les cartes vues le même jour reviennent le même
# jour, et la séance du jour 9 déborde pendant que celle du jour 10 est vide.
GIGUE = 0.10


def prochaine_echeance(niveau, aujourdhui=None, alea=None):
    jours = INTERVALLES[niveau]
    if jours is None:
        return None
    aujourdhui = aujourdhui or timezone.localdate()
    alea = random.uniform(-GIGUE, GIGUE) if alea is None else alea
    return aujourdhui + timedelta(days=max(1, round(jours * (1 + alea))))


def est_hesitation(latence_ms, seuil_ms):
    """Juste, mais au-delà du seuil d'automatisation.

    C'est la mesure qui distingue « je sais lire » de « je sais déchiffrer ».
    Sans elle, on entraîne des gens qui répondent bien en cinq secondes —
    c'est-à-dire qui épellent encore.
    """
    return latence_ms > seuil_ms


def niveau_suivant(niveau_actuel, juste, hesitation):
    """Transition. Trois issues, pas deux."""
    if not juste:
        return max(NIVEAU_MIN_APRES_ECHEC, niveau_actuel - 1)
    if hesitation:
        # Juste mais lent : on ne monte pas. La carte revient demain.
        return niveau_actuel
    return min(NIVEAU_MAX, niveau_actuel + 1)


def appliquer(maitrise, *, juste, latence_ms, seuil_ms, aujourdhui=None, alea=None):
    """Met à jour une maîtrise d'après une réponse. Ne sauvegarde pas."""
    aujourdhui = aujourdhui or timezone.localdate()
    hesitation = juste and est_hesitation(latence_ms, seuil_ms)
    avant = maitrise.level
    apres = niveau_suivant(avant, juste, hesitation)

    maitrise.level = apres
    if juste and not hesitation:
        maitrise.due_at = prochaine_echeance(apres, aujourdhui, alea)
    else:
        # Échec ou hésitation : retour demain, quel que soit le niveau.
        # Une carte ratée ne revient JAMAIS immédiatement — réussir dix
        # secondes après un échec ne teste que la mémoire de travail.
        maitrise.due_at = aujourdhui + timedelta(days=1)

    maitrise.seen_count += 1
    maitrise.correct_count += 1 if juste else 0
    maitrise.hesitation_count += 1 if hesitation else 0
    # Moyenne glissante sur cinq : suit le progrès sans être dominée par les
    # premières tentatives, forcément lentes.
    n = min(maitrise.seen_count, 5)
    maitrise.avg_latency_ms = round(
        (maitrise.avg_latency_ms * (n - 1) + latence_ms) / n
    ) if n > 1 else latence_ms
    maitrise.last_seen_at = timezone.now()

    return avant, apres, hesitation
