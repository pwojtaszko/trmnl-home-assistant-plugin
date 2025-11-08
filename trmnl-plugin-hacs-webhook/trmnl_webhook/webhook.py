import aiohttp

async def send_to_trmnl_webhook(data, webhook_url):
    payload = {"merge_variables": data}
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Webhook error: {response.status} {text}")
