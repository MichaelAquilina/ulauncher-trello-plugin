import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction


logger = logging.getLogger(__name__)


def search(query: str, *, api_token: str, api_key: str) -> list[ExtensionResultItem]:
    params: dict[str, str] = {
        "query": query,
        "key": api_key,
        "token": api_token,
        "partial": "true",
        "card_fields": "name,desc,url",
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
    for card in data["cards"]:
        results.append(
            ExtensionResultItem(
                icon="images/icon.png",
                name=card["name"],
                description=card["desc"][:100],
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
        )
        return RenderResultListAction(results[:5])


if __name__ == "__main__":
    TrelloExtension().run()
