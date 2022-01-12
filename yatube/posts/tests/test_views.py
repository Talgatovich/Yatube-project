from http import HTTPStatus

from django import forms
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, Follow  # isort:skip
from posts.tests.utils import divide  # isort:skip

FIRST_PAGE_POSTS_COUNT = 10
OK = HTTPStatus.OK
REDIRECT = HTTPStatus.FOUND

User = get_user_model()


class PostViewsTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.authorized_client.force_login(cls.user)
        # Создадим второго пользователя и автора
        cls.second_authorized_client = Client()
        cls.second_user = User.objects.create_user(username='SecondAuthor')
        cls.second_authorized_client.force_login(cls.second_user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание тестовой группы'
        )

        cls.second_group = Group.objects.create(
            title='Вторая группа',
            slug='test_group_2',
            description='Тестовое описание второй группы'
        )

        cls.post = Post.objects.create(
            text='Пост со второй группой',
            author=cls.second_user,
            group=cls.second_group

        )

        cls.post_with_group = Post.objects.create(
            text='Пост с первой группой',
            author=cls.user,
            group=cls.group

        )

        cls.base_post_text = PostViewsTests.post_with_group.text
        cls.base_post_author = PostViewsTests.post_with_group.author.username
        cls.base_post_group = PostViewsTests.post_with_group.group.title

    # Проверка namespace:name
    def test_pages_uses_correct_html(self):
        post_id = PostViewsTests.post.id
        slug = PostViewsTests.post.group.slug
        username = PostViewsTests.post.author.username
        template_pages_name = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': slug}): (
                'posts/group_list.html'),
            reverse('posts:profile', kwargs={'username': username}): (
                'posts/profile.html'),
            reverse('posts:post_detail', kwargs={'post_id': post_id}): (
                'posts/post_detail.html'),
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': post_id}): (
                'posts/create_post.html')
        }

        for reverse_name, template in template_pages_name.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.second_authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_group_list_show_correct_context(self):
        """
        Проверяем, что шаблон group_list сформирован
        с правильным контекстом.
        """
        slug = PostViewsTests.group.slug
        response = self.authorized_client.get(reverse(
            'posts:group_list', args=((slug,))))
        # Проверяем что словарь context содержит ожидаемые значения
        first_object = response.context['page_obj'][0]
        post_text = first_object.text
        post_author = first_object.author.username
        post_group = first_object.group.title

        self.assertEqual(post_text, self.base_post_text)
        self.assertEqual(post_author, self.base_post_author)
        self.assertEqual(post_group, self.base_post_group)

        # Проверка переменной group и фильтрации по группам
        page_obj = response.context.get('page_obj')
        group = response.context.get('group')
        for post in page_obj:
            with self.subTest(post=post):
                group_id = post.group.id
                self.assertEqual(group_id, group.id)

    def test_profile_show_correct_context(self):
        """
        Проверяем, что шаблон profile сформирован
        с правильным контекстом.
        """
        client_user_name = self.user.username
        response = self.authorized_client.get(reverse(
            'posts:profile', args=((client_user_name,))))

        # Проверка фильтрации по автору
        page_obj = response.context.get('page_obj')
        for post in page_obj:
            with self.subTest(post=post):
                username = post.author.username
                self.assertEqual(username, client_user_name)

        # Проверяем что словарь context содержит ожидаемые значения
        first_object = response.context['page_obj'][0]
        post_text = first_object.text
        post_author = first_object.author.username
        post_group = first_object.group.title
        self.assertEqual(post_text, self.base_post_text)
        self.assertEqual(post_author, self.base_post_author)
        self.assertEqual(post_group, self.base_post_group)

        # Проверка переменной author
        self.assertEqual(response.context.get(
            'author').username, self.base_post_author)

        # Проверка переменной post_count
        self.assertEqual(response.context.get('post_count'), 1)

    def test_post_detail_show_correct_context(self):
        """
        Проверяем, что шаблон post_detail сформирован
        с правильным контекстом.
        """
        post_id = self.post_with_group.id
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=((post_id,))))
        context_post = response.context.get('post')

        self.assertEqual(context_post.text, self.base_post_text)
        self.assertEqual(context_post.author.username, self.base_post_author)

    def test_post_create_show_correct_context(self):
        """Проверяем, что шаблон post_create сформирован
        с правильным контекстом.
        """
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Проверяем, что шаблон post_edit сформирован
        с правильным контекстом.
        """
        post_id = PostViewsTests.post.id
        response = self.second_authorized_client.get(reverse(
            'posts:post_edit', args=((post_id,))))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_is_post_exist(self):
        """
        Проверяем, что пост с группой выводится на:
        главной странице,
        странице группы,
        странице профиля.
        И не выводится на странице другой группы

        """
        post = PostViewsTests.post_with_group
        slug = post.group.slug
        author_username = post.author.username

        response_index = self.authorized_client.get(reverse('posts:index'))
        response_group = self.authorized_client.get(reverse(
            'posts:group_list', args=((slug,))))
        response_profile = self.authorized_client.get(reverse(
            'posts:profile', args=((author_username,))))
        response_another_group = self.authorized_client.get(reverse(
            'posts:group_list', args=((PostViewsTests.second_group.slug,))))

        index_page_obj = response_index.context['page_obj'][0]
        group_page_obj = response_group.context['page_obj'][0]
        profile_page_obj = response_profile.context['page_obj'][0]
        another_group_page_obj = response_another_group.context['page_obj'][0]

        self.assertEqual(index_page_obj.text, self.base_post_text)
        self.assertEqual(group_page_obj.text, self.base_post_text)
        self.assertEqual(profile_page_obj.text, self.base_post_text)
        self.assertNotIn(another_group_page_obj.text, self.base_post_text)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание тестовой группы'
        )

        cls.second_group = Group.objects.create(
            title='Вторая группа',
            slug='test_group_2',
            description='Тестовое описание второй группы'
        )

        cls.post_without_group = Post.objects.create(
            text='Пост для теста',
            author=cls.user

        )

    def setUp(self):
        # Создали второго авторизованного пользователя(он же - второй автор)
        self.second_authorized_client = Client()
        self.second_user = User.objects.create_user(username='SecondAuthor')

        # Создали посты с первым автором и первой группой
        posts = [
            Post(
                text=f'Тестовый пост{i} для теста',
                author=self.user,
                group=self.group
            ) for i in range(1, 14)
        ]
        Post.objects.bulk_create(posts)
        self.group_posts_count = len(posts)

        # Создали посты с другим автором и второй группой
        posts = [
            Post(
                text=f'Пост {i} другого автора',
                author=self.second_user,
                group=self.second_group
            ) for i in range(1, 14)
        ]
        Post.objects.bulk_create(posts)
        self.second_group_posts_count = len(posts)

    # Проверка контекста главной страницы и паджинатора
    def test_index_show_correct_context_paginator(self):
        """Проверяем, что шаблон index сформирован с правильным контекстом.
        + проверка паджинатора. Общее количество постов 27
        """
        total_posts_count = (
            self.group_posts_count
            + self.second_group_posts_count + 1
        )
        page_count = total_posts_count // FIRST_PAGE_POSTS_COUNT + 1
        remainder = divide(total_posts_count, FIRST_PAGE_POSTS_COUNT)

        response = self.authorized_client.get(reverse('posts:index'))
        response_last_page = self.authorized_client.get(reverse(
            'posts:index') + f'?page={page_count}')
        page_obj = response.context.get('page_obj')
        page_obj_2 = response_last_page.context.get('page_obj')
        is_page_obj_queryset = page_obj.object_list

        self.assertIsInstance(is_page_obj_queryset, QuerySet)
        self.assertEqual(len(page_obj), FIRST_PAGE_POSTS_COUNT)
        self.assertEqual(len(page_obj_2), remainder)

    def test_group_list_paginator(self):
        total_posts_count = self.second_group_posts_count
        page_count = total_posts_count // FIRST_PAGE_POSTS_COUNT + 1
        remainder = divide(total_posts_count, FIRST_PAGE_POSTS_COUNT)

        response = self.second_authorized_client.get(reverse(
            'posts:group_list', args=(
                (PaginatorViewsTest.second_group.slug,))))
        page_obj = response.context.get('page_obj')
        response_second_page = self.second_authorized_client.get(reverse(
            'posts:group_list', args=((PaginatorViewsTest.second_group.slug,)))
            + f'?page={page_count}')
        second_page_obj = response_second_page.context.get('page_obj')

        self.assertEqual(len(page_obj), FIRST_PAGE_POSTS_COUNT)
        self.assertEqual(len(second_page_obj), remainder)

    def test_profile_show_correct_context(self):
        client_user_name = self.user.username
        response = self.authorized_client.get(reverse(
            'posts:profile', args=((client_user_name,))))
        author_posts_count = response.context.get('post_count')
        page_count = author_posts_count // FIRST_PAGE_POSTS_COUNT + 1
        remainder = divide(author_posts_count, FIRST_PAGE_POSTS_COUNT)

        second_response = self.authorized_client.get(reverse(
            'posts:profile', args=((client_user_name,)))
            + f'?page={page_count}')
        page_obj = response.context.get('page_obj')
        second_page_obj = second_response.context.get('page_obj')

        self.assertEqual(len(page_obj), FIRST_PAGE_POSTS_COUNT)
        self.assertEqual(len(second_page_obj), remainder)


class FollowViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.first_user = User.objects.create_user(username='JustUser')
        cls.authorized_client.force_login(cls.first_user)

        cls.favorite_author = Client()  # Создадим ибранного автора
        cls.second_user = User.objects.create_user(username='FavoriteAuthor')
        cls.favorite_author.force_login(cls.second_user)

        cls.another_client = Client()
        cls.third_user = User.objects.create_user(username='AnotherUser')
        cls.another_client.force_login(cls.third_user)

    def setUp(self):
        self.post = Post.objects.create(
            text='Пост от избранного автора',
            author=self.second_user
        )

        self.author_user_name = self.post.author
        self.first_cnt_client = self.first_user.follower.count()
        self.first_cnt_author = self.author_user_name.following.count()

        #  Авторизованный клиент подписывается на автора
        self.response = self.authorized_client.get(reverse(
            'posts:profile_follow', args=((self.author_user_name,))))

    def test_authorized_client_can_create_follower(self):
        """
        Проверка, что авторизованный клиент
        может подписаться
        """
        second_cnt_client = self.first_user.follower.count()
        second_cnt_author = self.author_user_name.following.count()
        exist = Follow.objects.filter(
            author=self.second_user, user=self.first_user
        ).exists()

        self.assertTrue(exist)
        self.assertEqual(self.response.status_code, REDIRECT)
        self.assertEqual(second_cnt_client, self.first_cnt_client + 1)
        self.assertEqual(second_cnt_author, self.first_cnt_author + 1)

    def test_authorized_client_can_delete_follower(self):
        """
        Проверка, что авторизованный клиент
        может отписаться
        """
        #  Начальное количество подписок и подписчиков
        second_cnt_client = self.first_user.follower.count()
        second_cnt_author = self.author_user_name.following.count()
        #  Отписались от автора
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', args=((self.author_user_name,))))
        #  Конечное количество подписок и подписчиков
        third_cnt_client = self.first_user.follower.count()
        third_cnt_author = self.author_user_name.following.count()
        exist = Follow.objects.filter(
            author=self.second_user, user=self.first_user
        ).exists()

        self.assertFalse(exist)
        self.assertEqual(self.response.status_code, REDIRECT)
        self.assertEqual(third_cnt_client, second_cnt_client - 1)
        self.assertEqual(third_cnt_author, second_cnt_author - 1)

    def test_authorized_client_have_favorite_posts(self):
        """
        Проверяем, что у подписанного пользователя
        появляется пост в ленте
        """
        form_data = {
            'text': 'Новый избранный пост',
            'author': self.second_user
        }
        self.favorite_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        response = self.authorized_client.get(
            reverse('posts:follow_index'))  # Перешли в ленту подписок

        post_text = response.context['page_obj'][0].text

        self.assertEqual(post_text, form_data['text'])

    def test_another_client_doesnot_have_favorite_posts(self):
        """
        Проверяем, что у неподписанного пользователя
        пост в ленте не появляется
        """
        form_data = {
            'text': 'Еще один избранный пост',
            'author': self.second_user
        }
        self.favorite_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        response = self.another_client.get(
            reverse('posts:follow_index'))  # Перешли в ленту подписок
        post_text = Post.objects.all().first().text

        #  Проверили, что пост создался
        self.assertEqual(post_text, form_data['text'])
        #  Проверили, что поста нет в ленте
        self.assertNotContains(response, post_text)
