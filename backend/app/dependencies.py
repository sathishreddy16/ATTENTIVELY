from functools import lru_cache

from app.config import Settings, get_settings
from app.services.storage import AudioStorage, build_storage


@lru_cache
def get_storage() -> AudioStorage:
    return build_storage(get_settings())


def settings_dependency() -> Settings:
    return get_settings()
