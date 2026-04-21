# LLM Client

Унифицированный асинхронный клиент для работы с LLM API.

## Особенности

- Единый интерфейс для разных LLM провайдеров
- Асинхронный (asyncio)
- Автоматические повторные попытки с экспоненциальной задержкой
- Pydantic валидация конфигов
- Поддержка контекстного менеджера
- Встроенные хелперы для создания сообщений

## Установка

```bash
pip install git+https://github.com/sidorov-works/llm-client.git@v0.1.7
```

## Быстрый старт

```python
from llm_client import DeepSeekClient, DeepSeekAPIConfig, DeepSeekClientConfig

# Конфигурация параметров API
api_config = DeepSeekAPIConfig(
    model="deepseek-chat",
    temperature=0.6,
    max_tokens=1024
)

# Конфигурация клиента
client_config = DeepSeekClientConfig(
    api_key="sk-xxx",
    timeout_total=60.0,
    max_retries=3
)

# Создание клиента
client = DeepSeekClient(api_config, client_config)

# Подготовка сообщений (через хелперы клиента)
messages = [
    client.system_message("Ты полезный ассистент"),
    client.user_message("Что такое Python?")
]

# Запрос
answer = await client.generate(messages)
print(answer)

# Закрытие
await client.close()
```

## Использование с контекстным менеджером

```python
async with DeepSeekClient(api_config, client_config) as client:
    answer = await client.generate(messages)
```

## Хелперы для сообщений

Каждый клиент предоставляет статические методы для создания сообщений в правильном формате:

```python
system_msg = client.system_message("Ты помощник")
user_msg = client.user_message("Привет")
assistant_msg = client.assistant_message("Здравствуйте!")
```

При необходимости хелперы переопределяются в наследниках для поддержки специфичных форматов API.

## Конфигурация

### DeepSeekAPIConfig (параметры API)

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| model | str | "deepseek-chat" | Имя модели |
| temperature | float | 0.6 | Креативность (0.0-2.0) |
| max_tokens | int | 1024 | Макс. длина ответа |
| top_p | float | 0.9 | Альтернатива temperature |
| frequency_penalty | float | 0.1 | Штраф за повторы |
| presence_penalty | float | 0.1 | Штраф за повтор тем |
| stop | List[str] | ["\n--", "\n###"] | Стоп-слова |

### DeepSeekClientConfig (настройки клиента)

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| api_key | str | **обязательный** | API ключ |
| api_url | str | "https://api.deepseek.com/v1/chat/completions" | URL API |
| timeout_total | float | 60.0 | Общий таймаут (сек) |
| max_retries | int | 3 | Кол-во повторных попыток |

## Доступные клиенты

| Клиент | Статус |
|--------|--------|
| DeepSeekClient | ✅ Готов |
| OpenAIClient | 🚧 В планах |
| OllamaClient | 🚧 В планах |

## Создание собственного клиента

```python
from llm_client import BaseLLMClient

class MyCustomClient(BaseLLMClient):
    @staticmethod
    def user_message(content: str) -> Dict[str, str]:
        # Переопределяем формат если нужно
        return {"speaker": "human", "text": content}
    
    async def generate(self, messages, **kwargs):
        # Реализация запроса к API
        pass
    
    async def close(self):
        # Освобождение ресурсов
        pass
```

## Требования

- Python >= 3.9
- http-utils (автоматически устанавливается)
- pydantic >= 2.0

## Лицензия

MIT