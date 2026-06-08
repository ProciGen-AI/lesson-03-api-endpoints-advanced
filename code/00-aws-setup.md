# Exercise 00 — Set up AWS Bedrock

This is a one-time setup that prepares your AWS account to run every Bedrock-based exercise in this course (02–08). There is no Python code here — it's a walkthrough of the AWS console plus a smoke test at the end.

Exercise 01 (Gemini via raw HTTP) does **not** require AWS — you can do that one with just a Google AI Studio key (Step 5). Everything from 02 onward needs the AWS setup below.

If you hit a snag, see [**Getting help when setup fails**](#getting-help-when-setup-fails) at the bottom — it shows the *format* in which to share an error or screenshot with Claude so you get a useful answer fast.

## What you'll do

1. Sign in to AWS (or create an account).
2. Create an IAM user with Bedrock permissions.
3. Generate access keys for that user.
4. Run `setup.sh` to seed `.env`, fill in your keys (and confirm the model ID in the Bedrock console), then re-run `setup.sh` to verify Bedrock works end-to-end.
5. Grab a free Google AI Studio API key — exercise 01 uses Gemini for one "an LLM API is just HTTP" example.

> ⚠️ **Use a personal sandbox AWS account, or an explicit "course" account.** Don't run lab exercises against a production AWS account. The total cost of running every exercise in this course is roughly **a few cents to under a dollar** — but you're responsible for any charges.

---

## Step 1 — AWS account

If you don't have an AWS account, sign up at https://aws.amazon.com/. New accounts get a free tier, though Bedrock itself is pay-per-token (no free tier for inference).

## Step 2 — Create an IAM user

Never use root account credentials for application access. Create a dedicated IAM user.

1. Open the IAM console: https://console.aws.amazon.com/iam/
2. In the left sidebar under **Access management**, click **IAM users** → **Create user**.
3. Name: `ai-course-bedrock` (or similar). **Leave "Provide user access to the AWS Management Console" unchecked.**
4. On **Set permissions**, the wizard defaults to **Add user to group** — switch to **Attach policies directly**. Groups are the production best practice, but for a single course user they only add extra clicks without any real benefit.
5. Search for `AmazonBedrockFullAccess` and check it.
   - This is broader than you'd use in production, but fine for the course.
   - The narrowest policy that would work is one granting `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`, `bedrock:Converse`, and `bedrock:ConverseStream` on `*` (or a specific model ARN).
6. Click **Next**, then **Create user**.

## Step 3 — Generate access keys

1. From the Users list, click the user you just created.
2. Open the **Security credentials** tab.
3. Scroll to **Access keys** → **Create access key**.
4. Use case: select **Application running outside AWS** → **Next**.
5. (Optional) Add a description tag like "ai course - bedrock full access". Click **Create access key**.
6. **Copy both the Access key and Secret access key now.** The secret key is shown only once — if you lose it, you'll need to create a new one.

## Step 4 — Configure `.env` and verify with `setup.sh`

The setup script handles `.env` for you. You'll run it twice: once to seed the file, and again — after you fill in your keys and confirm the model ID — to actually verify Bedrock works.

> **On Windows?** Run `setup.sh` (and every later command) from **Git Bash**, not PowerShell or cmd — they can't source a `.sh` file. Easiest: open the project in VS Code and set the integrated terminal to Git Bash (`Ctrl+Shift+P` → *Terminal: Select Default Profile* → *Git Bash*). No Git Bash? Install [Git for Windows](https://git-scm.com/download/win), or use [WSL](https://learn.microsoft.com/windows/wsl/install) (behaves like native Linux). Started in PowerShell by mistake? Run `.\setup.ps1` from the lab folder and it'll point you to Git Bash. macOS/Linux: nothing special — the commands below work as-is.

### 4a. First run: seed `.env`

Move into the lab's `code/` folder and source the setup script from there. You'll stay in `code/` for the rest of the lab — it's where you run every exercise — so `cd` in now:

```bash
cd code        # from the root of the cloned repo
source setup.sh
```

On the first run (no `.env` exists yet) the script copies `.env.example` into place and stops with an "ACTION REQUIRED" message. That's expected — you haven't filled in your keys yet.

### 4b. Fill in your AWS credentials

Open the `.env` file the script just created in your editor. The path is printed in the script output (look for `→ Env root:`). Set:

```env
AWS_ACCESS_KEY_ID=AKIA...           # from Step 3
AWS_SECRET_ACCESS_KEY=...           # from Step 3
AWS_REGION=us-east-1                # broadest Bedrock model availability
```

### 4c. Confirm — or update — the model ID

`.env.example` ships with `BEDROCK_MODEL_ID` set to **Amazon Nova 2 Lite** (`us.amazon.nova-2-lite-v1:0`), which is the course default. For most students this is fine and you can skip to 4d. You need to touch this line only if:

- you want to use a different model, **or**
- Amazon has shipped a newer Nova version since this lab was written and you want the latest.

To pick a current ID:

1. Open the Bedrock console: https://console.aws.amazon.com/bedrock/
2. Region selector (top-right) → match the value of `AWS_REGION` in your `.env`.
3. Left sidebar under **Discover** → **Model catalog** → filter by provider **Amazon**.
4. Click into the model you want → copy its **Model ID** from the detail page → paste it as `BEDROCK_MODEL_ID` in `.env`. Use the **cross-region inference-profile** ID (the `us.` one — e.g. `us.amazon.nova-2-lite-v1:0`), not the bare `amazon...` ID: Nova 2 Lite can't be called in-region on-demand in us-east-1, so the profile prefix is required.

> **Enable model access.** Before the first call, the model must be enabled for your account under **Model access** in the Bedrock console. Amazon's own models (Nova) are first-party and usually don't require the use-case form some third-party models do, but you may still need to toggle access on. If 4d below fails with an `AccessDeniedException` about model access, open **Model access**, enable **Amazon Nova 2 Lite**, wait a moment, then re-run the script.

### 4d. Second run: verify Bedrock works

Source the script again (you're already in `code/`):

```bash
source setup.sh
```

This time it runs the full check. On success the last lines are:

```
✓ Bedrock OK — model replied: 'ok'
✓ Lesson-02-API-Endpoints is ready. Run an exercise with:  python <exercise>.py
```

### If you see an error

The setup script prints a concrete action for every failure mode. The most common ones:

- **`AccessDeniedException`** — credentials are valid but the call was refused. Two common causes: (a) the IAM policy doesn't allow `bedrock:InvokeModel` (check the user's attached policies in IAM), or (b) model access for Nova 2 Lite isn't enabled for your account — re-read the **Model access** note in 4c.
- **`UnrecognizedClientException` / `InvalidSignatureException`** — your `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` is wrong. Re-check the values from Step 3.
- **`ResourceNotFoundException`** — the `BEDROCK_MODEL_ID` value isn't valid in your region. The most common cause is forgetting the `us.` inference-profile prefix (Nova 2 Lite needs it — the bare `amazon...` ID isn't on-demand callable in-region). Re-do 4c.
- **`EndpointConnectionError`** — `AWS_REGION` isn't a Bedrock-supported region. Try `us-east-1` or `us-west-2`.

