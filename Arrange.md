# Arrange.md — Ánh xạ Chỉnh sửa Chính xác vào 8 File Nguồn

```yaml
# §0 DOCUMENT IDENTITY
id:                   "TERA-ARRANGE"
title:                "TeraChat — Conflict Resolution & Edit Mapping Specification"
version:              "2.0.0"
status:               "ACTIVE — Sprint Reference"
date:                 "2026-03-21"
audience:             "Tech Lead, Platform Engineer, Security Engineer, Sprint Planner"
purpose:              >
  Nguồn sự thật duy nhất cho tất cả chỉnh sửa cần áp dụng vào 8 file tài liệu nguồn
  của TeraChat. Mỗi chỉnh sửa có: ID duy nhất, file đích, section mục tiêu,
  loại thay đổi, nội dung cụ thể (find/replace hoặc append), conflict ID liên kết,
  và sprint assignment.

scope:                >
  Tất cả thay đổi cần thiết cho TeraChat Alpha v0.3.0 trước platform release.
  Bao gồm: bug/conflict fixes (C-xx, M-xx, T-xx, B-xx, D-xx, O-xx),
  enhancement additions (C-12 đến C-21, F-xx, D-xx), và technical debt (TD-xx).

non_goals:
  - "Implement code thực tế — đây là spec, không phải implementation"
  - "Thay đổi kiến trúc cốt lõi — chỉ clarify, fix, và extend"
  - "Thay đổi Function.md ngoài FUNC-12 đến FUNC-14"

assumptions:
  - "Core_Spec.md v3.0 là nguồn sự thật cho crypto/infra — Arrange.md chỉ patch vào đó"
  - "Feature_Spec.md hiện tại rỗng hoàn toàn — cần tạo mới"
  - "ops/signing-pipeline.md chưa tồn tại — cần tạo mới"
  - "Introduction.md tồn tại nhưng không được list trong 8 file chính thức"

constraints_global:
  - "KHÔNG làm mất bất kỳ nội dung kỹ thuật nào từ source"
  - "KHÔNG thay đổi TERA-ID, section numbering, hoặc cross-reference trong source files"
  - "Mọi thay đổi PHẢI backward-compatible với WAL replay (DB schema changes)"
  - "Mọi code snippet PHẢI nhất quán với ring crate / RustCrypto (không self-implement crypto)"
  - "ZeroizeOnDrop bắt buộc cho mọi struct mới giữ key material"

breaking_changes_policy: >
  Edit nào thay đổi: MLS epoch format, CRDT schema, Crypto Host ABI, Host Function API
  → Phải ghi chú [BREAKING] và yêu cầu major version bump tương ứng.
  Minor edit = additive only, không breaking. Deprecation window: 12 tháng.

files_covered:
  - "Core_Spec.md        (TERA-CORE)"
  - "Feature_Spec.md     (TERA-FEAT) — TẠO MỚI"
  - "Design.md           (TERA-DESIGN)"
  - "Function.md         (TERA-FUNC)"
  - "BusinessPlan.md     (TERA-BIZ)"
  - "Web_Marketplace.md  (TERA-MKT)"
  - "TestMatrix.md       (TERA-TEST)"
  - "ops/signing-pipeline.md — TẠO MỚI"

depends_on:
  - "Core_Spec.md v3.0 (TERA-CORE)"
  - "Conflict Analysis Report 2026-03-21 (input để tạo EDIT C-01 đến C-11)"
```

---

## §1 EXECUTIVE SUMMARY

### 1.1 Mục tiêu

Arrange.md là **master edit mapping document** — nguồn sự thật duy nhất cho tất cả thay đổi cần áp dụng vào 8 file tài liệu nguồn của TeraChat trước bất kỳ platform release nào.

**Hai loại thay đổi:**

| Loại | Mô tả | Số lượng |
|---|---|---|
| **Bug / Conflict Fix** | Resolve xung đột kỹ thuật cross-platform đã được phân tích | 12 conflicts → 22 edits |
| **Enhancement Addition** | Thêm nội dung còn thiếu vào docs hiện có hoặc tạo docs mới | 25 edits |
| **Technical Debt** | Tracked items cho post-Beta | 4 items |

### 1.2 Tóm tắt 5 Conflict Quan trọng nhất

| ID | Conflict | Impact nếu không fix | File |
|---|---|---|---|
| RC-03 | NSE RAM additive overflow (20MB ceiling violated) | Jetsam kill → notification mất silently | Core_Spec.md |
| PB-01 | Feature_Spec.md rỗng hoàn toàn | 34+ TERA-CORE references không resolve | Feature_Spec.md |
| RC-02 | Android Doze + mlock() gap | Key material exposed mid-freeze | Core_Spec.md |
| BL-02 | EMDP Shun → MLS epoch causal deadlock | iOS Mesh frozen, cannot evict compromised node | Core_Spec.md |
| NI-01 | QUIC parallel probe race → NetworkProfile corruption | `strict_compliance=true` set incorrectly | Core_Spec.md |

### 1.3 Kiến trúc tổng quan của quá trình edit

```
Arrange.md (nguồn sự thật)
    │
    ├── SPRINT 1 (Blocker)
    │   ├── Core_Spec.md     ← EDIT C-01 đến C-11 (fix) + C-12 đến C-21 (enhance)
    │   └── Feature_Spec.md  ← Tạo mới hoàn toàn (§1–§8)
    │
    ├── SPRINT 2 (High Priority)
    │   ├── Design.md        ← EDIT D-01 đến D-07
    │   ├── Web_Marketplace.md ← EDIT M-01 đến M-06
    │   ├── Function.md      ← EDIT FUNC-01 đến FUNC-05
    │   ├── TestMatrix.md    ← EDIT T-01 đến T-03
    │   ├── BusinessPlan.md  ← EDIT B-01 đến B-04
    │   └── ops/signing-pipeline.md ← Tạo mới (COSIGN-01 đến 05)
    │
    └── SPRINT 3 (Technical Debt)
        ├── Core_Spec.md     ← TD-01 đến TD-03
        └── Web_Marketplace.md ← TD-04
```

---

## §2 SYSTEM OVERVIEW

### 2.1 Sơ đồ phụ thuộc giữa 8 file nguồn

```
Core_Spec.md (TERA-CORE)     ← ROOT — không phụ thuộc file nào
    │
    ├──► Feature_Spec.md (TERA-FEAT)     ← phụ thuộc TERA-CORE
    │        │
    │        ├──► Design.md (TERA-DESIGN) ← đọc CoreSignal từ TERA-FEAT
    │        └──► Web_Marketplace.md (TERA-MKT) ← đọc WASM constraints từ TERA-FEAT
    │
    ├──► Function.md (TERA-FUNC)         ← phụ thuộc TERA-CORE + TERA-FEAT
    │
    ├──► TestMatrix.md (TERA-TEST)       ← phụ thuộc tất cả để viết test scenarios
    │
    ├──► BusinessPlan.md (TERA-BIZ)      ← phụ thuộc TERA-CORE cho technical claims
    │
    └──► ops/signing-pipeline.md         ← độc lập, referenced by TERA-FEAT §16
```

### 2.2 Quy tắc lan truyền edit

- Edit vào `Core_Spec.md` → có thể cần update cross-reference trong tất cả file phụ thuộc.
- Edit vào `Feature_Spec.md` → chỉ ảnh hưởng `Design.md` và `Web_Marketplace.md`.
- Edit vào `TestMatrix.md` → không ảnh hưởng file khác (leaf node).
- Edit vào `ops/signing-pipeline.md` → được referenced bởi `Feature_Spec.md §16` và `BusinessPlan.md`.

### 2.3 Deployment model của edits

Edits được apply theo thứ tự strict:

1. `Core_Spec.md` (root — không phụ thuộc)
2. `Feature_Spec.md` (phụ thuộc Core_Spec)
3. Các file còn lại song song (không phụ thuộc lẫn nhau trong sprint này)

**Không** apply Feature_Spec.md edits trước khi Core_Spec.md edits đã merge và stable.

---

## §3 DATA MODEL

### 3.1 ConflictRecord

| Field | Type | Mô tả |
|---|---|---|
| `conflict_id` | String (`RC-xx`, `PB-xx`, `BL-xx`, `NI-xx`) | ID duy nhất của conflict |
| `layer` | Enum `L1\|L2\|L3\|L4\|L5` | Lớp conflict (Runtime / Packaging / Logic / Network / Emergent) |
| `severity` | Enum `Blocker\|High\|Medium` | Mức độ ưu tiên |
| `platforms_affected` | `Vec<Platform>` | Platforms bị ảnh hưởng |
| `source_file` | String | File nguồn chứa conflict |
| `impact_if_unresolved` | String | Hậu quả nếu không fix |
| `edit_ids` | `Vec<EditId>` | Danh sách edits để resolve |

### 3.2 EditRecord

| Field | Type | Mô tả |
|---|---|---|
| `edit_id` | String (`C-xx`, `F-xx`, `D-xx`, `M-xx`, `T-xx`, `B-xx`, `FUNC-xx`, `O-xx`) | ID duy nhất |
| `conflict_id` | `Option<String>` | Conflict liên kết (None nếu là enhancement) |
| `target_file` | String | File đích để apply |
| `target_section` | String | Section trong file đích |
| `change_type` | Enum `Append\|Replace\|CreateNew` | Loại thay đổi |
| `find` | `Option<String>` | Chuỗi cần tìm (cho Replace) |
| `content` | String | Nội dung cần thêm/thay thế |
| `sprint` | Enum `Sprint1\|Sprint2\|Sprint3` | Sprint assignment |
| `status` | Enum `TODO\|InProgress\|Done\|Verified` | Trạng thái hiện tại |

### 3.3 TechnicalDebtItem

| Field | Type | Mô tả |
|---|---|---|
| `debt_id` | String (`TD-xx`) | ID duy nhất |
| `target_file` | String | File đích |
| `target_section` | String | Section cần update |
| `description` | String | Mô tả debt |
| `priority` | String | Sprint 3 / Post-Beta |
| `blocking` | `Vec<EditId>` | Edits khác bị block bởi debt này |

---

## §4 FEATURE MODEL

> Mỗi edit là một "feature" của Arrange.md — có Description, Target, User Flow (= procedure áp dụng), Dependencies, và Content đầy đủ.
> Tổ chức theo: Sprint → File → Edit ID.

---

### SPRINT 1 — BLOCKER

---

#### FILE 1: `Core_Spec.md`

---

##### EDIT C-01

```yaml
edit_id:       "C-01"
conflict_id:   "RC-01"
target_file:   "Core_Spec.md"
target_section: "§3.1 Platform Matrix (hoặc §7 Platform Matrix)"
change_type:   "Replace + Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Tìm dòng:**

```
| 📱 Huawei HarmonyOS | `wasmtime` JIT (Cranelift) | Không bị W^X như iOS |
```

**Thay bằng:**

```markdown
| 📱 Huawei HarmonyOS | `wasmtime` JIT (Cranelift) — Primary; AOT `.waot` fallback khi JIT unavailable | Distribution: AOT `.waot` bundle bắt buộc cho AppGallery review. Runtime: `WasmRuntime::HarmonyOS { mode: JitWithAotFallback }`. JIT không bị W^X. |
```

**Append footnote cuối bảng:**

```markdown
> **Huawei Dual-Path Note:** AppGallery policy yêu cầu AOT-precompiled `.waot` bundle để pass review.
> Runtime vẫn dùng wasmtime JIT làm primary. Fallback sang AOT chỉ khi JIT detection fails.
> Cross-reference: → Web_Marketplace.md MARKETPLACE-07
```

---

##### EDIT C-02

```yaml
edit_id:       "C-02"
conflict_id:   "RC-03"
target_file:   "Core_Spec.md"
target_section: "§8.2 Memory (bảng RAM Budget có dòng 'NSE Process | ≤24MB')"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Thêm dòng ngay sau row `NSE Micro-Crypto`:**

```markdown
| NSE Micro-NER ONNX | **PROHIBITED** | 📱 iOS | `NsePolicy::ProhibitOnnxLoad` — KHÔNG bao giờ load ONNX trong NSE process. Lý do: NSE Arena 10MB + decrypt 2MB + MLS 2MB = 14MB → không còn margin để load 8MB Micro-NER. Dùng regex-only PII detection trong NSE. Full NER defer sang Main App qua `main_app_decrypt_needed=true`. |
```

**Append warning box sau bảng:**

```markdown
> ⚠️ **NSE RAM Ceiling Additive Rule:**
> NSE Arena (10MB) + MLS Decrypt (~2MB) + system overhead (~2MB) = 14MB baseline.
> Hard margin còn lại: 6MB. ONNX Micro-NER (8MB) vi phạm ceiling → Jetsam kill → notification mất.
> **Invariant:** `NsePolicy::ProhibitOnnxLoad` là non-negotiable. Không exception.
> Cross-reference: → §5.5 NSE RAM Budget Protocol
```

---

##### EDIT C-03

```yaml
edit_id:       "C-03"
conflict_id:   "RC-03"
target_file:   "Core_Spec.md"
target_section: "§9.4 AI Safety — phần mô tả ISDM / Micro-NER / ONNX"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append sau đoạn mô tả Micro-NER:**

```markdown
**NSE Context Restriction:**
- 📱 iOS NSE: `NsePolicy::ProhibitOnnxLoad` — **ONNX model load trong NSE process bị cấm tuyệt đối**.
- NSE chỉ được dùng regex-based PII detection (Aho-Corasick pattern matching, no neural model).
- Full Micro-NER scan (ONNX) chỉ chạy trong Main App context sau khi NSE set `main_app_decrypt_needed=true`.
- Lý do: NSE 20MB hard ceiling bị vi phạm khi ONNX (8MB) + Arena (10MB) + overhead cộng lại.
- Cross-reference: → §8.2 RAM Budget, → §5.5 NSE RAM Budget Protocol
```

---

##### EDIT C-04

```yaml
edit_id:       "C-04"
conflict_id:   "BL-01"
target_file:   "Core_Spec.md"
target_section: "§5.1 HKMS (Dead Man Switch) hoặc §F-04 Key Management System"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append ngay sau đoạn mô tả CallKit exemption:**

```rust
/// Bắt buộc log khi Dead Man Switch bị DEFER do active session.
/// CISO cần entry này để distinguish legitimate deferral vs compromise.
#[derive(Debug, Serialize, Ed25519Signed)]
pub struct DeadManDeferralEntry {
    pub event_type:      AuditEventType,   // = DeadManDeferral
    pub device_id:       DeviceId,
    pub call_id:         Uuid,             // CallKit session ID
    pub reason:          DeferralReason,
    pub device_counter:  u64,              // TPM monotonic counter tại thời điểm defer
    pub server_counter:  u64,              // Server's last known valid counter
    pub deferred_at:     HLC_Timestamp,
    pub expected_resume: Option<HLC_Timestamp>,
    pub ed25519_sig:     Ed25519Signature, // Ký bằng DeviceIdentityKey
}

pub enum DeferralReason {
    ActiveCallKitSession { call_id: Uuid },
    ActiveEmdpSession    { ttl_expires_at: u64 },
    AdminOverride        { admin_device_id: DeviceId },
}
```

