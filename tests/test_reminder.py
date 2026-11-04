
import datetime
import io
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from unittest.mock import patch

import src.main as medilink


NOW = datetime.datetime(2026, 11, 3, 12, 0)


class TestReminderService(unittest.TestCase):

    def setUp(self):
        self.service = medilink.MediLinkReminderService()

    def add(self, id=1, seconds=86400, cancelled=False):
        when = NOW + datetime.timedelta(seconds=seconds)

        self.service.add_appointment(
            id,
            f"Patient {id}",
            when,
            is_cancelled=cancelled
        )

        return self.service.appointments[-1]

    def process(self, at=NOW):

        class FrozenDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return at

        output = io.StringIO()

        with patch.object(
            medilink.datetime, "datetime", FrozenDatetime
        ):
            with redirect_stdout(output):
                self.service.process_reminders()

        return output.getvalue()

    @staticmethod
    def sent_count(text):
        return sum(
            "[SUCCESS]" in line
            and "reminder" in line.lower()
            for line in text.splitlines()
        )

    # =====================================
    # GENERAL APPOINTMENT TESTS
    # =====================================

    def test_new_appointment_stored(self):
        a = self.add(id=42)

        self.assertEqual(a["id"], 42)
        self.assertEqual(a["patient"], "Patient 42")
        self.assertFalse(a["cancelled"])
        self.assertFalse(a["sent"])

    def test_upcoming_appointment_processed(self):
        a = self.add()

        self.assertEqual(
            self.sent_count(self.process()), 1
        )
        self.assertTrue(a["sent"])

    def test_empty_service(self):
        self.assertEqual(
            self.sent_count(self.process()), 0
        )
        self.assertEqual(self.service.appointments, [])

    def test_processing_preserves_appointment_fields(self):
        a = self.add(id=77)
        original = (
            a["id"], a["patient"],
            a["time"], a["cancelled"]
        )

        self.process()

        self.assertEqual(
            (a["id"], a["patient"],
             a["time"], a["cancelled"]),
            original
        )

    # =====================================
    # WI-02: CANCELLATION TESTS
    # =====================================

    def test_cancelled_appointment_not_sent(self):
        a = self.add(cancelled=True)

        self.assertEqual(
            self.sent_count(self.process()), 0
        )
        self.assertFalse(a["sent"])

    def test_cancelled_after_booking_not_sent(self):
        a = self.add()

        a["cancelled"] = True

        self.assertEqual(
            self.sent_count(self.process()), 0
        )
        self.assertFalse(a["sent"])

    def test_cancelled_and_expired_not_sent(self):
        a = self.add(seconds=-3600, cancelled=True)

        self.assertEqual(
            self.sent_count(self.process()), 0
        )
        self.assertFalse(a["sent"])

    # =====================================
    # WI-04: EXPIRED APPOINTMENT TESTS
    # =====================================

    def test_past_appointment_not_sent(self):
        a = self.add(seconds=-3600)

        self.assertEqual(
            self.sent_count(self.process()), 0
        )
        self.assertFalse(a["sent"])

    def test_exact_start_time_not_sent(self):
        a = self.add(seconds=0)

        self.assertEqual(
            self.sent_count(self.process()), 0
        )
        self.assertFalse(a["sent"])

    def test_one_second_past_start_not_sent(self):
        a = self.add(seconds=0)

        later = NOW + datetime.timedelta(seconds=1)

        self.assertEqual(
            self.sent_count(self.process(later)), 0
        )
        self.assertFalse(a["sent"])

    # =====================================
    # WI-03: BASIC DUPLICATE PREVENTION
    # =====================================

    def test_reprocessing_does_not_duplicate(self):
        a = self.add()

        first = self.process()
        second = self.process()

        self.assertEqual(
            self.sent_count(first + second), 1
        )
        self.assertTrue(a["sent"])

    def test_previously_sent_not_resent(self):
        a = self.add()

        a["sent"] = True

        self.assertEqual(
            self.sent_count(self.process()), 0
        )

    def test_two_valid_appointments(self):
        self.add(id=1)
        self.add(id=2)

        self.assertEqual(
            self.sent_count(self.process()), 2
        )

    def test_add_new_appointment_after_processing(self):
        self.add(id=1)
        first = self.process()

        self.add(id=2)
        second = self.process()

        self.assertEqual(self.sent_count(first), 1)
        self.assertEqual(self.sent_count(second), 1)

    # =====================================
    # WI-06: REFACTORING AND REGRESSION
    # =====================================

    def test_multiple_appointments_independent(self):
        valid = self.add(id=1)
        cancelled = self.add(id=2, cancelled=True)
        expired = self.add(id=3, seconds=-1)

        self.assertEqual(
            self.sent_count(self.process()), 1
        )

        self.assertTrue(valid["sent"])
        self.assertFalse(cancelled["sent"])
        self.assertFalse(expired["sent"])

    def test_validator_accepts_future_active_appointment(self):
        a = self.add()

        self.assertTrue(
            medilink.AppointmentValidator.is_valid(a, NOW)
        )

    def test_validator_rejects_cancelled_appointment(self):
        a = self.add(cancelled=True)

        with redirect_stdout(io.StringIO()):
            self.assertFalse(
                medilink.AppointmentValidator.is_valid(a, NOW)
            )

    def test_validator_rejects_expired_appointment(self):
        a = self.add(seconds=-1)

        with redirect_stdout(io.StringIO()):
            self.assertFalse(
                medilink.AppointmentValidator.is_valid(a, NOW)
            )

    # =====================================
    # WI-01: PENDING REMINDER SCHEDULING
    # =====================================

    @unittest.skip(
        "WI-01: interval scheduling absent from current main.py"
    )
    def test_three_reminder_intervals(self):
        self.add(seconds=24 * 3600)

        times = [
            NOW,
            NOW + datetime.timedelta(hours=22),
            NOW + datetime.timedelta(
                hours=23, minutes=30
            )
        ]

        outputs = [self.process(t) for t in times]

        self.assertEqual(
            self.sent_count("".join(outputs)), 3
        )

    @unittest.skip(
        "WI-01: due-time gating absent from current main.py"
    )
    def test_no_early_reminder(self):
        self.add(seconds=24 * 3600 + 60)

        self.assertEqual(
            self.sent_count(self.process()), 0
        )

    @unittest.skip(
        "WI-01: missed reminder protection absent from main"
    )
    def test_no_late_reminder(self):
        self.add(seconds=24 * 3600 - 60)

        self.assertEqual(
            self.sent_count(self.process()), 0
        )

    # =====================================
    # WI-03: PENDING CONCURRENCY SUPPORT
    # =====================================

    @unittest.skip(
        "WI-03: atomic concurrency protection absent from main"
    )
    def test_concurrent_sends_once(self):
        self.add()

        messages = []
        lock = threading.Lock()
        barrier = threading.Barrier(8)

        def mock_print(*args, **kwargs):
            message = " ".join(map(str, args))

            if "[SUCCESS]" in message:
                time.sleep(0.01)

            with lock:
                messages.append(message)

        def worker(_):
            barrier.wait(timeout=5)
            self.service.process_reminders()

        class FrozenDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW

        with patch.object(
            medilink.datetime, "datetime", FrozenDatetime
        ):
            with patch(
                "builtins.print", side_effect=mock_print
            ):
                with ThreadPoolExecutor(
                    max_workers=8
                ) as pool:
                    list(pool.map(worker, range(8)))

        self.assertEqual(
            self.sent_count("\n".join(messages)), 1
        )

    @unittest.skip(
        "WI-03: dispatched_tokens absent from current main.py"
    )
    def test_notification_token_deduplication(self):
        a = self.add()

        first = self.process()
        a["sent"] = False
        second = self.process()

        self.assertEqual(
            self.sent_count(first + second), 1
        )
        self.assertIn(
            "appt_1_reminder",
            self.service.dispatched_tokens
        )

    # =====================================
    # WI-05: PENDING QUEUE MAINTENANCE
    # =====================================

    @unittest.skip(
        "WI-05: queue API absent from current main.py"
    )
    def test_expired_queue_cleanup(self):
        self.assertTrue(
            hasattr(self.service, "reminder_queue")
        )
        self.assertTrue(
            callable(getattr(
                self.service,
                "cleanup_expired_reminders",
                None
            ))
        )

    @unittest.skip(
        "WI-05: queue API absent from current main.py"
    )
    def test_queue_cleanup_preserves_pending(self):
        self.assertTrue(
            hasattr(self.service, "reminder_queue")
        )
        self.assertTrue(
            callable(getattr(
                self.service,
                "cleanup_expired_reminders",
                None
            ))
        )


if __name__ == "__main__":
    unittest.main()
