# Schema: chat

`chats/YYYY-MM-DD_slug.md`. A summary of one meaningful consultation between
the patient and the harness, the equivalent of a visit note written by the
physician afterwards. Ad-hoc questions are not recorded here.

Frontmatter: common keys with `type: chat`, `author_kind: model`,
`source: none`. Additional key:

| Key | Required | Meaning |
|---|---|---|
| `visit_kind` | yes | `consultation`, `review`, `second_opinion`, `onboarding` |

Body sections, in this order:

```
## Context
Why this consultation happened and what the patient wanted from it.

## Discussed
The substance, in the order it was discussed. Patient's reports in the
patient's terms; the harness's reasoning labelled as such.

## Findings
What the harness concluded, with confidence. Cross-field connections
noticed. Anything urgent, first.

## Record changes
Every file created or changed as a result of this consultation, one per
line, with the path. This is the reconciliation list for the commit.

## For the doctors
Concrete questions and requests to take to named clinicians.

## Open questions
What remains unresolved and what the harness wants to see next.
```
