# Projections (generated — do not edit; derived from `interactions`, §2.4)

## interaction_matrix

| edge | entity crossing |
|---|---|
| intake_agent -> account_service | CustomerRef -> AccountView |
| intake_agent -> resolution_agent | ClassifiedRequest -> DraftResolution |
| refund_service -> account_service | RefundExecuted |
| resolution_agent -> refund_service | RefundProposal -> RefundReceipt |

## depends_on

- **intake_agent** → account_service, resolution_agent
- **refund_service** → account_service
- **resolution_agent** → refund_service

## events

- refund_service emits `refund_executed` → account_service

