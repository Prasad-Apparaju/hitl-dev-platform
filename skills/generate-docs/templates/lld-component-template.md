# [Component Name]

> **Package:** `[category]/[component-name]`
> **Type:** Controller | Service | Model | Security | Config
> **Related HLD:** [Link to HLD document]

---

## 1. Overview

[Brief description of this component's purpose and role in the system.]

---

## 2. Class Diagram

```mermaid
classDiagram
    class ComponentName {
        -privateField: Type
        +publicField: Type
        +methodName(param: Type): ReturnType
        -helperMethod(): void
    }

    class DependencyName {
        +dependencyMethod(): Type
    }

    ComponentName --> DependencyName : uses
```

---

## 3. Methods

### `methodName(param: Type): ReturnType`

**Description:** [What this method does]

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `param` | `Type` | Yes | [Description] |

**Returns:** `ReturnType` — [Description of return value]

**Throws:**

| Error | Condition |
|-------|-----------|
| `NotFoundError` | When resource doesn't exist |
| `ValidationError` | When input is invalid |

**Example:**
```typescript
const result = await component.methodName(param);
```

---

### `anotherMethod(): void`

[Repeat the pattern above for each public method]

---

## 4. Sequence Diagrams

### [Flow Name]

```mermaid
sequenceDiagram
    participant Caller
    participant This as ComponentName
    participant Dep as DependencyName

    Caller->>This: methodName(param)
    This->>This: validate input
    This->>Dep: dependencyMethod()
    Dep-->>This: result
    This-->>Caller: processed result
```

---

## 5. Data Structures

### [DTO / Interface Name]

```typescript
interface ExampleDTO {
  id: string;
  name: string;
  createdAt: Date;
  metadata?: Record<string, unknown>;
}
```

---

## 6. Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `SETTING_NAME` | `string` | `"default"` | [Description] |

---

## 7. Error Handling

| Scenario | Error Type | HTTP Status | Recovery |
|----------|-----------|-------------|----------|
| Resource not found | `NotFoundError` | 404 | Return error message |
| Invalid input | `ValidationError` | 400 | Return validation details |

---

## 8. Related Components

- **Depends on:** [`DependencyName`](../services/dependency-name.md)
- **Used by:** [`ConsumerName`](../controllers/consumer-name.md)
- **Related model:** [`ModelName`](../models/model-name.md)
