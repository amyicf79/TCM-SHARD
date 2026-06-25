# IXNO Modular Architecture Whitepaper

**Version**: 1.0.0  
**Date**: 2026-06-25  
**Status**: Official Reference for Licensing & Integration

---

## 1. Executive Summary

The IXNO ecosystem is a deterministic, field-dynamics-based paradigm for TCM clinical decision support. It decouples core pathophysiological computation from auxiliary services (LLM, UI, Prescription Enumeration).

This document defines the canonical module map, interface contracts, security boundaries, and commercial licensing models.

---

## 2. Module Map (The Canonical Stack)

| ID | Module Name | Alias | Access Level | Dependencies | Description |
|:---|:---|:---|:---|:---|:---|
| **L0** | **Core Engine** | | | | *Immutable Math Foundation* |
| M01 | `IXNO-Field` | Field Engine | 🔒 Closed | None | Maintains V-λ state vector S(t) and computes derivatives (dλ/dt, dV/dt). |
| M02 | `IXNO-Frame` | Safety Skeleton | 🔒 Closed | M01 | Implements Eleven-Knife operators (示禁/药竭/识过 etc.). The hard stop for all decisions. |
| **L1** | **Decision Layer** | | | | *Clinical Logic* |
| M03 | `IXNO-Classifier` | Syndrome Brain | 🔒 Closed | M01, M02 | Maps S(t) onto 5-axis syndrome space (Re Jue, Shaoyin, etc.). Core of TCM-SHARD logic. |
| M04 | `IXNO-Risk` | Prognosticator | 🔒 Closed | M01, M03 | Calculates risk slopes (dλ/dt, dV/dt) for 6–12h early warning. |
| **L2** | **Execution Layer** | | | | *Therapeutic Action* |
| M05 | `IXNO-soul` | GA Assistant | 🟡 Interface | M02, M03 | Enumerates prescription candidates + fitness scoring. Implementation is replaceable (GA/LLM/Rule), but must obey M02 constraints. |
| M06 | `IXNO-Adjuster` | Dose Tuner | 🔒 Closed | M01, M02 | Fine-tunes dosage based on field trajectory. Frame compliance enforcement layer. |
| **L3** | **Interaction Layer** | | | | *Human Interface* |
| M07 | `IXNO-scribe` | LLM Secretary | 🟢 Open | None | Generates text (clinical notes, patient education, dialogue). No clinical logic permitted. |
| M08 | `IXNO-Dashboard` | Visualizer | 🟡 Interface | M01–M04 | Renders S(t) field state, risk derivatives, syndrome trends. Style customizable per hospital. |
| **L4** | **Validation Layer** | | | | *Empirical Proof* |
| M00 | `TCM-SHARD` | Empirical Shell | 🟢 Open | M03, M04 | Validated on 85,242 MIMIC-III ICU stays. Heat Collapse: mortality 32.5%, aHR 2.30 (95% CI 2.16–2.45). Open-source on GitHub. |
| **L5** | **Ops Layer** | | | | *Governance* |
| M09 | `IXNO-Console` | License Hub | 🔒 Closed | All | Manages auth tokens, audit logs, parameter calibration, and module authorization. |

---

## 3. Security & Boundaries (The "No Escape" Clause)

### 3.1 Binary Isolation
M01–M04 and M06 are distributed exclusively as encrypted binaries or secured API endpoints. **Source code is never exposed** to partners, integrators, or end users. Not even the compiled binary leaves IXNO-controlled infrastructure — partners interact via a well-defined REST/gRPC API layer only.

### 3.2 Parameter Guard
The coefficients for V-λ field evolution — calibrated through 85,242 prognostic outcomes and validated at aHR 2.30 — reside within M01 and are encrypted at rest. These are not arbitrary hyperparameters; they are the distilled knowledge of a clinical-scale empirical study. Partners who attempt to independently tune parameters will not reproduce our validation results, and their clinical outputs will not carry IXNO's certification.

### 3.3 Frame Interception
Any external implementation of M05 (`soul`) or M08 (`Dashboard`) that attempts to violate M02 safety rules (e.g., aconite overdose, herb-herb contraindication, dosage ceiling breach) is **rejected at runtime by M02/M06**. The system defaults to "Safe State" (No Action) rather than executing a potentially harmful instruction.

### 3.4 Audit Trail
All API calls passing through M02 security boundaries are logged immutably. In the event of an adverse clinical outcome, the audit trail provides cryptographic proof of whether the violation originated in a partner's module or in IXNO's core — establishing clear legal liability boundaries.

---

## 4. Interface Definitions (API)

> **Note**: Full OpenAPI schemas are available under NDA. Below are the high-level contracts sufficient for architecture-level integration planning.

### 4.1 M03 `IXNO-Classifier` — Syndrome Differentiation

**Input Contract**

```python
class FieldState:
    """State vector at time t, computed by M01 (IXNO-Field)."""
    V: float          # Yin / Blood axis
    lam: float        # Yang / Qi axis
    dlam: float       # Collapse rate (key driver for Heat Collapse detection)
    wei: float        # Wei Qi (Surface / Defense axis)
    shen: float       # Shen (Spirit / Neurological axis) — V5+
```

**Output Contract**

