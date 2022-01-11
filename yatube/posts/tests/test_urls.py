from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()
OK = HTTPStatus.OK
REDIRECT = HTTPStatus.FOUND
NOT_FOUND = HTTPStatus.NOT_FOUND


class StaticURLTests(TestCase):

    def setUp(self):
        # Устанавливаем данные для тестирования
        # Создаём экземпляр клиента. Он неавторизован.
        self.guest_client = Client()

    def test_homepage(self):

        # Делаем запрос к главной странице и проверяем статус
        response = self.guest_client.get('/')
        # Утверждаем, что для прохождения теста код должен быть равен 200
        self.assertEqual(response.status_code, OK)

    def test_about_author(self):

        # Делаем запрос к странице об авторе и проверяем статус
        response = self.guest_client.get('/about/author/')
        # Утверждаем, что для прохождения теста код должен быть равен 200
        self.assertEqual(response.status_code, OK)

    def test_about_tech(self):

        # Делаем запрос к странице технологии и проверяем статус
        response = self.guest_client.get('/about/tech/')
        # Утверждаем, что для прохождения теста код должен быть равен 200
        self.assertEqual(response.status_code, OK)


class PostURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='Noname')
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание тестовой группы'
        )

        cls.post = Post.objects.create(
            text='Тестовый пост для теста',
            author=cls.user,
            group=cls.group
        )

        cls.slug = PostURLTests.group.slug

        cls.name = PostURLTests.post.author.username

    def setUp(self):
        self.not_author = Client()
        self.not_author_client = User.objects.create_user(username='Stas')
        self.not_author.force_login(self.not_author_client)

    def test_html_templates(self):
        """
        Проверка соответствия шаблонов адресам
        """
        post_id = PostURLTests.post.id
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.slug}/': 'posts/group_list.html',
            f'/profile/{self.name}/': 'posts/profile.html',
            f'/posts/{post_id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{post_id}/edit/': 'posts/create_post.html',
            'posts/unexisting_page/': 'core/404.html',
            '/follow/': 'posts/follow.html'

        }

        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress, template=template):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_page_is_available_guest_client(self):
        """
        Для неавторизованного пользователя доступны страницы:
        главная, посты группы, подробная информация о посте,
        профиль автора поста.
        Страницы создания поста и редактирования,
        поста с избранными авторами,
        подписки на автора и отписки от него осуществляют редирект.
        Несуществующая страница - недоступна

        """

        post_id = PostURLTests.post.id
        templates_url_names = {
            '/': OK,
            f'/group/{self.slug}/': OK,
            f'/profile/{self.name}/': OK,
            f'/posts/{post_id}/': OK,
            '/create/': REDIRECT,
            f'/posts/{post_id}/edit/': REDIRECT,
            'posts/unexisting_page/': NOT_FOUND,
            '/follow/': REDIRECT,
            f'/profile/{self.name}/follow/': REDIRECT,
            f'/profile/{self.name}/unfollow/': REDIRECT

        }

        for adress, value in templates_url_names.items():
            with self.subTest(adress=adress, value=value):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, value)

    def test_page_is_available_authorized_client_create(self):
        """ Страницы создания, редактирования поста доступна
         авторизованному  пользователю(он же автор)
        """
        post_id = PostURLTests.post.id
        adress = [
            '/create/',
            f'/posts/{post_id}/edit/',
            '/follow/'

        ]

        for adress in adress:
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, OK)

    def test_page_not_available_authorized_client_not_author_edit(self):
        """
        Страница редактирования поста недоступна
         никому, кроме автора поста
        """
        post_id = PostURLTests.post.id
        response = self.not_author.get(f'/posts/{post_id}/edit/')
        self.assertEqual(response.status_code, REDIRECT)

    def test_guest_redirect_to_login(self):
        """
        Проверяем происходит ли редирект
        на страницу авторизации при попытке
        неавторизованного пользователя
        перейти на страницу с постами избранных
        авторов,
        подписаться на автора и отписаться
        от него
        """
        url_list = [
            '/follow/',
            f'/profile/{self.name}/follow/',
            f'/profile/{self.name}/unfollow/'
        ]
        for adress in url_list:
            response = self.guest_client.get(adress)
            self.assertRedirects(response, (reverse(
                'users:login') + '?next=' + adress))
