from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Post

User = get_user_model()


class ViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.user_follow = User.objects.create_user(username='follower')
        Post.objects.create(author=cls.user, text='Тестовый пост')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.follow_client = Client()
        self.post_id = 1

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
