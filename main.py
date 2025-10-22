import logging
import requests
from typing import Literal
import functools
from gi.repository import Gio

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.action.BaseAction import BaseAction


logger = logging.getLogger(__name__)

SortBy = Literal["-created", "created", "-edited", "edited"]
ItemAction = Literal["browser", "tro"]


@functools.cache
def get_default_terminal() -> tuple[str, str]:
    settings = Gio.Settings.new("org.gnome.desktop.default-applications.terminal")
    terminal = settings.get_string("exec")
    terminal_args = settings.get_string("exec-arg")
    return (terminal, terminal_args)


def get_terminal_script(application: str) -> str:
    terminal, exec_args = get_default_terminal()
    script = f"{terminal} {exec_args} {application}"
    logger.debug(f"{script=}")
    return script


def search(
    query: str,
    *,
    api_token: str,
    api_key: str,
    item_action: ItemAction,
    default_sort: SortBy,
) -> list[ExtensionResultItem]:
    # By default, we assume the user is searching for open cards
    if "is:closed" not in query:
        query += " is:open"

    if "sort:" not in query:
        query += f" sort:{default_sort}"

    logger.debug("trello query: %s", query)

    params: dict[str, str] = {
        "query": query,
        "key": api_key,
        "token": api_token,
        "cards_limit": "5",
        "card_list": "true",
        "card_board": "true",
        "card_fields": "name,url",
    }

    resp = requests.get(
        "https://api.trello.com/1/search",
        headers={"Accept": "application/json"},
        params=params,
    )
    if not resp.ok:
        logger.error("Unable to retrieve trello lists")
        logger.error(resp.content)
        return []

    results: list[ExtensionResultItem] = []
    data = resp.json()
    logger.debug("trello api response: %s", resp.content)

    if "cards" not in data:
        return results

    for card in data["cards"]:
        description = ""
        board_name = card["board"]["name"]
        list_name = card["list"]["name"]
        card_name = card["name"]

        if item_action == "browser":
            action = OpenUrlAction(card["url"])
        elif item_action == "tro":
            action = RunScriptAction(
                get_terminal_script(
                    f"tro show '{board_name}' '{list_name}' '{card_name}'"
                )
            )
        else:
            raise ValueError("Unable to determine action", item_action)

        results.append(
            ExtensionResultItem(
                icon="images/icon.png",
                name=f"[{board_name}] {card_name}",
                description=description,
                on_enter=action,
            )
        )
    return results


class TrelloExtension(Extension):
    def __init__(self) -> None:
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(
        self,
        event: KeywordQueryEvent,
        extension: Extension,
    ) -> RenderResultListAction:
        api_token = extension.preferences["api_token"]
        api_key = extension.preferences["api_key"]
        default_sort: SortBy = extension.preferences["default_sort"]
        item_action: ItemAction = extension.preferences["item_action"]

        logger.debug(f"{default_sort=}")
        logger.debug(get_default_terminal())

        argument = event.get_argument()

        if api_token is None:
            logger.warn("API token must be set")
            return []

        if api_key is None:
            logger.warn("API key must be set")
            return []

        if argument is None:
            return []

        results: list[ExtensionResultItem] = search(
            argument,
            api_token=api_token,
            api_key=api_key,
            item_action=item_action,
            default_sort=default_sort,
        )
        return RenderResultListAction(results[:5])


if __name__ == "__main__":
    TrelloExtension().run()
