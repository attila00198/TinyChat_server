# TinyChat Server Docker

This file explains how to build and run the TinyChat server using Docker.

Build the image (from the `chat_server` directory):

```powershell
docker build -t tinychat-server:latest .
```

Run the container, exposing port 8765 (change env as needed):

```powershell
docker run -d -p 8765:8765 --name tinychat-server \
  -e MOD_PASSWORD=yourpassword \
  tinychat-server:latest
```

Logs:

```powershell
docker logs -f tinychat-server
```

Override host/port with environment variables (if main.py reads them in future):

```powershell
docker run -d -p 8765:8765 -e HOST=0.0.0.0 -e PORT=8765 tinychat-server:latest
```
