# ==========================================
# PART / BRANCH (WI-05): Reminder Queue Cleanup (main.py)
# ==========================================
import datetime

class MediLinkReminderService:
    def __init__(self):
        self.appointments = []
        # WI-03: Track dispatched notification tokens to prevent double-firing
        self.dispatched_tokens = set()

    def add_appointment(self, appt_id, patient_name, appt_time, is_cancelled=False):
        self.appointments.append({
            "id": appt_id,
            "patient": patient_name,
            "time": appt_time,
            "cancelled": is_cancelled,
            "sent": False
        })

    def process_reminders(self):
        """WI-03 Fix: Prevent duplicate reminders when processing runs more than once."""
        print("--- Running Deduplication-Protected Reminder Service ---")
        now = datetime.datetime.now()
        
        for appt in self.appointments:
            # Generate a unique tracking token for this appointment's notification
            notification_token = f"appt_{appt['id']}_reminder"

            # Skip cancelled or past-due appointments
            if appt["cancelled"] or appt["time"] <= now:
                continue

            # WI-03: Concurrency check - verify if token was already processed and dispatched
            if notification_token in self.dispatched_tokens:
                print(f"[BLOCKED] Duplicate prevention: Reminder for Appt #{appt['id']} was already dispatched.")
                continue

            if not appt["sent"]:
                print(f"[SUCCESS] Sending reminder to {appt['patient']} for {appt['time']}")
                appt["sent"] = True
                # Register token as successfully dispatched
                self.dispatched_tokens.add(notification_token)

    def cleanup_reminder_queue(self):
        """WI-05: Remove expired and already-processed entries from the reminder queue."""
        now = datetime.datetime.now()
        before = len(self.appointments)
        self.appointments = [
            a for a in self.appointments
            if not (a["sent"] or a["cancelled"] or a["time"] <= now)
        ]
        removed = before - len(self.appointments)
        print(f"[CLEANUP] Removed {removed} processed/expired entries. {len(self.appointments)} pending reminder(s) kept.")
        return removed

if __name__ == "__main__":
    service = MediLinkReminderService()
    future_time = datetime.datetime.now() + datetime.timedelta(hours=5)
    service.add_appointment(101, "Alex Mercer", future_time, is_cancelled=False)
    
    # Simulate running the process twice concurrently/back-to-back
    print("--- First Run ---")
    service.process_reminders()
    
    print("\n--- Second Run (Should block duplicates) ---")
    service.process_reminders()

    # WI-05: add a future appointment that has not been reminded yet, then clean up
    service.add_appointment(102, "Sam Lee", future_time, is_cancelled=False)
    print("\n--- Queue Cleanup ---")
    service.cleanup_reminder_queue()