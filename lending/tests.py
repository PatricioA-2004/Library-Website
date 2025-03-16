from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Book, Profile

#-------------Test Setup-------------------
class LendingTestSetUp(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            password="password",
        )

        cls.userlibrarian = User.objects.create_user(
            username="librarian",
            password="1234",
        )

        cls.profile_picture = SimpleUploadedFile(
            "profile_picture.jpg", b"file_content", content_type="image/jpeg",
        )

        cls.profile = Profile.objects.create(
            user = cls.user,
            profile_picture = cls.profile_picture,
        )

        cls.librarian = Profile.objects.create(
            user = cls.userlibrarian,
            profile_picture = SimpleUploadedFile("librarian.jpg", b"file_content", content_type="image/jpeg"),
        )

        cls.book1 = Book.objects.create(
            book_title="Harry Potter",
            book_author="JK Rowling",
            book_genre="Fantasy",
            pub_year=1990,
            summary="A book about wizards",
            in_stock=True,
            book_cover = SimpleUploadedFile("cover.jpg", b"file_content", content_type="image/jpeg"),
        )

        cls.book2 = Book.objects.create(
            book_title="The Great Gatsby",
            book_author="F. Scott Fitzgerald",
            book_genre="Realistic Fiction",
            pub_year="1925",
        )

        cls.sample_image = SimpleUploadedFile(
            "test_cover.jpg", b"file_content", content_type="image/jpeg",
        )
