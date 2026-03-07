from src.settings.build_logger import logger


class SmsNotifier:
    async def send(self, user_id: str, template_name: str, reason: str) -> None:
        """Log a stubbed SMS notification send action."""
        logger.info(
            "Stub sms send to provider | user_id=%s template=%s reason=%s",
            user_id,
            template_name,
            reason,
        )
