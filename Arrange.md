C1 — Hợp nhất UI: Flutter-only Mobile
Loại bỏ React Native. Flutter Dart FFI → Rust C ABI cho cả iOS + Android + Huawei
iOS: Dart FFI → UniquePtr C++ wrapper. Android: Dart FFI TypedData. 1 codebase, 1 team, throughput ~400MB/s đồng nhất
Tauri giữ nguyên Desktop. Mất: JSI C++ pointer tối ưu iOS ~5-10% vs Dart FFI. Được: -50% surface bug, +1 platform (Huawei)
C2 — WASM Behavioral Parity Test Suite
Không cần đồng nhất engine. Cần đảm bảo output giống nhau: thêm WasmParity CI gate chạy cùng test
vector trên wasm3 (iOS) và wasmtime (Android). Fail → block merge. Latency delta ≤ 20ms là chấp nhận được, nhưng
output semantic phải identical. Ghi rõ vào Feature_Spec.md: "wasm3 = reference runtime, wasmtime = optimized runtime"
C3 — Huawei HarmonyOS Stack (Khẩn cấp — cần thêm vào Core_Spec.md)
Push: HMS Push Kit (HPK) thay FCM. Rust FFI gọi HiAI Foundation API thay NNAPI. BLE: HarmonyOS BLE API tương đương
Attestation: HMS SafetyDetect DeviceIntegrity() thay Play Integrity. TrustZone TEE thay StrongBox (cùng ARM API, khác HAL)
WASM: HarmonyOS cho phép wasmtime JIT (không bị W^X như iOS) → dùng cùng engine Android. Distribution: AppGallery
Enterprise MDM = Huawei Device Manager. Không có dynamic WASM từ marketplace → áp dụng AOT bundle như iOS
C4 — iOS Key Protection: Double-Buffer Zeroize Protocol
Thay madvise(MADV_NOCORE) đơn lẻ bằng: (1) Phân bổ key vào 2 page liền kề MAP_ANONYMOUS|MAP_PRIVATE
(2) Ngay sau decrypt xong: ghi đè 0x00 vào page 1 TRƯỚC KHI dùng key. Dùng key từ page 2. (3) Sau ZeroizeOnDrop:
ghi đè cả 2 page. Nếu Jetsam kill trước Drop: page 1 đã clean, page 2 còn key nhưng là 1 page đơn lẻ khó exploit hơn
C5 — Tauri SAB/COOP: Fallback IPC Ladder
Tier 1: SharedArrayBuffer (COOP+COEP headers OK) → ~500MB/s. Tier 2: Named Pipe IPC (Windows)
~200MB/s. Tier 3: Protobuf-over-stdin copy ~50MB/s. Rust Core tự detect SAB availability lúc init, chọn tier cao nhất
có sẵn. UI không biết tier — chỉ thấy throughput khác. Log tier selection vào audit trail.
C6 — Push Key / MLS Epoch: Versioned Key Ladder
Thêm field push_key_version (u32) vào Shared Keychain. NSE đọc version từ payload header trước khi decrypt.
Nếu payload_version == keychain_version → giải mã bình thường. Nếu lệch: NSE cache ciphertext raw vào nse_staging.db
và bắn content-available:1. Main App nhận wakeup → rotate key → decrypt staged payload → clear staging. Zero notification loss.
C7 — iOS Mesh Graceful Super Node Handover
Khi iOS detect memory pressure sắp trigger Jetsam: Rust Core broadcast MeshRoleHandover(candidate_node_id)
tới Desktop/Android peer qua BLE trước khi BLE scan bị kill. Desktop nhận → assume Super Node role ngay.
iOS → Leaf Node. UI hiển thị "Đã chuyển vai trò Relay sang [tên thiết bị]" thay vì silent disconnect.
C8 — Linux Multi-Init Daemon Support
Thêm init detection vào install script: detect systemd/openrc/runit/s6/launchd. Generate correct service file
cho từng init system. Fallback: XDG autostart (.desktop file) cho desktop environments không có systemd.
terachat-daemon viết PID file → bất kỳ init nào cũng có thể monitor. Ghi vào Feature_Spec.md §6.3.
Giải pháp Gốc rễ — Formal IPC Memory Ownership Contract (trả lời câu hỏi phản biện)
Rust Core xuất 2 FFI primitive thay vì raw pointer: (1) tera_buf_acquire(id) → trả handle opaque (u64 token),
không phải raw pointer. (2) tera_buf_release(token) → Rust mới được phép zeroize. iOS JSI và Android Dart FFI
đều gọi tera_buf_release() trong destructor/finalizer của mình. Rust Core có reference counter per-token:
ZeroizeOnDrop chỉ thực thi khi ref_count == 0. CI lint rule: cấm FFI endpoint trả Vec/ptr trực tiếp không qua
token protocol. Đây là Formal Memory Contract thay thế "convention" hiện tại — cần thêm vào Core_Spec.md §2.1

## Tóm tắt: File nào cần commit gì

| File | Nội dung commit | Sprint |
|---|---|---|
| `Core_Spec.md` | Thêm §Huawei HMS Stack; Thêm §Formal IPC Memory Contract với token protocol; Cập nhật Remote Attestation table thêm Huawei row | Sprint 1 |
| `Feature_Spec.md` | Đổi "React Native + Flutter" → "Flutter unified"; Thêm WasmParityTestSuite requirement; Thêm IPC Tier Ladder §6.1; Đổi madvise → Double-Buffer Zeroize §6.4; Thêm multi-init daemon §6.3; Thêm Versioned Push Key Ladder §6.6 | Sprint 1 |
| `Design.md` | Thêm Huawei HarmonyOS breakpoint; Thêm MeshRoleChanged banner state; Đổi "React Native + Flutter" → "Flutter unified" trong §28 | Sprint 2 |
| `Introduction.md` | Cập nhật platform matrix: Huawei HarmonyOS (Beta); Clarify Super Node handover policy | Sprint 2 |
| `Function.md` | Thêm Mesh Graceful Handover user flow; Thêm Huawei notification flow | Sprint 2 |
| `BusinessPlan.md` | Thêm Huawei AppGallery distribution strategy §4.4; Market sizing cho Huawei segment | Sprint 3 |
| `Web_Marketplace.md` | Thêm Huawei AOT bundle rule tương tự iOS | Sprint 3 |
=========================================================================

# 🏗️ Lớp 2 — Xung đột Packaging, Build Pipeline & OS Integration

Đây là **lớp xung đột hoàn toàn mới**, khác biệt với lớp runtime đã phân tích. Các vấn đề ở đây xảy ra tại thời điểm **build, sign, package và deploy** — không phải lúc runtime.

---

## 🔴 P1 — Glassmorphism backdrop-filter: WebView2 Windows bể trên GPU cũ

**Vấn đề gốc rễ:** `Design.md` định nghĩa hiệu ứng Glass bắt buộc với `backdrop-filter: blur(16-24px)`. WebView2 trên Windows dùng Chromium rendering engine, nhưng khi GPU driver cũ hoặc là Integrated Graphics (Intel UHD 620 — rất phổ biến trong môi trường enterprise laptop), Chromium **tự động disable hardware compositing** → `backdrop-filter` bị software-render hoặc skip hoàn toàn → UI trông như flat design không có Glass.

**Tại sao đây là khẩn cấp:** Glassmorphism là visual identity cốt lõi của TeraChat. Nếu 40% laptop enterprise Windows bị flat UI do driver cũ, đây là vấn đề perception nghiêm trọng khi demo với khách hàng Gov/Banking.

**3 giải pháp, ưu nhược điểm rõ ràng:**

**Giải pháp A — CSS Hardware Acceleration Force (khuyến nghị):**

```css
/* Thêm vào Design.md: GPU Acceleration Hint bắt buộc */
.glass-layer {
  /* Force GPU composite layer */
  transform: translateZ(0);
  will-change: backdrop-filter;
  
  /* Fallback stack nếu blur fail */
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  
  /* Graceful degradation: nếu GPU không support */
  background: rgba(255, 255, 255, 0.75); /* fallback opaque */
}

/* Feature detection tại Rust → IPC → UI */
/* Rust Core detect WebView2 GPU caps lúc init → emit GpuCapability(has_backdrop_filter: bool) */
/* UI nhận flag → render Glass hoặc Flat variant */
```

Ưu điểm: không đổi design system, chỉ thêm graceful fallback. Nhược điểm: Flat variant trông khác Glass variant — cần designer approve Flat spec.

**Giải pháp B — Tauri Custom Render Backend (tham khảo dài hạn):**
Tauri 2.x hỗ trợ switching WebView2 → Wry với accelerated compositing hints. Tuy nhiên đây là thay đổi phụ thuộc Tauri roadmap, không nên block release.

**Giải pháp C — MSIX with GPU policy (Enterprise MDM):**
Deploy MSIX package với `AppExecutionAlias` và MDM policy yêu cầu GPU driver version tối thiểu. Phù hợp với Gov/Enterprise MDM environment nhưng không scale cho consumer.

**Cập nhật `Design.md`:** Thêm section `§GPU Capability Fallback Matrix` — định nghĩa rõ Glass variant và Flat variant cho mỗi tier GPU capability.

---

## 🔴 P2 — macOS Hardened Runtime xung đột với wasmtime JIT + memfd

**Vấn đề gốc rễ:** Để distribute qua macOS, app **bắt buộc** phải Notarized. Notarization bắt buộc **Hardened Runtime**. Hardened Runtime mặc định chặn 3 thứ mà TeraChat đang dùng:

