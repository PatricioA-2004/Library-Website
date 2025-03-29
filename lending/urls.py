from django.urls import path

from . import views
from .views import profile_view, profile_update


app_name = "lending"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path('add/', views.add_book, name='add_book'),
    path('login/', views.login, name='login'),
    path("book/<int:pk>/", views.BookDetailView.as_view(), name="book_detail"),
    path('profile/', profile_view, name='profile'),
    path('profile/update/', profile_update, name='profile_update'),
    path('book/<int:pk>/edit/', views.edit_book, name='edit_book'),
    path('collection/create/', views.create_collection, name='create_collection'),
    path('request/', views.request_book, name='request_book'),

]
