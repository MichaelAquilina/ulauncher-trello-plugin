import logging
import requests
from typing import Literal

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction


logger = logging.getLogger(__name__)

SortBy = Literal["-created", "created", "-edited", "edited"]


def search(
    query: str,
    *,
    api_token: str,
    api_key: str,
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

        results.append(
            ExtensionResultItem(
                icon="images/icon.png",
                name=f"[{card["board"]["name"]}] {card["name"]} ",
                description=description,
                on_enter=OpenUrlAction(card["url"]),
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

        logger.debug(f"{default_sort=}")

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
            default_sort=default_sort,
        )
        return RenderResultListAction(results[:5])


if __name__ == "__main__":
    TrelloExtension().run()
