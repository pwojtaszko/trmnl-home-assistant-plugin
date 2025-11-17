from homeassistant.components.frontend import async_register_built_in_panel

async def async_setup_entry(hass, entry):
    await async_register_built_in_panel(
        hass,
        component_name="trmnl_dashboard_panel",
        sidebar_title="TRMNL Dashboard",
        sidebar_icon="mdi:webhook",
        frontend_url_path="trmnl-webhook",
        require_admin=True,
    )
    return True
