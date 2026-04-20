# src/llm_client/deepseek_client.py

"""
DeepSeek API клиент.

Реализует BaseLLMClient для DeepSeek API с использованием RetryableHTTPClient.
"""

from typing import List, Dict, Optional, Any

from .base_client import BaseLLMClient
from http_utils import RetryableHTTPClient

from pydantic import BaseModel, Field, field_validator

import logging
logger = logging.getLogger(__name__)

class DeepSeekAPIConfig(BaseModel):
    """
    Параметры генерации -
    параметры, которые уходят в тело запроса к API
    """
    model_config = {
        "extra": "ignore",  # чтобы не сломаться, если клиентский код подкинет что-то "левое"
        "frozen": True      # неизменяемый после создания
    }

    model: str = "deepseek-chat"
    temperature: float = 0.6
    max_tokens: int = 1024
    top_p: float = 0.9
    frequency_penalty: float = 0.1
    presence_penalty: float = 0.1
    stop: Optional[List[str]] = ["\n--", "\n###"]


class DeepSeekClientConfig(BaseModel):
    """Конфигурация клиента"""
    api_key: str
    api_url: str = "https://api.deepseek.com/v1/chat/completions"
    timeout_total: float = 60.0
    max_retries: int = 3

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v:
            raise ValueError("API key is required")
        return v


