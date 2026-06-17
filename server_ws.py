import subprocess
import time
import asyncio
import websockets
import os
import threading

class MinecraftServerManager:
    def __init__(self, server_jar_path, max_idle_time=300):
        self.server_jar_path = server_jar_path
        self.process = None
        self.max_idle_time = max_idle_time
        self.last_active_time = None
        self.check_interval = 60
        self.player_count = 0
        self.websocket_port = 5487
        self.clients = set()

    def start_server(self):
        """Starts MC Server via subprocess"""
        if not self.process:
            print("Starting Minecraft server...")
            self.process = subprocess.Popen(
                ['java', '-Xmx16384M', '-Xms2048M', '-jar', f"{self.server_jar_path}\\fabric-server-launch.jar"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True
            )
            while self.process:
                output = self.process.stdout.readline()
                if output == "" and self.process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if "Done" in line and "For help, type \"help\"" in line:
                        self.last_active_time = time.time()
                        asyncio.create_task(self.broadcast("(status):Online"))
                        asyncio.create_task(self.broadcast("(logmsg):Minecraft Server successfully started."))
                        asyncio.create_task(self.broadcast(f"(player_count):{self.get_player_count()}"))
                        break

        else:
            print("Minecraft server is already running.")

    def stop_server(self):
        if self.process:
            print("Stopping Minecraft server...")
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            self.process.wait()
            self.process = None
            asyncio.create_task(self.broadcast("(status):Offline"))
            asyncio.create_task(self.broadcast("(logmsg):Minecraft server stopped."))

    def get_player_count(self):
        if self.process:
            self.process.stdin.write("/list\n")
            self.process.stdin.flush()

            while True:
                output = self.process.stdout.readline()
                if 'players online:' in output:
                    print(f"Server response: {output}")
                    self.player_count = self.parse_player_count(output)
                    return self.player_count
                if output == '' and self.process.poll() is not None:
                    break
        return 0

    def parse_player_count(self, output):
        """Parse the '/list' command output to extract the player count."""
        if 'There are' in output:
            try:
                start_index = output.index('There are') + len('There are ')
                end_index = output.index(' of a max')
                player_count_str = output[start_index:end_index].split(' ')[0]
                return int(player_count_str)
            except ValueError:
                pass
        return 0

    async def monitor_players(self):
        while True:
            if self.process:
                player_count = self.get_player_count()
                # await self.websocket.send(f"(player_count):{player_count}")
                print(f"Player count: {player_count}")

                if player_count > 0:
                    self.last_active_time = time.time()
                elif time.time() - self.last_active_time > self.max_idle_time:
                    print(f"No players detected for {self.max_idle_time} seconds. Stopping server...")
                    # await self.websocket.send(f"(logmsg):No players detected for {self.max_idle_time} seconds. Stopping server...")
                    self.stop_server()
            await asyncio.sleep(self.check_interval)

    async def websocket_handler(self, websocket, path):
        """Handles incoming WebSocket messages."""
        self.clients.add(websocket)
        try:
            async for message in websocket:
                if message == "start":
                    if self.process:
                        response = "(logmsg):Server is already running."
                        print(response)
                        await websocket.send(response)
                    else:
                        response = "(logmsg):Starting the Minecraft server..."
                        print(response)
                        await websocket.send(response)
                        self.start_server()

                elif message == "status":
                    if self.process:
                        response = "(status):Online"
                    else:
                        response = "(status):Offline"
                    print(f"Status request: {response}")
                    await websocket.send(response)

                elif message == "players":
                    if self.process:
                        player_count = self.get_player_count()
                        response = f"(player_count):{player_count}"
                    else:
                        response = "(player_count):N/A"
                    print(response)
                    await websocket.send(response)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Client connection closed unexpectedly: {e}")
        except asyncio.exceptions.IncompleteReadError as e:
            print(f"Incomplete read error: {e}")
        finally:
            self.clients.remove(websocket)
            print("client disconnected.")

    async def websocket_server(self):
        """Starts a WebSocket server to handle client messages."""
        server = await websockets.serve(self.websocket_handler, "localhost", self.websocket_port)
        await server.wait_closed()

    async def broadcast(self , message):
        """Broadcasts a message to all connected WebSocket clients."""
        if self.clients:
            print(message)
            await asyncio.gather(*[client.send(message) for client in self.clients])


if __name__ == "__main__":
    # Minecraft server folder path
    server_path = "C:\\Users\\rocke\Desktop\ServerStarter\mc_server"
    os.chdir(server_path)

    server_manager = MinecraftServerManager(server_jar_path=server_path)

    loop = asyncio.get_event_loop()

    asyncio.ensure_future(server_manager.websocket_server())
    asyncio.ensure_future(server_manager.monitor_players())


    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        server_manager.stop_server()
        loop.close()

