# Procedure: harness-update

Pulls a newer harness into this record. The only sanctioned way harness-
owned files change inside a patient record. Precondition: session-start
completed, working tree clean.

## 1. Check the upstream remote

```
git remote get-url upstream
```

If there is none, the record was not set up per the README. Ask the
patient for the harness repository URL and add it:
`git remote add upstream <url>`.

## 2. See what is new

```
git fetch upstream
git log --oneline HEAD..upstream/master
git diff HEAD...upstream/master --stat
git diff HEAD...upstream/master -- harness/CHANGELOG.md
```

Three dots, not two: the three-dot form shows only what upstream added
since the branches diverged. The two-dot form compares whole trees and
lists every record file as a deletion, which is misleading.

Tell the patient the current version (`harness/VERSION`), the new version,
and what the changelog says changed, including any migration notes. Wait
for a yes.

## 3. Merge

```
git merge --no-ff upstream/master -m "harness-update: <old> -> <new>" -m "Model: <model>" -m "Runtime: <runtime>"
```

The merge is the one commit not made through `msdh.py commit`, so carry
the provenance in the message yourself.

By construction there are no conflicts: upstream touches only
harness-owned paths, patient sessions never do. If git reports a conflict
anyway, run `git merge --abort`, tell the patient which files conflicted,
and stop. Do not resolve conflicts in harness-owned files yourself.

## 4. Restart the session

The harness version changed, so the session identity is stale:

```
python3 harness/scripts/msdh.py session --model <model> --runtime "<runtime>"
```

with the same values the patient confirmed at session start.

## 5. Validate and migrate

```
python3 harness/scripts/msdh.py validate
```

A new version may tighten schemas. If existing record files now fail,
follow the migration notes in `harness/CHANGELOG.md` for every version
between old and new. Migrations edit record files, so they are committed
through `harness/procedures/commit.md` with `--procedure migration` and
subject `migrate record to harness <new>`. Record files are never deleted
in a migration; renames are done with `git mv`.

## 6. Push

If the remote is private: `git push origin HEAD`.

Then re-read `AGENTS.md`; the new version may route differently.
