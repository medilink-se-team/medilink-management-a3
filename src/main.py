# ==========================================
# FILE 1: reminder_service.py (PRODUCTION BASELINE)
# ==========================================
import datetime

class MediLinkReminderService:
    def __init__(self):
        # Simulated database of appointments
        self.appointments = []

    def add_appointment(self, appt_id, patient_name, appt_time, is_cancelled=False):
        self.appointments.append({
            "id": appt_id,
            "patient": patient_name,
            "time": appt_time,
            "cancelled": is_cancelled,
            "sent": False
        })

    def process_reminders(self):
        """Production v1.0: Blindly sends reminders without validation."""
        print("--- Running Reminder Service (Production) ---")
        for appt in self.appointments:
            if not appt["sent"]:
                # BUG: Does not check if appointment is cancelled or time has passed!
                print(f"-> Sending reminder email to {appt['patient']} for appointment at {appt['time']}")
                appt["sent"] = True

if __name__ == "__main__":
    service = MediLinkReminderService()
    # Add a past appointment and a cancelled appointment to show the flaw
    past_time = datetime.datetime.now() - datetime.timedelta(hours=2)
    service.add_appointment(1, "John Doe", past_time, is_cancelled=True)
    service.process_reminders()