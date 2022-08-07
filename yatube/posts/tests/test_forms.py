import shutil

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from faker import Faker

from .utils import (
    small_gif,
    TEMP_MEDIA_ROOT,
    uploaded_image,
)
from ..models import Post, Group, Comment

User = get_user_model()
fake = Faker()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username=fake.user_name())
        cls.user2 = User.objects.create_user(username=fake.user_name())

        cls.group1 = Group.objects.create(
            title=fake.text(max_nb_chars=20),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=100),
        )
        cls.group2 = Group.objects.create(
            title=fake.text(max_nb_chars=20),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=100),
        )
        cls.login_url = reverse('users:login')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user1)
        uploaded_image.seek(0)

    def test_auth_user_can_create_post_form_valid(self):
        """
        Проверяем, что при отправлении валидной формы
        авторизованным пользователем создаётся новый пост
        и происходит редирект в профиль автора.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': fake.text(max_nb_chars=100),
            'group': PostFormTests.group1.id,
            'image': uploaded_image
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        new_post = Post.objects.first()

        test_data = {
            new_post.text: form_data['text'],
            new_post.author: PostFormTests.user1,
            new_post.group: PostFormTests.group1,
            new_post.image.read(): small_gif
        }

        for post_field, expected in test_data.items():
            with self.subTest(post_field=post_field):
                self.assertEqual(post_field, expected)

        self.assertEqual(
            Post.objects.count(),
            posts_count + 1
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args=(PostFormTests.user1,))
        )

    def test_author_can_edit_post_form_valid(self):
        """
        Проверяем, что при отправлении валидной формы
        авторизованным пользователем редактируется существующий пост
        и происходит редирект на страницу с информацией о посте.
        """
        test_post = Post.objects.create(
            text=fake.text(max_nb_chars=100),
            author=PostFormTests.user1,
            group=PostFormTests.group1,
        )

        posts_count = Post.objects.count()

        form_data = {
            'text': fake.text(max_nb_chars=100),
            'group': PostFormTests.group2.id,
            'image': uploaded_image
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(test_post.id,)),
            data=form_data,
            follow=True
        )
        test_post.refresh_from_db()

        test_data = {
            test_post.text: form_data['text'],
            test_post.author: PostFormTests.user1,
            test_post.group: PostFormTests.group2,
            test_post.image.read(): small_gif
        }

        self.assertEqual(
            Post.objects.count(),
            posts_count
        )

        for post_field, expected in test_data.items():
            with self.subTest(post_field=post_field):
                self.assertEqual(post_field, expected)

        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=(test_post.id,)
            )
        )

    def test_authorized_nonauthor_cant_edit(self):
        """
        Проверяем, что авторизованный пользователь не может
        редактировать чужой пост.
        """
        test_post = Post.objects.create(
            text=fake.text(max_nb_chars=100),
            author=PostFormTests.user2,
            group=PostFormTests.group1
        )

        posts_count = Post.objects.count()

        form_data = {
            'text': fake.text(max_nb_chars=100),
            'group': PostFormTests.group2.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(test_post.id,)),
            data=form_data,
            follow=True
        )
        test_post.refresh_from_db()

        self.assertEqual(
            Post.objects.count(),
            posts_count
        )
        self.assertNotEqual(test_post.text, form_data['text'])
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(test_post.id,))
        )

    def test_guest_cannot_create(self):
        """
        Проверяем, что неавторизованный пользователь не может создать пост,
        и его перенаправляет на страницу регистрации.
        """
        url = reverse('posts:post_create')
        posts_count = Post.objects.count()

        form_data = {
            'text': fake.text(max_nb_chars=100),
            'group': PostFormTests.group1.id
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(
            Post.objects.count(),
            posts_count
        )
        self.assertRedirects(
            response,
            f'{PostFormTests.login_url}?next={url}'
        )


class CommentFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=fake.user_name())

        cls.group = Group.objects.create(
            title=fake.text(max_nb_chars=20),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=100),
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(max_nb_chars=200),
            group=cls.group,
            image=uploaded_image
        )

        cls.login_url = reverse('users:login')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentFormTests.user)

    def test_guest_cannot_comment(self):
        """
        Проверяем, что неавторизованный пользователь не может создать
        комментарий, и его перенаправляет на страницу регистрации.
        """
        comments_count = Comment.objects.count()

        form_data = {
            'text': fake.text(max_nb_chars=100),
        }
        response = self.client.post(
            reverse('posts:add_comment', args=(CommentFormTests.post.id,)),
            data=form_data,
            follow=True
        )

        self.assertEqual(
            Comment.objects.count(),
            comments_count
        )
        self.assertRedirects(
            response,
            f"{CommentFormTests.login_url}?next="
            f"{reverse('posts:add_comment', args=(CommentFormTests.post.id,))}"
        )

    def test_authorized_users_can_comment(self):
        """
        Проверяем, что авторизованный пользователь может создать
        комментарий.
        """
        comments_count = Comment.objects.count()

        form_data = {
            'text': fake.text(max_nb_chars=100),
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(CommentFormTests.post.id,)),
            data=form_data,
            follow=True
        )

        self.assertEqual(
            Comment.objects.count(),
            comments_count + 1
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(CommentFormTests.post.id,))
        )
        self.assertEqual(
            response.context['comments'][0].text,
            form_data['text']
        )
