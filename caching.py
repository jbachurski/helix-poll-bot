import json

import discord

import pollmaker

SUPPORTED_DISCORD_TYPES = (
    discord.Channel, discord.Message, discord.Member, discord.User
)
SUPPORTED_DISCORD_TYPES_STR = (
    "Channel", "Message", "Member", "User"
)

def cache_discord_object(obj):
    if isinstance(obj, discord.Channel):
        return {
            "type": "Channel",
            "id": obj.id
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
            "id": obj.id
        }
    elif isinstance(obj, discord.User):
        return {
            "type": "User",
            "id": obj.id
        }

def recover_discord_object(client, cache):
    if cache["type"] == "Channel":
        return client.get_channel(cache["id"])
    elif cache["type"] == "Message":
        return client.get_message(recover_discord_object(client, cache["channel"]), cache["id"])
    elif cache["type"] == "Member":
        return client.get_member(cache["id"])
    elif cache["type"] == "User":
        return client.get_user_info(cache["id"])

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
