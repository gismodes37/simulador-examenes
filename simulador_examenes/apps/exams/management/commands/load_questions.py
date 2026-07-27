"""
Management command to load exam questions from JSON files.

Usage:
    python manage.py load_questions --file data/sample_questions.json
    python manage.py load_questions --all
    python manage.py load_questions --all --dry-run
    python manage.py load_questions --all --verbose
"""

import glob
import json
import os
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.exams.models import Area, Category, Question

# Map JSON category codes to exam structure details.
# Based on SUBTEL official exam structure (Resolución 2620)
# exam_size = reglamento_count + tecnica_count
CATEGORY_CONFIG = {
    "CD": {
        "name": "Aspirante",
        "exam_size": 30,
        "reglamento_count": 18,
        "tecnica_count": 12,
    },
    "CA": {
        "name": "Novicio",
        "exam_size": 30,
        "reglamento_count": 15,
        "tecnica_count": 15,
    },
    "CE": {
        "name": "General",
        "exam_size": 30,
        "reglamento_count": 12,
        "tecnica_count": 18,
    },
    "XQ": {
        "name": "Superior",
        "exam_size": 30,
        "reglamento_count": 6,
        "tecnica_count": 24,
    },
}

REQUIRED_FIELDS = ["text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]
VALID_ANSWERS = {"A", "B", "C", "D"}
VALID_CATEGORIES = set(CATEGORY_CONFIG.keys())
VALID_AREAS = {"Reglamento", "Tecnica"}


class Command(BaseCommand):
    help = "Load exam questions from JSON files into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Path to a specific JSON file to import.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="import_all",
            help="Import all JSON files from the data/ directory.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the JSON file(s) without saving to the database.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each question processed.",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        import_all = options["import_all"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        if not file_path and not import_all:
            raise CommandError("Either --file or --all is required.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE — no data will be saved."))

        # Collect files to process
        if import_all:
            base_dir = Path(__file__).resolve().parents[5]  # project root
            data_dir = base_dir / "data"
            if not data_dir.exists():
                raise CommandError(f"Data directory not found: {data_dir}")
            files = sorted(glob.glob(str(data_dir / "*.json")))
            if not files:
                self.stdout.write(self.style.WARNING(f"No JSON files found in {data_dir}"))
                return
            self.stdout.write(f"Found {len(files)} JSON file(s) in {data_dir}")
        else:
            if not os.path.isfile(file_path):
                raise CommandError(f"File not found: {file_path}")
            files = [file_path]

        total_imported = 0
        total_skipped = 0
        total_errors = 0

        for fpath in files:
            self.stdout.write(f"\n--- Processing: {fpath} ---")
            imported, skipped, errors = self._process_file(
                fpath, dry_run=dry_run, verbose=verbose
            )
            total_imported += imported
            total_skipped += skipped
            total_errors += errors

        # Summary
        self.stdout.write("\n" + "=" * 50)
        mode = "DRY RUN" if dry_run else "IMPORT"
        self.stdout.write(f"[{mode}] Complete:")
        self.stdout.write(f"  Imported:  {total_imported}")
        self.stdout.write(f"  Skipped:   {total_skipped}")
        self.stdout.write(f"  Errors:    {total_errors}")

    def _process_file(self, fpath, dry_run=False, verbose=False):
        """Process a single JSON file. Returns (imported, skipped, errors)."""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f"Invalid JSON in {fpath}: {e}"))
            return 0, 0, 1
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading {fpath}: {e}"))
            return 0, 0, 1

        # Validate top-level structure
        category_code = data.get("category")
        area_name = data.get("area")
        questions = data.get("questions")

        errors = 0
        if not category_code:
            self.stderr.write(self.style.ERROR(f"Missing 'category' field in {fpath}"))
            errors += 1
        elif category_code not in VALID_CATEGORIES:
            self.stderr.write(
                self.style.ERROR(
                    f"Invalid category '{category_code}' in {fpath}. "
                    f"Valid: {', '.join(sorted(VALID_CATEGORIES))}"
                )
            )
            errors += 1

        if not area_name:
            self.stderr.write(self.style.ERROR(f"Missing 'area' field in {fpath}"))
            errors += 1
        elif area_name not in VALID_AREAS:
            self.stderr.write(
                self.style.ERROR(
                    f"Invalid area '{area_name}' in {fpath}. "
                    f"Valid: {', '.join(sorted(VALID_AREAS))}"
                )
            )
            errors += 1

        if not questions or not isinstance(questions, list):
            self.stderr.write(
                self.style.ERROR(f"Missing or empty 'questions' array in {fpath}")
            )
            errors += 1

        if errors:
            return 0, 0, errors

        if dry_run:
            # Validate all questions without saving
            return self._validate_questions(
                questions, category_code, area_name, verbose
            )

        return self._import_questions(questions, category_code, area_name, verbose)

    def _validate_questions(self, questions, category_code, area_name, verbose):
        """Validate questions without saving. Returns (valid, skipped, errors)."""
        valid = 0
        skipped = 0
        for i, q in enumerate(questions, 1):
            is_valid, reason = self._validate_question(q)
            if is_valid:
                valid += 1
                if verbose:
                    self.stdout.write(f"  [OK] Q{i}: {q['text'][:60]}...")
            else:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] Q{i}: {reason}")
                )
                if verbose:
                    self.stdout.write(f"    Text: {q.get('text', '<missing>')[:80]}")
        return valid, skipped, 0

    def _import_questions(self, questions, category_code, area_name, verbose):
        """Import questions into DB. Returns (imported, skipped, errors)."""
        # Ensure category and area exist
        cat_config = CATEGORY_CONFIG[category_code]
        category, _ = Category.objects.get_or_create(
            code=category_code,
            defaults={
                "name": cat_config["name"],
                "exam_size": cat_config["exam_size"],
                "reglamento_count": cat_config["reglamento_count"],
                "tecnica_count": cat_config["tecnica_count"],
            },
        )
        area, _ = Area.objects.get_or_create(name=area_name)

        imported = 0
        skipped = 0
        for i, q in enumerate(questions, 1):
            is_valid, reason = self._validate_question(q)
            if not is_valid:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  [SKIP] Q{i}: {reason}"))
                continue

            try:
                obj, created = Question.objects.update_or_create(
                    text=q["text"].strip(),
                    category=category,
                    area=area,
                    defaults={
                        "option_a": q["option_a"].strip(),
                        "option_b": q["option_b"].strip(),
                        "option_c": q["option_c"].strip(),
                        "option_d": q["option_d"].strip(),
                        "correct_answer": q["correct_answer"].upper().strip(),
                        "explanation": q.get("explanation", "").strip(),
                    },
                )
                if created:
                    imported += 1
                    if verbose:
                        self.stdout.write(f"  [CREATED] Q{i}: {obj.text[:60]}...")
                else:
                    if verbose:
                        self.stdout.write(f"  [UPDATED] Q{i}: {obj.text[:60]}...")
            except Exception as e:
                skipped += 1
                self.stderr.write(
                    self.style.ERROR(f"  [ERROR] Q{i}: {e}")
                )

        self.stdout.write(
            f"  Results: {imported} created, {skipped} skipped "
            f"(total {imported + skipped} processed)"
        )
        return imported, skipped, 0

    @staticmethod
    def _validate_question(q):
        """Validate a single question dict. Returns (is_valid, reason)."""
        if not isinstance(q, dict):
            return False, "Question is not a dict"

        for field in REQUIRED_FIELDS:
            val = q.get(field)
            if not val or not str(val).strip():
                return False, f"Missing or empty required field: {field}"

        correct = q["correct_answer"].strip().upper()
        if correct not in VALID_ANSWERS:
            return False, f"Invalid correct_answer: '{q['correct_answer']}' (must be A/B/C/D)"

        return True, ""
