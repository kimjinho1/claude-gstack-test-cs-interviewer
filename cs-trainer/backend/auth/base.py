from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OAuthUserInfo:
    provider: str
    provider_id: str
    email: str | None
    name: str | None
    avatar_url: str | None


class OAuthProvider(ABC):
    """새 프로바이더 추가 시 이 클래스를 상속받아 구현"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str, state: str) -> str: ...

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> dict: ...

    @abstractmethod
    async def get_user_info(self, tokens: dict) -> OAuthUserInfo: ...
