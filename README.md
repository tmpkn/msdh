# MSDH — Medical Self Diagnose Harness

A harness that turns an LLM agent session into a holistic physician who knows
your entire medical history. It sits alongside your specialists and tests; it
does not replace them. It holds everything in one place, spots cross-field
patterns, and sends you back to your doctors with better questions.

There is no app. You open an agent (Claude Code, Codex, pi, or any agent that
reads `AGENTS.md`) in this directory and talk to it. The record is markdown and
CSV in git. Design rationale is in `harness/PRINCIPLES.md`.

## Set up your record

1. Create a **private** repository on a host you control. The record will
   contain your health information.
2. Clone this harness and repoint it:

   ```
   git clone <harness-repo-url> my-record
   cd my-record
   git remote rename origin upstream
   git remote add origin <your-private-repo-url>
   git push -u origin master
   ```

3. Open your agent in `my-record` and say: *"onboard me"*. The agent will ask
   who it is running as, then walk you through an intake questionnaire.

## Daily use

Open your agent in the record directory. It always starts by confirming its
identity and checking the record. Then:

- *"I have a new blood panel"* → it ingests the file into the record.
- *"Let's talk about how I'm doing"* → a consultation, summarized like a visit.
- *"Is this headache something to worry about?"* → an ad-hoc question,
  answered with your full history in mind.
- *"Give me a second opinion"* → run from a different model; it assesses the
  record blind and its view is recorded next to the others.

Every change is committed with the model that made it stamped in the commit.
`git log` is the audit trail.

## Update the harness

```
git pull upstream master
```

The harness only ever touches `AGENTS.md`, `CLAUDE.md`, `README.md`,
`.gitignore` and `harness/`. Your record files are never affected.

## Helper script

```
python3 harness/scripts/msdh.py --help
```

Standard library only; Python 3.10 or newer.
