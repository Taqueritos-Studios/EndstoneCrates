from typing import Any


COLOR = "\u00a7"


def default_config() -> dict[str, Any]:
    return {
        "settings": {
            "prefix": "&6Crates &8> &r",
            "default_crate_block": "minecraft:chest",
            "default_key_item": "minecraft:tripwire_hook",
            "set_block_on_link": False,
            "protect_crates": True,
            "broadcast_wins": True,
            "preview_max_rewards": 35,
            "admin_bypass_keys": False,
            "crate_cooldown_seconds": 1,
        },
        "holograms": {
            "enabled": True,
            "actor_identifier": "armor_stand",
            "y_offset": 1.35,
            "update_interval_ticks": 20,
            "lines": [
                "{name}",
                "&7Right-click to open",
                "&8Left-click to preview",
            ],
        },
        "opening": {
            "spin_ticks": 36,
            "spin_interval_ticks": 3,
            "spin_sound": "random.click",
            "win_sound": "random.levelup",
            "particle": "minecraft:basic_flame_particle",
        },
        "messages": {
            "error.players_only": "&cOnly players can use this command.",
            "error.no_permission": "&cYou do not have permission to do that.",
            "error.unknown_command": "&cUnknown command. Use &f/crates help&c.",
            "error.admin_usage": "&cUsage: &f{usage}",
            "error.crate_missing": "&cCrate &f{crate}&c does not exist.",
            "error.reward_missing": "&cCrate &f{crate}&c has no rewards configured.",
            "error.no_key": "&cYou need a &f{key}&c to open this crate.",
            "error.player_missing": "&cPlayer &f{player}&c is not online.",
            "error.invalid_amount": "&cAmount must be a positive number.",
            "error.already_opening": "&cYou are already opening a crate.",
            "error.cooldown": "&cWait &f{seconds}&c seconds before opening that crate again.",
            "error.key_place_blocked": "&cYou cannot place a &f{key}&c. Keep it to open crates.",
            "crate.help.header": "&6&lCrates",
            "crate.help.list": "&7/crates list &8- &fList available crates",
            "crate.help.preview": "&7/crates preview <crate> &8- &fPreview rewards",
            "crate.help.open": "&7/crates open <crate> &8- &fOpen with a key",
            "crate.help.keys": "&7/keys &8- &fView your crate keys",
            "crate.list.header": "&6&lAvailable Crates",
            "crate.list.entry": "&7- &f{id} &8({name}&8)",
            "crate.preview.header": "&6&l{name}",
            "crate.preview.content": "&7Possible rewards for &f{name}&7:",
            "crate.preview.button": "&aOpen this crate",
            "crate.preview.reward": "&7{chance}% &8- &f{name}",
            "crate.opening": "&eOpening &f{name}&e...",
            "crate.win": "&aYou won &f{reward}&a!",
            "crate.broadcast": "&6{player} &ewon &f{reward} &efrom &f{crate}&e!",
            "keys.none": "&7You do not have any crate keys.",
            "keys.header": "&6&lYour Crate Keys",
            "keys.entry": "&7- &f{crate}&7: &e{amount}",
            "admin.help.header": "&6&lCrates Admin",
            "admin.help.give": "&7/crateadmin give <player> <crate> [amount]",
            "admin.help.giveall": "&7/crateadmin giveall <crate> [amount]",
            "admin.help.set": "&7/crateadmin set <crate> &8- &fLink your next clicked block",
            "admin.help.remove": "&7/crateadmin remove &8- &fUnlink your next clicked crate",
            "admin.help.locations": "&7/crateadmin locations",
            "admin.help.info": "&7/crateadmin info <crate>",
            "admin.help.reload": "&7/crateadmin reload",
            "admin.help.cancel": "&7/crateadmin cancel",
            "admin.give.sender": "&aGave &f{amount}x {key} &ato &f{player}&a.",
            "admin.give.target": "&aYou received &f{amount}x {key}&a.",
            "admin.giveall": "&aGave &f{amount}x {key} &ato &f{count}&a online players.",
            "admin.link.start": "&eRight-click the block you want to make the &f{crate}&e crate.",
            "admin.link.done": "&aLinked &f{crate}&a crate at &f{x}, {y}, {z}&a.",
            "admin.remove.start": "&eRight-click a linked crate block to remove it.",
            "admin.remove.done": "&aRemoved crate link for &f{crate}&a at &f{x}, {y}, {z}&a.",
            "admin.remove.none": "&cThat block is not a linked crate.",
            "admin.cancel": "&aCancelled crate setup mode.",
            "admin.reload": "&aCrates config, locations, and stats reloaded.",
            "admin.locations.header": "&6&lCrate Locations",
            "admin.locations.none": "&7No crate locations are linked yet.",
            "admin.locations.entry": "&7- &f{crate} &8@ &f{dimension} {x}, {y}, {z}",
            "admin.info.header": "&6&l{name}",
            "admin.info.rewards": "&7Rewards: &f{count}",
            "admin.info.locations": "&7Locations: &f{count}",
            "admin.info.opens": "&7Total opens: &f{count}",
            "admin.protected": "&cThis crate is protected. Use &f/crateadmin remove&c first.",
        },
        "crates": {
            "vote": {
                "display_name": "&aVote Crate",
                "block_type": "minecraft:chest",
                "requires_key": True,
                "key": {
                    "item": "minecraft:tripwire_hook",
                    "name": "&aVote Key",
                    "lore": [
                        "&7Use this key on a Vote Crate.",
                        "&8crate: vote",
                    ],
                },
                "rewards": [
                    {
                        "id": "cobblestone",
                        "display_name": "&f64 Cobblestone",
                        "weight": 35,
                        "items": [
                            {"type": "minecraft:cobblestone", "amount": 64}
                        ],
                    },
                    {
                        "id": "iron",
                        "display_name": "&f16 Iron Ingots",
                        "weight": 25,
                        "items": [
                            {"type": "minecraft:iron_ingot", "amount": 16}
                        ],
                    },
                    {
                        "id": "diamonds",
                        "display_name": "&b3 Diamonds",
                        "weight": 10,
                        "broadcast": True,
                        "items": [
                            {"type": "minecraft:diamond", "amount": 3}
                        ],
                    },
                    {
                        "id": "xp",
                        "display_name": "&a150 XP",
                        "weight": 30,
                        "exp": 150,
                    },
                ],
            },
            "rare": {
                "display_name": "&dRare Crate",
                "block_type": "minecraft:ender_chest",
                "requires_key": True,
                "key": {
                    "item": "minecraft:tripwire_hook",
                    "name": "&dRare Key",
                    "lore": [
                        "&7Use this key on a Rare Crate.",
                        "&8crate: rare",
                    ],
                },
                "rewards": [
                    {
                        "id": "emeralds",
                        "display_name": "&a12 Emeralds",
                        "weight": 35,
                        "items": [
                            {"type": "minecraft:emerald", "amount": 12}
                        ],
                    },
                    {
                        "id": "diamond_pickaxe",
                        "display_name": "&bDiamond Pickaxe",
                        "weight": 20,
                        "broadcast": True,
                        "items": [
                            {
                                "type": "minecraft:diamond_pickaxe",
                                "amount": 1,
                                "name": "&bRare Pickaxe",
                                "lore": ["&7Won from the Rare Crate."],
                                "enchants": [
                                    {"id": "efficiency", "level": 3},
                                    {"id": "unbreaking", "level": 2},
                                ],
                            }
                        ],
                    },
                    {
                        "id": "gold",
                        "display_name": "&632 Gold Ingots",
                        "weight": 30,
                        "items": [
                            {"type": "minecraft:gold_ingot", "amount": 32}
                        ],
                    },
                    {
                        "id": "levels",
                        "display_name": "&a5 XP Levels",
                        "weight": 15,
                        "exp_levels": 5,
                    },
                ],
            },
        },
    }
