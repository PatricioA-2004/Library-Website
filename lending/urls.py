from django.urls import path

from . import views

app_name = "lending"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path('add/', views.add_book, name='add_book'),
    path('login/', views.login, name='login'),
    path("book/<int:pk>/", views.BookDetailView.as_view(), name="book_detail")
]