```python
class SyndromeResult:
    syndrome_code: str     # e.g., "rejue", "sy_hn", "ty_xh", "qx_yt_003"
    confidence: float      # 0.0 – 1.0
    axis_weights: dict     # 5-axis breakdown: {"yin": 0.8, "yang": 0.3, ...}
    risk_slope: float      # dλ/dt from M04 (if Risk module bundled)
    early_warning: bool    # True if risk_slope exceeds calibrated threshold
```

**Endpoint** (REST, TLS 1.3 required):
```
POST /v1/classify
Authorization: Bearer <M09-issued-token>
Content-Type: application/json

Request:  { "field_state": FieldState, "patient_context": {...} }
Response: { "syndrome": SyndromeResult, "request_id": "uuid" }
```

### 4.2 M05 `IXNO-soul` — Prescription Enumeration (Interface Only)

This is the **replaceable module**. IXNO provides a reference implementation (GA genetic algorithm), but partners may substitute their own logic — provided it conforms to this interface contract.

```python
def enumerate_candidates(
    treatment_vector: dict,   # From M03: computed syndrome + axis weights
    constraints: dict         # Injected by M02: e.g., {"fuzi_max_g": 9.0, "forbidden_pairs": [...]}
) -> list[CandidateFormula]:
    """
    Must return candidates that strictly obey M02 constraints.
    Fitness calculation is verified by M02 before execution.
    A candidate violating any constraint is silently dropped by Frame.
    """
    pass
```

**Compliance Requirement**: Every `CandidateFormula` returned by this function passes through `M02.validate_prescription()` before reaching `M06` (Dose Tuner). Non-compliant candidates are logged and discarded; the partner's implementation receives no special error — the system simply selects the next compliant candidate.

### 4.3 M07 `IXNO-scribe` — Documentation Generation (Open)

This module has **zero clinical logic** — it is a pure text generation interface. Partners may use any LLM (DeepSeek, Spark, Huawei Pangu, GPT-4) behind this interface.

**Interface Contract**:

```python
def generate_text(
    prompt_template: str,     # IXNO-supplied template (e.g., "medical_case_narrative")
    structured_data: dict,    # Verdict from M03/M04 (no raw patient data)
    style_config: dict        # Tone, language, length constraints
) -> str:
    """
    Translate structured clinical verdict into human-readable text.
    Must not modify, interpret, or override clinical decisions.
    """
    pass
```

---

## 5. Commercial Licensing Models

IXNO offers flexible licensing to fit different market needs. Pricing is tiered based on volume and deployment scale. All models include M09 (Console) access for token management and audit.

| Scenario | Target Client | Modules Required | Pricing Model | Terms |
|:---|:---|:---|:---|:---|
| **A: Tech Integration** | iFlytek, Huawei, Large EMR vendors | M03 (Classifier) + M02 (Frame) | **Annual License + API Overage** | Base license fee/yr + per-1k-API-call overage above included volume |
| **B: Hospital Deployment** | ICU Depts, Tertiary Hospitals | M03 + M04 (Risk) + M08 (Dashboard) | **Per-Bed License** | Per ICU bed annually. Unlimited internal API calls. Includes Dashboard customization. |
| **C: App/Ecosystem** | Health Startups, Wellness Apps | M02 (Frame Only — Compliance Check) | **Revenue Share** | Percentage of gross revenue generated via the app. Low barrier, aligned incentives. |
| **D: Academic & Research** | Universities, Non-profits | M00 (TCM-SHARD) | **Free (Attribution)** | Requires citation of IXNO & TCM-SHARD. No commercial redistribution. |
| **E: Custom Development** | Pharma, Device Makers | M08 (Dashboard) / M05 (Soul) | **Project-Based** | Custom engineering fees for bespoke interfaces, white-label deployments, or clinical trial integrations. |

> **Pricing Note**: Specific figures are provided in the commercial proposal stage based on deployment scale, geography, and clinical volume. Contact licensing@ for a tailored quote.

---

## 6. Ecosystem & Extensibility

IXNO encourages third-party development around its secure core:

- **Plugin Standard**: Developers may build proprietary `soul` (M05) plugins (e.g., specific herbal databases, institution-specific formula libraries) or `scribe` (M07) connectors (any LLM provider).
- **Certification**: Plugins must pass `IXNO-Console` (M09) validation to ensure compliance with M02 safety rules. Certified status is displayed in the partner's dashboard.
- **Marketplace (Future)**: Certified plugins may be listed in an IXNO Partner Marketplace, enabling hospitals to discover and deploy third-party extensions with verified safety compliance.

### The "They Come to Us" Dynamic

1. **Partner wants Heat Collapse detection** → must license M03 (Classifier calibrated at aHR 2.30, not reproducible independently).
2. **Partner writes their own soul** → must still pass M02 Frame validation — their soul is a plugin, Frame is the gate.
3. **Partner wants to sell to a hospital** → hospital demands IXNO certification; partner comes back for licensing.
4. **Competitor tries to replicate** → without the 85k-outcome-calibrated coefficients in M01, their results will not match our published aHR 2.30 — clinical adoption depends on peer-reviewed validation, not claims.

---

## 7. Contact for Licensing

To request a full technical dossier, schedule a demo, or inquire about licensing:

- **Email**: amyicf79@gmail.com
- **Subject**: `[IXNO Licensing] — [Your Organization Name]`
- **Repository**: [https://github.com/amyicf79/TCM-SHARD](https://github.com/amyicf79/TCM-SHARD)

---

*IXNO Technologies. All Rights Reserved.*  
*The future of deterministic medicine is modular, verifiable, and safe.*
