import asyncio
import websockets
import json
import logging
import os
import ssl

from dotenv import load_dotenv
from datetime import datetime
from websockets import ServerConnection

# Konfiguráció (környezeti változókból is felülírható)
load_dotenv()
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))
MOD_PASSWORD = os.getenv("MOD_PASSWORD", "admin123")

# SSL/TLS Configuration
USE_SSL = os.getenv("USE_SSL", "False").lower() == "true"
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "./certs/server.crt")
SSL_KEY_PATH = os.getenv("SSL_KEY_PATH", "./certs/server.key")

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


def getCurrentTime():
    return datetime.now().strftime("%H:%M:%S")


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
    return {cmd: {"usage": info["usage"]} for cmd, info in COMMANDS.items()}


def find_user_by_username(username):
    """User keresése username alapján"""
    for client_id, user_data in users.items():
        if user_data["username"] == username:
            return client_id, user_data
    return None, None


###############################
####  Command Handlers     ####
###############################


async def handle_whisper(username: str, args: list, websocket: ServerConnection):
    """Whisper parancs kezelése"""
    if len(args) < 2:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": "Használat: /whisper [cél_user] [üzenet]",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    target_user = args[0]
    message_content = " ".join(args[1:])

    # Ellenőrzés: létezik-e a target user
    target_id, target_data = find_user_by_username(target_user)
    if not target_data:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": f"User '{target_user}' nem található",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    # Private üzenet a címzettnek
    private_msg = {
        "type": "private",
        "from": username,
        "to": target_user,
        "content": message_content,
        "timestamp": getCurrentTime(),
    }
    await send_to_user(target_user, private_msg)
    await send_to_user(username, private_msg)


async def handle_login(username: str, args: list, websocket: ServerConnection):
    """Login parancs kezelése: /login [jelszó]

    If the provided password matches MOD_PASSWORD, promote the calling
    user to moderator (is_mod=True) and broadcast updated user list.
    """
    if len(args) < 1:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": "Használat: /login [jelszó]",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    password = args[0]

    # Find caller
    client_id, user_data = find_user_by_username(username)
    if not user_data:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": "Hiba: felhasználó nem található",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    if user_data.get("is_mod", False):
        info = {
            "type": "system",
            "username": "System",
            "content": "Már moderátor vagy",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, info)
        return

    # Braadcast if someone gets moderator role
    if password == MOD_PASSWORD:
        user_data["is_mod"] = True
        success = {
            "type": "system",
            "username": "System",
            "content": f"{user_data['username']} moderátor lett.",
            "timestamp": getCurrentTime(),
        }
        await broadcast(success)

        # Broadcast updated user list to everyone
        user_list_message = {
            "type": "user_list",
            "content": get_user_list(),
            "timestamp": getCurrentTime(),
        }
        await broadcast(user_list_message)
        logger.info(f"[INFO]: {username} promoted to moderator")
    else:
        fail = {
            "type": "error",
            "username": "System",
            "content": "Hibás jelszó",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, fail)


