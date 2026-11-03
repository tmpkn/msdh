# Schema: symptoms

The patient's experience over time. Narrative in dated journal files,
structure in one log table.

## `symptoms/log.csv`

One row per symptom report. Append-only in spirit: a symptom that changes
gets a new row with a new date, the old row stays.

```
date,symptom,severity,duration,status,notes,source
```

| Column | Values |
|---|---|
| `date` | Date the report applies to |
| `symptom` | Lowercase short name, consistent across rows: `headache`, `fatigue`, `palpitations`. Reuse existing names; check before inventing |
| `severity` | 0 to 10 as the patient rates it, or empty |
| `duration` | How long it has been present at this report: `3 days`, `2 weeks`, `since 2024`, or empty |
| `status` | `new`, `ongoing`, `improving`, `worsening`, `resolved` |
| `notes` | Character, triggers, timing, what helps |
| `source` | Repo path of the chat, journal entry or visit where it was reported |

`msdh.py symptoms` lists distinct symptom names so that agents reuse them.

## `symptoms/YYYY-MM-DD_slug.md`

A journal entry. Written when the patient describes how they have been, in
a visit or in passing. Frontmatter: common keys with `type: symptom`,
`author_kind: patient` (the content is the patient's account), `author:
patient`, `source: none` or the chat file it came from.

Body is free text, the patient's account lightly edited, followed by:

```
## Logged
- headache: severity 6, ongoing, worse mornings  (one line per log.csv row added)
```

so that the narrative and the table can be reconciled.
