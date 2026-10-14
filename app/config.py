# Copyright 2025 Roblox Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for the Sentinel FastAPI application."""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime settings from SENTINEL_* environment variables (this API, not upstream Sentinel)."""

    # SENTINEL_AUTO_LOAD_BANKS_PATH: saved-bank directory; loaded at startup if set.
    auto_load_banks_path: Optional[str] = None

    # SENTINEL_DEFAULT_TOP_K: nearest neighbors per bank; overridable via POST /score `top_k`.
    default_top_k: int = 5
    # SENTINEL_DEFAULT_MIN_SCORE: zero out weaker per-message scores; overridable via `min_score_to_consider`.
    default_min_score: float = 0.1
    # SENTINEL_DEFAULT_MIN_SIZE_OF_SCORES: min messages for skewness aggregation; not overridable per request.
    default_min_size_of_scores: int = 5

    class Config:
        env_prefix = "SENTINEL_"
        case_sensitive = False


# Global settings instance
settings = Settings()
