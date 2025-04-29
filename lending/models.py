from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Book(models.Model):
    book_title = models.CharField(max_length=100, verbose_name="Name of Book *")
    book_author = models.CharField(max_length=50, verbose_name="Author of Book *")
    book_genre = models.CharField(max_length=50, verbose_name="Genre of Book *")
    pub_year = models.PositiveIntegerField("Year Published *")
    isbn = models.CharField('ISBN *', max_length=13, default='0000000000000', blank = False)
    summary = models.TextField(max_length=500, default="", verbose_name="Summary of Book *")
    in_stock = models.BooleanField(default=False)
    book_cover = models.ImageField(upload_to='media/book_covers', blank=True, null=True)
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
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="collections", db_index = True)
    allowed_users = models.ManyToManyField(User)
    books = models.ManyToManyField(Book)
    private = models.BooleanField(db_index = True) # Only librarians can make private collections
    collection_name = models.CharField(max_length=100, verbose_name="Collection Name *")
    description = models.CharField(max_length=200, default="", verbose_name="Description of Collection *")


class Request(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requested_books")
    requested_book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="requests")
    requested_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    returned = models.BooleanField(default=False)
    returned_at = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('RETURNED', 'Returned')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

class CollectionRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collection_requests')
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        unique_together = ['user', 'collection']

    def __str__(self):
        return f"{self.user.username} - {self.collection.collection_name} ({self.status})"


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    RATING_CHOICES = [
        (1, '1 star'),
        (2, '2 stars'),
        (3, '3 stars'),
        (4, '4 stars'),
        (5, '5 stars'),
    ]
    rating = models.IntegerField(choices=RATING_CHOICES, null=False)
    comment = models.TextField(max_length=500, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['book', 'user']

    def __str__(self):
        return f"Review by {self.user.username} for {self.book.book_title}"

class BookCopy(models.Model):
    LOCATION_CHOICES = [
        ('SHANNON', 'Shannon Library'),
        ('BROWN', 'Brown Science and Engineering Library'),
        ('CLEMONS', 'Clemons Library'),
        ('ON_LOAN', 'On Loan')
    ]
    LIBRARY_CHOICES = [
        ('SHANNON', 'Shannon Library'),
        ('BROWN', 'Brown Science and Engineering Library'),
        ('CLEMONS', 'Clemons Library')
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    location = models.CharField(max_length=50, choices=LIBRARY_CHOICES, default='SHANNON')
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Copy of {self.book.book_title} at {self.location}"
    
class AlternateCover(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="alternate_covers")
    image = models.ImageField(upload_to="alternate_covers/", blank=True, null=True)

