from django.db import models

# Create your models here.
class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Book(models.Model):
    book_title = models.CharField(max_length=200)
    book_author = models.CharField(max_length=200)
    genres = models.ManyToManyField(Genre, related_name="books")
    #Alternate: genres = ArrayField(models.CharField(max_length=50), blank=True, default=list)
    pub_year = models.PositiveIntegerField("Year Published")
    in_stock = models.BooleanField(default=False) 

    def __str__(self):
        return self.book_title + " " + self.book_author + ", " + str(self.pub_year)
    
class User(models.Model):
    email = models.EmailField(max_length=254)
