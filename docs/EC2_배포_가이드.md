# EC2 배포 가이드

로컬에서 docker compose로 검증된 앱을 AWS EC2에 올리는 절차.
DB는 이미 배포한 RDS를 사용 (EC2엔 db 컨테이너 없음).

## 1. EC2 인스턴스 생성

AWS 콘솔 → EC2 → Launch instance
- 이름: promptune-app
- AMI: Ubuntu 22.04 LTS
- 타입: t3.small (2GB) 권장 — t2.micro(1GB)는 빌드 시 메모리 부족 위험. 유료 주의
- 키 페어: 새로 생성 (.pem 저장)
- 스토리지: 20GB

보안 그룹 인바운드:
- 22 (SSH): 내 IP
- 80, 443: 0.0.0.0/0 (Nginx — HTTPS 적용 후엔 이 두 개만 있으면 됨. 5-2절 참고)
- 3000: 0.0.0.0/0 (프론트, HTTPS 붙이기 전 직접 테스트용 — 나중에 닫아도 됨)
- 8080: 0.0.0.0/0 (백엔드, HTTPS 붙이기 전 직접 테스트용 — 나중에 닫아도 됨)
- 8000: 0.0.0.0/0 (AI, 선택)

## 2. RDS 보안 그룹에 EC2 허용

RDS 보안그룹(Checkmate-promptune) 인바운드에 EC2 접근 추가:
- 유형: PostgreSQL (5432)
- 소스: EC2 보안그룹 또는 private IP

## 3. EC2 접속 + Docker 설치

    ssh -i promptune-key.pem ubuntu@<EC2_PUBLIC_IP>

    sudo apt update
    sudo apt install -y docker.io docker-compose-plugin git
    sudo usermod -aG docker ubuntu
Flyway가 RDS에 마이그레이션 자동 실행.
- 로그: docker compose -f docker-compose.prod.yml logs -f
    exit
    # 재접속

## 4. 코드 받기

    git clone https://github.com/bxbae/promptune-mockup.git
    cd promptune-mockup

## 5. 환경변수 설정

    ./scripts/setup-env.sh <도메인>
    # 예: ./scripts/setup-env.sh 54-180-115-193.nip.io
    nano .env.production

`setup-env.sh`가 `.env.production`을 (없으면 `.env.production.example`로부터) 만들고, 도메인 기반
URL 7개(`DOMAIN`, `APP_FRONTEND_URL`, `APP_CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, `OAUTH_REDIRECT_BASE`,
`MICROSOFT_REDIRECT_URI`, `MICROSOFT_FRONTEND_URL`)를 자동으로 채워준다 — 손으로 하나씩 고치다
빠뜨리는 실수를 막기 위함. 재실행해도 안전(그때마다 최신 도메인 기준으로 덮어씀).

이어서 `nano .env.production`으로 RDS 사용자명, 소셜 클라이언트 ID(있으면) 등 나머지 값만 채우면 된다.
**DB 비밀번호·JWT_SECRET·소셜 클라이언트 시크릿 등 민감한 값은 여기 직접 채우지 않는다** — 5-1 참고.

## 5-1. 시크릿 값 (AWS SSM Parameter Store)

민감한 값 7개(`SPRING_DATASOURCE_PASSWORD`, `JWT_SECRET`, `GOOGLE_CLIENT_SECRET`,
`KAKAO_CLIENT_SECRET`, `NAVER_CLIENT_SECRET`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TOKEN_KEY`)는
`.env.production`에 평문으로 직접 적지 않고, AWS SSM Parameter Store(`/promptune/prod/<KEY>`, SecureString)에
등록해두고 배포 때마다 스크립트로 가져온다.

사전 조건 (최초 1회):
- EC2에 붙어있는 IAM 역할(`promptune-ec2-s3-role`)에 `ssm:GetParameter`, `ssm:GetParametersByPath`,
  `kms:Decrypt`(`kms:ViaService=ssm.<region>.amazonaws.com` 조건) 권한 추가
- AWS 콘솔 → Systems Manager → Parameter Store에서 위 7개 값을 `/promptune/prod/<KEY>` 이름의
  SecureString으로 등록

배포 전에 아래 스크립트를 실행하면 `.env.production`의 시크릿 7개 라인만 SSM 최신값으로 덮어쓰고,
나머지 라인(URL·클라이언트 ID·플래그 등)은 그대로 둔다. 재실행해도 중복 없이 안전하게 갱신된다.

    ./scripts/fetch-secrets.sh

## 5-2. HTTPS (Nginx + Let's Encrypt)