```markdown
**Audit Obligation:** Mọi Dead Man Switch deferral event **bắt buộc** tạo `DeadManDeferralEntry`
và append vào Audit Log trước khi deferral có hiệu lực.
Counter delta (`server_counter - device_counter`) phải được log để CISO assess risk.
```

---

##### EDIT C-05

```yaml
edit_id:       "C-05"
conflict_id:   "RC-02"
target_file:   "Core_Spec.md"
target_section: "§5.2 Hardware Root of Trust (hoặc §F-01) — sau iOS Double-Buffer Zeroize Protocol"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append section mới "Android Doze Mitigation":**

```markdown
#### Android Doze Mitigation — StrongBox Wrap-on-Derive Pattern

📱 Android: `mlock()` không khả dụng (StrongBox/TrustZone không expose `mlock` API).
Risk: Doze-triggered process freeze có thể xảy ra mid-`ZeroizeOnDrop`, để key material
trong RAM page chưa được zero-fill.

**Mitigation — Wrap-on-Derive (bắt buộc cho mọi sensitive key trên Android):**
```

```rust
pub fn derive_and_wrap_android(
    input_key_material: &[u8],
    context: &KeyDerivationContext,
) -> Result<WrappedKey, KeyError> {
    // Step 1: Derive key trong local scope
    let plaintext_key = hkdf_sha256(input_key_material, &context.info)?;

    // Step 2: NGAY LẬP TỨC wrap vào StrongBox trước khi bất kỳ await point nào
    // Không có async operation giữa derive và wrap — Doze không thể freeze giữa 2 bước
    let wrapped = android_keystore::wrap(
        &plaintext_key,
        &context.wrapping_key_alias,
        KeyProtection::StrongBox,
    )?;

    // Step 3: ZeroizeOnDrop plaintext ngay sau wrap
    drop(plaintext_key); // ZeroizeOnDrop triggered
    Ok(wrapped)
}
```

```markdown
**Invariant:** Plaintext key window tồn tại < 1ms (derive → wrap → zeroize đồng bộ, không await).
Doze kill chỉ có thể xảy ra trước hoặc sau window này — không thể vào giữa.
```

---

##### EDIT C-06

```yaml
edit_id:       "C-06"
conflict_id:   "NI-02"
target_file:   "Core_Spec.md"
target_section: "§5.4 Hybrid PQ-KEM — sau đoạn 'Survival Mesh Fragmentation'"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append paragraph:**

```markdown
**BLE Channel Disambiguation — ML-KEM Key Exchange:**

> ⚠️ **Quan trọng:** ML-KEM key exchange **KHÔNG** sử dụng BLE Advertising channel (31-byte beacon).

| BLE Channel | MTU | Mục đích trong TeraChat |
|---|---|---|
| **Advertising (ADV_EXT_IND)** | 31 bytes | Peer discovery ONLY — `BLE_Stealth_Beacon` (§6.3) |
| **GATT Connected (ATT MTU negotiated)** | 512 bytes | Data transfer — ML-KEM, CRDT events, key material |

ML-KEM Kyber768 payload (~1.18KB) sử dụng **BLE GATT connected mode** với RaptorQ FEC
fragmentation (RFC 6330) thành các fragments ≤ 400 bytes để đảm bảo reliable delivery
qua GATT ATT MTU 512 bytes.

**Prohibit:** Không bao giờ fragment PQ key material vào ADV_EXT_IND PDU frames.
Beacon frames chỉ carry HMAC commitment để peer discovery — không carry bất kỳ key bytes nào.
Cross-reference: → §6.3 BLE Stealth Beaconing
```

---

##### EDIT C-07

```yaml
edit_id:       "C-07"
conflict_id:   "NI-02"
target_file:   "Core_Spec.md"
target_section: "§6.3 BLE Stealth Beaconing (hoặc §F-12 Mesh) — sau mô tả 31-byte PDU format"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
**Beacon Content Restriction (HARD RULE):**
- ✅ Beacon carries: `HMAC(R, PK_identity)[0:8]` — identity commitment (8 bytes)
- ✅ Beacon carries: `slot_rotation_counter` — replay protection (4 bytes)
- ✅ Beacon carries: `capability_flags` — mesh role indicators (2 bytes)
- ❌ **PROHIBITED:** Key material, PQ keys, MLS epoch data, CRDT payloads trong beacon frame.

Mọi key exchange (ML-KEM, X25519, MLS KeyPackage) đi qua **BLE GATT connected channel**
sau khi peer discovery hoàn tất qua beacon. Beacon là discovery-only.
Cross-reference: → §5.4 Hybrid PQ-KEM, BLE Channel Disambiguation
```

---

##### EDIT C-08

```yaml
edit_id:       "C-08"
conflict_id:   "BL-02"
target_file:   "Core_Spec.md"
target_section: "§6.7 EMDP (hoặc §12 EMDP) — sau constraints 'KHÔNG merge DAG, KHÔNG rotate MLS Epoch'"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append EMDP Shun Exception Protocol:**

```markdown
#### EMDP Shun Exception Protocol

Trong điều kiện bình thường, EMDP prohibit MLS Epoch rotation. Exception bắt buộc
khi Byzantine Shun xảy ra trong all-iOS EMDP mesh:

```

```
EMDP_SHUN_EXCEPTION = {
    trigger:      Shun Record nhận được trong EMDP active state,
    condition_A:  poisoned_node != tactical_relay → Proceed với limited re-key,
    condition_B:  poisoned_node == tactical_relay → Emergency handover IMMEDIATELY
}
```

```markdown
**Case A — Poisoned node là regular member (không phải Tactical Relay):**
1. Loại poisoned node khỏi EMDP text buffer ngay lập tức.
2. Derive temporary group key:
   `TempGroupKey = HKDF(EmdpKeyEscrow.relay_session_key, "shun-rekey" || poisoned_node_id || HLC_now)`.
   - ⚠️ Security note: Nếu poisoned node đã nhận `EmdpKeyEscrow` trước khi bị Shun,
     `TempGroupKey` này bị tainted. Accepted risk: (a) TTL còn tối đa 60 phút,
     (b) EMDP chỉ carry text messages, không carry key material.
     Desktop sẽ re-key hoàn toàn khi reconnect.
3. Subsequent messages encrypt bằng `TempGroupKey`.
4. Log `EmdpShunEvent { poisoned_node_id, hlc, tainted_escrow: bool }` vào local append buffer.

**Case B — Tactical Relay bị Shun:**
1. Terminate EMDP session NGAY LẬP TỨC (không chờ TTL).
2. Trigger new Tactical Relay election từ iOS nodes còn lại.
3. Nếu không đủ nodes (< 2 iOS với battery > 20%): enter `CAUSAL_FREEZE` mode.
4. Emit `CoreSignal::EmdpTerminated { reason: TacticalRelayCompromised }`.

**Invariant — Post-Desktop-Reconnect:**
1. Desktop kiểm tra `tainted_escrow` flag trong EMDP log.
2. Nếu `true`: treat toàn bộ EMDP window messages như potentially compromised.
3. Full MLS Epoch rotation bắt buộc trước khi merge EMDP messages vào main DAG.
```

---

##### EDIT C-09

```yaml
edit_id:       "C-09"
conflict_id:   "NI-03"
target_file:   "Core_Spec.md"
target_section: "§7.1 DAG Storage (hoặc §F-14 CRDT) — đoạn 'VACUUM INTO hot_dag_tmp.db'"
change_type:   "Replace"
sprint:        "Sprint1"
status:        "TODO"
```

**Tìm:** Đoạn pseudocode/comment về `VACUUM INTO hot_dag_tmp.db` + atomic rename.

**Thay bằng:**

```rust
/// SAFE VACUUM pattern cho hot_dag.db — tránh concurrent write race condition.
///
/// Prefer WAL checkpoint thay vì VACUUM cho append-only DB:
/// hot_dag.db không có deleted rows (INV-08: append-only),
/// nên VACUUM chỉ có ích khi WAL file quá lớn.
pub async fn compact_hot_dag(db: &SqlitePool) -> Result<(), StorageError> {
    // Option A (PREFERRED): WAL checkpoint — không cần exclusive lock
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)").await?;

    // Option B: Nếu VACUUM INTO thực sự cần (e.g., fragmentation analysis):
    // BẮT BUỘC acquire exclusive lock trước khi VACUUM
    // db.execute("BEGIN EXCLUSIVE TRANSACTION").await?;
    // db.execute("VACUUM INTO 'hot_dag_tmp.db'").await?;
    // db.execute("COMMIT").await?;
    // tokio::fs::rename("hot_dag_tmp.db", "hot_dag.db").await?;

    Ok(())
}
```

**Append rule:**

```markdown
**VACUUM INTO Locking Rule (bắt buộc):**
Mọi `VACUUM INTO` operation trên `hot_dag.db` phải được bao bọc trong
`BEGIN EXCLUSIVE TRANSACTION ... COMMIT` để prevent concurrent Tokio writer
swap incomplete DB qua atomic `rename()`.

**Ưu tiên:** Dùng `PRAGMA wal_checkpoint(TRUNCATE)` thay VACUUM cho append-only DB.
Không có deleted rows để reclaim → WAL checkpoint hiệu quả hơn và không cần exclusive lock.
```

---

##### EDIT C-10

```yaml
edit_id:       "C-10"
conflict_id:   "NI-01"
target_file:   "Core_Spec.md"
target_section: "§9.2 Micro-Core Relay — ALPN Probe Learning pseudocode"
change_type:   "Replace"
sprint:        "Sprint1"
status:        "TODO"
```

**Tìm:** Logic có pattern `profile.probe_fail_count += 1;` đứng TRƯỚC `tokio::select!`.

**Thay bằng:**

```rust
/// BUGFIX: probe_fail_count phải increment SAU KHI connection race resolve,
/// không phải khi probe bắt đầu.
pub async fn negotiate_alpn_adaptive(
    profile: &mut NetworkProfile,
) -> Result<AlpnResult, NetworkError> {
    // Parallel probe — QUIC và gRPC cùng lúc
    let result = tokio::select! {
        quic_res = probe_quic() => AlpnResult { protocol: Quic, inner: quic_res },
        grpc_res = probe_grpc() => AlpnResult { protocol: GrpcTcp, inner: grpc_res },
    };

    // ✅ CORRECT: Chỉ increment nếu QUIC CONFIRMED failed VÀ không phải winner
    match result.protocol {
        Quic => {
            // QUIC won — reset fail count (successful probe)
            profile.probe_fail_count = 0;
            profile.strict_compliance = false;
        }
        GrpcTcp | Wss => {
            // gRPC/WSS won — QUIC failed, increment counter
            profile.probe_fail_count += 1;
            if profile.probe_fail_count >= 3 {
                profile.strict_compliance = true;
                emit_admin_notification("Auto-switched to TCP-strict on this network.");
            }
        }
    }

    db.save_network_profile(profile).await?;
    Ok(result)
}

// ❌ BUG (pattern cũ — KHÔNG dùng):
// profile.probe_fail_count += 1;  // ← incremented BEFORE race resolves
// let result = tokio::select! { ... };
```

---

##### EDIT C-11

```yaml
edit_id:       "C-11"
conflict_id:   "BL-03"
target_file:   "Core_Spec.md"
target_section: "§9.4 Federation Bridge (hoặc §F-18) — sau section về read-only federation mode"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
**OPA Policy Distribution — Federation Mode Exception:**

> ⚠️ **Rule:** OPA Policy bundle distribution **EXEMPT** khỏi federation schema restrictions.

| Federation State | Data sync | OPA Policy sync |
|---|---|---|
| `SCHEMA_COMPATIBLE` | ✅ Full read/write | ✅ Full |
| `READ_ONLY` (±1 minor delta) | ⛔ Data write blocked | ✅ **Policy write ALLOWED** |
| `SCHEMA_INCOMPATIBLE` (±1 major) | ⛔ All blocked | ✅ **Policy write ALLOWED** |

**Rationale:** Security policy updates (CRL, permission changes, user revocation) phải đến được
Branch cluster bất kể schema version gap. Khóa policy channel khi schema mismatch tạo ra
stale OPA state indefinitely — security risk nghiêm trọng hơn schema incompatibility.

**Implementation:** `federation_policy_sync` channel dùng endpoint riêng biệt, độc lập
với data federation channel. mTLS mutual auth vẫn bắt buộc. OPA bundle signature verify trước apply.
Cross-reference: → §9.4 Federation Bridge, → Web_Marketplace.md §7.2
```

---

##### EDIT C-12

```yaml
edit_id:       "C-12"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§2.1 Shared Core Philosophy — sau đoạn 'Unidirectional State Sync'"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
#### Formal IPC Memory Ownership Contract (Token Protocol)

Rust Core xuất 2 FFI primitive thay vì raw pointer:

1. `tera_buf_acquire(id)` → trả handle opaque (`u64` token), không phải raw pointer.
2. `tera_buf_release(token)` → Rust mới được phép zeroize.

iOS JSI và Android Dart FFI đều gọi `tera_buf_release()` trong destructor/finalizer.
Rust Core có reference counter per-token: `ZeroizeOnDrop` chỉ thực thi khi `ref_count == 0`.

**CI lint rule:** Cấm FFI endpoint trả `Vec<u8>/ptr` trực tiếp không qua Token Protocol.
Cross-reference: → TERA-FEAT §1 IPC Signal/Command Contract
```

---

##### EDIT C-13

```yaml
edit_id:       "C-13"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§5.2 Hardware Root of Trust (hoặc §F-01) — sau mô tả Biometric-Bound Cryptographic Handshake"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
#### iOS Key Protection — Double-Buffer Zeroize Protocol

📱 **Double-Buffer:** Phân bổ key vào 2 page liền kề `MAP_ANONYMOUS|MAP_PRIVATE`.
Ngay sau decrypt xong: ghi đè `0x00` vào page 1 TRƯỚC KHI dùng key. Dùng key từ page 2.
Sau `ZeroizeOnDrop`: ghi đè cả 2 page.
Nếu Jetsam kill trước Drop: page 1 đã clean, page 2 còn key nhưng là 1 page đơn lẻ
khó exploit hơn so với madvise đơn lẻ.
```

---

##### EDIT C-14

```yaml
edit_id:       "C-14"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§5.9 (sau đoạn Gossip Broadcast + iBeacon) hoặc §12 EMDP — nếu chưa có EMDP section"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
note:          "C-08 đã add EMDP Shun Exception. C-14 add EMDP State Machine nếu chưa có §12."
```

**Append nếu §12 EMDP chưa tồn tại:**

```markdown
### §12 Emergency Mobile Dictator Protocol (EMDP)

> **Bài toán:** Khi tất cả peer là iOS Leaf Node (không có Desktop/Android Super Node),
> BLAKE3 Hash Election không tìm được Dictator → Causal Freeze → không gửi được tin nhắn SOS.

**EMDP State Machine:**

| Trạng thái | Điều kiện | Hành vi |
|---|---|---|
| `Normal` | Có Desktop hoặc Android Super Node | BLAKE3 Hash Election bình thường |
| `EmergencyMobileOnly` | Toàn bộ peer là iOS Leaf Node | Bầu iOS có battery cao nhất làm Tactical Relay |
| `SoloAppendOnly` | Chỉ 1 thiết bị | Append-Only, không cần election |

