import importlib.util
import unittest
from pathlib import Path


REWARDS_MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "crates" / "rewards.py"
SPEC = importlib.util.spec_from_file_location("rewards", REWARDS_MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
REWARDS_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REWARDS_MODULE)
command_templates = REWARDS_MODULE.command_templates
format_reward_command = REWARDS_MODULE.format_reward_command


class CommandRewardTests(unittest.TestCase):
    def test_command_only_reward_supports_singular_and_plural_forms(self):
        reward = {
            "command": "say first",
            "commands": ["give {player} diamond 1", "say last"],
        }

        self.assertEqual(
            command_templates(reward, "commands", "command"),
            ["say first", "give {player} diamond 1", "say last"],
        )

    def test_plural_command_may_be_a_string(self):
        reward = {"commands": "say one command"}

        self.assertEqual(
            command_templates(reward, "commands", "command"),
            ["say one command"],
        )

    def test_command_placeholders_and_optional_slash_are_normalized(self):
        command = format_reward_command(
            "  /say {player} won {reward} from {crate}  ",
            player="Steve",
            crate="vote",
            reward="VIP Rank",
        )

        self.assertEqual(command, "say Steve won VIP Rank from vote")

    def test_literal_braces_can_be_escaped(self):
        command = format_reward_command(
            "say {{literal}} {player}",
            player="Alex",
            crate="rare",
            reward="Coins",
        )

        self.assertEqual(command, "say {literal} Alex")


if __name__ == "__main__":
    unittest.main()
