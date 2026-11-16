<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="harness/assets/msdh-logo-reversed.svg">
    <img src="harness/assets/msdh-logo.svg" alt="MSDH" width="320">
  </picture>
</p>

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
   git clone https://github.com/tmpkn/msdh.git my-record
   cd my-record
   git remote rename origin upstream
   git remote set-url --push upstream DISABLED
   git remote add origin <your-private-repo-url>
   git push -u origin master
   ```

   The third line matters: this harness repository is public, and disabling
   the push URL makes it impossible to push your record to it by mistake.
   The agent's status check warns if it is ever re-enabled.

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
- *"Ingest the ClinVar run"* → after you run `harness/tools/clinvar/analyze_wgs.py`
  on your sequencing file by hand; matches are layered onto the record as
  screening findings. See `harness/tools/clinvar/README.md`.

Every change is committed with the model that made it stamped in the commit.
`git log` is the audit trail.

## Tested with

| Agent | Models | Environment |
|---|---|---|
| Claude Code | Opus 5.5<br>Fable 5.1<br>Mythos 5.2 | Cloud |
| DeepSeek Harness 0.2 | DeepSeek-V4.1-Flash-1017-TrellisMX-K2-Mix | Fully offline, on-premise |

Any agent that reads `AGENTS.md` and can run Python 3 and git should work.
Reports from other agents and models are welcome.

## Update the harness

```
git pull upstream master
```

The harness only ever touches `AGENTS.md`, `CLAUDE.md`, `README.md`,
`.gitignore`, `.github/` and `harness/`. Your record files are never affected.

## Contributing

Pull requests are welcome. Work in a clone of this repository, not in your
record: a record must never be pushed anywhere public, and the pull-request
check fails on any change outside the harness-owned files above. Run
`python3 harness/scripts/msdh.py validate` before opening one, bump
`harness/VERSION` and add a `harness/CHANGELOG.md` entry for anything a
record would notice.

## Helper script

```
python3 harness/scripts/msdh.py --help
```

Standard library only; Python 3.10 or newer.
