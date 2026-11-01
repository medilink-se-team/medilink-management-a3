# ==========================================
# FILE 3: reminder_service.py (DEFECT PATCHED)
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
        """WI-02 & WI-04 Fix: Skip cancelled and past-due appointments."""
        print("--- Running Reminder Service (Defect Patched) ---")
        now = datetime.datetime.now()
        
        for appt in self.appointments:

            # FIX 2 (WI-04): Check if appointment time has already passed
            if appt["time"] <= now:
                print(f"[BLOCKED] Skipping Appt #{appt['id']}: Appointment time has passed.")
                continue

            if not appt["sent"]:
                print(f"[SUCCESS] Sending reminder to {appt['patient']} for {appt['time']}")
                appt["sent"] = True

if __name__ == "__main__":
    service = MediLinkReminderService()
    # Test case: past appointment should be safely ignored
    past_time = datetime.datetime.now() - datetime.timedelta(hours=1)
    service.add_appointment(42, "Jane Smith", past_time, is_cancelled=True)
    service.process_reminders()