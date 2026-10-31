# ==========================================
# PART A: Production Baseline (main.py)
# ==========================================
import datetime

class MediLinkReminderService:
    def __init__(self):
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
        print("--- Running Production Reminder Service ---")
        for appt in self.appointments:
            if not appt["sent"]:
                # BUG: Blindly sends reminders without checking cancellation or past times
                print(f"-> Sending reminder email to {appt['patient']} for appointment at {appt['time']}")
                appt["sent"] = True

if __name__ == "__main__":
    service = MediLinkReminderService()
    service.add_appointment(1, "John Doe", datetime.datetime.now() - datetime.timedelta(hours=2), is_cancelled=True)
    service.process_reminders()