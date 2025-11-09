import logging

_LOGGER = logging.getLogger(__name__)

async def send_to_trmnl_webhook(session, data, webhook_url):
    payload = {"merge_variables": data}
    try:
        async with session.post(webhook_url, json=payload) as response:
            resp_text = await response.text()
            if response.status != 200:
                _LOGGER.error(f"TRMNL Webhook: Error response: {resp_text}")
                raise Exception(f"Webhook error: {response.status} {resp_text}")
    except Exception as ex:
        _LOGGER.error(f"TRMNL Webhook: Exception during webhook update: {ex}")
        raise
