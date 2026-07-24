# Topology (generated — do not edit)

Orchestration: **sequential**

```mermaid
graph LR
  account_service[account_service<br/>deterministic]
  intake_agent{{intake_agent<br/>simple_agent}}
  refund_service[refund_service<br/>deterministic]
  resolution_agent{{resolution_agent<br/>simple_agent}}
  intake_agent -->|classify_to_lookup| account_service
  intake_agent -->|lookup_to_resolve| resolution_agent
  resolution_agent -. async .->|propose_refund| refund_service
  refund_service -. event .->|refund_executed_event| account_service
```

