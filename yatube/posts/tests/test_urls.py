from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse
from faker import Faker

from ..models import Post, Group

User = get_user_model()
login_url = reverse('users:login')
fake = Faker()


class PostsURLTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=fake.user_name())
        cls.nonauthor = User.objects.create_user(username=fake.user_name())
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_nonauthor = Client()
        cls.authorized_nonauthor.force_login(cls.nonauthor)

        cls.group = Group.objects.create(
            title=fake.text(max_nb_chars=200),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=200),
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(max_nb_chars=200)
        )

    def setUp(self):
        cache.clear()

    def test_url_exists_guest(self):
        """
        Проверяем, что публичные страницы доступны
        для неавторизованного пользователя.
        """
        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', args=(PostsURLTests.group.slug,)),
            reverse('posts:profile', args=(PostsURLTests.user.username,)),
            reverse('posts:post_detail', args=(PostsURLTests.post.id,)),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_redirect_guest(self):
        """
        Проверяем, что приватные страницы недоступны для неавторизованного
        пользователя и происходит редирект на страницу авторизации.
        """
        urls = [
            reverse('posts:post_edit', args=(PostsURLTests.post.id,)),
            reverse('posts:post_create')
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f'{login_url}?next={url}')

    def test_url_exists_auth(self):
        """
        Проверяем, что приватные адреса доступны авторизованному пользователю
        и автору доступно редактирование своих постов.
        """
        urls = [
            reverse('posts:post_edit', args=(PostsURLTests.post.id,)),
            reverse('posts:post_create')
        ]
        for url in urls:
            with self.subTest(url=url):
                response = PostsURLTests.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_redirect_nonauthor(self):
        """
        Проверяем, что авторизованный пользователь при попытке редактирования
        чужого поста перенаправляется на страницу просмотра поста.
        """
        response = PostsURLTests.authorized_nonauthor.get(
            reverse('posts:post_edit', args=(PostsURLTests.post.id,))
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(PostsURLTests.post.id,))
        )

    def test_templates_guest(self):
        """
        Проверяем, что вызываются верные шаблоны по запросу
        неавторизованного пользователя.
        """
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', args=(PostsURLTests.group.slug,)): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', args=(PostsURLTests.user.username,)): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', args=(PostsURLTests.post.id,)): (
                'posts/post_detail.html'
            ),
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertTemplateUsed(response, template)

    def test_templates_authorized(self):
        """
        Проверяем, что вызываются верные шаблоны по запросу
        авторизованного пользователя.
        """
        templates_url_names = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', args=(PostsURLTests.post.id,)): (
                'posts/create_post.html'
            )
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = PostsURLTests.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_nonexisting_page_404(self):
        response = self.client.get('/posts/notapostid/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
