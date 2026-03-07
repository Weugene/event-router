from src.settings.build_logger import logger


class EmailNotifier:
    async def send(self, user_id: str, template_name: str, reason: str) -> None:
        """Log a stubbed email notification send action."""
        logger.info(
            "Stub email send to provider | user_id=%s template=%s reason=%s",
            user_id,
            template_name,
            reason,
        )
