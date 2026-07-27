from django.conf import settings
from django.db import models


class Category(models.Model):
    """
    License category for Chilean radio amateur exams.
    CD = Novicio, CA = General, CE = Superior, XQ = Experimental
    """

    code = models.CharField(
        max_length=5,
        unique=True,
        help_text="Category code: CD, CA, CE, XQ",
    )
    name = models.CharField(
        max_length=50,
        help_text="Category name (e.g., Novicio, General, Superior)",
    )
    exam_size = models.IntegerField(
        help_text="Total number of questions in an exam for this category",
    )
    reglamento_count = models.IntegerField(
        help_text="Number of questions from Reglamento section",
    )
    tecnica_count = models.IntegerField(
        help_text="Number of questions from Tecnica section",
    )

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Area(models.Model):
    """
    Question area: Reglamentacion or Tecnica.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Area name (e.g., Reglamentacion, Tecnica)",
    )

    class Meta:
        verbose_name = "area"
        verbose_name_plural = "areas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tema(models.Model):
    """
    Topic within an area and category.
    """

    name = models.CharField(
        max_length=100,
        help_text="Topic name",
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="temas",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="temas",
    )

    class Meta:
        verbose_name = "tema"
        verbose_name_plural = "temas"
        ordering = ["area", "name"]
        unique_together = ["name", "area", "category"]

    def __str__(self):
        return f"{self.name} ({self.area.name} - {self.category.code})"


class Question(models.Model):
    """
    Multiple choice question for the exam simulator.
    """

    ANSWER_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    ]

    text = models.TextField(
        help_text="Question text",
    )
    option_a = models.CharField(
        max_length=500,
        help_text="Option A",
    )
    option_b = models.CharField(
        max_length=500,
        help_text="Option B",
    )
    option_c = models.CharField(
        max_length=500,
        help_text="Option C",
    )
    option_d = models.CharField(
        max_length=500,
        help_text="Option D",
    )
    correct_answer = models.CharField(
        max_length=1,
        choices=ANSWER_CHOICES,
        help_text="Correct answer (A, B, C, or D)",
    )
    explanation = models.TextField(
        blank=True,
        default="",
        help_text="Explanation for the correct answer (optional)",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    tema = models.ForeignKey(
        Tema,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this question is active and can appear in exams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "question"
        verbose_name_plural = "questions"
        ordering = ["category", "area", "pk"]

    def __str__(self):
        return f"Q{self.pk}: {self.text[:60]}..."


class ExamAttempt(models.Model):
    """
    An attempt at taking an exam (exam or training mode).
    """

    MODE_CHOICES = [
        ("exam", "Examen"),
        ("training", "Entrenamiento"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exam_attempts",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        help_text="Exam mode: exam (timed, graded) or training (with feedback)",
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Score as percentage (0-100)",
    )

    class Meta:
        verbose_name = "exam attempt"
        verbose_name_plural = "exam attempts"
        ordering = ["-started_at"]

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{user_str} - {self.category.code} ({self.get_mode_display()})"


class AnswerAttempt(models.Model):
    """
    Individual answer within an exam attempt.
    """

    exam_attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answer_attempts",
    )
    selected_answer = models.CharField(
        max_length=1,
        choices=Question.ANSWER_CHOICES,
    )
    is_correct = models.BooleanField()
    time_spent_seconds = models.IntegerField(
        default=0,
        help_text="Time spent on this question in seconds",
    )

    class Meta:
        verbose_name = "answer attempt"
        verbose_name_plural = "answer attempts"
        unique_together = ["exam_attempt", "question"]

    def __str__(self):
        return f"Q{self.question.pk} -> {self.selected_answer} ({'OK' if self.is_correct else 'WRONG'})"
