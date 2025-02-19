from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.views.generic import DetailView
from .models import Book

# Create your views here.
class IndexView(TemplateView):
    template_name = "lending/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class BookDetailView(DetailView):
    model = Book
    template_name = "lending/book_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
