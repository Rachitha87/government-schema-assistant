# Knowledge Base

`schemes.jsonl` is the entire knowledge base of this project.

## Format

**JSONL** = one JSON object per line. It was chosen over a single JSON array
because it is easy to read, easy to diff in Git, and easy to append to
(a new scheme is one new line - no comma/bracket mistakes).

Each line has two groups of fields:

| Group | Fields | Used by |
|---|---|---|
| Human readable | `name`, `provider`, `description`, `eligibility`, `income_limit`, `education_level`, `benefits`, `deadline`, `application_link` | RAG chunks, the LLM prompt, the UI cards |
| Structured filters | `min_age`, `max_age`, `gender`, `categories`, `max_annual_income`, `states`, `education_levels`, `course_keywords`, `student_status`, `disability_required`, `min_percentage` | The deterministic eligibility rule engine |
| Provenance | `data_status`, `notes`, `tags` | Banners, warnings, search |

Why both groups? The LLM reads the text, but eligibility is decided by the
structured numbers. That way the assistant can never quote a benefit the rule
engine has not seen, and it can never *invent* a criterion.

## ⚠️ Data status - read this

Every record in this file is marked:

```json
"data_status": "sample-unverified"
```

The scheme names, providers and portals are based on real, well-known Indian
government scholarship schemes, but the **income ceilings, benefit amounts and
deadlines in this file are illustrative sample values** that have **not** been
verified against the current official notification. Deadlines in particular
change every cycle.

Before this project is used for anything real:

1. Open the official portal for each scheme.
2. Read the latest official notification / guidelines PDF.
3. Replace `eligibility`, `income_limit`, `benefits`, `deadline` and the
   structured limits with the verified values.
4. Change `"data_status"` to `"officially-published"` and note the date you
   verified it in `notes`.

The UI reads `data_status` and shows a "Sample data" badge, so a record can
never be presented as verified until you say so.

`SCH012` is an **explicitly illustrative** record: it exists only to show how a
state-level scheme would be added, and its name/limits are placeholders.

## Adding a scheme

1. Append one line to `schemes.jsonl`.
2. Restart the backend (the knowledge base is read once at startup).
3. Check it appears: `curl http://127.0.0.1:8000/schemes/{new_id}`

A JSON array file (`schemes.json`) is also supported - the loader detects the
format automatically, so you can paste data from anywhere.