**Tactical Relay ≠ Super Node:** Chỉ `Append-Only CRDT` đơn giản, store-and-forward text.
KHÔNG merge DAG, KHÔNG rotate MLS Epoch. Auto-expire sau 60 phút.
```

```rust
pub enum DictatorElectionMode { Normal, EmergencyMobileOnly, SoloAppendOnly }
// Selection: battery_score (battery_pct * 100) + ble_rssi_score (rssi + 100)
// TacticalRelayMode::TextOnlyForward, ttl_minutes: 60
```

**EMDP Key Escrow Handshake:**

```rust
pub struct EmdpKeyEscrow {
    relay_session_key: AesKey256,
    emdp_start_epoch:  u64,
    emdp_expires_at:   u64, // now() + 3600
}
// Desktop xuất EMDP Escrow Key trước khi offline/handover:
// 1. Sinh EmdpKeyEscrow
// 2. ECIES encrypt với iOS device pubkey
// 3. Gửi qua BLE Control Plane
// Khi Desktop reconnect:
// → nhận lại escrow từ iOS → decrypt relay messages → merge vào DAG với đúng epoch context
// → Không có orphan messages.
```

---

##### EDIT C-15

```yaml
edit_id:       "C-15"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§5.11 (sau đoạn WebRTC TURN) hoặc §F-06 Voice/Video"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
#### iOS WebRTC TURN — CallKit Integration

📱 **Vấn đề:** iOS cho app Background tối đa 30s network. TURN failover 3s + SRTP renegotiate
có thể vượt window.
📱 **Giải pháp:** Sử dụng CallKit — iOS treat TeraChat calls như native calls, không bị background kill.
```

```swift
class TeraCallKitProvider: NSObject, CXProviderDelegate {
    // CXProvider giữ audio session active dù app background
    // TURN failover xảy ra trong CallKit context → không bị suspend
    // Dual TURN preconnect: khi call active và app sắp vào Background,
    // Rust proactively connect tới TURN server dự phòng.
}
```

```markdown
#### iOS AWDL Monitor — Hotspot/CarPlay Conflict

📱 **Vấn đề:** iOS tự tắt AWDL khi bật Personal Hotspot hoặc CarPlay
→ voice call drop không giải thích.
```

```swift
class AWDLMonitor {
    // NWPathMonitor detect AWDL interface + bridge (hotspot/CarPlay)
    // Callback → Rust Core downgrade Tier 2 → Tier 3 (BLE only)
    // Emit UIEvent::TierChanged với message giải thích
    // Queue voice packets TTL 30s chờ AWDL phục hồi
}
```

---

##### EDIT C-16

```yaml
edit_id:       "C-16"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§5.19 (hoặc §F-14 CRDT) — thay đoạn 'Shadow DAG bị loại bỏ hoàn toàn'"
change_type:   "Replace"
sprint:        "Sprint1"
status:        "TODO"
```

**Tìm:** `"Giao thức Shadow DAG bị loại bỏ hoàn toàn khỏi bộ định tuyến P2P Mesh"`

**Thay bằng:**

```markdown
**Tiered Conflict Resolution Protocol:**

| Tier | Môi trường | Cơ chế | Cam kết |
|---|---|---|---|
| 1 | Online | Shadow DAG đầy đủ | User thấy conflict, chọn merge |
| 2 | Mesh P2P | Lightweight Conflict Marker | Desktop Super Node mediator |
| 3 | Solo offline | Optimistic Append | WARNING "Bản này có thể bị ghi đè" |

**Ràng buộc cứng:** Không bao giờ silent LWW trên document có `content_type = CONTRACT | POLICY | APPROVAL`.
Bắt buộc hiển thị Conflict Resolution UI trước khi ghi khi reconnect phát hiện conflict.
```

---

##### EDIT C-17

```yaml
edit_id:       "C-17"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§3.4.2 (sau 'SQLite WAL Autocheckpoint') hoặc §F-07 Infrastructure"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
#### XPC Transaction Journal Protocol (macOS)
```

```rust
// hot_dag.db journal trước khi dispatch sang XPC Worker
// States: PENDING → VERIFIED → COMMITTED
// Crash in PENDING  → abort + notify user "Phiên ký bị gián đoạn. Vui lòng ký lại."
// Crash in VERIFIED → commit from journal (idempotent)
pub struct XpcTransactionJournal { /* tx_id, status, payload_hash */ }
```

---

##### EDIT C-18

```yaml
edit_id:       "C-18"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§11 Huawei HarmonyOS Stack — sau §11.5 hoặc thêm mục §11.6"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
#### §11.6 Huawei CRL Polling Fallback

📱 **Vấn đề:** HMS không có equivalent APNs `content-available` background push cho CRL updates.
📱 **Giải pháp:** CRL refresh 4h polling khi Foreground + HMS Data Message khi Background.
**Acknowledged limitation:** Huawei CRL update có thể delay tối đa 4h so với iOS/Android 30 phút.
Phải được disclosed trong Enterprise SLA documentation.
```

---

##### EDIT C-19

```yaml
edit_id:       "C-19"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§13 License Architecture — thêm §13.6"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
### §13.6 Offline TTL Profile (Dynamic — không hardcode 24h)
```

```rust
pub enum OfflineTTLProfile {
    Consumer    { ttl_hours: 24 },
    Enterprise  { ttl_hours: u32 },    // configurable bởi Admin, default 168 (7 ngày)
    GovMilitary { ttl_hours: 720 },    // 30 ngày
    AirGapped   { revocation_only: bool },
}
```

```markdown
TTL được cấu hình bởi Admin trong Admin Console và baked vào License JWT field `offline_ttl_hours`.
**Lý do:** Hardcode 24h mâu thuẫn với Survival Mesh promise cho Gov/Military deployment kéo dài nhiều ngày.
```

---

##### EDIT C-20

```yaml
edit_id:       "C-20"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§14 Network Layer — thêm §14.8"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
### §14.8 AES-NI / ARM NEON — Software Fallback
```

```rust
pub fn init_crypto_backend() -> CryptoBackend {
    if is_cpu_feature_detected!("aes") && is_cpu_feature_detected!("sse2") {
        CryptoBackend::HardwareAccelerated
    } else {
        tracing::warn!("AES-NI not available, using software backend. Expect ~3x slower.");
        CryptoBackend::Software
    }
}
```

```markdown
Admin Console hiển thị warning khi thiết bị dùng software backend:
*"Thiết bị này không có hardware crypto. Mã hóa chậm hơn 3x bình thường."*
```

---

##### EDIT C-21

```yaml
edit_id:       "C-21"
conflict_id:   null
target_file:   "Core_Spec.md"
target_section: "§14 Network Layer — thêm §14.9"
change_type:   "Append"
sprint:        "Sprint1"
status:        "TODO"
```

**Append:**

```markdown
### §14.9 Shadow DB Write Lock Protocol
```

```rust
pub struct ShadowMigrationLock { migration_in_progress: AtomicBool }
// NSURLSession completion check lock → queue to hot_dag.db nếu migration đang chạy
// Đảm bảo không race giữa shadow rename và NSURLSession background write
impl ShadowMigrationLock {
    pub fn is_migration_in_progress(&self) -> bool { self.migration_in_progress.load(Ordering::SeqCst) }
}
```

---

#### FILE 2: `Feature_Spec.md` — TẠO MỚI HOÀN TOÀN

```yaml
conflict_id:  "PB-01"
target_file:  "Feature_Spec.md"
change_type:  "CreateNew"
sprint:       "Sprint1"
status:       "TODO"
reason:       "34+ references trong Core_Spec.md trỏ đến TERA-FEAT — file rỗng là critical gap"
```

**Tạo file mới với header:**

```yaml
# Feature_Spec.md — TeraChat TERA-FEAT v0.1.0-mvp
id:       "TERA-FEAT"
version:  "0.1.0-mvp"
status:   "IN PROGRESS — Sprint 1 Priority"
depends:  "TERA-CORE (Core_Spec.md)"
```

##### EDIT F-01 — §1 IPC Signal/Command Contract

```yaml
edit_id:       "F-01"
conflict_id:   null
target_file:   "Feature_Spec.md"
target_section: "§1 — Tạo mới"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §1:**

```markdown
## §1 IPC Signal/Command Contract

> Cross-reference: → Core_Spec.md §4.2 (CoreSignals và UICommands catalog)

### §1.1 Token Protocol

Rust Core xuất 2 FFI primitive thay vì raw pointer (→ Core_Spec.md §2.1):
```

```dart
class TeraSecureBuffer {
  final TeraBufferToken _token;
  final Finalizer<TeraBufferToken> _finalizer;
  bool _released = false;

  // Mọi TeraSecureBuffer PHẢI được wrap bởi useInTransaction hoặc explicit releaseNow()
  void releaseNow() {
    if (!_released) {
      _released = true;
      _finalizer.detach(this);
      tera_buf_release(_token);
    }
  }

  T useInTransaction<T>(T Function(Pointer<Uint8> ptr) action) {
    try { return action(_token.toPointer()); }
    finally { releaseNow(); } // Always release kể cả exception
  }
}
```

```markdown
**CI lint rule:** `tera_buf_acquire` phải có matching `releaseNow()` trong cùng scope
hoặc `useInTransaction` wrapper. Violation → CI block.

### §1.2 Data Plane Transport Per-Platform

| Platform | Mechanism | Throughput |
|---|---|---|
| 📱 iOS | JSI C++ `std::unique_ptr` + Custom Deleter | ~400MB/s |
| 📱 Android / Huawei | Dart FFI TypedData (C ABI static buffer) | ~400MB/s |
| 💻🖥️ Desktop | `SharedArrayBuffer` (mmap physical) | ~500MB/s |
| All | Protobuf over Control Plane (<50 bytes) | N/A |
```

---

##### EDIT F-02 — §2 OS Hook Matrix Per-Platform

```yaml
edit_id:       "F-02"
conflict_id:   null
target_file:   "Feature_Spec.md"
target_section: "§2 — Tạo mới"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §2:**

```markdown
## §2 OS Hook Matrix Per-Platform

### §2.1 iOS OS Hooks

| Hook | API | Mục đích |
|---|---|---|
| Push (NSE) | `UNNotificationServiceExtension` | E2EE decrypt push trước khi display |
| Voice call | `CXProvider` (CallKit) | Giữ network active khi background |
| AWDL monitor | `NWPathMonitor` | Detect Hotspot/CarPlay conflict |
| Background task | `BGProcessingTask` | VACUUM + CRDT compaction khi sạc |
| Memory pressure | `UIApplication.didReceiveMemoryWarning` | ZeroizeOnDrop vector caches |

### §2.2 Android OS Hooks

| Hook | API | Mục đích |
|---|---|---|
| Push | `FirebaseMessagingService` | E2EE decrypt FCM Data Message |
| Battery bucket | `CompanionDeviceManager` | Bypass Doze throttle (→ C-03) |
| Memory | `onTrimMemory(TRIM_MEMORY_RUNNING_CRITICAL)` | ZeroizeOnDrop + flush WAL |
| Background upload | `WorkManager` | Chunked file upload khi offline |

**Android 14+ FCM Throttle:**
```kotlin
<uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
// Request REQUEST_COMPANION_RUN_IN_BACKGROUND via CompanionDeviceManager
```

### §2.3 Huawei HarmonyOS OS Hooks

| Hook | API | Mục đích |
|---|---|---|
| Push | HMS Push Kit Data Message | Background wakeup (delay ≤ 4h — xem C-18) |
| Biometric | HMS Biometric API | Key signing gate |
| BLE | HarmonyOS BLE API | Mesh discovery |

### §2.4 macOS OS Hooks

| Hook | API | Mục đích |
|---|---|---|
| Background daemon | `launchd` LaunchAgent `terachat-daemon` | Push decrypt + notifications |
| WASM worker | XPC Service `terachat-wasm-worker` | JIT-isolated sandbox (allow-jit) |
| Entitlements | Main: NO `allow-jit`; Worker: `allow-jit=true` | W^X compliance |

**macOS Process Layout:**

```
TeraChat.app/
├── Contents/MacOS/
│   ├── terachat              ← Main process, NO allow-jit
│   └── terachat-wasm-worker  ← XPC child, allow-jit only
```

### §2.5 Windows OS Hooks

| Hook | API | Mục đích |
|---|---|---|
| Background service | Windows Service API | `terachat-daemon` |
| Notifications | WNS (Windows Notification Service) | OS native notifications |
| Crypto | CNG + TPM 2.0 NCrypt | Key storage |

### §2.6 Linux OS Hooks

**Linux Multi-Init Daemon Support:**

```bash
# Install script detect: systemd / openrc / runit / s6 / launchd
if systemctl --version &>/dev/null 2>&1; then
    systemctl enable --now terachat-daemon.service
elif command -v rc-service &>/dev/null; then
    rc-update add terachat-daemon default
elif command -v runit &>/dev/null; then
    ln -sf /etc/sv/terachat-daemon /var/service/
else
    install -m644 terachat-daemon.desktop ~/.config/autostart/
fi
# terachat-daemon viết PID file → bất kỳ init nào có thể monitor
```

**Wayland Clipboard Backend Detection:**

```rust
let clipboard_backend = if std::env::var("WAYLAND_DISPLAY").is_ok() {
    ClipboardBackend::WlClipboard  // wl-clipboard — Wayland native
} else {
    ClipboardBackend::Xclip        // xclip/xsel — X11
};
```

```

---

##### EDIT F-03 — §3 Storage & Hydration Lifecycle

```yaml
edit_id:       "F-03"
conflict_id:   null
target_file:   "Feature_Spec.md"
target_section: "§3 — Tạo mới"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §3:**

```markdown
## §3 Storage & Hydration Lifecycle

Cross-reference: → Core_Spec.md §7.1 (hot_dag.db), §5.1 (cold_state.db + Hydration_Checkpoint)

### §3.1 hot_dag.db WAL Compaction

Dùng WAL checkpoint thay VACUUM (INV-08: append-only, không có deleted rows → C-09):
```rust
db.execute("PRAGMA wal_checkpoint(TRUNCATE)").await?;
```

### §3.2 cold_state.db Shadow Paging

1. Download snapshot → `cold_state_shadow.db`
2. Verify `SHA-256(content) == cas_uuid`
3. Atomic rename: `cold_state_shadow.db → cold_state.db`
4. `ShadowMigrationLock` prevent race với NSURLSession background write (→ C-21)

### §3.3 Schema Migration Runbook

```rust
const CURRENT_HOT_DAG_SCHEMA_VERSION: u32 = 1;
// 1. db.backup(DatabaseName::Main, &backup_path)?
// 2. BEGIN EXCLUSIVE TRANSACTION
// 3. migration.up(db)?
// 4. PRAGMA user_version = target_version
// 5. COMMIT
// Safety net: cold_state.db có thể rebuild từ hot_dag.db bất kỳ lúc nào
```

```

---

##### EDIT F-04 — §4 WASM Runtime Behavior Per-Platform

```yaml
edit_id:       "F-04"
conflict_id:   "RC-01"
target_file:   "Feature_Spec.md"
target_section: "§4 — Tạo mới"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §4:**

```markdown
## §4 WASM Runtime Behavior Per-Platform

