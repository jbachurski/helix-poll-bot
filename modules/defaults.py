import types
import importlib
from . import pollmaker

async def leave(self, message):
    await self.finalize_and_logout()

async def reload_pollmaker(self, message):
    print("Reloading pollmaker...")
    importlib.reload(pollmaker)
    pollmaker.eject_module(self)
    pollmaker.inject_module(self)
    print("Done")

def inject_module(client):
    def bound(func): return types.MethodType(func, client)
    client.command_handler.add_command_group(
        "defaults",
        (
            ("leave", bound(leave)),
            ("reload_pollmaker", bound(reload_pollmaker))
        )
    )

def eject_module(client):
    client.command_handler.remove_command_group("defaults")
