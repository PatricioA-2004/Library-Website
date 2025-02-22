"""
URL configuration for book_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.conf.urls.static import static
from django.conf import settings

def force_google_redirect(request):
    return redirect('https://accounts.google.com/o/oauth2/auth?client_id=REDACTED_OAUTH_KEYm&redirect_uri=http://127.0.0.1:8000/auth/complete/google-oauth2/&response_type=code&scope=email')

def custom_logout(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('/lending/login/')

urlpatterns = [
    path('', lambda request: redirect('lending:index')),
    path('admin/', admin.site.urls),
    path('lending/', include("lending.urls")),
    path('auth/', include('social_django.urls', namespace='social')),
    path('force-login/', force_google_redirect, name='force-google-login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/lending/login/'), name='logout'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
