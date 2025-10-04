import asyncio
import websockets
import json
import logging

from datetime import datetime
from threading import Thread
from websockets import ServerConnection

# Konfiguráció
HOST = "0.0.0.0"
PORT = 8765
MOD_PASSWORD = "admin123"

# User információk tárolása
users = {}
messages = {}

# Timeout timerek tárolása
timeout_tasks = {}

###############################
####    Setup Logging      ####
###############################
is_debug_enabled = True

logging.basicConfig(
    format="%(asctime)s [%(levelname)s]: [%(name)s] %(message)s", datefmt="%I:%M:%S %p"
)

logger = logging.getLogger("chat_server")
if is_debug_enabled:
    logger.level = logging.DEBUG
else:
    logger.level = logging.INFO


###############################
####   Helper Functions    ####
###############################


def get_user_list():
    """User lista összeállítása socket nélkül"""
    return [
        {
            "username": user_data["username"],
            "is_mod": user_data["is_mod"],
            "is_timed_out": user_data["is_timed_out"],
        }
        for user_data in users.values()
        if user_data["username"] is not None
    ]


def get_command_list():
    return {
        "type": "command_list",
        "username": "System",
        "content": "[INFO]: Not Implemented",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def find_user_by_username(username):
    """User keresése username alapján"""
    for client_id, user_data in users.items():
        if user_data["username"] == username:
            return client_id, user_data
    return None, None


async def send_to_user(username, message):
    """Üzenet küldése egy adott usernek"""
    for user_data in users.values():
        if user_data["username"] == username:
            try:
                await user_data["websocket"].send(json.dumps(message))
            except:
                pass
            break


async def broadcast(message, exclude=None):
    """Üzenet broadcast minden kliensnek (exclude kivételével)"""
    # Új dict készítése a type mezővel (ne módosítsuk az eredeti objektumot)

    for client_id, user_data in users.items():
        if client_id != exclude:
            try:
                await user_data["websocket"].send(json.dumps(message))
                logger.debug(f"Elküldve: {message}")
            except:
                pass


async def send_user_list(message):
    """User lista broadcast minden kliensnek"""
    for user_data in users.values():
        try:
            await user_data["websocket"].send(json.dumps(message))
        except:
            pass


async def send_command_list(message):
    for user_data in users.values():
        try:
            await user_data["websocket"].send(json.dumps(message))
        except:
            pass


###############################
####  Command Handlers     ####
###############################


async def handle_whisper(username: str, args: list, websocket: ServerConnection):
    """Whisper parancs kezelése"""
    if len(args) < 2:
        error_msg = {
            "type": "system",
            "username": "System",
            "content": "Használat: /whisper [cél_user] [üzenet]",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        await send_to_user(username, error_msg)
        return

    target_user = args[0]
    message_content = " ".join(args[1:])

    # Ellenőrzés: létezik-e a target user
    target_id, target_data = find_user_by_username(target_user)
    if not target_data:
        error_msg = {
            "type": "system",
            "username": "System",
            "content": f"User '{target_user}' nem található",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        await send_to_user(username, error_msg)
        return

    # Private üzenet a címzettnek
    private_msg = {
        "type": "private",
        "from": username,
        "to": target_user,
        "content": message_content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    await send_to_user(target_user, private_msg)
    await send_to_user(username, private_msg)


async def handle_login(username: str, args: list, websocket: ServerConnection):
    """Login parancs kezelése"""
    response = {
        "type": "system",
        "username": "System",
        "content": "Command '/login' Not implemented",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    await send_to_user(username, response)


async def handle_to(username: str, args: list, websocket: ServerConnection):
    """Timeout parancs kezelése"""
    response = {
        "type": "system",
        "username": "System",
        "content": "Command '/to' Not implemented",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    await send_to_user(username, response)


async def handle_help(username: str, args: list, websocket: ServerConnection):
    """Help parancs kezelése"""
    response = {
        "type": "system",
        "username": "System",
        "content": "Command '/help' Not implemented",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    await send_to_user(username, response)


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
    "/help": {"usage": "/help [parancs](opcionális)", "handler": handle_help},
}


async def process_command(client_id: int, data: dict, websocket: ServerConnection):
    """Parancsok feldolgozása"""
    username = users[client_id]["username"]
    content = data.get("content", "")

    parts = content.split(" ")
    command = parts[0]
    args = parts[1:]

    logger.debug(f"User of the command: {username}")
    logger.debug(f"Command: {command}")
    logger.debug(f"Args: {args}")

    if command in COMMANDS:
        handler = COMMANDS[command]["handler"]
        await handler(username, args, websocket)
    else:
        logger.error(f"Ismeretlen parancs: {command}")
        error_msg = {
            "type": "system",
            "username": "System",
            "content": f"Ismeretlen parancs: {command}",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        await send_to_user(username, error_msg)


###############################
####   WebSocket Server    ####
###############################


async def handle_client(websocket):
    """Kliens kapcsolat kezelése"""
    client_id = id(websocket)
    users[client_id] = {
        "websocket": websocket,
        "username": None,
        "is_mod": False,
        "is_timed_out": False,
    }

    logger.info(f"Új kliens csatlakozott. ID: {client_id}")
    logger.info(f"Aktív userek száma: {len(users)}")

    try:
        async for message in websocket:
            try:
                # JSON üzenet feldolgozása
                data = json.loads(message)
                logger.debug(f"received: ", data)

                # Username mentése ha még nincs
                if "username" in data and users[client_id]["username"] is None:
                    users[client_id]["username"] = data["username"]
                    logger.info(f"Felhasználónév beállítva: {data['username']}")

                    # Frissített user lista küldése MINDENKINEK
                    user_list_message = {
                        "type": "user_list",
                        "content": get_user_list(),
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    }
                    await send_user_list(user_list_message)
                    command_list_message = {
                        "type": "command_list",
                        "content": get_command_list(),
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    }
                    await send_command_list(command_list_message)

                # Üzenet típus validálása
                msg_type = data.get("type")
                valid_types = ["message", "command", "join"]

                if msg_type not in valid_types:
                    error_response = {
                        "type": "system",
                        "username": "System",
                        "content": "[ERROR]: Hibás üzenet típus.",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    }
                    await send_to_user(users[client_id]["username"], error_response)

                if users[client_id]["is_timed_out"]:
                    # Timeout ellenőrzés
                    timeout_msg = {
                        "type": "system",
                        "username": "System",
                        "content": "Jelenleg némítva vagy",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    }
                    await websocket.send(json.dumps(timeout_msg))
                    continue

                elif msg_type == "join":
                    # JOIN típus kezelése
                    join_message = {
                        "type": "system",
                        "username": "System",
                        "content": f"{users[client_id]['username']} csatlakozott.",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    }
                    await broadcast(join_message)
                    continue

                elif msg_type == "command":
                    # COMMAND típus kezelése
                    await process_command(client_id, data, websocket)
                    continue

                elif msg_type == "message":
                    # MESSAGE típus kezelése (public broadcast)
                    message_data = {
                        "username": data.get("username", users[client_id]["username"]),
                        "content": data.get("content", ""),
                    }
                    await broadcast(message_data, exclude=client_id)
                    continue
                else:
                    continue

            except json.JSONDecodeError:
                error_response = {
                    "type": "system",
                    "username": "System",
                    "content": "[ERROR]: Érvénytelen JSON formátum",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }
                await websocket.send(json.dumps(error_response))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Kliens lecsatlakozott: {client_id}")
    finally:
        # User törlése a listából
        if client_id in users:
            username = users[client_id]["username"]

            # Timeout timer törlése ha van
            if username and username in timeout_tasks:
                timeout_tasks[username].cancel()
                del timeout_tasks[username]

            del users[client_id]
            logger.info(f"Aktív felhasználók száma: {len(users)}")

            # Frissített user lista küldése mindenkinek
            if len(users) > 0:
                user_list_message = {
                    "type": "user_list",
                    "content": get_user_list(),
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }
                await send_user_list(user_list_message)


async def start_server():
    """WebSocket szerver indítása"""
    async with websockets.serve(handle_client, HOST, PORT):
        logger.info(f"WebSocket szerver fut: ws://{HOST}:{PORT}")
        logger.info(f"Várakozás kliensekre...")
        await asyncio.Future()  # Run forever


def run_server():
    """Szerver futtatása külön szálon"""
    asyncio.run(start_server())


if __name__ == "__main__":
    # Szerver indítása threadben
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()

    logger.info("Nyomj Enter-t a leállításhoz...")

    try:
        input()
    except KeyboardInterrupt:
        pass

    logger.info("Szerver leállítása...")