| Platform | Runtime | Mode | Notes |
|---|---|---|---|
| 📱 iOS | `wasm3` pure interpreter | Interpreter only | W^X compliant. +15-20ms latency/call. AOT `.dylib` trong XPC Worker (macOS only). |
| 📱 Android | `wasmtime` JIT | Cranelift backend | CFI enforcement, sandbox |
| 📱 Huawei | `wasmtime` JIT + AOT fallback | `JitWithAotFallback` | AOT `.waot` bundle bắt buộc cho AppGallery review (→ C-01) |
| 💻 macOS | `wasmtime` JIT trong XPC Worker | Child process isolated | Main App: NO `allow-jit`. XPC Worker: `allow-jit=true`. |
| 💻🖥️ Win/Linux | `wasmtime` JIT | Cranelift backend | Maximum throughput |

Switch condition: `#[cfg(target_os = "ios")]` tại compile-time.

### §4.1 WasmParity CI Gate (→ §5)

Cross-reference bắt buộc: → §5 WasmParity CI Gate Specification
```

---

##### EDIT F-05 — §5 WasmParity CI Gate Specification

```yaml
edit_id:       "F-05"
conflict_id:   "PB-01"
target_file:   "Feature_Spec.md"
target_section: "§5 — Tạo mới (Referenced Core_Spec §11.4 as Blocker, Not implemented)"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §5:**

```markdown
## §5 WasmParity CI Gate Specification

**Status:** Referenced by Core_Spec §11.4 as "Blocker, Not implemented" → Sprint 1 priority.

### §5.1 Input

Identical test vectors chạy trên cả 2 runtimes:
- `wasm3` (iOS — reference runtime): output semantic là ground truth
- `wasmtime` (Desktop — optimized runtime): phải match wasm3 output

### §5.2 Acceptance Criteria

| Criterion | Threshold | Fail action |
|---|---|---|
| Output semantic identity | 100% identical | Block merge |
| Latency delta | ≤ 20ms | Block merge |
| Memory delta | ≤ 5MB | Block merge |

### §5.3 CI Command

```bash
cargo test --test wasm_parity -- --timeout 60
```

Failure → block merge + notify Marketplace team.

### §5.4 Runtime Parity Rule

| Runtime | Platform | Role |
|---|---|---|
| `wasm3` (interpreter) | iOS (W^X mandatory) | **Reference runtime** — output semantic là ground truth |
| `wasmtime` JIT | Android, Desktop, Huawei | **Optimized runtime** — phải match wasm3 output |

```

---

##### EDIT F-06 — §6 Protected Clipboard Bridge

```yaml
edit_id:       "F-06"
conflict_id:   null
target_file:   "Feature_Spec.md"
target_section: "§6 — Tạo mới"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §6:**

```markdown
## §6 Protected Clipboard Bridge

| Platform | Backend | Mechanism |
|---|---|---|
| 📱 iOS | `UIPasteboard` | Auto-clear sau 60s |
| 📱 Android | `ClipboardManager` + `FLAG_SECURE` | Kernel Compositor blocks screenshot |
| 📱 Huawei | HarmonyOS PasteBoard | Equivalent Android FLAG_SECURE |
| 💻 macOS | `NSPasteboard` | Hook via Rust |
| 💻🖥️ Windows | Win32 `SetClipboardData` | Rust hook |
| 🖥️ Linux Wayland | `wl-clipboard` (`wl-copy`/`wl-paste`) | Runtime detect WAYLAND_DISPLAY |
| 🖥️ Linux X11 | `xclip` / `xsel` | Fallback khi WAYLAND_DISPLAY absent |

**Detection (Linux):** → Core_Spec.md §2.1 (EDIT C-12) hoặc code snippet tại C-22 (Feature_Spec §2.6).
```

---

##### EDIT F-07 — §7 AI Worker Process Isolation

```yaml
edit_id:       "F-07"
conflict_id:   "RC-03"
target_file:   "Feature_Spec.md"
target_section: "§7 — Tạo mới"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §7:**

```markdown
## §7 AI Worker Process Isolation

`terachat-ai-worker` chạy như **separate OS process** — không share RAM với Rust Core.
`catch_unwind` boundary tại mọi AI worker entry point.

### §7.1 Memory Ceilings

| Context | Ceiling | Enforcement |
|---|---|---|
| Desktop ONNX worker | 150MB | OOM-kill worker process, không crash Core |
| Mobile ONNX pipeline | 8MB heap | Custom allocator returns `AllocError` on overflow |
| NSE process (iOS) | **ONNX PROHIBITED** | `NsePolicy::ProhibitOnnxLoad` — KHÔNG bao giờ load ONNX |

**NSE Restriction:** → Core_Spec.md C-02, C-03. NSE chỉ dùng regex-only PII detection.
Full Micro-NER defer sang Main App qua `main_app_decrypt_needed=true`.

### §7.2 Whisper AI Memory Budget Protocol

```rust
pub enum WhisperModelTier {
    Tiny,     // 39MB, WER ~25% tiếng Việt
    Base,     // 74MB, WER ~15% tiếng Việt
    Disabled, // fallback text-only BLE
}

pub fn select_whisper_tier(available_ram_mb: u32, battery_pct: u8) -> WhisperModelTier {
    if battery_pct < 20     { return WhisperModelTier::Disabled; }
    if available_ram_mb > 200 { return WhisperModelTier::Base;  }
    if available_ram_mb > 100 { return WhisperModelTier::Tiny;  }
    WhisperModelTier::Disabled
}
// Khi Disabled: UI hiển thị "Thiết bị đang tiết kiệm RAM — Voice tạm chuyển sang text."
```

**Constraint:** Whisper chỉ load khi `available_ram > 100MB` && `battery > 20%`.

```

---

##### EDIT F-08 — §8 Build Target Matrix + §16 AppArmor/SELinux Postinstall

```yaml
edit_id:       "F-08"
conflict_id:   "PB-02"
target_file:   "Feature_Spec.md"
target_section: "§8 + §16 — Tạo mới (§16 referenced Core_Spec §11.4 as High, Not implemented)"
change_type:   "CreateNew"
sprint:        "Sprint1"
```

**Nội dung §8:**

```markdown
## §8 Build Target Matrix

```

x86_64-apple-darwin        → macOS Intel
aarch64-apple-darwin       → macOS Apple Silicon
x86_64-pc-windows-msvc     → Windows x64
aarch64-pc-windows-msvc    → Windows ARM64 (MỚI — Surface Pro X, Copilot+ PCs)
x86_64-unknown-linux-gnu   → Linux x64 (.deb/.rpm/AppImage)
aarch64-unknown-linux-gnu  → Linux ARM64 (server deployment)
aarch64-apple-ios          → iOS
aarch64-linux-android      → Android + Huawei HarmonyOS (OHOS SDK)

```

**Windows ARM64 note:** Cần test SAB behavior trên ARM64 WebView2 riêng trước release (→ TD-03).

**Linux Packaging Strategy:**

| Format | memfd_create | seccomp-bpf | Gov Enterprise |
|---|---|---|---|
| **Signed .deb/.rpm** | ✅ | ✅ | ✅ GPG signed |
| **AppImage (fallback)** | ✅ | ✅ | ⚠️ Cosign |
| ~~Flatpak~~ | ❌ blocked by bubblewrap | ❌ conflict | ❌ không dùng |
```

**Nội dung §16:**

```markdown
## §16 AppArmor / SELinux Postinstall Script

**Status:** Referenced by Core_Spec §11.4 as "High, Not implemented" → Sprint 1 priority.
Without this script: startup crash trên `memfd_create` và `ipc_lock` denial trên enforcing systems.

### §16.1 Detection Logic

```bash
#!/bin/bash
if command -v apparmor_parser &>/dev/null; then
    apparmor_parser -r -W /etc/apparmor.d/usr.bin.terachat
    apparmor_parser -r -W /etc/apparmor.d/terachat-daemon
elif command -v semodule &>/dev/null; then
    semodule -i /usr/share/terachat/terachat.pp
fi
# Verify: terachat --check-permissions (built-in self-test)
```

### §16.2 AppArmor Profile (Ubuntu 20.04+)

Profile phải allow: `memfd_create`, `ipc_lock`, restrict `ptrace`.

### §16.3 SELinux Policy Module (RHEL 8+)

`.pp` module compiled từ `.te` + `.fc` files: `semodule -i terachat.pp`.

### §16.4 Self-test

`terachat --check-permissions` exit code 0 = OK, exit code 1 = MAC profile missing.

```

---

---

### SPRINT 2 — HIGH PRIORITY

---

#### FILE 3: `Design.md`

---

##### EDIT D-01
```yaml
edit_id:       "D-01"
conflict_id:   "BL-01, BL-02"
target_file:   "Design.md"
target_section: "§17 IPC Signal Mapping (hoặc DESIGN-GPU-02)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append rows vào bảng IPC Signal → UI Response:**

```markdown
| `dead_man_deferral` | `DeadManDeferralEntry` logged; subtle amber badge ở status bar "⚠ Bảo mật tạm hoãn" (không interrupt call). Sau call kết thúc: modal "Phiên bảo mật đã được khôi phục." | 📱 iOS |
| `emdp_shun_exception_a` | Toast ngắn "Thiết bị [name] đã bị loại khỏi nhóm tạm thời." Mesh UI hiển thị node màu đỏ nhạt trong topology view. | 📱 iOS Mesh |
| `emdp_shun_exception_b` | Modal cảnh báo: "Relay tạm thời đã bị xâm phạm. Đang chọn relay mới..." + spinner. Nếu không có relay mới: "Mesh tạm dừng — vui lòng chờ thiết bị khác vào phạm vi." | 📱 iOS Mesh |
```

---

##### EDIT D-02

```yaml
edit_id:       "D-02"
conflict_id:   null
target_file:   "Design.md"
target_section: "§DESIGN-GPU-01 (đã có) — cuối section"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**Bổ sung §DESIGN-GPU-01 — GPU Capability Signal:**

Rust Core emit `GpuCapability { has_backdrop_filter: bool, compositing_tier: u8 }` qua IPC lúc init.
UI chọn Glass variant tương ứng:
- `compositing_tier = 2` → Tier A: Full Glass `backdrop-filter: blur(16-24px)`
- `compositing_tier = 1` → Tier B: Frosted Lite `blur(8px)`
- `compositing_tier = 0` → Tier C: Flat Solid `rgba(255,255,255,0.75)`

Flat variant (Tier C) phải được Designer approve spec riêng — đảm bảo brand identity TeraChat nhận diện được.
```

---

##### EDIT D-03

```yaml
edit_id:       "D-03"
conflict_id:   null
target_file:   "Design.md"
target_section: "§DESIGN-GPU-03 (đã có) — mở rộng XPC Recovery UI"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**Mở rộng §DESIGN-GPU-03 — XPC Worker Crash Recovery:**

Khi XPC Worker crash giữa Smart Approval → Modal:
- Title: "Phiên ký bị gián đoạn"
- Body: "Vui lòng ký lại."
- Primary: [Ký lại] | Secondary: [Bỏ qua]
- Glass Modal border-color: `var(--color-warning)` (Amber)
```

---

##### EDIT D-04

```yaml
edit_id:       "D-04"
conflict_id:   null
target_file:   "Design.md"
target_section: "Thêm §DESIGN-CONFLICT-01 (mới)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
### §DESIGN-CONFLICT-01: Conflict Resolution UI States

| Tier | UI Element | Visual |
|---|---|---|
| Online Conflict | Modal 2 cột | Glass card, "Phiên bản của [Bạn]" vs "Phiên bản của [Đồng nghiệp]" |
| Mesh Conflict Marker | Badge trên document | ⚠️ amber badge, tooltip "Mâu thuẫn phát hiện" |
| CONTRACT/POLICY/APPROVAL | Block interaction | Hazard stripe overlay + "Cần giải quyết xung đột trước khi tiếp tục" |

**Hard rule:** Không bao giờ render merged result trực tiếp lên `content_type = CONTRACT | POLICY | APPROVAL`
mà không có user confirmation.
```

---

##### EDIT D-05

```yaml
edit_id:       "D-05"
conflict_id:   null
target_file:   "Design.md"
target_section: "Thêm §DESIGN-AWDL-01 (mới)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
### §DESIGN-AWDL-01: AWDL/Hotspot Conflict Banner

| Trạng thái | Banner | Duration |
|---|---|---|
| Hotspot detected → AWDL off | Amber bar: "📡 Hotspot đang bật — Mesh chuyển BLE. Voice tạm không khả dụng." | Persistent |
| CarPlay connected → AWDL off | Amber bar: "🚗 CarPlay đang kết nối — Mesh BLE only." | Persistent |
| Voice dropped (30s timeout) | Red toast: "Cuộc gọi bị ngắt do mất kết nối Mesh" | 5s auto-dismiss |
| AWDL restored | Green toast: "Mesh khôi phục — Voice sẵn sàng" | 3s |
```

---

##### EDIT D-06

```yaml
edit_id:       "D-06"
conflict_id:   null
target_file:   "Design.md"
target_section: "Thêm §38 Swarm Workspace & Causal Decision Timeline (mới)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
### §38 Swarm Workspace & Causal Decision Timeline

#### §38.1 Agent Member Indicators

| Trạng thái Agent | Badge trong Member List | Tooltip |
|---|---|---|
| Online & Active | 🤖 Xanh neon | "Agent [tên] — đang xử lý" |
| Idle | 🤖 Xám | "Agent [tên] — chờ task" |
| Burner (TTL active) | ⏳ Cam countdown | "Ephemeral Agent — tự hủy sau Xm" |
| Pending Remove | 🔴 Nhấp nháy | "Agent đang bị remove khỏi Group" |

#### §38.2 Causal Decision Timeline View

```

[User] ──────────────────── [Timeline] ──────────────────────▶ t
         │                               │
         @AgentOrchestrator              ▼
                         ┌───────────────────────────────────┐
                         │ 🤖 [PROPOSE] Trích xuất dữ liệu  │ ← xanh
                         │    agent: fin-analyst | 14:23:01  │
                         └───────────────────────────────────┘
                                         ▼
                         ┌───────────────────────────────────┐
                         │ ⚠️ [AWAIT APPROVAL] Chi tiêu>$50K│ ← amber pulse
                         │ [Phê duyệt ▶] [Từ chối ✕]        │
                         └───────────────────────────────────┘
                                         ▼ (sau Biometric)
                         ┌───────────────────────────────────┐
                         │ ✅ [APPROVED] Nguyễn V. A | FaceID│ ← xanh lá
                         │    14:23:45 · Ed25519 ✓           │
                         └───────────────────────────────────┘
                                         ▼
                         ┌───────────────────────────────────┐
                         │ 🔷 [EXECUTED] Transfer $52,400    │ ← tím
                         │    BLAKE3: a3f9... · Audit #2847  │
                         └───────────────────────────────────┘

```

- Glass Card mỗi node: `border-radius: 8px`, `backdrop-filter: blur(12px)`.
- `AWAIT_APPROVAL` node: Amber Pulse animation (→ §26 pattern) + countdown timer.
- Tap vào bất kỳ node → Expand xem full payload hash, parent DAG links, platform indicator.
```

---

##### EDIT D-07

```yaml
edit_id:       "D-07"
conflict_id:   null
target_file:   "Design.md"
target_section: "Thêm §39 Burner Agent Termination Ceremony (mới)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
### §39 Burner Agent Termination Ceremony

