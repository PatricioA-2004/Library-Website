from django import forms
from .models import Book, Request
from .models import Profile
from .models import Collection

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
            'total_available',
            'in_stock'
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
        queryset=Book.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Collection
        fields = ['collection_name', 'private', 'books']
        
    def __init__(self, *args, user_is_staff=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not user_is_staff:
            # Hide private field for non-staff users
            self.fields['private'].widget = forms.HiddenInput()
            self.fields['private'].initial = False
    
class CollectionChangeForm(forms.ModelForm):
    books_to_add = forms.ModelMultipleChoiceField(
        queryset=Book.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    books_to_remove = forms.ModelMultipleChoiceField(
        queryset=Book.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Collection
        fields = ['collection_name', 'private', 'books']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['books_to_add'].queryset = Book.objects.exclude(id__in=self.instance.books.values_list('id', flat=True))
            self.fields['books_to_remove'].queryset= self.instance.books.all()

    def save_edits(self, commit=True):
        collection = super().save(commit=False)
        if commit:
            self.instance.books.add(*self.cleaned_data['books_to_add'])
            self.instance.books.remove(*self.cleaned_data['books_to_remove'])
            collection.save()
        return collection

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['requested_book']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['requested_book'].queryset = Book.objects.filter(in_stock=True)
