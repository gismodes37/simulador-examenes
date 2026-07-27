import pytest
from django.contrib.auth import get_user_model

from apps.exams.models import (
    AnswerAttempt,
    Area,
    Category,
    ExamAttempt,
    Question,
    Tema,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def category_cd():
    return Category.objects.create(
        code="CD",
        name="Novicio",
        exam_size=30,
        reglamento_count=15,
        tecnica_count=15,
    )


@pytest.fixture
def category_ca():
    return Category.objects.create(
        code="CA",
        name="General",
        exam_size=50,
        reglamento_count=25,
        tecnica_count=25,
    )


@pytest.fixture
def category_ce():
    return Category.objects.create(
        code="CE",
        name="Superior",
        exam_size=80,
        reglamento_count=40,
        tecnica_count=40,
    )


@pytest.fixture
def category_xq():
    return Category.objects.create(
        code="XQ",
        name="Experimental",
        exam_size=50,
        reglamento_count=25,
        tecnica_count=25,
    )


@pytest.fixture
def area_reglamento():
    return Area.objects.create(name="Reglamento")


@pytest.fixture
def area_tecnica():
    return Area.objects.create(name="Tecnica")


@pytest.fixture
def tema_reglamento(area_reglamento, category_ce):
    return Tema.objects.create(
        name="Normativa General",
        area=area_reglamento,
        category=category_ce,
    )


@pytest.fixture
def sample_question(category_ce, area_reglamento):
    return Question.objects.create(
        text="¿Cuál es la impedancia característica más común?",
        option_a="25 ohm",
        option_b="50 ohm",
        option_c="75 ohm",
        option_d="300 ohm",
        correct_answer="B",
        explanation="La mayoría de equipos utilizan sistemas de 50 ohm.",
        category=category_ce,
        area=area_reglamento,
    )


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        callsign="XQ1TEST",
        is_radio_amateur=True,
    )


# ---------------------------------------------------------------------------
# Category Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCategory:
    def test_create_all_categories(
        self, category_cd, category_ca, category_ce, category_xq
    ):
        categories = Category.objects.all()
        assert categories.count() == 4
        codes = set(categories.values_list("code", flat=True))
        assert codes == {"CD", "CA", "CE", "XQ"}

    def test_category_str(self, category_ce):
        assert str(category_ce) == "CE - Superior"

    def test_category_ordering(self, category_ce, category_cd, category_ca):
        categories = list(Category.objects.all())
        assert categories[0].code == "CA"
        assert categories[1].code == "CD"
        assert categories[2].code == "CE"

    def test_category_code_unique(self, category_cd):
        with pytest.raises(Exception):
            Category.objects.create(
                code="CD",
                name="Duplicate",
                exam_size=30,
                reglamento_count=15,
                tecnica_count=15,
            )

    def test_category_fields(self, category_ce):
        assert category_ce.exam_size == 80
        assert category_ce.reglamento_count == 40
        assert category_ce.tecnica_count == 40


# ---------------------------------------------------------------------------
# Area Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestArea:
    def test_create_areas(self, area_reglamento, area_tecnica):
        assert Area.objects.count() == 2
        names = set(Area.objects.values_list("name", flat=True))
        assert names == {"Reglamento", "Tecnica"}

    def test_area_str(self, area_reglamento):
        assert str(area_reglamento) == "Reglamento"

    def test_area_unique(self, area_reglamento):
        with pytest.raises(Exception):
            Area.objects.create(name="Reglamento")


# ---------------------------------------------------------------------------
# Tema Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTema:
    def test_create_tema(self, tema_reglamento, area_reglamento, category_ce):
        assert tema_reglamento.name == "Normativa General"
        assert tema_reglamento.area == area_reglamento
        assert tema_reglamento.category == category_ce
        assert str(tema_reglamento) == "Normativa General (Reglamento - CE)"

    def test_tema_unique_together(self, tema_reglamento, area_reglamento, category_ce):
        with pytest.raises(Exception):
            Tema.objects.create(
                name="Normativa General",
                area=area_reglamento,
                category=category_ce,
            )

    def test_tema_cascade_area(self, tema_reglamento, area_reglamento):
        area_reglamento.delete()
        assert Tema.objects.count() == 0

    def test_tema_cascade_category(self, tema_reglamento, category_ce):
        category_ce.delete()
        assert Tema.objects.count() == 0


