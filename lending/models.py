from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Book(models.Model):
    book_title = models.CharField(max_length=100)
    book_author = models.CharField(max_length=50)
    book_genre = models.CharField(max_length=50)
    pub_year = models.PositiveIntegerField("Year Published")
    summary = models.TextField(max_length=500, default="")
    in_stock = models.BooleanField(default=False) 
    book_cover = models.ImageField(upload_to='media/book_covers')
    total_copies = models.PositiveIntegerField("Total Copies")
    total_available = models.PositiveIntegerField("Total Available")
    def __str__(self):
        return self.book_title + ". By " + self.book_author + " (" + str(self.pub_year) + ")"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='media/profile_pictures', blank=True, null=True)

    def __str__(self):
        return str(self.user)
        
class Collection(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    books = models.ManyToManyField(Book)
    private = models.BooleanField() # Only librarians can make private collections
    collection_name = models.CharField(max_length=100)

class Request(models.Model):
    requester = models.OneToOneField(User, on_delete=models.CASCADE)
    requested_book = models.OneToOneField(Book, on_delete=models.CASCADE)

