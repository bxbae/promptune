#!/bin/bash
# .env.production을 도메인 기준으로 한 번에 생성/갱신하는 스크립트.
#
# 왜 필요한가: HTTPS(Nginx) 적용 때 DOMAIN·APP_FRONTEND_URL·APP_CORS_ORIGINS·NEXT_PUBLIC_API_URL·
# OAUTH_REDIRECT_BASE·MICROSOFT_REDIRECT_URI·MICROSOFT_FRONTEND_URL 이렇게 7개 줄을 nano/sed로
# 손으로 하나씩 바꾸다가 하나(OAUTH_REDIRECT_BASE)를 빠뜨려서 로그인이 깨진 적이 있음.
# 이 스크립트는 도메인 하나만 인자로 주면 이 7개를 한 번에, 실수 없이 채운다. 재실행해도 안전
# (매번 값을 덮어쓸 뿐 중복으로 쌓이지 않음).
#
# 하는 일:
#   1) .env.production이 없으면 .env.production.example을 복사해서 새로 만듦
#   2) 도메인 기반 URL 7개를 지정한 도메인으로 덮어씀 (그 외 나머지 줄은 그대로 둠)
#   3) --with-secrets 를 주면 이어서 scripts/fetch-secrets.sh 도 실행해서 SSM 시크릿까지 반영
#
# 사용법:
#   ./scripts/setup-env.sh <도메인> [--with-secrets]
#   예: ./scripts/setup-env.sh 54-180-115-193.nip.io
#       ./scripts/setup-env.sh 54-180-115-193.nip.io --with-secrets

set -euo pipefail

DOMAIN="${1:?사용법: ./scripts/setup-env.sh <도메인> [--with-secrets]}"
WITH_SECRETS="${2:-}"
ENV_FILE=".env.production"
EXAMPLE_FILE=".env.production.example"

if [ ! -f "$ENV_FILE" ]; then
  if [ ! -f "$EXAMPLE_FILE" ]; then
    echo "$EXAMPLE_FILE 을 찾을 수 없습니다. 프로젝트 루트(promptune-mockup)에서 실행해주세요." >&2
    exit 1
  fi
  echo "$ENV_FILE 이 없어서 $EXAMPLE_FILE 로부터 새로 만듭니다."
  cp "$EXAMPLE_FILE" "$ENV_FILE"
fi

BASE_URL="https://${DOMAIN}"

declare -A URL_VARS=(
  [DOMAIN]="$DOMAIN"
  [APP_FRONTEND_URL]="$BASE_URL"
  [APP_CORS_ORIGINS]="$BASE_URL"
  [NEXT_PUBLIC_API_URL]="$BASE_URL"
  [OAUTH_REDIRECT_BASE]="$BASE_URL"
  [MICROSOFT_REDIRECT_URI]="$BASE_URL/api/integrations/microsoft/callback"
  [MICROSOFT_FRONTEND_URL]="$BASE_URL"
)

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

# 기존 값 제거 후 새로 덮어씀 (재실행해도 중복 없이 안전)
PATTERN="^($(IFS='|'; echo "${!URL_VARS[*]}"))="
grep -vE "$PATTERN" "$ENV_FILE" > "$TMP_FILE" || true
for KEY in "${!URL_VARS[@]}"; do
  echo "${KEY}=${URL_VARS[$KEY]}" >> "$TMP_FILE"
done

mv "$TMP_FILE" "$ENV_FILE"
trap - EXIT
chmod 600 "$ENV_FILE"

echo "완료: ${ENV_FILE}의 도메인 기반 URL 7개를 ${BASE_URL} 기준으로 채웠습니다."

if [ "$WITH_SECRETS" = "--with-secrets" ]; then
  echo ""
  echo "이어서 SSM에서 시크릿을 가져옵니다..."
  ./scripts/fetch-secrets.sh "$ENV_FILE"
fi
