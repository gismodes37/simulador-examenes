from django.contrib import admin

from .models import AnswerAttempt, Area, Category, ExamAttempt, Question, Tema


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "exam_size", "reglamento_count", "tecnica_count"]
    search_fields = ["code", "name"]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ["name", "area", "category"]
    list_filter = ["area", "category"]
    search_fields = ["name"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "text",
        "category",
        "area",
        "tema",
        "correct_answer",
        "is_active",
    ]
    list_filter = ["category", "area", "is_active"]
    search_fields = ["text"]
    list_editable = ["is_active"]
    list_per_page = 50


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "user",
        "category",
        "mode",
        "started_at",
        "finished_at",
        "score",
    ]
    list_filter = ["category", "mode"]
    search_fields = ["user__username", "user__callsign"]
    readonly_fields = ["started_at"]


@admin.register(AnswerAttempt)
class AnswerAttemptAdmin(admin.ModelAdmin):
    list_display = [
        "exam_attempt",
        "question",
        "selected_answer",
        "is_correct",
        "time_spent_seconds",
    ]
    list_filter = ["is_correct"]
    search_fields = ["question__text"]
