#!/usr/bin/env bash
set -euo pipefail

: "${VERCEL_API_TOKEN:?VERCEL_API_TOKEN is required}"
: "${VERCEL_AUTOMATION_BYPASS_SECRET:=}"
: "${TEAM_ID:?TEAM_ID is required}"
: "${FRONTEND_PROJECT_ID:?FRONTEND_PROJECT_ID is required}"
: "${BACKEND_PROJECT_NAME:?BACKEND_PROJECT_NAME is required}"
: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${GITHUB_REF:?GITHUB_REF is required}"
: "${GITHUB_REF_NAME:?GITHUB_REF_NAME is required}"
: "${EVIDENCE_PATH:?EVIDENCE_PATH is required}"

mkdir -p "$(dirname "$EVIDENCE_PATH")"
phase="initialization"
write_failure_evidence() {
  local exit_code=$?
  jq -n \
    --arg commit_sha "$GITHUB_SHA" \
    --arg phase "$phase" \
    --argjson exit_code "$exit_code" \
    '{
      schema_version:1,
      result:"FAILED",
      commit_sha:$commit_sha,
      phase:$phase,
      exit_code:$exit_code,
      message:"Deployment did not reach completed verification"
    }' >"$EVIDENCE_PATH"
  exit "$exit_code"
}
trap write_failure_evidence ERR

jq -n --arg commit_sha "$GITHUB_SHA" '{
  schema_version:1,
  result:"FAILED",
  commit_sha:$commit_sha,
  phase:"initialization",
  message:"Deployment did not reach completed verification"
}' >"$EVIDENCE_PATH"

vc() {
  npx --yes vercel@56.5.0 "$@"
}

retry_json_endpoint() {
  local url=$1
  local filter=$2
  local attempts=${3:-12}
  local delay_seconds=${4:-5}
  local response="$RUNNER_TEMP/retry-response.json"

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if curl -fsS "$url" >"$response" && jq -e "$filter" "$response" >/dev/null; then
      return 0
    fi
    if (( attempt < attempts )); then
      sleep "$delay_seconds"
    fi
  done

  cat "$response" >&2 || true
  return 1
}

phase="toolchain"
node --version
npm --version
vc --version

auth=(
  -H "Authorization: Bearer $VERCEL_API_TOKEN"
  -H "Content-Type: application/json"
)

phase="project-provisioning"
project_response="$RUNNER_TEMP/backend-project.json"
status=$(curl -sS -o "$project_response" -w '%{http_code}' \
  "https://api.vercel.com/v9/projects/$BACKEND_PROJECT_NAME?teamId=$TEAM_ID" \
  -H "Authorization: Bearer $VERCEL_API_TOKEN")
if test "$status" = "404"; then
  status=$(curl -sS -o "$project_response" -w '%{http_code}' \
    -X POST "https://api.vercel.com/v11/projects?teamId=$TEAM_ID" \
    "${auth[@]}" \
    --data "$(jq -n --arg name "$BACKEND_PROJECT_NAME" \
      '{name:$name,framework:"fastapi",serverlessFunctionRegion:"fra1"}')")
fi
case "$status" in
  200|201) ;;
  *)
    jq '{error:(.error.code // "project_request_failed")}' "$project_response" >&2 || true
    exit 1
    ;;
esac
backend_project_id=$(jq -er '.id' "$project_response")

# Keep the project preset explicit even when the project already existed.
curl -fsS -X PATCH \
  "https://api.vercel.com/v9/projects/$backend_project_id?teamId=$TEAM_ID" \
  "${auth[@]}" \
  --data '{"framework":"fastapi","serverlessFunctionRegion":"fra1"}' \
  | jq -e '.framework == "fastapi"' >/dev/null

env_response="$RUNNER_TEMP/backend-env.json"
curl -fsS \
  "https://api.vercel.com/v9/projects/$backend_project_id/env?teamId=$TEAM_ID" \
  -H "Authorization: Bearer $VERCEL_API_TOKEN" >"$env_response"
