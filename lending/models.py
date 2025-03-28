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
    total_copies = models.PositiveIntegerField("Total Copies", default=1)
    total_available = models.PositiveIntegerField("Total Available", default=1)
    def __str__(self):
        return self.book_title + ". By " + self.book_author + " (" + str(self.pub_year) + ")"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='media/profile_pictures', blank=True, null=True)

    def __str__(self):
        return str(self.user)
        
class Collection(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="collections")
    books = models.ManyToManyField(Book)
    private = models.BooleanField() # Only librarians can make private collections
    collection_name = models.CharField(max_length=100)

class Request(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requested_books")
    requested_book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="requests")

