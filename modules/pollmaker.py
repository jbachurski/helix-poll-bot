import json
import types
import os
import caching
import asyncio

import discord

from utils import is_admin

ENGLISH_NUMBERS = [
    "zero", "one", "two", "three", "four", 
    "five", "six", "seven", "eight", "nine"
]
ENGLISH_NUMBERS_TO_INT = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9
}
EMOJI_NUMBERS = [f":{x}:" for x in ENGLISH_NUMBERS]
UNICODE_EMOJI_NUMBERS = [
    "0⃣", "1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣",
    "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", 
    "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷",
    "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"
]
EMOJI_NUMBERS_TO_INT = {
    c: i for c, i in enumerate(UNICODE_EMOJI_NUMBERS)
}

def create_poll_template_text(options, poll_index, title=None):
    if not (2 <= len(options) <= len(UNICODE_EMOJI_NUMBERS)):
        raise ValueError("Invalid option count")
    template = f"A new poll (ID {str(poll_index).zfill(3)}) is approaching!\n=====\n"
    if title is not None:
        template += title + "\n"
    for i in range(len(options)):
        template += f"{UNICODE_EMOJI_NUMBERS[i]}: {options[i]}\n"
    return template.strip()

class PollModel:
    def __init__(self, poll_index=None, author=None, 
                       poll_message=None, options=[], owner=None):
        self.poll_index = poll_index
        self.author = author
        self.poll_message = poll_message
        self.options = options
        self.owner = owner
        self.votes = [[] for _ in range(len(self.options))]
        self.active = True
        self.dead = False

    def create_cache(self):
        return {
            "poll_index": self.poll_index, 
            "author": self.author,
            "poll_message": self.poll_message,
            "options": self.options,
            "owner": self.owner,
            "votes": self.votes,
            "active": self.active,
            "dead": self.dead
        }

    @classmethod
    def load_from_cache(cls, cache):
        obj = cls()
        obj.poll_index = cache["poll_index"]
        obj.author = cache["author"]
        obj.poll_message = cache["poll_message"]
        obj.options = cache["options"]
        obj.owner = cache["owner"]
        obj.votes = cache["votes"]
        obj.active = cache["active"]
        obj.dead = cache["dead"]
        return obj

    def deactivate(self):
        self.active = False

    def kill(self):
        self.active = False
        self.dead = True
        self.poll_index = self.author = self.poll_message = None
        self.options, self.votes = [], []

    def get_emoji_as_index(self, reaction):
        opt = EMOJI_NUMBERS_TO_INT[reaction.emoji]-1
        if opt not in range(len(self.options)):
            raise IndexError("Option index out of bounds.")
        else:
            return opt

    def add_vote(self, reaction, user):
        if self.owner == user: return False
        try:
            self.votes[self.get_emoji_as_index(reaction)].append(user)
        except (KeyError, IndexError, AssertionError):
            return False
        else:
            return True

    def erase_vote(self, reaction, user):
        if self.owner == user: return False
        try:
            self.votes[self.get_emoji_as_index(reaction)].remove(user)
        except (KeyError, IndexError, ValueError, AssertionError):
            return False
        else:
            return True

async def load_cached_polls(self):
    if self.poll_cache_file is None:
        return
    path = os.path.join(os.getcwd(), self.poll_cache_file)
    print(f"Looking for poll cache in {path}")
    try:
        with open(self.poll_cache_file, "r", encoding="utf-8") as file:
            raw_cache = file.read()
    except FileNotFoundError:
        print("No cache was found.")
        return True
    print("Loading polls from cache.")
    hook = caching.discord_support_decoder_hook_factory(self)
    try:
        cache = json.loads(raw_cache, object_hook=hook)
        await caching.await_all(cache)
    except json.decoder.JSONDecodeError:
        print("Failed cache load, aborting. Please clear the cache.")
        raise
    for sub in cache:
        obj = PollModel.load_from_cache(sub)
        if obj.poll_message is None:
            print(f"Poll message for poll ID {obj.poll_index} is gone, deleting")
            continue
        self.polls.append(obj)
        self.messages.append(self.polls[-1].poll_message)
    self.polls_by_msgid = {
        poll.poll_message.id: poll for poll in self.polls if poll.poll_message is not None
    }
    print("Loaded successfully!")

async def write_poll_cache(self):
    if self.poll_cache_file is None or not self.ready:
        return
    print("Updating poll cache!")
    dlist = [poll.create_cache() for poll in self.polls]
    with open(self.poll_cache_file, "w", encoding="utf-8") as file:
        s = json.dumps(
            dlist, cls=caching.DiscordSupportJSONEncoder,
            sort_keys=True, indent=4
        )
        file.write(s)
    return s

async def assert_updated_poll_cache(self, message):
    if self.polls_changed:
        await self.write_poll_cache()
        self.polls_changed = False

async def get_poll_index(self, message, args):
    if len(args) > 1:    
        await self.send_message(message.channel, "You gave me too many arguments. :question:")
        return None
    try:
        poll_id = int(args[0].lstrip('0'))-1
        if poll_id not in range(len(self.polls)) or self.polls[poll_id].dead:
            raise IndexError("No living poll on such index.")
    except (ValueError, IndexError):
        await self.send_message(message.channel, "That's not a valid ID :angry:.")
        return None
    else:
        return poll_id

