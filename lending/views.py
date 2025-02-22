from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.shortcuts import redirect


# Create your views here.
class IndexView(TemplateView):
    template_name = "lending/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

def login(request):
    return render(request, 'lending/login.html')


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('https://accounts.google.com/logout?continue=http://127.0.0.1:8000/lending/login/')