# Data layer scorecard

Mode: advisory. No baseline given; nothing to diff.

## Metrics

| Metric | Before | After |
|---|---|---|
| verification_rate.entities |  | 0.167 |
| verification_rate.fields |  | 0.105 |
| verification_rate.edges |  | 0.25 |
| entities_without_mapping |  | 1 |
| sources_not_extracted |  | 1 |
| evidence_age_days.oldest |  | 0 |
| evidence_age_days.newest |  | 0 |
| evidence_age_days.median |  | 0 |
| open_high_findings |  | 1 |
| negative_edges |  | 0 |
| answerable.yes |  | 3 |
| answerable.no |  | 1 |
| answerable.unconfirmed |  | 1 |
| answerable.total |  | 5 |
| collisions |  | 2 |

## Questions not answerable

- q:4 waits on ent:delivery-slot, map:delivery-slot/warehouse.delivery_slots.

1 question(s) have a needs list nobody confirmed; they count as not answerable.

## Collisions

- ent:delivery-slot and ent:shipment share synonym: delivery.
- ent:eta and ent:shipment share natural key ['order_no'] in src:shipments-db.

## Open high-severity findings

- fnd:1

Declared and not extracted: src:warehouse.