| Capability bị chặn | TeraChat cần | Entitlement cần xin |
|---|---|---|
| JIT compilation | `wasmtime` JIT (Cranelift) | `com.apple.security.cs.allow-jit` |
| Unsigned dylib | CoreML `.dylib` plugins | `com.apple.security.cs.disable-library-validation` |
| Apple Events from 3rd party | Automation flows | `com.apple.security.automation.apple-events` |

**Tại sao nguy hiểm:** `allow-jit` entitlement **mở lại W^X** cho toàn bộ process — không chỉ cho wasmtime. Nếu có WASM Sandbox Escape lúc runtime, JIT page của wasmtime có thể bị khai thác để execute arbitrary code trong cùng process space. Đây là contradiction trực tiếp với security model của TeraChat.

**Giải pháp tối ưu — Process Isolation cho JIT (Khuyến nghị mạnh):**

Tách wasmtime JIT ra một **separate hardened child process** riêng. Process cha (Tauri UI + Rust Core) không có `allow-jit`. Chỉ process con `terachat-wasm-worker` có entitlement này:

```
TeraChat.app/
├── Contents/
│   ├── MacOS/
│   │   ├── terachat          ← Main process, NO allow-jit
│   │   └── terachat-wasm-worker  ← Child process, allow-jit only
│   └── Info.plist
```

Communication giữa hai process qua XPC Service (Apple-blessed IPC) với Mach port. Nếu WASM worker bị exploit, attacker chỉ có process con với restricted capabilities — không leo thang được lên Main process có Keychain access.

**Cập nhật `Feature_Spec.md` §6.3 macOS:**

```
macOS Entitlement Matrix:
- Main process: com.apple.security.app-sandbox=true, NO allow-jit
- terachat-wasm-worker (XPC Service):
    com.apple.security.cs.allow-jit=true
    com.apple.security.cs.disable-library-validation=true  
    com.apple.security.network.client=true (cho egress daemon)
- NSE Extension: com.apple.security.app-sandbox=true, NO network
```

---

## 🔴 P3 — Linux: Flatpak Sandbox xung đột với memfd_create + seccomp-bpf

**Vấn đề gốc rễ:** Không có file nào trong 7 tài liệu định nghĩa **Linux distribution format**. Đây là gap hoàn toàn. Các lựa chọn đều có conflict:

**So sánh 3 format:**

| Format | memfd_create | seccomp-bpf custom filter | Auto-update | Gov Enterprise |
|---|---|---|---|---|
| **AppImage** | ✅ OK | ✅ OK | ❌ Cần bake in | ⚠️ Không có signature check |
| **Flatpak** | 🔴 Blocked by bubblewrap | 🔴 Flatpak có seccomp riêng, filter tùy chỉnh bị chặn | ✅ Flatpak hub | ⚠️ Flatpak runtime layer |
| **Debian .deb / RPM** | ✅ OK | ✅ OK | ⚠️ Cần apt repo | ✅ GPG signed, enterprise-ready |

**Khuyến nghị — Combo: `.deb`/`.rpm` Native + AppImage fallback:**

```
Tier 1 (Enterprise/Gov): Signed .deb và .rpm packages
  - GPG signed bởi TeraChat Release Key
  - Tương thích: Ubuntu 20.04+, RHEL 8+, Debian 11+
  - Auto-update qua apt/dnf repo
  - systemd service install tự động
  - KHÔNG có Flatpak bubblewrap conflict

Tier 2 (Other distros): AppImage
  - Portable, self-contained
  - AppImage signature via appimagetool --sign
  - User-space update qua AppImageUpdate
  - Chạy được trên bất kỳ Linux x86_64/ARM64 có glibc 2.31+
```

**Cập nhật `Feature_Spec.md` §6.3 Linux:** Thêm section `Linux Packaging Strategy` với 2-tier approach trên, định nghĩa rõ syscall whitelist cho seccomp-bpf filter của TeraChat không conflict với distribution sandbox.

---

## 🟡 P4 — Windows ARM64: Build Target thiếu

**Tác động thực tế:** Surface Pro X, Qualcomm Snapdragon laptops (Copilot+ PCs 2024-2025) chiếm thị phần ngày càng lớn trong enterprise. Rust cross-compile sang `aarch64-pc-windows-msvc` cần MSVC ARM64 toolchain riêng — không tự động từ x64 toolchain. WebView2 ARM64 version tồn tại nhưng có một số quirk với SharedArrayBuffer.

**Giải pháp:** Thêm `aarch64-pc-windows-msvc` vào `Cargo.toml` build matrix. Test SAB behavior trên ARM64 WebView2 trước release.

---

## 🟡 P5 — iOS Keychain Group: NSE + Share Extension shared access

**Vấn đề bảo mật packaging:** Khi TeraChat add Share Extension (để share file vào TeraChat từ Files app), Extension này phải join cùng App Group Keychain với NSE để hoạt động. Nhưng Share Extension không yêu cầu biometric authentication — người dùng chỉ tap "Share" là extension chạy. Extension có thể đọc `Push_Key` từ Shared Keychain mà không cần FaceID/TouchID.

**Giải pháp — Keychain Access Group Segmentation:**

```
App Group: group.com.terachat
├── Keychain item: push_key_<chat_id>     → accessible by: NSE only
│   (kSecAttrAccessGroup = "group.com.terachat.nse")
├── Keychain item: device_identity_key    → accessible by: Main App only  
│   (kSecAttrAccessGroup = "group.com.terachat.main")
└── Keychain item: share_extension_token  → accessible by: Share Extension
    (kSecAttrAccessGroup = "group.com.terachat.share")
```

Phân tách Access Group bằng suffix — Push_Key chỉ có NSE access group, Share Extension không có trong provision. Cần cập nhật `Feature_Spec.md` §7.5 Push Key Storage.

---

## 🟡 P6 — Android 14+ Restricted Background: FCM throttling

**Vấn đề thực tế:** Android 14 (API 34) tăng cường `SCHEDULE_EXACT_ALARM` restrictions và battery bucket penalties. App bị xếp vào "Restricted" bucket (sau 3+ ngày không dùng) → FCM Data Message wakeup bị throttle tới 10 lần/giờ max. E2EE push notification trong enterprise group chat có thể delay 5-15 phút trong worst case.

**Giải pháp — Foreground Service Hybrid + Priority FCM:**

```kotlin
// Android: High-priority FCM message (bypass throttle nhưng cần permission)
// Trong Firebase console: message priority = "high"
// Trong AndroidManifest.xml:
<uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>

// Companion Device Manager đăng ký để bypass Doze
val cdm = getSystemService(CompanionDeviceManager::class.java)
// Request REQUEST_COMPANION_RUN_IN_BACKGROUND
```

Kết hợp với FCM `high` priority message cho chat notifications (đã có trong `Core_Spec.md` nhưng chưa có Android 14 specific handling) và Companion Device Manager registration để bypass battery restriction.

---

## 🟡 P7 — CI/CD Code Signing Pipeline: Chưa có strategy

**Gap hoàn toàn trong tài liệu.** Đây là nợ kỹ thuật vận hành quan trọng nhất — không có signing strategy thì không thể distribute. Mỗi platform cần quy trình khác nhau:

**Unified Signing Strategy:**

```yaml
# .github/workflows/release.yml (skeleton cần thêm vào BusinessPlan.md)

iOS Signing:
  - Apple Distribution Certificate (stored in GitHub Secrets)
  - Provisioning Profile per target (Main App, NSE, Share Ext)
  - fastlane match để sync certificates
  - Notarize via Apple Transporter

macOS Signing:
  - Developer ID Application Certificate
  - Notarization via notarytool (Xcode 13+)
  - Staple ticket vào .dmg

Windows Signing:
  - EV Code Signing Certificate (DigiCert/Sectigo)
  - Sign với signtool.exe
  - SmartScreen reputation: cần tích lũy 30+ ngày clean submissions
  - MSIX packaging cho Store distribution

Android Signing:
  - Keystore file (stored encrypted in GitHub Secrets)
  - Google Play App Signing (delegate signing to Google)
  - APK + AAB dual signing

Linux Signing:
  - GPG key cho .deb/.rpm packages
  - Cosign cho AppImage
  - Public key published tại packages.terachat.com/gpg.key
```

**Lưu ý quan trọng:** Windows EV Code Signing Certificate hiện chỉ available trên **hardware token** (USB). Trong CI/CD cần Cloud HSM provider (DigiCert KeyLocker hoặc SSL.com eSigner) để sign trong pipeline mà không cần người giữ token. Chi phí ~$500/năm nhưng bắt buộc cho SmartScreen không cảnh báo trên Windows.

---

## 🟢 P8 — Linux Wayland: Protected Clipboard Bridge

`Feature_Spec.md §9.6` định nghĩa Protected Clipboard Bridge nhưng implementation hint dùng `xclip`/`xsel` — không hoạt động trên Wayland native (chỉ hoạt động qua XWayland compatibility layer, có thể bị disable trong secure environments).

**Fix đơn giản:** Detect display server lúc runtime và chọn clipboard backend:

```rust
// Detect Wayland vs X11
let clipboard_backend = if std::env::var("WAYLAND_DISPLAY").is_ok() {
    ClipboardBackend::WlClipboard  // wl-clipboard
} else {
    ClipboardBackend::Xclip        // xclip/xsel
};
```

