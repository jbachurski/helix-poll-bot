import asyncio
import discord
import credentials
import uuid

ENGLISH_NUMBERS = [
    "zero", "one", "two", "three", "four", 
    "five", "six", "seven", "eight", "nine"
]
EMOJI_NUMBERS = [f":{x}:" for x in ENGLISH_NUMBERS]

def create_poll_template(options, poll_id):
    if not (2 <= len(options) <= len(EMOJI_NUMBERS)):
        raise ValueError("Invalid option count")
    template = "A new poll is approaching!\n=====\n"
    for i in range(len(options)):
        template += f"{EMOJI_NUMBERS[i+1]}: {options[i]}\n"
    template += f"This poll's ID is {str(poll_id).zfill(3)}"
    return template.strip()

class HelixClient(discord.Client):
    PREFIX = "&"

    _POLL_DELETED = object()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_polls = []
    async def on_ready(self):
        print("Ready!")
    async def on_message(self, message):
        print("Got message:", message)
        if message.content == f'{self.PREFIX}leave':
            await self.logout()
        elif message.content.startswith(f'{self.PREFIX}addpoll'):
            await self.addpoll(message)
        elif message.content.startswith(f'{self.PREFIX}delpoll'):
            await self.delpoll(message)
        elif message.content == "Oy vey.":
            await self.oy_vey(message)
    async def addpoll(self, message):
        args = message.content.split()[1:]
        try:
            for i in range(len(self.active_polls)):
                if self.active_polls[i][1]  == self._POLL_DELETED:
                    poll_id = i+1
                    break
            else:
                poll_id = len(self.active_polls)+1
            template = create_poll_template(args, poll_id)
        except ValueError:
            await self.send_message(message.channel, "Sorry, I couldn't create the poll :frowning:")
            return False
        else:
            await self.send_message(message.channel, template)
            if poll_id <= len(self.active_polls):
                self.active_polls[poll_id-1] = (args, message.author)
            else:
                self.active_polls.append((args, message.author))
            return True

    async def delpoll(self, message):
        args = message.content.split()[1:]
        if len(args) > 1:    
            await self.send_message(message.channel, "You gave me too many arguments. :question:")
            return False
        try:
            poll_id = int(args[0].lstrip('0'))-1
            if poll_id not in range(len(self.active_polls)):
                raise IndexError("Out of bounds.")
        except (ValueError, IndexError):
            await self.send_message(message.channel, "That's not a valid ID :angry:.")
            return False
        else:
            poll = self.active_polls[poll_id]
            if poll[1] == self._POLL_DELETED:
                await self.send_message(message.channel, "I have already deleted that poll.")
                return False
            if poll[1] != message.author:
                await self.send_message(message.channel, "That's not your poll :exclamation:")
                return False
            self.active_polls[poll_id] = ([], self._POLL_DELETED)
            await self.send_message(message.channel, "I took care of that poll. :bread:")
            return True

    async def oy_vey(self, message):
        await asyncio.sleep(0.5)
        await self.send_message(message.channel, "Oy vey. :open_mouth:")



if __name__ == '__main__':
    client = HelixClient()
    client.run(credentials.TOKEN)
