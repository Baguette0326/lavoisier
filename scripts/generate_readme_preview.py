"""Generate a static README preview image from Lavoisier report outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RANKED_RECORDS = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
FALLBACK_RANKED_RECORDS = PROJECT_ROOT / "reports" / "backend_fixture_export" / "ranked_records.csv"
VIRTUAL_LAB_SUMMARY = PROJECT_ROOT / "reports" / "virtual_lab_demo" / "demo_summary.csv"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "assets" / "lavoisier-preview.png"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: object, font, fill: str = "#17201f") -> None:
    draw.text(xy, str(value), font=font, fill=fill)


def chip(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str, fill: str) -> None:
    font = load_font(22, bold=True)
    x, y = xy
    bbox = draw.textbbox((0, 0), label, font=font)
    width = bbox[2] - bbox[0] + 34
    draw.rounded_rectangle((x, y, x + width, y + 40), radius=18, fill=fill)
    text(draw, (x + 17, y + 7), label, font, "#17312e")


def draw_table(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    headers: list[str],
    rows: list[list[str]],
    widths: list[int],
) -> int:
    header_font = load_font(22, bold=True)
    body_font = load_font(21)
    row_h = 48
    draw.rounded_rectangle((x, y, x + sum(widths), y + row_h * (len(rows) + 1)), radius=8, fill="#ffffff")
    draw.rectangle((x, y, x + sum(widths), y + row_h), fill="#e9f0ef")
    cursor = x
    for header, width in zip(headers, widths, strict=True):
        text(draw, (cursor + 16, y + 12), header, header_font, "#223633")
        cursor += width
    for row_idx, row in enumerate(rows, start=1):
        row_y = y + row_h * row_idx
        if row_idx % 2 == 0:
            draw.rectangle((x, row_y, x + sum(widths), row_y + row_h), fill="#f7faf9")
        cursor = x
        for value, width in zip(row, widths, strict=True):
            text(draw, (cursor + 16, row_y + 12), value, body_font, "#243331")
            cursor += width
    draw.rounded_rectangle((x, y, x + sum(widths), y + row_h * (len(rows) + 1)), radius=8, outline="#d0dcd9", width=2)
    return y + row_h * (len(rows) + 1)


def fmt(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def main() -> None:
    ranked_path = RANKED_RECORDS if RANKED_RECORDS.exists() else FALLBACK_RANKED_RECORDS
    ranked = pd.read_csv(ranked_path).head(5)
    lab = pd.read_csv(VIRTUAL_LAB_SUMMARY) if VIRTUAL_LAB_SUMMARY.exists() else pd.DataFrame()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (1600, 1160), "#f3f7f6")
    draw = ImageDraw.Draw(image)
    title_font = load_font(60, bold=True)
    subtitle_font = load_font(28)
    section_font = load_font(31, bold=True)
    small_font = load_font(22)
    metric_font = load_font(38, bold=True)

    draw.rounded_rectangle((56, 50, 1544, 250), radius=18, fill="#dfecea", outline="#c5d8d4", width=2)
    text(draw, (92, 78), "Lavoisier", title_font, "#17312e")
    text(
        draw,
        (94, 154),
        "Carbon-capture MOF screening with controlled comparisons, provenance, and reviewable ML triage.",
        subtitle_font,
        "#243c39",
    )
    chip(draw, (94, 204), "CRAFTED GCMC slice", "#cfe3df")
    chip(draw, (350, 204), "CoRE MOF provenance", "#dbe9f7")
    chip(draw, (628, 204), "Target-specific ML", "#e7e3f5")
    chip(draw, (868, 204), "Reviewable exports", "#ece6d7")

    metric_specs = [
        ("Ranked records", len(ranked)),
        ("Top score", fmt(ranked["screening_score"].max(), 3) if "screening_score" in ranked else "n/a"),
        ("Evidence type", "GCMC"),
        ("Candidate checks", len(lab) if not lab.empty else "n/a"),
    ]
    for idx, (label, value) in enumerate(metric_specs):
        x = 56 + idx * 372
        draw.rounded_rectangle((x, 285, x + 340, 395), radius=10, fill="#ffffff", outline="#d4dfdc", width=2)
        text(draw, (x + 24, 306), label, small_font, "#61716e")
        text(draw, (x + 24, 336), value, metric_font, "#17312e")

    text(draw, (56, 435), "Ranked MOF Screening", section_font, "#17201f")
    table_rows = []
    for _, row in ranked.iterrows():
        table_rows.append(
            [
                str(row.get("material_id", ""))[:14],
                fmt(row.get("screening_score"), 3),
                fmt(row.get("co2_uptake_mmol_g"), 2),
                fmt(row.get("co2_n2_selectivity"), 1),
                str(row.get("core_match_status", "n/a")).replace("_", " ")[:22],
            ]
        )
    bottom = draw_table(
        draw,
        56,
        485,
        ["Material", "Score", "CO2 uptake", "CO2/N2 sel.", "Provenance"],
        table_rows,
        [240, 160, 210, 210, 390],
    )

    text(draw, (56, bottom + 48), "Candidate Virtual Lab", section_font, "#17201f")
    lab_rows = []
    for _, row in lab.head(3).iterrows():
        lab_rows.append(
            [
                str(row.get("material_id", ""))[:31],
                str(row.get("final_decision", "")).replace("_", " ")[:32],
                str(row.get("review_confidence", "")),
            ]
        )
    draw_table(
        draw,
        56,
        bottom + 98,
        ["Candidate", "Decision", "Confidence"],
        lab_rows or [["Demo candidates", "Run scripts/run_virtual_lab_demo.py", "n/a"]],
        [480, 520, 210],
    )

    text(
        draw,
        (56, 1090),
        "Generated from local report outputs. Computational screening aid only; not experimental validation.",
        small_font,
        "#61716e",
    )
    image.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