---

## Tổng hợp Combo Giải pháp Packaging

**Combo X — Unified Build Matrix** (ưu tiên nhất):

Tạo một `build-matrix.md` hoặc section trong `Feature_Spec.md §6` định nghĩa rõ:

```
Target triples bắt buộc:
├── x86_64-apple-darwin        → macOS Intel
├── aarch64-apple-darwin       → macOS Apple Silicon  
├── x86_64-pc-windows-msvc     → Windows x64
├── aarch64-pc-windows-msvc    → Windows ARM64 (thêm mới)
├── x86_64-unknown-linux-gnu   → Linux x64 (.deb/.rpm/AppImage)
├── aarch64-unknown-linux-gnu  → Linux ARM64 (server deployment)
├── aarch64-apple-ios          → iOS
└── aarch64-linux-android      → Android
```

**Combo Y — OS Capability Contract** (bắt buộc cho macOS/iOS):
Thêm `entitlements-matrix.md` vào docs/ định nghĩa mỗi process/extension trên mỗi platform có entitlement gì — không được phép có entitlement thừa (Principle of Least Privilege áp dụng cho OS permissions).

**Combo Z — Adaptive Renderer** (cho Glassmorphism stability):
`Design.md` cần thêm `§GPU Capability Tiers`:

- Tier A (GPU Hardware Compositing): Full Glassmorphism
- Tier B (Software Compositing): Frosted Glass lite (blur 8px, opacity 0.85)
- Tier C (No Compositing): Flat Solid với border accent — vẫn nhận diện được TeraChat nhưng không phụ thuộc GPU

**Combo W — Signing Pipeline**:
Thêm `signing-pipeline.md` vào `BusinessPlan.md §3.3` hoặc một file ops riêng, định nghĩa signing ceremony, certificate rotation schedule, và EV token handling strategy.

---

## File nào cần cập nhật — Lớp Packaging

| File | Nội dung cần thêm | Ưu tiên |
|---|---|---|
| `Feature_Spec.md` | §6.3 macOS: Entitlement Matrix + XPC Worker pattern; §6.3 Linux: 2-tier packaging (.deb/.rpm + AppImage); §6.3 Windows ARM64 build target; §7.5 iOS Keychain Access Group segmentation; §9.6 Wayland clipboard backend detection | 🔴 Sprint 1 |
| `Design.md` | §GPU Capability Fallback Matrix — Glass/FrostedLite/Flat 3 tiers; Breakpoint cho Windows ARM64 | 🔴 Sprint 1 |
| `Core_Spec.md` | §Android 14 Battery Bucket Handling — FCM high priority + Companion Device Manager; §macOS XPC Worker security boundary | 🟡 Sprint 2 |
| `BusinessPlan.md` | §3.3 Thêm Signing Pipeline & Certificate Management strategy; §EV Code Signing cost ($500/yr) vào COGS | 🟡 Sprint 2 |
| `Introduction.md` | Cập nhật supported platforms: thêm Windows ARM64, Linux ARM64; cập nhật Linux distribution note (deb/rpm/AppImage) | 🟡 Sprint 2 |
| `Web_Marketplace.md` | Thêm Linux package signing via GPG/Cosign vào §1.2 Ed25519 Signing section | 🟢 Sprint 3 |
| `Function.md` | Thêm user flow cho GPU Tier C (Flat mode) — UI phải vẫn functional khi không có Glassmorphism | 🟢 Sprint 3 |

---
=======================================================================

# 🧠 Lớp 3 — Xung đột Giao thức, Logic Nghiệp vụ & Kiến trúc Ẩn

Đây là lớp nguy hiểm nhất vì các mâu thuẫn **không gây lỗi runtime** — chúng gây ra **cam kết sai với khách hàng**, **lỗ hổng logic không thể audit**, và **nợ kỹ thuật không thể refactor dễ dàng**.

---

## 🔴 Q1 — CRDT Mobile-Only "Causal Freeze": SOS tê liệt không có Dictator

**Phân tích gốc rễ:** `Feature_Spec.md` thừa nhận bài toán nhưng giải pháp "Optimistic Append-Only" chỉ là một note ngắn, không có protocol specification đầy đủ. Scenario thực tế: 20 nhân viên chính phủ dùng iPhone trong tòa nhà bị cô lập — không có Laptop, không có Android Super Node. BLAKE3 Tie-Breaker Hash Election cần ít nhất 1 node đủ năng lực làm Dictator. Tất cả đều là Leaf Node iOS → Election loop không kết thúc → không ai gửi tin nhắn được.

**Giải pháp — Emergency Mobile Dictator Protocol (EMDP):**

```rust
// core/src/mesh/emergency_dictator.rs

pub enum DictatorElectionMode {
    /// Chế độ bình thường: ưu tiên Desktop/Android Super Node
    Normal,
    /// Chế độ khẩn cấp: khi toàn bộ peer là iOS Leaf Node
    EmergencyMobileOnly,
}

impl MeshDictatorElection {
    pub fn elect(&self, peers: &[PeerInfo]) -> ElectionResult {
        let has_super_node = peers.iter()
            .any(|p| p.platform != Platform::iOS && p.capabilities.contains(SUPER_NODE));

        if has_super_node {
            // Đường bình thường: BLAKE3 Hash Election
            return self.blake3_election(peers);
        }

        // EMDP: Emergency Mobile Dictator Protocol
        // Chọn iOS node có battery cao nhất + BLE signal mạnh nhất
        // làm "Tactical Relay" — vai trò nhẹ hơn Super Node
        let tactical_relay = peers.iter()
            .max_by_key(|p| {
                let battery_score = p.battery_pct as u32 * 100;
                let signal_score = p.ble_rssi.saturating_add(100) as u32; // normalize -100..0 → 0..100
                battery_score + signal_score
            });

        if let Some(relay) = tactical_relay {
            ElectionResult::TacticalRelay {
                node_id: relay.id,
                // Chức năng hạn chế: chỉ store-and-forward text
                // KHÔNG làm full DAG merge (quá nặng cho iOS)
                mode: TacticalRelayMode::TextOnlyForward,
                ttl_minutes: 60, // Auto-expire sau 60 phút để tránh pin drain
            }
        } else {
            // Solo mode: chỉ 1 thiết bị, không cần election
            ElectionResult::SoloAppendOnly
        }
    }
}
```

**Semantic quan trọng:** Tactical Relay ≠ Super Node. iOS làm Tactical Relay chỉ forward text message theo mô hình `Append-Only CRDT` đơn giản nhất — không merge DAG nhánh, không xử lý conflict, không rotate MLS Epoch. Đây là **SOS mode**: đảm bảo tin nhắn đến nơi, không đảm bảo consistency cao. Khi Desktop/Server reconnect, toàn bộ merge thật sự được thực hiện lúc đó.

**Cập nhật `Core_Spec.md` §5.12:** Thêm EMDP spec với 3 trạng thái `Normal → EmergencyMobileOnly → SoloAppendOnly` và transition conditions.

**Cập nhật `Introduction.md`:** Làm rõ "Offline Survival" hoạt động ở 3 cấp độ, cấp 3 (Mobile-Only) chỉ đảm bảo text SOS, không đảm bảo full collaboration.

---

## 🔴 Q2 — Open-Core vs License Entanglement: Contradiction kiến trúc

**Phân tích gốc rễ:** Đây là mâu thuẫn thiết kế nghiêm trọng nhất về mặt business model. `BusinessPlan.md §4.2` nói Core Cryptography là **mã nguồn mở** để Gov/Bank tự compile kiểm chứng. Nhưng `Core_Spec.md §9.5` nói License validation được **Cryptographic Entanglement** vào `DeviceIdentityKey + License_Token_Signature + Current_Epoch = Master_Unlock_Key`. Nếu Core thực sự mở, bất kỳ ai cũng có thể compile lại và bỏ entanglement → crack license.

**3 giải pháp, trade-off rõ ràng:**

**Giải pháp A — License Boundary Tách hoàn toàn khỏi Crypto Core (Khuyến nghị):**

Tách License validation ra một **separate closed-source module** (`terachat-license-guard`) được compile as a `.so`/`.dll` và loaded at runtime. Core Crypto hoàn toàn sạch, không chứa license logic:

```
Mã nguồn mở (AGPLv3):
└── terachat-core/          ← Crypto, CRDT, MLS, Mesh
    ├── src/crypto/
    ├── src/mesh/
    └── src/crdt/

Mã nguồn đóng (BSL):
└── terachat-license-guard/ ← License validation
    ├── src/entanglement.rs  ← KDF(DeviceKey + LicenseToken)
    └── src/quota.rs         ← Seat counting
```

`terachat-core` tại startup gọi FFI vào `terachat-license-guard` để lấy `Feature_Flags`. Nếu không có `license-guard.so`, core chạy ở Community mode (unlimited users, watermark). Enterprise features unlock khi guard trả về valid token.

**Ưu điểm:** Gov/Bank compile và audit Core thoải mái. License guard là black box riêng, không trong scope của open-source audit. **Nhược điểm:** Attacker vẫn có thể patch `license-guard.so` call trong Core binary (không phải mã nguồn). Cần O-LLVM trên call site trong Core.

**Giải pháp B — Server-Side License Attestation:**
License không validate ở client mà validate ở server — client chỉ nhận Feature Token JWT từ server. Attacker không thể crack cái gì ở client vì không có logic ở đó. Nhược điểm: Air-gapped deployment không hoạt động.