Khi Burner Agent tự hủy:

1. **Agent card** chạy Shatter Effect (→ §DESIGN-WASM-01 Kill-Switch animation)
   với màu nền `rgba(239, 68, 68, 0.15)` thay vì Blood-Red
   (Burner là intended termination, không phải security incident).
2. Sau 400ms: card replace bằng **Termination Proof Badge**:
   `🔐 Tác tử đã tự hủy · Xem bằng chứng`
3. Tap vào Badge → Modal: `BurnerTerminationProof` — task_id, timestamp, BLAKE3 hash,
   hai chữ ký CA với QR code để verify độc lập.
4. Badge tồn tại trong conversation history vĩnh viễn (append-only) — không thể xóa.
```

---

#### FILE 4: `Web_Marketplace.md`

---

##### EDIT M-01

```yaml
edit_id:       "M-01"
conflict_id:   "RC-01"
target_file:   "Web_Marketplace.md"
target_section: "MARKETPLACE-07 — sau Huawei AOT requirement policy statement"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**Runtime Clarification:** `.waot` AOT bundle là yêu cầu của AppGallery review process —
không có nghĩa là runtime phải chạy thuần AOT. Sau khi app được install, runtime sử dụng
`WasmRuntime::HarmonyOS { mode: JitWithAotFallback }`:
1. Primary: wasmtime JIT (performance)
2. Fallback: AOT compiled bytecode (nếu JIT detection fails)

Cross-reference: → Core_Spec.md §3.1 EDIT C-01
```

---

##### EDIT M-02

```yaml
edit_id:       "M-02"
conflict_id:   "BL-03"
target_file:   "Web_Marketplace.md"
target_section: "§7.2 — sau OPA bundle version monotonic counter"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**Federation Mode Exception:** OPA Policy distribution không bị block bởi federation
schema read-only mode. Policy channel hoạt động độc lập với data sync channel.
Cross-reference: → Core_Spec.md §9.4 EDIT C-11
```

---

##### EDIT M-03

```yaml
edit_id:       "M-03"
conflict_id:   null
target_file:   "Web_Marketplace.md"
target_section: "§MARKETPLACE-05 — mở rộng Publisher Migration Guide"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**SLA cam kết:**
- TeraChat Foundation support **2 major ABI versions đồng thời**
- Deprecation window: **12 tháng** từ ngày announce
- Breaking changes chỉ trong major version — minor version là additive only

**Rejection vs Warning:**
- `host_api_version` ngoài `[min, max]` range → **Reject** (hard fail, block load)
- `host_api_version` trong deprecated range → **Warning badge** ⚠️ trong Marketplace
- `host_api_version` EOL → **Block load** + alert Admin Console
```

---

##### EDIT M-04

```yaml
edit_id:       "M-04"
conflict_id:   null
target_file:   "Web_Marketplace.md"
target_section: "§5 W^X Sandboxing — sau 'iOS AOT W^X Compliance'"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**WASM Runtime Behavioral Parity Rule:**

| Runtime | Platform | Khi nào dùng |
|---|---|---|
| `wasm3` (interpreter) | iOS (W^X mandatory) | **Reference runtime** — output semantic là ground truth |
| `wasmtime` JIT | Android, Desktop, Huawei | **Optimized runtime** — phải match wasm3 output |

**WasmParity CI Gate:** Mọi `.tapp` submit Marketplace phải pass test vector giống nhau trên cả 2 runtime.
Fail → block merge. Latency delta ≤ 20ms chấp nhận được, nhưng **output semantic phải identical**.
Cross-reference: → Feature_Spec.md §5 WasmParity CI Gate
```

---

##### EDIT M-05

```yaml
edit_id:       "M-05"
conflict_id:   null
target_file:   "Web_Marketplace.md"
target_section: "Thêm §MARKETPLACE-10 Tapp-Agent Developer SDK (mới)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
### §MARKETPLACE-10: Tapp-Agent Developer SDK & ClawHub Discovery Registry

**Agent Manifest Contract v2:**
```json
{
  "tapp_id": "fin-analyst-agent-v1",
  "tapp_type": "heavyweight",
  "agent_did": "did:terachat:acme:fin-agent-001",
  "runtime": "wasm3",
  "capabilities": ["network.egress", "storage.read", "crypto.sign"],
  "agent_behavior": {
    "max_context_tokens": 8192,
    "auto_invoke_on_mention": true,
    "swarm_participant": true,
    "ttl_seconds": 0
  },
  "host_api_version": "1.3.0"
}
```

**ClawHub Agent Registry:** Discovery query không reveal User_ID — chỉ trả về `CAS_UUID` của bundle.
**Revenue Share Engine:** 70% về Publisher wallet tự động mỗi 30 ngày sau khi Client xác nhận BLAKE3 hash.

```

---

##### EDIT M-06
```yaml
edit_id:       "M-06"
conflict_id:   null
target_file:   "Web_Marketplace.md"
target_section: "Thêm §MARKETPLACE-11 Swarm Agent Orchestration (mới)"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
note:          "Architecture detail → Function.md FUNC-03 đến FUNC-05"
```

**Append:** Cross-reference section mô tả Swarm Workspace — nội dung chi tiết tại Function.md §FUNC-13/14.

---

#### FILE 5: `Function.md`

---

##### EDIT FUNC-01

```yaml
edit_id:       "FUNC-01"
conflict_id:   null
target_file:   "Function.md"
target_section: "§5 — sau FUNC-11, thêm FUNC-12"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**FUNC-12: FCP Trust Boundary Declaration**

Phân biệt rõ 2 chế độ:

| Chế độ | Server | AI Agent | Cam kết |
|---|---|---|---|
| **Default (Zero-Knowledge)** | Blind Relay | Nhận masked context | Server không đọc nội dung |
| **FCP Mode (Admin-Opt-In)** | Vẫn Blind Relay | Nhận plaintext context | TLS bảo vệ transit; AI endpoint thấy plaintext |

FCP Mode yêu cầu: YubiKey + typed consent + audit log signed.
Phù hợp khi AI endpoint là on-premise model do doanh nghiệp tự host.
```

---

##### EDIT FUNC-02

```yaml
edit_id:       "FUNC-02"
conflict_id:   null
target_file:   "Function.md"
target_section: "§2 User Functions — sau 'Tài liệu thông minh'"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
📱💻 **Offline Conflict Resolution:** Khi sửa tài liệu offline và reconnect phát hiện conflict:
1. Tier 2 (Mesh): Badge ⚠️ trên document — Desktop Super Node làm mediator
2. Tier 3 (Solo): WARNING toast "Bản này có thể bị ghi đè khi đồng bộ"
3. Khi reconnect: Bảng đối chiếu 2 cột bắt buộc hiện ra trước khi commit
   — đặc biệt với `content_type = CONTRACT | POLICY | APPROVAL`
```

---

##### EDIT FUNC-03

```yaml
edit_id:       "FUNC-03"
conflict_id:   null
target_file:   "Function.md"
target_section: "Thêm FUNC-13 Burner Agent Cross-Org Flow"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**FUNC-13: Burner Agent Cross-Org Collaboration Flow**

```text
[Admin Org A]
    │ Tạo FederationInviteToken (Signed JWT, scope: reconcile_invoices)
    ▼
[Admin Org B] nhận Token → xác nhận scope → counter-sign
    │
    ▼ [BurnerAgent.spawn() — cả hai Admin ký bằng YubiKey]
    │
[Burner Agent — Ephemeral sandbox, TTL=60min]
    │ Đọc dữ liệu trong org_a_scope ∩ org_b_scope
    │ Xử lý task
    │ Emit kết quả vào MLS Group E2EE
    ▼
[Task hoàn thành / TTL hết]
    │ ZeroizeOnDrop soul.db
    │ Generate BurnerTerminationProof (cả hai CA ký)
    ▼
[Admin Org A + B nhận TerminationProof] → "Tác tử đã tự hủy. Xem bằng chứng mật mã."
```

```

---

##### EDIT FUNC-04
```yaml
edit_id:       "FUNC-04"
conflict_id:   null
target_file:   "Function.md"
target_section: "Thêm FUNC-14 Swarm Workspace User Flow"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**FUNC-14: Swarm Workspace User Flow**

```text
[User] tạo Group Chat → bấm [+ Add Agent]
    │ Consent Modal: "Agent này sẽ đọc: [scope list]"
    │ User approve bằng Biometric
    ▼
[Agent join MLS Group như member — Agent_DID hiển thị trong member list]
    │ User @mention Agent Orchestrator: "Phân tích Q1 report và tóm tắt top 5 risks"
    ▼
[Orchestrator phân công Worker Agents]
    │ Worker 1: Data extraction
    │ Worker 2: Risk classification
    │ Worker 3: Vietnamese summary
    ▼
[Results stream về Group Chat qua Timeline View]
    │ Items cần approval → Supervisor nhận Biometric prompt
    ▼
[User bấm [Remove Agent] → MLS remove_member → Epoch rotation]
    → Agent không còn access kênh
```

```

---

##### EDIT FUNC-05
```yaml
edit_id:       "FUNC-05"
conflict_id:   null
target_file:   "Function.md"
target_section: "Thêm FUNC-15 Causal Smart Approval — Agent-Backed Decision Flow"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**FUNC-15: Causal Smart Approval — Agent-Backed Decision Flow**

Dùng cho: Phê duyệt chi tiêu, ký hợp đồng tự động, thực thi workflow có điều kiện.

```text
[Agent Worker phân tích request]
    ↓ PROPOSE action (ghi DecisionNode vào DAG)
    ↓
[Lõi Rust check: action có trong "human-required" list?]
    ├── Không → Agent EXECUTE trực tiếp
    └── Có → Notification đến Supervisor
              "Agent X đề xuất: [Tóm tắt action]. Approve?"
              [Supervisor xác thực Biometric → ký HumanApprovalRecord]
              ↓ EXECUTE (ghi DecisionNode(type=Execute))
              ↓ Non-Repudiation Audit → Append-Only Log
```

```

---

#### FILE 6: `TestMatrix.md`

---

##### EDIT T-01
```yaml
edit_id:       "T-01"
conflict_id:   "RC-02, RC-03, BL-01, BL-02, NI-01"
target_file:   "TestMatrix.md"
target_section: "§1 — cuối danh sách scenarios hiện tại"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append rows vào bảng scenarios:**

```markdown
| SC-08 | Android Doze mid-ZeroizeOnDrop | Force Android process freeze 50ms sau key derive, trước StrongBox wrap | Key material không tồn tại trong RAM sau resume; StrongBox wrap-on-derive đã hoàn thành | RC-02 |
| SC-09 | NSE Micro-NER load attempt | Trigger ONNX load trong NSE process context | `NsePolicy::ProhibitOnnxLoad` reject; fallback to regex-only; no Jetsam kill | RC-03 |
| SC-10 | Dead Man Switch during active CallKit | Trigger DMS lockout trong khi CallKit session active | `DeadManDeferralEntry` logged với call_id + counter delta; lockout deferred; call continues | BL-01 |
| SC-11 | EMDP Shun received for regular member | Valid Shun Record → all-iOS EMDP mesh, non-relay member | Case A: member evicted, TempGroupKey derived, `tainted_escrow` logged | BL-02 |
| SC-12 | EMDP Shun received for Tactical Relay | Valid Shun Record → all-iOS EMDP mesh, Tactical Relay | Case B: EMDP terminated, new election triggered, `EmdpTerminated` signal emitted | BL-02 |
| SC-13 | QUIC + gRPC parallel probe both succeed | Both QUIC ACK và gRPC handshake succeed simultaneously | gRPC wins (tiebreak); `probe_fail_count` NOT incremented; `strict_compliance` unchanged | NI-01 |
```

---

##### EDIT T-02

```yaml
edit_id:       "T-02"
conflict_id:   null
target_file:   "TestMatrix.md"
target_section: "§2 Extended Scenarios — tạo mới nếu chưa có"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
## §2 Extended Scenarios

| Scenario | Điều kiện | Expected behavior |
|---|---|---|
| SC-14 | Windows ARM64 + SAB unavailable | Fallback Tier 2 (Named Pipe ~200MB/s), log tier selection |
| SC-15 | Linux Flatpak attempt (blocked) | Install script detect, redirect to .deb/.rpm, user notification |
| SC-16 | AES-NI unavailable + high load crypto | Software fallback (ChaCha20), Admin Console warning, ~3x slower |
| SC-17 | Dart FFI GC race: buffer released before releaseNow() | NativeFinalizer catches, ZeroizeOnDrop executes, no UAF, audit log |
| SC-18 | EMDP 60min expire + iOS still only peer | Auto-transition SoloAppendOnly, UI banner "Chế độ chỉ đọc — chờ Desktop" |
| SC-19 | Shadow DB rename race với NSURLSession chunk write | Write lock queues chunk to hot_dag.db, no data loss, no corruption |
```

---

##### EDIT T-03

```yaml
edit_id:       "T-03"
conflict_id:   null
target_file:   "TestMatrix.md"
target_section: "§3 Pre-Gov Go-Live Checklist — tạo mới nếu chưa có"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append section mới:**

```markdown
## §3 Pre-Gov Go-Live Checklist

Ngoài tất cả scenarios, các hạng mục sau phải được verified bởi independent security auditor:

- [ ] Ed25519 signature verification trên mọi OPA Policy bundle
- [ ] HSM FIPS 140-3 Shamir's SSS ceremony (3-of-5 reconstruction test)
- [ ] Air-gapped license JWT validation (no network, TPM monotonic counter check)
- [ ] EMDP Key Escrow roundtrip (Desktop offline 60min → reconnect → DAG merge clean)
- [ ] Crypto-shred verification (forensic tool xác nhận không recovery được sau wipe)
- [ ] WasmParity CI Gate pass rate: 100% (→ Feature_Spec §5)
- [ ] AppArmor/SELinux profiles verified on target Gov Linux distro (→ Feature_Spec §16)
```

---

#### FILE 7: `BusinessPlan.md`

---

##### EDIT B-01

```yaml
edit_id:       "B-01"
conflict_id:   "PB-02, PB-03"
target_file:   "BusinessPlan.md"
target_section: "§10.2 Use of Funds — 'Compliance & Certifications' section"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append rows vào budget breakdown:**

```markdown
| Windows EV Code Signing Certificate | $500/năm | Bắt buộc cho SmartScreen reputation — mua Month 1 | Month 1 |
| Linux GPG Key + AppImage Cosign setup | $0 (internal) | → ops/signing-pipeline.md COSIGN-02, COSIGN-03 | Month 2 |
| AppArmor/SELinux policy authoring | $5,000 (consultant) | → Feature_Spec §16 — High priority | Month 2–3 |
```

**Append rows vào §11.1 Risk Register:**

```markdown
| Linux enterprise deployment blocked by AppArmor | Medium | Medium | Feature_Spec §16 postinstall script — Sprint 1 priority |
| Windows SmartScreen delay (30+ days reputation build) | Medium | Low | EV cert purchase Month 1; clean submissions from Day 1 |
```

---

##### EDIT B-02

