"""Library for sending events when a Media Source content changes.

A media source is a browsable directory of media files. This library will scan
the media source for files and directories. This library keeps track of the hash
of the contents of each file and will publish an event when the content has changed
since the last scan.
"""

import hashlib
import logging
import datetime
from typing import cast

import aiohttp

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.components.media_source import (
    URI_SCHEME,
    async_browse_media,
    async_resolve_media,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_PATH = f"{DOMAIN}/media_source_listener/{{listener_id}}"
LISTENER_DATA_KEY = "listener"
UPDATE_INTERVAL = datetime.timedelta(minutes=60)


def async_create_media_source_listener(
    hass: HomeAssistant, media_source_domain: str, event_name: str
) -> CALLBACK_TYPE:
    """Register a hook to process media files.

    Events will be published to the hook when media files are added or changed using the
    listener_id as the event identifier.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(LISTENER_DATA_KEY, {})

    listener = MediaSourceListener(hass, media_source_domain, event_name)
    listener.async_attach()

    hass.data[DOMAIN][LISTENER_DATA_KEY].update({event_name: listener})

    return cast(CALLBACK_TYPE, listener.async_detach)


class MediaSourceListener:
    """Library for listening for content changes in a media source."""

    def __init__(
        self, hass: HomeAssistant, media_source_domain: str, listener_id: str
    ) -> None:
        """Initialize the media source listener."""
        self._hass = hass
        self._listener_id = listener_id
        self._media_source_prefix = f"{URI_SCHEME}{media_source_domain}"
        self._store = Store(
            hass,
            version=STORAGE_VERSION,
            key=STORAGE_PATH.format(listener_id=listener_id),
            private=True,
        )
        self._unsub_refresh: CALLBACK_TYPE | None = None

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
        _LOGGER.debug("Processing start")
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

                # Publish an event indicating the content has changed
                self._hass.bus.async_fire(
                    self._listener_id,
                    {
                        "identifier": child.identifier,
                        "title": child.title,
                        "media_class": child.media_class,
                        "media_content_type": child.media_content_type,
                        "sha256": content_hash,
                    },
                )

                # Store the new hash
                hashes[child.identifier] = content_hash
                data["hashes"] = hashes
                await self._store.async_save(data)

        _LOGGER.debug("Processing ended")