**Giải pháp C — Trusted Execution Environment (TEE) cho License:**
License guard chạy trong Intel SGX Enclave — code không thể extract hay patch dù attacker có full root access. Đây là giải pháp mạnh nhất nhưng phức tạp nhất.

**Khuyến nghị thực tế:** Combo A + B — Client có license guard tách biệt (A) cho Air-gapped. Server attestation (B) cho Cloud deployment. TEE (C) cho Elite tier.

**Cập nhật `BusinessPlan.md §4.2` và `Core_Spec.md §9.5`:** Phân tách rõ ranh giới Open/Closed, định nghĩa License Guard là module riêng không thuộc Core Crypto scope.

---

## 🔴 Q3 — Shadow DAG loại khỏi Mesh + Không có Offline Conflict Resolution

**Phân tích gốc rễ:** `Core_Spec.md §5.19` phát biểu rõ ràng: *"Giao thức Shadow DAG bị loại bỏ hoàn toàn khỏi bộ định tuyến P2P Mesh."* Nhưng `Function.md` cho phép người dùng thực hiện `Local Edit` khi offline. Khi hai người dùng cùng edit một document offline và reconnect — không có giao thức nào xử lý conflict này ngoài CRDT LWW (Last-Write-Wins) im lặng.

Trong enterprise context, LWW im lặng trên document hợp đồng là **thảm họa pháp lý** — một bên ký hợp đồng có thể bị ghi đè mà không ai biết.

**Giải pháp — Tiered Conflict Resolution Protocol:**

```
Tier 1 (Online): Shadow DAG đầy đủ → User nhìn thấy conflict, chọn merge
Tier 2 (Mesh P2P): Lightweight Conflict Marker → đánh dấu "conflict pending"
                   khi có Desktop Super Node làm mediator  
Tier 3 (Solo offline): Optimistic Append → ghi nhật ký edit, LWW khi sync
                       với WARNING rõ ràng: "Bản này có thể bị ghi đè khi đồng bộ"
```

Ở Tier 2 và 3, khi reconnect và phát hiện conflict, **bắt buộc hiển thị Conflict Resolution UI** trước khi cho phép ghi. Không bao giờ silent LWW trên document có `content_type = CONTRACT | POLICY | APPROVAL`.

**Cập nhật `Core_Spec.md §5.19`:** Thay "loại bỏ hoàn toàn" bằng "Shadow DAG full protocol chỉ chạy online. Mesh mode dùng Conflict Marker Protocol nhẹ." Cập nhật `Function.md`: thêm user flow "Conflict Resolution khi sync từ offline".

---

## 🟡 Q4 — Retention Policy vs Zero-Retention: Mâu thuẫn cam kết với khách hàng

**Phân tích:** `Introduction.md` và marketing cam kết **Zero-Retention** — server không giữ dữ liệu. Nhưng `Feature_Spec.md §5.10.1` mô tả `cold_state.db` được đẩy lên VPS khi hot DAG evict sau 7 ngày. Đây là server-side retention thực sự, không phải Zero-Retention.

**Giải pháp — Tiered Retention Policy với terminology rõ ràng:**

| Tier | Mô tả | Đối tượng |
|---|---|---|
| **Zero Server Retention** | Server không giữ plaintext. Server giữ ciphertext mù (cold_state.db encrypted). Server không thể đọc. | Tất cả tier |
| **Client-Controlled Retention** | Enterprise tự quyết định giữ bao lâu bằng cách configure VPS cold storage TTL | Enterprise/Gov |
| **Compliance Retention** | 7 năm audit log, encrypted at rest, key giữ ở client | Banking/Gov |

**Sửa terminology trong tài liệu:** Thay "Zero-Retention" bằng "Zero-Knowledge Retention" — server giữ encrypted data nhưng không có key để đọc. Đây là cam kết chính xác hơn và vẫn là selling point mạnh mẽ.

**Cập nhật `Introduction.md §1.1`** và **`BusinessPlan.md §2.3`**: Clarify "Zero-Knowledge Retention" và thêm Compliance Retention tier vào pricing model.

---

## 🟡 Q5 — FCP vs Blind Relay: Cần clarify threat model

**Phân tích:** FCP (Full Context Passthrough) khi Admin ký Risk Acceptance thực ra là **intentional break** của Zero-Knowledge model — doanh nghiệp chấp nhận rủi ro để đổi lấy AI capability đầy đủ hơn. Đây là thiết kế đúng về mặt business. Vấn đề là tài liệu **không nói rõ** điều này với khách hàng.

**Giải pháp — Explicit Trust Boundary Declaration:**

Trong `Introduction.md` và `Function.md`, thêm section "Trust Boundary Matrix":

```
Default Mode (Zero-Knowledge):
  Server = Blind Relay. AI Agent = nhận masked context.
  Cam kết: Server không đọc được nội dung.

FCP Mode (Admin-Opt-In):
  Server vẫn Blind Relay. AI Agent = nhận plaintext context.
  Cam kết bị giới hạn: TLS bảo vệ transit, nhưng AI endpoint thấy plaintext.
  Yêu cầu: YubiKey + typed consent + audit log signed.
  Phù hợp khi: AI endpoint là on-premise model do doanh nghiệp tự host.
```

---

## 🟡 Q6 — Offline TTL 24h mâu thuẫn với Survival Mesh promise

**Phân tích:** `Core_Spec.md §Offline PKI Defense` ghi rõ "App tự đóng băng Session nếu mất Server > TTL (24h)". Nhưng use case chính của Survival Mesh là thiên tai/gián đoạn kéo dài nhiều ngày. TTL 24h đóng băng session sau 1 ngày = vô hiệu hóa tính năng quan trọng nhất của sản phẩm.

**Giải pháp — Dynamic TTL based on deployment profile:**

```rust
pub enum OfflineTTLProfile {
    /// Consumer app: 24h — cân bằng security vs UX
    Consumer { ttl_hours: 24 },
    /// Enterprise: 7 ngày — doanh nghiệp tự quyết
    Enterprise { ttl_hours: u32 },
    /// Gov/Military: 30 ngày — thiên tai, chiến tranh scenario
    GovMilitary { ttl_hours: 720 },
    /// Air-gapped: vô thời hạn — chỉ hết hạn khi Admin revoke
    AirGapped { revocation_only: bool },
}
```

TTL được cấu hình bởi Admin trong Admin Console và baked vào License. Không phải hardcode 24h cho tất cả.

**Cập nhật `Core_Spec.md §Offline PKI`** và **`Feature_Spec.md §9.5`**: Thay hardcode 24h bằng `OfflineTTLProfile` configurable. Thêm vào `BusinessPlan.md`: GovMilitary tier có TTL 30 ngày là premium feature.

---

## 🟡 Q7 — Web_Marketplace.md thiếu Host Function ABI Versioning

**Phân tích:** Khi TeraChat Core v2.0 release với breaking change trong Host Function API (ví dụ: đổi signature của `terachat_send_message`), tất cả `.tapp` cũ compiled against v1.0 ABI sẽ crash ngay khi load. Không có semver contract, không có deprecation window, không có compatibility matrix trong `Web_Marketplace.md`.

**Giải pháp — Host Function ABI Contract:**

```json
// manifest.json của mỗi .tapp bắt buộc có:
{
  "host_api_version": "1.3.0",
  "min_host_api_version": "1.0.0",
  "max_host_api_version": "2.0.0"
}
```

TeraChat Core publish **Host API Changelog** theo semver. Breaking changes chỉ được phép trong major version. Minor version chỉ additive. `.tapp` load bị reject nếu `host_api_version` nằm ngoài range Core hiện tại đang support.

**Cập nhật `Web_Marketplace.md`**: Thêm `§Host API Versioning Contract` và `§Publisher Migration Guide`.

---

## 🟢 Q8 — BusinessPlan.md thiếu TCO Calculator cho Enterprise On-Premise

**Phân tích:** `BusinessPlan.md` mô tả BYOS model nhưng Sales team không có công cụ tính chi phí thực sự cho khách hàng. Enterprise IT cần biết: cần bao nhiêu storage cho 1000 user × 2 năm? Backup strategy như thế nào? DR RTO/RPO là bao nhiêu?

**Giải pháp:** Thêm `§TCO Reference Architecture` vào `BusinessPlan.md` với sizing guidelines:

```
1,000 users × 1 năm ≈ 500GB cold storage (BYOS)
10,000 users × 1 năm ≈ 5TB cold storage
VPS minimum spec: 4 vCPU, 8GB RAM, 100GB SSD (Control Plane only)
DR: Active-Passive với PostgreSQL streaming replication, RTO < 15 phút
```

---

## Tổng hợp toàn bộ 3 lớp — Ma trận file cần cập nhật

Sau 3 vòng phân tích, đây là bản tổng hợp đầy đủ nhất:

