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
