"""API settings from the environment (API-001 §7). Secrets are never logged."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from homedesign.model.paths import is_canonical_uuid


class ConfigError(ValueError):
    """The server refuses to start with this configuration."""


@dataclass(frozen=True)
class Settings:
    preview_key: bytes = field(repr=False)
    store: str = "postgres"  # postgres | memory
    database_url: str | None = field(default=None, repr=False)
    dev_tokens: Mapping[str, str] = field(default_factory=dict, repr=False)  # token -> actor UUID
    cors_origins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.preview_key) < 32:
            raise ConfigError("HOMEDESIGN_PREVIEW_KEY must be at least 32 bytes (D047).")
        if self.store not in ("postgres", "memory"):
            raise ConfigError("HOMEDESIGN_STORE must be 'postgres' or 'memory'.")
        if self.store == "postgres" and not self.database_url:
            raise ConfigError("HOMEDESIGN_DATABASE_URL is required when HOMEDESIGN_STORE=postgres.")
        for token, actor in self.dev_tokens.items():
            if not token or not is_canonical_uuid(actor):
                raise ConfigError("HOMEDESIGN_DEV_TOKENS entries must be token=<canonical actor UUID>.")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        raw_key = env.get("HOMEDESIGN_PREVIEW_KEY", "")
        if not raw_key:
            raise ConfigError("HOMEDESIGN_PREVIEW_KEY is required (D047).")
        try:
            key = bytes.fromhex(raw_key)
        except ValueError as exc:
            raise ConfigError("HOMEDESIGN_PREVIEW_KEY must be hex-encoded.") from exc
        tokens: dict[str, str] = {}
        for entry in filter(None, (e.strip() for e in env.get("HOMEDESIGN_DEV_TOKENS", "").split(","))):
            token, sep, actor = entry.partition("=")
            if not sep:
                raise ConfigError("HOMEDESIGN_DEV_TOKENS entries must be token=<actor UUID>.")
            tokens[token.strip()] = actor.strip()
        origins = tuple(filter(None, (o.strip() for o in env.get("HOMEDESIGN_CORS_ORIGINS", "").split(","))))
        return cls(
            preview_key=key,
            store=env.get("HOMEDESIGN_STORE", "postgres"),
            database_url=env.get("HOMEDESIGN_DATABASE_URL") or None,
            dev_tokens=tokens,
            cors_origins=origins,
        )
