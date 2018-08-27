import asyncio
import json

import discord

import caching
import pollmaker
import credentials

def is_admin(member):
    return member.server_permissions.administrator

class HelixClient(discord.Client):
    PREFIX = "&"
    
    def __init__(self, *args, poll_cache_file="caches/polls.json", **kwargs):
        super().__init__(*args, **kwargs)
        self.polls = []
        self.polls_by_msgid = {}
        self.poll_cache_file = poll_cache_file

    async def load_cached_polls(self):
        if self.poll_cache_file is None:
            return
        print(f"Looking for poll cache in {self.poll_cache_file}")
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
            for sub in cache:
                stack = [sub]
                while stack:
                    current = stack.pop()
                    it = current.items() if isinstance(current, dict) else enumerate(current)
                    for key, value in it:
                        if asyncio.iscoroutine(value):
                            current[key] = await value 
                        elif isinstance(value, (dict, list)):
                            stack.append(value)
        except json.decoder.JSONDecodeError:
            print("Failed cache load, aborting. Please clear the cache.")
            raise
        for sub in cache:
            self.polls.append(pollmaker.PollModel.load_from_cache(sub))
            self.messages.append(self.polls[-1].poll_message)
        print("Loaded successfully!")

    async def write_poll_cache(self):
        print("Updating poll cache!")
        dlist = [poll.create_cache() for poll in self.polls]
        with open(self.poll_cache_file, "w", encoding="utf-8") as file:
            s = json.dumps(
                dlist, cls=caching.DiscordSupportJSONEncoder,
                sort_keys=True, indent=4
            )
            file.write(s)
        return s

    async def finalize_and_logout(self, do_cache=True):
        if self.poll_cache_file is not None and do_cache:
            await self.write_poll_cache()
        await self.logout()

    async def on_ready(self):
        print("Ready!")
        try:
            await self.load_cached_polls()
            self.polls_by_msgid = {
                poll.poll_message.id: poll for poll in self.polls
            }
        except Exception as e:
            await self.finalize_and_logout(False)
            raise

    async def on_message(self, message):
        cont = message.content
        if len(cont) > 64 or len(cont.split("\n"))>1: 
            cont = cont.split("\n")[0][:64] + "..."
        print(f"Got message: {message} ({cont})")
        polls_changed = False
        if message.content == f'{self.PREFIX}leave':
            await self.finalize_and_logout()
        elif message.content.startswith(f'{self.PREFIX}addpoll'):
            polls_changed = await self.add_poll(message)
        elif message.content.startswith(f'{self.PREFIX}stoppoll'):
            polls_changed = await self.del_poll(message)
        elif message.content.startswith(f'{self.PREFIX}delpoll'):
            polls_changed = await self.kill_poll(message)
        elif message.content.startswith(f'{self.PREFIX}votes'):
            await self.list_votes(message)
        elif message.content == "Oy vey.":
            await self.oy_vey(message)
        if polls_changed:
            await self.write_poll_cache()

    async def add_poll(self, message):
        try:
            left = message.content.find('(')
            right = message.content.rfind(')')
            string = message.content[left:right] + ",)"
            args = ast.literal_eval(string)
            for i in range(len(self.polls)):
                if self.polls[i].dead:
                    poll_index = i
                    break
            else:
                poll_index = len(self.polls)
            template = pollmaker.create_poll_template_text(args, poll_index+1)
        except (SyntaxError, ValueError):
            await self.send_message(message.channel, "Sorry, I couldn't create the poll :frowning:")
            return False
        else:
            poll_message = await self.send_message(message.channel, template)
            poll = pollmaker.PollModel(poll_index, message, poll_message, args, message.server.me)
            if poll_index < len(self.polls):
                self.polls[poll_index] = poll
            else:
                self.polls.append(poll)
            self.polls_by_msgid[poll.poll_message.id] = poll
            for i in range(1, len(poll.options)+1):
                await self.add_reaction(poll.poll_message, pollmaker.UNICODE_EMOJI_NUMBERS[i])
            return True

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

    async def del_poll(self, message):
        args = message.content.split()[1:]
        poll_id = await self.get_poll_index(message, args)
        if poll_id is not None:
            poll = self.polls[poll_id]
            if not poll.active:
                await self.send_message(message.channel, "I have already deleted that poll.")
                return False
            if poll.creator_message.author != message.author and not is_admin(message.author):
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
            if poll.creator_message.author != message.author and not is_admin(message.author):
                await self.send_message(message.channel, "That's not your poll :exclamation:")
                return False
            await self.edit_message(poll.poll_message, poll.poll_message.content + "\n[This poll's results were deleted and you can no longer vote officially in it.]")
            del self.polls_by_msgid[poll.poll_message.id]
            poll.kill()
            await self.send_message(message.channel, "I took care of that poll. :bread:")
            while self.polls and self.polls[-1].dead:
                self.polls.pop()
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

    async def on_reaction_add(self, reaction, user):
        print(f"Got reaction {reaction} by {user}")
        if (reaction.message.id not in self.polls_by_msgid):
            return
        poll = self.polls_by_msgid[reaction.message.id]
        if not poll.active:
            return
        success = poll.add_vote(reaction, user)
        if success:
            await self.write_poll_cache()

    async def on_reaction_remove(self, reaction, user):
        print(f"Removing reaction {reaction} by {user}")
        if (reaction.message.id not in self.polls_by_msgid):
            return
        poll = self.polls_by_msgid[reaction.message.id]
        if not poll.active:
            return
        success = poll.erase_vote(reaction, user)
        if success:
            await self.write_poll_cache()

    async def oy_vey(self, message):
        await asyncio.sleep(0.5)
        await self.send_message(message.channel, "Oy vey. :open_mouth:")


if __name__ == '__main__':
    client = HelixClient()
    client.run(credentials.TOKEN)