async def handle_reaction_addition(self, reaction, user):
    if (reaction.message.id not in self.polls_by_msgid):
        return
    poll = self.polls_by_msgid[reaction.message.id]
    if not poll.active:
        return
    success = poll.add_vote(reaction, user)
    if success:
        await self.write_poll_cache()

async def handle_reaction_removal(self, reaction, user):
    if (reaction.message.id not in self.polls_by_msgid):
        return
    poll = self.polls_by_msgid[reaction.message.id]
    if not poll.active:
        return
    success = poll.erase_vote(reaction, user)
    if success:
        await self.write_poll_cache()

async def handle_poll_message_removal(self, message):
    if message.id in self.polls_by_msgid:
        self.polls_by_msgid[message.id].kill()
        self.polls_changed = True
    await self.assert_updated_poll_cache()


class PollmakerCommands:
    async def add_poll(self, message):
        try:
            args, kwargs = self.command_handler.command_find_args(message.content)
            if any(not isinstance(o, str) for o in args):
                raise ValueError("(At least) one of the arguments was not a string")
            for i in range(len(self.polls)):
                if self.polls[i].dead:
                    poll_index = i
                    break
            else:
                poll_index = len(self.polls)
            template = create_poll_template_text(args, poll_index+1, kwargs.get("title", None))
        except (SyntaxError, ValueError):
            await self.send_message(message.channel, "Sorry, I couldn't create the poll :frowning:")
            return False
        else:
            poll_message = await self.send_message(message.channel, template)
            poll = PollModel(poll_index, message.author, poll_message, args, message.server.me)
            if poll_index < len(self.polls):
                self.polls[poll_index] = poll
            else:
                self.polls.append(poll)
            self.polls_by_msgid[poll.poll_message.id] = poll
            for i in range(1, len(poll.options)+1):
                await self.add_reaction(poll.poll_message, UNICODE_EMOJI_NUMBERS[i])
            self.polls_changed = True
            return True

    async def stop_poll(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            if not poll.active:
                await self.send_message(message.channel, "I have already deactivated that poll.")
                return False
            if not (poll.author == message.author or is_admin(message.author)):
                await self.send_message(message.channel, "That's not your poll :exclamation:")
                return False
            await self.edit_message(poll.poll_message, poll.poll_message.content + "\n[This poll has ended.]")
            poll.deactivate()
            await self.send_message(message.channel, "I deactivated that poll. :bulb:")
            self.polls_changed = True
            return True

    async def del_poll(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            if poll.dead:
                await self.send_message(message.channel, "I have already deleted that poll.")
                return False
            if not (poll.author == message.author or is_admin(message.author)):
                await self.send_message(message.channel, "That's not your poll :exclamation:")
                return False
            await self.edit_message(poll.poll_message, poll.poll_message.content + "\n[This poll's results were deleted and you can no longer vote officially in it.]")
            del self.polls_by_msgid[poll.poll_message.id]
            poll.kill()
            await self.send_message(message.channel, "I took care of that poll. :bread:")
            while self.polls and self.polls[-1].dead:
                self.polls.pop()
            self.polls_changed = True
            return True

    async def list_votes(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            text = ""
            for option, voters in zip(poll.options, poll.votes):
                print(option, voters)
                text += f"{option} [{len(voters)}]: ";
                text += ", ".join(v.display_name for v in voters)
                text += "\n"
            text = text.strip()
            await self.send_message(message.channel, "Here are the results for that poll:\n" + text)

def inject_module(client):
    def bound(func): return types.MethodType(func, client)
    client.polls_changed = False
    client.write_poll_cache = bound(write_poll_cache)
    client.get_poll_index = bound(get_poll_index)
    client.assert_updated_poll_cache = bound(assert_updated_poll_cache)
    client.listeners["on_ready"]["pollmaker_load"] = bound(load_cached_polls)
    client.listeners["finalize"]["pollmaker_write"] = client.write_poll_cache
    client.listeners["after_on_message"]["pollmaker_update"] = client.assert_updated_poll_cache
    client.listeners["on_reaction_add"]["pollmaker_update"] = bound(handle_reaction_addition)
    client.listeners["on_reaction_remove"]["pollmaker_update"] = bound(handle_reaction_removal)
    client.listeners["on_message_delete"]["pollmaker_delete"] = bound(handle_poll_message_removal)
    client.command_handler.add_command_group(
        "pollmaker",
        (
            ("addpoll", bound(PollmakerCommands.add_poll)),
            ("stoppoll", bound(PollmakerCommands.stop_poll)),
            ("delpoll", bound(PollmakerCommands.del_poll)),
            ("votes", bound(PollmakerCommands.list_votes))
        )
    )

def eject_module(client):
    del client.polls_changed
    del client.write_poll_cache
    del client.get_poll_index
    del client.assert_updated_poll_cache
    del client.listeners["on_ready"]["pollmaker_load"]
    del client.listeners["finalize"]["pollmaker_write"]
    del client.listeners["after_on_message"]["pollmaker_update"]
    del client.listeners["on_reaction_add"]["pollmaker_update"]
    del client.listeners["on_reaction_remove"]["pollmaker_update"]
    del client.listeners["on_message_delete"]["pollmaker_delete"]
    client.command_handler.remove_command_group("pollmaker")
