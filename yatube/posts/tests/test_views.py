import random
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from faker import Faker

from .utils import (
    TEMP_MEDIA_ROOT,
    uploaded_image
)
from ..forms import PostForm
from ..models import Follow, Group, Post

User = get_user_model()
fake = Faker()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=fake.user_name())
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title=fake.text(max_nb_chars=200),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=200),
        )

        cls.group2 = Group.objects.create(
            title=fake.text(max_nb_chars=200),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=200),
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(max_nb_chars=200),
            group=cls.group,
            image=uploaded_image
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()

    def test_cache_index(self):
        """
        Проверяем, что если удалить пост после первой загрузки страницы
        и создания кеша, пост останется на странице до принудительной
        очистки кеша.
        """
        new_post = Post.objects.create(
            author=PostsViewsTests.user,
            text=fake.text(max_nb_chars=200),
            group=PostsViewsTests.group
        )
        response = self.client.get(reverse('posts:index'))
        page_content1 = response.content
        new_post.delete()
        response = self.client.get(reverse('posts:index'))
        page_content2 = response.content

        self.assertEqual(page_content1, page_content2)

        cache.clear()
        response = self.client.get(reverse('posts:index'))
        page_content3 = response.content

        self.assertNotEqual(page_content2, page_content3)

    def test_post_in_index(self):
        """
        Проверяем, что в контекст домашней страницы передаётся ключ
        page_obj, первый пост на странице - последний опубликованный пост.
        """
        response = self.client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        self.assertEqual(
            response.context['page_obj'][0],
            PostsViewsTests.post
        )
        self.assertEqual(
            response.context['page_obj'][0].image,
            PostsViewsTests.post.image
        )

    def test_context_group_posts(self):
        """
        Проверяем, что в контекст страницы со списком групп передаются ключи
        group и page_obj, группа соответствует переданной в запросе,
        первый пост на странице - последний пост, опубликованный в этой группе.
        """
        response = self.client.get(
            reverse('posts:group_list', args=(PostsViewsTests.group.slug,))
        )

        self.assertIn('group', response.context)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['group'], PostsViewsTests.group)
        self.assertEqual(
            response.context['page_obj'][0],
            PostsViewsTests.post
        )
        self.assertEqual(
            response.context['page_obj'][0].image,
            PostsViewsTests.post.image
        )

    def test_context_profile(self):
        """
        Проверяем, что в контекст страницы профиля пользователя передаются
        ключи authot и page_obj, профиль соответствует пользователю,
        переданному в запросе, первый пост на странице - последний пост,
        опубликованный этим пользователем.
        """
        response = self.client.get(
            reverse('posts:profile', args=(PostsViewsTests.user.username,))
        )

        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['author'], PostsViewsTests.user)
        self.assertEqual(
            response.context['page_obj'][0],
            PostsViewsTests.post
        )
        self.assertEqual(
            response.context['page_obj'][0].image,
            PostsViewsTests.post.image
        )

    def test_context_post_detail(self):
        """
        Проверяем, что в контекст страницы информации о посте передаётся
        ключ post и пост соответствует тому, который передан в запросе.
        """
        response = self.client.get(
            reverse('posts:post_detail', args=(PostsViewsTests.post.id,))
        )

        self.assertIn('post', response.context)
        self.assertEqual(response.context['post'], PostsViewsTests.post)
        self.assertEqual(
            response.context['post'].image,
            PostsViewsTests.post.image
        )

    def test_context_post_create_and_edit(self):
        """
        Проверяем, что в контекст страниц создания и редактирования постов
        передаётся ключ form и тип объекта формы - PostForm.
        Если в контексте есть ключ is_edit, то его значение True.
        """
        urls = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', args=(PostsViewsTests.post.id,))
        ]

        for url in urls:
            response = PostsViewsTests.authorized_client.get(url)

            self.assertIn('form', response.context)
            self.assertIsInstance(response.context['form'], PostForm)
            if 'is_edit' in response.context:
                self.assertTrue(response.context['is_edit'])

    def test_post_not_in_wrong_group(self):
        """
        Проверяем, что поста нет на странице группы,
        к которой он не принадлежит.
        """
        response = self.client.get(
            reverse('posts:group_list', args=(PostsViewsTests.group2.slug,))
        )
        self.assertNotIn(
            PostsViewsTests.post,
            response.context['page_obj'].object_list
        )


class PostsFollowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            username=fake.user_name()
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def setUp(self):
        self.author = User.objects.create(
            username=fake.user_name()
        )
        self.post_number = random.randint(1, settings.POSTS_PER_PAGE - 1)
        Post.objects.bulk_create([
            Post(
                text=fake.text(max_nb_chars=200),
                author=self.author,
            ) for _ in range(self.post_number)
        ])

    def test_follow_index(self):
        """
        Проверяем, что после подписки на автора на странице подписок
        появляются его посты
        """
        response = PostsFollowTests.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']),
            0
        )

        PostsFollowTests.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.author.username,)
            ))
        response = PostsFollowTests.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']),
            self.post_number
        )

    def test_unfollow_index(self):
        """
        Проверяем, что после отписки от автора на странице подписок
        нет его постов
        """
        Follow.objects.create(
            user=PostsFollowTests.user,
            author=self.author
        )
        response = PostsFollowTests.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']),
            self.post_number
        )

        PostsFollowTests.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.author.username,)
            ))
        response = PostsFollowTests.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']),
            0
        )

    def test_new_posts_emerge_on_follow_index(self):
        """
        Новый пост появляется в ленте подписчика, но не появляется в ленте
        неподписчика.
        """
        user2 = User.objects.create_user(username=fake.slug())
        user2_client = Client()
        user2_client.force_login(user2)
        Follow.objects.create(
            user=PostsFollowTests.user,
            author=self.author
        )
        Post.objects.create(
            text=fake.text(max_nb_chars=200),
            author=self.author,
        )

        response = PostsFollowTests.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']),
            self.post_number + 1
        )

        response = user2_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']),
            0
        )

    def test_user_cannot_follow_self(self):
        """
        Проверяем, что подписаться на самого себя не удаётся, а при попытке
        не создаётся новых подписок.
        """
        follow_count = Follow.objects.count()
        PostsFollowTests.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(PostsFollowTests.user.username,)
            ))
        self.assertTrue(
            not Follow.objects.filter(
                user=PostsFollowTests.user,
                author=PostsFollowTests.user
            ).exists()
        )
        self.assertEqual(
            Follow.objects.count(),
            follow_count
        )


class PaginatorViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=fake.slug())
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title=fake.text(max_nb_chars=200),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=200),
        )

        cls.posts_on_two_pages = random.randint(
            settings.POSTS_PER_PAGE + 1,
            settings.POSTS_PER_PAGE * 2
        )

        Post.objects.bulk_create([
            Post(
                text=fake.text(max_nb_chars=200),
                author=PaginatorViewsTests.user,
                group=PaginatorViewsTests.group
            ) for _ in range(cls.posts_on_two_pages)
        ])

    def setUp(self):
        cache.clear()

    def test_right_number_of_posts_per_page(self):
        """
        Проверяем, что на страницах верное количество постов.
        """
        urls = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                args=(PaginatorViewsTests.group.slug,)
            ),
            reverse('posts:profile', args=(PaginatorViewsTests.user.username,))
        ]

        posts_on_page = [
            settings.POSTS_PER_PAGE,
            PaginatorViewsTests.posts_on_two_pages - settings.POSTS_PER_PAGE
        ]

        for i in range(2):
            for url in urls:
                with self.subTest(url=url):
                    response = self.client.get(
                        url, data={'page': i + 1}
                    )
                    self.assertEqual(
                        len(response.context['page_obj']),
                        posts_on_page[i]
                    )