| File | Lớp 1 (Runtime) | Lớp 2 (Packaging) | Lớp 3 (Protocol/Business) | Tổng thay đổi |
|---|---|---|---|---|
| `Core_Spec.md` | Huawei HMS, Token Protocol, iOS mlock | macOS Entitlement Matrix, Android 14 | EMDP, Tiered TTL, License Boundary | 🔴 Nhiều nhất |
| `Feature_Spec.md` | Flutter unified, WASM Parity, C6 Push Key | Linux packaging, iOS Keychain segmentation, Wayland clipboard | Tiered Conflict Resolution, ABI Contract | 🔴 Nhiều nhất |
| `Design.md` | Huawei breakpoint, MeshRole banner | GPU Capability Fallback Matrix | Conflict Resolution UI flow | 🟡 Trung bình |
| `Introduction.md` | Platform matrix + Huawei | Windows ARM64, Linux distro note | Zero-Knowledge Retention clarify, Offline TTL tiers, Survival mode levels | 🟡 Trung bình |
| `BusinessPlan.md` | Huawei AppGallery strategy | EV Code Signing cost, Signing Pipeline | License Boundary separation, TCO Calculator, GovMilitary TTL tier | 🟡 Trung bình |
| `Function.md` | Mesh Graceful Handover | Flat GPU UI flow | Offline Conflict Resolution flow, FCP Trust Boundary declaration | 🟢 Ít nhất |
| `Web_Marketplace.md` | Huawei AOT bundle rule | Linux GPG/Cosign signing | Host Function ABI Versioning Contract | 🟢 Ít nhất |
=========================================================================

## Giai đoạn 1 — Thương mại: Tạo License Token tại HSM

Sau khi hợp đồng được ký và thanh toán xác nhận, Sales Portal của TeraChat tổng hợp thông tin đơn hàng và gửi yêu cầu ký xuống **HSM FIPS 140-3 Level 4** offline — chip vật lý không bao giờ kết nối internet. HSM sinh ra một **License JWT** với cấu trúc:

```json
{
  "tenant_id": "acme-corp-vn",
  "domain": "acme.terachat.io",
  "max_seats": 500,
  "tier": "enterprise",
  "valid_from": "2026-03-15T00:00:00Z",
  "valid_until": "2027-03-15T00:00:00Z",
  "max_protocol_version": "2.0",
  "offline_ttl_hours": 720,
  "air_gapped": false,
  "features": ["mesh_survival", "ai_dlp", "federation", "compliance_audit"]
}
```

Chữ ký **Ed25519** từ HSM Private Key — key này không bao giờ rời chip. Không có phần mềm nào ở TeraChat HQ có thể đọc raw key. Điều này có nghĩa là kể cả nhân viên TeraChat bị mua chuộc cũng không thể tự tạo License giả.

---

## Giai đoạn 2 — Phân phối theo kênh

**Kênh Online (Cloud/VPS):** JWT được gửi qua email bảo mật. Admin chạy một lệnh duy nhất:

```bash
curl -sL https://install.terachat.com/install.sh | \
  cosign verify-blob --key terachat-root.pub - && \
  sudo bash - --token="eyJhbGciOiJFZERTQS..."
```

Lệnh tự động verify chữ ký script (chống supply chain attack), sau đó truyền JWT vào installer.

**Kênh Air-Gapped (Quân sự/Gov):** JWT được ghi lên USB được mã hóa AES-256 và giao vật lý cho CISO của khách hàng. Không có internet, không có phone-home, không có telemetry. Phù hợp môi trường SCIF (Sensitive Compartmented Information Facility).

---

## Giai đoạn 3 — KMS Bootstrap Ritual: Lõi Rust chặn mọi thứ cho đến khi an toàn

Đây là giai đoạn quan trọng nhất và thường bị các sản phẩm khác bỏ qua. Rust Core **từ chối tạo bất kỳ database nào** cho đến khi Admin hoàn thành 4 bước:

**Bước 1 — Verify Token:** Lõi Rust kiểm tra chữ ký JWT đối chiếu với TeraChat HSM Root CA Public Key đã được bundle sẵn trong binary. Không cần gọi về server TeraChat. Nếu JWT sai chữ ký hoặc `tenant_id` không khớp `domain` → từ chối ngay.

**Bước 2 — Sinh Master Key:** Rust tạo `terachat_master_<domain>.terakey` — file bọc Master Key bằng Argon2id từ Admin password (tuning 0.5s CPU để chống GPU brute-force). File này là "chìa khóa két" — mất file này = mất toàn bộ hệ thống.

**Bước 3 — Shamir Secret Sharing:** Master Key bị chia thành 5 mảnh theo thuật toán Shamir, cần 3 mảnh để khôi phục. 5 mảnh được xuất ra 5 YubiKey/Smartcard của C-Level (CEO, CISO, CFO, COO, CTO). Không một cá nhân nào đơn lẻ có thể khôi phục hệ thống.

**Bước 4 — Xác nhận backup:** Admin báo cáo đã lưu thành công → Rust ghi nhận vào audit log có chữ ký Ed25519 → mở khóa DB → hệ thống khởi động lần đầu.

---

## Giai đoạn 4 — Cryptographic Entanglement: License không thể tách khỏi phần cứng

Đây là giải pháp cho câu hỏi phản biện từ phiên trước — **làm thế nào để License validation dùng DeviceIdentityKey mà không vi phạm Write-Only FFI**. Câu trả lời: License validation không xảy ra ở tầng UI hay License Guard module — nó xảy ra **bên trong Rust Core** theo mô hình Write-Only:

```rust
// Rust Core — KHÔNG export ra ngoài, không có FFI endpoint nào expose điều này
fn derive_master_unlock_key(
    license_token: &LicenseToken,
    epoch: u64,
) -> Result<MasterUnlockKey, LicenseError> {
    // DeviceIdentityKey chỉ được dùng làm INPUT cho KDF
    // Không bao giờ return ra ngoài — đây là Write-Only
    let device_key_material = secure_enclave::sign_derive(
        b"license-kdf-v1",
        epoch.to_le_bytes().as_ref(),
    )?;  // ← Secure Enclave ký/derive, private key không rời chip

    let kdf_input = [
        device_key_material.as_ref(),          // từ Secure Enclave
        license_token.signature.as_ref(),       // từ HSM JWT
        &epoch.to_le_bytes(),                   // từ TPM Monotonic Counter
    ].concat();

    let master_key = hkdf_sha256(&kdf_input, b"terachat-master-v1");

    // master_key được dùng để mở DB — nếu license sai → key sai → DB = rác
    // Không return device_key_material. Không export master_key qua FFI.
    Ok(MasterUnlockKey(master_key))
}
```

Điểm mấu chốt: `DeviceIdentityKey` **không bao giờ ra khỏi Secure Enclave dưới dạng raw bytes**. Secure Enclave chỉ thực hiện phép tính derive/sign rồi trả về output — đây là pattern chuẩn của Apple CryptoKit và không vi phạm Write-Only mandate. License Guard module chỉ trả về `FeatureFlags` (một struct đơn giản) — không có raw key nào đi qua FFI.

---

## Giai đoạn 5 — Runtime Validation: Kiểm tra im lặng mỗi 24h

Admin Console và Lõi Rust chạy **License Heartbeat** theo lịch mà user không thấy, gồm 4 kiểm tra theo thứ tự:

| Kiểm tra | Cơ chế | Fail → |
|---|---|---|
| JWT signature | Ed25519 vs bundled Root CA | Immediate lock |
| Thời hạn | `valid_until` > Monotonic Counter TPM | Immediate lock |
| Seat count | `active_device_keys` ≤ `max_seats` | Block new enrollment |
| Revocation | CRL endpoint (online only) hoặc skip (air-gapped) | Immediate lock |

Tất cả validate locally — không cần gọi về server TeraChat. Air-Gapped deployment hoạt động hoàn toàn offline.

---

## Giai đoạn 6 — Graceful Degradation: Hết hạn theo 4 cấp độ

Thiết kế này đến từ bài học kinh doanh: enterprise customer **không thể chấp nhận** hệ thống chết đột ngột vì lý do billing. Đồng thời TeraChat cần đảm bảo doanh thu.

**T-30 ngày:** Banner vàng xuất hiện trong Admin Console mỗi lần đăng nhập. Email tự động gửi đến billing contact mỗi 7 ngày. Không ảnh hưởng gì đến hoạt động.

**T-0 (hết hạn):** Admin Console vẫn mở nhưng các tính năng sinh doanh thu bị khóa — không add user mới, AI module tắt, Azure AD Sync báo lỗi. Chat, Mesh và dữ liệu hiện có hoàn toàn bình thường. Đây là điểm quan trọng để tránh rủi ro pháp lý (khách hàng không bị gián đoạn giao tiếp khẩn cấp).

**T+90 ngày:** Lõi Rust từ chối bootstrap mới (nhưng không xóa data). Hệ thống đang chạy vẫn tiếp tục, chỉ không thể khởi động lại sau khi tắt máy.

**Gia hạn:** Admin nhận JWT mới → paste vào Admin Console → Rust verify → tất cả tính năng khôi phục trong vòng dưới 5 giây. Không restart, không re-install.

---

## Giai đoạn 7 — Renewal và License Transfer

**Gia hạn thông thường:** JWT mới qua email hoặc USB (air-gapped). Rust verify và update `valid_until` trong secure storage.

**Nâng tier** (từ Standard lên Enterprise): JWT mới với `max_seats` lớn hơn và `features` mở rộng. Áp dụng ngay lập tức.

**Chuyển domain** (M&A, đổi tên công ty): Cần ceremony đặc biệt — Admin phải ký xác nhận bằng YubiKey + TeraChat phát JWT mới với `tenant_id` và `domain` cập nhật. Không thể tự chuyển vì JWT cũ bị bound vào `tenant_id` cũ.

---

## Tổng kết bảo đảm kỹ thuật

