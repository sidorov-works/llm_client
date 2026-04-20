# LLM Client

Унифицированный асинхронный клиент для работы с LLM API (DeepSeek, OpenAI, Ollama и др.).

## Особенности

- Единый интерфейс для разных LLM провайдеров
- Асинхронный (asyncio)
- Автоматические повторные попытки при сбоях (через `http-utils`)
- Pydantic валидация конфигов
- Поддержка контекстного менеджера

## Установка

```bash
pip install git+https://github.com/sidorov-works/llm-client.git@v0.1.0
```

## Быстрый старт

```python
from llm_client import DeepSeekClient, DeepSeekConfig, user_message, system_message

# Создание клиента
config = DeepSeekConfig(api_key="sk-xxx")
client = DeepSeekClient(config)

# Подготовка сообщений
messages = [
    system_message("Ты полезный ассистент"),
    user_message("Что такое Python?")
]

# Запрос
answer = await client.generate(messages)
print(answer)

# Закрытие
await client.close()
```

## Использование с контекстным менеджером

```python
async with DeepSeekClient(config) as client:
    answer = await client.generate(messages)
```

## Создание сообщений

```python
from llm_client import user_message, system_message, assistant_message

messages = [
    system_message("Инструкция для системы"),
    user_message("Вопрос пользователя"),
    assistant_message("Предыдущий ответ")
]
```

## Конфигурация

```python
config = DeepSeekConfig(
    api_key="sk-xxx",
    model="deepseek-chat",
    temperature=0.6,
    max_tokens=1024,
    timeout_total=60.0,
    max_retries=3
)
```

## Доступные клиенты

| Клиент | Статус |
|--------|--------|
| DeepSeekClient | ✅ Готов |
| OpenAIClient | 🚧 В планах |
| OllamaClient | 🚧 В планах |
| TGIClient | 🚧 В планах |

## Бизнес-логика

Для подготовки сложных промптов используйте отдельные классы, принимающие `BaseLLMClient`:

```python
class SupportAgent:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client
    
    async def answer_ticket(self, ticket):
        messages = self._prepare_messages(ticket)
        return await self.llm.generate(messages)
```

## Требования

- Python >= 3.9
- http-utils (автоматически устанавливается)

## Лицензия

MIT