Nginx가 리버스 프록시로 앞단에 서서 80/443을 받고, `/api`·`/login`·`/oauth2`는 backend로,
나머지는 frontend로 보낸다. 프론트/백엔드가 같은 도메인(오리진)을 쓰게 되어 CORS 문제도 줄어든다.
인증서는 Let's Encrypt에서 발급받고, `docker-compose.prod.yml`의 `certbot` 컨테이너가 자동으로 갱신한다.

**도메인이 없다면**: 무료로 [nip.io](https://nip.io)를 쓸 수 있다. 가입 없이
`<IP를-대시로-바꾼값>.nip.io`가 그 IP로 자동 resolve된다.
예: EC2 퍼블릭 IP가 `54.180.115.193`이면 `DOMAIN=54-180-115-193.nip.io`.

**주의**: EC2 퍼블릭 IP가 바뀌면(인스턴스 stop/start 등) 도메인도 그 IP를 다시 반영해야 하고
인증서도 새로 받아야 한다. Elastic IP를 붙여서 고정해두는 걸 권장하지만, 필수는 아니다.

1. `./scripts/setup-env.sh <도메인>` 로 도메인 기반 URL 7개를 채운다 (5번 참고 — 이미 했다면 생략).
2. 보안 그룹에 80, 443이 열려있는지 확인 (1번 참고).
3. 최초 인증서 발급 (도메인당 딱 1번만):

       ./scripts/init-letsencrypt.sh <도메인> [이메일]
       # 예: ./scripts/init-letsencrypt.sh 54-180-115-193.nip.io

4. 이후 배포는 6번과 동일 — `nginx`, `certbot` 컨테이너도 `docker compose up`에 같이 포함되어 있다.
5. 구글/카카오/네이버/MS 등 소셜 로그인 콘솔의 redirect URI도 새 `https://<도메인>` 기준으로
   갱신해야 한다 — 8번 참고.

## 6. 실행

    ./scripts/fetch-secrets.sh
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

주의: RDS 스키마가 비어 있어야 정식으로 밟음. 이미 테이블 있으면 병환에게 문의.
HTTPS를 아직 설정 안 했다면(5-2절), 이 시점엔 `http://<EC2_PUBLIC_IP>:3000`으로 직접 접속해서 확인해도 된다.

## 7. 확인

    docker compose -f docker-compose.prod.yml ps
    docker compose -f docker-compose.prod.yml logs backend | grep -i flyway

브라우저: `https://<도메인>` (5-2절까지 끝냈다면) 또는 `http://<EC2_PUBLIC_IP>:3000` (아직이면)

## 8. 소셜 로그인 (배포 후, 담당: 승연)

각 제공자 콘솔의 redirect URI를 새 도메인 기준으로 등록/수정한다 (HTTPS 적용 후엔 포트 번호 없이):
- 구글: `https://<도메인>/login/oauth2/code/google`
- 카카오: `https://<도메인>/login/oauth2/code/kakao`
- 네이버: `https://<도메인>/login/oauth2/code/naver`
- MS: `https://<도메인>/api/integrations/microsoft/callback` (`MICROSOFT_REDIRECT_URI`와 동일해야 함)

카카오/네이버는 개발 중 상태면 "멤버 관리"에 테스트 계정을 등록 + 해당 계정이 초대를 수락해야
로그인이 된다는 점도 참고.

## 운영 팁

- 중지: docker compose -f docker-compose.prod.yml down
- 업데이트: git pull 후 6번 재실행 (fetch-secrets.sh 포함)
- 비용 절약: 안 쓸 때 EC2 인스턴스 중지(stop) — 단, Elastic IP를 안 붙였다면 재시작 시 IP가 바뀌어서
  도메인·인증서를 다시 잡아야 할 수 있음. 그럴 땐 `./scripts/setup-env.sh <새-도메인>` 으로
  `.env.production`을 새 도메인 기준으로 다시 채운 뒤, `./scripts/init-letsencrypt.sh <새-도메인>`으로
  인증서를 새로 받으면 됨
- 시크릿 값 변경(비밀번호 교체 등): SSM Parameter Store에서 값만 갱신 후 6번 재실행 — 코드나 .env.production을 직접 안 고쳐도 됨
- 인증서 갱신: 자동(certbot 컨테이너, 12시간마다 체크). 수동 확인하고 싶으면
  `docker compose -f docker-compose.prod.yml logs certbot`

## 나중에 개선

- AI 모델 실제화 (메모리 큰 인스턴스 필요)
- CI/CD 자동 배포
