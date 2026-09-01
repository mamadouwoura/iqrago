"""Droits d'accès au contenu.

**Point d'extension du futur service d'`Entitlement`** (D3). Aujourd'hui la
règle est simple et réelle : les jours 1 à 3 sont ouverts, le reste ne l'est
pas encore parce qu'aucun moyen de payer n'existe.

Ce n'est pas une simulation — un compte ordinaire se heurte vraiment au jour 4.
Quand la facturation arrivera, seule `peut_acceder` change : elle interrogera
`Entitlement` au lieu de regarder `is_free`. Rien d'autre dans le code produit
n'a connaissance des droits, ce qui est précisément le but.
"""


def peut_acceder(user, lecon):
    """L'utilisateur a-t-il accès à cette leçon ?"""
    if user.is_staff:
        # L'équipe doit pouvoir relire tout le parcours sans acheter.
        return True
    return lecon.is_free


def motif_refus(lecon):
    return {
        "code": "entitlement_required",
        "message": "Cette leçon fait partie du programme complet.",
        "details": {"feature": f"{lecon.course_id}", "day": lecon.day_number},
    }
