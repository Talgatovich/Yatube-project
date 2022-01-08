import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Post, Group  # isort:skip

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

OK = HTTPStatus.OK
REDIRECT = HTTPStatus.FOUND

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Новая группа',
            slug='new_group',
            description='описание тестовой группы'
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.post = Post.objects.create(
            text='Текст поста',
            author=cls.user,
            group=cls.group,
            image=uploaded

        )
        cls.post_count = Post.objects.count()
        cls.comment_count = cls.post.comments.count()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_post_create(self):
        """
        проверяем, что при отправке поста с картинкой
        через форму PostForm создаётся запись в базе данных.
        """
        small_gif_1 = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_1 = SimpleUploadedFile(
            name='small_1.gif',
            content=small_gif_1,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'author': self.user,
            'image': uploaded_1

        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        client_user_name = self.user.username
        first_post = Post.objects.all().first()
        img = form_data['image'].name

        self.assertEqual(Post.objects.count(), self.post_count + 1)
        self.assertEqual(response.status_code, OK)
        self.assertRedirects(response, reverse(
            'posts:profile', args=((client_user_name,))))
        self.assertEqual(first_post.text, form_data['text'])
        self.assertEqual(first_post.author, form_data['author'])
        self.assertEqual(first_post.image.name, f'posts/{img}')

    def test_guest_cannot_create_post(self):
        """
        Проверяем, что неавторизованный
        клиент не может создать пост и
        при попытке перехода на страницу создания поста
        происходит редирект
        """
        form_data = {
            'text': 'Невозможный пост от гостя',
            'author': self.user

        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), self.post_count)
        self.assertRedirects(response, (reverse(
            'users:login') + '?next=' + reverse('posts:post_create')))

    def test_post_edit(self):
        """
        Проверка формы редактирования поста.
        """
        old_post_text = PostFormTest.post.text
        post_id = PostFormTest.post.id
        form_data = {
            'text': 'Обновленный текст',
            'author': self.user

        }

        response = self.authorized_client.post(
            reverse('posts:post_edit', args=((post_id,))),
            data=form_data,
            follow=True
        )
        first_post = Post.objects.all().first()
        post_text = first_post.text
        post_author = first_post.author

        self.assertEqual(response.status_code, OK)
        self.assertNotEquals(old_post_text, post_text)
        self.assertEqual(Post.objects.count(), self.post_count)
        self.assertEqual(post_text, form_data['text'])
        self.assertEqual(post_author, form_data['author'])

    def test_check_context_with_picture(self):
        """
        проверяем, что при выводе поста с картинкой
        изображение передаётся в словаре context
        на главную страницу,
        на страницу профайла,
        на страницу группы,
        на отдельную страницу поста
        """
        slug = self.post.group.slug
        username = self.post.author.username
        id = self.post.id
        index = reverse('posts:index')
        profile = reverse('posts:profile', args=((username,)))
        group = reverse('posts:group_list', args=((slug,)))
        post_detail = reverse('posts:post_detail', args=((id,)))
        reverse_list = [
            index,
            profile,
            group,
            post_detail
        ]
        for adress in reverse_list:
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                if adress == post_detail:
                    post_image = response.context.get('post').image
                else:
                    post_image = response.context['page_obj'][0].image
                self.assertEqual(post_image, self.post.image)

    def test_guest_cannot_create_comments(self):
        """
        Проверяем не появляется ли комментарий от
        неавторизованного пользователя и
        происходит ли редирект на страницу авторизации
        """
        form_data = {
            'text': 'Невозможный коммент от гостя'

        }
        post_id = self.post.id
        response = self.guest_client.post(
            reverse('posts:add_comment', args=((post_id,))),
            data=form_data,
            follow=True
        )

        self.assertEqual(self.post.comments.count(), self.comment_count)
        self.assertRedirects(response, (reverse(
            'users:login') + '?next=' + reverse(
                'posts:add_comment', args=((post_id,)))))

    def test_authorized_client_can_create_comments(self):
        """
        Проверяем появляется ли комментарий от
        авторизованного пользователя и
        происходит ли редирект на страницу с
        подробной информацией о посте
        """
        form_data = {
            'text': 'Новый комментарий'

        }
        post_id = self.post.id
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=((post_id,))),
            data=form_data,
            follow=True
        )

        self.assertEqual(self.post.comments.count(), self.comment_count + 1)
        self.assertEqual(
            self.post.comments.first().text, form_data.get('text')
        )
        self.assertRedirects(response, (reverse(
            'posts:post_detail', args=((post_id,)))))
