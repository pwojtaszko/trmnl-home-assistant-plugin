import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = "trmnl_webhook"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    # Register static path for frontend JS
    # Static www directory registration removed
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry"] = entry

    # Always use merged config: options override data
    def get_merged_config():
        merged = dict(entry.data)
        if hasattr(entry, "options") and entry.options:
            merged.update(entry.options)
        return merged

    # Interval update setup
    from datetime import timedelta
    from homeassistant.helpers.event import async_track_time_interval
    from .webhook import send_to_trmnl_webhook

    session = async_get_clientsession(hass)
    merged_config = get_merged_config()
    interval_seconds = merged_config.get("interval", 60)  # Default 60s

    try:
        async def periodic_update(now):
            config = get_merged_config()
            webhook_url = config.get("webhook_url")  # Always fetch latest
            # Build dynamic data from entity states
            groups = config.get("groups", [])
            pills = config.get("pills", [])
            updated_groups = []
            for group in groups:
                updated_entities = []
                for entity in group.get("entities", []):
                    entity_id = entity.get("entity_id")
                    state_obj = hass.states.get(entity_id)
                    if state_obj:
                        updated_entity = {
                            "entity_id": entity_id,
                            "state": state_obj.state,
                            "attributes": dict(state_obj.attributes),
                            "last_changed": str(state_obj.last_changed),
                            "last_updated": str(state_obj.last_updated),
                        }
                        updated_entities.append(updated_entity)
                    else:
                        updated_entities.append(entity)  # fallback to config
                updated_group = dict(group)
                updated_group["entities"] = updated_entities
                updated_groups.append(updated_group)
            updated_pills = []
            for pill in pills:
                entity_id = pill.get("entity_id")
                state_obj = hass.states.get(entity_id)
                if state_obj:
                    updated_pill = {
                        "entity_id": entity_id,
                        "state": state_obj.state,
                        "attributes": dict(state_obj.attributes),
                        "last_changed": str(state_obj.last_changed),
                        "last_updated": str(state_obj.last_updated),
                    }
                    updated_pills.append(updated_pill)
                else:
                    updated_pills.append(pill)
            webhook_data = {
                "groups": updated_groups,
                "pills": updated_pills
            }
            if webhook_url:
                try:
                    await send_to_trmnl_webhook(session, webhook_data, webhook_url)
                except Exception as e:
                    _LOGGER.error(f"TRMNL Webhook periodic update failed: {e}")

        remove_listener = async_track_time_interval(
            hass,
            periodic_update,
            timedelta(seconds=interval_seconds)
        )
        hass.data[DOMAIN]["remove_listener"] = remove_listener

        # Initial update
        webhook_url = merged_config.get("webhook_url")  # Always fetch latest
        if webhook_url:
            # Build dynamic data from entity states (same as periodic_update)
            groups = merged_config.get("groups", [])
            pills = merged_config.get("pills", [])
            updated_groups = []
            for group in groups:
                updated_entities = []
                for entity in group.get("entities", []):
                    entity_id = entity.get("entity_id")
                    state_obj = hass.states.get(entity_id)
                    if state_obj:
                        updated_entity = {
                            "entity_id": entity_id,
                            "state": state_obj.state,
                            "attributes": dict(state_obj.attributes),
                            "last_changed": str(state_obj.last_changed),
                            "last_updated": str(state_obj.last_updated),
                        }
                        updated_entities.append(updated_entity)
                    else:
                        updated_entities.append(entity)  # fallback to config
                updated_group = dict(group)
                updated_group["entities"] = updated_entities
                updated_groups.append(updated_group)
            updated_pills = []
            for pill in pills:
                entity_id = pill.get("entity_id")
                state_obj = hass.states.get(entity_id)
                if state_obj:
                    updated_pill = {
                        "entity_id": entity_id,
                        "state": state_obj.state,
                        "attributes": dict(state_obj.attributes),
                        "last_changed": str(state_obj.last_changed),
                        "last_updated": str(state_obj.last_updated),
                    }
                    updated_pills.append(updated_pill)
                else:
                    updated_pills.append(pill)
            webhook_data = {
                "groups": updated_groups,
                "pills": updated_pills
            }
            try:
                await send_to_trmnl_webhook(session, webhook_data, webhook_url)
            except Exception as e:
                _LOGGER.error(f"TRMNL Webhook initial update failed: {e}")

    except Exception as setup_ex:
        _LOGGER.error(f"TRMNL Webhook: Error in async_setup_entry: {setup_ex}")

    async def _reload_service(call):
        await async_reload_entry(hass, entry)

    hass.services.async_register(DOMAIN, "reload", _reload_service)
    return True

async def async_unload_entry(hass, entry):
    # Remove stored entry and unregister service
    hass.data[DOMAIN].pop("entry", None)
    # Remove interval listener if exists
    remove_listener = hass.data[DOMAIN].pop("remove_listener", None)
    if remove_listener:
        remove_listener()
    hass.services.async_remove(DOMAIN, "reload")
    return True

async def async_reload_entry(hass, entry):
    # Unload and re-setup entry for live config reload
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
