# Guia de Instalação e Operação

Este guia descreve a instalação completa, inicialização, verificação das portas, uso dos canais de e-mail, aprovação inicial de segurança e encerramento seguro da plataforma **AulaRedes**.

## 1. Pré-requisitos

- **Sistema operacional:** Windows 10/11 (PowerShell) com **Docker Desktop** usando contêineres Linux.
- **Python 3.13+:** necessário no host para geração inicial de segredos (`scripts/configure.py`), coletores locais de recursos e vulnerabilidades, e execução dos scripts de verificação.
- **Node.js 20+ / npm** *(opcional)*: necessário apenas se você for compilar o frontend localmente ou rodar os testes unitários/E2E fora do Docker.
- **Internet na primeira construção:** necessária para baixar as imagens base do Docker (`python`, `coredns`, `prometheus`, `alertmanager`, `mailpit`, `postgres`, `syft`, `grype`) e dependências Python/Node.

## 2. Configuração inicial de segredos e ambiente

Na raiz do repositório, execute:

```powershell
python scripts/configure.py
```

O script cria/atualiza o arquivo local `.env` e os arquivos de segredo em `.runtime/secrets/` (`admin-password-hash` e `webhook-token`) sem sobrescrever segredos já existentes:

- `ADMIN_USERNAME` e `ADMIN_PASSWORD`: credenciais do dashboard (`:8000`) e do painel do web-demo (`:8011`).
- `LAB_TOKEN`: token usado para mutações no Laboratório, recalibração de tráfego e aprovação de integridade.
- `WEBHOOK_TOKEN`: segredo Bearer usado pelo Alertmanager ao enviar alertas para a API.
- `POSTGRES_ADMIN_PASSWORD`, `POSTGRES_MONITOR_PASSWORD`, `POSTGRES_WORKLOAD_PASSWORD`: credenciais isoladas dos papéis do PostgreSQL.

> **Segurança:** o arquivo `.env` e a pasta `.runtime/` estão no `.gitignore` e nunca devem ser versionados.

## 3. Subir a plataforma

### Opção A — Script automático (PowerShell)

```powershell
./scripts/start.ps1
```

### Opção B — Passo a passo manual

Caso a política de execução do PowerShell bloqueie scripts locais:

```powershell
python scripts/configure.py
docker compose up -d --build --wait
python scripts/scan_vulnerabilities.py --background
python scripts/collect_resources.py --background
```

> Os dois coletores locais (`scan_vulnerabilities.py` e `collect_resources.py`) rodam em segundo plano no host para manter a API sem acesso ao socket Docker e sem privilégios elevados. O coletor de recursos prepara automaticamente um ambiente Python próprio em `.runtime/resource-worker-venv`.

## 4. Verificação das portas e interfaces

Todas as portas são vinculadas apenas a `127.0.0.1` (ambiente acadêmico local):

| Serviço | URL / Porta | Função |
|---|---|---|
| **Dashboard Principal (Workbyte)** | `http://localhost:8000` | Landing → Login → Visão consolidada, métricas por serviço, recursos, segurança, incidentes e laboratório |
| **Documentação OpenAPI** | `http://localhost:8000/docs` | Swagger UI (protegido por sessão) |
| **Aplicação HTTP Demo + Simulador de Ataques** | `http://localhost:8011` | Landing 8-bit WORKBYTE → Login → Painel ao vivo e aba de simulação dos 8 ataques |
| **Serviço HTTP monitorado (`/work`)** | `http://localhost:8011/work` | Endpoint instrumentado pelas sondas e métricas HTTP |
| **Mailpit — Alertas da Plataforma** | `http://localhost:8025` | Caixa de e-mails para onde o Alertmanager envia notificações `warning` e `critical` |
| **Mailpit — Receptor do SMTP monitorado** | `http://localhost:8026` | Caixa final das mensagens enviadas pelo laboratório SMTP (`aluno@aularedes.test`) |
| **Prometheus** | `http://localhost:9090` | Séries temporais, alvos (`/targets`) e estado das regras (`/alerts`) |
| **Alertmanager** | `http://localhost:9093` | Agrupamento, deduplicação e roteamento de alertas |

## 5. Primeiros passos após subir

1. **Login no dashboard:** acesse `http://localhost:8000`, clique em **Entrar** e informe `ADMIN_USERNAME` e `ADMIN_PASSWORD` do seu `.env`.
2. **Aguardar baseline:** aguarde ~15 s para as primeiras taxas (`rate`) e ~2 minutos para o detector de tráfego formar a referência inicial dos 4 serviços.
3. **Aprovar integridade das configurações:** acesse `http://localhost:8000/#security` → **Integridade das configurações** → **Revisar e aprovar uma referência**, selecione as pendências e aprove com o `LAB_TOKEN` do `.env` (ou execute `python scripts/approve_integrity.py` se aplicável). Isso evita o alerta `ConfiguracaoReferenciaPendente`.
4. **Atualizar após editar arquivos em `infra/`:** ao modificar `infra/alerts.yml` ou `infra/prometheus.yml`, recarregue o Prometheus com:
   ```powershell
   docker compose restart prometheus
   ```

## 6. Encerrar e preservar histórico

Para parar a stack **preservando métricas (7 dias), banco PostgreSQL, histórico de incidentes e e-mails**:

```powershell
python scripts/scan_vulnerabilities.py --stop
python scripts/collect_resources.py --stop
./scripts/stop.ps1
```

Ou manualmente:

```powershell
python scripts/scan_vulnerabilities.py --stop
python scripts/collect_resources.py --stop
docker compose down
```

> **Atenção:** evite `docker compose down -v`, pois a flag `-v` apaga todos os volumes persistentes (`incidents`, `metrics`, `alerts`, `mail`, `postgres-data`, `smtp-data`, `smtp-mail`).

## 7. Ambiente de desenvolvimento local (fora dos containers)

Para desenvolver frontend ou backend com hot-reload (mantendo o container `api` parado ou em porta separada):

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt

# Frontend principal
cd frontend
npm ci
npm run dev   # Proxy automático de /api para 127.0.0.1:8000
```

Para os testes completos da aplicação, consulte a seção **Testes e verificações** no [README.md](../README.md).