```yaml
edit_id:       "B-02"
conflict_id:   null
target_file:   "BusinessPlan.md"
target_section: "§BIZ-LICENSE-03 — cuối section"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**Phân tách module để Gov/Bank audit:**

| Module | License | Scope audit |
|---|---|---|
| `terachat-core` (Crypto, MLS, CRDT, Mesh) | AGPLv3 | Public — Gov/Bank tự compile và verify |
| `terachat-license-guard` | BSL (Business Source) | Closed — không trong scope crypto audit |
| `terachat-ui` (Tauri, Flutter) | Apache 2.0 | Public |

**Sales pitch:** *"Toàn bộ cryptographic core có thể compile và audit độc lập.
License validation là module riêng không ảnh hưởng security audit scope."*

**Cryptographic Entanglement — Write-Only pattern:**
`DeviceIdentityKey` không bao giờ ra khỏi Secure Enclave dưới dạng raw bytes.
`License Guard` chỉ nhận `FeatureFlags` struct — không có raw key nào qua FFI.
```

---

##### EDIT B-03

```yaml
edit_id:       "B-03"
conflict_id:   null
target_file:   "BusinessPlan.md"
target_section: "§BIZ-TIER-05 — cập nhật tier table"
change_type:   "Replace"
sprint:        "Sprint2"
status:        "TODO"
```

**Tìm:** Bảng tier feature comparison có cột Community / Enterprise / GovMilitary.

**Thêm rows vào bảng (hoặc replace nếu thiếu columns):**

```markdown
| **Offline TTL** | 24h | 7 ngày (configurable) | **30 ngày** |
| EMDP Tactical Relay | ❌ | ✅ | ✅ |
| Air-Gapped License | ❌ | ✅ | ✅ |
| Compliance Retention | ❌ | 90 ngày | **7 năm** |
| **Chaos Engineering** | ❌ | Optional | **Bắt buộc trước go-live** |
| TEE License | ❌ | ❌ | Available |
```

---

##### EDIT B-04

```yaml
edit_id:       "B-04"
conflict_id:   null
target_file:   "BusinessPlan.md"
target_section: "§09/09 Licensing Strategy hoặc §10.2"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Append:**

```markdown
**License Distribution Channels:**

| Channel | Delivery | Security |
|---|---|---|
| Online | JWT qua email bảo mật + `cosign verify-blob` | Supply chain attack prevention |
| Air-Gapped (SCIF) | JWT trên USB AES-256, giao vật lý cho CISO | Không internet, không phone-home, không telemetry |

**Graceful Degradation Timeline:**

| T | Trạng thái | Impact |
|---|---|---|
| T-30 ngày | Banner vàng Admin Console | Không ảnh hưởng |
| T-0 | Admin Console partial lock | Chat/Mesh bình thường; AI + add user bị khóa |
| T+90 ngày | Refuse new bootstrap | App đang chạy OK; không restart được |
| Gia hạn | JWT mới → restore <5s | Không restart cần |
```

---

#### FILE 8: `ops/signing-pipeline.md` — TẠO MỚI

```yaml
conflict_id:  "PB-02, PB-03"
target_file:  "ops/signing-pipeline.md"
change_type:  "CreateNew"
sprint:       "Sprint2"
status:       "TODO"
```

**Nội dung file mới:**

```markdown
# ops/signing-pipeline.md — TeraChat Code Signing Pipeline

## COSIGN-01: iOS / macOS
- Tool: fastlane match + Apple Developer certificate
- Command: `bundle exec fastlane match appstore`
- Validation: `bundle exec fastlane match nuke --dry-run`
- Note: Requires Apple Developer Program membership ($99/year)

## COSIGN-02: Linux AppImage
- Tool: Cosign (Sigstore)
- Command: `cosign sign-blob --key release-key.pem --output-signature terachat.AppImage.sig terachat.AppImage`
- Customer verify: `cosign verify-blob --key terachat-root.pub --signature terachat.AppImage.sig terachat.AppImage`

## COSIGN-03: Linux .deb / .rpm
- Tool: GPG (detached signature)
- Command: `dpkg-sig --sign builder terachat_*.deb`
- Key rotation: Annually, 4096-bit RSA minimum
- APT/DNF repo: signed Release file

## COSIGN-04: Windows
- Tool: signtool.exe với EV Certificate
- Prerequisite: EV Code Signing cert (Sectigo / DigiCert) — ~$500/năm
- SmartScreen note: **30+ days clean submissions required for reputation**
  → Purchase Month 1; start clean submissions immediately.
- Command: `signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 /f cert.p12 terachat-setup.exe`
- Validation: `signtool verify /pa terachat-setup.exe`

## COSIGN-05: SBOM (CycloneDX 1.5)
- Generate: `cargo cyclonedx --format json --output terachat-sbom.json`
- Sign: `cosign sign-blob --key release-key.pem --output-signature terachat-sbom.json.sig terachat-sbom.json`
- Customer verify: `cosign verify-blob --key https://releases.terachat.com/cosign-pub.pem --signature terachat-sbom.json.sig terachat-sbom.json`
```

---

---

### SPRINT 3 — TECHNICAL DEBT (Tracked)

| Debt ID | File | Section | Mô tả | Ưu tiên |
|---|---|---|---|---|
| TD-01 | `Core_Spec.md` | §6.7 EMDP | Long-term fix cho tainted EmdpKeyEscrow sau Shun: Desktop pre-provision multiple escrow keys trước khi offline. Blocking: EDIT C-08 là accepted-risk workaround. | Post-Beta |
| TD-02 | `Core_Spec.md` | §11.4 Known Gaps | Border Node auto-detection heuristics — algorithm undefined. Blocking: F-05 EMDP mesh topology. | Sprint 3 |
| TD-03 | `Core_Spec.md` | §3.1 + §2.1 | Windows ARM64 SAB (SharedArrayBuffer) behavior validation on ARM64 WebView2. Blocking: Release on ARM64 Windows. | Sprint 3 |
| TD-04 | `Web_Marketplace.md` | §MARKETPLACE-05 | `.tapp` stale epoch key handling khi re-activated sau 12-month deprecation window. | Sprint 3 |

---

## §5 STATE MACHINE

### 5.1 Edit Item Lifecycle

```
States: TODO → IN_PROGRESS → PR_OPEN → REVIEWED → MERGED → VERIFIED

Transitions:
  TODO         ──sprint starts──────────────▶ IN_PROGRESS
  IN_PROGRESS  ──PR created─────────────────▶ PR_OPEN
  PR_OPEN      ──reviewer approved────────────▶ REVIEWED
  REVIEWED     ──CI passes + lead approve─────▶ MERGED
  MERGED       ──CI validation + smoke test───▶ VERIFIED

  Any state    ──CI fails──────────────────────▶ IN_PROGRESS (back)
  PR_OPEN      ──reviewer requests changes──────▶ IN_PROGRESS (back)
```

### 5.2 Conflict Lifecycle

```
States: OPEN → ADDRESSED → CLOSED

Transitions:
  OPEN       ──all linked edit_ids → MERGED──▶ ADDRESSED
  ADDRESSED  ──verification test passes──────▶ CLOSED
  CLOSED     ──regression detected────────────▶ OPEN (reopen)
```

### 5.3 Combo Fix Strategy (Sprint Planning Aid)

Các edits sau share codebase và nên được thực hiện trong cùng PR để tránh double-touch:

| Combo | Edits | Shared module | Rationale |
|---|---|---|---|
| **Combo A** — Mobile RAM Safety Net | C-02, C-03, C-04, C-05 | `crypto/zeroize.rs`, `nse_policy.rs` | Tất cả liên quan đến memory safety và audit logging trong mobile crypto lifecycle |
| **Combo B** — Mesh Resilience | C-08, C-06, C-07, C-14 | `mesh/emdp.rs`, `mesh/ble_beacon.rs` | EMDP exception + BLE disambiguation — cùng sprint, cùng module |
| **Combo C** — Network Integrity | C-09, C-10 | `infra/alpn.rs`, `crdt/dag.rs` | Cả hai là concurrency bugs — fix cùng PR với `tokio::sync` patterns |
| **Combo D** — Policy Sovereignty | C-11, M-01, M-02 | Spec-only edits | Cross-document spec reconciliation — review cùng với CISO + Platform Lead |

---

## §6 API / IPC CONTRACT

### 6.1 Find/Replace Protocol

Mọi edit có `change_type: Replace` phải tuân theo:

1. `find` string phải **unique trong file** — không được match nhiều hơn 1 occurrence.
2. Nếu không unique: dùng thêm context (2–3 dòng xung quanh) trong `find`.
3. Verify bằng `grep -n "<find_string>" <target_file>` — expected: exactly 1 match.

### 6.2 Append Protocol

Mọi edit có `change_type: Append` phải tuân theo:

1. Xác định anchor: section header hoặc dòng cuối cùng của section đó.
2. Thêm một dòng trống trước và sau nội dung append.
3. Verify bằng cách đọc lại section sau khi append — đảm bảo flow logic không bị gián đoạn.

### 6.3 Cross-Reference Contract

Mọi edit thêm cross-reference phải dùng format chuẩn:

```
Cross-reference: → <FileName>.md §<SectionNumber> <DescriptiveName>
```

Không dùng relative path (`../`). Không dùng URL. Chỉ dùng file name và section ID.

### 6.4 Code Snippet Contract

Mọi code snippet trong edits phải:

- Dùng `ring` crate hoặc `RustCrypto` — không self-implement crypto.
- Có `#[derive(ZeroizeOnDrop)]` cho mọi struct giữ key material.
- Không dùng `SystemTime::now()` cho ordering — dùng HLC.
- Không trả raw pointer từ `pub extern "C"` — dùng Token Protocol.

---

## §7 PLATFORM MATRIX

### 7.1 Conflict × Platform

| Conflict ID | 📱 iOS | 📱 Android | 📱 Huawei | 💻 macOS | 💻🖥️ Win | 🖥️ Linux |
|---|---|---|---|---|---|---|
| RC-01 | — | — | ✅ Affected | — | — | — |
| RC-02 | — | ✅ Primary | ✅ Affected | — | — | — |
| RC-03 | ✅ Primary | — | — | — | — | — |
| PB-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PB-02 | — | — | — | — | — | ✅ Primary |
| PB-03 | — | — | — | — | ✅ Primary | — |
| BL-01 | ✅ Primary | — | — | — | — | — |
| BL-02 | ✅ Primary | — | — | — | — | — |
| BL-03 | — | — | — | ✅ | ✅ | ✅ |
| NI-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| NI-02 | ✅ | ✅ | ✅ | ✅ | — | — |
| NI-03 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 7.2 Edit × Sprint × Platform

| Sprint | Edits | Platform(s) |
|---|---|---|
| Sprint 1 | C-01 đến C-21, F-01 đến F-08 | Tất cả platforms (Core + Feature) |
| Sprint 2 | D-01 đến D-07, M-01 đến M-06, FUNC-01 đến FUNC-05, T-01 đến T-03, B-01 đến B-04, O-01 (ops) | UI + Marketplace + Ops |
| Sprint 3 | TD-01 đến TD-04 | Core: iOS Mesh, Windows ARM64 |

---

## §8 NON-FUNCTIONAL REQUIREMENTS

### 8.1 Edit Quality

| Requirement | Threshold | Verification |
|---|---|---|
| Zero content loss | 100% nội dung hiện tại preserved | Manual review before merge |
| Cross-reference accuracy | Mọi `→ File.md §X` phải resolve | `grep -r "§X" <File.md>` |
| Code snippet compilability | Mọi Rust snippet phải compile (conceptually) | Peer review |
| ID uniqueness | Mỗi edit_id, conflict_id unique | Script check |

### 8.2 Process Constraints

| Constraint | Rule |
|---|---|
| Apply order | Core_Spec.md trước, Feature_Spec.md sau, rest parallel |
| Rollback window | Mỗi edit có thể rollback độc lập trong 48h sau merge |
| Review requirement | Sprint 1 edits cần ≥ 2 reviewers (Tech Lead + Security Lead) |
| CI gate | WasmParity + Clippy + cargo audit phải pass trước merge |

### 8.3 Performance Impact

Không có edit nào trong document này thay đổi:

- Hot path crypto operations
- BLE duty cycle
- SQLite WAL mode

Edits chỉ thêm: audit logging (C-04), platform clarification (C-01, C-06, C-07), safeguards (C-02, C-03, C-05).

---

## §9 SECURITY MODEL

### 9.1 Security-Critical Edits (ordered by risk)

| Edit ID | Security Improvement | Risk nếu không apply |
|---|---|---|
| C-05 | Android key material protection khỏi Doze | Key exposure trên all Android devices |
| C-08 | EMDP Shun exception — evict compromised relay | Compromised iOS Tactical Relay có thể ở trong EMDP mesh indefinitely |
| C-04 | Dead Man Switch audit trail | CISO không detect legitimate vs compromised deferral |
| C-03 | Explicit NSE ONNX prohibition | Jetsam kill → silent notification loss |
| C-11 | OPA policy sync bypass federation schema lock | Branch cluster có thể stuck với stale (insecure) OPA policy |

### 9.2 Không thay đổi Security Architecture

Các edits trong Arrange.md KHÔNG thay đổi:

- MLS E2EE core (RFC 9420)
- ZeroizeOnDrop pattern
- Hardware Root of Trust (Secure Enclave / StrongBox / TPM 2.0)
- Audit Log append-only invariant
- Token Protocol (no raw pointer across FFI)

### 9.3 New Audit Events (từ edits)

| Event | Edit Source | Struct |
|---|---|---|
| `DeadManDeferral` | C-04 | `DeadManDeferralEntry` |
| `EmdpShunEvent` | C-08 | `EmdpShunEvent { poisoned_node_id, hlc, tainted_escrow }` |
| `NsePolicyViolation` | C-03 | Log khi ONNX load attempt detected trong NSE context |

---

## §10 FAILURE MODEL

### 10.1 Impact nếu Blocker edits không được apply

| Conflict ID | Failure Mode | Detection | Impact |
|---|---|---|---|
| RC-03 (C-02, C-03) | NSE load ONNX → Jetsam kill | iOS Notification delivery failure, no error log | Tất cả iOS users không nhận push notifications silently |
| PB-01 (Feature_Spec.md rỗng) | 34+ TERA-CORE references unresolved | Developer confusion, wrong implementation | Implementation drift → security gaps in client code |
| RC-02 (C-05) | Android Doze freeze mid-ZeroizeOnDrop | Forensic memory analysis | Key material in RAM page → potential key extraction |
| BL-02 (C-08) | EMDP deadlock khi Shun + no Desktop | All-iOS mesh frozen after any Byzantine event | SOS messaging disabled during critical incident |
| NI-01 (C-10) | strict_compliance set incorrectly | ALPN always uses TCP, never QUIC | 30ms → 80ms RTT regression for all users on affected networks |

### 10.2 Impact nếu High Priority edits không được apply

| Conflict ID | Failure Mode | Impact |
|---|---|---|
| PB-02 (F-08 §16) | AppArmor/SELinux denial on Linux | Startup crash on Ubuntu/RHEL Gov deployments |
| PB-03 (COSIGN-04) | No EV cert → SmartScreen blocks install | Enterprise Windows pilots fail before first demo |
| BL-03 (C-11, M-02) | Branch cluster stale OPA state | Revoked users may retain access on Branch cluster |

