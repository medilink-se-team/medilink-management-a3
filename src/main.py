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

    
    def process_reminders(self, now=None):
        print("--- Running Reminder Service (Feature Update) ---")

        if now is None:
            now = datetime.datetime.now()

        current_minute = now.replace(second=0, microsecond=0)

        for appt in self.appointments:
            intervals = self.calculate_reminder_times(appt["time"])

            for label, r_time in intervals.items():
                reminder_minute = r_time.replace(second=0, microsecond=0)

                if label in appt["sent_intervals"]:
                    continue

                if reminder_minute == current_minute:
                    print(f"-> Sending {label} reminder to {appt['patient']}")
                    appt["sent_intervals"].append(label)


if __name__ == "__main__":
    service = MediLinkReminderService()
    service.add_appointment(1, "John Doe", datetime.datetime.now() - datetime.timedelta(hours=2), is_cancelled=True)
    service.process_reminders()