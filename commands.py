import ast

class CommandHandler:
    def __init__(self, prefix):
        self.prefix = prefix
        self.commands = {}
        self.groups = {}

    def name_satisfies_no_prefixes(name):
        for pre in self.commands:
            if pre.startswith(name) or name.startswith(pre):
                return False
        else:
            return True

    def add_command(self, name, func):
        assert name_satisfies_no_prefixes(name), \
               f"{name} doesn't satisfy no-prefixes rule"
        self.commands[name] = func

    def remove_command(self, name):
        del self.commands[name]

    def add_command_group(self, group, commands):
        assert all(name_satisfies_no_prefixes(name) 
                   for name, func in commands), \
               f"Group {group} doesn't satisfy no-prefixes rule"
        self.groups[group] = tuple(c[0] for c in commands)
        for name, func in commands:
            self.add_command(name, func)

    def remove_command_group(self, group):
        for name in self.groups[group]:
            self.remove_command(name)
        del self.groups[group]

    @staticmethod
    def command_arg_parse(instr):
        left = instr.find('(')
        right = instr.rfind(')')
        # The comma at the end raises a SyntaxError for empty tuples,
        # but it allows 1-element tuples: `(spam,)` 
        # and is ignored for larger tuples: `(foo, bar,)`.
        if right - left > 1:
            back = ",)"
        elif ")" in instr:
            back = ")"
        else:
            back = ""
        string = instr[left:right] + back
        args = ast.literal_eval(string)
        if args and isinstance(args[-1], dict):
            kwargs = args.pop()
        else:
            kwargs = {}
        return args, kwargs

    def check_for_command_call(string, **kwargs):
        if not string: return
        body = string.split()[0]
        for name, func in self.commands.values():
            if body.startswith(self.prefix + name):
                func(**kwargs)