---

## §11 VERSIONING & MIGRATION

### 11.1 Document Version History

| Version | Date | Summary |
|---|---|---|
| 1.0.0 | 2026-03-21 | Initial structured version — Sprint 1/2/3 structure, 12 conflict IDs, 22 fix edits |
| 2.0.0 | 2026-03-21 | Full restructure — 14-section production-grade format; merge raw edits + conflict analysis; 47 total edit IDs |

### 11.2 Edit ID Naming Convention

| Prefix | Target File | Range |
|---|---|---|
| `C-` | Core_Spec.md | C-01 đến C-21 |
| `F-` | Feature_Spec.md | F-01 đến F-08 |
| `D-` | Design.md | D-01 đến D-07 |
| `M-` | Web_Marketplace.md | M-01 đến M-06 |
| `FUNC-` | Function.md | FUNC-01 đến FUNC-05 |
| `T-` | TestMatrix.md | T-01 đến T-03 |
| `B-` | BusinessPlan.md | B-01 đến B-04 |
| `O-` | ops/signing-pipeline.md | O-01 (CreateNew), COSIGN-01 đến 05 |
| `TD-` | Technical Debt (multi-file) | TD-01 đến TD-04 |

### 11.3 Cách thêm Conflict mới

1. Assign `conflict_id` theo pattern layer: RC-xx (Runtime), PB-xx (Packaging), BL-xx (Logic), NI-xx (Network), EU-xx (Emergent).
2. Tạo EditRecord với edit_id mới (tiếp nối số cuối).
3. Thêm vào §4 FEATURE MODEL theo sprint.
4. Cập nhật §7.1 Platform Matrix.
5. Cập nhật §10 Failure Model.
6. Increment document version minor nếu additive, major nếu breaking.

---

## §12 OBSERVABILITY

### 12.1 CI Gates bắt buộc sau khi apply edits

| Gate | Command | Blocker |
|---|---|---|
| FFI-01: No raw pointer in `pub extern C` | `cargo clippy -- -D tera_ffi_raw_pointer` | Yes |
| KEY-02: ZeroizeOnDrop verification | `cargo miri test --test zeroize_verification` | Yes |
| WasmParity: wasm3 vs wasmtime | `cargo test --test wasm_parity` | Yes |
| Dependency audit | `cargo audit --deny warnings` | Yes |
| Secret scan | `gitleaks detect --source . --exit-code 1` | Yes |
| SBOM signature | `cosign verify-blob --key terachat-root.pub ...` | Yes (Sprint 2) |

### 12.2 Sprint Progress Tracking

| Sprint | Total Edits | Files | Done | Remaining |
|---|---|---|---|---|
| Sprint 1 | 29 (C-01 đến C-21 + F-01 đến F-08) | Core_Spec.md, Feature_Spec.md | — | 29 |
| Sprint 2 | 22 (D+M+FUNC+T+B+O edits) | 6 files | — | 22 |
| Sprint 3 | 4 (TD-01 đến TD-04) | 2 files | — | 4 |

### 12.3 Checklist Per Edit

Trước khi mark edit là MERGED:

- [ ] `find` string tìm được exactly 1 match trong file (nếu Replace)
- [ ] Nội dung append không duplicate với content hiện có
- [ ] Cross-references đúng format và resolve được
- [ ] Code snippets nhất quán với `ring`/`RustCrypto` constraint
- [ ] `ZeroizeOnDrop` present trên mọi struct mới giữ key material
- [ ] CI gates pass

---

**Phân tích routing:**

Nội dung document 15 là một báo cáo điều hành mang tính **business/strategic positioning** — so sánh competitive, problem landscape, value proposition, và future outlook. Không chứa technical spec hay implementation detail.

Theo document dependency map trong `Arrange.md §2.1`:

```
BusinessPlan.md (TERA-BIZ) ← phụ thuộc TERA-CORE cho technical claims
TestMatrix.md (TERA-TEST)  ← leaf node
```

**Routing quyết định: `BusinessPlan.md` (TERA-BIZ)**

Lý do: nội dung thuộc loại *competitive analysis + risk landscape + strategic positioning* — đây là domain của TERA-BIZ, không phải TERA-CORE hay TERA-FEAT. Cụ thể nhất là mapping vào section **§6 Competitive Advantage** và **§11 Risk & Mitigation** của BusinessPlan.md hiện tại.

---

**Edit record cho Arrange.md:**

```yaml
edit_id:       "B-05"
conflict_id:   null
target_file:   "BusinessPlan.md"
target_section: "§6 Competitive Advantage — sau §6.3 Head-to-Head Comparison"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Nội dung append vào §6:**

```markdown
### §6.4 Systemic Risk Landscape — Tại sao Window Cơ hội Đang Mở

Giai đoạn 2023–2026 đánh dấu bước ngoặt khi các lỗi hệ thống chuyển từ "trục trặc cục bộ" sang "thảm họa mang tính hệ thống." Bốn nhóm rủi ro hội tụ tạo ra demand không thể đảo ngược:

| Nhóm Rủi ro | Biểu hiện | Impact với TeraChat |
|---|---|---|
| **Tập trung hóa Cloud** | AWS us-east-1 cascading failure (12/2021), Cloudflare (6/2022) | TeraChat single-binary on-prem loại bỏ single point of failure |
| **Mối đe dọa địa chính trị** | Salt Typhoon (US telecoms), drone attacks vào data center | Air-gapped + BLE Mesh hoạt động khi infrastructure bị tấn công |
| **Chuỗi cung ứng & Danh tính** | XZ Utils backdoor, Change Healthcare, Snowflake API breach | Zero-Knowledge: server mù; không có credential tĩnh |
| **Tác nhân AI vượt quyền** | AWS Kiro xóa môi trường, Meta AI data leak | WASM sandbox + OPA policy + human-in-the-loop cho mọi destructive action |

**So sánh kiến trúc niềm tin:**

| Yếu tố | Hệ thống Truyền thống (SaaS cũ) | TeraChat |
|---|---|---|
| Mô hình niềm tin | Implicit trust sau perimeter | Xác minh mật mã liên tục |
| Phạm vi sự cố | Cascading, hệ thống | Cục bộ, phân lập |
| Quản trị AI | IAM tĩnh cho người dùng | JIT provisioning cho cả human + AI agent |
| Chuỗi cung ứng | Dễ bị nhiễm độc transitive | Immutable binary, reproducible build, SBOM |
| Khả năng offline | 0 | BLE Mesh + CRDT DAG |

**Kết luận positioning:** TeraChat không cạnh tranh trên feature — cạnh tranh trên *kiến trúc niềm tin*. Các nền tảng SaaS cũ không thể retrofit Zero-Knowledge hay Offline Mesh mà không rebuild hoàn toàn. Window cơ hội: 18–24 tháng trước khi đối thủ lớn vào thị trường.
```

---

**Edit record thứ hai:**

```yaml
edit_id:       "B-06"
conflict_id:   null
target_file:   "BusinessPlan.md"
target_section: "§11 Risk & Mitigation — sau bảng Risk Register hiện tại"
change_type:   "Append"
sprint:        "Sprint2"
status:        "TODO"
```

**Nội dung append vào §11:**

```markdown
### §11.3 Strategic Outlook — Niềm tin như Lợi thế Cạnh tranh

Khái niệm "niềm tin" trong công nghệ đang dịch chuyển từ *implicit trust* sang *continuous cryptographic proof*. Khi số lượng AI agent vượt xa người dùng con người và căng thẳng địa chính trị vũ khí hóa internet infrastructure, các hệ thống truyền thống trở thành rủi ro không thể cứu vãn.

**Ba lợi thế dài hạn của kiến trúc TeraChat:**

1. **Giảm blast radius:** Phân lập rủi ro theo vùng; một sự cố không cascade toàn hệ thống. Bảo vệ uy tín thương hiệu khi đối thủ sập.

2. **AI-safe by design:** Các rào chắn WASM sandbox + OPA policy cho phép doanh nghiệp triển khai AI agent mạnh dạn trong khi đối thủ còn ngần ngại. Đây là lợi thế ROI thực sự trong 2027–2030.

3. **Compliance tự nhiên:** Kiến trúc phi tập trung + audit log Ed25519 + reproducible build SBOM đơn giản hóa báo cáo theo SEC cybersecurity disclosure rules, ISO 27001, và các quy định data localization SEA.

