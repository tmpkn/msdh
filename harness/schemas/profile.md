# Schema: profile

Who the patient is. Created by onboarding, updated whenever a fact changes.
Three files.

## `profile/profile.md`

Frontmatter: common keys with `type: profile`, `date` = date of onboarding,
`author_kind: patient` (the content is the patient's own account, transcribed
by the agent), `author: patient`, `source: none`. The agent that transcribed
it is recorded in the commit.

Body sections, all present, in this order. Write `Unknown` or `None reported`
rather than leaving a section empty.

```
## Identity
- Name:
- Date of birth:
- Sex at birth:
- Gender (if different):
- Height:
- Weight (date):
- Blood type:

## Allergies and intolerances
- <substance>: <reaction>, <severity>, <how established>

## Past medical history
- <condition>: <year diagnosed>, <by whom>, <status>

## Surgeries and procedures
- <YYYY or YYYY-MM-DD>: <procedure>, <where>, <outcome>

## Family history
- <relative>: <condition>, <age at onset or death>

## Lifestyle
- Smoking:
- Alcohol:
- Other substances:
- Exercise:
- Diet:
- Sleep:
- Occupation and exposures:

## Reproductive history
(or "Not applicable")

## Patient's own account
Free text. What brought them here, what they are worried about, what the
specialists have and have not explained. The patient's words, lightly edited.
```

When a fact changes, edit it in place and add a line under a trailing
`## Changelog` section: `- YYYY-MM-DD: weight updated from 82 to 79 kg`.
The changelog is append-only.

## `profile/medications.csv`

Every medication and supplement, past and present. A medication whose dose
changes gets a new row; the old row gets an `end` date.

```
name,dose,route,frequency,start,end,prescriber,reason,source,notes
```

| Column | Values |
|---|---|
| `name` | Generic name, lowercase. Brand in `notes` if relevant |
| `dose` | Amount with unit, e.g. `50 mg`, `1000 IU` |
| `route` | `oral`, `topical`, `inhaled`, `injection`, `other` |
| `frequency` | e.g. `once daily`, `twice daily`, `as needed`, `weekly` |
| `start` | Date started, or empty if unknown |
| `end` | Date stopped, empty if current |
| `prescriber` | Name, or `self` for supplements and over-the-counter |
| `reason` | Indication, short |
| `source` | Repo path of the document or chat where this was established, or `patient` |
| `notes` | Free text: brand, side effects, adherence |

A row with an empty `end` is a current medication. `SUMMARY.md` lists exactly
those.

## `profile/specialists.csv`

The patient's care team.

```
name,role,institution,since,last_visit,notes
```

| Column | Values |
|---|---|
| `name` | As the patient refers to them, e.g. `Dr Jane Smith` |
| `role` | Specialty, lowercase: `gp`, `cardiologist`, `endocrinologist`, ... |
| `institution` | Practice or hospital, may be empty |
| `since` | Date of first visit, may be empty |
| `last_visit` | Date of latest recorded visit, may be empty |
| `notes` | Free text |

`clinician` fields elsewhere in the record should match a `name` here.
