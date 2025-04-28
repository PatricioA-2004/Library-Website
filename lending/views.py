from datetime import timezone, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic.base import TemplateView
from django.views.generic import DeleteView
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from .models import Profile
from .forms import ProfileForm, CollectionForm, AddLibrarianForm
from django.contrib.auth.models import User
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib.postgres.search import SearchVector
from django.db.models import Q, OuterRef, Exists
from datetime import timedelta
from lending.models import Request
from django.utils.timezone import now

from .forms import BookForm, ReviewForm, BookCopyFormSet
from django.views.generic import DetailView, ListView
from .models import Book, Collection, Review, CollectionRequest, BookCopy
from django.contrib import messages
from django.db.utils import IntegrityError

# Create your views here.
class IndexView(ListView):
    template_name = "lending/index.html"
    context_object_name = "book_list"
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Book.objects.all().order_by('book_title')
        elif user.is_authenticated:
            return Book.objects.filter(Q(collection__private=False) | Q(collection__allowed_users=user) | Q(collection__isnull=True)).distinct().order_by('book_title')
        else:
            return Book.objects.exclude(collection__private=True).order_by('book_title')

def collection_list_view(request):
    context = {}
    if request.user.is_staff:
        collection_list = Collection.objects.all()
        context = {'collections' : collection_list}
    elif request.user.is_authenticated:
        collection_list = Collection.objects.filter(Q(private = False) | Q(owner = request.user) | Q(allowed_users = request.user))
        private_titles = Collection.objects.filter(Q(private = True) & ~Q(owner = request.user) & ~Q(allowed_users = request.user)).annotate(
            requested = Exists(CollectionRequest.objects.filter(user=request.user, collection=OuterRef('pk'))))
        context = {'collections' : collection_list, 'private_collections' : private_titles}
    elif request.user.is_anonymous:
        collection_list = Collection.objects.filter(private = False)
        context = {'collections' : collection_list}

    return render(request, 'lending/collection_list.html', context)

@require_POST
@login_required
def request_collection_access(request):
    collection_id = request.POST.get('collection_id')
    collection = get_object_or_404(Collection, id=collection_id)

    # Check if a request already exists
    existing_request = CollectionRequest.objects.filter(user=request.user, collection=collection).exists()

    if not existing_request:
        CollectionRequest.objects.create(user=request.user, collection=collection)
        messages.success(request, f"Access request for '{collection.collection_name}' has been submitted.")
    else:
        messages.info(request, f"You've already requested access to '{collection.collection_name}'.")

    return redirect('lending:collections_list')

def login(request):
    auto_return_overdue_books()
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
            book = form.save(commit=False)
            book.total_available = book.total_copies
            book.save()
            form.save_m2m()
            
            for _ in range(book.total_copies):
                BookCopy.objects.create(book=book)
                
            return redirect('lending:index')
    else:
        form = BookForm()

    return render(request, 'lending/add_book.html', {'form': form})

@login_required
def profile_view(request): #fixed
    user_instance = request.user
    profile, created = Profile.objects.get_or_create(user=user_instance)

    if request.method == 'POST':
        new_username = request.POST.get("username")
        if new_username and new_username != user_instance.username:
            user_instance.username = new_username
            user_instance.save()

        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()

        return redirect('lending:profile')

    return render(request, 'lending/profile.html', {'profile': profile})

