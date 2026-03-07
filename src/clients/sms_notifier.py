from src.settings.build_logger import build_logger

logger = build_logger(__name__)


class SmsNotifier:
    async def send(self, user_id: str, template_name: str, reason: str) -> None:
        logger.info(
            "Stub sms send to provider | user_id=%s template=%s reason=%s",
            user_id,
            template_name,
            reason,
        )
