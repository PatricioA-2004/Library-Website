from django.db import models

# Create your models here.


class Book(models.Model):
    book_title = models.CharField(max_length=200)
    book_author = models.CharField(max_length=200)
    book_genre = models.CharField(max_length=200)
    pub_year = models.DateTimeField("date published")
    # genre


    def __str__(self):
        return self.book_title + " " + self.book_author + " " + self.book_genre
    
class User(models.Model):
    email = models.EmailField(max_length=254)
