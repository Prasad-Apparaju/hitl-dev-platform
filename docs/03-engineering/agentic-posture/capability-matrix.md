# Capability matrix (generated — do not edit)

| capability | class | risk | ceiling | used_by |
|---|---|---|---|---|
| crm.read | tool | low | read:customer; read:order | account_service |
| llm.generate | model | low | invoke:completion | intake_agent, resolution_agent |
| refund.execute | tool | high | execute:refund | refund_service |
| session.memory | memory | med | read:session; write:session | resolution_agent |

