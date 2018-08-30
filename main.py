import os

import discord

import commands
import caching
import credentials
from utils import shortened
import modules.defaults
import modules.pollmaker

DEVELOPMENT_MODE = False
if DEVELOPMENT_MODE:
    credentials.TOKEN = credentials.DEV_TOKEN 

DEFAULT_POLL_CACHE_FILENAME = os.path.join("caches", "polls.json")

class HelixClient(discord.Client):
    PREFIX = "&&" if DEVELOPMENT_MODE else "&"

    def __init__(self, *args, poll_cache_file=DEFAULT_POLL_CACHE_FILENAME, **kwargs):
        super().__init__(*args, **kwargs)
        self.polls = [] 
        self.polls_by_msgid = {}
        self.poll_cache_file = poll_cache_file
        self.listeners = {
            "on_ready": {}, "finalize": {},
            "before_on_message": {}, "after_on_message": {},
            "on_reaction_add": {}, "on_reaction_remove": {},
            "on_message_delete": {}
        }
        self.command_handler = commands.CommandHandler(prefix=self.PREFIX)
        modules.defaults.inject_module(self)
        modules.pollmaker.inject_module(self)
        self.ready = False

    async def finalize_and_logout(self):
        for func in self.listeners["finalize"].values():
            await func()
        await self.logout()

    async def on_ready(self):
        print("Ready!")
        try:
            for func in self.listeners["on_ready"].values():
                await func()
        except Exception as e:
            await self.finalize_and_logout(False)
            raise
        else:
            self.ready = True

    async def on_message(self, message):
        if not self.ready: return
        print(f"Got message: {message} ({shortened(message.content)})")
        for func in self.listeners["before_on_message"].values():
            await func(message)
        await self.command_handler.handle_command_call(message.content, message)
        for func in self.listeners["after_on_message"].values():
            await func(message)

    async def on_message_delete(self, message):
        if not self.ready: return
        for func in self.listeners["on_message_delete"].values():
            await func(message)

    async def on_reaction_add(self, reaction, user):
        if not self.ready: return
        print(f"Got reaction {reaction} by {user}")
        for func in self.listeners["on_reaction_add"].values():
            await func(reaction, user)

    async def on_reaction_remove(self, reaction, user):
        if not self.ready: return
        print(f"Removing reaction {reaction} by {user}")
        for func in self.listeners["on_reaction_remove"].values():
            await func(reaction, user)

if __name__ == '__main__':
    client = HelixClient()
    client.run(credentials.TOKEN)
