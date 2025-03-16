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
            is_staff=False,
        )

        cls.userlibrarian = User.objects.create_user(
            username="librarian",
            password="1234",
            is_staff=True
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

# ---------------Model Tests------------------
class BookModelTest(LendingTestSetUp):
    def test_create_book(self):
        self.assertEqual(self.book1.book_title, "Harry Potter")
        self.assertEqual(self.book1.book_author, "JK Rowling")
        self.assertEqual(self.book1.book_genre, "Fantasy")
        self.assertEqual(self.book1.pub_year, 1990)
        self.assertEqual(self.book1.summary, "A book about wizards")
        self.assertTrue(self.book1.in_stock)
        self.assertIsNotNone(self.book1.book_cover)

    def test_book_str(self):
        self.assertEqual(str(self.book1), "Harry Potter. By JK Rowling (1990)")

    def test_book_summary_default(self):
        self.assertEqual(self.book2.summary, "")

    def test_book_in_stock_default(self):
        self.assertFalse(self.book2.in_stock)

class ProfileModelTest(LendingTestSetUp):
    def test_create_profile_user(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertIsNotNone(self.profile.profile_picture)

    def test_create_profile_librarian(self):
        self.assertEqual(self.librarian.user, self.userlibrarian)
        self.assertIsNotNone(self.librarian.profile_picture)

    def test_profile_str(self):
        self.assertEqual(str(self.profile), "testuser")

    def test_profile_no_picture(self):
        user2 = User.objects.create_user(username="user2", password="password")
        profile2 = Profile.objects.create(user=user2)
        self.assertIsNone(profile2.profile_picture.name)

# ---------------View Tests------------------
class IndexViewTest(LendingTestSetUp):
    def test_index_view(self):
        response = self.client.get(reverse("lending:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Harry Potter")
        self.assertContains(response, "The Great Gatsby")

class LoginViewTest(LendingTestSetUp):
    def test_login_view(self):
        response = self.client.get(reverse("lending:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lending/login.html")

class LogoutViewTest(LendingTestSetUp):
    def test_logout_view(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, '/lending/login/')

class AddBookViewTest(LendingTestSetUp):
    def test_add_book_view(self):
        self.client.login(username="libarian", password="1234")
        response = self.client.get(reverse("lending:add_book"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lending/add_book.html")

    def test_add_book_nonlibrarian(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("lending:add_book"))
    #    self.assertEqual(response.status_code, 403)

    def test_add_book_post_valid(self):
        self.client.login(username="librarian", password="1234")
        form_data = {
            "book_title": "The Hobbit",
            "book_author": "JRR Tolkien",
            "book_genre": "Fantasy",
            "pub_year": 1937,
            "summary": "A book about hobbits",
            "in_stock": True,
            "book_cover": self.sample_image,
        }
        response = self.client.post(reverse("lending:add_book"), data=form_data, follow=True)
        #self.assertRedirects(response, reverse("lending:index"))
        self.assertContains(response, "The Hobbit")


class ProfileViewTest(LendingTestSetUp):
    def test_profile_view(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("lending:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lending/profile.html")

    def test_profile_view_requires_login(self):
        response = self.client.get(reverse("lending:profile"))
    #    self.assertRedirects(response, f"/accounts/login/?next={reverse('lending:profile')}")

class BookDetailViewTest(LendingTestSetUp):
    def test_book_detail_view(self):
        response = self.client.get(reverse("lending:book_detail", args=[self.book1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lending/book_detail.html")
        self.assertContains(response, "Harry Potter")

class ProfileUpdateViewTest(LendingTestSetUp):
    def test_profile_update_requires_login(self):
        response = self.client.get(reverse("lending:profile_update"))
    #    self.assertRedirects(response, f"/accounts/login/?next={reverse('lending:profile_update')}")

    def test_profile_update_view(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("lending:profile_update"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lending/profile_update.html")
    
    def test_profile_update_post(self):
        self.client.login(username="testuser", password="password")
        form_data = {
            "profile_picture": self.sample_image,
        }
        response = self.client.post(reverse("lending:profile_update"), data=form_data, follow=True)
    #    self.assertRedirects(response, reverse("lending:profile"))
