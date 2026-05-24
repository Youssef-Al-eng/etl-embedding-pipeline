"""
CheckpointManager — Persist completed batch indices to disk.
Enables resume-from-failure across pipeline runs.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("pipeline.checkpoint")


class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.dir = Path(checkpoint_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, file_id: str) -> Path:
        return self.dir / f"{file_id}.json"

    def load(self, file_id: str) -> set[int]:
        """Return set of already-completed batch indices."""
        p = self._path(file_id)
        if p.exists():
            try:
                data = json.loads(p.read_text())
                return set(data.get("done_batches", []))
            except Exception as e:
                logger.warning(f"Could not read checkpoint '{p}': {e}")
        return set()

    def save(self, file_id: str, batch_idx: int):
        """Mark a batch index as completed."""
        done = self.load(file_id)
        done.add(batch_idx)
        p = self._path(file_id)
        p.write_text(json.dumps({"done_batches": sorted(done)}, indent=2))

    def clear(self, file_id: str):
        p = self._path(file_id)
        if p.exists():
            p.unlink()

    def clear_all(self):
        for f in self.dir.glob("*.json"):
            f.unlink()
        logger.info("Checkpoints cleared after successful run.")