| Mối đe dọa | Cơ chế ngăn chặn |
|---|---|
| Giả mạo License | Ed25519 HSM — không có Private Key → không ký được |
| Crack bằng patch binary | KDF cần DeviceIdentityKey từ Secure Enclave chip vật lý |
| Clock rollback để kéo dài hạn | TPM 2.0 Monotonic Counter — chỉ tăng, không giảm |
| Clone License sang nhiều server | HSM Decrementing Counter — giảm mỗi lần issue |
| Rò rỉ key qua License Guard FFI | DeviceIdentityKey không rời chip — chỉ làm KDF input |
| Mất internet (Air-Gapped) | Validate locally, không phone-home |

---
===============================================================

# 🔬 Lớp 4 — Xung đột Mạng, Data Integrity & Nợ kỹ thuật ẩn cuối

---

## 🔴 R1 — QUIC/eBPF Client-Side: Scope định nghĩa sai trong tài liệu

**Phân tích:** `Core_Spec.md` mô tả eBPF/XDP như một tính năng của client nhằm chống DDoS: *"eBPF/XDP program chạy tại tầng Kernel Linux... throughput filtering ~10Gbps trên single core"*. Đây là **nhầm lẫn scope nghiêm trọng**.

eBPF/XDP là công nghệ **server-side Linux kernel**. Trên client:

- iOS không có kernel module loading capability
- Android không cho user-space app inject eBPF filter
- Windows không có BPF equivalent cho user app
- macOS user-space app không có `CAP_NET_ADMIN`

Chỉ có Linux Desktop (và chỉ với elevated privileges) mới có thể dùng `SO_ATTACH_BPF` ở user space, và ngay cả đó thì `seccomp-bpf` (đã được đề cập đúng chỗ) khác với XDP.

**Giải pháp rõ ràng — Tách scope:**

```
Server-side (VPS/🗄️):
  eBPF/XDP anti-DDoS — ĐÚNG vị trí, giữ nguyên
  Rate limiting tại kernel level — hợp lệ

Client-side QUIC:
  iOS/Android: Dùng Network.framework QUIC (Apple/Google native)
  Desktop Linux: seccomp-bpf (đã đúng) — KHÔNG phải XDP
  Desktop Windows: Windows Filtering Platform (WFP) tương đương
  
Client-side chỉ hưởng lợi từ QUIC 0-RTT và Connection Migration,
KHÔNG implement eBPF/XDP filtering.
```

**Cập nhật `Core_Spec.md` §5.3 QUIC:** Di chuyển toàn bộ eBPF/XDP description vào section `☁️🗄️ Server Infrastructure`. Thêm note rõ: *"Client không implement eBPF/XDP. Client hưởng lợi từ server-side eBPF/XDP protection thông qua connection quality."*

---

## 🔴 R2 — iOS AWDL: Tắt ngầm không có warning khi Hotspot/CarPlay active

**Phân tích:** iOS tự động tắt AWDL (Apple Wireless Direct Link) khi người dùng bật Personal Hotspot hoặc kết nối CarPlay. Đây là Apple hardware limitation — Wi-Fi chip chỉ có 1 radio và phải chọn giữa AWDL và Hotspot. `Feature_Spec.md §5.21` thừa nhận "AWDL băng thông không ổn định" nhưng không định nghĩa detection + fallback protocol.

**Hệ quả thực tế:** Nhân viên đang dùng iOS Tier 2 voice call, bật Hotspot cho laptop đồng nghiệp → AWDL tắt ngầm → voice call drop → không hiểu lý do.

**Giải pháp — AWDL Status Monitor + Graceful Fallback:**

```swift
// iOS Swift layer — gửi qua FFI về Rust Core
import Network

class AWDLMonitor {
    private var pathMonitor = NWPathMonitor(requiredInterfaceType: .wifi)
    
    func startMonitoring(callback: @escaping (AWDLStatus) -> Void) {
        pathMonitor.pathUpdateHandler = { path in
            let awdlAvailable = path.availableInterfaces
                .contains(where: { $0.type == .wifi && $0.name.contains("awdl") })
            
            let hotspotActive = path.availableInterfaces
                .contains(where: { $0.name.contains("bridge") })
            
            if hotspotActive || !awdlAvailable {
                // Gọi Rust Core qua FFI để chuyển từ AWDL → BLE fallback
                callback(.unavailable(reason: hotspotActive ? .hotspot : .unavailable))
            }
        }
        pathMonitor.start(queue: .global())
    }
}
```

Khi `AWDLStatus = .unavailable`, Rust Core ngay lập tức:

1. Downgrade kênh từ Tier 2 → Tier 3 (BLE only)
2. Emit `UIEvent::TierChanged` với message: *"Hotspot đang bật — Mesh chuyển sang BLE. Voice tạm không khả dụng."*
3. Queue voice packets với TTL 30s chờ AWDL phục hồi
4. Nếu sau 30s AWDL không phục hồi → drop voice, thông báo user

**Cập nhật `Feature_Spec.md` §5.21:** Thêm `AWDLStatus Monitor` spec và iOS Tier 2 downgrade path.

---

## 🔴 R3 — WebRTC TURN Failover vs iOS Background Time Limit

**Phân tích:** `Core_Spec.md §5.11` mô tả TURN HA với "Keepalived Floating IP, failover 3 giây". Nhưng iOS có một ràng buộc nghiêm ngặt: khi app vào Background, iOS cho tối đa **30 giây** để hoàn thành network operations trước khi suspend. Nếu TURN failover xảy ra khi app đang background, 3 giây failover + thời gian SRTP renegotiate có thể vượt quá window iOS cho phép.

Tuy nhiên, iOS có ngoại lệ: VoIP apps sử dụng `PKPushRegistry` và `CallKit` được hưởng **extended background execution** cho voice calls. Vấn đề là tài liệu chưa định nghĩa TeraChat có integrate CallKit hay không.

**Giải pháp — CallKit Integration cho iOS Voice:**

```swift
// iOS: Sử dụng CallKit để iOS treat TeraChat calls như native calls
// → không bị background kill, không bị audio session interrupt

import CallKit

class TeraCallKitProvider: NSObject, CXProviderDelegate {
    let provider: CXProvider
    
    override init() {
        let config = CXProviderConfiguration()
        config.supportsVideo = true
        config.maximumCallGroups = 1
        config.maximumCallsPerCallGroup = 1
        config.supportedHandleTypes = [.generic]
        self.provider = CXProvider(configuration: config)
        super.init()
        provider.setDelegate(self, queue: nil)
    }
    
    // Khi TURN failover xảy ra → CallKit giữ audio session active
    // iOS không suspend WebRTC trong khi CallKit call đang active
    func reportCallStarted(callUUID: UUID) {
        let update = CXCallUpdate()
        update.hasVideo = true
        provider.reportNewIncomingCall(with: callUUID, update: update) { _ in }
    }
}
```

Ngoài ra, cần thêm **TURN preconnect strategy**: khi app chuyển sang Background trong khi call active, Rust Core proactively connect tới TURN server dự phòng trước (dual TURN connection) để failover xảy ra ngay lập tức, không cần 3 giây.

**Cập nhật `Core_Spec.md` §5.11:** Thêm CallKit integration requirement cho iOS và dual TURN preconnect strategy.

---

## 🟡 R4 — Database Schema Migration: Two-Tier SQLite không có versioning

**Phân tích:** `Feature_Spec.md` định nghĩa kiến trúc `hot_dag.db` + `cold_state.db` rất chi tiết, nhưng **không có một dòng nào** về database schema versioning hay migration strategy. Khi TeraChat v2.0 thay đổi cấu trúc DAG (rất có thể xảy ra khi thêm tính năng collaboration mới), thiết bị đang chạy v1.x sẽ có schema cũ.

**Giải pháp — SQLite Schema Versioning Protocol:**

```rust
// core/src/storage/migration.rs
const CURRENT_HOT_DAG_SCHEMA_VERSION: u32 = 1;
const CURRENT_COLD_STATE_SCHEMA_VERSION: u32 = 1;

pub struct MigrationRunner {
    migrations: Vec<Box<dyn Migration>>,
}

impl MigrationRunner {
    pub fn run(&self, db: &Connection) -> Result<()> {
        let current_version = db.pragma_query_value(None, "user_version", |r| r.get(0))?;
        
        for migration in &self.migrations {
            if migration.version() > current_version {
                // Backup trước khi migrate
                let backup_path = format!("{}.bak.v{}", db_path, current_version);
                db.backup(DatabaseName::Main, &backup_path, None)?;
                
                // Chạy migration trong transaction
                db.execute_batch("BEGIN EXCLUSIVE TRANSACTION")?;
                migration.up(db)?;
                db.pragma_update(None, "user_version", migration.version())?;
                db.execute_batch("COMMIT")?;
            }
        }
        Ok(())
    }
}
```

Thêm rule bất biến: **cold_state.db có thể rebuild từ hot_dag.db bất kỳ lúc nào** — đây là safety net quan trọng nhất. Nếu migration cold_state.db fail, drop nó và rebuild từ hot_dag.db.

**Cập nhật `Feature_Spec.md` §6.2 (Database Layer):** Thêm `§Schema Migration Protocol` và rebuild-from-hot-dag safety net.

---

## 🟡 R5 — AES-NI / ARM NEON: Không có software fallback cho chip cũ

**Phân tích:** `Core_Spec.md §2.6` và `Feature_Spec.md §6.1` ưu tiên AES-NI (Intel/AMD) và ARM NEON để tăng tốc Kyber768 và AES-256-GCM. Các thiết bị Android cũ (Cortex-A53 trên Snapdragon 430, MediaTek Helio A22 — vẫn phổ biến ở thị trường SME Việt Nam/Đông Nam Á) không có hardware crypto engine chuyên dụng.

