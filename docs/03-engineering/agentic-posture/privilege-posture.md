# Privilege posture (generated — do not edit)

| domain | kind | principal | granted | uses |
|---|---|---|---|---|
| account_service | deterministic | sa-account | read:customer; read:order | crm.read:read:customer; crm.read:read:order |
| intake_agent | simple_agent | sa-intake | invoke:completion | llm.generate:invoke:completion |
| refund_service | deterministic | sa-refund | execute:refund | refund.execute:execute:refund |
| resolution_agent | simple_agent | sa-resolution | invoke:completion; read:session; write:session | llm.generate:invoke:completion; session.memory:read:session; session.memory:write:session |

