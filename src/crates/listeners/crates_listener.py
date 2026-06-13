from endstone.event import BlockBreakEvent, BlockPlaceEvent, PlayerInteractEvent, event_handler

from crates.managers import CrateManager


class CratesListener:
    def __init__(self, manager: CrateManager):
        self.manager = manager

    @event_handler
    def on_player_interact(self, event: PlayerInteractEvent):
        action_name = getattr(event.action, "name", str(event.action))
        if action_name not in ["LEFT_CLICK_BLOCK", "RIGHT_CLICK_BLOCK"]:
            return

        if not event.has_block:
            return

        player = event.player
        block = event.block

        if self.manager.handle_setup_click(player, block):
            event.cancel()
            return

        if self.manager.get_location_for_block(block) is None:
            return

        event.cancel()
        preview = action_name == "LEFT_CLICK_BLOCK" or bool(getattr(player, "is_sneaking", False))
        self.manager.open_from_block(player, block, preview=preview)

    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        if self.manager.protect_crate_break(event.player, event.block):
            event.cancel()

    @event_handler
    def on_block_place(self, event: BlockPlaceEvent):
        if self.manager.protect_key_placement(event.player):
            event.cancel()
