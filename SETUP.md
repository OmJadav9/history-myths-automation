# One-time setup

After this, nothing needs your attention: failures open GitHub Issues, which GitHub emails to you.

## 1. Instagram + Meta (Unified login, system-user token)

Already done:
- @did.you.know9104 is a Creator account in the **Did You Know History** business portfolio (ID 1849759719676789).
- The app **History Myths Publisher** exists, with app ID 2530734860769356 and the "Manage messaging & content on Instagram" use case.
- Its IG user ID is **17841456970662962**.

Remaining:
1. App → Use cases → Customize → **API setup with Unified login**. Create the configuration (from the template is fine).
2. App roles → Roles → **Instagram testers**: add `did.you.know9104`. Then accept the invite in the Instagram app (Settings → Website permissions / Apps and websites → Tester invites).
3. Business Settings → Users → **System users**: add an **Admin** system user. Assign it the app **and** the Instagram account, both with full control, *before* generating the token.
4. Generate a new token for the system user:
   - App: History Myths Publisher.
   - Expiry: **Never**.
   - Permissions: only **instagram_basic** and **instagram_content_publish**.

   Copy it straight into step 3 below, and never paste it into a chat or file.

If any screen insists on a Facebook Page, create one inside the same portfolio (free) and link the Instagram account to it.

## 2. Claude token

Run this yourself and copy the token it prints:

```bash
claude setup-token
```

## 3. Store the secrets

```powershell
powershell -ExecutionPolicy Bypass -File scripts\set_secrets.ps1     # Windows
```
```bash
bash scripts/set_secrets.sh                                          # Git Bash / Mac / Linux
```

It asks, with hidden input, for `CLAUDE_CODE_OAUTH_TOKEN`, `IG_ACCESS_TOKEN` and `IG_USER_ID`. The app ID and secret
aren't needed, because a never-expiring system-user token needs no refresh.

## 4. Test, then go live

1. Actions → **Post myth reel** → Run workflow, with `dry_run` ticked. Download the `dry-run-reel` artifact and watch it.
2. Run it again with `publish_test` ticked. One real reel goes out now.
3. Set `start_date` in `config.yaml` to the first day of automatic posting (day 1 = 1 reel/day).

## Changing things later

- **Pace:** `schedule.ramp` / `max_reels_per_day`. Keep `slots_utc` in sync with the cron in `post.yml`.
- **Topics to avoid:** `content.excluded_keywords` (checked on the claim, event and people only).
- **Voice:** `voice.edge_voice`. Run `python -m mythreels voices` to hear the options.
- **Pronunciations:** `voice.pronunciations`. The researcher also adds tricky names per myth.
