import asyncio
import collections
import traceback

import discord

import credentials


ENGLISH_NUMBERS = [
    "zero", "one", "two", "three", "four", 
    "five", "six", "seven", "eight", "nine"
]
ENGLISH_NUMBERS_TO_INT = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9
}
EMOJI_NUMBERS_TO_INT = {
    "0⃣": 0, "1⃣": 1, "2⃣": 2, "3⃣": 3, "4⃣": 4, 
    "5⃣": 5, "6⃣": 6, "7⃣": 7, "8⃣": 8, "9⃣": 9
}

EMOJI_NUMBERS = [f":{x}:" for x in ENGLISH_NUMBERS]

def create_poll_template_text(options, poll_index):
    if not (2 <= len(options) <= len(EMOJI_NUMBERS)):
        raise ValueError("Invalid option count")
    template = f"A new poll (ID {str(poll_index).zfill(3)}) is approaching!\n=====\n"
    for i in range(len(options)):
        template += f"{EMOJI_NUMBERS[i+1]}: {options[i]}\n"
    return template.strip()

class PollModel:
    def __init__(self, poll_index=None, creator_message=None, 
                       poll_message=None, options=[]):
        self.poll_index = poll_index
        self.creator_message = creator_message
        self.poll_message = poll_message
        self.options = options
        self.votes = [[] for _ in range(len(self.options))]
        self.active = True
        self.dead = False
    def deactivate(self):
        self.active = False
    def kill(self):
        self.active = False
        self.dead = True
        self.poll_index = self.creator_message = self.poll_message = None
        self.options, self.votes = [], []
    def get_emoji_as_index(self, reaction):
        opt = EMOJI_NUMBERS_TO_INT[reaction.emoji]-1
        if opt not in range(len(self.options)):
            raise IndexError("Option index out of bounds.")
        else:
            return opt
    def add_vote(self, reaction, user):
        try:
            self.votes[self.get_emoji_as_index(reaction)].append(user)
        except (KeyError, IndexError) as e:
            return False
        else:
            return True
    def erase_vote(self, reaction, user):
        try:
            self.votes[self.get_emoji_as_index(reaction)].remove(user)
        except (KeyError, IndexError, ValueError):
            return False
        else:
            return True

class HelixClient(discord.Client):
    PREFIX = "&"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.polls = []
        self.polls_by_msgid = {}

    async def on_ready(self):
        print("Ready!")

    async def on_message(self, message):
        cont = message.content
        if len(cont) > 64 or len(cont.split("\n"))>1: 
            cont = cont.split("\n")[0][:64] + "..."
        print(f"Got message: {message} ({cont})")
        if message.content == f'{self.PREFIX}leave':
            await self.logout()
        elif message.content.startswith(f'{self.PREFIX}addpoll'):
            await self.add_poll(message)
        elif message.content.startswith(f'{self.PREFIX}stoppoll'):
            await self.del_poll(message)
        elif message.content.startswith(f'{self.PREFIX}delpoll'):
            await self.kill_poll(message)
        elif message.content.startswith(f'{self.PREFIX}votes'):
            await self.list_votes(message)
        elif message.content == "Oy vey.":
            await self.oy_vey(message)

    async def add_poll(self, message):
        args = message.content.split()[1:]
        try:
            for i in range(len(self.polls)):
                if self.polls[i].dead:
                    poll_index = i
                    break
            else:
                poll_index = len(self.polls)
            template = create_poll_template_text(args, poll_index+1)
        except ValueError:
            await self.send_message(message.channel, "Sorry, I couldn't create the poll :frowning:")
            return False
        else:
            poll_message = await self.send_message(message.channel, template)
            poll = PollModel(poll_index, message, poll_message, args)
            if poll_index < len(self.polls):
                self.polls[poll_index] = poll
            else:
                self.polls.append(poll)
            self.polls_by_msgid[poll.poll_message.id] = poll
            return True

    async def get_poll_index(self, message, args):
        if len(args) > 1:    
            await self.send_message(message.channel, "You gave me too many arguments. :question:")
            return None
        try:
            poll_id = int(args[0].lstrip('0'))-1
            if poll_id not in range(len(self.polls)):
                raise IndexError("Out of bounds.")
        except (ValueError, IndexError):
            await self.send_message(message.channel, "That's not a valid ID :angry:.")
            return None
        else:
            return poll_id

    async def del_poll(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            if not poll.active:
                await self.send_message(message.channel, "I have already deleted that poll.")
                return False
            if poll.creator_message.author != message.author:
                await self.send_message(message.channel, "That's not your poll :exclamation:")
                return False
            await self.edit_message(poll.poll_message, poll.poll_message.content + "\n[This poll has ended.]")
            poll.deactivate()
            await self.send_message(message.channel, "I deactivated that poll. :bulb:")
            return True

    async def kill_poll(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            if poll.dead:
                await self.send_message(message.channel, "I have already killed that poll.")
                return False
            if poll.creator_message.author != message.author:
                await self.send_message(message.channel, "That's not your poll :exclamation:")
                return False
            await self.edit_message(poll.poll_message, poll.poll_message.content + "\n[This poll's results were deleted and you can no longer vote officially in it.]")
            del self.polls_by_msgid[poll.poll_message.id]
            poll.kill()
            await self.send_message(message.channel, "I took care of that poll. :bread:")
            return True

    async def list_votes(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            text = ""
            for option, voters in zip(poll.options, poll.votes):
                print(option, voters)
                text += option + ": ";
                text += ", ".join(str(v) for v in voters)
                text += "\n"
            text = text.strip()
            await self.send_message(message.channel, "Here are the results for that poll:\n" + text)


    async def on_reaction_add(self, reaction, user):
        print(f"Got reaction {reaction} by {user}")
        if (reaction.message.id not in self.polls_by_msgid):
            return
        poll = self.polls_by_msgid[reaction.message.id]
        if not poll.active:
            return
        success = poll.add_vote(reaction, user)

    async def on_reaction_remove(self, reaction, user):
        print(f"Removing reaction {reaction} by {user}")
        if (reaction.message.id not in self.polls_by_msgid) or \
           (not self.polls_by_msgid[reaction.message.id].active):
            print("Didn't do anything about it, though.")
            return
        success = self.polls_by_msgid[reaction.message.id].erase_vote(reaction, user)

    async def oy_vey(self, message):
        await asyncio.sleep(0.5)
        await self.send_message(message.channel, "Oy vey. :open_mouth:")

if __name__ == '__main__':
    client = HelixClient()
    client.run(credentials.TOKEN)
