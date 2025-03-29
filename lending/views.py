from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from .models import Profile
from .forms import ProfileForm, CollectionForm, RequestForm
from django.contrib.auth.models import User


from .forms import BookForm
from django.views.generic import DetailView, ListView
from .models import Book, Collection

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

@login_required
def profile_view(request):
    user_instance = User.objects.get(username=request.user.username)
    profile, created = Profile.objects.get_or_create(user=user_instance)
    return render(request, 'lending/profile.html', {'profile': profile})

class BookDetailView(DetailView):
    model = Book
    template_name = "lending/book_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

@login_required
def profile_update(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('lending:profile')
    else:
        form = ProfileForm(instance=request.user.profile)

    return render(request, 'lending/profile_update.html', {'form': form})

def is_staff(user):
    return user.is_staff

@user_passes_test(is_staff)
def edit_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            return redirect('lending:book_detail', pk=pk)
    else:
        form = BookForm(instance=book)
    
    return render(request, 'lending/edit_book.html', {'form': form, 'book': book})

class CollectionDetailView(DetailView):
    model = Collection
    template_name = "lending/collection_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.books.all()
        return context

@login_required
def create_collection(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST, user_is_staff=request.user.is_staff)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.owner = request.user
            collection.save()
            # Save the many-to-many relationships
            form.save_m2m()
            return redirect('lending:index')
    else:
        form = CollectionForm(user_is_staff=request.user.is_staff)
    
    return render(request, 'lending/create_collection.html', {'form': form})

@login_required
def request_book(request):
    if request.method == 'POST':
        form = RequestForm(request.POST, user=request.user)
        if form.is_valid():
            book_request = form.save(commit=False)
            book_request.requester = request.user
            book_request.save()
            return redirect('lending:index')
    else:
        form = RequestForm(user=request.user)
    return render(request, 'lending/request_book.html', {'form': form})