import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class YandexWebmasterClient:
    """
    Унифицированный клиент для работы с API Яндекс.Вебмастер.
    """

    base_url: str = "https://api.webmaster.yandex.net/v4"

    def __init__(
        self,
        *,
        token: Optional[str] = None,
        user_id: Optional[str] = None,
        host_id: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.token = token or getattr(settings, "YANDEX_WEBMASTER_TOKEN", "")
        self.user_id = user_id or getattr(settings, "YANDEX_WEBMASTER_USER_ID", "")
        self.host_id = host_id or getattr(settings, "YANDEX_WEBMASTER_HOST_ID", "")
        self.session = session or requests.Session()

    # --------------------------------------------------------------------- #
    # Общие утилиты
    # --------------------------------------------------------------------- #
    @property
    def configured(self) -> bool:
        """
        Проверяет наличие обязательных параметров.
        """
        return bool(self.token and self.user_id and self.host_id)

    def _make_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"OAuth {self.token}",
            "Content-Type": "application/json",
        }

    def _build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        Отправляет запрос к API Яндекс.Вебмастер.
        """
        if not self.configured:
            raise ValueError("Yandex Webmaster credentials are not configured")

        url = self._build_url(path)
        headers = kwargs.pop("headers", {})
        headers = {**self._make_headers(), **headers}

        response = self.session.request(method.upper(), url, headers=headers, timeout=30, **kwargs)
        return response

    # --------------------------------------------------------------------- #
    # Основные операции
    # --------------------------------------------------------------------- #
    def enqueue_recrawl(self, url: str) -> Dict[str, Any]:
        """
        Добавляет URL в очередь переобхода (recrawl queue).
        """
        if not self.configured:
            logger.warning("Yandex Webmaster credentials not configured")
            return {"success": False, "error": "not_configured"}

        payload = {"url": url}

        try:
            response = self._request(
                "post",
                f"user/{self.user_id}/hosts/{self.host_id}/recrawl/queue",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json() if response.content else {}
                logger.info("✅ URL добавлен в очередь переобхода Яндекса: %s", url)
                return {
                    "success": True,
                    "task_id": data.get("task_id"),
                    "response": data,
                }

            logger.error(
                "❌ Ошибка Яндекс.Вебмастер (%s): %s",
                response.status_code,
                response.text,
            )
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
            }
        except requests.RequestException as exc:
            logger.error("❌ Ошибка сети при обращении к Яндекс.Вебмастер: %s", exc)
            return {"success": False, "error": str(exc)}

    def fetch_404_urls(self) -> List[str]:
        """
        Возвращает список URL-адресов с ошибкой 404 по данным Яндекс.Вебмастер.
        """
        if not self.configured:
            logger.warning("Yandex Webmaster credentials not configured")
            return []

        try:
            response = self._request(
                "get",
                f"user/{self.user_id}/hosts/{self.host_id}/diagnostics/errors",
                params={"error_type": "HTTP_4XX"},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                urls = [item.get("url") for item in data.get("errors", []) if item.get("url")]
                logger.info("ℹ️ Получено %s URL с ошибкой 404 из Яндекс.Вебмастер", len(urls))
                return urls

            logger.error(
                "❌ Не удалось получить список 404 из Яндекс.Вебмастер (%s): %s",
                response.status_code,
                response.text,
            )
            return []
        except requests.RequestException as exc:
            logger.error("❌ Ошибка сети при получении 404 URL из Яндекс.Вебмастер: %s", exc)
            return []

    def ping_sitemap(self, sitemap_url: str) -> Dict[str, Any]:
        """
        Отправляет ping с адресом sitemap в Яндекс.Вебмастер.
        """
        endpoint = "https://webmaster.yandex.ru/ping"
        params = {"sitemap": sitemap_url}

        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            success = response.status_code == 200

            if success:
                logger.info("✅ Yandex уведомлён об обновлении sitemap: %s", sitemap_url)
            else:
                logger.error(
                    "❌ Ошибка ping sitemap (%s): %s",
                    response.status_code,
                    response.text,
                )

            return {
                "success": success,
                "status_code": response.status_code,
                "response": response.text,
            }
        except requests.RequestException as exc:
            logger.error("❌ Сетевая ошибка при ping sitemap Яндекс: %s", exc)
            return {"success": False, "error": str(exc)}


@lru_cache
def get_yandex_webmaster_client() -> YandexWebmasterClient:
    """
    Возвращает синглтон-клиент для работы с Яндекс.Вебмастер.
    """
    return YandexWebmasterClient()

