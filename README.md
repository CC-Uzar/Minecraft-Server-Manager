# Minecraft-Server-Manager
Personal script used to manage a Minecraft Server

This Python script opens a WebSocket to receive remote requests to run a Minecraft server. Requests must follow a certain syntax and format and are otherwise ignored. The script also polls and reads the server output to determine when a server is empty long enough to be closed, to free up computer resources.
