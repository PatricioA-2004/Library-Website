from django.shortcuts import render
from django.views.generic.base import TemplateView

# Create your views here.
class IndexView(TemplateView):
    template_name = "lending/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context