class DeepSeekClient(BaseLLMClient):
    """
    Клиент для DeepSeek API.

    Отвечает ТОЛЬКО за взаимодействие с DeepSeek API:
    - Принимает сообщения в унифицированном формате
    - Отправляет запрос через RetryableHTTPClient с ретраями
    - Возвращает ответ или None при ошибке

    НЕ содержит бизнес-логики подготовки сообщений.

    Пример использования:

        from llm_client import DeepSeekClient, DeepSeekAPIConfig, DeepSeekClientConfig

        # Параметры API (идут в тело запроса)
        api_config = DeepSeekAPIConfig(
            model="deepseek-chat",
            temperature=0.6,
            max_tokens=1024
        )

        # Параметры клиента (настройки соединения)
        client_config = DeepSeekClientConfig(
            api_key="sk-xxx",
            api_url="https://api.deepseek.com/v1/chat/completions",
            timeout_total=60.0,
            max_retries=3
        )

        # Создание клиента
        client = DeepSeekClient(api_config, client_config)

        # Подготовка сообщений
        messages = [
            {"role": "system", "content": "Ты полезный ассистент"},
            {"role": "user", "content": "Что такое Python?"}
        ]

        # Запрос
        answer = await client.generate(messages)
        print(answer)

        # Освобождение ресурсов
        await client.close()
    """
    
    def __init__(self, api_config: DeepSeekAPIConfig, client_config: DeepSeekClientConfig):
        """
        Инициализация DeepSeek клиента.
        
        Args:
            api_config: Параметры генерации (DeepSeekAPIConfig)
            client_config: Параметры клиента (DeepSeekClientConfig)
                   Обязательно должен содержать api_key.
        """
        
        self._api_config = api_config
        self._client_config = client_config
        
        # Инициализируем HTTP клиент с ретраями
        # Используем RetryableHTTPClient из пакета http_utils
        self._http_client = RetryableHTTPClient(
            base_timeout=client_config.timeout_total,   # таймаут на один запрос
            max_retries=client_config.max_retries,      # количество повторных попыток
            base_delay=1.0,                             # начальная задержка 1 секунда
            max_delay=30.0,                             # максимум 30 секунд между попытками
            total_timeout=client_config.timeout_total   # общий таймаут на все попытки
        )
        
        logger.debug(f"DeepSeekClient initialized with model={api_config.model}")
    
    def _prepare_payload(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Подготовка payload для DeepSeek API.
        
        Преобразует унифицированные сообщения и параметры генерации
        в формат, который ожидает DeepSeek API.
        
        Args:
            messages: Сообщения в унифицированном формате
                      [{"role": "user", "content": "..."}]
            **kwargs: Параметры генерации (переопределяют config)
        
        Returns:
            Payload для отправки в DeepSeek API
        """
        # Базовый payload из конфига
        payload = {
            "model": self._api_config.model,
            "messages": messages,  # DeepSeek использует те же ключи "role"/"content"
            "temperature": kwargs.get("temperature", self._api_config.temperature),
            "max_tokens": kwargs.get("max_tokens", self._api_config.max_tokens),
            "top_p": kwargs.get("top_p", self._api_config.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self._api_config.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self._api_config.presence_penalty),
        }
        
        # Добавляем stop, если он указан
        stop = kwargs.get("stop", self._api_config.stop)
        if stop:
            payload["stop"] = stop
        
        # Удаляем None значения (чтобы не отправлять лишнего)
        payload = {k: v for k, v in payload.items() if v is not None}
        
        logger.debug(f"Prepared payload: model={payload['model']}, "
                    f"temperature={payload['temperature']}, "
                    f"max_tokens={payload['max_tokens']}")
        
        return payload
    
    def _extract_content(self, response_data: Dict[str, Any]) -> Optional[str]:
        """
        Извлечение текста ответа из сырого JSON DeepSeek API.
        
        Args:
            response_data: JSON ответа от DeepSeek API
        
        Returns:
            Текст ответа или None, если ответ не содержит choices
        
        Raises:
            ValueError: Если ответ имеет неожиданный формат
        """
        if not response_data.get("choices"):
            logger.error("Invalid API response: missing 'choices'")
            raise ValueError("Malformed API response: no choices")
        
        choice = response_data["choices"][0]
        
        if not choice.get("message"):
            logger.error("Invalid API response: missing 'message' in choice")
            raise ValueError("Malformed API response: no message in choice")
        
        content = choice["message"].get("content")
        
        if content is None:
            logger.warning("API response has empty content")
            return None
        
        # Логируем использование токенов, если есть
        if response_data.get("usage"):
            usage = response_data["usage"]
            logger.debug(f"Token usage: prompt={usage.get('prompt_tokens')}, "
                        f"completion={usage.get('completion_tokens')}, "
                        f"total={usage.get('total_tokens')}")
        
        return content
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Optional[str]:
        """
        Генерация ответа от DeepSeek API.
        
        Args:
            messages: Сообщения в унифицированном формате.
                     Каждое сообщение должно содержать ключи "role" и "content".
                     
                     Поддерживаемые роли:
                     - "system" - системные инструкции
                     - "user" - сообщения пользователя
                     - "assistant" - предыдущие ответы ассистента (история)
            
            **kwargs: Параметры генерации (переопределяют настройки из config):
                     - temperature: float (0.0-2.0)
                     - max_tokens: int
                     - top_p: float (0.0-1.0)
                     - frequency_penalty: float (-2.0 до 2.0)
                     - presence_penalty: float (-2.0 до 2.0)
                     - stop: List[str]
        
        Returns:
            str: Текст ответа или None при ошибке.
                 None возвращается при:
                 - Сетевых ошибках (после всех ретраев)
                 - Таймаутах
                 - Ошибках API (кроме критических, которые вызывают исключение)
        
        Raises:
            ValueError: Если messages имеет неверный формат
            Exception: При критических ошибках (неверный API ключ и т.п.)
        
        Example:
            >>> messages = [
            ...     {"role": "system", "content": "Ты оператор техподдержки"},
            ...     {"role": "user", "content": "Как оплатить заказ?"}
            ... ]
            >>> answer = await client.generate(messages, temperature=0.5)
        """
        # Валидация входных данных
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        # Подготовка payload
        payload = self._prepare_payload(messages, **kwargs)
        
        # Заголовки запроса
        headers = {
            "Authorization": f"Bearer {self._client_config.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"Sending request to {self._client_config.api_url}")
        
        try:
            # Выполняем запрос с автоматическими ретраями
            response = await self._http_client.post_with_retry(
                url=self._client_config.api_url,
                headers=headers,
                json=payload,
                success_statuses={200}
            )
            
            # Парсим ответ
            data = response.json()
            content = self._extract_content(data)
            
            logger.debug(f"Successfully generated response ({len(content) if content else 0} chars)")
            return content
            
        except Exception as e:
            # Логируем ошибку, но не пробрасываем (кроме критических)
            # Возвращаем None - клиентский код сам решит, что делать
            logger.error(f"Failed to generate response: {type(e).__name__}: {e}")
            return None
    
    async def close(self) -> None:
        """
        Освобождение ресурсов.
        
        Закрывает HTTP клиент и все открытые соединения.
        Обязательно вызывать перед завершением работы.
        """
        logger.debug("Closing DeepSeekClient")
        await self._http_client.close()
    
    async def __aenter__(self):
        """Поддержка async with контекста"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста"""
        await self.close()