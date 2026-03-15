# TestMatrix.md — TeraChat Alpha v0.3.0

```yaml
# DOCUMENT IDENTITY
id:       "TERA-TEST"
title:    "TeraChat — Chaos Engineering & Test Matrix"
version:  "2.0"
audience: "QA Engineer, Security Engineer, Product Manager"
purpose:  "Đặc tả kịch bản kiểm thử (Test Matrix), đặc biệt là Chaos Engineering với các kịch bản hỏng hóc kết hợp (combined-failure scenarios) trước khi go-live."

ai_routing_hint: |
  "AI mở file này khi người dùng hỏi về kịch bản kiểm thử, stress test, edge cases, combined-failure scenarios, hoặc chuẩn bị go-live cho khối Gov/Military."
```

> **Status:** `ACTIVE — Pre-requisite for Gov/Military Contracts`
> **Audience:** QA Engineer · Security Engineer · Product Manager
> **Scope:** Combined-Failure Scenarios · Chaos Engineering
> **Last Updated:** 2026-03-15
> **Depends On:** → TERA-CORE, → TERA-FEAT, → TERA-FUNC
> **Consumed By:** QA, DevSecOps

---

## 1. [TEST] [SECURITY] Chaos Engineering Matrix: Tài liệu bắt buộc trước Gov go-live

Đây là yêu cầu **non-negotiable** với Government/Military customers. 7 combined-failure scenarios dưới đây phải được verified trước khi go-live:

| Scenario | Điều kiện | Expected behavior |
|---|---|---|
| SC-01 | iOS AWDL off + TURN failover + CRDT merge >5000 events | AWDL warn → BLE → TURN preconnect → CRDT queue |
| SC-02 | Jetsam kill NSE mid-WAL + Desktop offline + EMDP active | WAL rollback → DAG self-heal → EMDP key escrow |
| SC-03 | XPC Worker OOM + Smart Approval pending | Journal PENDING → abort → user re-sign prompt |
| SC-04 | Battery <20% + Mesh active + Whisper loading | Whisper disabled → Voice text-fallback → BLE only |
| SC-05 | AppArmor deny memfd + mlock + seccomp active | Graceful degrade to software crypto → performance warn |
| SC-06 | License expire T+0 + Active emergency call | Chat survives → Admin Console lock only |
| SC-07 | EMDP 60min + Desktop reconnect + 1000 relay messages | Key escrow decrypt → DAG merge → epoch reconcile |

---
