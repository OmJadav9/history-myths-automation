#!/usr/bin/env bash
# Stores the automation's secrets in GitHub Actions. Run it yourself:  bash scripts/set_secrets.sh
# Values are typed with hidden input and piped straight to `gh secret set`. Nothing is printed or written to disk.
set -euo pipefail
REPO="OmJadav9/history-myths-automation"
NAMES=(CLAUDE_CODE_OAUTH_TOKEN IG_ACCESS_TOKEN IG_USER_ID)
HINTS=("Claude token (run 'claude setup-token' yourself first)"
       "Meta system-user access token (never-expiring)"
       "Instagram account ID (17841456970662962 for @did.you.know9104)")

gh auth status >/dev/null
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"
  read -rsp "$name - ${HINTS[$i]} (Enter to skip): " value; echo
  value="$(printf '%s' "$value" | tr -d '\r\n')"
  if [ -z "$value" ]; then echo "  skipped $name"; continue; fi
  printf '%s' "$value" | gh secret set "$name" --repo "$REPO"
  unset value
  echo "  stored $name"
done
echo "Done. Check them at https://github.com/$REPO/settings/secrets/actions"
