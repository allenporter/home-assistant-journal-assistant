"""Library for sending events when a Media Source content changes.

A media source is a browsable directory of media files. This library will scan
the media source for files and directories. This library keeps track of the hash
of the contents of each file and will publish an event when the content has changed
since the last scan.

This actually fetches the media content to determine if it has changed, so the
source must be resilient to frequent requests. This works well for local sources
where it would be reading a local file anyway.
"""

import hashlib
import logging
import datetime
from abc import ABC, abstractmethod

import aiohttp

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.components.media_source import (
    async_browse_media,
    async_resolve_media,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.storage import Store

from .const import DOMAIN, CONF_MEDIA_SOURCE

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
HASH_STORAGE_PATH = f".storage/{DOMAIN}/{{config_entry_id}}/hashes"
LISTENER_DATA_KEY = "listener"
UPDATE_INTERVAL = datetime.timedelta(hours=6)


class ProcessItem(ABC):
    """Base class for processing media items."""

    @abstractmethod
    async def process(self, hass: HomeAssistant, identifier: str) -> bool:
        """Process the media item.

        Return True if the item was processed, or False if there is a retryable error.
        """


class ProcessMediaServiceCall(ProcessItem):
    """Base class for processing media items."""

    async def process(self, hass: HomeAssistant, identifier: str) -> bool:
        """Process the media item."""
        try:
            await hass.services.async_call(
                DOMAIN,
                "process_media",
                {CONF_MEDIA_SOURCE: identifier},
                blocking=True,
            )
        except ServiceValidationError as err:
            _LOGGER.warning("Skipping process_media due to bad request: %s", err)
            return True
        except HomeAssistantError as err:
            _LOGGER.error("Retryable error processing media content: %s", err)
            return False
        return True


class MediaSourceListener:
    """Library for listening for content changes in a media source."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        media_source_prefix: str,
        process_item: ProcessItem,
    ) -> None:
        """Initialize the media source listener."""
        self._hass = hass
        self._media_source_prefix = media_source_prefix
        self._store = Store(
            hass,
            version=STORAGE_VERSION,
            key=HASH_STORAGE_PATH.format(config_entry_id=config_entry_id),
            private=True,
        )
        self._process_item = process_item
        self._unsub_refresh: CALLBACK_TYPE | None = None
        _LOGGER.info("Creating media source listener for %s", self._media_source_prefix)

    def async_attach(self) -> None:
        """Attach an event listener."""
        self._unsub_refresh = async_track_time_interval(
            self._hass, self.async_process_media, UPDATE_INTERVAL
        )

    @callback
    def async_detach(self) -> None:
        """Detach the event listener."""
        if self._unsub_refresh:
            self._unsub_refresh()
        self._unsub_refresh = None

    async def async_process_media(self, _: datetime.datetime) -> None:
        """Walk the directory structure and check for changes."""
        _LOGGER.info("Processing changes in media source %s", self._media_source_prefix)
        session = aiohttp_client.async_get_clientsession(self._hass)

        data = await self._store.async_load() or {}
        hashes = data.get("hashes", {})

        queue = [self._media_source_prefix]
        while queue:
            identifier = queue.pop()
            _LOGGER.debug("Processing media %s", identifier)
            browse = await async_browse_media(self._hass, identifier)
            _LOGGER.debug("Media has %s children", len(browse.children))
            for child in browse.children:
                if child.can_expand:
                    queue.append(child.identifier)
                    continue

                _LOGGER.debug("Processing media content %s", child.identifier)
                # Can't expand, this is the media file.
                play_media = await async_resolve_media(
                    self._hass, child.identifier, target_media_player=None
                )
                _LOGGER.debug("Fetching media content %s", play_media.url)
                # Download the content and compare the hash to determine if it has changed.
                try:
                    response = await session.request("get", play_media.url)
                    response.raise_for_status()
                    content = await response.read()
                except aiohttp.ClientError as err:
                    _LOGGER.error(
                        "Error downloading media content %s: %s", play_media.url, err
                    )
                    continue

                content_hash = hashlib.sha256(content).hexdigest()
                if content_hash == hashes.get(child.identifier):
                    _LOGGER.debug("Media content has not changed, skipping")
                    continue

                _LOGGER.debug("Media content has changed (%s bytes)", len(content))

                # Process the media content
                result = await self._process_item.process(self._hass, child.identifier)
                if not result:
                    _LOGGER.info("Error processing media content %s", child.identifier)
                    continue

                # Store the updated hash
                hashes[child.identifier] = content_hash
                data["hashes"] = hashes
                await self._store.async_save(data)

        _LOGGER.debug("Processing ended")
