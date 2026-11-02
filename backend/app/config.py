from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    gemini_api_key: str                  
    llm_model: str = "gemini-3.5-flash"
    slack_webhook_url: str = ""
    admin_token: str = "change-me"
    cors_origins: str = "http://localhost:5173"
    model_cache: str = ".model_cache"
    prompt_version: str = "v2"
    top_k: int = 5
    min_retrieval_score: float = 0.5   
    min_confidence: float = 0.6       

settings = Settings()