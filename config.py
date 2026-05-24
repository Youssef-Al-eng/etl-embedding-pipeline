"""
Pipeline Configuration
Loads from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field


@dataclass
class PipelineConfig:
    # Paths
    data_dir: str = os.getenv("DATA_DIR", "data")
    checkpoint_dir: str = os.getenv("CHECKPOINT_DIR", "checkpoints")
    output_dir: str = os.getenv("OUTPUT_DIR", "output")
    log_dir: str = os.getenv("LOG_DIR", "logs")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Batching
    batch_size: int = int(os.getenv("BATCH_SIZE", "100"))
    max_concurrent: int = int(os.getenv("MAX_CONCURRENT", "5"))

    # Retry / recovery
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay: float = float(os.getenv("RETRY_DELAY", "1.0"))

    # Cleaning
    min_text_length: int = int(os.getenv("MIN_TEXT_LENGTH", "10"))
    drop_duplicate_rows: bool = os.getenv("DROP_DUPLICATES", "true").lower() == "true"
    fill_numeric_na: str = os.getenv("FILL_NUMERIC_NA", "mean")   # mean | median | zero
    text_columns: list = field(default_factory=list)               # auto-detected if empty

    def __post_init__(self):
        import os
        for d in [self.data_dir, self.checkpoint_dir, self.output_dir, self.log_dir]:
            os.makedirs(d, exist_ok=True)
