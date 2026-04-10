from dataclasses import dataclass
from os import getenv


@dataclass(slots=True)
class ETLSettings:
    provider_code: str = getenv("ETL_PROVIDER", "statsbomb")
    raw_data_root: str = getenv("RAW_DATA_ROOT", "data/raw")
    processed_data_root: str = getenv("PROCESSED_DATA_ROOT", "data/processed")
    database_url: str = getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tactics_lab")


def get_settings() -> ETLSettings:
    return ETLSettings()

