from typing import Any


def command_templates(
    reward: dict[str, Any],
    plural_key: str,
    singular_key: str,
) -> list[str]:
    """Return configured reward commands in a consistent list form."""
    templates: list[str] = []

    for key in (singular_key, plural_key):
        value = reward.get(key)
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, (list, tuple)):
            values = value
        else:
            continue

        templates.extend(str(entry) for entry in values if str(entry).strip())

    return templates


def format_reward_command(
    template: str,
    *,
    player: str,
    crate: str,
    reward: str,
) -> str:
    """Substitute reward placeholders and normalize an optional leading slash."""
    command = template.format(player=player, crate=crate, reward=reward).strip()
    if command.startswith("/"):
        command = command[1:].lstrip()
    return command
