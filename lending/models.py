from django.db import models

# Create your models here.
class Book(models.Model):
    book_title = models.CharField(max_length=50)
    book_author = models.CharField(max_length=50)
    genre = models.CharField(max_length=50)
    pub_year = models.PositiveIntegerField("Year Published")
    summary = models.CharField(max_length=250)
    in_stock = models.BooleanField(default=False) 
    book_cover = models.ImageField(upload_to='media/book_covers')

    def __str__(self):
        return self.book_title + ". By " + self.book_author + " (" + str(self.pub_year) + ")"
    
class User(models.Model):
    email = models.EmailField(max_length=254)
