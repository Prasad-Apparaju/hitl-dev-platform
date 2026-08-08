# Observability survey (brownfield Step 6)

The full procedure for HITL's Step 6. Read this file and perform every part of it, then return to
`SKILL.md` Step 7.

Update `.hitl/current-change.yaml` — set `current_step`:
```yaml
  number: 6
  name: "Set up observability"
  phase: "Brownfield Setup"
```

HITL requires two observability layers: **application observability** (logs, metrics, tracing, alerting — so production failures are visible and pages fire) and **agentic observability** (session logs, token cost — so AI-assisted development costs and decisions are tracked). Both must be in place before the first Tier 2 change is deployed.

**1. Survey existing application observability:**

Check for evidence of each signal type:

| Signal | Where to look |
|---|---|
| Structured logs | Logger imports, `log4j.properties`, `logging.yaml`, Logback config, sidecar containers in k8s |
| Metrics | Prometheus scrape config, Datadog/CloudWatch agent config, `micrometer`/`actuator`, metrics libraries in package files |
| Distributed tracing | OpenTelemetry config, Jaeger/Zipkin clients, Datadog APM, trace headers in middleware |
| Error tracking | Sentry SDK, Rollbar client, error reporting middleware |
| Dashboards | `grafana/`, `datadog/monitors/`, CloudWatch dashboard JSON |
| Alerting | `grafana/alerts/`, `datadog/monitors/`, CloudWatch alarms, PagerDuty config |

Record what is present, what is absent, and which tool is in use for each signal type.

**2. Set up agentic observability:**

| Signal | Check | Action if missing |
|---|---|---|
| Session logs | `docs/session-logs/` is in `.gitignore` and `write-session-summary.sh` hook is wired | Step 0 handles this — flag if absent |
| Token cost registry | `docs/04-operations/token-cost-registry.yaml` exists | Copy from plugin template (see below) |

Create the token cost registry if it does not exist:
```bash
mkdir -p docs/04-operations
PLUGIN_ROOT=$(python3 -c "
import json,os,sys
try:
  d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
  for inst in d.get('plugins',{}).get('hitl@hitl',[]):
    p=inst.get('installPath','')
    if os.path.isfile(os.path.join(p,'.claude-plugin/plugin.json')):
      print(p);sys.exit(0)
except:pass
try:
  d=json.load(open(os.path.expanduser('~/.claude/settings.json')))
  for p in d.get('plugins',[]):
    path=p if isinstance(p,str) else p.get('path','')
    if os.path.isfile(os.path.join(path,'.claude-plugin/plugin.json')):
      print(path);sys.exit(0)
except:pass
" 2>/dev/null)
[[ ! -f docs/04-operations/token-cost-registry.yaml ]] && \
  cp "$PLUGIN_ROOT/shared/templates/token-cost-registry-template.yaml" \
     docs/04-operations/token-cost-registry.yaml
```

**3. Fill in ADR-0005:**

`docs/02-design/technical/adrs/adr-0005-observability-strategy.md` was copied in Step 0. Open it and fill in the tools found in step 1. Ask the architect:
> "Are the observability tools listed in ADR-0005 correct? Any planned changes? Who owns on-call for production incidents in each domain?"

**4. Flag gaps:**

| Gap | Severity | Action |
|---|---|---|
| No structured logging | 🔴 | Required before first Tier 2 deploy — add a structured logging library for the tech stack |
| No metrics or dashboards | 🟡 | Run `/hitl:ops-setup-observability` per change to instrument go/no-go criteria |
| No alerting or on-call routing | 🟡 | Must be configured before first production deploy — required by `/hitl:ops-deploy` |
| No error tracking | 🟢 | Recommended — Sentry free tier covers most projects |
| No distributed tracing | 🟢 | Optional for monoliths; required for microservices with cross-service calls |
| Token cost registry missing | 🟡 | Created above — update at Step 31 of every change |

**5. Persist the survey (required):** record `F1` in the readiness register (from Step 5):
`verified` with instrument names as evidence, or `gap` at the worst open row's severity with
the open rows listed. An unrecorded gap is invisible to the roadmap and the deploy gate.
