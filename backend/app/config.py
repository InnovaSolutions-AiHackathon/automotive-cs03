from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Claude
    ANTHROPIC_API_KEY: str = "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"
    CLAUDE_MODEL: str = "claude-sonnet-3-20250514"

    # MySQL
    MYSQL_USER: str = "cs03_user"
    MYSQL_PASSWORD: str = "admin"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "automotive_cs03"

    # ChromaDB
    CHROMA_PATH: str = "./chroma_db"

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:4200"]
    SECRET_KEY: str = "changeme"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    class Config:
        env_file = ".env"

settings = Settings()