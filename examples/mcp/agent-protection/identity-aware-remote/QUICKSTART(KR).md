# 빠른 시작 가이드

실행을 위해 필요한 사전 준비작업은 다음과 같습니다.
- Docker 및 Docker Compose 설치
- curl 및 Python 3

## 1. 서비스 시작

```bash
docker-compose up -d
```

## 2. Keycloak 초기화 (약 30초 대기 후)

```bash
# Keycloak이 준비될 때까지 대기
sleep 30

# Keycloak 초기화
./init-keycloak.sh
```

## 3. Vault 초기화

```bash
# Vault 초기화
./init-vault.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- JWT 인증 방법 활성화
- Keycloak 통합 설정
- KV secrets engine 활성화 (Jira, Github용)
- Database secrets engine 활성화 (PostgreSQL용)
- PostgreSQL 연결 설정 및 동적 role 생성
- Policy Templating을 사용한 사용자별 정책 생성
- JWT role 생성
- 사용자별 자격증명 초기화 (alice: Jira, Github, PostgreSQL / bob: Github, PostgreSQL)

## 4. 사용자 자격증명 확인 (선택사항)

`init-vault.sh` 스크립트가 자동으로 자격증명을 생성합니다:
- **alice**: Jira, Github, PostgreSQL 자격증명 모두 생성
- **bob**: Github, PostgreSQL 자격증명만 생성 (Jira는 없음 - 데모용)

자격증명을 확인하려면:

```bash
# Alice의 자격증명 확인
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/alice/jira
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/alice/github
docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/alice

# Bob의 자격증명 확인
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/bob/github
docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/bob
```

## 5. 접속

브라우저에서 http://localhost:8501 접속

**로그인 정보:**
- Username: `alice` / Password: `alice123`
- Username: `bob` / Password: `bob123`

## 6. 사용 방법

1. **로그인**: Keycloak으로 인증
2. **MCP 서버 선택**: 하나 이상의 MCP 서버 선택 (체크박스로 다중 선택 가능)
   - **Jira**: Jira 이슈 및 프로젝트 관리
   - **Github**: GitHub 저장소 및 이슈 관리
   - **PostgreSQL**: PostgreSQL 데이터베이스 쿼리 및 관리
3. **"Load Tools" 클릭**: 
   - 사용 가능한 도구 목록 로드
   - **인증 흐름 추적 (Authentication Flow Trace) 자동 표시**
4. **도구 선택 및 실행**: 원하는 도구를 선택하고 파라미터 입력 후 실행

## 인증 흐름 추적 (Authentication Flow Trace)

"Load Tools" 클릭 시 다음 정보가 자동으로 표시됩니다:

- **Step 1-2**: 사용자 로그인 및 JWT 발급 정보
- **Step 3**: MCP 서버 요청 상태
- **Step 4-5**: Vault 인증 및 Entity 정보
- **Step 6**: 각 MCP 서버별 자격증명 상태
  - **User Information**: User ID (JWT의 `sub`), Username, Email
  - **Vault Path**: 현재 사용자의 자격증명이 저장된 Vault 경로
  - **Credentials (Masked)**: 마스킹된 자격증명 (보안을 위해 일부만 표시)
  - **자격증명 존재 여부**: 각 MCP 서버별로 자격증명이 있는지 확인

이를 통해 각 사용자가 자신의 자격증명만 조회되는지 확인할 수 있습니다.

## 서비스 상태 확인

```bash
# 모든 서비스 상태
docker-compose ps

# 특정 서비스 로그
docker-compose logs -f streamlit-client
docker-compose logs -f jira-mcp-server
docker-compose logs -f vault
```

## 문제 해결

### Keycloak이 시작되지 않음
```bash
docker-compose logs keycloak
docker-compose restart keycloak
```

### Vault 설정 오류
```bash
docker exec -e VAULT_TOKEN=root-token vault vault status
docker-compose logs vault
```

### MCP 서버 연결 오류
```bash
docker-compose logs jira-mcp-server
docker-compose logs github-mcp-server
docker-compose logs postgresql-mcp-server
```

### 자격증명 조회 실패
```bash
# Vault 정책 확인
docker exec -e VAULT_TOKEN=root-token vault vault policy read user-secrets

# Vault 로그 확인
docker-compose logs vault
```