class BookDetailView(DetailView):
    model = Book
    template_name = "lending/book_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reviews = self.object.reviews.all().order_by('-created_at')
        context['reviews'] = reviews
        context['copies'] = self.object.copies.all().values()
        if self.request.user.is_authenticated:
            context['review_form'] = ReviewForm()
            context['user_review'] = self.object.reviews.filter(user=self.request.user).first()
            user_requests = Request.objects.filter(
                requester=self.request.user,
                returned=False,
                status__in=["PENDING", "APPROVED"]
            ).values_list('requested_book_id', flat=True)
            context['can_request'] = self.object.id not in user_requests
        else:
            context['can_request'] = False
        
        if reviews:
            total_rating = sum(review.rating for review in reviews)
            context['average_rating'] = total_rating / len(reviews)
        else:
            context['average_rating'] = 0

        borrowed_count = Request.objects.filter(
            requested_book=self.object,
            status="APPROVED"
        ).count()

        pending_count = Request.objects.filter(
            requested_book=self.object,
            status="PENDING"
        ).count()

        in_library_count = max(self.object.total_copies - borrowed_count - pending_count, 0)

        context['borrowed_count'] = borrowed_count
        context['pending_count'] = pending_count
        context['in_library_count'] = in_library_count


        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        book = self.object

        # Check if user already requested or has the book
        already_requested = Request.objects.filter(
            requester=request.user,
            requested_book=book,
            returned=False,
            status__in=["PENDING", "APPROVED"]
        ).exists()

        if already_requested:
            messages.error(request, "You already have this book requested or checked out.")
            return self.get(request, *args, **kwargs)

        # Create the new request directly
        Request.objects.create(
            requester=request.user,
            requested_book=book,
            status="PENDING"
        )

        return redirect('lending:book_detail', pk=book.id)

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
        copy_formset = BookCopyFormSet(request.POST, instance=book)

        if form.is_valid() and copy_formset.is_valid():
            book = form.save(commit=False)
            
            deleted_copies = sum(1 for form in copy_formset.deleted_forms if form.instance.pk)
            
            old_total_copies = Book.objects.get(pk=pk).total_copies
            new_total_copies = book.total_copies
            difference = new_total_copies - old_total_copies
            
            if difference > 0:
                book.total_available += difference
            else:
                book.total_available = max(0, book.total_available + difference - deleted_copies)
                book.total_copies = old_total_copies - deleted_copies
            
            book.save()
            form.save_m2m()

            copies = copy_formset.save(commit=False)
            for copy in copies:
                copy.book = book
                if not copy.location:
                    copy.location = Location.objects.first()
                copy.save()

            for form in copy_formset.deleted_forms:
                if form.instance.pk:
                    form.instance.delete()

            if difference > 0:
                default_location = Location.objects.first()
                for _ in range(difference):
                    BookCopy.objects.create(book=book, location=default_location)

            return redirect('lending:book_detail', pk=pk)
    else:
        form = BookForm(instance=book)
        copy_formset = BookCopyFormSet(instance=book, queryset=book.copies.all().order_by('id'))

    empty_copy_form = BookCopyFormSet().empty_form

    return render(request, 'lending/edit_book.html', {
        'form': form,
        'copy_formset': copy_formset,
        'empty_copy_form': empty_copy_form,
        'book': book,
        'locations': Location.objects.all()
    })


class CollectionDetailView(DetailView):
    model = Collection
    template_name = "lending/collection_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.books.all().order_by()
        return context

@login_required
def edit_collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    if not request.user.is_staff and request.user != collection.owner:
        return HttpResponseForbidden("You do not have permission to edit this collection.")
    if request.method == 'POST':
        form = CollectionForm(request.POST, instance=collection, user_is_staff=request.user.is_staff)
        if form.is_valid():
            collection = form.save(commit = False)
            if collection.private and not request.user.is_staff:
                return HttpResponseForbidden("You do not have permission to create private collections.")
            collection.save()
            form.save_m2m()

            if collection.private:
                # we need to remove the books in this collection from all public collections
                private_books = collection.books.all()
                for other_collection in Collection.objects.all():
                    if collection == other_collection:
                        continue
                    other_collection.books.remove(*private_books)
                    other_collection.save()
            return redirect('lending:collection_detail', pk=pk)
    else:
        form = CollectionForm(instance=collection, user_is_staff=request.user.is_staff)

    return render(request, 'lending/edit_collection.html', {'form': form, 'collection': collection})


class CollectionDeleteView(UserPassesTestMixin, DeleteView):
    model = Collection
    template_name = "lending/collection_confirm_delete.html"
    success_url = reverse_lazy('lending:collections_list')

    def test_func(self):
        collection = self.get_object()
        return self.request.user.is_staff or collection.owner == self.request.user

@login_required
def create_collection(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST, user_is_staff=request.user.is_staff)
        if form.is_valid():
            if form.cleaned_data['private'] and not request.user.is_staff:
                return HttpResponseForbidden('Can\'t make private collection as non-staff')
            collection = form.save(commit=False)
            collection.owner = request.user
            collection.save()
            # Save the many-to-many relationships
            form.save_m2m()

            if collection.private:
                # we need to remove the books in this collection from all public collections
                private_books = collection.books.all()
                for other_collection in Collection.objects.all():
                    if collection == other_collection:
                        continue
                    other_collection.books.remove(*private_books)
                    other_collection.save()
            return redirect('lending:collections_list')
    else:
        form = CollectionForm(user_is_staff=request.user.is_staff)

    return render(request, 'lending/create_collection.html', {'form': form})

def search_view(request):
    query = request.GET.get('q')
    books = Book.objects.annotate(search=SearchVector("book_title", "book_author"),).filter(search=query)
    collections = Collection.objects.annotate(search=SearchVector("collection_name")).filter(search=query)
    private_titles = None
    if request.user.is_authenticated and not request.user.is_staff:
        books = books.filter(Q(collection__private=False) | Q(collection__allowed_users=request.user)).distinct()
        private_titles = collections._clone().filter(Q(private = True) & ~Q(owner = request.user) & ~Q(allowed_users = request.user)).values('collection_name')
        collections = collections.filter(Q(private = False) | Q(owner = request.user) | Q(allowed_users = request.user))
    elif request.user.is_anonymous:
        books = books.exclude(collection__private=True)
        collections = collections.filter(private = False)
    return render(request, 'lending/search_view.html', {'book_list' : books, 'query' : query, 'collections' : collections, 'private_collections' : private_titles})