**Target narrative cho investor:** TeraChat không bán phần mềm — bán *khả năng phục hồi như lợi thế cạnh tranh*. Doanh nghiệp adopt TeraChat không chỉ tồn tại qua kỷ nguyên rủi ro hệ thống; họ biến resilience thành moat.
```

---

## §13 APPENDIX

### 13.1 Conflict ID Glossary

| ID | Layer | Description | Severity |
|---|---|---|---|
| RC-01 | L1 Runtime | Huawei WASM JIT vs AOT mandate — unreconciled dual-path | Blocker |
| RC-02 | L1 Runtime | Android `mlock()` gap — no mitigation for Doze mid-ZeroizeOnDrop | Blocker |
| RC-03 | L1 Runtime | NSE 20MB ceiling — ONNX + Arena + decrypt = overflow | Blocker |
| PB-01 | L2 Packaging | Feature_Spec.md empty — 34+ TERA-CORE references unresolved | Blocker |
| PB-02 | L2 Packaging | Linux Flatpak vs seccomp-bpf deadlock — no alternative specified | High |
| PB-03 | L2 Packaging | Windows SmartScreen EV cert delay — GTM timing risk | High |
| BL-01 | L3 Logic | Dead Man Switch + CallKit deferral — no audit trail | High |
| BL-02 | L3 Logic | EMDP Shun + MLS epoch causal deadlock | High |
| BL-03 | L3 Logic | OPA rollback protection vs Federation schema mismatch | High |
| NI-01 | L4 Network | QUIC parallel probe race → probe_fail_count corrupted | High |
| NI-02 | L4 Network | BLE channel confusion — Advertising vs GATT for PQ keys | High |
| NI-03 | L4 Network | VACUUM INTO mid-write race — hot_dag.db integrity | High |

### 13.2 Edit ID Quick Reference

| Edit ID | File | Sprint | Conflict | Status |
|---|---|---|---|---|
| C-01 | Core_Spec.md | 1 | RC-01 | TODO |
| C-02 | Core_Spec.md | 1 | RC-03 | TODO |
| C-03 | Core_Spec.md | 1 | RC-03 | TODO |
| C-04 | Core_Spec.md | 1 | BL-01 | TODO |
| C-05 | Core_Spec.md | 1 | RC-02 | TODO |
| C-06 | Core_Spec.md | 1 | NI-02 | TODO |
| C-07 | Core_Spec.md | 1 | NI-02 | TODO |
| C-08 | Core_Spec.md | 1 | BL-02 | TODO |
| C-09 | Core_Spec.md | 1 | NI-03 | TODO |
| C-10 | Core_Spec.md | 1 | NI-01 | TODO |
| C-11 | Core_Spec.md | 1 | BL-03 | TODO |
| C-12 | Core_Spec.md | 1 | — | TODO |
| C-13 | Core_Spec.md | 1 | — | TODO |
| C-14 | Core_Spec.md | 1 | — | TODO |
| C-15 | Core_Spec.md | 1 | — | TODO |
| C-16 | Core_Spec.md | 1 | — | TODO |
| C-17 | Core_Spec.md | 1 | — | TODO |
| C-18 | Core_Spec.md | 1 | — | TODO |
| C-19 | Core_Spec.md | 1 | — | TODO |
| C-20 | Core_Spec.md | 1 | — | TODO |
| C-21 | Core_Spec.md | 1 | — | TODO |
| F-01 | Feature_Spec.md | 1 | PB-01 | TODO |
| F-02 | Feature_Spec.md | 1 | — | TODO |
| F-03 | Feature_Spec.md | 1 | — | TODO |
| F-04 | Feature_Spec.md | 1 | RC-01 | TODO |
| F-05 | Feature_Spec.md | 1 | PB-01 | TODO |
| F-06 | Feature_Spec.md | 1 | — | TODO |
| F-07 | Feature_Spec.md | 1 | RC-03 | TODO |
| F-08 | Feature_Spec.md | 1 | PB-02 | TODO |
| D-01 | Design.md | 2 | BL-01/02 | TODO |
| D-02 | Design.md | 2 | — | TODO |
| D-03 | Design.md | 2 | — | TODO |
| D-04 | Design.md | 2 | — | TODO |
| D-05 | Design.md | 2 | — | TODO |
| D-06 | Design.md | 2 | — | TODO |
| D-07 | Design.md | 2 | — | TODO |
| M-01 | Web_Marketplace.md | 2 | RC-01 | TODO |
| M-02 | Web_Marketplace.md | 2 | BL-03 | TODO |
| M-03 | Web_Marketplace.md | 2 | — | TODO |
| M-04 | Web_Marketplace.md | 2 | — | TODO |
| M-05 | Web_Marketplace.md | 2 | — | TODO |
| M-06 | Web_Marketplace.md | 2 | — | TODO |
| FUNC-01 | Function.md | 2 | — | TODO |
| FUNC-02 | Function.md | 2 | — | TODO |
| FUNC-03 | Function.md | 2 | — | TODO |
| FUNC-04 | Function.md | 2 | — | TODO |
| FUNC-05 | Function.md | 2 | — | TODO |
| T-01 | TestMatrix.md | 2 | RC-02/03/BL-01/02/NI-01 | TODO |
| T-02 | TestMatrix.md | 2 | — | TODO |
| T-03 | TestMatrix.md | 2 | — | TODO |
| B-01 | BusinessPlan.md | 2 | PB-02/03 | TODO |
| B-02 | BusinessPlan.md | 2 | — | TODO |
| B-03 | BusinessPlan.md | 2 | — | TODO |
| B-04 | BusinessPlan.md | 2 | — | TODO |
| O-01 | ops/signing-pipeline.md | 2 | PB-02/03 | TODO |
| TD-01 | Core_Spec.md | 3 | BL-02 | TODO |
| TD-02 | Core_Spec.md | 3 | — | TODO |
| TD-03 | Core_Spec.md | 3 | — | TODO |
| TD-04 | Web_Marketplace.md | 3 | — | TODO |

### 13.3 File Summary

| File | Trạng thái | Sprint 1 Edits | Sprint 2 Edits | Sprint 3 Debt |
|---|---|---|---|---|
| `Core_Spec.md` | Existing — patch | C-01 đến C-21 (21) | — | TD-01, TD-02, TD-03 |
| `Feature_Spec.md` | **TẠO MỚI** | F-01 đến F-08 (8) | — | — |
| `Design.md` | Existing — patch | — | D-01 đến D-07 (7) | — |
| `Web_Marketplace.md` | Existing — patch | — | M-01 đến M-06 (6) | TD-04 |
| `Function.md` | Existing — patch | — | FUNC-01 đến FUNC-05 (5) | — |
| `TestMatrix.md` | Existing — patch | — | T-01 đến T-03 (3) | — |
| `BusinessPlan.md` | Existing — patch | — | B-01 đến B-04 (4) | — |
| `ops/signing-pipeline.md` | **TẠO MỚI** | — | O-01 / COSIGN-01 đến 05 | — |

---

*TeraChat Arrange.md v2.0.0 — Restructured 2026-03-21*
*Dùng file này như master checklist trong sprint planning. Check-off từng EDIT ID khi VERIFIED.*
*Mỗi edit độc lập — có thể rollback riêng lẻ trong 48h sau merge.*

Dựa vào file tài liệu gốc `BusinessPlan.md` của hệ thống TeraChat, hãy cập nhật và tái cấu trúc lại tài liệu này bằng cách tích hợp nội dung về chiến lược "Ngựa Thành Troy" (Combo 2-3-4) và các lập luận pháp lý chiến lược.

Yêu cầu giữ nguyên văn phong B2B Enterprise (sắc bén, tập trung vào giải pháp cho C-Level/CISO) và định dạng Markdown gốc. Hãy chèn/sửa các nội dung sau vào ĐÚNG các vị trí được chỉ định:

### YÊU CẦU 1: Cập nhật "Phần 3. Go-to-Market Strategy & Operations"

Thay thế hoặc định hình lại mục `3.1 GTM Phases` thành: **3.1 Chiến lược Go-to-Market**
Tích hợp 3 giai đoạn sau vào mục này:

- **Giai đoạn 1: Tạo Compliance as a Service:** Nhắm vào CISO/Legal với Compliance Dashboard, Legal as a Feature (Cam kết đền bù pháp lý), và tính năng Vùng cách ly (Data Sovereignty). Thay vì bán app chat, hãy bán "Sự an tâm".
- **Giai đoạn 2: Land & Expand:** Luồng Onboarding qua gói "Black Ops Team" (nhóm nhỏ 20 người dùng cho dự án mật). Định vị song song với Slack/Teams. Rủi ro bằng 0, trải nghiệm mượt mà để nuôi dưỡng "Internal Champions".
- **Giai đoạn 3: One-Click Migration:** Dùng TeraChat Migration Suite làm đòn dứt điểm. Ánh xạ 1:1 API của Slack/Teams (channels, threads, files). Chạy "Shadow Mode" đồng bộ realtime 30 ngày để IT có thể Cut-over với 0 giờ downtime.

### YÊU CẦU 2: Bổ sung "Lập luận Pháp lý về Migration" vào Phần 3

Tạo một sub-section mới trong Phần 3 (ví dụ: `3.8 Tính hợp pháp của Data Migration`) để giải quyết objection của Giám đốc Pháp chế:

- **Quyền sở hữu dữ liệu:** Nhấn mạnh Khách hàng sở hữu 100% dữ liệu trên Slack/Teams, không vi phạm ToS.
- **Cơ chế kỹ thuật:** Sử dụng Official APIs (Slack Corporate Export API, Microsoft Graph API) thông qua ủy quyền OAuth 2.0.
- **Data Portability:** Tuân thủ GDPR/CCPA về quyền di động dữ liệu.

### YÊU CẦU 3: Cập nhật "Phần 2. Competitive Advantage"

Thêm một mục mới (ví dụ: `2.11 Vũ khí Pháp lý Phi đối xứng: Legal Indemnification`) để giải thích tại sao TeraChat dám đền bù $X triệu:

- Phân tích rủi ro của Slack/Teams: Dùng Server-side encryption, giữ chìa khóa, nên rủi ro lộ plaintext cao -> Không dám cam kết.
- Điểm mạnh của TeraChat: Dựa vào Zero-Knowledge & E2EE. Kể cả nhân viên/hacker xâm nhập server cũng chỉ thấy ciphertext. Xác suất rủi ro bằng 0.
- Biến đây thành đòn bẩy tâm lý (Psychological Leverage) để chốt sales Enterprise.

### YÊU CẦU 4: Cập nhật "Phần 6. Funding Allocation & Operations"

Bổ sung cấu trúc tổ chức đội ngũ (Task Forces) vào phần Vận hành/Giải ngân:

- **Đội Khiên chắn (Shield):** Legal, Security, QA -> Tập trung chứng chỉ ISO, SOC2 và Compliance Dashboard.
- **Đội Mũi nhọn (Spearhead):** Product Design, Growth -> Tập trung Onboarding siêu mượt cho gói Black Ops 20 người.
- **Đội Xây cầu (Bridge):** Data Engineers -> Tập trung hoàn thiện TeraChat Migration Suite hút dữ liệu từ Slack/Teams.

Sau khi tiếp nhận yêu cầu này, hãy in ra toàn bộ nội dung của file `BusinessPlan.md` mới đã được tích hợp hoàn chỉnh và mạch lạc.
Tôi cần xem tài liệu Pricing_Packages.md để hiểu đúng context về tính năng "doanh nghiệp tự code tiện ích" trước khi đề xuất giải pháp kiến trúc.Có vẻ file `Pricing_Packages.md` chưa được upload vào hệ thống. Tuy nhiên, dựa trên context bạn mô tả — **doanh nghiệp tự code tiện ích** — tôi hoàn toàn hiểu bài toán. Hãy để tôi phân tích ngay.

---

# Kiến trúc TeraChat `.tapp` — Mô hình WeChat MiniProgram

## Vấn đề gốc rễ cần giải quyết

```
Mô hình AOT (.dylib nhúng sẵn):        Mô hình cần đạt được:
────────────────────────────────        ────────────────────────────────
✅ Vượt Rule 2.5.2                      ✅ Vượt Rule 2.5.2
❌ Doanh nghiệp KHÔNG tự code được     ✅ Doanh nghiệp TỰ code tiện ích
❌ TeraChat phải compile từng plugin    ✅ TeraChat chỉ cung cấp SDK/Runtime
❌ Mỗi plugin mới = release app mới    ✅ Plugin mới = không cần update app
❌ App phình to theo số plugin          ✅ App size cố định
```

---

## Giải pháp: Áp dụng Mô hình WeChat JSCore vào TeraChat

### Nền tảng pháp lý Apple cho phép

```
Apple CẤM:                          Apple CHO PHÉP (ngoại lệ):
──────────────────────────────      ──────────────────────────────
❌ Tải file .wasm từ server         ✅ Tải file .js / .html từ server
❌ Tải file .dylib từ server        ✅ Chạy JS trong JavaScriptCore
❌ JIT compiler tự triển khai       ✅ Dùng WebKit engine của Apple
❌ Thực thi mã nhị phân động        ✅ Thực thi JS trong Sandbox WebView
```

> **Chìa khóa:** TeraChat không tải *mã máy* — tải *mã nguồn JS* và giao cho Apple's engine thực thi. Apple tự xử lý, Apple tự chịu trách nhiệm runtime.

---

## Kiến trúc Chi tiết: TeraChat MiniApp Runtime

### Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                    TeraChat iOS App                          │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │   App Core      │    │     .tapp Runtime Engine      │   │
│  │  (Swift/ObjC)   │    │                              │   │
│  │                 │    │  ┌────────────────────────┐  │   │
│  │  - Chat         │    │  │  JavaScriptCore (JSC)  │  │   │
│  │  - Auth         │◄───┤  │  (Apple's engine)      │  │   │
│  │  - File         │    │  │                        │  │   │
│  │  - Notification │    │  │  ┌──────────────────┐  │  │   │
│  │                 │    │  │  │  .tapp Sandbox   │  │  │   │
│  └─────────────────┘    │  │  │  ┌────────────┐  │  │  │   │
│                         │  │  │  │ JS Bundle  │  │  │  │   │
│  ┌─────────────────┐    │  │  │  │(từ server) │  │  │  │   │
│  │  TeraChat API   │    │  │  │  └────────────┘  │  │  │   │
│  │  Bridge (Swift) │◄───┤  │  └──────────────────┘  │  │   │
│  │                 │    │  └────────────────────────┘  │   │
│  │  - sendMessage()│    │                              │   │
│  │  - getUser()    │    │  Mỗi .tapp = 1 JSC instance  │   │
│  │  - uploadFile() │    │  hoàn toàn cô lập            │   │
│  └─────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Tải JS Bundle
                              ┌─────┴──────┐
                              │  .tapp CDN │
                              │  (Server)  │
                              └────────────┘
```

---

### Luồng hoạt động thực tế

```
Doanh nghiệp A tự code tiện ích "HR Leave Request":

Bước 1 — DEV (Doanh nghiệp tự làm):
  Dùng TeraChat SDK (giống WeChat DevTools)
  Code bằng JavaScript/TypeScript thuần
  Gọi TeraChat Bridge API:
    TeraChatAPI.sendMessage({to: "hr_channel", content: form})
    TeraChatAPI.getCurrentUser() → {id, name, department}
    TeraChatAPI.uploadFile(pdfBlob) → fileUrl

Bước 2 — PUBLISH:
  Build → xuất ra file bundle.js (đã minify + encrypt)
  Upload lên TeraChat Developer Portal
  TeraChat review (automated security scan ~24h)
  Xuất bản lên Private Marketplace (chỉ nội bộ công ty)

Bước 3 — RUNTIME trên iOS:
  User bấm mở tiện ích "HR Leave Request"
  App tải bundle.js từ CDN về RAM (không lưu disk)
  Nạp vào JSC Sandbox instance mới
  Render giao diện qua WKWebView
  Mọi call API → qua Bridge → App Core xử lý
  Đóng tiện ích → JSC instance bị hủy hoàn toàn
```

---

### Thiết kế TeraChat Bridge API (SDK cho doanh nghiệp)

```javascript
// ============================================
// TeraChat .tapp SDK — Doanh nghiệp sử dụng
// ============================================

// 1. MESSAGING
TeraChatAPI.sendMessage({
  channelId: "general",
  content: "Xin nghỉ phép ngày 25/3",
  attachments: [fileUrl],
  mentions: ["@manager_id"]
})

// 2. USER & ORG
const user = await TeraChatAPI.getCurrentUser()
// → { id, name, email, department, role }

const members = await TeraChatAPI.getChannelMembers("team-dev")

// 3. FILE
const url = await TeraChatAPI.uploadFile(blob, "leave-form.pdf")
const file = await TeraChatAPI.downloadFile(fileId)

// 4. STORAGE (sandbox riêng mỗi .tapp)
await TeraChatAPI.storage.set("draft", JSON.stringify(formData))
const draft = await TeraChatAPI.storage.get("draft")

// 5. UI NATIVE COMPONENTS
TeraChatAPI.ui.showDatePicker(({ date }) => setLeaveDate(date))
TeraChatAPI.ui.showAlert({ title: "Đã gửi!", type: "success" })
TeraChatAPI.ui.navigate("back")

// ============================================
// CÁC API BỊ SANDBOX CHẶN — Không thể gọi:
// ============================================
// ❌ fetch("https://external-server.com")  → bị chặn
// ❌ localStorage                          → không tồn tại
// ❌ navigator.geolocation                 → cần xin phép
// ❌ XMLHttpRequest đến domain lạ          → bị chặn
// ❌ eval(), new Function()                → bị chặn
```

---

### So sánh trực tiếp với WeChat MiniProgram

```
Tiêu chí              WeChat MiniProgram        TeraChat .tapp
────────────────────────────────────────────────────────────────
Runtime               JSCore + WKWebView         JSCore + WKWebView
Ngôn ngữ dev          WXML + WXSS + JS           HTML + CSS + JS/TS
SDK                   wx.sendMessage()           TeraChatAPI.sendMessage()
Sandbox               Có, cô lập mỗi app         Có, cô lập mỗi .tapp
Tải từ server         ✅ JS bundle               ✅ JS bundle
Vượt Rule 2.5.2       ✅                         ✅
Dev tự publish        ✅ (WeChat DevTools)        ✅ (TeraChat DevTools)
Private distribution  ✅ (Enterprise WeChat)      ✅ (Private Marketplace)
Context               Super-app xã hội           Super-app doanh nghiệp
```

---

## Cơ chế Bảo mật Sandbox — Tại sao Apple chấp nhận?

```
Mỗi .tapp chạy trong vùng cô lập hoàn toàn:

┌─────────────────────────────────────────────┐
│              .tapp Sandbox                  │
│                                             │
│  ✅ Có thể:                                 │
│     - Gọi TeraChat Bridge API (whitelist)   │
│     - Đọc/ghi storage riêng của .tapp       │
│     - Render UI trong WKWebView             │
│     - Nhận data từ TeraChat (qua Bridge)    │
│                                             │
│  ❌ Không thể:                              │
│     - Gọi API ngoài TeraChat domain         │
│     - Truy cập camera/micro (không xin phép)│
│     - Đọc data của .tapp khác               │
│     - Truy cập file system của app          │
│     - Chạy eval() / dynamic code gen        │
│     - Giao tiếp trực tiếp với server riêng  │
└─────────────────────────────────────────────┘

→ Apple reviewer thấy: "Đây là WebView sandbox"
→ Không khác gì Safari chạy một trang web
→ Hoàn toàn hợp lệ theo App Store Guidelines
```

---

## Kết hợp 2 mô hình: Giải pháp Hybrid hoàn chỉnh

```
Loại Plugin              Mô hình              Lý do
──────────────────────────────────────────────────────────────────
Plugin hệ thống          AOT .dylib           Cần hiệu năng cao
(OCR, mã hóa, camera)    (nhúng sẵn)          Truy cập native API

Plugin doanh nghiệp      JSCore Sandbox       Doanh nghiệp tự code
(HR, ERP, Workflow)      (tải JS từ server)   Không cần update app

Plugin public            JSCore Sandbox       Bên thứ 3 publish
(3rd party)              (tải JS từ server)   TeraChat review JS code
```

```
App Size khi dùng Hybrid:

  App Core:              ~40 MB
  System plugins (AOT):  ~30 MB  (OCR, encrypt, camera...)
  JSCore Runtime:        ~15 MB  (1 lần, dùng mãi)
  ─────────────────────────────
  Tổng cố định:          ~85 MB  ← KHÔNG tăng dù có 1000 plugin JS
  Plugin JS mỗi cái:     ~200KB  ← Tải về RAM, không lưu disk
```

---

## Tóm tắt Toàn bộ Kiến trúc

```
                    TỔNG KẾT KIẾN TRÚC .TAPP
    ┌──────────────────────────────────────────────┐
    │                                              │
    │   Plugin hệ thống   →   AOT .dylib           │
    │   (hiệu năng cao)       (nhúng trong .ipa)   │
    │                                              │
    │   Plugin doanh nghiệp → JSCore Sandbox       │
    │   (linh hoạt, mở rộng)  (tải JS từ CDN)     │
    │                                              │
    │   Cả hai đều:                                │
    │   ✅ Vượt Apple Rule 2.5.2                   │
    │   ✅ Chạy trong Sandbox cô lập               │
    │   ✅ Doanh nghiệp tự phát triển được         │
    │   ✅ App size không phình to vô hạn           │
    │   ✅ Không cần update app khi thêm plugin     │
    └──────────────────────────────────────────────┘
```

> **Kết luận:** TeraChat không cần chọn một trong hai mô hình — **dùng cả hai có chủ đích**. AOT cho những gì cần sức mạnh native, JSCore Sandbox cho những gì cần sự linh hoạt của ecosystem. Đây chính xác là cách WeChat vận hành MiniProgram song song với native features của họ.

Bạn muốn tôi đi sâu vào phần **TeraChat DevTools** (công cụ để doanh nghiệp code `.tapp`) hay phần **security review pipeline** khi doanh nghiệp publish tiện ích không?
