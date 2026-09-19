# Setting up the S3 remote

One person does **Part 1** once. Everyone does **Part 2** on their own machine.

Storage cost is negligible -- the project data is about 1 MB. The reason to be
careful below is not the bill for storage, it is that this GitHub repo is
**public**, and a leaked AWS key on a public repo gets found by scrapers within
seconds. Everything here is aimed at making a leak survivable: keys that are
scoped to one bucket, and issued per person so one can be revoked alone.

## Part 1: bucket and IAM (one person, once)

### 1. Create the bucket

S3 console -> **Create bucket**. Any unique name; keep **Block all public
access** switched ON (the default). Note the region you picked.

### 2. Create a policy scoped to that bucket

IAM -> **Policies** -> **Create policy** -> **JSON**. Paste this, replacing
`YOUR-BUCKET-NAME` in both places:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListTheBucket",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME"
    },
    {
      "Sid": "ReadWriteObjectsInIt",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
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
git add .dvc/config && git commit -m "Point DVC at the group S3 bucket"
```

Only the bucket URL is committed. No keys.

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

`--local` is the part that matters. It writes to `.dvc/config.local`, which is
gitignored. Without it, the keys go into `.dvc/config`, which is committed and
public.

If the bucket is not in your default region, also:

```bash
dvc remote modify --local storage region <bucket-region>
```

### Check you did it right

```bash
git check-ignore -v .dvc/config.local   # should print a .gitignore line
git status --short                      # .dvc/config.local must NOT appear
grep -ri "AKIA" .dvc/config             # must print nothing
```

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