def collection_search_view(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    books = None
    query = request.GET.get('q', '')
    if query != '':
        books = collection.books.annotate(search=SearchVector("book_title", "book_author"),).filter(search=query)
    else:
        books = collection.books.all()
    context = {'collection' : collection, 'books' : books, 'query': query}
    return render(request, 'lending/collection_search.html', context)

@login_required
def my_book_requests(request):
    requests = Request.objects.filter(requester=request.user).select_related('requested_book').order_by('-requested_at')
    return render(request, 'lending/my_requests.html', {'requests': requests})


@user_passes_test(is_staff)
def manage_requests(request):
    if request.method == "POST":
        req_id = request.POST.get("request_id")
        action = request.POST.get("action")
        book_request = get_object_or_404(Request, id=req_id)

        if action == "approve":
            book = book_request.requested_book
            # Find an available copy
            available_copy = book.copies.filter(is_available=True).first()
            if not available_copy:
                messages.error(request, f"No available copies of '{book.book_title}' to lend.")
                return redirect('lending:manage_requests')
            
            # Update the copy's status and location
            available_copy.is_available = False
            available_copy.location = Location.objects.get(name='ON_LOAN')
            available_copy.save()
            
            book_request.status = "APPROVED"
            book_request.due_date = now() + timedelta(days=30)
            book.total_available -= 1
            book.save()
            messages.success(request, f"Request for '{book.book_title}' approved.")

        elif action == "reject":
            book_request.status = "REJECTED"
            messages.error(request, f"Request for '{book_request.requested_book.book_title}' rejected.")

        book_request.save()
        return redirect('lending:manage_requests')

    pending_requests = Request.objects.filter(status="PENDING").select_related('requested_book', 'requester')
    replied_requests = Request.objects.exclude(status="PENDING").select_related('requested_book', 'requester')

    return render(request, 'lending/manage_requests.html', {
        'pending_requests': pending_requests,
        'replied_requests': replied_requests,
    })


@user_passes_test(is_staff)
def add_librarian(request):
    message = ''
    if request.method == "POST":
        form = AddLibrarianForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                user.is_staff = True
                user.save()
                message = user.username + " has been granted librarian access."
            except User.DoesNotExist:
                message = "No user found with that email address."
    else:
        form = AddLibrarianForm()

    return render(request, 'lending/add_librarian.html', {
        'form': form,
        'message': message
    })


@login_required
def return_book(request, pk):
    book_request = get_object_or_404(Request, pk=pk, requester=request.user, returned=False)
    book = book_request.requested_book
    
    loaned_copy = book.copies.filter(is_available=False, location__name='ON_LOAN').first()
    if loaned_copy:
        # Update the copy's status and location
        loaned_copy.is_available = True
        loaned_copy.location = Location.objects.get(name='SHANNON')
        loaned_copy.save()
    
    book.total_available += 1
    book.save()

    book_request.returned = True
    book_request.status = "RETURNED"
    book_request.returned_at = now()
    book_request.save()

    messages.success(request, f"You successfully returned '{book.book_title}'.")
    return redirect('lending:my_books')


@login_required
def my_books(request):
    auto_return_overdue_books()
    active_requests = Request.objects.filter(
        requester=request.user,
        status="APPROVED",
        returned=False
    ).select_related("requested_book").order_by("due_date")

    for r in active_requests:
        if r.due_date:
            r.days_left = (r.due_date - now()).days
        else:
            r.days_left = None

    return render(request, "lending/my_books.html", {"requests": active_requests})

def auto_return_overdue_books():
    overdue = Request.objects.filter(
        returned=False,
        status="APPROVED",
        due_date__lt=now()
    ).select_related("requested_book")

    for r in overdue:
        r.returned = True
        r.returned_at = now()
        book = r.requested_book
        book.total_available += 1
        book.save()
        r.save()

@login_required
def add_review(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.user = request.user
            try:
                review.save()
                #messages.success(request, 'Review added successfully!')
            except IntegrityError:
                messages.error(request, 'You have already reviewed this book.')
        else:
            messages.error(request, 'Please fill in both rating and comment.')
    return redirect('lending:book_detail', pk=pk)

@login_required
@user_passes_test(is_staff)
def delete_request(request, pk):
    book_request = get_object_or_404(Request, id=pk)
    if request.method == "POST":
        if request.user == book_request.requester or request.user.is_staff:
            book_request.delete()  
    return redirect(request.META.get('HTTP_REFERER', 'lending:manage_requests'))

@login_required
@require_POST
def cancel_request(request, pk):
    book_request = get_object_or_404(Request, pk=pk, requester=request.user)
    if book_request.status == "PENDING":
        book_request.delete()
    return redirect('lending:my_book_requests')

@user_passes_test(is_staff)
@require_POST
def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    
    book.reviews.all().delete()
    
    for collection in book.collection_set.all():
        collection.books.remove(book)
    
    book.delete()
    
    messages.success(request, f'Book "{book.book_title}" has been successfully deleted.')
    return redirect('lending:index')