**Giải pháp — Crypto Backend Detection:**

```rust
// Rust build-time feature detection + runtime fallback
#[cfg(target_arch = "x86_64")]
use aes::Aes256 as AesImpl; // uses AES-NI via cpu-feature detection

#[cfg(target_arch = "aarch64")]  
use aes::Aes256 as AesImpl; // uses ARM Crypto Extension if available, else SW

// Runtime capability check
pub fn init_crypto_backend() -> CryptoBackend {
    if is_cpu_feature_detected!("aes") && is_cpu_feature_detected!("sse2") {
        CryptoBackend::HardwareAccelerated
    } else {
        // Software fallback — chậm hơn 3-5x nhưng functional
        tracing::warn!("AES-NI not available, using software backend. Expect ~3x slower encryption.");
        CryptoBackend::Software
    }
}
```

Thêm **performance warning** trong Admin Console khi thiết bị dùng software backend: *"Thiết bị này không có hardware crypto. Mã hóa chậm hơn 3x bình thường. Nâng cấp thiết bị để cải thiện hiệu suất."*

---

## 🟡 R6 — Whisper AI Local Memory Budget: Thiếu constraint

**Phân tích:** `Feature_Spec.md §5.21` mô tả Whisper AI chạy local để chuyển Voice → Text khi Tier 2 fallback. Whisper tiny = 39MB, Whisper base = 74MB. Trong khi đó, iOS LRU Cache đã chiếm 50MB và Micro-Crypto module ~4MB. Tổng ~93-128MB có thể trigger Jetsam trên thiết bị RAM 3GB với pressure cao.

**Giải pháp — Whisper Memory Budget Protocol:**

```rust
pub enum WhisperModelTier {
    /// Whisper tiny.en — 39MB, WER ~15% tiếng Anh, ~25% tiếng Việt
    Tiny,
    /// Whisper base — 74MB, WER ~8% tiếng Anh, ~15% tiếng Việt  
    Base,
    /// Disabled — fallback về text-only BLE
    Disabled,
}

pub fn select_whisper_tier(available_ram_mb: u32, battery_pct: u8) -> WhisperModelTier {
    if battery_pct < 20 { return WhisperModelTier::Disabled; }
    if available_ram_mb > 200 { return WhisperModelTier::Base; }
    if available_ram_mb > 100 { return WhisperModelTier::Tiny; }
    WhisperModelTier::Disabled // Ưu tiên stability hơn voice feature
}
```

Thêm constraint cứng: Whisper chỉ load khi `available_ram > 100MB` và `battery > 20%`. Khi Disabled, UI hiển thị: *"Thiết bị đang tiết kiệm RAM — Voice tạm chuyển sang text."*

---

## 🟢 R7 — SQLite Write Contention: Priority Scheduling

**Giải pháp đơn giản:** Tách hai database hoàn toàn vào hai tokio task với priority khác nhau. `hot_dag.db` ở `Priority::High`, `tapp_egress.db` ở `Priority::Low`. Rust tokio scheduler đảm bảo messaging core không bao giờ bị Egress starve.

---

## Tổng hợp Master — 7 File cần cập nhật (Toàn bộ 4 lớp)

| File | Thay đổi từ Lớp 1 | Thay đổi từ Lớp 2 | Thay đổi từ Lớp 3 | Thay đổi từ Lớp 4 |
|---|---|---|---|---|
| **`Core_Spec.md`** | Huawei HMS, Token Protocol, iOS mlock, EMDP | macOS Entitlement Matrix, Android 14 | License Boundary, Tiered TTL, Conflict Resolution | QUIC scope fix, CallKit TURN, AES-NI fallback |
| **`Feature_Spec.md`** | Flutter unified, WASM Parity, Push Key Ladder | Linux packaging, iOS Keychain segmentation, Wayland | Conflict Resolution tiers, ABI Contract | AWDL Monitor, DB schema migration, Whisper budget |
| **`Design.md`** | Huawei breakpoint, MeshRole banner | GPU Capability Fallback 3-tier | Conflict Resolution UI, FCP Trust Badge | AWDL status banner, Voice drop warning state |
| **`Introduction.md`** | Platform matrix + Huawei, Survival mode levels | Windows ARM64, Linux distro | Zero-Knowledge Retention clarify, Offline TTL | QUIC client scope clarify, WebRTC CallKit note |
| **`BusinessPlan.md`** | Huawei AppGallery strategy | EV Code Signing, Signing Pipeline | License Boundary, TCO Calculator, GovMilitary TTL | AES-NI performance tier note cho SME market |
| **`Function.md`** | Mesh Graceful Handover | Flat GPU UI flow | Offline Conflict flow, FCP Trust Boundary | AWDL hotspot conflict user flow, Voice fallback flow |
| **`Web_Marketplace.md`** | Huawei AOT bundle rule | Linux GPG/Cosign signing | Host Function ABI Versioning | Whisper model tier requirement cho .tapp voice plugins |

---

## Combo Giải pháp Tổng thể 4 Lớp

**Combo Alpha — Unified Core** (Sprint 1, cao nhất): Flutter unified mobile + Huawei HMS Stack + Token-based FFI Protocol + macOS XPC JIT isolation + Linux .deb/.rpm packaging. Giải quyết 12/28 điểm xung đột có tác động cao nhất.

**Combo Beta — Hardened Packaging** (Sprint 2): GPU Fallback Matrix + iOS Keychain segmentation + CI/CD Signing Pipeline + Android 14 battery handling + AWDL Monitor. Giải quyết 8/28 điểm.

**Combo Gamma — Protocol Integrity** (Sprint 3-4): EMDP Mesh + Tiered Retention + Offline TTL dynamic + QUIC scope fix + CallKit WebRTC + DB migration protocol + AES-NI fallback + Whisper memory budget. Giải quyết 8/28 điểm còn lại.

---
=======================================================================

# 🔬 Lớp 5 — Rủi ro Hội tụ Sau Nâng cấp

Đây là điều quan trọng cần hiểu rõ: **mỗi giải pháp đưa vào đều có khả năng tạo ra xung đột mới**. Sau khi áp dụng toàn bộ 4 lớp, có 3 rủi ro khẩn cấp mới xuất hiện do chính các fix đó gây ra.

---

## 🔴 S1 — Flutter Dart FFI + Token Protocol: Memory Ownership Race

**Tại sao xảy ra SAU nâng cấp:** Lớp 1 thay React Native → Flutter và Lớp 3 thêm Token Protocol (`tera_buf_acquire`/`tera_buf_release`). Khi kết hợp, vấn đề mới xuất hiện.

Trong React Native JSI, `std::unique_ptr` với Custom Deleter đảm bảo C++ destructor gọi `tera_buf_release` **deterministically** khi object ra khỏi scope. Dart GC thì khác hoàn toàn — GC không đảm bảo thứ tự hay thời điểm finalize. Nếu Dart GC chưa chạy finalizer mà Rust Core đã timeout token (ví dụ token TTL 30s cho Smart Approval), `ref_count` về 0 và Rust zeroize buffer — trong khi Dart vẫn nghĩ buffer còn sống.

**Giải pháp — NativeFinalizer với Explicit Keepalive:**

```dart
// Dart: Explicit keepalive đảm bảo buffer sống đến khi transaction xong
class TeraSecureBuffer {
  final TeraBufferToken _token;
  final Finalizer<TeraBufferToken> _finalizer;
  bool _released = false;
  
  TeraSecureBuffer(this._token)
    : _finalizer = Finalizer((token) {
        // Finalizer được gọi bởi GC — nhưng cần guard
        if (!_released) {
          tera_buf_release(token);
        }
      }) {
    // Attach với this làm detach key — cho phép explicit release
    _finalizer.attach(this, _token, detach: this);
  }
  
  // Transaction completion: LUÔN gọi explicit release trước khi GC
  void releaseNow() {
    if (!_released) {
      _released = true;
      _finalizer.detach(this);
      tera_buf_release(_token);
    }
  }
  
  // Dùng trong transaction: guaranteed release dù exception
  T useInTransaction<T>(T Function(Pointer<Uint8> ptr) action) {
    try {
      return action(_token.toPointer());
    } finally {
      releaseNow(); // Always release, even on exception
    }
  }
}
```

Thêm rule vào `Feature_Spec.md CONTRACT section`: *"Mọi TeraSecureBuffer trong Dart PHẢI được wrap bởi `useInTransaction` hoặc explicit `releaseNow()`. Không được để GC làm finalizer là đường duy nhất release."*

---

## 🔴 S2 — macOS XPC Worker Crash: Transaction Atomicity Gap

**Tại sao xảy ra SAU nâng cấp:** Lớp 2 tạo XPC Worker cho wasmtime JIT. Kịch bản: User đang thực hiện Smart Approval (ký WASM contract) — WASM verification đang chạy trong XPC Worker. Đúng lúc đó, Worker crash vì OOM. Main App nhận `NSXPCConnectionInterrupted`.

Câu hỏi chưa có trả lời trong bất kỳ tài liệu nào: transaction đó đang ở trạng thái nào? WASM đã verify xong chưa? Kết quả verify có được commit chưa? Nếu abort và retry, user có phải ký lại không? Nếu không retry, approval bị mất?

**Giải pháp — XPC Transaction Journal:**

