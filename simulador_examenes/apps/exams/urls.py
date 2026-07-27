from django.urls import path

from . import views

app_name = "exams"

urlpatterns = [
    path("categories/", views.category_list, name="category-list"),
    path("questions/", views.question_list, name="question-list"),
]
