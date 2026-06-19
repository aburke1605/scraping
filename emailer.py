import os
from dotenv import load_dotenv
load_dotenv()

import requests
import pathlib
import hashlib
from datetime import datetime, timedelta, timezone
import argparse


client_id = os.getenv("client_id")


def get_device_code() -> str:
    data = {
        "client_id": client_id,
        "scope": "Mail.Send offline_access"
    }

    response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode",
        data=data
    )
    response.raise_for_status()

    response_data = response.json()

    device_code = response_data["device_code"]
    message = response_data["message"]

    print(message)
    print("Enter \"continue\" once finished to continue")
    while True:
        if input() == "continue":
            break
    
    return device_code


def get_access_token(device_code: str) -> tuple[str, str]:
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": device_code
    }

    response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data=data
    )
    response.raise_for_status()

    response_data = response.json()

    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]

    return access_token, refresh_token


def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "scope": "Mail.Send offline_access"
    }

    response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data=data
    )
    response.raise_for_status()

    response_data = response.json()

    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]

    return access_token, refresh_token


def read_tokens(token_file_name: str) -> tuple[str, str]:
    token_key_file = pathlib.Path(__file__).parent.as_posix() + "/" + token_file_name

    tokens = open(token_key_file).readlines()
    if len(tokens) != 2:
        raise ValueError

    access_token =  tokens[0].replace("access_token=", "").strip()
    refresh_token = tokens[1].replace("refresh_token=", "").strip()

    return access_token, refresh_token


def write_tokens(token_file_name: str, access_token: str, refresh_token: str):
    token_key_file = pathlib.Path(__file__).parent.as_posix() + "/" + token_file_name
    pathlib.Path(token_key_file).touch(exist_ok=True)
    with open(token_key_file, "w") as f:
        f.write(f"access_token={access_token}\n")
        f.write(f"refresh_token={refresh_token}")


def send_email(to_addresses: list[str], subject: str, body: str, access_token: str) -> str:
    data = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "html",
                "content": body
            },
            "toRecipients": [{
                "emailAddress": {
                    "address": address
                }
                for address in to_addresses
            }]
        },
        "saveToSentItems": True
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        json=data,
        headers=headers
    )

    response.raise_for_status()


def scrape() -> tuple[bool, str]:
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

        if min_beds_available >= 4 and is_available:
            were_in_business = True
            body += f"{min_beds_available} beds from {arrivalDate}<br>"
            body += "<a href=\"https://bookings.doc.govt.nz/Web/Default.aspx#!greatwalk-result\">https://bookings.doc.govt.nz/Web/Default.aspx#!greatwalk-result</a><br>"

        date = date + timedelta(days=1)
    body += "</body></html>"

    if were_in_business:
        # don't repeatedly send emails
        hash_key_file = pathlib.Path(__file__).parent.as_posix() + "/last_email_hash.txt"
        pathlib.Path(hash_key_file).touch(exist_ok=True)
        hash_object = hashlib.sha256(body.encode("utf-8"))
        new_hash_key = hash_object.hexdigest()
        previous_hash_key = open(hash_key_file).readlines()
        if len(previous_hash_key) != 0 and new_hash_key == previous_hash_key[0]:
            print("SAME AVAILABILITY - SKIPPING EMAIL")
            return False, ""

        else:
            with open(hash_key_file, "w") as f:
                f.write(new_hash_key)
            return True, body

    else:
        print("NO AVAILABILITY")
        return False, ""


def init(args):
    device_code = get_device_code()
    access_token, refresh_token = get_access_token(device_code=device_code)
    token_file_name = args.token_file_name
    write_tokens(token_file_name, access_token, refresh_token)


def run(args):
    print(f"[{datetime.now(timezone(timedelta(hours=12)))}] STARTED SCRIPT")

    token_file_name = args.token_file_name
    recipients =      args.recipients
    subject =         args.subject
    body =            args.body

    previous_access_token, previous_refresh_token = read_tokens(token_file_name)

    subject = "New Milford Track availability"
    send, body = scrape()
    if send:
        try:
            send_email(recipients, subject, body, previous_access_token)
        except Exception:
            access_token, refresh_token = refresh_access_token(refresh_token=previous_refresh_token)
            send_email(recipients, subject, body, access_token)
            write_tokens(token_file_name, access_token, refresh_token)

    print(f"[{datetime.now(timezone(timedelta(hours=12)))}] FINISHED SCRIPT")
    print("\n\n\n\n\n\n\n\n")

def emailer():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )


    def add_subparser(name: str, func, **kwargs):
        p = subparsers.add_parser(name, **kwargs)
        p.set_defaults(func=func)
        p.add_argument(
            "--token-file-name",
            type=str,
            required=True,
            help="name of file tokens will be stored in",
        )
        return p


    add_subparser(
        "init",
        init,
        help="get new device code to initialise email service",
        description="get new device code to initialise email service",
    )

    run_parser = add_subparser(
        "run",
        run,
        help="run emailer after initialisation",
        description="run emailer after initialisation",
    )
    run_parser.add_argument(
        "--subject",
        type=str,
        required=True,
        help="email subject",
    )
    run_parser.add_argument(
        "--body",
        type=str,
        required=True,
        help="email body",
    )
    run_parser.add_argument(
        "--recipients",
        type=str,
        nargs="+",
        required=True,
        help="recipient email address(es)",
    )

    args = parser.parse_args()

    args.func(args)

if __name__ == "__main__":
    emailer()