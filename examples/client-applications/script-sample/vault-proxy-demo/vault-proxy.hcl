# =============================================================================
# Vault Proxy 설정 파일 (데모용)
# =============================================================================
# 이 설정은 데모 목적으로 root token을 사용합니다.
# 운영 환경에서는 적절한 인증 방법을 사용하세요.
# =============================================================================

# Vault Proxy 리스너 설정
listener "tcp" {
  address = "127.0.0.1:8400"
  tls_disable = true
}

# Vault 서버 연결 설정
vault {
  address = "http://127.0.0.1:8200"
}

# 자동 인증 설정 (root token 사용)
auto_auth {
  method "token_file" {
    config = {
      token_file_path = "./token"
    }
  }
  
  sink "file" {
    config = {
      path = "./token"
    }
  }
}

# 캐시 설정
cache {
  use_auto_auth_token = true
}

# API 프록시 설정
api_proxy {
  use_auto_auth_token = true
}

# 로그 설정
log_level = "INFO"
log_file = "./vault-proxy.log"
