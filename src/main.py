# ==========================================
# PART H / WI-06: Improvement Experiment & Refactoring (main.py)
# ==========================================
import datetime

class AppointmentValidator:
    """WI-06: Extracted validation logic to decouple checks and reduce code complexity."""
    @staticmethod
    def is_valid(appt, now):
        if appt["cancelled"]:
            print(f"[BLOCKED] Appt #{appt['id']}: Cancelled.")
            return False
        if appt["time"] <= now:
            print(f"[BLOCKED] Appt #{appt['id']}: Time has passed.")
            return False
        return True

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
        """Refactored loop leveraging modular validator."""
        print("--- Running Experiment Refactored Service ---")
        now = datetime.datetime.now()
        
        for appt in self.appointments:
            if not appt["sent"] and AppointmentValidator.is_valid(appt, now):
                print(f"[SUCCESS] Sending reminder to {appt['patient']}")
                appt["sent"] = True

if __name__ == "__main__":
    service = MediLinkReminderService()
    service.add_appointment(99, "Experiment User", datetime.datetime.now() - datetime.timedelta(hours=1), is_cancelled=False)
    service.process_reminders()