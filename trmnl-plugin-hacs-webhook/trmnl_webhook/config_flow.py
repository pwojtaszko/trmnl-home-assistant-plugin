import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from . import DOMAIN
from .webhook import send_to_trmnl_webhook
from homeassistant.helpers.selector import selector

class TrmnlWebhookConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        prev_data = {}
        if hasattr(self, "config_entry") and self.config_entry:
            prev_data = {**self.config_entry.data, **self.config_entry.options}

        # Always build groups from user_input if present, else from prev_data
        if user_input is not None:
            # Determine current number of groups from user_input
            i = 0
            while f"group_{i}_name" in user_input or f"group_{i}_entities" in user_input:
                i += 1
            num_groups = i if i > 0 else 1
            add_group = user_input.get("add_another_group", False)
            # Build groups from user_input (just entity IDs)
            new_groups = []
            for idx in range(num_groups):
                group_name = user_input.get(f"group_{idx}_name", f"Group {idx+1}")
                group_entities = user_input.get(f"group_{idx}_entities", [])
                group_dict = {
                    "entities": [{"entity_id": ent} for ent in group_entities if ent]
                }
                if group_name:
                    group_dict["groupName"] = group_name
                new_groups.append(group_dict)
            if add_group:
                new_groups.append({"groupName": f"Group {len(new_groups)+1}", "entities": []})
                num_groups = len(new_groups)
                schema = self._get_dynamic_schema(prev_data, user_input, num_groups)
                
                # Build description_placeholders for dynamic group labels
                placeholders = {}
                for i in range(num_groups):
                    placeholders[f"group_{i}_name"] = {"number": str(i + 1)}
                    placeholders[f"group_{i}_entities"] = {"number": str(i + 1)}
                
                return self.async_show_form(
                    step_id="user",
                    data_schema=schema,
                    description_placeholders=placeholders,
                )
            webhook_url = user_input.get("webhook_url") or prev_data.get("webhook_url", "")
            pill_entities = user_input.get("pill_entities", [])
            pills_obj = [{"entity_id": ent} for ent in pill_entities if ent]
            data = {
                "webhook_url": webhook_url,
                "groups": new_groups,
                "pills": pills_obj
            }
            return self.async_create_entry(title="TRMNL Webhook", data=data)
        else:
            groups = prev_data.get("groups", [])
            num_groups = len(groups) if groups else 1
            schema = self._get_dynamic_schema(prev_data, user_input, num_groups)
            
            # Build description_placeholders for dynamic group labels
            placeholders = {}
            for i in range(num_groups):
                placeholders[f"group_{i}_name"] = {"number": str(i + 1)}
                placeholders[f"group_{i}_entities"] = {"number": str(i + 1)}
            
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                description_placeholders=placeholders,
            )

    def _get_dynamic_schema(self, prev_data=None, user_input=None, num_groups=1):
        prev_data = prev_data or {}
        webhook_url_default = ""
        if user_input and "webhook_url" in user_input:
            webhook_url_default = user_input["webhook_url"]
        else:
            webhook_url_default = prev_data.get("webhook_url", "")
        schema_dict = {
            vol.Required("webhook_url", default=webhook_url_default): str,
        }
        pill_entities_default = []
        if user_input:
            pill_entities_default = user_input.get("pill_entities", [e.get("entity_id") for e in prev_data.get("pills", [])])
        elif prev_data.get("pills"):
            pill_entities_default = [e.get("entity_id") for e in prev_data["pills"]]
        schema_dict[vol.Optional("pill_entities", default=pill_entities_default)] = selector({"entity": {"multiple": True}})

        groups = prev_data.get("groups", [])
        for i in range(num_groups):
            group_name_default = None
            group_entities_default = []
            if user_input:
                group_name_default = user_input.get(f"group_{i}_name", groups[i].get("groupName", f"Group {i+1}") if i < len(groups) else f"Group {i+1}")
                group_entities_default = user_input.get(f"group_{i}_entities", [e.get("entity_id") for e in groups[i].get("entities", [])] if i < len(groups) else [])
            elif i < len(groups):
                group_name_default = groups[i].get("groupName", f"Group {i+1}")
                group_entities_default = [e.get("entity_id") for e in groups[i].get("entities", [])]
            else:
                group_name_default = f"Group {i+1}"
                group_entities_default = []
            schema_dict[vol.Optional(f"group_{i}_name", default=group_name_default)] = str
            schema_dict[vol.Optional(f"group_{i}_entities", default=group_entities_default)] = selector({"entity": {"multiple": True}})
        schema_dict[vol.Optional("add_another_group", default=False)] = bool
        return vol.Schema(schema_dict)


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TrmnlWebhookOptionsFlowHandler(config_entry)

class TrmnlWebhookOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        # Store entry_id for context lookup
        self.entry_id = config_entry.entry_id

    async def async_step_init(self, user_input=None):
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        prev_data = {**entry.data, **entry.options} if entry else {}
        hass = self.hass

        # Always build groups from user_input if present, else from prev_data
        if user_input is not None:
            # Determine current number of groups from user_input
            i = 0
            while f"group_{i}_name" in user_input or f"group_{i}_entities" in user_input:
                i += 1
            num_groups = i if i > 0 else 1
            add_group = user_input.get("add_another_group", False)
            # Handle group removal
            removed_indices = []
            for idx in range(num_groups):
                if user_input.get(f"remove_group_{idx}"):
                    removed_indices.append(idx)
            # Build groups from user_input (just entity IDs)
            updated_groups = []
            for idx in range(num_groups):
                if idx in removed_indices:
                    continue
                group_name = user_input.get(f"group_{idx}_name", f"Group {idx+1}")
                group_entities = user_input.get(f"group_{idx}_entities", [])
                group_dict = {
                    "entities": [{"entity_id": ent} for ent in group_entities if ent]
                }
                if group_name:
                    group_dict["groupName"] = group_name
                updated_groups.append(group_dict)
            if add_group:
                updated_groups.append({"groupName": f"Group {len(updated_groups)+1}", "entities": []})
                num_groups = len(updated_groups)
                schema = self._get_dynamic_options_schema(prev_data, user_input, num_groups)
                
                # Build description_placeholders for dynamic group labels
                placeholders = {}
                for i in range(num_groups):
                    placeholders[f"group_{i}_name"] = {"number": str(i + 1)}
                    placeholders[f"group_{i}_entities"] = {"number": str(i + 1)}
                    placeholders[f"remove_group_{i}"] = {"number": str(i + 1)}
                
                return self.async_show_form(
                    step_id="init",
                    data_schema=schema,
                    description_placeholders=placeholders,
                )
            webhook_url = user_input.get("webhook_url", prev_data.get("webhook_url", ""))
            pills_entities = user_input.get("pill_entities", [])
            pills_obj = [{"entity_id": ent} for ent in pills_entities if ent]
            data = {
                "webhook_url": webhook_url,
                "groups": updated_groups,
                "pills": pills_obj
            }
            return self.async_create_entry(title="config_flow.options_title", data=data)
        else:
            groups = prev_data.get("groups", [])
            num_groups = len(groups) if groups else 1
            schema = self._get_dynamic_options_schema(prev_data, user_input, num_groups)
            
            # Build description_placeholders for dynamic group labels
            placeholders = {}
            for i in range(num_groups):
                placeholders[f"group_{i}_name"] = {"number": str(i + 1)}
                placeholders[f"group_{i}_entities"] = {"number": str(i + 1)}
                placeholders[f"remove_group_{i}"] = {"number": str(i + 1)}
            
            return self.async_show_form(step_id="init", data_schema=schema, description_placeholders=placeholders)

    def _get_dynamic_options_schema(self, prev_data=None, user_input=None, num_groups=1):
        prev_data = prev_data or {}
        schema_dict = {
            vol.Required("webhook_url", default=prev_data.get("webhook_url", "")): str,
        }
        pill_entities_default = []
        if user_input:
            pill_entities_default = user_input.get("pill_entities", [e.get("entity_id") for e in prev_data.get("pills", [])])
        elif prev_data.get("pills"):
            pill_entities_default = [e.get("entity_id") for e in prev_data["pills"]]
        schema_dict[vol.Optional("pill_entities", default=pill_entities_default)] = selector({"entity": {"multiple": True}})

        groups = prev_data.get("groups", [])
        for i in range(num_groups):
            group_name_default = None
            group_entities_default = []
            if user_input:
                group_name_default = user_input.get(f"group_{i}_name", groups[i].get("groupName", f"Group {i+1}") if i < len(groups) else f"Group {i+1}")
                group_entities_default = user_input.get(f"group_{i}_entities", [e.get("entity_id") for e in groups[i].get("entities", [])] if i < len(groups) else [])
            elif i < len(groups):
                group_name_default = groups[i].get("groupName", f"Group {i+1}")
                group_entities_default = [e.get("entity_id") for e in groups[i].get("entities", [])]
            else:
                group_name_default = f"Group {i+1}"
                group_entities_default = []
            schema_dict[vol.Optional(f"group_{i}_name", default=group_name_default)] = str
            schema_dict[vol.Optional(f"group_{i}_entities", default=group_entities_default)] = selector({"entity": {"multiple": True}})
            schema_dict[vol.Optional(f"remove_group_{i}", default=False)] = bool
        schema_dict[vol.Optional("add_another_group", default=False)] = bool
        return vol.Schema(schema_dict)

    def _get_options_schema(self, prev_data=None, user_input=None, num_groups=1):
        prev_data = prev_data or {}
        schema_dict = {
            vol.Required("webhook_url", default=prev_data.get("webhook_url", "")): str,
        }
        # Pills first
        pill_entities_default = []
        if user_input:
            pill_entities_default = user_input.get("pill_entities", [e.get("entity_id") for e in prev_data.get("pills", [])])
        elif prev_data.get("pills"):
            pill_entities_default = [e.get("entity_id") for e in prev_data["pills"]]
        schema_dict[vol.Optional("pill_entities", default=pill_entities_default)] = selector({"entity": {"multiple": True}})

        # Then groups, each with a red checkbox for removal
        groups = prev_data.get("groups", [])
        for i in range(num_groups):
            group_name_default = None
            group_entities_default = []
            if user_input:
                group_name_default = user_input.get(f"group_{i}_name", groups[i].get("groupName", f"Group {i+1}") if i < len(groups) else f"Group {i+1}")
                group_entities_default = user_input.get(f"group_{i}_entities", [e.get("entity_id") for e in groups[i].get("entities", [])] if i < len(groups) else [])
            elif i < len(groups):
                group_name_default = groups[i].get("groupName", f"Group {i+1}")
                group_entities_default = [e.get("entity_id") for e in groups[i].get("entities", [])]
            else:
                group_name_default = f"Group {i+1}"
                group_entities_default = []
            schema_dict[vol.Optional(f"group_{i}_name", default=group_name_default)] = str
            schema_dict[vol.Optional(f"group_{i}_entities", default=group_entities_default)] = selector({"entity": {"multiple": True}})
            # Red checkbox for removal (UI color is handled by frontend, but label can indicate removal)
            schema_dict[vol.Optional(f"remove_group_{i}", default=False)] = bool
        return vol.Schema(schema_dict)
