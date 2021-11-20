import json
import struct
import threading
from typing import List, Optional
import os

import aiohttp
import pypresence
import asyncio
from urllib.parse import quote
import websockets
import pystray
from PIL import Image


def patch_async_pypresence_client(client: pypresence.AioClient):
    old = client.on_event

    def sync_on_event(data):
        asyncio.get_event_loop().create_task(old(data))

    client.on_event = sync_on_event


def uses_rpc(f):
    async def inner(self, *args, **kwargs):
        try:
            return await f(self, *args, **kwargs)
        except struct.error:
            print("Discord closed")
            self._rpc_stop_evt.set()
    return inner


class DoorMuteClient:
    def __init__(self, host: str, key: str):
        self.host: str = host
        self.key: str = quote(key)

        self.rpc: Optional[pypresence.AioClient] = None
        self.socket: websockets.WebSocketClientProtocol = None
        self.client_id: Optional[str] = None
        self.scopes: List[str] = []
        self._rpc_stop_evt = asyncio.Event()
        self.active = True

    @property
    def api_route(self):
        return "http://" + self.host

    @property
    def websocket_route(self):
        return "ws://" + self.host + "/subscribe"

    async def handle_voice_select(self, data):
        if data["channel_id"] is not None:
            await self.socket.send(json.dumps({"action": "VC_JOIN"}))
        else:
            await self.socket.send(json.dumps({"action": "VC_LEAVE"}))

    async def open_rpc(self):
        while True:
            try:
                await self.start_rpc()
                await self._rpc_stop_evt.wait()
                self._rpc_stop_evt.clear()
            except pypresence.InvalidPipe:
                pass

            print("no discord client found, retrying in 10 sec")
            await asyncio.sleep(5)

    async def start(self):
        await self.fetch_server_info()
        asyncio.get_event_loop().create_task(self.open_rpc())

        do = True
        while do:
            try:
                do = await self.start_websocket()
            except (websockets.ConnectionClosedError, ConnectionResetError, OSError):
                do = True
            if do:
                await asyncio.sleep(5)

    async def start_rpc(self):
        self.rpc = pypresence.AioClient(client_id=self.client_id)
        patch_async_pypresence_client(self.rpc)

        await self.rpc.start()
        access_token = await self.fetch_token()
        await self.rpc.authenticate(access_token)

        print("Authenticated and connected to Discord Client")

        await self.rpc.register_event("VOICE_CHANNEL_SELECT", self.handle_voice_select)

    @uses_rpc
    async def handle_mute_packet(self, data):
        if not self.active:
            print("Not active")
            return

        print("Muting Client")
        await self.rpc.set_voice_settings(mute=True)

    async def start_websocket(self):
        async with websockets.connect(f"{self.websocket_route}?key={self.key}") as ws:
            print("Websocket Connection Opened")
            self.socket = ws
            while ws.open:
                p = json.loads(await ws.recv())
                if p["action"] == "MUTE_CLIENT":
                    await self.handle_mute_packet(p)
        return True

    async def fetch_server_info(self):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.api_route}/meta?key={self.key}") as r:
                r.raise_for_status()
                data = await r.json()
                self.client_id, self.scopes = data["client_id"], data["scopes"]

    async def authorize(self):
        print("Authorizing..")
        e = await self.rpc.authorize(self.client_id, self.scopes)

        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.api_route}/generate?key={self.key}&code={e['data']['code']}") as r:
                r.raise_for_status()
                r = await r.json()

        return r["access_token"]

    async def fetch_token(self):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.api_route}/token?key={self.key}") as r:
                r = await r.json()

                if r.get("code") == 4030:  # invalid / no password
                    raise ValueError("invalid password")

                if r.get("code") == 4011:  # not authorized with discord
                    return await self.authorize()

        return r["access_token"]


async def main():
    with open("client.json") as f:
        data = json.loads(f.read())
        config = data["server_host"], data["password"]

    client = DoorMuteClient(*config)

    if os.name == "nt":
        threading.Thread(target=icon_thread, daemon=True, args=(client, )).start()

    await client.start()


def icon_thread(client: DoorMuteClient):
    icon = pystray.Icon("DoorMute")
    image = Image.open("resources/icon.ico")
    icon.icon = image
    client.active = False

    def set_active():
        client.active = not client.active
        text = "Enabled" if client.active else "Disabled"
        toggle = pystray.MenuItem(text, set_active, checked=lambda x: client.active)
        icon.menu = pystray.Menu(toggle)

    set_active()
    icon.run()


if __name__ == '__main__':
    # todo: icons for client + installer
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("Closing Client")
