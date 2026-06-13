from endstone.command import Command, CommandSender
from endstone.plugin import Plugin

from crates.commands import CratesCommand
from crates.listeners import CratesListener
from crates.managers import CrateManager


class CratesPlugin(Plugin):
    api_version = "0.11"

    commands = {
        "crates": {
            "description": "Open and preview crates",
            "usages": ["/crates [args: message]"],
            "aliases": ["crate"],
            "permissions": ["crates.command.crates"],
        },
        "keys": {
            "description": "View your crate keys",
            "usages": ["/keys"],
            "permissions": ["crates.command.keys"],
        },
        "crateadmin": {
            "description": "Manage crate keys and physical crates",
            "usages": ["/crateadmin [args: message]"],
            "aliases": ["cratesadmin"],
            "permissions": ["crates.admin"],
        },
    }

    permissions = {
        "crates.command.crates": {
            "description": "Allows players to use /crates.",
            "default": True,
        },
        "crates.command.keys": {
            "description": "Allows players to use /keys.",
            "default": True,
        },
        "crates.admin": {
            "description": "Allows administrators to manage crates.",
            "default": "op",
            "children": {
                "crates.command.crates": True,
                "crates.command.keys": True,
            },
        },
    }

    def on_enable(self):
        self.manager = CrateManager(self)
        self.command_handler = CratesCommand(self.manager)
        self.listener = CratesListener(self.manager)
        self.register_events(self.listener)
        self.logger.info(f"Crates enabled with {len(self.manager.config.get('crates', {}))} crates.")

    def on_disable(self):
        if hasattr(self, "manager"):
            self.manager.save_locations()
            self.manager.save_stats()
        self.logger.info("Crates disabled.")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        return self.command_handler.handle(sender, command, self.normalize_args(args))

    def normalize_args(self, args: list[str]) -> list[str]:
        if len(args) == 1 and isinstance(args[0], str):
            return args[0].split()

        return args
