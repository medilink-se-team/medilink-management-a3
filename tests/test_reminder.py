
import unittest
import datetime
import inspect
import io
import threading
import time

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, contextmanager
from unittest.mock import patch

import src.main as medilink


# Fixed time prevents tests from depending on the real clock.
NOW = datetime.datetime(2026, 11, 2, 12, 0, 0)


@contextmanager
def freeze_time(moment):
    original = datetime.datetime

    class FrozenDateTime(original):
        @classmethod
        def now(cls, tz=None):
            return moment

    with patch.object(medilink.datetime, "datetime", FrozenDateTime):
        yield


class TestReminderService(unittest.TestCase):

    def setUp(self):
        self.service = medilink.MediLinkReminderService()

    def add(self, appt_id=1, hours=24, minutes=0,
            cancelled=False):
        appointment_time = NOW + datetime.timedelta(
            hours=hours, minutes=minutes
        )
        self.service.add_appointment(
            appt_id, "Test Patient", appointment_time,
            is_cancelled=cancelled
        )
        return self.service.appointments[-1]

    def process(self, moment=NOW):
        output = io.StringIO()

        with freeze_time(moment), redirect_stdout(output):
            parameters = inspect.signature(
                self.service.process_reminders
            ).parameters

            if "now" in parameters:
                self.service.process_reminders(now=moment)
            else:
                self.service.process_reminders()

        return output.getvalue()

    @staticmethod
    def sent_messages(output):
        return [
            line for line in output.splitlines()
            if "sending" in line.lower()
            and "reminder" in line.lower()
        ]

    # ======================================
    # WI-02: APPOINTMENT CANCELLATION
    # ======================================

    def test_cancelled_appointment_not_sent(self):
        appointment = self.add(cancelled=True)

        output = self.process()

        self.assertFalse(appointment["sent"])
        self.assertEqual(len(self.sent_messages(output)), 0)

    def test_cancelled_after_booking(self):
        appointment = self.add(cancelled=False)

        appointment["cancelled"] = True
        output = self.process()

        self.assertFalse(appointment["sent"])
        self.assertEqual(len(self.sent_messages(output)), 0)

    def test_cancelled_and_expired_appointment(self):
        appointment = self.add(
            hours=-1, cancelled=True
        )

        output = self.process()

        self.assertFalse(appointment["sent"])
        self.assertEqual(len(self.sent_messages(output)), 0)

    def test_cancelled_remains_blocked_on_repeated_runs(self):
        appointment = self.add(cancelled=True)

        first = self.process()
        second = self.process()

        self.assertFalse(appointment["sent"])
        self.assertEqual(
            len(self.sent_messages(first + second)), 0
        )

    # ======================================
    # WI-04: EXPIRED APPOINTMENTS
    # ======================================

    def test_past_appointment_not_sent(self):
        appointment = self.add(hours=-1)

        output = self.process()

        self.assertFalse(appointment["sent"])
        self.assertEqual(len(self.sent_messages(output)), 0)

    def test_appointment_at_exact_start_time(self):
        appointment = self.add(hours=0)

        output = self.process()

        self.assertFalse(appointment["sent"])
        self.assertEqual(len(self.sent_messages(output)), 0)

    def test_appointment_one_second_after_start(self):
        appointment = self.add(hours=0)
        moment = NOW + datetime.timedelta(seconds=1)

        output = self.process(moment)

        self.assertFalse(appointment["sent"])
        self.assertEqual(len(self.sent_messages(output)), 0)

    # ======================================
    # WI-01: REMINDER SCHEDULING
    # ======================================

    def test_reminder_intervals(self):
        intervals = [
            ("24h", 24, 0),
            ("2h", 2, 0),
            ("30min", 0, 30),
        ]

        for label, hours, minutes in intervals:
            with self.subTest(interval=label):
                self.setUp()
                self.add(hours=hours, minutes=minutes)

                output = self.process()
                messages = self.sent_messages(output)

                self.assertEqual(
                    len(messages), 1,
                    f"{label} reminder not sent correctly"
                )
                self.assertIn(
                    label.lower(), messages[0].lower()
                )

    def test_reminder_not_sent_early(self):
        self.add(hours=24, minutes=1)

        output = self.process()

        self.assertEqual(
            len(self.sent_messages(output)), 0
        )

    def test_missed_reminder_not_sent_late(self):
        # The 24h reminder was due one minute ago.
        # The 2h and 30min reminders are not due yet.
        self.add(hours=23, minutes=59)

        output = self.process()

        self.assertEqual(
            len(self.sent_messages(output)), 0
        )

    def test_all_three_intervals_for_same_appointment(self):
        self.add(hours=24)

        results = [
            self.process(NOW),
            self.process(NOW + datetime.timedelta(hours=22)),
            self.process(
                NOW + datetime.timedelta(hours=23, minutes=30)
            ),
        ]

        messages = self.sent_messages("".join(results))

        self.assertEqual(
            len(messages), 3,
            "An appointment should receive three reminders"
        )

        for label in ("24h", "2h", "30min"):
            self.assertTrue(
                any(label.lower() in msg.lower()
                    for msg in messages),
                f"Missing {label} reminder"
            )

    # ======================================
    # WI-03: DUPLICATE PREVENTION
    # ======================================

    def test_no_duplicate_reminder(self):
        appointment = self.add()

        first = self.process()
        second = self.process()

        messages = self.sent_messages(first + second)

        self.assertEqual(len(messages), 1)
        self.assertTrue(appointment["sent"])

    def test_two_appointments_processed_independently(self):
        self.add(appt_id=1)
        self.add(appt_id=2)

        output = self.process()

        self.assertEqual(
            len(self.sent_messages(output)), 2
        )

    def test_concurrent_processing(self):
        self.add()
        messages = []
        messages_lock = threading.Lock()
        start = threading.Barrier(8)

        def capture_print(*args, **kwargs):
            message = " ".join(map(str, args))

            if "sending" in message.lower():
                # Encourage a race between checking and
                # updating the notification's sent state.
                time.sleep(0.01)

            with messages_lock:
                messages.append(message)

        def worker(_):
            start.wait(timeout=5)
            return self.service.process_reminders()

        with freeze_time(NOW):
            with patch("builtins.print",
                       side_effect=capture_print):
                with ThreadPoolExecutor(
                    max_workers=8
                ) as executor:
                    list(executor.map(worker, range(8)))

        successful = self.sent_messages("\n".join(messages))

        self.assertEqual(
            len(successful), 1,
            "Concurrent workers dispatched duplicate reminders"
        )

    def test_dispatched_token_prevents_resending(self):
        if not hasattr(self.service, "dispatched_tokens"):
            self.skipTest(
                "WI-03 token tracking not yet merged into main"
            )

        appointment = self.add()

        first = self.process()
        appointment["sent"] = False
        second = self.process()

        self.assertEqual(
            len(self.sent_messages(first + second)), 1
        )

    # ======================================
    # WI-05: REMINDER QUEUE MAINTENANCE
    # ======================================

    def queue_api(self):
        queue = getattr(self.service, "reminder_queue", None)
        cleanup = getattr(
            self.service, "cleanup_expired_reminders", None
        )

        if not isinstance(queue, list) or not callable(cleanup):
            self.skipTest(
                "WI-05 queue API not implemented. "
                "Expected reminder_queue list and "
                "cleanup_expired_reminders(now=...). "
                "Adapt this test to teammate's actual API."
            )

        return queue, cleanup

    def test_expired_queue_cleanup(self):
        queue, cleanup = self.queue_api()

        queue.append({
            "id": 101,
            "due_at": NOW - datetime.timedelta(hours=1),
            "status": "processed"
        })

        cleanup(now=NOW)

        self.assertFalse(
            any(item["id"] == 101 for item in queue)
        )

    def test_queue_cleanup_preserves_pending_reminders(self):
        queue, cleanup = self.queue_api()

        queue.append({
            "id": 102,
            "due_at": NOW + datetime.timedelta(hours=2),
            "status": "pending"
        })

        cleanup(now=NOW)

        self.assertTrue(
            any(item["id"] == 102 for item in queue)
        )

    # ======================================
    # WI-06: BACKWARD COMPATIBILITY
    # ======================================

    def test_existing_behaviour_after_refactoring(self):
        self.add(appt_id=1, cancelled=True)
        self.add(appt_id=2, hours=-1)
        self.add(appt_id=3, hours=24)

        output = self.process()
        appointments = self.service.appointments

        self.assertFalse(appointments[0]["sent"])
        self.assertFalse(appointments[1]["sent"])
        self.assertTrue(appointments[2]["sent"])

        self.assertEqual(
            len(self.sent_messages(output)), 1
        )

    # ======================================
    # GENERAL EDGE CASES
    # ======================================

    def test_empty_appointment_list(self):
        output = self.process()

        self.assertEqual(
            len(self.sent_messages(output)), 0
        )
        self.assertEqual(len(self.service.appointments), 0)

    def test_processing_does_not_change_appointment_id(self):
        appointment = self.add(appt_id=999)

        self.process()

        self.assertEqual(appointment["id"], 999)


if __name__ == "__main__":
    unittest.main()
