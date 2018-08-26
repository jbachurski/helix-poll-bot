import json

import discord

import pollmaker

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
