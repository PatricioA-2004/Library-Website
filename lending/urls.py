from django.urls import path
from . import views

app_name = "lending"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path('login/', views.login, name='login'),
]
