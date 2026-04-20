# src/llm_client/standard.py

from enum import Enum
from typing import Dict


class StandardRole(str, Enum):
    """Унифицированные названия ролей"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class StandardField(str, Enum):
    """Унифицированные названия полей"""
    ROLE = "role"
    CONTENT = "content"


def _create_message(role: StandardRole, content: str) -> Dict[str, str]:
    """Создаёт сообщение в унифицированном формате"""
    return {
        StandardField.ROLE: role,
        StandardField.CONTENT: content
    }


# Хелперы для удобства
def user_message(content: str) -> Dict[str, str]:
    return _create_message(StandardRole.USER, content)


def system_message(content: str) -> Dict[str, str]:
    return _create_message(StandardRole.SYSTEM, content)


def assistant_message(content: str) -> Dict[str, str]:
    return _create_message(StandardRole.ASSISTANT, content)