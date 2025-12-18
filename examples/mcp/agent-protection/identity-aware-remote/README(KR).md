# MCP Remote Vault 데모

HashiCorp Vault를 사용하여 MCP (Model Context Protocol) 서버가 사용자별 동적 자격증명을 관리하는 시스템 데모입니다.

## 목표

Remote MCP Server가 사용자마다 다른 자격증명을 올바르게 가져오는지 검증하는 것이 핵심 목표입니다.

HashiCorp의 공식 블로그 [Validated Patterns: AI Agent Identity with HashiCorp Vault](https://developer.hashicorp.com/validated-patterns/vault/ai-agent-identity-with-hashicorp-vault) 에서는 MCP 인증을 위해 JWT의 On-Behalf-Of (OBO) 토큰을 사용하는 방법을 설명합니다. 하지만 이 방식에서는 사용자별 자격증명 관리를 위한 구성이므로, JWT의 `sub` claim을 사용하여 Entity를 생성하고, 각 Entity에 대해 JWT auth method에 연결된 Entity alias를 생성하는 방식을 사용합니다.

## 아키텍처

![Architecture](flow-chart.svg)

## 데모

![MCP Remote Vault Demo](mcp-remote-vault-demo.gif)


### 구성 요소

- **Keycloak**: 사용자 인증 및 JWT 발급
- **HashiCorp Vault**: JWT 기반 인증 및 사용자별 자격증명 관리 (Policy Templating 사용)
  - **KV Secrets Engine**: Jira, Github 자격증명 저장
  - **Database Secrets Engine**: PostgreSQL 동적 자격증명 생성
- **PostgreSQL**: 관계형 데이터베이스 (MCP 서버용)
- **Streamlit Client**: 웹 UI에서 MCP 서버 선택 및 사용, 인증 흐름 추적 및 자격증명 디버깅 정보 표시
- **Remote MCP Servers** (FastMCP 기반): 
  - **Jira MCP Server**: Jira 이슈 및 프로젝트 관리
  - **Github MCP Server**: GitHub 저장소 및 이슈 관리
  - **PostgreSQL MCP Server**: PostgreSQL 데이터베이스 쿼리 및 관리
- **Mock Backend Services**: Jira 및 Github API 시뮬레이션

### 데이터 흐름

1. **초기화 단계**: `init-vault.sh` 스크립트가 Keycloak에서 사용자 목록을 조회하고, 각 사용자에 대해 Vault Entity를 사전 생성합니다 (Entity name = username, 예: "alice", "bob"). 각 Entity에 대해 JWT auth method에 연결된 Entity alias를 생성합니다 (alias name = 사용자 UUID, JWT의 `sub` claim 값).
2. **사용자 인증**: 사용자가 Streamlit Client를 통해 Keycloak에 로그인하여 JWT 토큰을 받습니다 (JWT의 `sub` claim에 사용자 UUID 포함)
3. **MCP 요청**: Streamlit Client가 선택한 MCP 서버(들)에 JWT 토큰과 함께 요청을 전송합니다 (다중 선택 가능)
4. **Vault 인증**: MCP 서버가 JWT를 Vault에 전달하면, Vault는 Keycloak의 JWKS URL을 통해 JWT 서명을 검증하고, 기존 Entity를 찾아 alias를 연결합니다
5. **자격증명 조회**: 
   - **KV Secrets (Jira, Github)**: Vault Policy Templating을 통해 사용자별 경로(`secret/data/users/{{identity.entity.name}}/*`)에 접근이 허용되며, MCP 서버가 Entity name을 사용하여 자격증명을 조회합니다
   - **Database Secrets (PostgreSQL)**: Vault Database Secrets Engine을 통해 동적 데이터베이스 자격증명을 생성합니다 (`database/creds/{{identity.entity.name}}`)
6. **API/DB 호출**: MCP 서버가 Vault에서 가져온 자격증명으로 Mock API 또는 PostgreSQL 데이터베이스를 호출합니다

## 핵심 개념

### 사용자별 자격증명 분리

각 사용자는 자신의 자격증명만 조회할 수 있습니다:

1. **Entity 사전 생성**: `init-vault.sh` 스크립트가 Keycloak에서 사용자 목록을 조회하고, 각 사용자에 대해 Vault Entity를 사전에 생성합니다. Entity name은 username (예: "alice", "bob")으로 설정되어 관리자가 쉽게 식별할 수 있습니다.
2. **Entity Alias 연결**: 각 Entity에 대해 JWT auth method에 연결된 Entity alias를 생성합니다. Alias name은 사용자 UUID (JWT의 `sub` claim 값)로 설정되어 JWT와 매칭됩니다.
3. **사용자 인증**: 사용자가 Keycloak으로 로그인하여 JWT 토큰을 받습니다 (JWT의 `sub` claim에 사용자 UUID 포함)
4. **Vault 인증**: MCP 서버가 JWT를 Vault에 전달하면, Vault는 Keycloak의 공개 키로 JWT 서명을 검증하고, JWT의 `sub` claim을 사용하여 기존 Entity alias를 찾아 Entity를 연결합니다.
5. **Policy Templating**: Vault Policy Templating을 통해 다음 경로 접근이 허용됩니다:
   - **KV Secrets**: `secret/data/users/{{identity.entity.name}}/*` (Jira, Github)
   - **Database Secrets**: `database/creds/{{identity.entity.name}}`, `database/roles/{{identity.entity.name}}` (PostgreSQL)
   Entity name은 username이므로 관리자가 쉽게 추적할 수 있습니다.
6. **자격증명 조회**: 
   - **KV Secrets**: MCP 서버가 Entity name을 사용하여 `secret/data/users/{entity_name}/jira` 또는 `secret/data/users/{entity_name}/github` 경로로 자격증명을 조회합니다.
   - **Database Secrets**: MCP 서버가 Entity name을 사용하여 `database/creds/{entity_name}` 경로로 동적 데이터베이스 자격증명을 생성합니다.
7. **접근 제어**: 각 사용자는 자신의 자격증명만 조회 가능하며, 다른 사용자의 자격증명에는 접근할 수 없습니다.

### Keycloak-Vault 통합

Vault는 Keycloak의 JWKS URL을 사용하여 JWT 토큰을 검증합니다:

- **JWKS URL**: `http://keycloak:8080/realms/mcp-demo/protocol/openid-connect/certs`
- **설정 위치**: `init-vault.sh` 스크립트에서 다음 명령으로 설정됩니다:
  ```bash
  vault write auth/jwt/config \
    jwks_url="http://keycloak:8080/realms/mcp-demo/protocol/openid-connect/certs" \
    bound_issuer="http://localhost:8080/realms/mcp-demo"
  ```
- **동작 원리**:
  1. Vault는 JWKS URL에서 Keycloak의 공개 키를 가져옵니다
  2. 공개 키를 사용하여 JWT 서명을 검증합니다
  3. `bound_issuer`를 통해 JWT의 `iss` claim이 Keycloak의 issuer와 일치하는지 확인합니다
  4. 검증이 성공하면, JWT의 `sub` claim을 기반으로 Entity를 생성합니다

## 시작하기

실행을 위해 필요한 사전 준비작업은 다음과 같습니다.
- Docker 및 Docker Compose 설치
- curl 및 Python 3

### 1. 서비스 시작

```bash
docker-compose up -d
```

### 2. Keycloak 초기화

Keycloak이 시작될 때까지 대기한 후 (약 30초), 초기화 스크립트 실행:

```bash
./init-keycloak.sh
```

### 3. Vault 초기화

Vault가 시작된 후 초기화 스크립트 실행:

```bash
./init-vault.sh
```

이 스크립트는 다음을 수행합니다:
- JWT 인증 방법 활성화
- Keycloak과의 통합 설정
- KV secrets engine 활성화 (Jira, Github용)
- Database secrets engine 활성화 (PostgreSQL용)
- PostgreSQL 연결 설정 및 동적 role 생성
- Keycloak에서 사용자 목록 조회
- 각 사용자에 대해 Vault Entity 사전 생성 (Entity name = username, 예: "alice", "bob")
- 각 Entity에 대해 JWT auth method에 연결된 Entity alias 생성 (alias name = 사용자 UUID)
- Policy Templating을 사용한 사용자별 정책 생성 (`{{identity.entity.name}}` 사용)
- JWT role 생성
- 사용자별 자격증명 초기화 (alice: Jira, Github, PostgreSQL / bob: Github, PostgreSQL)

### 4. 사용자 자격증명 확인

`init-vault.sh` 스크립트가 자동으로 다음 자격증명을 생성합니다:

- **alice**: Jira, Github, PostgreSQL 자격증명 모두 생성
- **bob**: Github, PostgreSQL 자격증명만 생성 (Jira는 없음 - 데모용)

수동으로 확인하거나 수정하려면:

```bash
# Alice의 Jira 자격증명 확인
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/alice/jira

# Alice의 Github 자격증명 확인
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/alice/github

# Alice의 PostgreSQL role 확인
docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/alice

# Bob의 Github 자격증명 확인
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/bob/github

# Bob의 PostgreSQL role 확인
docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/bob
```

**참고**: Entity name은 username (alice, bob)을 사용하므로 관리가 용이합니다.

## 사용 방법

### 1. Streamlit 클라이언트 접속

브라우저에서 http://localhost:8501 접속

### 2. 로그인

- **Username**: `alice` 또는 `bob`
- **Password**: `alice123` 또는 `bob123`

### 3. MCP 서버 선택 및 도구 로드

- 하나 이상의 MCP 서버 선택 (체크박스로 다중 선택 가능):
  - **Jira**: Jira 이슈 및 프로젝트 관리
  - **Github**: GitHub 저장소 및 이슈 관리
  - **PostgreSQL**: PostgreSQL 데이터베이스 쿼리 및 관리
- "Load Tools" 버튼 클릭

**인증 흐름 추적 (Authentication Flow Trace)**: "Load Tools" 클릭 시 자동으로 다음 정보가 표시됩니다:
- **Step 1-2**: 사용자 로그인 및 JWT 발급 정보
- **Step 3**: MCP 서버 요청 상태
- **Step 4-5**: Vault 인증 및 Entity 정보
- **Step 6**: 각 MCP 서버별 자격증명 상태
  - User ID (JWT의 `sub` claim)
  - Username, Email
  - Vault 경로
  - 마스킹된 자격증명 (보안을 위해 일부만 표시)
  - 자격증명 존재 여부 및 오류 정보

### 4. 도구 사용

각 도구를 확장하고 필요한 파라미터를 입력한 후 "Execute" 버튼 클릭

## 데모 시나리오

### 시나리오 1: 사용자별 자격증명 분리 검증

1. **alice로 로그인**
   - Streamlit에서 `alice` / `alice123`으로 로그인
   - MCP 서버 선택 (예: Jira, Github, PostgreSQL 중 하나 이상)
   - "Load Tools" 클릭
   - Authentication Flow Trace에서 자격증명 정보 확인:
     - User ID: alice의 UUID (JWT의 `sub` claim)
     - Entity Name: `alice` (사전 생성된 Entity name, username 사용)
     - Vault Path: 
       - Jira: `secret/data/users/alice/jira`
       - Github: `secret/data/users/alice/github`
       - PostgreSQL: `database/creds/alice`
     - Credentials: alice의 자격증명 (각 MCP 서버별로 표시)

2. **bob으로 로그인** (다른 브라우저/시크릿 모드)
   - Streamlit에서 `bob` / `bob123`으로 로그인
   - 동일한 MCP 서버 선택
   - "Load Tools" 클릭
   - Authentication Flow Trace에서 자격증명 정보 확인:
     - User ID: bob의 UUID (alice와 다름, JWT의 `sub` claim)
     - Entity Name: `bob` (사전 생성된 Entity name, username 사용)
     - Vault Path: 
       - Jira: 자격증명 없음 (Step 6 실패 표시)
       - Github: `secret/data/users/bob/github`
       - PostgreSQL: `database/creds/bob`
     - Credentials: bob의 자격증명 (alice와 다름)

**결과**: 각 사용자가 자신의 자격증명만 조회됨을 확인

### 시나리오 2: MCP 도구 실행

1. 도구 선택 (예: `get_issue`)
2. 파라미터 입력 (예: `issue_key`: PROJ-1)
3. "Execute" 클릭
4. 결과 확인 (사용자의 자격증명으로 Mock API 호출)

## 서비스 포트

- **Keycloak**: http://localhost:8080
- **Vault**: http://localhost:8200 (UI: http://localhost:8200/ui, root token: `root-token`)
- **PostgreSQL**: localhost:5432
- **Streamlit Client**: http://localhost:8501
- **Jira MCP Server**: http://localhost:3001
- **Github MCP Server**: http://localhost:3002
- **PostgreSQL MCP Server**: http://localhost:3003
- **Mock Jira API**: http://localhost:8001
- **Mock Github API**: http://localhost:8002

## 파일 구조

```
mcp-remote/
├── docker-compose.yml          # 모든 서비스 정의
├── init-keycloak.sh            # Keycloak 초기화 스크립트
├── init-vault.sh               # Vault 초기화 스크립트
├── README.md                   # 이 문서
├── flow-chart.svg              # 아키텍처 다이어그램
├── vault/
│   ├── config.hcl              # Vault 설정
│   └── setup.sh                # Vault 설정 스크립트
├── keycloak/
│   └── (디렉토리 - 현재 사용되지 않음)
├── mcp-servers/
│   ├── jira-server/
│   │   ├── main.py             # Jira MCP 서버
│   │   ├── requirements.txt    # Python 의존성
│   │   └── Dockerfile          # Docker 이미지 정의
│   ├── github-server/
│   │   ├── main.py             # Github MCP 서버
│   │   ├── requirements.txt    # Python 의존성
│   │   └── Dockerfile          # Docker 이미지 정의
│   └── postgresql-server/
│       ├── main.py             # PostgreSQL MCP 서버
│       ├── requirements.txt    # Python 의존성
│       └── Dockerfile          # Docker 이미지 정의
├── streamlit-client/
│   ├── app.py                  # Streamlit 웹 UI
│   ├── auth_trace.py           # 인증 흐름 추적 모듈
│   ├── requirements.txt       # Python 의존성
│   ├── Dockerfile              # Docker 이미지 정의
│   └── .streamlit/
│       └── config.toml         # Streamlit 설정
├── init-postgresql.sql         # PostgreSQL 초기화 스크립트
└── mock-services/
    ├── jira-api/
    │   ├── main.py             # Mock Jira API
    │   ├── requirements.txt    # Python 의존성
    │   └── Dockerfile          # Docker 이미지 정의
    └── github-api/
        ├── main.py             # Mock Github API
        ├── requirements.txt    # Python 의존성
        └── Dockerfile          # Docker 이미지 정의
```

## 문제 해결

### Keycloak이 시작되지 않음

PostgreSQL이 먼저 시작되어야 합니다:

```bash
docker-compose logs postgres
docker-compose logs keycloak
docker-compose restart keycloak
```

### Vault 설정 오류

Vault가 완전히 시작될 때까지 대기:

```bash
docker exec -e VAULT_TOKEN=root-token vault vault status
docker-compose logs vault
```

### MCP 서버 연결 오류

서비스 로그 확인:

```bash
docker-compose logs jira-mcp-server
docker-compose logs github-mcp-server
```

### 자격증명 조회 실패

Vault 정책이 올바르게 설정되었는지 확인:

```bash
docker exec -e VAULT_TOKEN=root-token vault vault policy read user-secrets
docker-compose logs vault
```

## 정리

모든 서비스 중지:

```bash
docker-compose down
```

볼륨까지 삭제:

```bash
docker-compose down -v
```

## 기술 스택

- **FastMCP**: MCP 서버 구현을 위한 Python 프레임워크
- **FastAPI**: MCP 서버의 HTTP 엔드포인트 제공
- **Policy Templating**: Vault의 동적 정책 생성 기능 (`{{identity.entity.name}}` 사용)
- **JWT Authentication**: Keycloak과 Vault 간의 인증
- **Vault Database Secrets Engine**: PostgreSQL 동적 자격증명 생성
- **Streamlit**: 웹 UI 및 인증 흐름 추적 시각화

## 참고 자료

- [HashiCorp Vault 문서](https://developer.hashicorp.com/vault)
- [Vault Policy Templating](https://developer.hashicorp.com/vault/tutorials/policies/policy-templating)
- [MCP Remote Protocol](https://modelcontextprotocol.io/docs/develop/connect-remote-servers)
- [Keycloak 문서](https://www.keycloak.org/documentation)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Validated Patterns: AI Agent Identity with HashiCorp Vault](https://developer.hashicorp.com/validated-patterns/vault/ai-agent-identity-with-hashicorp-vault)
