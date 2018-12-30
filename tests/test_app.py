import unittest
from competition import create_app
from config import Config


class TestConfig(Config):
    TESTING = True


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_app_context(self):
        print(self.app_context)
        print(self.app.config["TESTING"])
