import random
from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import AnswerAttempt, Area, Category, ExamAttempt, Question


EXAM_DURATION_MINUTES = 60


def home(request):
    """Landing page with category selection."""
    from django.db.models import Count, Q

    categories = Category.objects.annotate(
        active_questions=Count(
            "questions",
            filter=Q(questions__is_active=True),
        )
    ).all()

    return render(request, "exams/home.html", {"categories": categories})


def exam_setup(request, category_code):
    """Configure exam mode before starting."""
    category = get_object_or_404(Category, code__iexact=category_code)
    return render(request, "exams/exam_setup.html", {"category": category})


def exam_start(request, category_code):
    """Create an exam attempt and redirect to exam page."""
    if request.method != "POST":
        return redirect("exams:home")

    category = get_object_or_404(Category, code__iexact=category_code)
    mode = request.POST.get("mode", "training")
    if mode not in ("exam", "training"):
        mode = "training"

    # Get active questions for this category, split by area
    reglamento_area = Area.objects.filter(name__icontains="reglamento").first()
    tecnica_area = Area.objects.filter(name__icontains="tecnica").first()

    reglamento_questions = []
    tecnica_questions = []

    if reglamento_area:
        reglamento_questions = list(
            Question.objects.filter(
                category=category, area=reglamento_area, is_active=True
            ).order_by("?")[: category.reglamento_count]
        )

    if tecnica_area:
        teknica_count = category.tecnica_count
        tecnica_questions = list(
            Question.objects.filter(
                category=category, area=tecnica_area, is_active=True
            ).order_by("?")[:teknica_count]
        )

    selected_questions = reglamento_questions + tecnica_questions
    random.shuffle(selected_questions)

    if not selected_questions:
        messages.error(request, "No hay preguntas disponibles para esta categoría.")
        return redirect("exams:home")

    # Create attempt
    attempt = ExamAttempt.objects.create(
        user=request.user if request.user.is_authenticated else None,
        category=category,
        mode=mode,
    )

    # Store question order in session
    session_key = f"exam_{attempt.pk}_questions"
    request.session[session_key] = [q.pk for q in selected_questions]
    request.session[f"exam_{attempt.pk}_current"] = 0
    request.session[f"exam_{attempt.pk}_started"] = timezone.now().isoformat()

    return redirect("exams:exam_page", attempt_id=attempt.pk)


def exam_page(request, attempt_id):
    """Display current question in the exam."""
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id)

    # Security: only allow owner or anonymous
    if attempt.user and attempt.user != request.user:
        messages.error(request, "No tienes acceso a este examen.")
        return redirect("exams:home")

    session_key = f"exam_{attempt.pk}_questions"
    question_pks = request.session.get(session_key, [])
    current_idx = request.session.get(f"exam_{attempt.pk}_current", 0)

    if not question_pks:
        messages.error(request, "Sesión de examen no encontrada. Comienza uno nuevo.")
        return redirect("exams:home")

    # Check if finished
    if current_idx >= len(question_pks):
        return redirect("exams:exam_results", attempt_id=attempt.pk)

    # Timer calculation for exam mode
    seconds_remaining = EXAM_DURATION_MINUTES * 60
    if attempt.mode == "exam":
        started_str = request.session.get(f"exam_{attempt.pk}_started")
        if started_str:
            try:
                started = timezone.datetime.fromisoformat(started_str)
                if timezone.is_naive(started):
                    started = timezone.make_aware(started)
                elapsed = (timezone.now() - started).total_seconds()
                seconds_remaining = max(0, EXAM_DURATION_MINUTES * 60 - int(elapsed))
            except (ValueError, TypeError):
                pass

        if seconds_remaining <= 0:
            return redirect("exams:finish_exam", attempt_id=attempt.pk)

    question = get_object_or_404(Question, pk=question_pks[current_idx])
    total = len(question_pks)
    progress_pct = int((current_idx / total) * 100) if total > 0 else 0

    context = {
        "attempt": attempt,
        "question": question,
        "current_index": current_idx + 1,
        "total_questions": total,
        "progress_pct": progress_pct,
        "is_last": current_idx + 1 >= total,
        "seconds_remaining": seconds_remaining,
    }

    return render(request, "exams/exam_page.html", context)


