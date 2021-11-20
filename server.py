import json

import aiohttp

import util
import time
from sanic import Sanic
from sanic.response import json as jsonify


config, save_config = util.use_json_file("serverdata.json")
app = Sanic(__name__)
pw = config()["password"]
connections = []


def requires_password(f):
    async def inner(req, *args):
        if req.args.get("key") != pw:
            return jsonify({"error": "invalid password", "code": 4010}, status=401)
        return await f(req, *args)
    return inner


def update_config(current_config, token_response):
    current_config["refresh_token"] = token_response["refresh_token"]
    current_config["access_token"] = token_response["access_token"]
    current_config["expires"] = time.time() + token_response["expires_in"]
    return save_config(current_config)


async def refresh_token():
    conf = config()
    async with aiohttp.ClientSession() as s:
        async with s.post("https://discord.com/api/oauth2/token", data={
            "client_id": conf["client_id"],
            "client_secret": conf["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": conf["refresh_token"]
        }, headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        }) as r:
            return update_config(conf, await r.json())


@app.get("/token")
@requires_password
async def get_access_token(_):
    conf = config()

    if not conf.get("access_token") and not conf.get("refresh_token"):
        return jsonify({"error": "not authorized with discord", "code": 4011}, status=401)

    if conf.get("expires") <= time.time() or not conf.get("access_token"):
        print("refreshing token")
        conf = await refresh_token()

    return jsonify({"access_token": conf["access_token"], "code": 2000})


@app.get("/generate")
@requires_password
async def auth_callback(req):
    code = req.args["code"]

    if not code:
        return jsonify({"error": "no token provided", "code": 4002}, status=400)

    conf = config()

    async with aiohttp.ClientSession() as s:
        async with s.post("https://discord.com/api/oauth2/token", data={
            "client_id": conf["client_id"],
            "client_secret": conf["client_secret"],
            "grant_type": "authorization_code",
            "code": code
        }, headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        }) as r:
            update_config(conf, await r.json())

    return jsonify({"access_token": conf["access_token"], "code": 2000})


@app.route("/meta")
@requires_password
async def meta(_):
    return jsonify({
        "client_id": config()["client_id"],
        "scopes": ["rpc", "rpc.voice.read", "rpc.voice.write"]
    })


@app.route("/trigger")
@requires_password
async def trigger_mute(_):
    for c in connections:
        await c.send(json.dumps({"action": "MUTE_CLIENT"}))

    return jsonify({"success": "triggered mute", "code": 2000})


@app.websocket("/subscribe")
@requires_password
async def socket(_, ws):
    connections.append(ws)
    print(f"Connection opened, {len(connections)} clients connected")

    try:
        while True:
            pkt = json.loads(await ws.recv())
            if pkt["action"] == "VC_JOIN":
                print("joined vc")
            elif pkt["action"] == "VC_LEAVE":
                print("left vc")
    except:
        pass

    connections.remove(ws)
    print(f"Connection closed, {len(connections)} remaining")


if __name__ == '__main__':
    app.run("0.0.0.0", 3465)
