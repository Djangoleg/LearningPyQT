import unittest

from common.variables import TIME, ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR
from server import Server


class TestServer(unittest.TestCase):

    err = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }
    ok = {
        RESPONSE: 200
    }

    def test_no_account_name(self):
        self.assertEqual(
            Server().process_client_message({ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: ''}}), self.err)

    def test_error_action(self):
        self.assertEqual(
            Server().process_client_message({ACTION: 'Error', TIME: 1.1, USER: {ACCOUNT_NAME: ''}}), self.err)

    def test_no_time(self):
        self.assertEqual(
            Server().process_client_message({ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.err)

    def test_no_user(self):
        self.assertEqual(
            Server().process_client_message({ACTION: PRESENCE, TIME: 1.1}), self.err)

    def test_ok(self):
        self.assertEqual(
            Server().process_client_message({ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}), self.ok)


if __name__ == '__main__':
    unittest.main()
