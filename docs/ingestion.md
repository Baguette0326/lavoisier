# Ingestion and Extraction

CarbonSense stages source data for human review before it can enter the approved screening workflow. The first ingestion layer is deterministic and supports CSV plus blank-line-separated structured text. It does not call external APIs, scrape sources, convert units, merge material aliases, or write to `data/approved`.

## Data flow

```text
source text -> deterministic extraction -> pending candidates -> human review -> separate approval workflow
```

Each extraction candidate retains:

- the raw field name and value;
- a proposed canonical field, or no mapping when the label is unknown;
- a conservatively parsed scalar value;
- deterministic field-match confidence from 0 to 1;
- source name, source type, SHA-256 content hash, and row/line locator;
- source unit, canonical unit, quantity kind, and unit-review status;
- a human approval status, initially `pending`.

Confidence describes only the deterministic field-label match. It is not scientific confidence, measurement uncertainty, source quality, or permission to approve a record.

## CSV

```python
from carbonsense.ingestion import extract_csv

batch = extract_csv(csv_text, "materials.csv")
```

CSV headers must be nonblank and unique. Rows with the wrong number of values are skipped with a warning rather than padded or truncated. Unknown columns remain visible as candidates with no canonical mapping. Callers may provide an explicit `column_mapping` dictionary; its targets must be known canonical fields.

## Structured text

```python
from carbonsense.ingestion import extract_structured_text

batch = extract_structured_text(notes_text, "lab-notes.txt")
```

Records are separated by blank lines. Within a record, only `key: value` and `key=value` lines are recognized. Duplicate candidates are retained and flagged for human resolution.

## Unit safety

Numeric values may be parsed, but units are never converted in this layer. An exact unit is marked `exact`; a missing unit is marked `missing`; a different or unrecognized unit is marked `requires_review`. The original value and unit remain available for review.

## PDF boundary

PDF support is deliberately deferred. A future adapter should first classify PDFs as text-native or scanned, preserve page and bounding-box provenance, record the extraction tool and version, and emit the same candidate models. OCR or table extraction must not bypass licence review or human approval, and extracted text should never be treated as ground truth without checking it against the rendered page.