If the error you're seeing isn't in that list — or the suggested action doesn't fix it — see [Getting help when setup fails](#getting-help-when-setup-fails) below.

## Step 5 — Get a Google AI Studio API key

Exercise 01 hits Gemini directly via raw HTTP — the point is to show "an LLM API endpoint is just an HTTP POST" without the SigV4 signing that Bedrock requires. That call uses an API key rather than IAM credentials, and Google AI Studio gives one out free.

1. Open https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Get API key**. If prompted, accept the terms and choose a project (any will do).
3. Copy the key shown (starts with `AIza...`).
4. Open the `.env` file (same one as Step 4b) and paste the key:

```env
GOOGLE_API_KEY=AIza...
```

`GEMINI_MODEL_ID` is already set to a reasonable default. The free tier rate limits are generous enough for the lab; no billing setup needed.

You don't need to verify this end-to-end now — exercise 01 will tell you if the key is wrong. Once both `AWS_*` and `GOOGLE_API_KEY` are filled in, you're ready for the exercises.

---

## Getting help when setup fails

AWS console UIs change, regions differ, and error messages come in many flavors. When you're stuck, the quality of Claude's answer depends almost entirely on the quality of what you paste. Include the same five pieces every time:

1. **Where you are.** Which step — "Step 4c, picking the model ID from the catalog."
2. **What you did.** The specific action that triggered the problem.
3. **What you expected vs. what happened.**
4. **Evidence.** The **exact** error text (copy-paste, not paraphrase), or a screenshot — both is better.
5. **Environment.** Region, model ID, and relevant `.env` values — **with secrets redacted.**

**Redact secrets.** Never paste AWS keys in clear text — not in chat, not in a screenshot. Show the first 4 chars of the access key only and none of the secret:

```
AWS_ACCESS_KEY_ID=AKIA...REDACTED
AWS_SECRET_ACCESS_KEY=...REDACTED
```

If a screenshot accidentally exposes a key, **rotate it immediately** (IAM → Security credentials → make inactive → delete → create a new pair) and update `.env`.

### A good error-report prompt looks like this

```
I'm at Step 4d (verifying with setup.sh). I ran
`source setup.sh` and got:

  ✗ Bedrock returned [AccessDeniedException]: User: arn:aws:iam::123456789012:user/ai-course-bedrock
    is not authorized to perform: bedrock:InvokeModel

My .env has AWS_REGION=us-east-1 and
BEDROCK_MODEL_ID=us.amazon.nova-2-lite-v1:0 (keys redacted).
The IAM user has AmazonBedrockFullAccess. The account is brand new and I
have not yet enabled model access for Nova 2 Lite (Step 4c).

What's the most likely cause?
```

That lets Claude rule out 80% of failure modes immediately and zero in on the real one (here, model access). Compare it to "it doesn't work" — which forces three follow-up questions before any help is possible.

### When you don't know what to ask

The structured form still works:

```
Where I am:      Step [N] of the AWS Bedrock setup.
What I did:      [exact actions]
What I expected: [expected outcome]
What happened:   [actual outcome, exact words from console / terminal]
Evidence:        [paste the full error block, OR attach a screenshot, OR both]
Environment:     region=[...], model_id=[...], .env values, secrets redacted.

What's the most likely cause, and what's the next thing to check?
```

The same pattern works for every later lab in this course — and most of your real work after it.
