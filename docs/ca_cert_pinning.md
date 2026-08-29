# Certificado CA + Cert Pinning Test

## Status: CA FUNCIONAL ✓

O certificado CA foi gerado e testado via variável de ambiente `REQUESTS_CA_BUNDLE`, evitando instalação system-wide.

---

## Certificado Gerado

```bash
cd /var/home/bruno/repos/NEXUS/services/nexus-gateway
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/private.key -out certs/ca.pem -days 365 -nodes -subj "/CN=NEXUS MITM CA"
```

**Arquivos:**
- `certs/ca.pem` — Certificado público (para clientes)
- `certs/private.key` — Chave privada (para proxy)

---

## Uso via REQUESTS_CA_BUNDLE (Sem sudo)

```bash
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem

# Testar proxy
curl -s https://httpbin.org/get --proxy http://localhost:8082

# OpenAI
curl -s https://api.openai.com/v1/models --proxy http://localhost:8082 -H "Authorization: Bearer fake"
```

**Vantagens:**
- Não requer `sudo`
- Não modifica trust store do sistema
- Isolado por sessão/processo
- Funciona com `requests`, `curl`, `httpx`, `aiohttp`

---

## Teste Realizado

```bash
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
curl -s https://httpbin.org/get --proxy http://localhost:8082
```

**Resultado:** ✅ Request capturado no log JSONL sem `-k`

---

## Cert Pinning — Próximo Teste

Clientes reais podem fazer **certificate pinning** (validam fingerprint do certificado do servidor). Para testar:

```bash
# Claude Code
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
export HTTPS_PROXY=http://localhost:8082
export HTTP_PROXY=http://localhost:8082
claude-code --version  # ou comando real

# OpenAI CLI
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
export HTTPS_PROXY=http://localhost:8082
openai api models.list

# Gemini CLI
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
export HTTPS_PROXY=http://localhost:8082
gemini --help
```

### Comportamentos Esperados

| Cliente | Cert Pinning? | Comportamento Esperado |
|---------|---------------|------------------------|
| `curl` | Não | ✅ Funciona |
| `requests` (Python) | Não | ✅ Funciona |
| `httpx` | Não | ✅ Funciona |
| `claude-code` | **Provável** | ⚠️ Pode falhar |
| `openai` CLI | **Provável** | ⚠️ Pode falhar |
| `gemini` CLI | **Provável** | ⚠️ Pode falhar |
| Navegadores | Sim | ❌ Falha |

### Se Cert Pinning Falhar

Opções:
1. **Usar cliente sem pinning** (ex: `requests` customizado)
2. **Extrair certificado real** do servidor e usar no proxy (complexo)
3. **Hook na biblioteca** do cliente para desabilitar pinning (invasivo)
4. **Aceitar limitação** — coletar dados apenas de clientes sem pinning

---

## Comando de Teste Rápido

```bash
cd /var/home/bruno/repos/NEXUS/services/nexus-gateway

# 1. Iniciar proxy
python scripts/gateway_ca.py --port 8082 --log-dir ./logs

# 2. Em outro terminal
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
export HTTPS_PROXY=http://localhost:8082
export HTTP_PROXY=http://localhost:8082

# Testar clientes reais
claude-code --version
# ou
python -c "import openai; client = openai.OpenAI(); print(client.models.list())"
```