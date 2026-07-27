from django.urls import path

from . import views

app_name = "exams"

urlpatterns = [
    # Pages
    path("", views.home, name="home"),
    path("setup/<str:category_code>/", views.exam_setup, name="exam_setup"),
    path("start/<str:category_code>/", views.exam_start, name="exam_start"),
    path("<int:attempt_id>/", views.exam_page, name="exam_page"),
    path("<int:attempt_id>/results/", views.exam_results, name="exam_results"),
    path("<int:attempt_id>/finish/", views.finish_exam, name="finish_exam"),
    path("history/", views.exam_history, name="exam_history"),
    # HTMX endpoints
    path("<int:attempt_id>/submit/", views.submit_answer, name="submit_answer"),
]
