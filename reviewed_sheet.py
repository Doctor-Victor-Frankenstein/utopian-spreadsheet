from datetime import date, timedelta
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pprint
import time

# Everything outside because I can't be bothered doing this properly
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    "/home/amos/utopian-spreadsheet/client_secret.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("Utopian Reviews")

today = date.today()
offset = (today.weekday() - 3) % 7
this_week = today - timedelta(days=offset)
next_week = this_week + timedelta(days=7)
title_unreviewed = f"Unreviewed - {this_week:%b %-d} - {next_week:%b %-d}"
title_reviewed = f"Reviewed - {this_week:%b %-d} - {next_week:%b %-d}"

unreviewed = sheet.worksheet(title_unreviewed)
reviewed = sheet.worksheet(title_reviewed)

MAX_VOTE = {
    "ideas": 5.0,
    "development": 30.0,
    "bug-hunting": 8.0,
    "translations": 20.0,
    "graphics": 25.0,
    "analysis": 25.0,
    "social": 15.0,
    "documentation": 15.0,
    "tutorials": 15.0,
    "video-tutorials": 20.0,
    "copywriting": 15.0,
    "blog": 15.0,
}


def main():
    time.sleep(1)
    result = unreviewed.get_all_values()
    for row in result[1:]:
        moderator = row[0]
        score = row[5]
        if moderator != "" and score != "":
            # Calculate voting %
            if float(score) >= 40:
                category = row[4]
                try:
                    max_vote = MAX_VOTE[category]
                except:
                    max_vote = 4.0
                    # Also set to pending
                row[-2] = "Pending"
                row[-1] = float(score) / 100.0 * max_vote
            else:
                row[-1] = 0.0
            unreviewed.delete_row(result.index(row) + 1)
            reviewed.append_row(row)
            return

if __name__ == '__main__':
    main()