# ---------------------------------------------------------------------------
# Question Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuestion:
    def test_create_question(self, sample_question):
        assert sample_question.pk is not None
        assert sample_question.text == "¿Cuál es la impedancia característica más común?"
        assert sample_question.correct_answer == "B"
        assert sample_question.is_active is True

    def test_question_str(self, sample_question):
        result = str(sample_question)
        assert result.startswith("Q")
        assert "impedancia" in result.lower()

    def test_question_filter_by_category_and_area(
        self, sample_question, category_cd, area_tecnica
    ):
        # Create a question in a different category/area
        Question.objects.create(
            text="Pregunta técnica diferente",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            category=category_cd,
            area=area_tecnica,
        )

        ce_reglamento = Question.objects.filter(
            category=sample_question.category,
            area=sample_question.area,
        )
        assert ce_reglamento.count() == 1
        assert ce_reglamento.first().pk == sample_question.pk

    def test_question_answer_choices(self):
        valid = {c[0] for c in Question.ANSWER_CHOICES}
        assert valid == {"A", "B", "C", "D"}

    def test_question_default_is_active(self, category_ce, area_reglamento):
        q = Question.objects.create(
            text="Test active default",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            category=category_ce,
            area=area_reglamento,
        )
        assert q.is_active is True

    def test_question_explanation_optional(self, category_ce, area_reglamento):
        q = Question.objects.create(
            text="Test no explanation",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            category=category_ce,
            area=area_reglamento,
        )
        assert q.explanation == ""


# ---------------------------------------------------------------------------
# ExamAttempt Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExamAttempt:
    def test_create_exam_attempt(self, user, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user,
            category=category_ce,
            mode="exam",
        )
        assert attempt.pk is not None
        assert attempt.user == user
        assert attempt.category == category_ce
        assert attempt.mode == "exam"
        assert attempt.started_at is not None
        assert attempt.finished_at is None
        assert attempt.score is None

    def test_create_training_attempt(self, user, category_cd):
        attempt = ExamAttempt.objects.create(
            user=user,
            category=category_cd,
            mode="training",
        )
        assert attempt.mode == "training"

    def test_exam_attempt_str(self, user, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user,
            category=category_ce,
            mode="exam",
        )
        result = str(attempt)
        assert "testuser" in result
        assert "CE" in result

    def test_exam_attempt_anonymous(self, category_ce):
        attempt = ExamAttempt.objects.create(
            category=category_ce,
            mode="exam",
        )
        result = str(attempt)
        assert "Anonymous" in result

    def test_exam_attempt_ordering(self, user, category_ce, category_cd):
        a1 = ExamAttempt.objects.create(
            user=user, category=category_cd, mode="exam"
        )
        a2 = ExamAttempt.objects.create(
            user=user, category=category_ce, mode="exam"
        )
        attempts = list(ExamAttempt.objects.all())
        # Ordered by -started_at, so a2 (created later) should be first
        assert attempts[0].pk == a2.pk


# ---------------------------------------------------------------------------
# AnswerAttempt Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAnswerAttempt:
    def test_create_answer_attempt(self, user, sample_question, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user,
            category=category_ce,
            mode="exam",
        )
        answer = AnswerAttempt.objects.create(
            exam_attempt=attempt,
            question=sample_question,
            selected_answer="B",
            is_correct=True,
            time_spent_seconds=15,
        )
        assert answer.pk is not None
        assert answer.is_correct is True
        assert answer.selected_answer == "B"
        assert answer.time_spent_seconds == 15

    def test_answer_attempt_str_correct(self, user, sample_question, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user, category=category_ce, mode="exam"
        )
        answer = AnswerAttempt.objects.create(
            exam_attempt=attempt,
            question=sample_question,
            selected_answer="B",
            is_correct=True,
        )
        result = str(answer)
        assert "OK" in result

    def test_answer_attempt_str_wrong(self, user, sample_question, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user, category=category_ce, mode="exam"
        )
        answer = AnswerAttempt.objects.create(
            exam_attempt=attempt,
            question=sample_question,
            selected_answer="A",
            is_correct=False,
        )
        result = str(answer)
        assert "WRONG" in result

    def test_answer_attempt_unique_together(
        self, user, sample_question, category_ce
    ):
        attempt = ExamAttempt.objects.create(
            user=user, category=category_ce, mode="exam"
        )
        AnswerAttempt.objects.create(
            exam_attempt=attempt,
            question=sample_question,
            selected_answer="B",
            is_correct=True,
        )
        with pytest.raises(Exception):
            AnswerAttempt.objects.create(
                exam_attempt=attempt,
                question=sample_question,
                selected_answer="C",
                is_correct=False,
            )

    def test_answer_attempt_cascade_delete(self, user, sample_question, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user, category=category_ce, mode="exam"
        )
        AnswerAttempt.objects.create(
            exam_attempt=attempt,
            question=sample_question,
            selected_answer="B",
            is_correct=True,
        )
        attempt.delete()
        assert AnswerAttempt.objects.count() == 0

    def test_answer_attempt_default_time(self, user, sample_question, category_ce):
        attempt = ExamAttempt.objects.create(
            user=user, category=category_ce, mode="exam"
        )
        answer = AnswerAttempt.objects.create(
            exam_attempt=attempt,
            question=sample_question,
            selected_answer="B",
            is_correct=True,
        )
        assert answer.time_spent_seconds == 0
