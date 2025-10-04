import json
from datetime import datetime

MOD_PASSWORD = "admin123"
users = {"123123": {"username": "Kamakosan", "is_mod": True, "is_timed_out": False}}


def handle_login(username: str, args: list):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print("OK")


def handle_to(username: str, args: list):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print("OK")


def handle_whisper(username: str, args: list):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print("OK")


def handle_help(username: str, args: list):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print("OK")


"""Command List"""
COMMANDS = {
    "/whisper": {
        "usage": "/whisper [cél_user] [üzenet]",
        "handler": handle_whisper,
    },
    "/login": {
        "usage": "/login [jelszó]",
        "handler": handle_login,
    },
    "/to": {
        "usage": "/to [cél_user] [idő]",
        "handler": handle_to,
    },
    "/help": {"usage": "/help [parancs](oprionális)", "handler": handle_help},
}


def process_command(client_id: str, data: str):
    """Parancsok feldolgozása"""
    username = users[client_id]["username"]

    parts = data.split(" ")
    command = parts[0]
    args = parts[1:]
    print(f"Callser of the command: {username}")
    print(f"Command: {command}")
    print(f"Args: {args}")

    if command in COMMANDS:
        print(f"Parancs megtalálva: {COMMANDS[command]}")
        handler = COMMANDS[command]["handler"]
        handler(username, args)
    else:
        print(f"Ismeretlen parancs: {command}")


if __name__ == "__main__":
    process_command("123123", "/login admin123")