if ! jq -e '.envs[]? | select(.key == "AI_PLATFORM_LEARNER_STATE_SECRET")' \
  "$env_response" >/dev/null; then
  signing_secret=$(openssl rand -hex 32)
  curl -fsS -X POST \
    "https://api.vercel.com/v10/projects/$backend_project_id/env?upsert=true&teamId=$TEAM_ID" \
    "${auth[@]}" \
    --data "$(jq -n --arg value "$signing_secret" '[{
      key:"AI_PLATFORM_LEARNER_STATE_SECRET",
      value:$value,
      type:"sensitive",
      target:["preview","production"]
    }]')" >/dev/null
  unset signing_secret
fi

curl -fsS -X POST \
  "https://api.vercel.com/v10/projects/$backend_project_id/env?upsert=true&teamId=$TEAM_ID" \
  "${auth[@]}" \
  --data '[{
    "key":"AI_PLATFORM_ENVIRONMENT",
    "value":"production",
    "type":"plain",
    "target":["preview","production"]
  }]' >/dev/null

curl -fsS -X POST \
  "https://api.vercel.com/v10/projects/$FRONTEND_PROJECT_ID/env?upsert=true&teamId=$TEAM_ID" \
  "${auth[@]}" \
  --data '[{
    "key":"ENABLE_EXPERIMENTAL_COREPACK",
    "value":"1",
    "type":"plain",
    "target":["preview","production"]
  }]' >/dev/null

phase="backend-deployment"
VERCEL_ORG_ID="$TEAM_ID" VERCEL_PROJECT_ID="$backend_project_id" \
  vc deploy --cwd apps/api --yes --archive=tgz --prod --force \
    --token "$VERCEL_API_TOKEN" 2>&1 | tee "$RUNNER_TEMP/backend-deploy.txt"
backend_deployment_url=$(grep -Eo 'https://[A-Za-z0-9.-]+\.vercel\.app' \
  "$RUNNER_TEMP/backend-deploy.txt" | head -n 1)
test -n "$backend_deployment_url"

phase="backend-public-domain"
domains_response="$RUNNER_TEMP/backend-domains.json"
curl -fsS \
  "https://api.vercel.com/v9/projects/$backend_project_id/domains?teamId=$TEAM_ID" \
  -H "Authorization: Bearer $VERCEL_API_TOKEN" >"$domains_response"
