"""Small persistent artifact repository for headless JSON clients."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List
import uuid

from core.settings import get_settings


class ArtifactNotFoundError(KeyError):
    pass


class ArtifactService:
    def __init__(self, artifact_dir: Path = None):
        self.artifact_dir = Path(artifact_dir or get_settings().artifact_dir).resolve()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name: str, content: str, artifact_type: str = "input", metadata=None) -> Dict[str, Any]:
        artifact_id = f"art_{uuid.uuid4().hex}"
        record = {
            "artifact_id": artifact_id,
            "name": Path(name).name,
            "type": artifact_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        target = self.artifact_dir / f"{artifact_id}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        temporary.replace(target)
        return {key: value for key, value in record.items() if key != "content"}

    def get(self, artifact_id: str) -> Dict[str, Any]:
        if not artifact_id.startswith("art_") or not artifact_id[4:].isalnum():
            raise ArtifactNotFoundError(artifact_id)
        target = self.artifact_dir / f"{artifact_id}.json"
        if not target.is_file():
            raise ArtifactNotFoundError(artifact_id)
        return json.loads(target.read_text(encoding="utf-8"))

    def as_file_info(self, artifact_ids: Iterable[str]):
        from pipeline.pipeline_models import FileInfo

        files: List[FileInfo] = []
        for artifact_id in artifact_ids:
            record = self.get(artifact_id)
            files.append(FileInfo(
                name=record["name"],
                content=record["content"],
                type=record.get("type"),
            ))
        return files
