#!/usr/bin/env bash
#
# This source file is part of the Schmiedmayer Lab open-source organization
#
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
#
# SPDX-License-Identifier: MIT
#

# Audits or applies the repository settings baseline in REPOSITORY_STANDARDS.md.
#
#   ./scripts/apply-repository-settings.sh              audit every public repository
#   ./scripts/apply-repository-settings.sh apply        bring them to the baseline
#   ./scripts/apply-repository-settings.sh audit REPO   audit one repository
#
# Applying is idempotent: a repository already at the baseline is left untouched.
# Requires the GitHub CLI, authenticated with admin access to the organization.

set -euo pipefail

ORG="${ORG:-SchmiedmayerLab}"
MODE="${1:-audit}"
ONLY="${2:-}"

case "$MODE" in
  audit|apply) ;;
  *) echo "usage: $0 [audit|apply] [repository]" >&2; exit 2 ;;
esac

command -v gh >/dev/null || { echo "the GitHub CLI is required" >&2; exit 1; }

# Contexts the standards workflow reports. Required only where the caller exists,
# because a required check that never reports blocks every merge.
STANDARDS_CHECKS='["Standards / Surface","Standards / Licensing / Check REUSE Compliance","Standards / Links / Check Markdown Links","Standards / Actions / Actionlint"]'

has_standards_caller() {
  gh api "repos/$ORG/$1/contents/.github/workflows/repository-standards.yml" --silent >/dev/null 2>&1
}

# Adds the standards contexts to the Main ruleset, keeping every check already required.
require_standards_checks() {
  local repo=$1 id=$2 body
  body=$(gh api "repos/$ORG/$repo/rulesets/$id" | jq --argjson add "$STANDARDS_CHECKS" '
    {name, target, enforcement, bypass_actors, conditions,
     rules: (
       (if any(.rules[]; .type == "required_status_checks") then .rules
        else .rules + [{type: "required_status_checks",
                        parameters: {strict_required_status_checks_policy: true,
                                     do_not_enforce_on_create: false,
                                     required_status_checks: []}}] end)
       | map(if .type == "required_status_checks" then
               .parameters.required_status_checks =
                 ((.parameters.required_status_checks + ($add | map({context: .})))
                  | unique_by(.context))
             else . end))}')
  printf '%s' "$body" | gh api -X PUT "repos/$ORG/$repo/rulesets/$id" --silent --input -
}

ruleset_payload() {
  cat <<'JSON'
{
  "name": "Main",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    {"actor_id": null, "actor_type": "OrganizationAdmin", "bypass_mode": "always"},
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {"ref_name": {"exclude": [], "include": ["~DEFAULT_BRANCH"]}},
  "rules": [
    {"type": "deletion"},
    {"type": "creation"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {"type": "required_signatures"},
    {"type": "pull_request", "parameters": {
      "allowed_merge_methods": ["squash"],
      "dismiss_stale_reviews_on_push": false,
      "dismissal_restriction": {"allowed_actors": [], "enabled": false},
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_approving_review_count": 1,
      "required_review_thread_resolution": true,
      "required_reviewers": []
    }}
  ]
}
JSON
}

if [ -n "$ONLY" ]; then
  repos="$ONLY"
else
  # Forks mirror an upstream project and are not held to this standard.
  repos=$(gh repo list "$ORG" --limit 100 --no-archived --visibility public \
            --json name,isFork --jq '.[] | select(.isFork | not) | .name')
fi

status=0

for repo in $repos; do
  meta=$(gh api "repos/$ORG/$repo")
  private=$(echo "$meta" | jq -r .private)

  drift=()
  [ "$(echo "$meta" | jq -r '.allow_squash_merge and (.allow_merge_commit|not) and (.allow_rebase_merge|not)')" = "true" ] \
    || drift+=("merge methods are not squash-only")
  [ "$(echo "$meta" | jq -r .allow_auto_merge)" = "true" ] || drift+=("auto-merge is disabled")
  [ "$(echo "$meta" | jq -r .delete_branch_on_merge)" = "true" ] || drift+=("branches are not deleted on merge")
  [ "$(echo "$meta" | jq -r '.security_and_analysis.secret_scanning.status')" = "enabled" ] \
    || drift+=("secret scanning is disabled")
  [ "$(echo "$meta" | jq -r '.security_and_analysis.secret_scanning_push_protection.status')" = "enabled" ] \
    || drift+=("push protection is disabled")
  [ "$(echo "$meta" | jq -r '.security_and_analysis.dependabot_security_updates.status')" = "enabled" ] \
    || drift+=("Dependabot security updates are disabled")

  rulesets=$(gh api "repos/$ORG/$repo/rulesets" 2>/dev/null || echo 'null')
  main_id=""
  if [ "$(echo "$rulesets" | jq -r 'if type == "array" then "ok" else "unreadable" end')" = "ok" ]; then
    main_id=$(echo "$rulesets" | jq -r '[.[] | select((.name | ascii_downcase) == "main" and .enforcement == "active")][0].id // ""')
    [ -n "$main_id" ] || drift+=("no active Main ruleset")
    if [ -n "$main_id" ] && has_standards_caller "$repo"; then
      missing=$(gh api "repos/$ORG/$repo/rulesets/$main_id" | jq -r --argjson want "$STANDARDS_CHECKS" '
        [$want[] | select(. as $c | ([.. | objects | select(has("context")) | .context] | index($c) | not))] | join(", ")')
      [ -z "$missing" ] || drift+=("standards checks not required: $missing")
    fi
  fi

  if [ "${#drift[@]}" -eq 0 ]; then
    printf '  ok        %s\n' "$repo"
    continue
  fi

  if [ "$MODE" = "audit" ]; then
    printf '  drift     %s\n' "$repo"
    printf '            - %s\n' "${drift[@]}"
    status=1
    continue
  fi

  printf '  applying  %s\n' "$repo"
  gh api -X PATCH "repos/$ORG/$repo" --silent \
    -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
    -F allow_auto_merge=true -F delete_branch_on_merge=true
  gh api -X PATCH "repos/$ORG/$repo" --silent \
    -f 'security_and_analysis[secret_scanning][status]=enabled' \
    -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
  gh api -X PUT "repos/$ORG/$repo/automated-security-fixes" --silent

  # Only create a Main ruleset where none exists. Replacing an existing one would
  # discard the required status checks, which are chosen per repository.
  if [ "$(echo "$rulesets" | jq -r 'if type == "array" then ([.[] | select((.name | ascii_downcase) == "main")] | length) else 1 end')" = "0" ]; then
    ruleset_payload | gh api -X POST "repos/$ORG/$repo/rulesets" --silent --input -
    main_id=$(gh api "repos/$ORG/$repo/rulesets" --jq '[.[] | select((.name | ascii_downcase) == "main")][0].id // ""' 2>/dev/null || echo "")
  fi

  # Gate on the standards checks only once the repository actually runs them.
  if [ -n "$main_id" ] && has_standards_caller "$repo"; then
    require_standards_checks "$repo" "$main_id"
  fi

  if [ "$private" = "true" ]; then
    printf '            note: auto-merge, scanning and rulesets need GitHub Pro or Team on a private repository\n'
  fi
done

exit $status
