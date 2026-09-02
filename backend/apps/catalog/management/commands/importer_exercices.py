"""Importe les brouillons d'exercices de `content/exercices/` vers la base.

    python manage.py importer_exercices [--auteur email] [--dry-run]

Un lot par jour de parcours : « Jour 08 — La famille ٮ » contient la trentaine
d'exercices introduits ce jour-là, se relit d'une traite et se publie d'un
seul tenant. C'est l'unité de relecture (§47) — valider 888 exercices un par
un est impraticable.

**Tout entre à l'état de brouillon.** Rien n'est publié par cette commande :
la publication exige une relecture puis une validation par un tiers, et la
machine à états de `ContentVersion` le refuse autrement.

Idempotent : l'identifiant de chaque exercice est dérivé de son contenu, et le
générateur étant déterministe, réimporter mille fois n'écrit qu'une version.
"""

import json
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import ContentVersion, Exercise, Lesson, Skill

User = get_user_model()

# Espace de noms fixe : le même exercice produit toujours le même UUID, sur
# tous les environnements. Sans cela l'import créerait des doublons en
# préproduction et en production.
NAMESPACE = uuid.UUID("6a1f0c3e-0000-4000-8000-000000000001")


def identifiant(skill_id, type_, rang):
    """UUID stable, dérivé du contenu plutôt que tiré au hasard."""
    return uuid.uuid5(NAMESPACE, f"{skill_id}|{type_}|{rang}")


class Command(BaseCommand):
    help = "Importe content/exercices/jour-*.json comme brouillons relisibles."

    def add_arguments(self, parser):
        parser.add_argument("--auteur", help="E-mail de l'auteur des lots (défaut : "
                                             "premier compte d'équipe).")
        parser.add_argument("--dry-run", action="store_true", help="Compte sans écrire.")

    def handle(self, *args, **options):
        dossier = Path(__file__).resolve().parents[5] / "content" / "exercices"
        fichiers = sorted(dossier.glob("jour-*.json")) if dossier.exists() else []

        if not fichiers:
            raise CommandError(
                f"Aucun lot dans {dossier}.\n"
                "Les brouillons ne sont pas versionnés — ils se regénèrent :\n"
                "  dart run tools/contenu/exercices.dart"
            )

        auteur = self._auteur(options.get("auteur"))
        connues = set(Skill.objects.values_list("id", flat=True))
        titres = dict(
            Lesson.objects.filter(course_id="course.1", content_version=None)
            .values_list("day_number", "title_fr")
        )

        total = crees = maj = ignores = 0
        inconnues = set()
        lots_figes = []

        for fichier in fichiers:
            data = json.loads(fichier.read_text(encoding="utf-8"))
            jour, exercices = data["jour"], data["exercices"]
            total += len(exercices)

            titre = titres.get(jour, "")
            label = f"Jour {jour:02d}" + (f" — {titre}" if titre else "")

            if options["dry_run"]:
                continue

            with transaction.atomic():
                version, _ = ContentVersion.objects.get_or_create(
                    label=label, defaults={"author": auteur}
                )
                # Un lot déjà publié est immuable : on ne le réécrit pas, on
                # crée une révision — mais c'est une décision éditoriale, pas
                # le rôle d'un import.
                if version.state == ContentVersion.State.PUBLISHED:
                    lots_figes.append(label)
                    ignores += len(exercices)
                    continue

                rangs = {}
                for e in exercices:
                    skill_id = e["skill_id"]
                    if skill_id not in connues:
                        inconnues.add(skill_id)
                        ignores += 1
                        continue

                    rang = rangs[skill_id] = rangs.get(skill_id, 0) + 1
                    _, cree = Exercise.objects.update_or_create(
                        id=identifiant(skill_id, e["type"], rang),
                        defaults={
                            "skill_id": skill_id,
                            "type": e["type"],
                            "payload": {k: v for k, v in e.items() if k != "skill_id"},
                            "difficulty": min(5, rang),
                            "content_version": version,
                        },
                    )
                    crees += cree
                    maj += 0 if cree else 1

        self.stdout.write("")
        self.stdout.write(f"  lots lus        {len(fichiers)}")
        self.stdout.write(f"  exercices lus   {total}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("  --dry-run : rien écrit."))
            return
        self.stdout.write(f"  créés           {crees}")
        self.stdout.write(f"  mis à jour      {maj}")
        if ignores:
            self.stdout.write(self.style.WARNING(f"  ignorés         {ignores}"))
        if inconnues:
            self.stdout.write(self.style.ERROR(
                f"  compétences inconnues : {', '.join(sorted(inconnues)[:5])}"
                " — regénérer competences.json ?"))
        if lots_figes:
            self.stdout.write(self.style.WARNING(
                f"  lots publiés, laissés intacts : {', '.join(lots_figes)}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{Exercise.objects.count()} exercices en base, tous en brouillon."))
        self.stdout.write("Relecture et publication se font dans l'admin.")

    def _auteur(self, email):
        if email:
            auteur = User.objects.filter(email__iexact=email).first()
            if not auteur:
                raise CommandError(f"Aucun compte avec l'e-mail {email}.")
            return auteur
        auteur = User.objects.filter(is_staff=True).order_by("created_at").first()
        if not auteur:
            raise CommandError(
                "Aucun compte d'équipe pour porter les lots.\n"
                "  python manage.py createsuperuser"
            )
        return auteur
