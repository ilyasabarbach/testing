import json
from pathlib import Path

from pydantic import BaseModel


class ReportWriteError(Exception):
    pass


def write_report_json(download_directory: str, report: BaseModel) -> None:
    report_path = Path(download_directory) / "report.json"

    try:
        report_path.write_text(
            json.dumps(report.model_dump(), indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ReportWriteError("Failed to write download report.") from exc
