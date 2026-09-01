"""Préproduction : identique à la production, sauf le domaine et les données."""

from .prod import *  # noqa: F403

# La préproduction ne doit jamais être indexée.
X_ROBOTS_TAG = "noindex, nofollow"
