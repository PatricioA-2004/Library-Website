from datetime import timezone, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import modelformset_factory, inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic.base import TemplateView
from django.views.generic import DeleteView
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, JsonResponse
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
from notifications.signals import notify
from django import forms


from .forms import BookForm, ReviewForm, BookCopyFormSet, AlternateCoverForm
from django.views.generic import DetailView, ListView
from .models import Book, Collection, Review, CollectionRequest, BookCopy, AlternateCover
from notifications.models import Notification
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
            messages.success(request, 'Book created successfully!')
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
            messages.success(request, 'Username saved successfully!')

        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            messages.success(request, 'Profile picture changed successfully!')

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
        context['alternate_covers'] = self.object.alternate_covers.all()
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
        messages.success(request, 'Book requested successfully!')
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
    messages.success(request, 'Profile updated successfully!')
    return render(request, 'lending/profile_update.html', {'form': form})

def is_staff(user):
    return user.is_staff

@user_passes_test(is_staff)
def edit_book(request, pk):
    book = get_object_or_404(Book, pk=pk)

    BookCopyFormSet = modelformset_factory(
        BookCopy,
        fields=('location',),
        extra=0,  # always show 1 empty form to add a copy
        can_delete=True,
    )

    AlternateCoverFormset = inlineformset_factory(
        Book, 
        AlternateCover, 
        form = AlternateCoverForm,
        extra=0,
        can_delete=True,
    )

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        formset = BookCopyFormSet(request.POST, queryset=book.copies.all())
        alternate_cover_formset = AlternateCoverFormset(request.POST, request.FILES, instance=book)

        if form.is_valid() and formset.is_valid() and alternate_cover_formset.is_valid():
            book = form.save(commit=False)
            form.save_m2m()

            instances = formset.save(commit=False)

            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()

            for instance in instances:
                instance.book = book
                instance.save()

            alternate_cover_formset.save()

            # Force total_copies to match the real count
            book.total_copies = book.copies.count()
            book.total_available = book.copies.filter(is_available=True).count()
            book.save()
            messages.success(request, 'Book edited successfully!')
            return redirect('lending:book_detail', pk=book.pk)
    else:
        form = BookForm(instance=book)
        formset = BookCopyFormSet(queryset=book.copies.all())
        alternate_cover_formset = AlternateCoverFormset(instance=book)

    return render(request, 'lending/edit_book.html', {
        'form': form,
        'formset': formset,
        'alternate_cover_formset': alternate_cover_formset,
        'book': book,
    })


class CollectionDetailView(DetailView):
    model = Collection
    template_name = "lending/collection_detail.html"
    
    def get_context_data(self, **kwargs):
        can_view = (
            (not self.object.private and self.request.user.is_authenticated)
            or self.request.user.is_staff
            or self.object.owner == self.request.user
            or self.request.user in self.object.allowed_users.all()
        )
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.books.all().order_by()
        context['can_view'] = can_view
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
            messages.success(request, f"Collection '{collection.collection_name}' updated successfully!")
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

    def form_valid(self, form):
        collection = self.get_object()
        messages.success(self.request, f"Collection '{collection.collection_name}' deleted successfully!")
        return super().form_valid(form)

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
            messages.success(request, f"Collection '{collection.collection_name}' has been created successfully!")
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
        print(req_id)
        print(action)
        if action == "approve":
            print("here")
            book_request = get_object_or_404(Request, id=req_id)
            book = book_request.requested_book
            available_copy = book.copies.filter(is_available=True).first()
            if not available_copy:
                messages.error(request, f"No available copies of '{book.book_title}' to lend.")
                return redirect('lending:manage_requests')
            
            available_copy.is_available = False
            available_copy.location = "ON_LOAN"
            available_copy.save()
            
            book_request.status = "APPROVED"
            book_request.due_date = now() + timedelta(days=30)
            book.total_available -= 1
            book_request.save()
            book.save()
            notify.send(
                sender=request.user,
                recipient=book_request.requester,
                verb="was approved",
                target=book,
                description=f"Your request for '{book.book_title}' has been approved.",
                level='success'
            )

        elif action == "reject":
            book_request = get_object_or_404(Request, id=req_id)
            book_request.status = "REJECTED"
            book_request.save()
            notify.send(
                sender=request.user,
                recipient=book_request.requester,
                verb="was rejected",
                target=book_request.requested_book,
                description=f"Your request for '{book_request.requested_book.book_title}' was rejected.",
                level='error'
            )

        elif action == "approve_collection":
            collection_request = get_object_or_404(CollectionRequest, id=req_id)
            collection_request.status = "APPROVED"
            collection_request.collection.allowed_users.add(collection_request.user)
            collection_request.save()
            collection_request.collection.save()
            notify.send(
                sender=request.user,
                recipient=collection_request.user,
                verb="was approved",
                target=collection_request.collection,
                description=f"Access to Collection '{collection_request.collection.collection_name}' has been granted.",
                level='success'
            )

        elif action == "reject_collection":
            collection_request = get_object_or_404(CollectionRequest, id=req_id)
            collection_request.status = "REJECTED" 
            collection_request.save()
            notify.send(
                sender=request.user,
                recipient=collection_request.user,
                verb="was rejected",
                target=collection_request.collection,
                description=f"Access to Collection '{collection_request.collection.collection_name}' has been denied.",
                level='error'
            )

        return redirect('lending:manage_requests')

    pending_book_requests = Request.objects.filter(status="PENDING").select_related('requested_book', 'requester')
    pending_collection_requests = CollectionRequest.objects.filter(status="PENDING").select_related('user', 'collection')
    replied_requests = Request.objects.exclude(status="PENDING").select_related('requested_book', 'requester')

    return render(request, 'lending/manage_requests.html', {
        'pending_requests': pending_book_requests,
        'pending_collection_requests': pending_collection_requests,
        'replied_requests': replied_requests,
    })


@user_passes_test(is_staff)
def add_librarian(request):
    if request.method == "POST":
        form = AddLibrarianForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                user.is_staff = True
                user.save()
                messages.success(request, f"{email} has been successfully added as a librarian.")
            except User.DoesNotExist:
                messages.error(request, "No user found with that email address.")
    else:
        form = AddLibrarianForm()

    return render(request, 'lending/add_librarian.html', {
        'form': form,
    })



@login_required
def return_book(request, pk):
    book_request = get_object_or_404(Request, pk=pk, requester=request.user, returned=False)
    book = book_request.requested_book
    
    loaned_copy = book.copies.filter(is_available=False, location='ON_LOAN').first()
    print(loaned_copy)
    if loaned_copy:
        loaned_copy.is_available = True
        loaned_copy.location = 'SHANNON'
        print(loaned_copy)
        loaned_copy.save()
    
    book.total_available += 1
    book.save()

    book_request.returned = True
    book_request.status = "RETURNED"
    book_request.returned_at = now()
    book_request.save()

    messages.success(request, f"'{book.book_title}' has been returned successfully!")
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
                messages.success(request, 'Review added successfully!')
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
            messages.success(request, 'Book request deleted successfully!')

    return redirect(request.META.get('HTTP_REFERER', 'lending:manage_requests'))

@login_required
@require_POST
def cancel_request(request, pk):
    book_request = get_object_or_404(Request, pk=pk, requester=request.user)
    if book_request.status == "PENDING":
        book_request.delete()
        messages.success(request, 'Request cancelled successfully!')

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

@require_POST
def mark_notification_as_read(request, notification_id):
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Authentication required")
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.mark_as_read()
        return JsonResponse({'status': 'ok'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
