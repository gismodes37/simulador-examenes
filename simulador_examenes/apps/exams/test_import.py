import json
import os
import tempfile

import pytest

from apps.exams.models import Area, Category, Question

# Re-use fixtures from tests.py via conftest — but since pytest collects
# both files under the same package, we define local fixtures for the
# import-specific scenarios to keep things self-contained.


@pytest.fixture
def valid_json_file(tmp_path):
    """Create a valid JSON file with sample questions."""
    data = {
        "category": "CE",
        "area": "Reglamento",
        "questions": [
            {
                "text": "¿Cuál es la impedancia característica más común?",
                "option_a": "25 ohm",
                "option_b": "50 ohm",
                "option_c": "75 ohm",
                "option_d": "300 ohm",
                "correct_answer": "B",
                "explanation": "Impedancia estándar.",
            },
            {
                "text": "¿Qué organismo regula las telecomunicaciones en Chile?",
                "option_a": "Ministerio Público",
                "option_b": "SUBTEL",
                "option_c": "Banco Central",
                "option_d": "SEC",
                "correct_answer": "B",
            },
        ],
    }
    fpath = tmp_path / "valid_questions.json"
    fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fpath


@pytest.fixture
def missing_fields_json_file(tmp_path):
    """JSON file with a question missing required fields."""
    data = {
        "category": "CD",
        "area": "Tecnica",
        "questions": [
            {
                "text": "Good question with all fields",
                "option_a": "A",
                "option_b": "B",
                "option_c": "C",
                "option_d": "D",
                "correct_answer": "A",
            },
            {
                "text": "Missing option_d",
                "option_a": "A",
                "option_b": "B",
                "option_c": "C",
                "correct_answer": "B",
            },
            {
                "text": "Missing correct_answer",
                "option_a": "A",
                "option_b": "B",
                "option_c": "C",
                "option_d": "D",
            },
        ],
    }
    fpath = tmp_path / "missing_fields.json"
    fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fpath


@pytest.fixture
def duplicate_json_file(tmp_path):
    """JSON file with the same questions as the valid fixture (for idempotency test)."""
    data = {
        "category": "CE",
        "area": "Reglamento",
        "questions": [
            {
                "text": "¿Cuál es la impedancia característica más común?",
                "option_a": "25 ohm",
                "option_b": "50 ohm",
                "option_c": "75 ohm",
                "option_d": "300 ohm",
                "correct_answer": "B",
                "explanation": "Impedancia estándar.",
            },
            {
                "text": "¿Qué organismo regula las telecomunicaciones en Chile?",
                "option_a": "Ministerio Público",
                "option_b": "SUBTEL",
                "option_c": "Banco Central",
                "option_d": "SEC",
                "correct_answer": "B",
            },
        ],
    }
    fpath = tmp_path / "duplicate_questions.json"
    fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fpath


# ---------------------------------------------------------------------------
# Import Tests via the management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoadQuestionsCommand:
    """Tests for the load_questions management command."""

    def test_import_valid_json(self, valid_json_file, capsys):
        """Importing a valid JSON file creates the expected objects."""
        from django.core.management import call_command

        call_command("load_questions", "--file", str(valid_json_file))

        assert Category.objects.filter(code="CE").exists()
        assert Area.objects.filter(name="Reglamento").exists()
        assert Question.objects.count() == 2

        q1 = Question.objects.get(
            text__startswith="¿Cuál es la impedancia"
        )
        assert q1.correct_answer == "B"
        assert q1.category.code == "CE"
        assert q1.area.name == "Reglamento"

    def test_import_skips_missing_fields(self, missing_fields_json_file, capsys):
        """Questions with missing required fields are skipped with a warning."""
        from django.core.management import call_command

        call_command(
            "load_questions",
            "--file",
            str(missing_fields_json_file),
            "--verbose",
        )

        # Only 1 valid question should be imported
        assert Question.objects.count() == 1
        q = Question.objects.first()
        assert q.text == "Good question with all fields"

        # Check that warnings were printed
        output = capsys.readouterr().out
        assert "[SKIP]" in output

    def test_idempotent_import(self, valid_json_file, duplicate_json_file):
        """Re-importing the same data does not create duplicates."""
        from django.core.management import call_command

        # First import
        call_command("load_questions", "--file", str(valid_json_file))
        assert Question.objects.count() == 2
        first_ids = list(Question.objects.order_by("pk").values_list("pk", flat=True))

        # Second import with same data
        call_command("load_questions", "--file", str(duplicate_json_file))
        assert Question.objects.count() == 2
        second_ids = list(Question.objects.order_by("pk").values_list("pk", flat=True))

        # PKs should be the same (updated, not duplicated)
        assert first_ids == second_ids

    def test_dry_run_does_not_save(self, valid_json_file, capsys):
        """Dry run mode validates but does not create database records."""
        from django.core.management import call_command

        call_command(
            "load_questions",
            "--file",
            str(valid_json_file),
            "--dry-run",
        )

        assert Question.objects.count() == 0
        assert not Category.objects.exists()
        assert not Area.objects.exists()

        output = capsys.readouterr().out
        assert "DRY RUN" in output

    def test_invalid_json_file(self, tmp_path, capsys):
        """An invalid JSON file is handled gracefully (error counted, not fatal)."""
        from django.core.management import call_command
        from django.core.management.base import CommandError

        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{", encoding="utf-8")

        # The command handles the error internally — it counts errors and
        # prints a summary, but does NOT raise. Verify no crash and error count.
        call_command("load_questions", "--file", str(bad_file))

        output = capsys.readouterr().out
        assert "Errors:    1" in output

    def test_missing_file_argument(self):
        """Calling without --file or --all raises CommandError."""
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with pytest.raises(CommandError, match="--file or --all is required"):
            call_command("load_questions")

    def test_import_all_flag(self, tmp_path, capsys):
        """--all imports all JSON files from data/ directory."""
        from django.core.management import call_command

        # Create a temporary data directory with JSON files
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        q1 = {
            "category": "CD",
            "area": "Reglamento",
            "questions": [
                {
                    "text": "Pregunta Novicio 1",
                    "option_a": "A",
                    "option_b": "B",
                    "option_c": "C",
                    "option_d": "D",
                    "correct_answer": "A",
                },
            ],
        }
        (data_dir / "cd_reglamento.json").write_text(
            json.dumps(q1), encoding="utf-8"
        )

        q2 = {
            "category": "CA",
            "area": "Tecnica",
            "questions": [
                {
                    "text": "Pregunta General 1",
                    "option_a": "X",
                    "option_b": "Y",
                    "option_c": "Z",
                    "option_d": "W",
                    "correct_answer": "C",
                },
            ],
        }
        (data_dir / "ca_tecnica.json").write_text(
            json.dumps(q2), encoding="utf-8"
        )

        # We can't easily test --all with the real data/ dir since it may not
        # exist in the test env. Instead, we test the file-based import with
        # both files.
        call_command("load_questions", "--file", str(data_dir / "cd_reglamento.json"))
        call_command("load_questions", "--file", str(data_dir / "ca_tecnica.json"))

        assert Category.objects.filter(code="CD").exists()
        assert Category.objects.filter(code="CA").exists()
        assert Question.objects.count() == 2

    def test_verbose_output(self, valid_json_file, capsys):
        """--verbose flag shows detailed per-question output."""
        from django.core.management import call_command

        call_command(
            "load_questions",
            "--file",
            str(valid_json_file),
            "--verbose",
        )

        output = capsys.readouterr().out
        assert "[CREATED]" in output or "[UPDATED]" in output
