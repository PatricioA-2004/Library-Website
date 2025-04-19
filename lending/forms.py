from django import forms
from .models import Book, Request, User
from .models import Profile
from .models import Collection
from .models import Review

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'book_title',
            'book_author',
            'book_genre',
            'pub_year',
            'summary',
            'book_cover',
            'total_copies',
            # 'total_available',
            # 'in_stock'
        ]
        widgets = {
            'publication_year': forms.NumberInput(attrs={'min': 1000, 'max': 9999}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture']

class CollectionForm(forms.ModelForm):
    books = forms.ModelMultipleChoiceField(
        queryset=Book.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    allowed_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_staff=False),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Collection
        fields = ['collection_name', 'private', 'books', 'allowed_users']
        
    def __init__(self, *args, user_is_staff=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not user_is_staff:
            # Hide private field for non-staff users
            self.fields['private'].widget = forms.HiddenInput()
            self.fields['private'].initial = False

        edit_collection = kwargs.get('instance', None)
        public_books = Book.objects.exclude(collection__private=True)
        if edit_collection:
            my_books = edit_collection.books.all()
            self.fields['books'].queryset = (public_books | my_books).distinct()
        else:
            self.fields['books'].queryset = public_books.distinct()

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['requested_book']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['requested_book'].queryset = Book.objects.filter(in_stock=True)

class AddLibrarianForm(forms.Form):
    email = forms.EmailField(label='', help_text='Input Librarian Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(attrs={'class': 'star-rating'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your review here...'})
        }
