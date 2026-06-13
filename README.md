# Endstone Crates

Crates for Endstone.

## Commands

- `/crates list` - list configured crates
- `/crates preview <crate>` - preview crate rewards
- `/crates open <crate>` - open a crate with a key
- `/keys` - show your crate keys
- `/crateadmin give <player> <crate> [amount]` - give keys
- `/crateadmin giveall <crate> [amount]` - give keys to online players
- `/crateadmin set <crate>` - right-click a block to link it as that crate
- `/crateadmin remove` - right-click a linked crate to unlink it
- `/crateadmin locations` - list linked physical crates
- `/crateadmin info <crate>` - show crate stats
- `/crateadmin reload` - reload JSON files

## Files

Source layout:

- `src/crates/plugin.py` - Endstone plugin entry point
- `src/crates/commands/` - player and admin command handling
- `src/crates/listeners/` - Endstone event listeners
- `src/crates/managers/` - crate logic, rewards, keys, stats
- `src/crates/storage/` - JSON persistence helpers
- `src/crates/constants.py` - default config/messages/crates

On first server load, the plugin creates these files in `bedrock_server/plugins/crates/`:

- `config.json` - crates, keys, rewards, messages, sounds, and settings
- `locations.json` - linked physical crate blocks
- `stats.json` - per-player and total crate open stats

Rewards support inventory items, console commands, player commands, XP, XP levels, private messages, and broadcasts. Left-click a linked crate, or sneak and right-click it, to preview rewards. Right-click normally to open it.
