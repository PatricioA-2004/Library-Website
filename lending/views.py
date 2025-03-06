from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


from .forms import BookForm
from django.views.generic import DetailView, ListView
from .models import Book

# Create your views here.
class IndexView(ListView):
    template_name = "lending/index.html"
    context_object_name = "book_list"
    def get_queryset(self):
        return Book.objects.all()

def login(request):
    return render(request, 'lending/login.html')

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('https://accounts.google.com/logout?continue=http://127.0.0.1:8000/lending/login/')

def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if not request.user or not request.user.is_staff:
            return HttpResponseForbidden('Permission Denied')
        if form.is_valid():
            form.save()
            return redirect('lending:index')
    else:
        form = BookForm()

    return render(request, 'lending/add_book.html', {'form': form})
    
class BookDetailView(DetailView):
    model = Book
    template_name = "lending/book_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
