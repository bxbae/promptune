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
- 3000: 0.0.0.0/0 (프론트)
- 8080: 0.0.0.0/0 (백엔드)
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

    cp .env.production.example .env.production
    nano .env.production

채울 것: RDS 비밀번호, <배포주소>를 EC2 IP로, JWT_SECRET, 소셜키(있으면)

## 6. 실행

    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

주의: RDS 스키마가 비어 있어야 정식으로 밟음. 이미 테이블 있으면 병환에게 문의.

## 7. 확인

    docker compose -f docker-compose.prod.yml ps
    docker compose -f docker-compose.prod.yml logs backend | grep -i flyway

브라우저: http://<EC2_PUBLIC_IP>:3000

## 8. 소셜 로그인 (배포 후, 담당: 승연)

각 제공자 콘솔 redirect URI에 배포 주소 추가:
- http://<EC2_IP>:8080/login/oauth2/code/google (kakao, naver 동일)

## 운영 팁

- 중지: docker compose -f docker-compose.prod.yml down
- 업데이트: git pull 후 6번 재실행
- 비용 절약: 안 쓸 때 EC2 인스턴스 중지(stop)

## 나중에 개선

- HTTPS (도메인 + Nginx + Let's Encrypt)
- AI 모델 실제화 (메모리 큰 인스턴스 필요)
- CI/CD 자동 배포
