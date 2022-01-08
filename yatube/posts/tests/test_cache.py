from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Post  # isort:skip

User = get_user_model()


class CacheTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.authorized_client.force_login(cls.user)

    def setUp(self):
        self.post = Post.objects.create(
            text='ТЕСТ ТЕСТ ТЕСТ',
            author=self.user
        )

    def test_index_cache(self):
        """
        Проверка кеширования главной страницы.
        При удалении записи из БД она остается в
        response.content главной страницы до тех пор,
        пока кэш не будет очищен принудительно.
        """
        post_text = self.post.text
        response = self.authorized_client.get(reverse('posts:index'))
        self.post.delete()

        self.assertIn(post_text, response.content.decode('utf-8'))
        page_obj = response.context.get('page_obj')
        key = make_template_fragment_key('index_page', [page_obj.number])
        cache.delete(key)
        response_1 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotIn(post_text, response_1.content.decode('utf-8'))
