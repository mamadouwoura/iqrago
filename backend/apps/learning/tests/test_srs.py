"""Répétition espacée.

Testée sans base ni interface : c'est de l'arithmétique de dates, et c'est
la partie du produit qu'on peut casser le plus longtemps sans s'en apercevoir.
"""

from datetime import date, timedelta

import pytest

from apps.learning import srs
from apps.learning.models import MasteryState

N = MasteryState.Level
AUJ = date(2026, 9, 1)


# ------------------------------------------------------------- transitions


@pytest.mark.parametrize(
    "avant,juste,hesitation,attendu",
    [
        (N.INCONNUE, True, False, N.DECOUVERTE),
        (N.DECOUVERTE, True, False, N.FRAGILE),
        (N.FRAGILE, True, False, N.SOLIDE),
        (N.SOLIDE, True, False, N.ACQUISE),
        (N.ACQUISE, True, False, N.ACQUISE),          # plafond
        (N.SOLIDE, True, True, N.SOLIDE),             # juste mais lent : on ne monte pas
        (N.ACQUISE, False, False, N.SOLIDE),
        (N.DECOUVERTE, False, False, N.DECOUVERTE),   # plancher
        (N.INCONNUE, False, False, N.DECOUVERTE),
    ],
)
def test_niveau_suivant(avant, juste, hesitation, attendu):
    assert srs.niveau_suivant(avant, juste, hesitation) == attendu


def test_juste_mais_lent_ne_fait_pas_monter():
    """Le mécanisme qui produit de la fluidité au lieu d'une simple exactitude.

    Sans lui, on entraîne des gens qui répondent bien en cinq secondes —
    c'est-à-dire qui épellent encore."""
    m = MasteryState(level=N.FRAGILE)
    avant, apres, hesitation = srs.appliquer(
        m, juste=True, latence_ms=4000, seuil_ms=2000, aujourdhui=AUJ
    )
    assert hesitation and avant == apres == N.FRAGILE
    assert m.due_at == AUJ + timedelta(days=1), "une hésitation revient demain"


def test_juste_et_rapide_fait_monter_et_espace():
    m = MasteryState(level=N.FRAGILE)
    _, apres, hesitation = srs.appliquer(
        m, juste=True, latence_ms=900, seuil_ms=2000, aujourdhui=AUJ, alea=0
    )
    assert not hesitation and apres == N.SOLIDE
    assert m.due_at == AUJ + timedelta(days=4)


def test_echec_redescend_et_revient_demain():
    m = MasteryState(level=N.ACQUISE)
    _, apres, _ = srs.appliquer(m, juste=False, latence_ms=900, seuil_ms=2000, aujourdhui=AUJ)
    assert apres == N.SOLIDE
    assert m.due_at == AUJ + timedelta(days=1)


# -------------------------------------------------------------- intervalles


@pytest.mark.parametrize(
    "niveau,jours", [(N.DECOUVERTE, 1), (N.FRAGILE, 2), (N.SOLIDE, 4), (N.ACQUISE, 8)]
)
def test_intervalles(niveau, jours):
    assert srs.prochaine_echeance(niveau, AUJ, alea=0) == AUJ + timedelta(days=jours)


def test_niveau_inconnu_na_pas_decheance():
    assert srs.prochaine_echeance(N.INCONNUE, AUJ) is None


def test_gigue_reste_dans_les_bornes():
    """±10 % : sans cela, toutes les cartes d'un même jour reviennent
    ensemble, et la séance du jour 9 déborde pendant que celle du jour 10
    est vide."""
    echeances = {srs.prochaine_echeance(N.ACQUISE, AUJ) for _ in range(200)}
    jours = sorted((e - AUJ).days for e in echeances)
    assert jours[0] >= 7 and jours[-1] <= 9


def test_echeance_jamais_dans_le_passe():
    for niveau in (N.DECOUVERTE, N.FRAGILE, N.SOLIDE, N.ACQUISE):
        for _ in range(50):
            assert srs.prochaine_echeance(niveau, AUJ) > AUJ


# ---------------------------------------------------------------- compteurs


def test_compteurs_et_latence_moyenne():
    m = MasteryState(level=N.INCONNUE)
    for latence in (1000, 2000, 3000):
        srs.appliquer(m, juste=True, latence_ms=latence, seuil_ms=5000, aujourdhui=AUJ)
    assert m.seen_count == 3 and m.correct_count == 3 and m.hesitation_count == 0
    assert 1000 <= m.avg_latency_ms <= 3000


def test_hesitations_comptees_separement():
    m = MasteryState(level=N.FRAGILE)
    srs.appliquer(m, juste=True, latence_ms=9000, seuil_ms=2000, aujourdhui=AUJ)
    assert m.correct_count == 1 and m.hesitation_count == 1


# ------------------------------------------- la première rencontre est lente


def test_premiere_rencontre_lente_fait_quand_meme_monter():
    """Découvrir une lettre est nécessairement lent.

    Pénaliser cette lenteur-là bloquerait l'apprenant au niveau 0
    indéfiniment : il ne peut pas répondre vite à ce qu'il voit pour la
    première fois. Le seuil mesure l'automatisation — une notion qui n'a de
    sens que sur ce qu'on connaît déjà.

    Défaut trouvé en jouant une vraie séance dans l'application : dix
    secondes de réponse, et la maîtrise restait à 0.
    """
    m = MasteryState(level=N.INCONNUE)
    _, apres, hesitation = srs.appliquer(
        m, juste=True, latence_ms=10_000, seuil_ms=1500, aujourdhui=AUJ
    )
    assert hesitation, "la lenteur est bien constatée"
    assert apres == N.DECOUVERTE, "mais elle ne bloque pas la découverte"


def test_lenteur_penalisee_des_le_niveau_1():
    """Au-delà de la découverte, la règle reprend : c'est là qu'elle produit
    de la fluidité au lieu d'une simple exactitude."""
    m = MasteryState(level=N.DECOUVERTE)
    _, apres, _ = srs.appliquer(
        m, juste=True, latence_ms=10_000, seuil_ms=1500, aujourdhui=AUJ
    )
    assert apres == N.DECOUVERTE, "juste mais lent ne fait pas monter"
