# Ambiente Experimental — Captura de Tráfego MITM

## Status: FUNCIONAL ✓

O proxy MITM (`gateway_ca.py`) está operacional e capturando tráfego real.

---

## Componentes Validados

| Componente | Status | Observação |
|------------|--------|------------|
| `mitmproxy` 12.2.3 | ✓ Instalado | Via pip com binary wheel |
| `gateway_ca.py` | ✓ Executando | Porta 8082 (8080 ocupada) |
| Captura JSONL | ✓ Funcional | Log estruturado por request |
| Pass-through TLS | ✓ Funcional | `curl -k --proxy` funcionou |
| Detecção de provider | ✓ Parcial | "unknown" para httpbin.org |

---

## Log Gerado (Exemplo)

```json
{
  "request_id": "f633d4d9-f756-4ee6-bc3f-5d75755633e0",
  "timestamp_start": "2026-08-29T18:49:57.554473+00:00",
  "timestamp_end": "2026-08-29T18:49:57.696205+00:00",
  "duration_ms": 142.32,
  "method": "GET",
  "url": "https://httpbin.org/get",
  "host": "httpbin.org",
  "path": "/get",
  "provider": "unknown",
  "request_headers": {"user-agent": "curl/8.18.0", "accept": "*/*"},
  "request_body_size": 0,
  "response_status": 200,
  "response_headers": {...},
  "response_body_size": 257,
  "error_type": null,
  "token_count_request": null,
  "token_count_response": null,
  "token_count_total": null
}
```

---

## Requisitos Procedentes (F1 — Captura Baseline)

### 1. Infraestrutura
- [x] Proxy MITM com CA custom (mitmproxy)
- [x] Log JSONL estruturado por request
- [x] Pass-through TLS sem modificação
- [x] Extração de metadados: headers, body size, latency, status

### 2. Detecção de Provider (Pendente)
- [ ] Mapear hosts conhecidos: `api.anthropic.com`, `api.openai.com`, `generativelanguage.googleapis.com`, etc.
- [ ] Extrair token counts de responses (OpenAI, Anthropic, Gemini formats)
- [ ] Classificar erro types: 429, 403, 500, 502, 503

### 3. Coleta de Baseline (7 dias)
- [ ] Executar clientes legítimos via proxy:
  - `HTTPS_PROXY=http://localhost:8082 claude-code ...`
  - `HTTPS_PROXY=http://localhost:8082 python -m openai ...`
  - `HTTPS_PROXY=http://localhost:8082 gemini-cli ...`
- [ ] Mínimo 10.000 requests por perfil
- [ ] Segmentar por: provedor, tipo de tarefa, horário

### 4. Armazenamento e Análise
- [ ] Logs em `/var/home/bruno/repos/NEXUS/services/nexus-gateway/logs/`
- [ ] Pipeline: JSONL → Parquet → Análise espectral (`spectral.py`)
- [ ] Integração com `humanoid-traffic/src/spectral.py`

---

## Impedimentos Conceituais Identificados

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| Provider detecta MITM via cert pinning | ALTA | Testar com clientes reais; alguns fazem pinning |
| Cliente rejeita CA não confiável | MÉDIA | Instalar CA no trust store do sistema/cliente |
| Volume de logs (7 dias × 10k reqs) | BAIXA | Rotate logs diários; compressão gzip |
| Correlação request→response em streaming | MÉDIA | Buffer por request_id; handle SSE |

---

## Aproveitamento em Outro Campo (Se F1 Falhar)

Se a captura de tráfego de provedores reais for bloqueada (cert pinning, detecção de MITM), a pesquisa **não é perdida**:

1. **Modelo Espectral (`spectral.py`)** — Independente de fonte de dados; aplica-se a qualquer série temporal
2. **Simulador Humanoide (`generator.py`)** — Gera tráfego sintético com assinatura 1/f para testes
3. **Detetor Híbrido (`detector.py`)** — Classifica padrões sem precisar de dados reais
4. **Otimizador de Throughput (`optimizer.py`)** — Calcula limites teóricos

Esses componentes podem ser usados para:
- **Análise de tráfego de rede** (DDoS detection, anomaly detection)
- **Modelagem de comportamento de usuário** (UX, product analytics)
- **Sistemas de rate limiting adaptativo** (API gateways genéricos)
- **Pesquisa em séries temporais financeiras** (mesma matemática 1/f)

---

## Próximos Passos

1. **Corrigir detecção de provider** em `gateway_ca.py` (mapear hosts conhecidos)
2. **Adicionar extração de tokens** para formats OpenAI/Anthropic/Gemini
3. **Instalar CA no cliente** (evitar `curl -k`)
4. **Executar coleta de 7 dias** com clientes reais
5. **Integrar com `humanoid-traffic`** para análise espectral automática

---

## Comandos de Operação

```bash
# Iniciar proxy (porta 8082)
cd /var/home/bruno/repos/NEXUS/services/nexus-gateway
python scripts/gateway_ca.py --port 8082 --log-dir ./logs

# Usar cliente via proxy
export HTTPS_PROXY=http://localhost:8082
export HTTP_PROXY=http://localhost:8082
# Adicionar CA ao trust store se necessário

# Ver logs
cat logs/*.jsonl | jq .

# Parar
pkill -f gateway_ca.py
```