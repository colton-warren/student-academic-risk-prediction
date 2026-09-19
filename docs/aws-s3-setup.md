# Setting up the S3 remote

One person does **Part 1** once. Everyone does **Part 2** on their own machine.

Storage cost is negligible -- the project data is about 1 MB. The reason to be
careful below is not the bill for storage, it is that this GitHub repo is
**public**, and a leaked AWS key on a public repo gets found by scrapers within
seconds. Everything here is aimed at making a leak survivable: keys that are
scoped to one bucket, and issued per person so one can be revoked alone.

The bucket for this project already exists:

| | |
|---|---|
| Bucket | `uc-bana-7075-fall2026-group7-student-academic-risk-prediction` |
| Region | `us-east-1` |
| DVC prefix | `dvcstore/` |

Part 1 is recorded for the next person who has to rebuild it, or to add a
teammate. If you just need access, skip to Part 2.

## Part 1: bucket and IAM (one person, once)

### 1. Create the bucket

S3 console -> **Create bucket**. The name must be unique across all of AWS,
not just your account. Keep **Block all public access** switched ON (the
default), leave versioning **Disabled** (DVC content-addresses its files, so
it never overwrites), and note the region you picked.

### 2. Create a policy scoped to that bucket

IAM -> **Policies** -> **Create policy** -> **JSON**. The policy below is the
one in use; if you are rebuilding under a different bucket, replace the name
in both places:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListTheBucket",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::uc-bana-7075-fall2026-group7-student-academic-risk-prediction"
    },
    {
      "Sid": "ReadWriteObjectsInIt",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::uc-bana-7075-fall2026-group7-student-academic-risk-prediction/*"
    }
  ]
}
```

Name it something like `Group7DvcBucketAccess`.

This grants exactly what `dvc push` and `dvc pull` need and nothing else. Do
not substitute `s3:*` on `"Resource": "*"` -- that is the difference between a
leaked key costing you one bucket and costing you the whole account.

### 3. Create a group and attach the policy

IAM -> **User groups** -> **Create group**, name it `group7-dvc`, and attach the
policy from step 2.

### 4. Create one user per teammate

IAM -> **Users** -> **Create user**, one per person, each added to the
`group7-dvc` group. Do **not** give them console access -- they only need
programmatic keys.

For each user: open it -> **Security credentials** -> **Create access key** ->
choose **Command Line Interface (CLI)**. You get an **Access key ID** and a
**Secret access key**. The secret is shown once.

Send each person only their own pair, and not over a channel that keeps
history where others can read it later.

### 5. Add the remote to the repo

```bash
dvc remote add -d storage s3://YOUR-BUCKET-NAME/dvcstore
dvc remote modify storage region YOUR-REGION
git add .dvc/config && git commit -m "Point DVC at the group S3 bucket"
```

Only the bucket URL and region are committed. No keys. This is already done
for the current bucket, so it is here for the rebuild case.

### 6. Set a budget alert

Billing -> **Budgets** -> a small monthly cost budget with an email alert. The
project itself costs pennies, so any real number is a signal that a key leaked.

## Part 2: each teammate, on their own machine

After cloning and installing requirements:

```bash
dvc remote modify --local storage access_key_id <your-access-key-id>
dvc remote modify --local storage secret_access_key <your-secret-access-key>
dvc pull
```

The region is already in the committed `.dvc/config`, so you do not set it.

`--local` is the part that matters. It writes to `.dvc/config.local`, which is
gitignored. Without it, the keys go into `.dvc/config`, which is committed and
public.

### Check you did it right

```bash
git check-ignore -v .dvc/config.local   # should print a .gitignore line
git status --short                      # .dvc/config.local must NOT appear
git grep -i "AKIA" -- .dvc/config       # must print nothing
```

`git grep` is used rather than plain `grep` because it ships with Git on every
platform, including Windows PowerShell and Command Prompt.

## If a key leaks

Speed matters more than tidiness, and this is not a disaster if you act:

1. IAM -> that user -> **Security credentials** -> **Deactivate**, then
   **Delete** the key. Deactivating alone stops it working immediately.
2. Create a replacement key for that one person. Nobody else is affected --
   that is the reason for one user each.
3. Check CloudTrail for use you do not recognise, and glance at the Billing
   dashboard for unexpected charges.
4. Removing the key from a file does **not** undo the leak. Anything pushed to
   GitHub stays in the history and in anyone's clone. The key must be revoked
   in IAM; editing the file is not enough.

## At the end of the semester

Delete the access keys, or delete the IAM users outright, and empty the bucket.
Long-lived keys for a finished project are the ones that leak later.
