from django.test import Client, TestCase


class CoreAppTest(TestCase):

    def setUp(self):
        self.guest_client = Client()

    def test_page_not_found(self):
        url = 'posts/unexisting_page/'
        template = 'core/404.html'
        response = self.guest_client.get(url)
        self.assertTemplateUsed(response, template)
