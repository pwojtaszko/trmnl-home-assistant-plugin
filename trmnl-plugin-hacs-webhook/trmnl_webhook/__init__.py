
DOMAIN = "trmnl_webhook"

async def async_setup_entry(hass, entry):
    # Register static path for frontend JS
    # Static www directory registration removed
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry"] = entry

    # Interval update setup
    from datetime import timedelta
    from homeassistant.helpers.event import async_track_time_interval
    from .webhook import send_to_trmnl_webhook

    interval_seconds = entry.data.get("interval", 60)  # Default 60s
    webhook_url = entry.data.get("webhook_url")
    webhook_data = {k: v for k, v in entry.data.items() if k not in ("interval", "webhook_url")}

    async def periodic_update(now):
        if webhook_url:
            try:
                await send_to_trmnl_webhook(webhook_data, webhook_url)
            except Exception as e:
                # Optionally log error
                hass.logger.warning(f"TRMNL Webhook periodic update failed: {e}")

    # Start interval task
    remove_listener = async_track_time_interval(
        hass,
        periodic_update,
        timedelta(seconds=interval_seconds)
    )
    hass.data[DOMAIN]["remove_listener"] = remove_listener

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
