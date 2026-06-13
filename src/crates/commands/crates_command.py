from typing import Any

from endstone.command import Command, CommandSender

from crates.managers import CrateManager


class CratesCommand:
    def __init__(self, manager: CrateManager):
        self.manager = manager

    def handle(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        name = command.name.lower()
        if name in ["crates", "crate"]:
            return self.handle_crates(sender, args)
        if name == "keys":
            return self.handle_keys(sender)
        if name in ["crateadmin", "cratesadmin"]:
            return self.handle_admin(sender, args)
        return False

    def handle_crates(self, sender: CommandSender, args: list[str]) -> bool:
        if not args or args[0].lower() == "help":
            self.manager.send_player_help(sender)
            return True

        subcommand = args[0].lower()
        if subcommand == "list":
            self.manager.send_crate_list(sender)
            return True

        if subcommand in ["preview", "rewards"]:
            if len(args) < 2:
                self.manager.send(sender, "error.admin_usage", usage="/crates preview <crate>")
                return True
            if not self.manager.is_player(sender):
                self.manager.send(sender, "error.players_only")
                return True
            self.manager.preview_crate(sender, args[1])
            return True

        if subcommand == "open":
            if len(args) < 2:
                self.manager.send(sender, "error.admin_usage", usage="/crates open <crate>")
                return True
            if not self.manager.is_player(sender):
                self.manager.send(sender, "error.players_only")
                return True
            self.manager.open_crate(sender, args[1])
            return True

        if subcommand == "keys":
            return self.handle_keys(sender)

        self.manager.send(sender, "error.unknown_command")
        return True

    def handle_keys(self, sender: CommandSender) -> bool:
        if not self.manager.is_player(sender):
            self.manager.send(sender, "error.players_only")
            return True

        self.manager.send_keys(sender)
        return True

    def handle_admin(self, sender: CommandSender, args: list[str]) -> bool:
        if not sender.has_permission("crates.admin"):
            self.manager.send(sender, "error.no_permission")
            return True

        if not args or args[0].lower() == "help":
            self.manager.send_admin_help(sender)
            return True

        subcommand = args[0].lower()

        if subcommand == "give":
            if len(args) < 3:
                self.manager.send(sender, "error.admin_usage", usage="/crateadmin give <player> <crate> [amount]")
                return True
            amount = self.parse_amount(sender, args[3] if len(args) >= 4 else "1")
            if amount is None:
                return True
            self.manager.give_key(sender, args[1], args[2], amount)
            return True

        if subcommand == "giveall":
            if len(args) < 2:
                self.manager.send(sender, "error.admin_usage", usage="/crateadmin giveall <crate> [amount]")
                return True
            amount = self.parse_amount(sender, args[2] if len(args) >= 3 else "1")
            if amount is None:
                return True
            self.manager.give_all(sender, args[1], amount)
            return True

        if subcommand == "set":
            if len(args) < 2:
                self.manager.send(sender, "error.admin_usage", usage="/crateadmin set <crate>")
                return True
            if not self.manager.is_player(sender):
                self.manager.send(sender, "error.players_only")
                return True
            self.manager.start_link_mode(sender, args[1])
            return True

        if subcommand in ["remove", "unset", "delete"]:
            if not self.manager.is_player(sender):
                self.manager.send(sender, "error.players_only")
                return True
            self.manager.start_remove_mode(sender)
            return True

        if subcommand == "cancel":
            self.manager.cancel_setup_mode(sender)
            return True

        if subcommand == "reload":
            self.manager.reload_all()
            self.manager.send(sender, "admin.reload")
            return True

        if subcommand in ["list", "crates"]:
            self.manager.send_crate_list(sender)
            return True

        if subcommand == "locations":
            self.manager.send_locations(sender)
            return True

        if subcommand == "info":
            if len(args) < 2:
                self.manager.send(sender, "error.admin_usage", usage="/crateadmin info <crate>")
                return True
            self.manager.send_crate_info(sender, args[1])
            return True

        self.manager.send(sender, "error.unknown_command")
        return True

    def parse_amount(self, sender: Any, value: str) -> int | None:
        try:
            amount = int(value)
        except Exception:
            self.manager.send(sender, "error.invalid_amount")
            return None

        if amount <= 0:
            self.manager.send(sender, "error.invalid_amount")
            return None

        return amount