```rust
// Rust Core: ghi journal entry trước khi dispatch sang XPC
pub struct XpcTransactionJournal {
    db: SqliteConnection, // hot_dag.db
}

impl XpcTransactionJournal {
    pub fn begin_xpc_transaction(&self, tx_id: Uuid, payload: &[u8]) -> Result<()> {
        // Phase 1: ghi PENDING trước khi gửi sang XPC
        self.db.execute(
            "INSERT INTO xpc_journal (tx_id, status, payload_hash, created_at)
             VALUES (?1, 'PENDING', ?2, ?3)",
            (tx_id, blake3::hash(payload).as_bytes(), unix_now()),
        )?;
        Ok(())
    }
    
    pub fn handle_xpc_interrupted(&self, tx_id: Uuid) -> XpcRecoveryAction {
        let entry = self.db.query_row(
            "SELECT status FROM xpc_journal WHERE tx_id = ?1",
            (tx_id,), |r| r.get::<_, String>(0)
        );
        
        match entry.as_deref() {
            Ok("PENDING") => XpcRecoveryAction::AbortAndNotifyUser,
            Ok("VERIFIED") => XpcRecoveryAction::CommitFromJournal, // đã verify xong
            Ok("COMMITTED") => XpcRecoveryAction::Idempotent,       // đã xong, noop
            _ => XpcRecoveryAction::AbortAndNotifyUser,
        }
    }
}
```

XPC Worker PHẢI cập nhật journal status trước khi return result. Nếu Worker crash trước khi update → status vẫn là PENDING → Main App biết an toàn để abort và hiển thị: *"Phiên ký bị gián đoạn. Vui lòng ký lại."* Không silent failure, không data corruption.

**Cập nhật `Core_Spec.md`:** Thêm `§XPC Transaction Journal Protocol` với 3 trạng thái PENDING/VERIFIED/COMMITTED và recovery action cho mỗi trạng thái.

---

## 🔴 S3 — EMDP Tactical Relay + MLS Epoch: Orphan Messages Không Decrypt được

**Tại sao xảy ra SAU nâng cấp:** Lớp 3 thêm EMDP (Emergency Mobile Dictator Protocol). Trong EMDP mode, iOS làm Tactical Relay với `TextOnlyForward` mode và `Append-Only CRDT`. Nhưng khi iOS làm Tactical Relay, nó KHÔNG có `Epoch_Key` hiện tại — iOS chỉ là Leaf Node, không phải Super Node, và MLS Epoch rotation xảy ra ở Super Node level. Khi Desktop reconnect và muốn decrypt các messages được relay qua iOS trong 60 phút EMDP, Desktop có thể thiếu intermediate epoch keys.

**Giải pháp — EMDP Key Escrow:**

```rust
// Khi iOS bắt đầu EMDP Tactical Relay mode:
// Trước khi Desktop "offline", Desktop xuất EMDP Escrow Key
pub struct EmdpKeyEscrow {
    // Desktop sinh ephemeral key cho EMDP session
    relay_session_key: AesKey256,
    // Thời điểm bắt đầu EMDP
    emdp_start_epoch: u64,
    // Thời điểm hết hạn (60 phút)  
    emdp_expires_at: u64,
}

impl Desktop {
    pub fn prepare_emdp_handover(&self) -> EmdpEscrow {
        let escrow = EmdpKeyEscrow {
            relay_session_key: AesKey256::generate(),
            emdp_start_epoch: current_mls_epoch(),
            emdp_expires_at: now() + 3600,
        };
        
        // Encrypt escrow key với iOS device's public key
        // iOS sẽ dùng relay_session_key để encrypt messages trong EMDP
        let encrypted_escrow = ecies_encrypt(
            &ios_device_pubkey,
            &escrow.serialize()
        );
        
        // Gửi qua BLE Control Plane trước khi Desktop offline
        self.ble_send(MeshControlMessage::EmdpEscrow(encrypted_escrow));
        escrow
    }
}
```

Khi Desktop reconnect: nhận lại escrow từ iOS → decrypt relay messages trong EMDP window → merge vào DAG với đúng epoch context. Messages không bị orphan.

**Cập nhật `Core_Spec.md` §5.12 EMDP:** Thêm EMDP Key Escrow handshake protocol.

---

## 🟡 S4 — Linux AppArmor/SELinux: Custom seccomp-bpf bị MAC deny

**Giải pháp — Dual-layer OS Security Profile:**

Thêm vào `.deb`/`.rpm` package:

```
# Ubuntu/Debian: AppArmor profile
/etc/apparmor.d/usr.bin.terachat:
  /proc/self/fd/* rw,
  /dev/shm/terachat** rw,
  capability ipc_lock,  # cho mlock()
  capability sys_ptrace restricted,
  # Cho phép memfd
  @{PROC}/*/fd/* rw,

# RHEL/Fedora: SELinux module  
# terachat.te:
allow terachat_t self:memfd_create { create };
allow terachat_t self:process { setsched };
```

Package postinstall script tự động detect và load profile phù hợp. Nếu AppArmor/SELinux enforce mode → load profile. Nếu disabled → chỉ dùng seccomp-bpf của TeraChat.

---

## 🟡 S5 — Huawei CRL Gossip: HMS Push không có background refresh

**Giải pháp — Huawei Polling Fallback:**

HMS không có equivalent APNs `content-available` background push cho CRL updates. Giải pháp: khi app Foreground trên Huawei, check CRL mỗi 4 giờ (aggressive polling). Khi Background, rely on HMS Push Kit Data Message (HMS có Data Message tương tự FCM) với `foreground: false` flag để trigger CRL check khi app được đánh thức.

Thêm vào `Core_Spec.md §Huawei HMS`: *"CRL refresh trên Huawei: 4h polling khi Foreground + HMS Data Message khi Background. Acknowledge rằng Huawei CRL update có thể delay tối đa 4h so với iOS/Android 30 phút."*

---

## 🟡 S6 — Shadow DB + NSURLSession Race: Write Lock Protocol

**Giải pháp — Write Lock trước Shadow Rename:**

```rust
// Trước khi bắt đầu shadow migration, đặt write lock
// NSURLSession chunks phải queue và chờ migration xong

pub struct ShadowMigrationLock {
    migration_in_progress: AtomicBool,
}

impl ShadowMigrationLock {
    pub fn acquire(&self) -> Result<MigrationGuard, MigrationError> {
        let prev = self.migration_in_progress.swap(true, Ordering::SeqCst);
        if prev {
            return Err(MigrationError::AlreadyInProgress);
        }
        Ok(MigrationGuard { lock: self })
    }
    
    // NSURLSession completion handler check lock trước khi write
    pub fn is_migration_in_progress(&self) -> bool {
        self.migration_in_progress.load(Ordering::SeqCst)
    }
}

// NSURLSession completion:
fn on_chunk_downloaded(chunk: &[u8]) {
    if SHADOW_LOCK.is_migration_in_progress() {
        // Queue chunk vào hot_dag.db thay vì cold_state_shadow.db
        queue_to_hot_dag(chunk);
    } else {
        write_to_cold_state(chunk);
    }
}
```

---

## 🟢 S7 — Chaos Engineering Matrix: Tài liệu bắt buộc trước Gov go-live

Đây là yêu cầu **non-negotiable** với Government/Military customers. Cần tạo file mới `TestMatrix.md` (hoặc thêm section vào `Core_Spec.md`) với 7 combined-failure scenarios:

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

## Tổng kết File Update Cuối — Lớp 5

| File | Nội dung cập nhật Lớp 5 |
|---|---|
| `Core_Spec.md` | §EMDP Key Escrow Protocol · §XPC Transaction Journal · §Huawei CRL Polling Fallback · §Shadow DB Write Lock |
| `Feature_Spec.md` | §Dart FFI NativeFinalizer Contract (explicit `releaseNow()` mandate) · §AppArmor/SELinux Profile note |
| `BusinessPlan.md` | §Chaos Engineering Plan requirement — điều kiện tiên quyết trước ký hợp đồng Gov/Military |
| `Introduction.md` | Minor — update Huawei platform note: CRL refresh delay 4h acknowledged |
| `Design.md` | Minor — XPC crash recovery UI: "Phiên ký bị gián đoạn. Vui lòng ký lại." state screen |
| `Function.md` | §EMDP User Flow update — thêm Key Escrow handover step vào Mesh Graceful Handover flow |
| `Web_Marketplace.md` | Minor — AppArmor note cho Linux .tapp publishers: seccomp-bpf profile compatibility |

---

## Tuyên bố về Trạng thái Ổn định

Sau 5 lớp phân tích và 35 điểm xung đột, TeraChat đã đạt đến ngưỡng **kiến trúc ổn định** theo nghĩa: không còn xung đột cơ bản nào có xác suất xảy ra cao mà chưa có mitigation. 3 rủi ro Lớp 5 đều là **emergent conflicts** — chỉ xuất hiện khi các fixes kết hợp với nhau, và đều có giải pháp rõ ràng. Đây là dấu hiệu tốt: không có thêm rủi ro kiến trúc nền tảng.

Điều còn lại không phải là xung đột kỹ thuật mà là **rủi ro vận hành**: không có team nào, dù thiết kế tốt đến đâu, có thể đảm bảo zero-incident trước khi có Chaos Engineering Plan được chạy thực tế. `TestMatrix.md` là tài liệu duy nhất còn thiếu có thể chặn một Gov contract.

---
