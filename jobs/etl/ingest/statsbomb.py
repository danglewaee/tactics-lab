from pydantic import BaseModel, Field

from config import ETLSettings


class ProviderManifest(BaseModel):
    provider: str
    raw_root: str
    processed_root: str
    expected_entities: list[str] = Field(default_factory=list)


def build_manifest(settings: ETLSettings) -> ProviderManifest:
    return ProviderManifest(
        provider=settings.provider_code,
        raw_root=settings.raw_data_root,
        processed_root=settings.processed_data_root,
        expected_entities=["competitions", "matches", "lineups", "events"],
    )

