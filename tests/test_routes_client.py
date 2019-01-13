import unittest
from competition import create_app
from competition.lib import models_graph as mg


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.client = self.app.test_client(use_cookies=True)
        mg.User().register('dirk', 'olse')

    def tearDown(self):
        self.app_ctx.pop()

    def get_login(self):
        """
        Login is available for many test cases
        Return response object - depending on the location or purpose another response object can show up. This method
        will ensure that response code is 200 after redirect, the sends the response object to the caller.
        @return:
        """
        r = self.client.get('/login')
        # r = self.client.get_label('/login')
        self.assertEqual(r.status_code, 200)
        self.assertTrue('<h1>Login</h1>' in r.get_data(as_text=True))
        r = self.client.post('/login',
                             data={'username': 'dirk', 'password': 'olse'},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        return r

    def get_logout(self):
        """
        This function will logout. After logout, home page should be displayed.
        :return:
        """
        r = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse('Logout' in r.get_data(as_text=True))
        self.assertTrue('Login' in r.get_data(as_text=True))
        return

    def test_login_logout(self):
        # Login
        r = self.get_login()
        self.assertTrue('<h1>Kalender</h1>' in r.get_data(as_text=True))
        self.assertTrue('Logout' in r.get_data(as_text=True))
        self.assertFalse('Login' in r.get_data(as_text=True))
        # Logout
        self.get_logout()

    def test_person_list(self):
        # Anonymous user, get person list
        # Go to Deelnemers
        r = self.client.get('/person/list', follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('Jan Baillevier' in r.get_data(as_text=True))
        self.assertFalse('Wedstrijden' in r.get_data(as_text=True))
        # Then get overview of Wedstrijden for Jan
        url = '/person/bc59fcf2-75e8-41b9-b0bb-cec365348941'
        r = self.client.get(url, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('Lier' in r.get_data(as_text=True))
        # Next get an overview for the participant in this race
        url = '/participant/3184bb3d-f2fd-4951-aeae-442dc4b566b0/list'
        r = self.client.get(url, follow_redirects=True)
        # You need to log in first, so check for log in message
        self.assertEqual(r.status_code, 200)
        self.assertTrue('Aankomsten' in r.get_data(as_text=True))