backend_domain=$(jq -er '
  [.domains[]
   | select((.verified // true) == true)
   | select((.gitBranch // null) == null)
   | .name
   | select(endswith(".vercel.app"))][0]
' "$domains_response")
backend_url="https://$backend_domain"

# The runtime proxy cannot rely on a Vercel login or protection-bypass header.
# Verify the stable backend production domain publicly before publishing it.
phase="backend-public-verification"
retry_json_endpoint "$backend_url/health/live" '.status == "ok"'
retry_json_endpoint "$backend_url/api/v1/roles" \
  'length == 1 and .[0].id == "junior-python-backend-engineer"'

phase="frontend-connection"
if test "$GITHUB_REF" = "refs/heads/main"; then
  frontend_env=$(jq -n --arg value "$backend_url" '[{
    key:"AI_PLATFORM_API_BASE_URL",
    value:$value,
    type:"plain",
    target:["production"]
  }]')
  environment=production
else
  frontend_env=$(jq -n --arg value "$backend_url" '[{
    key:"AI_PLATFORM_API_BASE_URL",
    value:$value,
    type:"plain",
    target:["preview"]
  }]')
  environment=preview
fi
curl -fsS -X POST \
  "https://api.vercel.com/v10/projects/$FRONTEND_PROJECT_ID/env?upsert=true&teamId=$TEAM_ID" \
  "${auth[@]}" --data "$frontend_env" >/dev/null

phase="frontend-deployment"
frontend_args=(deploy --yes --archive=tgz --token "$VERCEL_API_TOKEN")
if test "$GITHUB_REF" = "refs/heads/main"; then
  frontend_args+=(--prod)
fi
VERCEL_ORG_ID="$TEAM_ID" VERCEL_PROJECT_ID="$FRONTEND_PROJECT_ID" \
  vc "${frontend_args[@]}" 2>&1 | tee "$RUNNER_TEMP/frontend-deploy.txt"
frontend_url=$(grep -Eo 'https://[A-Za-z0-9.-]+\.vercel\.app' \
  "$RUNNER_TEMP/frontend-deploy.txt" | tail -n 1)
test -n "$frontend_url"

phase="deployed-verification"
frontend_bypass=()
if test -n "$VERCEL_AUTOMATION_BYPASS_SECRET"; then
  frontend_bypass=( -H "x-vercel-protection-bypass: $VERCEL_AUTOMATION_BYPASS_SECRET" )
fi

page=$(curl -fsS "${frontend_bypass[@]}" "$frontend_url/")
grep -F "Career Atlas" <<<"$page" >/dev/null
grep -F "Learning service online" <<<"$page" >/dev/null

plan="$RUNNER_TEMP/deployed-plan.json"
curl -fsS "${frontend_bypass[@]}" \
  -H "Content-Type: application/json" \
  -X POST "$frontend_url/api/platform/plans" \
  --data '{
    "learner_name":"Deployment Evidence Learner",
    "target_role":"junior-python-backend-engineer",
    "weekly_hours":8,
    "experience_summary":"Backend deployment verification",
    "ratings":[
      {"competency_id":"python","score":2},
      {"competency_id":"testing","score":2}
    ]
  }' >"$plan"
jq -e '.state_token | length > 20' "$plan" >/dev/null
jq -e '.current_activity.id | length > 5' "$plan" >/dev/null

resume_payload="$RUNNER_TEMP/resume-payload.json"
jq '{state_token}' "$plan" >"$resume_payload"
curl -fsS "${frontend_bypass[@]}" \
  -H "Content-Type: application/json" \
  -X POST "$frontend_url/api/platform/plans/resume" \
  --data-binary "@$resume_payload" \
  | jq -e '.sequence == 0 and .completed_count == 0' >/dev/null

progress_payload="$RUNNER_TEMP/progress-payload.json"
jq '{state_token, activity_id:.current_activity.id, reflection:
  "The deployed API, same-origin proxy, signed resume, and progress transition were verified end to end."}' \
  "$plan" >"$progress_payload"
progress="$RUNNER_TEMP/deployed-progress.json"
curl -fsS "${frontend_bypass[@]}" \
  -H "Content-Type: application/json" \
  -X POST "$frontend_url/api/platform/progress" \
  --data-binary "@$progress_payload" >"$progress"
jq -e '.sequence == 1 and .completed_count == 1' "$progress" >/dev/null

phase="evidence-publication"
trap - ERR
jq -n \
  --arg commit_sha "$GITHUB_SHA" \
  --arg environment "$environment" \
  --arg backend_project_id "$backend_project_id" \
  --arg backend_deployment_url "$backend_deployment_url" \
  --arg backend_url "$backend_url" \
  --arg frontend_project_id "$FRONTEND_PROJECT_ID" \
  --arg frontend_url "$frontend_url" \
  --argjson initial_readiness "$(jq '.readiness_percent' "$plan")" \
  --argjson progressed_readiness "$(jq '.readiness_percent' "$progress")" \
  '{
    schema_version:1,
    result:"PASSED",
    commit_sha:$commit_sha,
    environment:$environment,
    backend:{
      project_id:$backend_project_id,
      deployment_url:$backend_deployment_url,
      public_url:$backend_url,
      public_access:"ok",
      health:"ok",
      role_catalog:"ok"
    },
    frontend:{project_id:$frontend_project_id,url:$frontend_url,page:"ok",proxy:"ok"},
    journey:{create:"ok",resume:"ok",progress:"ok",initial_readiness:$initial_readiness,progressed_readiness:$progressed_readiness}
  }' >"$EVIDENCE_PATH"
