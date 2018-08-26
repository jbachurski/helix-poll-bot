import discord

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
UNICODE_EMOJI_NUMBERS = [
    "0⃣", "1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣"
]

def create_poll_template_text(options, poll_index):
    if not (2 <= len(options) <= len(EMOJI_NUMBERS)):
        raise ValueError("Invalid option count")
    template = f"A new poll (ID {str(poll_index).zfill(3)}) is approaching!\n=====\n"
    for i in range(len(options)):
        template += f"{EMOJI_NUMBERS[i+1]}: {options[i]}\n"
    return template.strip()

class PollModel:
    def __init__(self, poll_index=None, creator_message=None, 
                       poll_message=None, options=[], owner=None):
        self.poll_index = poll_index
        self.creator_message = creator_message
        self.poll_message = poll_message
        self.options = options
        self.owner = owner
        self.votes = [[] for _ in range(len(self.options))]
        self.active = True
        self.dead = False

    def create_cache(self):
        return {
            "poll_index": self.poll_index, 
            "creator_message": self.creator_message,
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
        obj.creator_message = cache["creator_message"]
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
        self.poll_index = self.creator_message = self.poll_message = None
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
        except (KeyError, IndexError) as e:
            return False
        else:
            return True

    def erase_vote(self, reaction, user):
        if self.owner == user: return False
        try:
            self.votes[self.get_emoji_as_index(reaction)].remove(user)
        except (KeyError, IndexError, ValueError):
            return False
        else:
            return True
