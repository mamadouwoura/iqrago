"""Importe le socle pédagogique de `content/` vers la base.

    python manage.py importer_contenu [--dry-run]

Idempotent : réexécutable sans créer de doublon. C'est ce qui permet de
retravailler les fichiers source et de réimporter sans repartir de zéro.

Les fichiers de `content/` restent la source de vérité tant que l'admin n'a
pas pris le relais. Une fois que la personne en charge du contenu travaille
dans l'admin, c'est la base qui fait foi et cette commande ne sert plus qu'à
l'amorçage d'un environnement neuf.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Course, Lesson, Media, Module, Skill, SkillPrerequisite

COURSE = {
    "code": "course.1",
    "title_fr": "Apprendre à lire l'arabe",
    "description_fr": (
        "Parcours intensif. Reconnaître les lettres, maîtriser les accents, "
        "assembler, puis lire."
    ),
    "order": 1,
}

# Variante B (D6) : les six lettres qui ne se lient jamais d'abord, pour lire
# un vrai mot dès le jour 3 sans forme positionnelle.
MODULES = [
    ("m1.noyau",      "Le noyau libre",             1,  7),
    ("m2.familles",   "Les familles connectées",    8,  14),
    ("m3.dernieres",  "Les dernières familles",     15, 18),
    ("m4.sukun",      "Sukun et prolongations",     19, 21),
    ("m5.shadda",     "Shadda, tanwin et article",  22, 24),
    ("m6.mots",       "Mots et phrases",            25, 27),
    ("m7.fluidite",   "Paragraphes et fluidité",    28, 29),
    ("m8.evaluation", "Évaluation finale",          30, 30),
]

TITRES = {
    1: "Deux formes, un point", 2: "Deux nouvelles formes libres",
    3: "Le premier mot", 4: "La bouche s'étire", 5: "Les lèvres s'arrondissent",
    6: "Consolidation", 7: "Respiration",
    8: "La famille ٮ", 9: "La famille ح", 10: "La famille س",
    11: "ل et م", 12: "ن et ي", 13: "ك et ه", 14: "Respiration",
    15: "ع et غ", 16: "ف et ق", 17: "ص et ض", 18: "ط et ظ",
    19: "Sukun", 20: "Les prolongations", 21: "Douces et emphatiques",
    22: "Shadda", 23: "Tanwin", 24: "L'article défini",
    25: "Mots", 26: "Phrases courtes", 27: "Phrases",
    28: "Paragraphes", 29: "Fluidité", 30: "Évaluation finale",
}

REPOS = {7, 14, 21}


class Command(BaseCommand):
    help = "Importe content/*.json (parcours, modules, compétences, leçons, médias)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Analyse et compte, sans rien écrire.")

    def handle(self, *args, **options):
        racine = Path(__file__).resolve().parents[5] / "content"
        if not racine.exists():
            raise CommandError(f"Dossier introuvable : {racine}")

        competences = self._lire(racine / "competences.json")["competences"]
        manifeste = self._lire(racine / "audio-manifeste.json")["audios"]

        if options["dry_run"]:
            self.stdout.write(f"{len(competences)} compétences, {len(manifeste)} médias.")
            self.stdout.write(self.style.WARNING("--dry-run : rien écrit."))
            return

        with transaction.atomic():
            course = self._parcours()
            modules = self._modules(course)
            n_skills, n_prereq = self._competences(course, competences)
            n_lecons = self._lecons(course, modules)
            n_medias = self._medias(manifeste)

        self.stdout.write("")
        for libelle, n in [
            ("parcours", 1), ("modules", len(modules)), ("compétences", n_skills),
            ("prérequis", n_prereq), ("leçons", n_lecons), ("médias", n_medias),
        ]:
            self.stdout.write(f"  {libelle:14} {n}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import terminé."))

    # ---------------------------------------------------------------- lecture

    def _lire(self, chemin):
        if not chemin.exists():
            raise CommandError(
                f"{chemin.name} manquant. Générer avec :\n"
                f"  dart run tools/contenu/contenu.dart generer"
            )
        return json.loads(chemin.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- écriture

    def _parcours(self):
        course, _ = Course.objects.update_or_create(
            code=COURSE["code"],
            defaults={k: v for k, v in COURSE.items() if k != "code"},
        )
        return course

    def _modules(self, course):
        modules = {}
        for ordre, (code, titre, debut, fin) in enumerate(MODULES, start=1):
            module, _ = Module.objects.update_or_create(
                code=code,
                defaults={"course": course, "title_fr": titre, "order": ordre,
                          "day_start": debut, "day_end": fin},
            )
            modules[code] = module
        return modules

    def _competences(self, course, competences):
        # Deux passes : toutes les compétences d'abord, les prérequis ensuite.
        # Un prérequis peut pointer vers une compétence introduite plus tard
        # dans le fichier.
        for c in competences:
            Skill.objects.update_or_create(
                id=c["id"],
                defaults={
                    "course": course,
                    "type": c["type"],
                    "arabic": c.get("arabic") or "",
                    "introduced_on_day": c["introduced_on_day"] or None,
                    "latency_threshold_ms": c["latency_threshold_ms"],
                },
            )

        n_prereq = 0
        for c in competences:
            for requis in c["prerequisites"]:
                _, cree = SkillPrerequisite.objects.get_or_create(
                    skill_id=c["id"], requires_id=requis
                )
                n_prereq += 1 if cree else 0
        return len(competences), SkillPrerequisite.objects.count()

    def _lecons(self, course, modules):
        n = 0
        for jour in range(1, 31):
            module = next(
                m for code, m in modules.items()
                if m.day_start <= jour <= m.day_end
            )
            lecon, _ = Lesson.objects.update_or_create(
                # Cible explicitement la leçon de socle, non versionnée : une
                # fois des révisions créées, plusieurs leçons coexistent pour
                # le même jour et un ciblage sur (parcours, jour) seul
                # deviendrait ambigu.
                course=course, day_number=jour, content_version=None,
                defaults={
                    "module": module,
                    "title_fr": TITRES.get(jour, f"Jour {jour}"),
                    # Les jours 1 à 3 sont gratuits : trois séances complètes
                    # suffisent à ressentir la progression, pas à finir (D4).
                    "is_free": jour <= 3,
                    # Le socle importé est le contenu servi tant qu'aucune version
                    # ne l'a remplacé.
                    "is_live": True,
                    "estimated_minutes": 15,
                },
            )
            # Les nouveautés du jour, d'après l'ordre par défaut des compétences.
            if jour not in REPOS:
                lecon.skills.set(Skill.objects.filter(introduced_on_day=jour))
            n += 1
        return n

    def _medias(self, manifeste):
        for audio in manifeste:
            Media.objects.update_or_create(
                key=audio["fichier"],
                defaults={"kind": Media.Kind.AUDIO_REFERENCE, "bundled": True},
            )
        return Media.objects.count()
