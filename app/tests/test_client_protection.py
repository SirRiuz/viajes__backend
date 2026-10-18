"""Optional client protection (SINGLE_REQUEST_PROTECT, ENCRYPTED_RESPONSE) and its helpers."""

import base64
import json
from unittest import mock

import jwt
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.response import Response

from app.cripto.kdf import decryptor, encryptor
from app.methods.storage import check_token, save_token
from app.methods.tokens import decode_token, encode_token
from app.permissions.client import IsClientAuthenticated
from app.renders.encoder import EncodeRenderer
from app.utils import rate_limit


class CryptoTestCase(SimpleTestCase):
    def test_encryptor_and_decryptor_round_trip(self):
        key, data, iv = encryptor('{"ok": true}')
        # decryptor keeps the PKCS7 padding, as it always did
        self.assertTrue(decryptor(key, data, iv).startswith('{"ok": true}'))

    def test_each_message_gets_a_fresh_key(self):
        self.assertNotEqual(encryptor("same")[0], encryptor("same")[0])


class TokensTestCase(SimpleTestCase):
    def test_round_trip(self):
        self.assertEqual(decode_token(encode_token({"a": 1})), {"a": 1})

    def test_foreign_signature_is_refused(self):
        forged = jwt.encode({"a": 1}, "another-key-another-key-another-key", algorithm="HS256")
        with self.assertRaises(jwt.PyJWTError):
            decode_token(forged)


class StorageTestCase(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_tokens_are_remembered_by_hash(self):
        self.assertFalse(check_token("abc"))
        save_token("abc")
        self.assertTrue(check_token("abc"))
        self.assertFalse(check_token("abd"))


class IsClientAuthenticatedTestCase(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.permission = IsClientAuthenticated()

    def request(self, token):
        return RequestFactory().get("/", HTTP_CLIENT_ASSERTION=token)

    def test_open_when_the_flag_is_off(self):
        self.assertTrue(self.permission.has_permission(self.request(""), None))

    @override_settings(SINGLE_REQUEST_PROTECT=True)
    def test_each_token_works_once(self):
        token = encode_token({"jti": "1"})
        self.assertTrue(self.permission.has_permission(self.request(token), None))
        self.assertFalse(self.permission.has_permission(self.request(token), None))

    @override_settings(SINGLE_REQUEST_PROTECT=True)
    def test_invalid_token_is_refused(self):
        self.assertFalse(self.permission.has_permission(self.request("nope"), None))


class EncodeRendererTestCase(SimpleTestCase):
    def test_body_and_key_travel_reversed(self):
        response = Response()
        body = EncodeRenderer().render({"ok": True}, renderer_context={"response": response})

        key, iv = base64.b64decode(response.headers["X-Response-Payload"][::-1]).decode().split(":")
        plain = decryptor(key, body[::-1], iv)
        self.assertEqual(json.loads(plain[: plain.rindex("}") + 1]), {"ok": True})


class RateLimitTestCase(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_window_counts_and_resets(self):
        self.assertTrue(rate_limit.hit("k", 2, 60))
        self.assertTrue(rate_limit.hit("k", 2, 60))
        self.assertFalse(rate_limit.hit("k", 2, 60))
        self.assertTrue(rate_limit.blocked("k", 2))
        rate_limit.reset("k")
        self.assertFalse(rate_limit.blocked("k", 2))

    def test_window_expiring_between_add_and_incr(self):
        with mock.patch.object(rate_limit.cache, "add", return_value=False), mock.patch.object(
            rate_limit.cache, "incr", side_effect=ValueError
        ):
            self.assertTrue(rate_limit.hit("k", 1, 60))
