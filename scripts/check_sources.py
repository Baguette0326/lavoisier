"""Generate a local source-monitoring report from the registry."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.sources import load_source_registry, source_status_rows


def main() -> None:
    registry_path = PROJECT_ROOT / "config" / "source_registry.yaml"
    registry = load_source_registry(registry_path)
    rows = source_status_rows(registry)
    report_path = PROJECT_ROOT / "reports" / "source_monitoring_report.md"

    lines = ["# Source Monitoring Report", "", "This report lists source leads. It does not confirm dataset ingestion approval.", ""]
    for row in rows:
        lines.extend(
            [
                f"## {row['source_id']}",
                "",
                f"- Title: {row['title']}",
                f"- Reference: {row['reference']}",
                f"- Evidence type: {row['evidence_type']}",
                f"- Status: {row['status']}",
                "",
            ]
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    pd.DataFrame(rows).to_csv(PROJECT_ROOT / "reports" / "source_monitoring_report.csv", index=False)
    print(f"Wrote {report_path.relative_to(PROJECT_ROOT)}")
    print("Wrote reports/source_monitoring_report.csv")


if __name__ == "__main__":
    main()
