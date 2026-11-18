"""Terminal input and validation; times are minutes since midnight."""

from datetime import date, timedelta


def ask_date(prompt):
    while True:
        value = input(prompt).strip()
        try:
            result = date.fromisoformat(value)
            if result.isoformat() != value:
                raise ValueError
            return result
        except ValueError:
            print("Enter a valid date in YYYY-MM-DD format, e.g. 2026-11-10.")


def ask_positive_integer(prompt, multiple=1):
    while True:
        try:
            value = int(input(prompt).strip())
            if value > 0 and value % multiple == 0:
                return value
        except ValueError:
            pass
        print(f"Enter a positive integer divisible by {multiple}.")


def ask_time(prompt):
    while True:
        value = input(prompt).strip()
        try:
            hour, minute = value.split(":")
            hour, minute = int(hour), int(minute)
            if 0 <= hour <= 23 and minute in (0, 30):
                return hour * 60 + minute
            if hour == 24 and minute == 0:
                return 1440
        except ValueError:
            pass
        print("Enter a half-hour time, such as 09:00 or 09:30; 24:00 is only valid as an end time.")


def collect_input():
    start_date = ask_date("Plan start date (YYYY-MM-DD): ")
    while start_date > date.max - timedelta(days=6):
        print("Start date must permit a full 7-day plan.")
        start_date = ask_date("Plan start date (YYYY-MM-DD): ")

    count = ask_positive_integer("How many free-time windows per day? ")
    windows = []
    for index in range(count):
        while True:
            print(f"Default time window {index + 1} (repeated daily):")
            start = ask_time("Start time (HH:MM): ")
            end = ask_time("End time (HH:MM): ")
            if start >= end:
                print("End time must be later than start time on the same day. Try again.")
            elif any(start < old_end and old_start < end
                     for old_start, old_end in windows):
                print("Time windows must not overlap. Try again.")
            else:
                windows.append((start, end))
                break

    tasks = []
    count = ask_positive_integer("How many subjects? ")
    for index in range(count):
        name = ""
        while not name:
            name = input(f"Name of subject #{index + 1}: ").strip()
            if not name:
                print("Subject name cannot be empty.")
        exam_date = ask_date("Exam date (YYYY-MM-DD): ")
        minutes = ask_positive_integer("Remaining study time (minutes, divisible by 30): ", 30)
        tasks.append({"subject": name, "exam_date": exam_date, "minutes": minutes})

    slots = []
    for day_offset in range(7):
        day = start_date + timedelta(days=day_offset)
        for start, end in windows:
            slots.append({"date": day, "start": start, "end": end})
    return start_date, tasks, slots