def submit_answer(request, attempt_id):
    """HTMX endpoint: record answer, advance to next question."""
    if request.method != "POST":
        return HttpResponseRedirect(reverse("exams:exam_page", args=[attempt_id]))

    attempt = get_object_or_404(ExamAttempt, pk=attempt_id)
    question_id = request.POST.get("question_id")
    selected = request.POST.get("answer", "").upper()

    if selected not in ("A", "B", "C", "D") or not question_id:
        return HttpResponseRedirect(reverse("exams:exam_page", args=[attempt_id]))

    question = get_object_or_404(Question, pk=question_id)
    is_correct = selected == question.correct_answer

    # Save answer (update if exists)
    AnswerAttempt.objects.update_or_create(
        exam_attempt=attempt,
        question=question,
        defaults={
            "selected_answer": selected,
            "is_correct": is_correct,
        },
    )

    # Advance current index
    current_idx = request.session.get(f"exam_{attempt.pk}_current", 0)
    request.session[f"exam_{attempt.pk}_current"] = current_idx + 1

    # Check if last question
    question_pks = request.session.get(f"exam_{attempt.pk}_questions", [])
    next_idx = current_idx + 1
    is_last = next_idx >= len(question_pks)

    # If HTMX request and training mode, return question card fragment with feedback
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx and next_idx < len(question_pks):
        next_question = get_object_or_404(Question, pk=question_pks[next_idx])
        total = len(question_pks)
        progress_pct = int((next_idx / total) * 100) if total > 0 else 0

        context = {
            "attempt": attempt,
            "question": next_question,
            "current_index": next_idx + 1,
            "total_questions": total,
            "progress_pct": progress_pct,
            "is_last": is_last,
            "is_correct": is_correct,
            "selected_answer": selected,
        }
        return render(request, "exams/question_card.html", context)

    if is_htmx and is_last:
        # Last question: redirect to results via HTMX redirect header
        from django.http import HttpResponse

        resp = HttpResponse()
        resp["HX-Redirect"] = reverse("exams:finish_exam", args=[attempt.pk])
        return resp

    return HttpResponseRedirect(reverse("exams:exam_page", args=[attempt_id]))


def finish_exam(request, attempt_id):
    """Calculate score and redirect to results."""
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id)

    if attempt.score is not None:
        return redirect("exams:exam_results", attempt_id=attempt.pk)

    answers = attempt.answers.select_related("question", "question__area")

    total = answers.count()
    if total == 0:
        # Mark as 0 if no answers
        attempt.score = 0
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["score", "finished_at"])
        return redirect("exams:exam_results", attempt_id=attempt.pk)

    correct = answers.filter(is_correct=True).count()
    score = int((correct / total) * 100)

    attempt.score = score
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=["score", "finished_at"])

    return redirect("exams:exam_results", attempt_id=attempt.pk)


def exam_results(request, attempt_id):
    """Display exam results with breakdown."""
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, score__isnull=False)

    answers = attempt.answers.select_related("question", "question__area")

    total = answers.count()
    correct = answers.filter(is_correct=True).count()
    score = attempt.score

    # Area breakdown
    reglamento_answers = answers.filter(question__area__name__icontains="reglamento")
    tecnica_answers = answers.filter(question__area__name__icontains="tecnica")

    reglamento_total = reglamento_answers.count()
    reglamento_correct = reglamento_answers.filter(is_correct=True).count()
    reglamento_score = int((reglamento_correct / reglamento_total) * 100) if reglamento_total > 0 else 0

    tecnica_total = tecnica_answers.count()
    tecnica_correct = tecnica_answers.filter(is_correct=True).count()
    tecnica_score = int((tecnica_correct / tecnica_total) * 100) if tecnica_total > 0 else 0

    # Wrong answers
    wrong_answers = []
    for ans in answers.filter(is_correct=False).select_related("question__area"):
        q = ans.question
        wrong_answers.append(
            {
                "question": q,
                "selected": ans.selected_answer,
                "selected_text": getattr(q, f"option_{ans.selected_answer.lower()}", ""),
                "correct_text": getattr(q, f"option_{q.correct_answer.lower()}", ""),
            }
        )

    context = {
        "attempt": attempt,
        "score": score,
        "passed": score >= 70,
        "correct_count": correct,
        "total_questions": total,
        "reglamento_score": reglamento_score,
        "reglamento_correct": reglamento_correct,
        "reglamento_total": reglamento_total,
        "tecnica_score": tecnica_score,
        "tecnica_correct": tecnica_correct,
        "tecnica_total": tecnica_total,
        "wrong_answers": wrong_answers,
    }

    return render(request, "exams/results.html", context)


def exam_history(request):
    """List all past exam attempts with filtering."""
    attempts = ExamAttempt.objects.select_related("category").all()

    selected_category = request.GET.get("category", "")
    selected_mode = request.GET.get("mode", "")

    if selected_category:
        attempts = attempts.filter(category__code__iexact=selected_category)

    if selected_mode in ("exam", "training"):
        attempts = attempts.filter(mode=selected_mode)

    paginator = Paginator(attempts, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    all_categories = Category.objects.all()

    context = {
        "attempts": page_obj,
        "all_categories": all_categories,
        "selected_category": selected_category,
        "selected_mode": selected_mode,
        "page_obj": page_obj,
    }

    return render(request, "exams/history.html", context)
