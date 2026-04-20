# src/llm_client/base_client.py
"""
Базовый абстрактный класс для всех LLM клиентов.

Этот модуль определяет ТОЛЬКО интерфейс. Никакой конкретной реализации
HTTP-клиентов, SSL, retry-логики здесь нет. Каждый конкретный клиент
(DeepSeek, OpenAI, Ollama, TGI) сам решает, как делать запросы.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """
    Стандартизированный ответ от LLM.
    
    Используется внутри клиентов для единообразного возврата результата.
    Клиентский код получает либо строку (через generate), либо может
    запросить расширенную информацию через этот датакласс.
    
    Attributes:
        content: Текст ответа LLM (основное содержимое)
        usage: Информация о потреблении токенов, если API её предоставляет
               Пример: {"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200}
        latency_ms: Время выполнения запроса в миллисекундах (полезно для мониторинга)
    """
    content: str
    usage: Optional[Dict[str, int]] = None
    latency_ms: float = 0.0


class BaseLLMClient(ABC):
    """
    Абстрактный базовый класс для всех LLM клиентов.
    
    Этот класс определяет ТОЛЬКО КОНТРАКТ (какие методы должны быть у клиента).
    Он не содержит:
    - HTTP клиентов (aiohttp, httpx, requests)
    - SSL контекстов
    - Retry логики
    - Таймаутов
    - Сессий
    
    Потому что:
    - Ollama может быть локальной командой (без HTTP вообще)
    - TGI может использовать gRPC вместо HTTP
    - Разные API требуют разной логики повторных попыток
    - Клиентский код не должен зависеть от этих деталей
    
    Каждый наследник реализует generate() так, как нужно конкретному API.
    
    Пример использования:
    
        # Клиентский код работает с абстракцией, не зная деталей
        client: BaseLLMClient = DeepSeekClient(api_key="...")
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]
        
        answer = await client.generate(messages)
        await client.close()
    """
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Optional[str]:
        """
        Генерация ответа от LLM.
        
        Это ЕДИНСТВЕННЫЙ метод, который нужен клиентскому коду.
        Он принимает сообщения в стандартном формате и возвращает текст ответа.
        
        Args:
            messages: Список сообщений в стандартизированном формате.
                     Все конкретные клиенты должны поддерживать этот формат.
                     
                     Формат сообщения:
                     {
                         "role": "system" | "user" | "assistant",
                         "content": "текст сообщения"
                     }
                     
                     Примеры:
                     # Простой запрос
                     [{"role": "user", "content": "What is AI?"}]
                     
                     # С системным промптом
                     [
                         {"role": "system", "content": "You are a Python expert"},
                         {"role": "user", "content": "How to use async/await?"}
                     ]
                     
                     # С историей диалога
                     [
                         {"role": "user", "content": "Hello"},
                         {"role": "assistant", "content": "Hi there!"},
                         {"role": "user", "content": "How are you?"}
                     ]
            
            **kwargs: Дополнительные параметры генерации.
                     Каждый клиент сам решает, какие параметры поддерживает.
                     
                     Общие параметры (по договорённости):
                     - temperature: float (0.0 - 2.0) - креативность ответа
                     - max_tokens: int - максимальная длина ответа
                     - top_p: float - альтернатива temperature
                     - stop: List[str] - стоп-слова
                     
                     Пример:
                     answer = await client.generate(
                         messages,
                         temperature=0.8,
                         max_tokens=500
                     )
        
        Returns:
            str: Текст ответа LLM или None, если произошла ошибка.
                 None возвращается вместо исключения, потому что в продакшене
                 ошибки LLM (таймауты, rate limits, недоступность) - это
                 ожидаемая ситуация, а не исключительная.
                 
                 Воркер, получив None, может:
                 - Отправить запрос в эскалацию
                 - Использовать fallback модель
                 - Повторить запрос позже
        
        Raises:
            Этот метод НЕ должен выбрасывать исключения в обычных ситуациях.
            Исключения возможны только при критических ошибках:
            - Неверный API ключ (бесполезно повторять)
            - Неверный формат messages (ошибка программиста)
            - Некорректная конфигурация (нельзя восстановиться)
            
            Временные ошибки (таймаут, 429, 5xx) обрабатываются ВНУТРИ клиента
            с помощью retry-логики, а клиентский код получает либо ответ,
            либо None после всех попыток.
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Освобождение ресурсов, занятых клиентом.
        
        Должен быть вызван перед завершением работы воркера.
        
        Что делает в разных реализациях:
        - DeepSeekClient: закрывает HTTP сессию (aiohttp.ClientSession)
        - OllamaClient: может ничего не делать (нет ресурсов)
        - TGRemoteClient: закрывает gRPC канал
        
        Важно вызывать этот метод в finally блоке или через контекстный менеджер,
        чтобы избежать утечки соединений.
        
        Пример правильного использования:
        
            client = DeepSeekClient(api_key="...")
            try:
                answer = await client.generate(messages)
                # обработать answer
            finally:
                await client.close()
        
        Или через контекстный менеджер (если наследник его поддерживает):
        
            async with DeepSeekClient(api_key="...") as client:
                answer = await client.generate(messages)
        """
        pass
    
    # Опционально: контекстный менеджер, но не требует реализации в ABC
    # Каждый наследник может реализовать __aenter__ и __aexit__ сам
    
    async def __aenter__(self):
        """
        Вход в контекстный менеджер.
        
        Не является абстрактным методом. Наследники могут переопределить
        для поддержки async with.
        
        По умолчанию просто возвращает self.
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Выход из контекстного менеджера.
        
        Вызывает close() по умолчанию.
        """
        await self.close()