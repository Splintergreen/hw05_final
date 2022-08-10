from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class URLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.wrong_user = User.objects.create_user(username='WrongUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост обрезаный до 15 знаков',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_authorized_user(self):
        '''Проверка соответствия URL для авторизованного пользователя.'''
        self.authorized_client.force_login(self.user)
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_guest_user(self):
        '''Проверка соответствия и редиректа URL для гостевого пользователя.'''
        templates_url_names = {
            f'/posts/{self.post.id}/edit/': '/auth/login/?next=',
            '/create/': '/auth/login/?next=',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, template + address)

    def test_wrong_author_edit(self):
        '''Проверка изменения поста пользователем отличным от автора'''
        self.authorized_client.force_login(self.wrong_user)
        url = f'/posts/{self.post.id}/edit/'
        response = self.authorized_client.get(url)
        expected_url = '/'
        self.assertRedirects(response,
                             expected_url,
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK,
                             fetch_redirect_response=True
                             )

    def test_unexiting_page(self):
        '''Проверка запроса к несуществующей странице'''
        response = self.guest_client.get('unexiting_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.authorized_client.get('unexiting_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_404_castom_template(self):
        '''Cтраница 404 отдаёт кастомный шаблон'''
        response = self.guest_client.get('unexiting_page')
        self.assertTemplateUsed(response, 'core/404.html')
