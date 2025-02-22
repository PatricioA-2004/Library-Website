from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['book_title', 'book_author', 'book_genre', 'pub_year']
        widgets = {
            'publication_year': forms.NumberInput(attrs={'min': 1000, 'max': 9999}),
        } 