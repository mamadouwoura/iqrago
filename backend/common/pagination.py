"""Pagination par curseur.

Curseur et non `offset` : les listes bougent sous la pagination — une nouvelle
tentative, un consentement retiré — et un `offset` fait alors sauter ou
répéter des éléments entre deux pages.

DRF trie par défaut sur un champ `created` que nos modèles n'ont pas : ils
portent `created_at` (voir `common.models.TimeStampedModel`).
"""

from rest_framework.pagination import CursorPagination


class CurseurParDate(CursorPagination):
    ordering = "-created_at"
    page_size = 50
    max_page_size = 200
    page_size_query_param = "taille"
