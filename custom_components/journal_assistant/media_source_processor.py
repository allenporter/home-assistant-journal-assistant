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
    URI_SCHEME,
    async_resolve_media,
    Unresolvable,
)
from homeassistant.components.media_player.errors import BrowseError
from homeassistant.components.media_player.browse_media import (
    async_process_play_media_url,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.storage import Store

from .const import DOMAIN, CONF_MEDIA_SOURCE, CONF_CONFIG_ENTRY_ID

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
HASH_STORAGE_PATH = f"{DOMAIN}/{{config_entry_id}}/hashes"
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

    def __init__(self, config_entry_id: str) -> None:
        """Initialize the process media service call."""
        self._config_entry_id = config_entry_id

    async def process(self, hass: HomeAssistant, identifier: str) -> bool:
        """Process the media item."""
        try:
            await hass.services.async_call(
                DOMAIN,
                "process_media",
                {
                    CONF_MEDIA_SOURCE: identifier,
                    CONF_CONFIG_ENTRY_ID: self._config_entry_id,
                },
                blocking=True,
            )
        except ServiceValidationError as err:
            _LOGGER.warning("Skipping process_media due to bad request: %s", err)
            return True
        except HomeAssistantError as err:
            _LOGGER.error("Retryable error processing media content: %s", err)
            return False
        return True


class MediaSourceProcessor:
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
        self._scanning = False

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
        if self._scanning:
            _LOGGER.debug("Media source listener is already scanning; Skipping")
            return
        self._scanning = True
        try:
            await self._async_process_media()
        finally:
            self._scanning = False

    async def _async_process_media(self) -> None:
        """Walk the directory structure and check for changes."""
        _LOGGER.info("Processing changes in media source %s", self._media_source_prefix)
        session = aiohttp_client.async_get_clientsession(self._hass)

        data = await self._store.async_load() or {}
        hashes = data.get("hashes", {})

        queue = [self._media_source_prefix]
        while queue:
            identifier = queue.pop()
            _LOGGER.debug("Processing media %s", identifier)
            try:
                browse = await async_browse_media(self._hass, identifier)
            except BrowseError as err:
                _LOGGER.error("Error browsing media %s: %s", identifier, err)
                continue
            _LOGGER.debug("Media has %s children", len(browse.children))
            for child in browse.children:
                child_identifier = f"{URI_SCHEME}{child.domain}/{child.identifier}"
                if child.can_expand:
                    queue.append(child_identifier)
                    continue

                _LOGGER.debug("Processing media content %s", child_identifier)
                # Can't expand, this is the media file.
                try:
                    play_media = await async_resolve_media(
                        self._hass, child_identifier, target_media_player=None
                    )
                except Unresolvable as err:
                    _LOGGER.error("Error resolving media %s: %s", child_identifier, err)
                    continue
                url = async_process_play_media_url(self._hass, play_media.url)
                _LOGGER.debug("Fetching media content %s", url)
                # Download the content and compare the hash to determine if it has changed.
                try:
                    response = await session.request("get", url)
                    response.raise_for_status()
                    content = await response.read()
                except aiohttp.ClientError as err:
                    _LOGGER.error(
                        "Error downloading media content %s: %s", play_media.url, err
                    )
                    continue

                content_hash = hashlib.sha256(content).hexdigest()
                if content_hash == hashes.get(child_identifier):
                    _LOGGER.debug("Media content has not changed, skipping")
                    continue

                _LOGGER.debug("Media content has changed (%s bytes)", len(content))

                # Process the media content
                result = await self._process_item.process(self._hass, child_identifier)
                if not result:
                    _LOGGER.info("Error processing media content %s", child_identifier)
                    continue

                # Store the updated hash
                hashes[child_identifier] = content_hash
                data["hashes"] = hashes
                await self._store.async_save(data)

        _LOGGER.debug("Processing ended")
