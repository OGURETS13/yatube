from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from faker import Faker

from ..models import Group, Post

User = get_user_model()
fake = Faker()


class PostModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=fake.user_name())
        cls.group = Group.objects.create(
            title=fake.text(max_nb_chars=200),
            slug=fake.slug(),
            description=fake.text(max_nb_chars=200),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(max_nb_chars=200)
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        test_models = {
            post: post.text[:settings.MAX_POST_STR_LENGTH],
            group: group.title
        }
        for model, expected_value in test_models.items():
            with self.subTest(model=model):
                self.assertEqual(str(model), expected_value,
                                 'Что-то не так')
