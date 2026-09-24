import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Configuration
INPUT_FILE = "input.htm"
OUTPUT_FILE = "schedule.ics"

# Mapping Hebrew days to Python's weekday index (0=Monday, 6=Sunday) and ICS rule days
DAYS_MAP = {
    "א'": {"py_weekday": 6, "rrule": "SU"},
    "ב'": {"py_weekday": 0, "rrule": "MO"},
    "ג'": {"py_weekday": 1, "rrule": "TU"},
    "ד'": {"py_weekday": 2, "rrule": "WE"},
    "ה'": {"py_weekday": 3, "rrule": "TH"},
    "ו'": {"py_weekday": 4, "rrule": "FR"},
}


def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD (e.g., 2026-10-18).")


def generate_ics(events, end_date):
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//My Schedule Converter//EN",
        "CALSCALE:GREGORIAN",
    ]

    # Format the end date for the UNTIL rule in UTC format (YYYYMMDDTHHMMSSZ)
    until_str = end_date.strftime('%Y%m%dT235959Z')

    for event in events:
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"SUMMARY:{event['name']} ({event['type']})",
            f"DTSTART;TZID=Asia/Jerusalem:{event['start_dt'].strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Asia/Jerusalem:{event['end_dt'].strftime('%Y%m%dT%H%M%S')}",
            f"RRULE:FREQ=WEEKLY;BYDAY={event['rrule_day']};UNTIL={until_str}",
            f"LOCATION:{event['room']}",
            f"DESCRIPTION:Lecturer: {event['lecturer']}\\nCourse Code: {event['code']}",
            "END:VEVENT"
        ])

    ics_lines.append("END:VCALENDAR")
    return "\n".join(ics_lines)


def parse_schedule(html_content, start_date):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='ContentPlaceHolder1_PeriodScheduleA_gvPeriodSchedule')

    events = []

    if not table:
        print("Could not find the schedule table in the HTML.")
        return events

    rows = table.find_all('tr', class_='GridRow')

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 13:
            continue

        day_text = cols[0].get_text(strip=True).replace('\xa0', '')
        time_text = cols[1].get_text(strip=True).replace('\xa0', '')

        # Skip rows without a defined day or time
        if not day_text or not time_text or day_text not in DAYS_MAP:
            continue

        name = cols[2].get_text(strip=True)
        code = cols[3].get_text(strip=True)
        lecturer = cols[8].get_text(strip=True)
        room = cols[9].get_text(strip=True)
        lesson_type = cols[12].get_text(strip=True)

        # Parse times
        start_time_str, end_time_str = time_text.split('-')
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))

        # Calculate the date of the first occurrence of this specific weekday
        day_info = DAYS_MAP[day_text]
        target_weekday = day_info['py_weekday']

        days_ahead = target_weekday - start_date.weekday()
        if days_ahead < 0:
            days_ahead += 7  # Target day has already passed this week, move to next week

        first_event_date = start_date + timedelta(days=days_ahead)

        start_dt = first_event_date.replace(hour=start_hour, minute=start_minute)
        end_dt = first_event_date.replace(hour=end_hour, minute=end_minute)

        events.append({
            "name": name,
            "code": code,
            "lecturer": lecturer,
            "room": room,
            "type": lesson_type,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "rrule_day": day_info['rrule']
        })

    return events


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find '{INPUT_FILE}'.")
        return

    print("--- University Schedule to ICS Converter ---")
    start_date = get_date_input("Enter the semester START date (YYYY-MM-DD): ")
    end_date = get_date_input("Enter the semester END date (YYYY-MM-DD): ")

    if end_date < start_date:
        print("Error: End date cannot be before the start date.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    print(f"\nParsing '{INPUT_FILE}'...")
    events = parse_schedule(html_content, start_date)

    if not events:
        print("No valid events were found. Check the HTML format.")
        return

    ics_content = generate_ics(events, end_date)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(ics_content)

    print(f"Successfully generated '{OUTPUT_FILE}' with {len(events)} recurring weekly events.")


if __name__ == "__main__":
    main()