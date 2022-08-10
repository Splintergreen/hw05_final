import shutil
import tempfile
from itertools import islice

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.user_follow = User.objects.create_user(username='follower')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_two = Group.objects.create(
            title='Тестовая группа номер 2',
            slug='test-slug-two',
            description='Тестовое описание',
        )
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
        batch_size = 13
        objs = (Post(author=cls.user,
                text='Test %s' % i,
                image=test_image,
                group=cls.group)
                for i in range(14))
        while True:
            batch = list(islice(objs, batch_size))
            if not batch:
                break
            Post.objects.bulk_create(batch, batch_size)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.follow_client = Client()
        # self.follow_client.force_login(self.user_follow)
        self.page_count = 10
        self.post_id = 1
        self.form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        self.templates_pages_names = {
            'index': ('posts/index.html', reverse('posts:index')),
            'group_list': ('posts/group_list.html', reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            )
            ),
            'group_list_two': ('posts/group_list.html', reverse(
                'posts:group_list', kwargs={'slug': self.group_two.slug}
            )
            ),
            'profile': ('posts/profile.html', reverse(
                'posts:profile', kwargs={'username': self.user}
            )
            ),
            'post_detail': ('posts/post_detail.html', reverse(
                'posts:post_detail', kwargs={'post_id': self.post_id}
            )
            ),
            'post_edit': ('posts/create_post.html', reverse(
                'posts:post_edit', kwargs={'post_id': self.post_id}
            )
            ),
            'post_create': ('posts/create_post.html',
                            reverse('posts:post_create')),
        }

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        for _, reverse_name in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name[1]):
                response = self.authorized_client.get(reverse_name[1])
                self.assertTemplateUsed(response, reverse_name[0])

    def test_index_page_show_correct_context(self):
        '''Проверка контеста шаблона index и Paginator'''
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        post_context = response.context['page_obj'].object_list
        post_list = list(Post.objects.all()[:self.page_count])
        # Проверка передачи изображения в контексте
        self.assertEqual(post_list[5].image, post_context[5].image)
        self.assertEqual(post_list, post_context)
        self.assertEqual(len(response.context['page_obj']), self.page_count)
        self.assertEqual(post_list[1], post_context[1])

    def test_group_list_show_correct_context(self):
        '''Проверка контеста шаблона group_list и Paginator'''
        response = self.authorized_client.get(
            self.templates_pages_names['group_list'][1]
        )
        group_context = response.context['group']
        post_by_group_context = list(group_context.posts.all())
        post_by_group = list(self.group.posts.select_related('group'))
        self.assertEqual(post_by_group, post_by_group_context)
        self.assertEqual(len(response.context['page_obj']), self.page_count)
        self.assertEqual(post_by_group[5], post_by_group_context[5])
        response = self.authorized_client.get(
            self.templates_pages_names['group_list_two'][1]
        )
        group_context = response.context['group']
        post_by_group_two_context = group_context.posts.all()
        self.assertEqual(len(post_by_group_two_context), 0)
        # Проверка передачи изображения в контексте
        self.assertEqual(post_by_group_context[3].image,
                         post_by_group[3].image)

    def test_profile_show_correct_context(self):
        '''Проверка контеста шаблона Профиля и Paginator'''
        response = self.authorized_client.get(
            self.templates_pages_names['profile'][1]
        )
        group_context = response.context['author']
        post_by_author_context = list(group_context.posts.all())
        post_by_author = list(self.group.posts.select_related('author'))
        self.assertEqual(post_by_author, post_by_author_context)
        self.assertEqual(len(response.context['page_obj']), self.page_count)
        self.assertEqual(post_by_author[3], post_by_author_context[3])
        # Проверка передачи изображения в контексте
        self.assertEqual(post_by_author_context[3].image,
                         post_by_author[3].image)

    def test_one_post_filter_by_id(self):
        '''Один пост отфильтрованный по id'''
        response = self.authorized_client.get(
            self.templates_pages_names['post_detail'][1]
        )
        context_post_id = response.context['post']
        self.assertEqual(self.post_id, context_post_id.id)
        # Проверка передачи изображения в контексте
        self.assertEqual(context_post_id.image,
                         Post.objects.get(pk=self.post_id).image)

    def test_form_post_edit_by_id(self):
        '''Проверка формы редактирования поста по id'''
        response = self.authorized_client.get(
            self.templates_pages_names['post_edit'][1]
        )
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_form_post_create(self):
        '''Проверка формы создания поста'''
        response = self.authorized_client.get(
            self.templates_pages_names['post_create'][1]
        )
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_cash_index_page_view(self):
        '''Тестирование кэша index_page'''
        response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.filter(id=self.post_id).delete()
        response_after_del = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_after_del.content)
        cache.clear()
        response_clear_cache = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response.content, response_clear_cache.content)

    def test_authorized_user_can_subscribe(self):
        '''Авторизованный пользователь может подписываться на других
        пользователей и удалять их из подписок.'''
        before_subscribing = Follow.objects.exists()
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_follow})
        )
        after_subscribing = Follow.objects.exists()
        self.assertNotEqual(before_subscribing, after_subscribing)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_follow})
        )
        unsubscribe = Follow.objects.exists()
        self.assertEqual(before_subscribing, unsubscribe)

    def test_authorized_user_view_subscribe(self):
        '''Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан.'''
        self.follow_client.force_login(self.user_follow)
        self.follow_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user})
        )
        response = self.follow_client.get(reverse('posts:follow_index'))
        subscribe_user_posts = list(response.context['page_obj'])
        response = self.authorized_client.get(reverse('posts:follow_index'))
        unsubscribe_user_posts = list(response.context['page_obj'])
        self.assertNotEqual(subscribe_user_posts, unsubscribe_user_posts)
