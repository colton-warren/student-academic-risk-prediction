# When something goes wrong

Ordered by how often it actually happens. Almost everything here is one of two
things: the virtual environment is not active, or Git and DVC are out of step
with each other.

If you are stuck for more than fifteen minutes, ask in the group chat. Paste the
**full** error message, not a summary — the useful part is usually the last two
lines, and often the part that looks like noise.

## "It worked yesterday and now nothing works"

Activate the virtual environment. This is the answer far more often than it
should be.

```bash
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

You can tell it worked because your prompt gains a `(.venv)` prefix. It does not
survive closing the terminal, so you do this every session, in every new window.

## `ModuleNotFoundError: No module named 'pandas'` (or dvc, mlflow, yaml...)

The environment is not active, or the install did not finish. Activate it, then:

```bash
pip install -r requirements.txt
```

## `python: command not found` / `'python' is not recognized`

Python is not on your PATH. On Windows this usually means the installer ran
without **"Add Python to PATH"** ticked — reinstall and tick it. On macOS try
`python3` instead of `python`.

Note that the pipeline itself calls plain `python`, which is why the virtual
environment has to be active for `dvc repro` to work.

## `dvc pull` says AccessDenied or InvalidAccessKeyId

Your AWS keys are wrong, missing, or in the wrong file.

```bash
dvc remote list          # should print: storage  s3://uc-bana-7075-...
cat .dvc/config.local    # Windows: type .dvc\config.local
```

`.dvc/config.local` should contain your `access_key_id` and `secret_access_key`.
If the file is missing, you never ran the two `dvc remote modify --local`
commands from the README. If it exists but still fails, your key may be typed
wrong or may have been revoked — ask Paul for a fresh one.

If you find your keys in `.dvc/config` instead of `.dvc/config.local`, **say so
in the group chat before doing anything else.** That file is committed to a
public repo, and the key has to be revoked in AWS rather than just deleted.

## `dvc pull` says a file is missing from the remote

Someone pushed code without pushing data. Ask whoever made the last commit to
run `dvc push`. It is not something you can fix on your end.

## `dvc repro` fails at `verify_prep`

Working as intended — it found a problem with the prepared dataset rather than
letting the models train on it. Read `reports/prep_verification.json` for the
specifics. The usual causes:

- **"KNIME output does not match src/clean_data.py"** — someone changed the
  KNIME workflow without updating the Python port, or the prepared CSV was
  edited by hand. Whoever changed the workflow needs to update
  `src/clean_data.py` to match.
- **missing cells / duplicate rows / unexpected target categories** — the
  prepared data genuinely has a problem. Rerun the KNIME workflow.
- **"values outside contract ranges"** — a warning, not a failure. The pipeline
  continues. It means new data exceeded what the reference data contained.

## Merge conflict in `dvc.lock`

This will happen, and you cannot hand-edit your way out of it — the file is
hashes. Take either side and regenerate it:

```bash
git checkout --theirs dvc.lock     # or --ours, it does not matter much
dvc repro                          # rebuilds it correctly
git add dvc.lock
git commit
```

The same applies to a conflict in a `.dvc` file.

## Merge conflict in the KNIME workflow

Git cannot merge KNIME workflows — they are XML and binary blobs. Do not try.
Decide with the other person which version to keep:

```bash
git checkout --theirs "Student_Risk_DataOps"   # or --ours
git add "Student_Risk_DataOps"
```

Then the person whose work was discarded redoes it on top. This is why it is
worth saying in the group chat before you start editing the workflow.

## The commit was blocked: "possible credentials in staged changes"

The pre-commit hook found something that looks like an AWS key. Read what it
printed — it names the file and line.

Nearly always this is `dvc remote modify` run without `--local`, which writes
your key into `.dvc/config`. Fix it by putting the key where it belongs:

```bash
git checkout .dvc/config
dvc remote modify --local storage access_key_id <your-key-id>
dvc remote modify --local storage secret_access_key <your-secret>
```

If the hook is genuinely wrong about a line, add `pragma: allowlist secret` to
that line. Use `git commit --no-verify` only when you are certain — if you need
it to commit a real credential, the credential is in the wrong file.

## `git push` is rejected

Someone pushed before you. Bring their work in, then push again:

```bash
git pull
dvc pull
git push
```

If `git pull` reports conflicts, see the two conflict sections above.

## MLflow: `Read-only file system: '/C:'` or a path that does not exist

An `mlflow.db` created on someone else's machine got into your folder. That file
stores absolute paths, so it only works on the machine that made it. Delete your
local copy and let it be recreated:

```bash
rm mlflow.db        # Windows: del mlflow.db
```

It is gitignored, so it should not reach you through Git in the first place.

## KNIME's Python node: `No module named 'mlflow'`

KNIME is pointed at a Python environment that does not have MLflow in it.
*File → Preferences → KNIME → Python*. Test with a one-line script containing
`import mlflow` before debugging anything else in the workflow.

## Starting over

Nothing here risks your committed work, and it resolves a surprising amount.

```bash
rm -rf .venv                      # Windows: rmdir /s .venv
python3 -m venv .venv             # Windows: python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
dvc pull
```

If that does not do it, delete the whole folder and clone again — you will need
to redo the `git config core.hooksPath .githooks` and the two
`dvc remote modify --local` commands, since neither survives a fresh clone.
