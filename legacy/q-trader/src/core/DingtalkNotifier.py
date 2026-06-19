class DingtalkNotifier:
    def __init__(self):
        self.webhook = Config.DINGTALK_WEBHOOK
        self.session = aiohttp.ClientSession()

    async def send_alert(self, message: str):
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "交易通知",
                "text": f"**交易信号**\n{message}\n> 时间：{datetime.now()}"
            }
        }

        try:
            async with self.session.post(self.webhook, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"钉钉通知发送失败: {await resp.text()}")
        except Exception as e:
            logger.error(f"通知异常: {e}")