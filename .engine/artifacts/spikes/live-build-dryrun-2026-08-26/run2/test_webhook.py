import hashlib
import hmac
import json
import unittest

from webhook import handle_webhook

SECRET = "shhh"
NOW = 1_700_000_000


def sign(raw: bytes, timestamp: int = NOW, secret: str = SECRET) -> str:
    signed = f"{timestamp}.".encode() + raw
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


class RecordingQueue:
    def __init__(self) -> None:
        self.written: list[dict] = []

    def put(self, payload: dict) -> None:
        self.written.append(payload)


class ContractTest(unittest.TestCase):
    """Catches a handler that accepts the request but never queues it, or that
    queues the raw bytes instead of the parsed payload."""

    def test_genuine_request_is_queued_once(self) -> None:
        raw = json.dumps({"event": "invoice.paid", "id": "in_9"}).encode()
        queue = RecordingQueue()

        status, body = handle_webhook(sign(raw), NOW, raw, SECRET, queue, NOW)

        self.assertEqual(202, status)
        self.assertEqual({"queued": True}, body)
        self.assertEqual([{"event": "invoice.paid", "id": "in_9"}], queue.written)


class RejectionTest(unittest.TestCase):
    """Catches the implementation that parses before verifying, or that lets a
    forged request reach the queue."""

    def test_forged_signature_is_rejected_and_never_reaches_the_queue(self) -> None:
        raw = json.dumps({"event": "invoice.paid"}).encode()
        queue = RecordingQueue()

        forged = sign(raw, NOW, "wrong-secret")
        status, body = handle_webhook(forged, NOW, raw, SECRET, queue, NOW)

        self.assertEqual(401, status)
        self.assertEqual({"error": "bad signature"}, body)
        self.assertEqual([], queue.written)

    def test_unparseable_body_from_a_real_sender_is_a_bad_request(self) -> None:
        raw = b"{not json at all"
        queue = RecordingQueue()

        status, _ = handle_webhook(sign(raw), NOW, raw, SECRET, queue, NOW)

        self.assertEqual(400, status)
        self.assertEqual([], queue.written)


class ReplayTest(unittest.TestCase):
    """Catches the two ways replay protection is usually got wrong: checking the age
    of a timestamp that was never signed (so an attacker just supplies a fresh one),
    and letting an expired-but-authentic request through to the queue."""

    def test_captured_request_replayed_later_is_refused(self) -> None:
        raw = json.dumps({"event": "invoice.paid"}).encode()
        queue = RecordingQueue()
        signed_at = NOW - 600

        status, body = handle_webhook(
            sign(raw, signed_at), signed_at, raw, SECRET, queue, NOW
        )

        self.assertEqual(401, status)
        self.assertEqual({"error": "timestamp too old"}, body)
        self.assertEqual([], queue.written)

    def test_swapping_in_a_fresh_timestamp_breaks_the_signature(self) -> None:
        raw = json.dumps({"event": "invoice.paid"}).encode()
        queue = RecordingQueue()
        captured = sign(raw, NOW - 600)

        status, body = handle_webhook(captured, NOW, raw, SECRET, queue, NOW)

        self.assertEqual(401, status)
        self.assertEqual({"error": "bad signature"}, body)
        self.assertEqual([], queue.written)


if __name__ == "__main__":
    unittest.main()
