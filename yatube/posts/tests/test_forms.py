import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NewUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Test text',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post_id = 1

    def test_post_create_form(self):
        '''
        При отправке валидной формы со страницы создания поста
        создаётся новая запись в базе данных
        '''
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        test_image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_data = {
            'text': 'Новый текст',
            'image': test_image
        }
        self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        # при отправке поста с картинкой через форму есть запись в базе данных.
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            image=f'posts/{test_image}').exists()
        )

    def test_post_create_form_with_group(self):
        '''
        При отправке валидной формы со страницы создания поста при указании
        группы создаётся новая запись в базе данных
        '''
        form_data = {
            'text': 'Текст новый, пост с группой',
            'group': self.group.id,
        }
        self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertTrue(Post.objects.filter(**form_data).exists())

    def test_post_edit_form(self):
        '''
        При отправке валидной формы со страницы изменения поста
        происходит изменение поста с post_id в базе данных
        '''
        text = Post.objects.get(id=self.post_id).text
        form_data = {
            'text': 'Совершенно другой текст',
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post_id}),
            data=form_data, follow=True
        )
        text_change = Post.objects.get(id=self.post_id).text
        self.assertNotEqual(text, text_change)

    def test_post_edit_form_with_group(self):
        '''
        При отправке валидной формы со страницы изменения поста при указании
        происходит изменение поста с post_id в базе данных
        '''
        form_data = {
            'text': 'Текст измененный, пост с группой',
            'group': self.group.id,
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post_id}),
            data=form_data, follow=True
        )
        self.assertTrue(Post.objects.filter(**form_data).exists())

    def test_post_comment_form(self):
        '''
        Комментировать посты может только авторизованный пользователь
        '''
        form_data = {
            'text': 'Тестовый текст комментария',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post_id}),
            data=form_data, follow=True
        )
        self.assertTrue(Comment.objects.filter(**form_data).exists())
        context_comments = response.context.get('comments')
        # после успешной отправки комментарий появляется на странице поста.
        self.assertTrue(context_comments.exists())
