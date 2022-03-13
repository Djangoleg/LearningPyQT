import json
import unittest

from common.utils import send_message, get_message
from common.variables import TIME, ACTION, PRESENCE, USER, ACCOUNT_NAME, RESPONSE, ERROR, ENCODING



class TestMessage:

    def __init__(self, message_dict):
        self.message_dict = message_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        js_message = json.dumps(self.message_dict)
        self.encoded_message = js_message.encode(ENCODING)
        self.received_message = message_to_send

    def recv(self, max_length):
        js_message = json.dumps(self.message_dict)
        return js_message.encode(ENCODING)



class TestUtils(unittest.TestCase):

    message_dict = {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Test User'}}
    err = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }
    ok = {
        RESPONSE: 200
    }

    def test_send_message(self):
        test_message = TestMessage(self.message_dict)
        send_message(test_message, self.message_dict)
        self.assertEqual(test_message.encoded_message, test_message.received_message)
        with self.assertRaises(Exception):
            send_message(test_message, test_message)

    def test_get_message_ok(self):
        test_ok = TestMessage(self.ok)
        self.assertEqual(get_message(test_ok), self.ok)

    def test_get_message_err(self):
        test_err = TestMessage(self.err)
        self.assertEqual(get_message(test_err), self.err)

if __name__ == '__main__':
    unittest.main()
