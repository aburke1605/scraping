import os
from dotenv import load_dotenv
load_dotenv()

import requests
from datetime import datetime, timedelta, timezone
import hashlib
import smtplib
from email.message import EmailMessage

print(f"[{datetime.now(timezone(timedelta(hours=12)))}] STARTED SCRIPT")

url = "https://prod-nz-rdr.recreation-management.tylerapp.com/nzrdr/rdr/search/greatwalkplacefacility"
headers = {
    "accept": "application/json",
    "accept-language": "en-US,en-GB;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://bookings.doc.govt.nz",
    "priority": "u=1, i",
    "referer": "https://bookings.doc.govt.nz/",
    "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
    ),
}
payload = {
    "accomodation": "",
    "placeId": 873,
    "customerClassificationId": 1,
    "nights": 2,
}

date = datetime(2026, 11, 1)
end_date = datetime(2027, 4, 28)

order = {
    "Clinton Hut": 0,
    "Mintaro Hut": 1,
    "Dumpling Hut": 2,
}


body = "<html><body>Availabilities:<br>"
were_in_business = False
while date <= end_date:
    arrivalDate = date.date().strftime("%Y-%m-%d")

    payload["arrivalDate"] = arrivalDate
    response = requests.post(url, headers=headers, json=payload)

    data = response.json()["GreatWalkFacilityData"]
    n_huts = len(data) # should be 3 (3 huts)
    min_beds_available = 100 # arbitrary large number
    is_available = True
    for i in range(n_huts):
        name = data[i]["FacilityName"]
        date_data = data[i]["GreatWalkFacilityDateData"][order[name]]
        is_available &= date_data["IsAvailable"]
        beds_available = date_data["TotalAvailable"]
        if beds_available > 0:
            print(f"{name}:\n", date_data)
        min_beds_available = min(min_beds_available, beds_available)

    if min_beds_available > 1 and is_available:
        were_in_business = True
        body += f"{min_beds_available} beds from {arrivalDate}<br>"
        body += "<a href=\"https://bookings.doc.govt.nz/Web/Default.aspx#!greatwalk-result\">https://bookings.doc.govt.nz/Web/Default.aspx#!greatwalk-result</a><br>"

    date = date + timedelta(days=1)
body += "</body></html>"

if were_in_business:
    # don't repeatedly send emails
    hash_key_file = "last_email_hash.txt"
    hash_object = hashlib.sha256(body.encode("utf-8"))
    new_hash_key = hash_object.hexdigest()
    previous_hash_key = open(hash_key_file).readlines()[0]
    if new_hash_key == previous_hash_key:
        print("same availability - skipping email")

    else:
        with open(hash_key_file, "w") as f:
            f.write(new_hash_key)

        smtp_server = "in-v3.mailjet.com"
        port = 587

        msg = EmailMessage()
        msg["From"] = "aodhan-burke@hotmail.co.uk"
        msg["To"] = ["aodhanburke@hotmail.com", "jessicayukamccrory@gmail.com"]
        msg["Subject"] = "New Milford Track availability"
        msg.set_content("Your email client does not support HTML.")
        msg.add_alternative(body, subtype="html")

        with smtplib.SMTP(smtp_server, port, timeout=10) as server:
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(os.getenv("api_key"), os.getenv("secret_key"))
            server.send_message(msg)
            server.quit()

else:
    print("no availability")

print(f"[{datetime.now(timezone(timedelta(hours=12)))}] FINISHED SCRIPT")
print("\n\n\n\n\n\n\n\n")
