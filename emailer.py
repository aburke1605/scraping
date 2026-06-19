import os
from dotenv import load_dotenv
load_dotenv()

import requests
import pathlib
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




def init(_):
    device_code = get_device_code()
    access_token, refresh_token = get_access_token(device_code=device_code)
    write_tokens("tokens.txt", access_token, refresh_token)


def run(_):
    previous_access_token, previous_refresh_token = read_tokens("tokens.txt")

    try:
        send_email(
            ["aodhan-burke@hotmail.co.uk"],
            "subject",
            "<html><body>b<br>o<br>d<br>y</body></html>",
            previous_access_token
        )
    except Exception:
        access_token, refresh_token = refresh_access_token(refresh_token=previous_refresh_token)
        
        send_email(
            ["aodhan-burke@hotmail.co.uk"],
            "subject",
            "<html><body>b<br>o<br>d<br>y</body></html>",
            access_token
        )

        write_tokens("tokens.txt", access_token, refresh_token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )


    def add_subparser(name: str, func, **kwargs):
        p = subparsers.add_parser(name, **kwargs)
        p.set_defaults(func=func)
        return p


    add_subparser(
        "init",
        init,
        help="get new device code to initialise email service",
        description="get new device code to initialise email service",
    )

    add_subparser(
        "run",
        run,
        help="run emailer after initialisation",
        description="run emailer after initialisation",
    )

    args = parser.parse_args()

    args.func(args)
    