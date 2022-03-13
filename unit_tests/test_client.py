import unittest

from common.variables import TIME, ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR
from client import Client


class TestClient(unittest.TestCase):

    def test_presence(self):
        message = Client().create_presence()
        message[TIME] = 1.1

        self.assertEqual(message, {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}})


    def test_200_answer(self):
        self.assertEqual(Client().process_answer({RESPONSE: 200}), '200 : OK')

    def test_400_answer(self):
        self.assertEqual(Client().process_answer({RESPONSE: 400, ERROR: 'error'}), '400 : error')

    def test_no_response(self):
        self.assertRaises(ValueError, Client().process_answer, {ERROR: 'error'})

if __name__ == '__main__':
    unittest.main()