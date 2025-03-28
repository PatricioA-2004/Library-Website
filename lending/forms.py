from django import forms
from .models import Book
from .models import Profile

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