import copy
import random
import time
from pathlib import Path
from typing import Any

from endstone.form import ActionForm
from endstone.inventory import ItemStack
from endstone.level import Location
from endstone.nbt import CompoundTag, StringTag

from crates.constants import COLOR, default_config
from crates.storage import JsonStorage


class CrateManager:
    def __init__(self, plugin: Any):
        self.plugin = plugin
        self.server = plugin.server
        self.logger = plugin.logger
        self.data_folder = Path(plugin.data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)

        self.config_path = self.data_folder / "config.json"
        self.locations_path = self.data_folder / "locations.json"
        self.stats_path = self.data_folder / "stats.json"
        self.storage = JsonStorage(self.logger)

        self.pending_links: dict[str, str] = {}
        self.pending_removals: set[str] = set()
        self.opening_players: set[str] = set()
        self.cooldowns: dict[str, float] = {}

        self.reload_all()

    def reload_all(self):
        self.config = self.storage.load_dict_with_defaults(self.config_path, default_config())
        self.locations_data = self.storage.load_dict_with_defaults(
            self.locations_path,
            {"schema_version": 1, "locations": []},
        )
        self.stats = self.storage.load_dict_with_defaults(
            self.stats_path,
            {"schema_version": 1, "players": {}, "total_opens": {}},
        )
        self.locations = [
            location
            for location in self.locations_data.get("locations", [])
            if isinstance(location, dict) and "crate" in location
        ]
        self.rebuild_location_index()

    def rebuild_location_index(self):
        self.locations_by_key: dict[str, dict[str, Any]] = {}
        for location in self.locations:
            key = self.location_key(
                str(location.get("dimension", "")),
                int(location.get("x", 0)),
                int(location.get("y", 0)),
                int(location.get("z", 0)),
            )
            self.locations_by_key[key] = location

    def save_locations(self):
        self.locations_data["locations"] = self.locations
        self.storage.save_dict(self.locations_path, self.locations_data)
        self.rebuild_location_index()

    def save_stats(self):
        self.storage.save_dict(self.stats_path, self.stats)

    def get_dimension_by_name(self, dimension_name: str) -> Any | None:
        try:
            for dimension in self.server.level.dimensions:
                if str(dimension.name).lower() == dimension_name.lower():
                    return dimension
        except Exception as error:
            self.logger.debug(f"Could not inspect dimensions: {error}")

        try:
            return self.server.level.get_dimension(dimension_name)
        except Exception:
            return None

    def format_text(self, text: Any, **kwargs: Any) -> str:
        value = str(text)
        try:
            value = value.format(**kwargs)
        except Exception:
            pass

        return value.replace("&", COLOR)

    def send(self, sender: Any, message_key: str, prefixed: bool = True, **kwargs: Any):
        messages = self.config.get("messages", {})
        text = messages.get(message_key, message_key)
        prefix = self.config.get("settings", {}).get("prefix", "")

        message = self.format_text(text, **kwargs)
        if prefixed:
            message = self.format_text(prefix, **kwargs) + message

        sender.send_message(message)

    def send_raw(self, sender: Any, text: str, prefixed: bool = False, **kwargs: Any):
        prefix = self.config.get("settings", {}).get("prefix", "")
        message = self.format_text(text, **kwargs)
        if prefixed:
            message = self.format_text(prefix, **kwargs) + message
        sender.send_message(message)

    def is_player(self, sender: Any) -> bool:
        return (
            hasattr(sender, "name")
            and hasattr(sender, "location")
            and hasattr(sender, "inventory")
            and hasattr(sender, "send_message")
        )

    def player_key(self, player: Any) -> str:
        try:
            return str(player.unique_id)
        except Exception:
            return str(getattr(player, "name", "unknown")).lower()

    def match_crate_id(self, crate_id: str) -> str | None:
        requested = crate_id.strip().lower()
        crates = self.config.get("crates", {})

        if requested in crates:
            return requested

        for current_id in crates:
            if str(current_id).lower() == requested:
                return str(current_id)

        return None

    def get_crate(self, crate_id: str) -> dict[str, Any] | None:
        matched = self.match_crate_id(crate_id)
        if matched is None:
            return None

        crate = self.config.get("crates", {}).get(matched)
        if isinstance(crate, dict):
            return crate

        return None

    def get_crate_name(self, crate_id: str) -> str:
        crate = self.get_crate(crate_id)
        if crate is None:
            return crate_id

        return self.format_text(crate.get("display_name", crate_id))

    def get_key_name(self, crate_id: str) -> str:
        crate = self.get_crate(crate_id)
        if crate is None:
            return crate_id

        key_config = crate.get("key", {})
        if not isinstance(key_config, dict):
            key_config = {}

        return self.format_text(key_config.get("name", f"&e{crate_id.title()} Key"))

    def get_rewards(self, crate_id: str) -> list[dict[str, Any]]:
        crate = self.get_crate(crate_id)
        if crate is None:
            return []

        rewards = crate.get("rewards", [])
        return [reward for reward in rewards if isinstance(reward, dict)]

    def reward_name(self, reward: dict[str, Any]) -> str:
        return self.format_text(
            reward.get("display_name", reward.get("name", reward.get("id", "Reward")))
        )

    def reward_weight(self, reward: dict[str, Any]) -> float:
        try:
            return max(0.0, float(reward.get("weight", 1)))
        except Exception:
            return 0.0

    def total_reward_weight(self, crate_id: str) -> float:
        return sum(self.reward_weight(reward) for reward in self.get_rewards(crate_id))

    def roll_reward(self, crate_id: str) -> dict[str, Any] | None:
        rewards = self.get_rewards(crate_id)
        total = sum(self.reward_weight(reward) for reward in rewards)
        if total <= 0:
            return None

        cursor = random.uniform(0, total)
        for reward in rewards:
            cursor -= self.reward_weight(reward)
            if cursor <= 0:
                return copy.deepcopy(reward)

        return copy.deepcopy(rewards[-1]) if rewards else None

    def find_player(self, name: str) -> Any | None:
        try:
            player = self.server.get_player(name)
            if player is not None:
                return player
        except Exception:
            pass

        requested = name.lower()
        for player in self.server.online_players:
            if str(player.name).lower() == requested:
                return player

        return None

    def normalize_item_type(self, item_type: Any) -> str:
        value = str(item_type).strip()
        if not value:
            value = "minecraft:paper"
        if ":" not in value:
            value = f"minecraft:{value}"
        return value

    def item_type_id(self, item: ItemStack | None) -> str:
        if item is None:
            return ""

        item_type = getattr(item, "type", "")
        type_id = getattr(item_type, "id", None)
        return str(type_id if type_id is not None else item_type)

    def make_item_stack(self, item_type: str, amount: int) -> ItemStack:
        normalized = self.normalize_item_type(item_type)
        try:
            return ItemStack(normalized, max(1, int(amount)))
        except Exception as error:
            self.logger.warning(f"Could not create item {normalized}: {error}. Falling back to minecraft:paper.")
            return ItemStack("minecraft:paper", max(1, int(amount)))

    def create_key_item(self, crate_id: str, amount: int = 1) -> ItemStack:
        crate = self.get_crate(crate_id) or {}
        settings = self.config.get("settings", {})
        key_config = crate.get("key", {})
        if not isinstance(key_config, dict):
            key_config = {}

        item_type = key_config.get("item", settings.get("default_key_item", "minecraft:tripwire_hook"))
        item = self.make_item_stack(str(item_type), amount)
        meta = item.item_meta
        meta.display_name = self.get_key_name(crate_id)
        lore = key_config.get("lore", [f"&7Opens {crate_id} crates.", f"&8crate: {crate_id}"])
        if isinstance(lore, list):
            meta.lore = [self.format_text(line, crate=crate_id) for line in lore]
        item.set_item_meta(meta)

        try:
            tag = item.nbt
            if tag is None:
                tag = CompoundTag()
            tag["endstone_crates_key"] = StringTag(crate_id)
            item.nbt = tag
        except Exception as error:
            self.logger.debug(f"Could not tag crate key item: {error}")

        return item

    def get_nbt_string(self, item: ItemStack, key: str) -> str | None:
        try:
            tag = item.nbt
            if tag is None or key not in tag:
                return None
            value = tag[key]
            return str(getattr(value, "value", value))
        except Exception:
            return None

    def is_key_item(self, item: ItemStack | None, crate_id: str) -> bool:
        if item is None:
            return False

        crate = self.get_crate(crate_id)
        if crate is None:
            return False

        key_config = crate.get("key", {})
        if not isinstance(key_config, dict):
            key_config = {}

        expected_type = self.normalize_item_type(
            key_config.get("item", self.config.get("settings", {}).get("default_key_item", "minecraft:tripwire_hook"))
        )
        if self.item_type_id(item) != expected_type:
            return False

        tagged_crate = self.get_nbt_string(item, "endstone_crates_key")
        if tagged_crate is not None:
            return tagged_crate.lower() == crate_id.lower()

        try:
            meta = item.item_meta
            if meta.has_display_name and meta.display_name == self.get_key_name(crate_id):
                lore = meta.lore if meta.has_lore else []
                marker = self.format_text(f"&8crate: {crate_id}")
                return marker in lore
        except Exception:
            pass

        return False

    def match_key_item(self, item: ItemStack | None) -> str | None:
        if item is None:
            return None
        for crate_id in self.config.get("crates", {}):
            if self.is_key_item(item, str(crate_id)):
                return str(crate_id)
        return None

    def protect_key_placement(self, player: Any) -> bool:
        try:
            held = player.inventory.item_in_main_hand
        except Exception:
            return False

        crate_id = self.match_key_item(held)
        if crate_id is None:
            return False

        self.send(player, "error.key_place_blocked", key=self.get_key_name(crate_id))
        return True

    def count_keys(self, player: Any, crate_id: str) -> int:
        count = 0
        for item in player.inventory.contents:
            if self.is_key_item(item, crate_id):
                count += int(getattr(item, "amount", 0))
        return count

    def take_key(self, player: Any, crate_id: str, amount: int = 1) -> bool:
        remaining = amount
        inventory = player.inventory

        for index, item in enumerate(inventory.contents):
            if not self.is_key_item(item, crate_id):
                continue

            stack_amount = int(item.amount)
            if stack_amount > remaining:
                item.amount = stack_amount - remaining
                inventory.set_item(index, item)
                return True

            remaining -= stack_amount
            inventory.clear(index)
            if remaining <= 0:
                return True

        return False

    def give_item(self, player: Any, item: ItemStack):
        leftovers = player.inventory.add_item(item)
        for leftover in leftovers.values():
            try:
                player.location.dimension.drop_item(player.location, leftover)
            except Exception as error:
                self.logger.warning(f"Could not drop leftover crate reward: {error}")

    def give_key(self, sender: Any, player_name: str, crate_id: str, amount: int):
        crate_id = self.match_crate_id(crate_id) or crate_id
        crate = self.get_crate(crate_id)
        if crate is None:
            self.send(sender, "error.crate_missing", crate=crate_id)
            return

        target = self.find_player(player_name)
        if target is None:
            self.send(sender, "error.player_missing", player=player_name)
            return

        key_item = self.create_key_item(crate_id, amount)
        self.give_item(target, key_item)
        self.send(sender, "admin.give.sender", player=target.name, amount=amount, key=self.get_key_name(crate_id))
        self.send(target, "admin.give.target", amount=amount, key=self.get_key_name(crate_id))

    def give_all(self, sender: Any, crate_id: str, amount: int):
        crate_id = self.match_crate_id(crate_id) or crate_id
        crate = self.get_crate(crate_id)
        if crate is None:
            self.send(sender, "error.crate_missing", crate=crate_id)
            return

        count = 0
        for player in self.server.online_players:
            self.give_item(player, self.create_key_item(crate_id, amount))
            self.send(player, "admin.give.target", amount=amount, key=self.get_key_name(crate_id))
            count += 1

        self.send(sender, "admin.giveall", amount=amount, key=self.get_key_name(crate_id), count=count)

    def get_dimension_name(self, dimension: Any) -> str:
        try:
            return str(dimension.name)
        except Exception:
            return "unknown"

    def snapshot_block_location(self, block: Any) -> dict[str, Any]:
        return {
            "dimension": self.get_dimension_name(block.dimension),
            "x": int(block.x),
            "y": int(block.y),
            "z": int(block.z),
        }

    def location_from_snapshot(self, snapshot: dict[str, Any] | None) -> Location | None:
        if snapshot is None:
            return None

        dimension = self.get_dimension_by_name(str(snapshot.get("dimension", "")))
        if dimension is None:
            return None

        return Location(
            dimension,
            float(snapshot.get("x", 0)) + 0.5,
            float(snapshot.get("y", 0)) + 0.5,
            float(snapshot.get("z", 0)) + 0.5,
        )

    def location_key(self, dimension_name: str, x: int, y: int, z: int) -> str:
        return f"{dimension_name.lower()}:{x}:{y}:{z}"

    def block_key(self, block: Any) -> str:
        return self.location_key(
            self.get_dimension_name(block.dimension),
            int(block.x),
            int(block.y),
            int(block.z),
        )

    def get_location_for_block(self, block: Any) -> dict[str, Any] | None:
        return self.locations_by_key.get(self.block_key(block))

    def start_link_mode(self, player: Any, crate_id: str):
        crate_id = self.match_crate_id(crate_id) or crate_id
        if self.get_crate(crate_id) is None:
            self.send(player, "error.crate_missing", crate=crate_id)
            return

        key = self.player_key(player)
        self.pending_links[key] = crate_id
        self.pending_removals.discard(key)
        self.send(player, "admin.link.start", crate=crate_id)

    def start_remove_mode(self, player: Any):
        key = self.player_key(player)
        self.pending_links.pop(key, None)
        self.pending_removals.add(key)
        self.send(player, "admin.remove.start")

    def cancel_setup_mode(self, sender: Any):
        if not self.is_player(sender):
            self.send(sender, "error.players_only")
            return

        key = self.player_key(sender)
        self.pending_links.pop(key, None)
        self.pending_removals.discard(key)
        self.send(sender, "admin.cancel")

    def handle_setup_click(self, player: Any, block: Any) -> bool:
        key = self.player_key(player)
        if key in self.pending_links:
            crate_id = self.pending_links.pop(key)
            self.link_crate_block(player, block, crate_id)
            return True

        if key in self.pending_removals:
            self.pending_removals.discard(key)
            self.remove_crate_block(player, block)
            return True

        return False

    def link_crate_block(self, player: Any, block: Any, crate_id: str):
        crate = self.get_crate(crate_id)
        if crate is None:
            self.send(player, "error.crate_missing", crate=crate_id)
            return

        existing = self.get_location_for_block(block)
        if existing is not None:
            self.locations.remove(existing)

        dimension_name = self.get_dimension_name(block.dimension)
        location = {
            "crate": crate_id,
            "dimension": dimension_name,
            "x": int(block.x),
            "y": int(block.y),
            "z": int(block.z),
        }
        self.locations.append(location)
        self.save_locations()

        if bool(self.config.get("settings", {}).get("set_block_on_link", True)):
            block_type = crate.get(
                "block_type",
                self.config.get("settings", {}).get("default_crate_block", "minecraft:chest"),
            )
            try:
                requested_type = self.normalize_item_type(block_type)
                current_type = self.normalize_item_type(getattr(block, "type", ""))
                if current_type != requested_type:
                    block.set_type(requested_type, False)
            except Exception as error:
                self.logger.warning(f"Could not set crate block type {block_type}: {error}")

        self.send(player, "admin.link.done", crate=crate_id, x=block.x, y=block.y, z=block.z)

    def remove_crate_block(self, player: Any, block: Any):
        location = self.get_location_for_block(block)
        if location is None:
            self.send(player, "admin.remove.none")
            return

        self.locations.remove(location)
        self.save_locations()
        self.send(
            player,
            "admin.remove.done",
            crate=location.get("crate", "unknown"),
            x=location.get("x", 0),
            y=location.get("y", 0),
            z=location.get("z", 0),
        )

    def open_from_block(self, player: Any, block: Any, preview: bool = False):
        location = self.get_location_for_block(block)
        if location is None:
            return

        crate_id = str(location.get("crate", ""))
        if preview:
            self.preview_crate(player, crate_id)
            return

        self.open_crate(player, crate_id, block=block)

    def open_crate(self, player: Any, crate_id: str, block: Any | None = None):
        effect_location = self.snapshot_block_location(block) if block is not None else None
        crate_id = self.match_crate_id(crate_id) or crate_id
        crate = self.get_crate(crate_id)
        if crate is None:
            self.send(player, "error.crate_missing", crate=crate_id)
            return

        rewards = self.get_rewards(crate_id)
        if not rewards:
            self.send(player, "error.reward_missing", crate=crate_id)
            return

        player_key = self.player_key(player)
        if player_key in self.opening_players:
            self.send(player, "error.already_opening")
            return

        cooldown_key = f"{player_key}:{crate_id}"
        now = time.time()
        cooldown_until = self.cooldowns.get(cooldown_key, 0)
        if cooldown_until > now:
            self.send(player, "error.cooldown", seconds=max(1, int(cooldown_until - now)))
            return

        requires_key = bool(crate.get("requires_key", True))
        bypass = bool(self.config.get("settings", {}).get("admin_bypass_keys", False)) and player.has_permission(
            "crates.admin"
        )
        if requires_key and not bypass and not self.take_key(player, crate_id):
            self.send(player, "error.no_key", key=self.get_key_name(crate_id))
            return

        reward = self.roll_reward(crate_id)
        if reward is None:
            self.send(player, "error.reward_missing", crate=crate_id)
            return

        cooldown_seconds = max(0, int(self.config.get("settings", {}).get("crate_cooldown_seconds", 1)))
        self.cooldowns[cooldown_key] = now + cooldown_seconds
        self.opening_players.add(player_key)
        self.send(player, "crate.opening", name=self.get_crate_name(crate_id))
        self.animate_open(player, crate_id, reward, effect_location)

    def animate_open(
        self,
        player: Any,
        crate_id: str,
        reward: dict[str, Any],
        effect_location: dict[str, Any] | None,
    ):
        opening = self.config.get("opening", {})
        interval = max(1, int(opening.get("spin_interval_ticks", 3)))
        steps = max(0, int(opening.get("spin_ticks", 36)) // interval)
        rewards = self.get_rewards(crate_id)
        state = {"step": 0}
        player_key = self.player_key(player)

        if steps <= 0:
            self.finish_open(player, crate_id, reward, effect_location)
            return

        def step():
            if player_key not in self.opening_players:
                return

            if state["step"] >= steps:
                self.finish_open(player, crate_id, reward, effect_location)
                return

            preview_reward = random.choice(rewards) if rewards else reward
            preview_name = self.reward_name(preview_reward)
            try:
                player.send_title("", preview_name, 0, interval + 6, 2)
            except Exception:
                player.send_popup(preview_name)

            self.play_effects(player, effect_location, win=False)
            state["step"] += 1
            self.server.scheduler.run_task(self.plugin, step, delay=interval)

        self.server.scheduler.run_task(self.plugin, step, delay=1)

    def finish_open(
        self,
        player: Any,
        crate_id: str,
        reward: dict[str, Any],
        effect_location: dict[str, Any] | None,
    ):
        player_key = self.player_key(player)
        self.opening_players.discard(player_key)

        reward_name = self.reward_name(reward)
        self.apply_reward(player, crate_id, reward)
        self.record_open(player, crate_id, reward)
        self.play_effects(player, effect_location, win=True)

        try:
            player.send_title(reward_name, "", 5, 40, 10)
        except Exception:
            pass

        self.send(player, "crate.win", reward=reward_name)

        if bool(reward.get("broadcast", False)) and bool(self.config.get("settings", {}).get("broadcast_wins", True)):
            message = self.config.get("messages", {}).get("crate.broadcast", "{player} won {reward} from {crate}.")
            self.server.broadcast_message(
                self.format_text(
                    message,
                    player=player.name,
                    reward=reward_name,
                    crate=self.get_crate_name(crate_id),
                )
            )

    def play_effects(self, player: Any, effect_location: dict[str, Any] | None, win: bool):
        opening = self.config.get("opening", {})
        location = self.location_from_snapshot(effect_location) or player.location

        try:
            sound = opening.get("win_sound" if win else "spin_sound", "")
            if sound:
                player.play_sound(location, str(sound), 1.0, 1.0)
        except Exception:
            pass

        try:
            particle = opening.get("particle", "")
            if particle:
                player.spawn_particle(str(particle), location)
        except Exception:
            pass

    def apply_reward(self, player: Any, crate_id: str, reward: dict[str, Any]):
        for item_config in self.reward_item_configs(reward):
            try:
                self.give_item(player, self.create_reward_item(item_config))
            except Exception as error:
                self.logger.error(f"Could not give crate reward item for {crate_id}: {error}")

        exp = int(reward.get("exp", 0) or 0)
        if exp > 0:
            player.give_exp(exp)

        exp_levels = int(reward.get("exp_levels", 0) or 0)
        if exp_levels > 0:
            player.give_exp_levels(exp_levels)

        for command in reward.get("commands", []) or []:
            command_line = str(command).format(
                player=player.name,
                crate=crate_id,
                reward=self.reward_name(reward),
            )
            try:
                self.server.dispatch_command(self.server.command_sender, command_line)
            except Exception as error:
                self.logger.error(f"Could not run crate reward command '{command_line}': {error}")

        for command in reward.get("player_commands", []) or []:
            command_line = str(command).format(
                player=player.name,
                crate=crate_id,
                reward=self.reward_name(reward),
            )
            try:
                player.perform_command(command_line)
            except Exception as error:
                self.logger.error(f"Could not run player reward command '{command_line}': {error}")

        for message in reward.get("messages", []) or []:
            self.send_raw(
                player,
                str(message),
                prefixed=True,
                player=player.name,
                crate=crate_id,
                reward=self.reward_name(reward),
            )

    def reward_item_configs(self, reward: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(reward.get("items"), list):
            return [item for item in reward["items"] if isinstance(item, dict)]

        item = reward.get("item")
        if isinstance(item, dict):
            return [item]

        if isinstance(item, str):
            return [{"type": item, "amount": int(reward.get("amount", 1) or 1)}]

        return []

    def create_reward_item(self, item_config: dict[str, Any]) -> ItemStack:
        item = self.make_item_stack(
            str(item_config.get("type", "minecraft:stone")),
            int(item_config.get("amount", 1) or 1),
        )

        meta = item.item_meta
        if "name" in item_config:
            meta.display_name = self.format_text(item_config["name"])
        if isinstance(item_config.get("lore"), list):
            meta.lore = [self.format_text(line) for line in item_config["lore"]]
        for enchant in item_config.get("enchants", []) or []:
            if not isinstance(enchant, dict):
                continue
            try:
                meta.add_enchant(str(enchant.get("id", "")), int(enchant.get("level", 1)), True)
            except Exception as error:
                self.logger.warning(f"Could not add enchantment {enchant}: {error}")
        item.set_item_meta(meta)
        return item

    def record_open(self, player: Any, crate_id: str, reward: dict[str, Any]):
        players = self.stats.setdefault("players", {})
        record = players.setdefault(
            self.player_key(player),
            {"name": player.name, "opens": {}, "last_reward": None},
        )
        record["name"] = player.name
        opens = record.setdefault("opens", {})
        opens[crate_id] = int(opens.get(crate_id, 0)) + 1
        record["last_reward"] = {
            "crate": crate_id,
            "reward": str(reward.get("id", self.reward_name(reward))),
            "time": int(time.time()),
        }

        total_opens = self.stats.setdefault("total_opens", {})
        total_opens[crate_id] = int(total_opens.get(crate_id, 0)) + 1
        self.save_stats()

    def preview_crate(self, player: Any, crate_id: str):
        crate_id = self.match_crate_id(crate_id) or crate_id
        crate = self.get_crate(crate_id)
        if crate is None:
            self.send(player, "error.crate_missing", crate=crate_id)
            return

        rewards = self.get_rewards(crate_id)
        if not rewards:
            self.send(player, "error.reward_missing", crate=crate_id)
            return

        total_weight = self.total_reward_weight(crate_id)
        max_rewards = int(self.config.get("settings", {}).get("preview_max_rewards", 35))
        lines = []
        for reward in rewards[:max_rewards]:
            chance = 0 if total_weight <= 0 else round((self.reward_weight(reward) / total_weight) * 100, 2)
            lines.append(
                self.format_text(
                    self.config.get("messages", {}).get("crate.preview.reward", "{chance}% - {name}"),
                    chance=chance,
                    name=self.reward_name(reward),
                )
            )

        if len(rewards) > max_rewards:
            lines.append(self.format_text("&7...and {count} more", count=len(rewards) - max_rewards))

        form = ActionForm(
            title=self.format_text(
                self.config.get("messages", {}).get("crate.preview.header", "{name}"),
                name=self.get_crate_name(crate_id),
            ),
            content=self.format_text(
                self.config.get("messages", {}).get("crate.preview.content", ""),
                name=self.get_crate_name(crate_id),
            )
            + "\n\n"
            + "\n".join(lines),
        )
        form.add_button(
            self.format_text(self.config.get("messages", {}).get("crate.preview.button", "Open")),
            on_click=lambda clicked_player: self.open_crate(clicked_player, crate_id),
        )
        player.send_form(form)

    def send_player_help(self, sender: Any):
        self.send(sender, "crate.help.header", prefixed=False)
        self.send(sender, "crate.help.list", prefixed=False)
        self.send(sender, "crate.help.preview", prefixed=False)
        self.send(sender, "crate.help.open", prefixed=False)
        self.send(sender, "crate.help.keys", prefixed=False)

    def send_admin_help(self, sender: Any):
        self.send(sender, "admin.help.header", prefixed=False)
        self.send(sender, "admin.help.give", prefixed=False)
        self.send(sender, "admin.help.giveall", prefixed=False)
        self.send(sender, "admin.help.set", prefixed=False)
        self.send(sender, "admin.help.remove", prefixed=False)
        self.send(sender, "admin.help.locations", prefixed=False)
        self.send(sender, "admin.help.info", prefixed=False)
        self.send(sender, "admin.help.reload", prefixed=False)
        self.send(sender, "admin.help.cancel", prefixed=False)

    def send_crate_list(self, sender: Any):
        crates = self.config.get("crates", {})
        self.send(sender, "crate.list.header", prefixed=False)
        for crate_id in crates:
            self.send(
                sender,
                "crate.list.entry",
                prefixed=False,
                id=crate_id,
                name=self.get_crate_name(str(crate_id)),
            )

    def send_keys(self, player: Any):
        self.send(player, "keys.header", prefixed=False)
        found = False
        for crate_id in self.config.get("crates", {}):
            amount = self.count_keys(player, str(crate_id))
            if amount <= 0:
                continue
            found = True
            self.send(player, "keys.entry", prefixed=False, crate=crate_id, amount=amount)

        if not found:
            self.send(player, "keys.none")

    def send_locations(self, sender: Any):
        if not self.locations:
            self.send(sender, "admin.locations.none")
            return

        self.send(sender, "admin.locations.header", prefixed=False)
        for location in self.locations:
            self.send(
                sender,
                "admin.locations.entry",
                prefixed=False,
                crate=location.get("crate", "unknown"),
                dimension=location.get("dimension", "unknown"),
                x=location.get("x", 0),
                y=location.get("y", 0),
                z=location.get("z", 0),
            )

    def send_crate_info(self, sender: Any, crate_id: str):
        crate_id = self.match_crate_id(crate_id) or crate_id
        crate = self.get_crate(crate_id)
        if crate is None:
            self.send(sender, "error.crate_missing", crate=crate_id)
            return

        location_count = sum(1 for location in self.locations if location.get("crate") == crate_id)
        total_opens = int(self.stats.get("total_opens", {}).get(crate_id, 0))
        self.send(sender, "admin.info.header", prefixed=False, name=self.get_crate_name(crate_id))
        self.send(sender, "admin.info.rewards", prefixed=False, count=len(self.get_rewards(crate_id)))
        self.send(sender, "admin.info.locations", prefixed=False, count=location_count)
        self.send(sender, "admin.info.opens", prefixed=False, count=total_opens)

    def protect_crate_break(self, player: Any, block: Any) -> bool:
        location = self.get_location_for_block(block)
        if location is None:
            return False

        if not bool(self.config.get("settings", {}).get("protect_crates", True)):
            self.locations.remove(location)
            self.save_locations()
            return False

        self.send(player, "admin.protected")
        return True