async def handle_timeout(username: str, args: list, websocket: ServerConnection):
    """Handle the /to (timeout) command.

    Usage: /to [target_user] [seconds]
    Only moderators can invoke this command. When called it will set the
    target user's `is_timed_out` flag and schedule an expiry task that will
    un-mute the user after the given number of seconds.
    """
    # Validate args
    if len(args) < 2:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": "Használat: /to [cél_user] [idő másodpercben]",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    target_username = args[0]
    try:
        seconds = int(args[1])
        if seconds <= 0:
            raise ValueError()
    except ValueError:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": "Az időnek pozitív egész számnak kell lennie",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    # Verify caller is moderator
    caller_id, caller_data = find_user_by_username(username)
    if not caller_data or not caller_data.get("is_mod", False):
        error_msg = {
            "type": "error",
            "username": "System",
            "content": "Csak moderátorok használhatják ezt a parancsot",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    # Find target user
    target_id, target_data = find_user_by_username(target_username)
    if not target_data:
        error_msg = {
            "type": "error",
            "username": "System",
            "content": f'User "{target_username}" nem található',
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)
        return

    # Apply timeout
    target_data["is_timed_out"] = True

    # Cancel previous timeout task if exist
    if target_username in timeout_tasks:
        try:
            timeout_tasks[target_username].cancel()
        except Exception as e:
            logger.exception(
                f"Failed to cancel existing timeout task for {target_username}: {e}"
            )

    # Expiry coroutine
    async def _expire_timeout(t_username: str, t_seconds: int):
        await asyncio.sleep(t_seconds)
        cid, udata = find_user_by_username(t_username)
        if cid and udata:
            udata["is_timed_out"] = False

            # Notify timed-out user
            system_msg = {
                "type": "system",
                "username": "System",
                "content": "Némításod lejárt, újra írhatsz",
                "timestamp": getCurrentTime(),
            }
            await send_to_user(t_username, system_msg)

            # Broadcast updated user list
            user_list_message = {
                "type": "user_list",
                "content": get_user_list(),
                "timestamp": getCurrentTime(),
            }
            await broadcast(user_list_message)

            logger.info(f"[INFO]: {t_username} timeout lejárt")

        # Clean up task record
        if t_username in timeout_tasks:
            del timeout_tasks[t_username]

    # Schedule expiry task
    task = asyncio.create_task(_expire_timeout(target_username, seconds))
    timeout_tasks[target_username] = task

    # Broadcast system message
    broadcast_msg = {
        "type": "system",
        "username": "System",
        "content": f"{username} némította {target_username}-t {seconds} másodpercre",
        "timestamp": getCurrentTime(),
    }
    await broadcast(broadcast_msg)

    # Broadcast updated user list
    user_list_message = {
        "type": "user_list",
        "content": get_user_list(),
        "timestamp": getCurrentTime(),
    }
    await broadcast(user_list_message)

    logger.info(f"[INFO]: {target_username} némítva {seconds} másodpercre")


async def handle_help(username: str, args: list, websocket: ServerConnection):
    """Help parancs kezelése"""
    response = {
        "type": "system",
        "username": "System",
        "content": "Command '/help' Not implemented",
        "timestamp": getCurrentTime(),
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
        "handler": handle_timeout,
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
            "type": "error",
            "username": "System",
            "content": f"Ismeretlen parancs: {command}",
            "timestamp": getCurrentTime(),
        }
        await send_to_user(username, error_msg)


###############################
####   WebSocket Server    ####
###############################


async def send_to_user(username, message):
    """Üzenet küldése egy adott usernek"""
    for user_data in users.values():
        if user_data["username"] == username:
            try:
                await user_data["websocket"].send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed as e:
                logger.debug(f"Connection closed when sending to {username}: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error when sending to {username}: {e}")
            break


async def broadcast(message, exclude=None):
    """Üzenet broadcast minden kliensnek (exclude kivételével)"""
    # iterate over a snapshot to avoid runtime errors if users is modified
    for client_id, user_data in list(users.items()):
        if client_id != exclude:
            try:
                await user_data["websocket"].send(json.dumps(message))
                logger.debug(f"Elküldve: {message}")
            except websockets.exceptions.ConnectionClosed as e:
                logger.debug(f"Connection closed when broadcasting to {client_id}: {e}")
            except Exception as e:
                logger.exception(
                    f"Unexpected error when broadcasting to {client_id}: {e}"
                )


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

    try:
        async for message in websocket:
            try:
                # JSON üzenet feldolgozása
                data = json.loads(message)
                logger.debug(f"Fogadva: {data}")

                # Username mentése ha még nincs
                if "username" in data and users[client_id]["username"] is None:
                    users[client_id]["username"] = data["username"]
                    logger.info(f"Felhasználónév beállítva: {data['username']}")
                    logger.info(f"Aktív userek száma: {len(users)}")

                    # Frissített user lista küldése MINDENKINEK
                    user_list_message = {
                        "type": "user_list",
                        "content": get_user_list(),
                        "timestamp": getCurrentTime(),
                    }
                    await broadcast(user_list_message)
                    # Parancs lista elküldése az új felhasználónak.
                    command_list_message = {
                        "type": "command_list",
                        "content": get_command_list(),
                        "timestamp": getCurrentTime(),
                    }
                    await send_to_user(
                        users[client_id]["username"], command_list_message
                    )

                # Üzenet típus validálása
                msg_type = data.get("type")
                valid_types = ["public", "command", "join"]

                if msg_type not in valid_types:
                    error_response = {
                        "type": "error",
                        "username": "System",
                        "content": "[ERROR]: Hibás üzenet típus.",
                        "timestamp": getCurrentTime(),
                    }
                    await send_to_user(users[client_id]["username"], error_response)

                if users[client_id]["is_timed_out"]:
                    # Timeout ellenőrzés
                    timeout_msg = {
                        "type": "system",
                        "username": "System",
                        "content": "Jelenleg némítva vagy",
                        "timestamp": getCurrentTime(),
                    }
                    await websocket.send(json.dumps(timeout_msg))
                    continue

                elif msg_type == "join":
                    join_message = {
                        "type": "system",
                        "username": "System",
                        "content": f"{users[client_id]['username']} csatlakozott.",
                        "timestamp": getCurrentTime(),
                    }
                    await broadcast(join_message)
                    continue

                elif msg_type == "command":
                    # COMMAND típus kezelése
                    await process_command(client_id, data, websocket)
                    continue

                elif msg_type == "public":
                    # PUBLIC típus kezelése
                    message_data = {
                        "type": "public",
                        "username": data.get("username", users[client_id]["username"]),
                        "content": data.get("content", ""),
                        "timestamp": getCurrentTime(),
                    }
                    await broadcast(message_data, exclude=client_id)
                    continue
                else:
                    continue

            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "username": "System",
                    "content": "[ERROR]: Érvénytelen JSON formátum",
                    "timestamp": getCurrentTime(),
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
                    "timestamp": getCurrentTime(),
                }
                await broadcast(user_list_message)


async def start_server():
    """WebSocket szerver indítása SSL/TLS támogatással"""
    ssl_context = None
    protocol = "ws"
    
    if USE_SSL:
        # SSL context létrehozása
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
            protocol = "wss"
            logger.info(f"SSL/TLS engedélyezve: cert={SSL_CERT_PATH}, key={SSL_KEY_PATH}")
        except FileNotFoundError as e:
            logger.error(f"SSL tanúsítvány nem található: {e}")
            logger.warning("Visszavonás: SSL nélkül futtatás")
            ssl_context = None
        except Exception as e:
            logger.error(f"SSL kontextus létrehozása sikertelen: {e}")
            ssl_context = None
    
    async with websockets.serve(handle_client, HOST, PORT, ssl=ssl_context):
        logger.info(f"WebSocket szerver fut: {protocol}://{HOST}:{PORT}")
        logger.info(f"Várakozás kliensekre...")
        await asyncio.Future()  # Run forever


def run_server():
    """Szerver futtatása külön szálon"""
    asyncio.run(start_server())


if __name__ == "__main__":
    # Non-interactive server start: run the asyncio server in the current
    # process. Use Ctrl+C to stop the server (KeyboardInterrupt will be
    # handled and logged).
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Szerver leállítása...")
