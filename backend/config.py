"""
config.py
---------
Uygulamanın yapılandırma ayarlarını yönetir. Örneğin, veritabanı bağlantı bilgileri,
model API endpoint’leri, environment değişkenleri gibi bilgiler burada tutulabilir.
"""

from core.settings import get_settings

_settings = get_settings()
MONGO_URI = _settings.mongo_uri
DATABASE_NAME = _settings.database_name
MODEL_API_BASE_URL = _settings.model_api_base_url
MODEL_IDENTIFIER = _settings.model_identifier
MODEL_API_KEY = _settings.model_api_key
