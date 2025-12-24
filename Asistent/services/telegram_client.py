import logging
import time
from typing import Optional

import requests
from django.conf import settings

from Asistent.services.integration_monitor import (
    record_integration_error,
    record_integration_success,
)

logger = logging.getLogger(__name__)

RETRIABLE_STATUSES = {429, 500, 502, 503, 504}


class TelegramClient:
    def __init__(self, *, token: Optional[str] = None, timeout: int = 10):
        self.token = token or getattr(settings, "BOT_TOKEN", "")
        self.timeout = timeout

    def _build_url(self, method: str) -> str:
        if not self.token:
            raise ValueError("Telegram token is not configured")
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def _request(self, method: str, *, json_payload=None, data=None, files=None, retries: int = 3) -> Optional[requests.Response]:
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    self._build_url(method),
                    json=json_payload,
                    data=data,
                    files=files,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                record_integration_success("telegram")
                return response
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                description = ""
                try:
                    description = exc.response.json().get("description", "")
                except Exception:
                    description = exc.response.text if exc.response is not None else ""

                code_text = str(status or "http_error")
                severity = "error" if status in (401, 403) else "warning"
                record_integration_error("telegram", code_text, description or str(exc), severity=severity)
                last_error = exc

                if status not in RETRIABLE_STATUSES or attempt == retries or status in (401, 403):
                    break
            except Exception as exc:  # pragma: no cover - сетевые ошибки
                record_integration_error("telegram", "network", str(exc), severity="warning")
                last_error = exc
                if attempt == retries:
                    break

            sleep_for = min(10, attempt * 2)
            logger.warning("⏳ Telegram API retry %s/%s через %sс", attempt, retries, sleep_for)
            time.sleep(sleep_for)

        if last_error:
            logger.error("❌ TelegramClient.%s: %s", method, last_error)
        return None

    def send_request(self, method: str, payload: dict) -> Optional[dict]:
        """Выполняет произвольный метод Telegram API и возвращает response.json()."""
        response = self._request(method, json_payload=payload)
        if not response:
            return None
        try:
            result = response.json()
        except ValueError as exc:  # pragma: no cover - защитное
            record_integration_error("telegram", "bad_json", str(exc), severity="warning")
            return None
        if not result.get("ok"):
            record_integration_error("telegram", "api_error", result.get("description", "unknown"))
        return result

    def send_message(self, chat_id: str, text: str, **kwargs) -> bool:
        payload = {"chat_id": chat_id, "text": text}
        payload.update(kwargs)
        return bool(self._request("sendMessage", json_payload=payload))

    def send_photo(self, chat_id: str, photo_path: str, caption: Optional[str] = None, **kwargs) -> bool:
        try:
            # Проверяем существование файла
            import os
            if not os.path.exists(photo_path):
                record_integration_error("telegram", "file_missing", f"File not found: {photo_path}", severity="warning")
                logger.error("❌ TelegramClient.send_photo: File not found: %s", photo_path)
                return False
            
            # Проверяем размер файла (не должен быть пустым)
            file_size = os.path.getsize(photo_path)
            if file_size == 0:
                record_integration_error("telegram", "file_empty", f"File is empty: {photo_path}", severity="warning")
                logger.error("❌ TelegramClient.send_photo: File is empty: %s", photo_path)
                return False
            
            # Увеличиваем timeout для больших файлов (30 секунд для фото)
            original_timeout = self.timeout
            self.timeout = max(30, original_timeout)
            
            try:
                with open(photo_path, "rb") as photo_file:
                    files = {"photo": photo_file}
                    data = {"chat_id": chat_id}
                    if caption:
                        data["caption"] = caption
                    data.update(kwargs)
                    response = self._request("sendPhoto", data=data, files=files)
                    return bool(response)
            finally:
                # Восстанавливаем оригинальный timeout
                self.timeout = original_timeout
        except FileNotFoundError as exc:
            record_integration_error("telegram", "file_missing", str(exc), severity="warning")
            logger.error("❌ TelegramClient.send_photo: %s", exc)
            return False
        except Exception as exc:
            record_integration_error("telegram", "send_photo_error", str(exc), severity="warning")
            logger.error("❌ TelegramClient.send_photo: %s", exc)
            return False

    def send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, **kwargs) -> bool:
        try:
            # Проверяем существование файла
            import os
            if not os.path.exists(video_path):
                record_integration_error("telegram", "file_missing", f"File not found: {video_path}", severity="warning")
                logger.error("❌ TelegramClient.send_video: File not found: %s", video_path)
                return False
            
            # Проверяем размер файла (не должен быть пустым)
            file_size = os.path.getsize(video_path)
            if file_size == 0:
                record_integration_error("telegram", "file_empty", f"File is empty: {video_path}", severity="warning")
                logger.error("❌ TelegramClient.send_video: File is empty: %s", video_path)
                return False
            
            # Увеличиваем timeout для видео (60 секунд для больших видео)
            original_timeout = self.timeout
            # Для видео нужен больший timeout, особенно для больших файлов
            self.timeout = max(60, original_timeout)
            
            try:
                with open(video_path, "rb") as video_file:
                    files = {"video": video_file}
                    data = {"chat_id": chat_id, "supports_streaming": True}
                    if caption:
                        data["caption"] = caption
                    data.update(kwargs)
                    response = self._request("sendVideo", data=data, files=files)
                    return bool(response)
            finally:
                # Восстанавливаем оригинальный timeout
                self.timeout = original_timeout
        except FileNotFoundError as exc:
            record_integration_error("telegram", "file_missing", str(exc), severity="warning")
            logger.error("❌ TelegramClient.send_video: %s", exc)
            return False
        except Exception as exc:
            record_integration_error("telegram", "send_video_error", str(exc), severity="warning")
            logger.error("❌ TelegramClient.send_video: %s", exc)
            return False


def get_telegram_client() -> TelegramClient:
    return TelegramClient()

