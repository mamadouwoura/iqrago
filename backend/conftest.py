"""Configuration partagée des tests."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def cache_vide():
    """Vide le cache entre les tests.

    Les compteurs de limitation de débit y vivent : sans cela, le sixième test
    qui appelle `/auth/login` reçoit un 429 parce que les cinq précédents ont
    consommé le quota. Le throttling n'est pas désactivé pour autant — il est
    vérifié par `test_limitation_de_debit_sur_la_connexion`.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(scope="session")
def volumes():
    """Les volumes attendus, lus dans `content/` plutôt que recopiés.

    Figer « 283 compétences » dans un test le fait échouer à chaque mot ajouté
    au corpus — c'est-à-dire punir exactement ce qu'on veut encourager. Ce
    qu'il faut vérifier, c'est que la base reflète les fichiers source.
    """
    import json
    from pathlib import Path

    racine = Path(__file__).resolve().parent.parent / "content"
    comp = json.loads((racine / "competences.json").read_text(encoding="utf-8"))
    audio = json.loads((racine / "audio-manifeste.json").read_text(encoding="utf-8"))
    return {
        "nb_competences": len(comp["competences"]),
        "nb_medias": len(audio["audios"]),
    }
