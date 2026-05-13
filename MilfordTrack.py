import os
from dotenv import load_dotenv
load_dotenv()

import requests
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage

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
    # available = True
    min_beds_available = 100 # arbitrary large number
    for i in range(n_huts):
        name = data[i]["FacilityName"]
        date_data = data[i]["GreatWalkFacilityDateData"][order[name]]
        beds_available = date_data["TotalAvailable"]
        min_beds_available = min(min_beds_available, beds_available)
        # available &= beds_available > 0

    # if available:
    if min_beds_available > 0:
        were_in_business = True
        body += f"{min_beds_available} beds from {arrivalDate}<br>"

    date = date + timedelta(days=1)
body += "</body></html>"

if were_in_business:
    smtp_server = "in-v3.mailjet.com"
    port = 587

    msg = EmailMessage()
    msg["From"] = "aodhan-burke@hotmail.co.uk"
    msg["To"] = ["aodhanburke@hotmail.com"]
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
