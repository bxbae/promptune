#!/bin/bash
# Let's Encrypt 인증서 최초 발급용 스크립트. 도메인당 딱 1번만 실행하면 됨
# (이후 갱신은 docker-compose.prod.yml의 certbot 컨테이너가 자동으로 12시간마다 체크해서 처리).
#
# 왜 필요한가: nginx는 443(https) 설정에 인증서 파일이 있어야 기동되는데, 처음엔 인증서가
# 아직 없음. 그래서 순서를 이렇게 함:
#   1) nginx를 잠깐 내림 (80번 포트를 비워서 인증서 발급용 임시 서버와 충돌 안 나게)
#   2) certbot을 standalone 모드로 잠깐 띄워서 진짜 인증서를 발급받음 (80번 포트 임시 사용)
#   3) 인증서가 생겼으니 nginx를 다시 올림
#
# 사전 조건:
#   - 이 도메인이 지금 이 EC2의 퍼블릭 IP로 정상적으로 resolve 되어야 함 (nip.io면 자동으로 됨)
#   - 보안 그룹에 80번 포트가 0.0.0.0/0 으로 열려있어야 함 (443도 미리 열어두는 걸 권장)
#   - .env.production에 DOMAIN 값이 설정되어 있어야 함
#
# 사용법:
#   ./scripts/init-letsencrypt.sh <도메인> [이메일]
#   예: ./scripts/init-letsencrypt.sh 54-180-115-193.nip.io
#       ./scripts/init-letsencrypt.sh 54-180-115-193.nip.io me@example.com

set -euo pipefail

DOMAIN="${1:?사용법: ./scripts/init-letsencrypt.sh <도메인> [이메일]}"
EMAIL="${2:-}"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

mkdir -p certbot/conf certbot/www

echo "=== 1/3: nginx를 잠깐 내립니다 (80번 포트 확보) ==="
$COMPOSE stop nginx 2>/dev/null || true

echo "=== 2/3: Let's Encrypt에서 ${DOMAIN} 인증서를 발급받습니다 (standalone, 80번 포트 임시 사용) ==="
EMAIL_ARGS="--register-unsafely-without-email"
if [ -n "$EMAIL" ]; then
  EMAIL_ARGS="--email $EMAIL --no-eff-email"
fi

docker run --rm \
  -p 80:80 \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --standalone \
  -d "$DOMAIN" \
  $EMAIL_ARGS \
  --agree-tos \
  --non-interactive

echo "=== 3/3: nginx를 발급받은 인증서와 함께 다시 올립니다 ==="
$COMPOSE up -d nginx

echo ""
echo "완료! https://${DOMAIN} 으로 접속해보세요."
echo "인증서 자동 갱신은 docker-compose.prod.yml의 certbot 컨테이너가 앞으로 계속 처리합니다."
