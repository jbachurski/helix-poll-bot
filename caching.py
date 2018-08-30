import asyncio
import json

import discord

SUPPORTED_DISCORD_TYPES = (
    discord.Server, discord.Channel, discord.Message, 
    discord.Member, discord.User
)
SUPPORTED_DISCORD_TYPES_STR = (
    "Server", "Channel", "Message", "Member", "User"
)

def cache_discord_object(obj):
    if isinstance(obj, discord.Server):
        return {
            "type": "Server",
            "id": obj.id
        }
    elif isinstance(obj, discord.Channel):
        return {
            "type": "Channel",
            "id": obj.id,
            "server": cache_discord_object(obj.server)
        }
    elif isinstance(obj, discord.Message):
        return {
            "type": "Message",
            "id": obj.id,
            "channel": cache_discord_object(obj.channel)
        }
    elif isinstance(obj, discord.Member):
        return {
            "type": "Member",
            "id": obj.id,
            "server": cache_discord_object(obj.server)
        }
    elif isinstance(obj, discord.User):
        return {
            "type": "User",
            "id": obj.id
        }

def recover_discord_object(client, cache):
    if cache["type"] == "Server":
        return client.get_server(cache["id"])
    elif cache["type"] == "Channel":
        return cache["server"].get_channel(cache["id"])
    elif cache["type"] == "Message":
        return client.get_message(cache["channel"], cache["id"])
    elif cache["type"] == "Member":
        return cache["server"].get_member(cache["id"])
    elif cache["type"] == "User":
        return client.get_user_info(cache["id"])
    else:
        raise ValueError("Unknown discord type.")

def discord_support_decoder_hook_factory(client):
    def discord_support_decoder_hook(dct):
        if "type" in dct and dct["type"] in SUPPORTED_DISCORD_TYPES_STR:
            return recover_discord_object(client, dct)
        return dct
    return discord_support_decoder_hook

class DiscordSupportJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SUPPORTED_DISCORD_TYPES):
            return cache_discord_object(obj)
        else:
            return super().default(obj)

async def await_all(cache):
    for sub in cache:
        stack = [sub]
        while stack:
            current = stack.pop()
            it = current.items() if isinstance(current, dict) else enumerate(current)
            for key, value in it:
                if asyncio.iscoroutine(value):
                    try:
                        current[key] = await value 
                    except discord.errors.NotFound:
                        print(f"Couldn't await '{value}' (error 404), using temporary None")
                        current[key] = None
                elif isinstance(value, (dict, list)):
                    stack.append(value)
