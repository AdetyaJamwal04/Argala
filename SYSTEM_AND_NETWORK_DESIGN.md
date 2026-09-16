# Argala (अर्गला) — Definitive System & Network Design Specification

> **Classification:** Production Architecture & Cryptographic Control Plane Specification  
> **Target Node:** Samsung Galaxy A6+ (Android 10, ARMv7 32-bit / AArch64 Userspace, Termux Core)  
> **Author:** DeepMind Agentic Systems Pair Programming Engineering  
> **Status:** Standard Reference Specification (RFC-Grade)  
> **Core Axiom:** *The laptop thinks. The cloud computes. Argala authorizes, protects, queues, and connects.*

---

## Table of Contents
1. [Architectural Axiom & Sovereign Edge Philosophy](#1-architectural-axiom--sovereign-edge-philosophy)
2. [Foundational Computer Science & Underlying Theoretical Concepts](#2-foundational-computer-science--underlying-theoretical-concepts)
   - 2.1 Distributed Systems Theory & Mobile Edge Realities
     - The 8 Fallacies of Distributed Computing in Edge Deployments
     - CAP Theorem & PACELC Formal Analysis: Why Argala is a Strict CP System
     - The Two Generals' Problem, Consensus & Lease Theory (Gray & Cheriton, 1989)
     - Message Delivery Semantics & Idempotency Proof
   - 2.2 Wire-Level Telecommunications & Networking Foundations
     - The OSI 7-Layer Reference Model & Encapsulation Stack (MTU 1420 Clamping)
     - Mathematical NAT Taxonomy: Full-Cone, Restricted, Port-Restricted & Symmetric
     - NAT Traversal Theory: STUN Binding, ICE Candidate Discovery & DERP Relays
     - 3GPP Cellular Radio Resource Control (RRC) & Discontinuous Reception (DRX)
     - Transport Layer Dynamics: TCP Head-of-Line (HoL) Blocking vs. WireGuard UDP
   - 2.3 Applied Cryptography & Information Security Foundations
     - Kerckhoffs's Principle, Shannon Entropy & the 256-Bit Search Space
     - Merkle-Damgård Construction & Resistance to Length-Extension Attacks
     - Microarchitectural Timing Side-Channels, CPU Branch Prediction & Constant-Time Logic
     - Concurrency Anomalies: Formal TOCTOU Vulnerability Definition & Invariants
     - Replay Attacks & Cryptographic Nonces as Monotonic State Transitions
   - 2.4 Operating Systems & Database Storage Engine Theory
     - Linux Process Lifecycle: POSIX fork, execve, setsid & PID 1 Orphan Adoption
     - Linux Seccomp-BPF (Berkeley Packet Filter) & Syscall Trapping (SIGSYS)
     - Storage Engine Theory: Write-Ahead Logging (WAL) vs. Rollback Journals
     - ARIES Recovery Algorithm & Shared-Memory Indexing (.db-shm)
     - Solid-State Physics: NAND Flash Block Geometry, Write Amplification & Wear Leveling
3. [End-to-End Network Topology & Wire-Level Traversal](#3-end-to-end-network-topology--wire-level-traversal)
   - 3.1 The Mobile Carrier-Grade NAT (CGNAT) Reality
   - 3.2 Tailscale WireGuard Mesh, ICE/STUN Hole Punching & DERP Relays
   - 3.3 Comprehensive Wire Packet Journey (Trace of a Single Request)
   - 3.4 Port Matrix, Protocols & Bound Interfaces
   - 3.5 Cellular Radio Resource Control (RRC) & Power Management
4. [Cryptographic Engineering & Vault Protocol Specification](#4-cryptographic-engineering--vault-protocol-specification)
   - 4.1 Canonical JSON Serialization (RFC 8785)
   - 4.2 Deterministic Intent Hashing
   - 4.3 HMAC-SHA256 Signature Issuance & Cryptographic Resistance
   - 4.4 Constant-Time Verification & Timing Side-Channel Defense
   - 4.5 TOCTOU (Time-of-Check to Time-of-Use) Mitigation Proof
   - 4.6 Anti-Replay Nonce Monotonic Consumption Engine
   - 4.7 PBKDF2-HMAC-SHA256 Envelope Encryption & Local Secrets Store
   - 4.8 Secretless Outbound API Brokering Architecture
5. [Storage Engine, SQLite WAL Internals & Durable Queue](#5-storage-engine-sqlite-wal-internals--durable-queue)
   - 5.1 SQLite Write-Ahead Logging (WAL) Architecture & eMMC Wear Leveling
   - 5.2 Concurrency Pragmas & Lock Contention Optimization
   - 5.3 Idempotency Deduplication Key Pattern (HTTP 202 vs 200)
   - 5.4 Distributed Worker Lease Protocol & Automatic Crash Recovery
   - 5.5 Dead-Letter Queue (DLQ) & Poison Pill Quarantine
6. [Cyber-Physical Human-in-the-Loop (HITL) Subsystem](#6-cyber-physical-human-in-the-loop-hitl-subsystem)
   - 6.1 Android Hardware Abstraction Layer (HAL) Bridge via Termux API
   - 6.2 Multi-Modal Physical Actuation (Haptics, TTS Audio, Notifications)
   - 6.3 Ticket Lifecycle State Machine & Anti-Zombie TTL Engine
   - 6.4 Embedded Mobile Web Dashboard (Zero-Dependency Dark-Mode PWA)
7. [Zero-Trust Identity, Scopes & Emergency Kill Switch](#7-zero-trust-identity-scopes--emergency-kill-switch)
   - 7.1 Identity-Based Access Control (IBAC) & Scoped Capability Policies
   - 7.2 Ingress Scope Enforcement Middleware (require_scope)
   - 7.3 The Emergency Kill Switch Protocol (The "Nuclear Option")
   - 7.4 Monotonic Revocation Ledger & Session Invalidation
8. [Model Context Protocol (MCP) Standard Implementation](#8-model-context-protocol-mcp-standard-implementation)
   - 8.1 Anthropic MCP 2024-11-05 Specification Compliance
   - 8.2 Hybrid SSE & JSON-RPC 2.0 Streaming Architecture
   - 8.3 Dynamic Tool Registration & Telemetry Exposure
9. [Hardware Lifecycle, Daemonization & Android Kernel Quirks](#9-hardware-lifecycle-daemonization--android-kernel-quirks)
   - 9.1 Android Doze Mode Circumvention & Kernel Wake-Lock Management
   - 9.2 Seccomp-BPF Syscall Filtering & Bypassing "Bad System Call" (SIGSYS)
   - 9.3 Watchdog Supervisor Loop & Crash Resilience
   - 9.4 Android BOOT_COMPLETED Broadcast & Termux:Boot Pipeline
10. [STRIDE Threat Model & Security Invariants](#10-stride-threat-model--security-invariants)
11. [Exhaustive Wire & API Specification](#11-exhaustive-wire--api-specification)
12. [Latency Budgets & Performance Profile](#12-latency-budgets--performance-profile)

---

## 1. Architectural Axiom & Sovereign Edge Philosophy

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          THE COMPUTE FABRIC                            │
│                                                                        │
│   Developer Workstation          Cloud VM GPU Cluster                  │
│   (Laptop AI Agent)              (LangGraph / Heavy Inference)         │
│   • Generates code               • Runs 70B+ parameter LLMs            │
│   • Constructs plans             • Processes vector RAG databases      │
│   • Untrusted / Hallucination-   • Ephemeral & subject to prompt       │
│     prone environment              injection                           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         Untrusted Execution Intent
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 ARGALA: THE HARDWARE CONTROL PLANE                     │
│               Physical Samsung Galaxy A6+ (Android 10)                 │
│                                                                        │
│   • Hardware Security Module     • Sovereign Credential Vault          │
│   • Physical Haptic/Audio Gate   • Durable Job Queue & Ledger          │
│   • Zero-Trust IBAC Validator    • Hardware Emergency Kill Switch      │
└────────────────────────────────────────────────────────────────────────┘
```

Modern autonomous AI systems suffer from an **architectural coupling vulnerability**: the compute environment that generates decisions is also given the credentials to execute them. If an agent with database credentials experiences prompt injection or hallucination, it can execute irreversible destruction (e.g. dropping production databases or draining cloud budgets) in milliseconds.

**Argala enforces an unbreachable separation of Compute and Custody:**
1. **The Laptop Thinks**: The workstation or cloud GPU cluster is the untrusted reasoning plane. It generates execution intents.
2. **Argala Authorizes**: High-privilege credentials never touch the laptop or cloud. They are held in memory-derived encryption on an independent physical smartphone in the user's pocket.
3. **The Physical Gate**: No irreversible state transition occurs without the phone vibrating, speaking the intent aloud, and requiring physical human verification.
4. **The Sovereign Deadbolt**: If an agent runs amok, the user reaches into their pocket and taps the Emergency Kill Switch, cutting off all agent access globally in sub-millisecond time.

---

## 2. Foundational Computer Science & Underlying Theoretical Concepts

Every architectural decision in Argala—from its cryptographic envelope formats to its kernel socket choices and SQLite pragmas—is grounded in foundational theorems of computer science, distributed systems, networking physics, and operating systems. This section formalizes the theoretical concepts that govern the system.

### 2.1 Distributed Systems Theory & Mobile Edge Realities

#### 2.1.1 The 8 Fallacies of Distributed Computing in Edge Deployments
Peter Deutsch and James Gosling formulated the *8 Fallacies of Distributed Computing*. In cloud data centers with redundant optical backbones, engineers often ignore these fallacies with minimal immediate penalty. In a mobile edge control plane operating on a battery-powered smartphone over cellular radio, **all eight fallacies manifest continuously**:

1. **"The network is reliable"**: Mobile connections suffer from handovers between cellular base stations (eNodeB / gNodeB), transient cell tower congestion, RF attenuation in elevators or basements, and baseband power-saving shutdowns.
   * *Argala Invariant*: Argala assumes zero network reliability. The local control plane runs completely standalone. All inter-agent communications utilize durable queue persistence with state recovery.
2. **"Latency is zero"**: Cellular links transition through Radio Resource Control (RRC) power states. Waking a dormant cellular radio introduces a 100ms–250ms physical latency spike. Tailscale DERP relays traversing geographical regions introduce additional roundtrip delays.
   * *Argala Invariant*: Argala decouples submission from processing via asynchronous HTTP 202 Accepted semantics and event streaming (SSE).
3. **"Bandwidth is infinite"**: Mobile cellular data plans are metered, throttled, and subject to packet loss under high congestion.
   * *Argala Invariant*: Wire formats enforce minimal payloads. JSON canonicalization strips all unnecessary whitespace and keys are kept compact.
4. **"The network is secure"**: The device connects to untrusted residential Wi-Fi, public hotspots, or cellular towers susceptible to IMSI-catchers (Stingrays).
   * *Argala Invariant*: Zero-Trust architecture. Argala treats the underlying transport network as completely hostile and compromised. All traffic is encapsulated within authenticated WireGuard ChaCha20-Poly1305 tunnels; all payloads carry independent HMAC-SHA256 signatures.
5. **"Topology doesn't change"**: The smartphone constantly migrates across IP subnets (switching between home Wi-Fi, 4G LTE, office Wi-Fi, and 5G).
   * *Argala Invariant*: Static virtual WireGuard overlay addressing (`100.68.31.91`). The application layer binds to `tun0` and is completely isolated from physical link layer topology shifts.
6. **"There is one administrator"**: The laptop running Claude/LangGraph, the cloud worker running batch jobs, and the human carrying the phone operate under different administrative authorities and conflicting incentives.
   * *Argala Invariant*: Identity-Based Access Control (IBAC) with cryptographically segregated principals and explicit capability boundaries.
7. **"Transport cost is zero"**: Radio transmission consumes physical power (battery milliamp-hours) and heats up the application processor.
   * *Argala Invariant*: Minimized packet chatter, batched polling, and long-lived SSE connections over aggressive HTTP polling.
8. **"The network is homogeneous"**: The compute fabric spans an x86_64 Windows workstation, Linux cloud AMD64 servers, and a 32-bit ARMv7 mobile processor.
   * *Argala Invariant*: Byte-order-independent canonical data representations (RFC 8785) and strict adherence to open standards (JSON-RPC 2.0, ASGI, POSIX).

#### 2.1.2 CAP Theorem & PACELC Formal Analysis: Why Argala is a Strict CP System
Eric Brewer's **CAP Theorem** proves that a distributed data store can simultaneously provide at most two out of three guarantees:
* **Consistency (C)**: Every read receives the most recent write or an error.
* **Availability (A)**: Every non-failing node returns a non-error response without guarantee that it contains the most recent write.
* **Partition Tolerance (P)**: The system continues to operate despite an arbitrary number of messages being dropped or delayed by the network.

Because physical networks cannot avoid partitions ($P$), any real-world distributed system must trade off between $C$ and $A$.

Furthermore, Daniel Abadi's **PACELC Theorem** extends CAP to normal operation:
$$\text{If Partition }(P) \rightarrow \text{Tradeoff between Availability }(A) \text{ and Consistency }(C); \quad \text{Else }(E) \rightarrow \text{Tradeoff between Latency }(L) \text{ and Consistency }(C)$$

```text
                  PARTITION (P)
                 /             \
        Availability (AP)    Consistency (CP)  <── [ARGALA]
       "Always answer, even   "Refuse action if consistency
        if state is stale"     or authorization is in doubt"
                 │             │
        (Eventual Consistency) (Fail-Closed Sovereign Security)
```

**Argala's Formal Stance: Strict $PC/EC$ (Consistency over Availability, Consistency over Latency)**
* **During Partition ($P$)**: If an autonomous AI agent loses connectivity to the Argala smartphone, or if an approval ticket cannot reach the human operator, Argala **fails closed**. It does **not** allow optimistic or default execution of sensitive actions. Availability is sacrificed to preserve absolute consistency and security invariants. An unverified database mutation or cloud deletion is irreversible; a delayed action is merely inconvenient.
* **During Normal Execution ($E$)**: Argala chooses **Consistency ($C$) over Latency ($L$)**. It forces canonical serialization (RFC 8785), SHA-256 intent hashing, HMAC signature verification, SQLite WAL disk flushing, and anti-replay nonce commits before returning a signed authorization token.

#### 2.1.3 The Two Generals' Problem, Consensus & Lease Theory (Gray & Cheriton, 1989)
In distributed systems, the **Two Generals' Problem** proves that two nodes communicating over an unreliable channel can never reach 100% guaranteed consensus regarding whether both have agreed on a state transition.

In naive distributed job queues, systems attempt distributed locking via distributed transactions or mutual exclusion locks. However, if a worker node crashes or loses network while holding a lock, the system deadlocks indefinitely.

Argala resolves this using **Time-Bounded Distributed Leases**, formulated by Cary Gray and David Cheriton (1989):
* Instead of granting an indefinite lock, Argala grants a **lease** bounded by a physical monotonic clock timeout:
  $$\text{LeaseExpiry} = t_{\text{claimed}} + \Delta t_{\text{lease}}$$
* The worker holds exclusive rights to execute the job if and only if:
  $$t_{\text{current}} < \text{LeaseExpiry}$$
* **Crash-Fault Tolerance**: If the worker process is terminated by the Android kernel's Out-Of-Memory (OOM) killer or suffers a network drop, it ceases renewing its lease. As soon as $t_{\text{current}} \ge \text{LeaseExpiry}$, the lease expires automatically. The SQLite queue's recovery query:
  $$\text{WHERE status} = \text{'PENDING'} \lor (\text{status} = \text{'RUNNING'} \land \text{lease\_expires\_at} < t_{\text{now}})$$
  instantly reclaims the abandoned job without requiring complex distributed consensus protocols (like Paxos or Raft) that would exhaust mobile CPU and battery resources.

#### 2.1.4 Message Delivery Semantics & Idempotency Proof
The Fischer-Lynch-Paterson (**FLP**) Impossibility Theorem proves that deterministic asynchronous consensus is impossible in the presence of even a single unannounced crash failure. Consequently, true **exactly-once delivery** across an asynchronous network is physically impossible.

Distributed architectures must choose between:
1. **At-most-once**: Messages may be lost, but never duplicated.
2. **At-least-once**: Messages are never lost, but may be duplicated due to retries.

Argala adopts **At-least-once transport combined with idempotent execution**, achieving **effectively-once processing**:
* Mathematically, an operation $f$ is **idempotent** if applying it multiple times produces the same system state as applying it once:
  $$f(f(x)) = f(x)$$
* When an agent submits a job to `POST /v1/jobs`, it supplies a cryptographically random UUIDv4 `idempotency_key`.
* **State Transition Logic**:
  * If $\text{idempotency\_key} \notin \text{DB}$: Insert job, transition state to `PENDING`, return `HTTP 202 Accepted` ($\Delta \text{State} \neq \emptyset$).
  * If $\text{idempotency\_key} \in \text{DB}$: Fetch existing record, return `HTTP 200 OK` ($\Delta \text{State} = \emptyset$).
* Even if network timeouts cause an agent to retry submission 10 times, exactly one job is inserted and executed.

---

### 2.2 Wire-Level Telecommunications & Networking Foundations

#### 2.2.1 The OSI 7-Layer Reference Model & Encapsulation Stack (MTU 1420 Clamping)
Understanding Argala's network path requires tracing how data flows through the OSI 7-Layer Stack, and specifically why standard 1500-byte Ethernet packets cause silent network failure if Maximum Transmission Unit (MTU) clamping is ignored.

```text
Layer 7 (Application)  : HTTP/1.1 JSON Payload / SSE Stream (FastAPI / Uvicorn)
Layer 6 (Presentation) : TLS 1.3 / RFC 8785 Canonical JSON Serialization
Layer 5 (Session)      : Tailscale Encrypted Peer Session (WireGuard Handshake)
Layer 4 (Transport)    : WireGuard UDP Datagram (Port 41641) encapsulating Inner TCP:8000
Layer 3 (Network)      : Inner IPv4 (100.68.31.91) encapsulated in Outer Carrier IPv4/IPv6
Layer 2 (Data Link)    : Wi-Fi (802.11ac) or Cellular LTE Frame (MAC / PDCP)
Layer 1 (Physical)     : Radio Frequency Transceiver (Snapdragon 450 Baseband Modem)
```

##### Mathematical Derivation of MTU Clamping
Standard Ethernet interfaces enforce an MTU of 1500 bytes:
$$\text{Max Payload Size} = \text{MTU} = 1500\text{ bytes}$$

When Tailscale encapsulates an inner IP packet into an outer WireGuard UDP datagram, overhead accumulates at every layer:
1. Standard Outer IPv4 Header: $20\text{ bytes}$ (or IPv6: $40\text{ bytes}$)
2. Outer UDP Header: $8\text{ bytes}$
3. WireGuard Encapsulation Header:
   - Type (1 byte) + Reserved (3 bytes): $4\text{ bytes}$
   - Sender Index: $4\text{ bytes}$
   - Monotonic Nonce Counter: $8\text{ bytes}$
   - Poly1305 Authentication Tag: $16\text{ bytes}$
   - Subtotal WireGuard Overhead: $32\text{ bytes}$
4. Total Encapsulation Overhead:
   $$\text{Overhead} = 20 (\text{IPv4}) + 8 (\text{UDP}) + 32 (\text{WireGuard}) = 60\text{ bytes}$$
5. Maximum Inner Tunnel MTU:
   $$\text{MTU}_{\text{tun0}} = 1500 - 60 = 1440\text{ bytes (or } 1420\text{ bytes with IPv6/PPPoE margin)}$$

**Why this matters**: If the virtual adapter `tun0` attempts to transmit an inner TCP segment of 1460 bytes (expecting a 1500-byte MTU), the cellular carrier's packet gateway will drop the outer packet because cellular base stations enforce strict fragment-dropping policies. Tailscale clamps the `tun0` MTU to **1420 bytes**. During the TCP three-way handshake, the Maximum Segment Size (MSS) option is clamped to:
$$\text{MSS} = \text{MTU}_{\text{tun0}} - 20 (\text{Inner IPv4}) - 20 (\text{Inner TCP}) = 1420 - 40 = 1380\text{ bytes}$$
This guarantees that no packet fragmentation ever occurs across cellular radio links.

#### 2.2.2 Mathematical NAT Taxonomy: Full-Cone, Restricted, Port-Restricted & Symmetric
To route traffic directly to a smartphone behind Carrier-Grade NAT (CGNAT), one must understand the RFC 3489 and RFC 4787 classification of Network Address Translators:

| NAT Type | Internal Mapping Rule | External Ingress Filter Rule | Hole-Punching Feasibility |
|---|---|---|---|
| **Full-Cone NAT (1:1)** | Any packet from $(IP_{in}, Port_{in})$ maps to fixed $(IP_{ext}, Port_{ext})$. | Any external host can send packets to $(IP_{ext}, Port_{ext})$. | Trivial. Any external packet reaches phone. |
| **Restricted-Cone NAT** | $(IP_{in}, Port_{in}) \rightarrow (IP_{ext}, Port_{ext})$. | External host $IP_Y$ can send packets only if $(IP_{in}, Port_{in})$ previously sent a packet to $IP_Y$. | Straightforward. STUN server coordinates mutual ping. |
| **Port-Restricted Cone** | $(IP_{in}, Port_{in}) \rightarrow (IP_{ext}, Port_{ext})$. | External host $(IP_Y, Port_Y)$ can send packets only if $(IP_{in}, Port_{in})$ previously sent a packet to $(IP_Y, Port_Y)$. | Moderate. Requires precise reciprocal UDP packet transmission. |
| **Symmetric NAT** | Every request from $(IP_{in}, Port_{in})$ to a specific destination $(IP_{dest}, Port_{dest})$ is mapped to a **unique, randomized** $(IP_{ext}, Port_{new})$. | Only the exact $(IP_{dest}, Port_{dest})$ that received the packet can reply. | **Mathematically Impossible without Relay.** |

Mobile cellular carriers (e.g. Jio, Airtel, T-Mobile, Verizon) almost universally implement **Symmetric NAT** or **Port-Restricted Carrier-Grade NAT (RFC 6598)**.

#### 2.2.3 NAT Traversal Theory: STUN Binding, ICE Candidate Discovery & DERP Relays
Tailscale utilizes the **Interactive Connectivity Establishment (ICE - RFC 8445)** and **Session Traversal Utilities for NAT (STUN - RFC 5389)** protocols to punch direct UDP tunnels through carrier firewalls:

```text
Client (Laptop)                     STUN Server (Coordination)                    Sovereign Edge (Phone)
      │                                         │                                           │
      │── 1. STUN Request (UDP) ───────────────>│                                           │
      │<─ 2. STUN Response (Mapped IP:Port_A) ──│                                           │
      │                                         │<── 3. STUN Request (UDP) ─────────────────│
      │                                         │─── 4. STUN Response (Mapped IP:Port_B) ──>│
      │                                         │                                           │
      │── 5. Exchange Candidates via DERP Control Plane ───────────────────────────────────>│
      │                                                                                     │
      │── 6. Simultaneous UDP Packet to Port_B ────────────────────────────────────────────>│ (Carrier NAT opens state)
      │<─ 7. Simultaneous UDP Packet to Port_A ─────────────────────────────────────────────│ (Carrier NAT opens state)
      │                                                                                     │
      │══════════════ 8. DIRECT ENCRYPTED PEER-TO-PEER WIREGUARD TUNNEL ESTABLISHED ═══════│
```

##### The Symmetric NAT Deadlock & The DERP Solution
When the cellular network assigns random external ports for each destination, packet 6 and packet 7 cannot anticipate the randomized port numbers chosen by the carrier's NAT gateway.
In this condition, direct hole punching fails. Tailscale activates **Designated Encrypted Relay for Packets (DERP)**:
* The phone and laptop establish outbound HTTPS connections (TCP port 443) to a geographically close DERP relay server.
* Because the connections are outbound, all corporate firewalls and cellular NATs allow them.
* WireGuard packets are wrapped into DERP frames. The DERP server acts as an untrusted blind packet forwarder: because the payload is encrypted with ChaCha20-Poly1305 using the private keys of the phone and laptop, the DERP relay **cannot inspect or modify the payload**.

#### 2.2.4 3GPP Cellular Radio Resource Control (RRC) & Discontinuous Reception (DRX)
Smartphones are battery-constrained. Cellular modems cannot maintain an active radio carrier continuously without draining a 4000mAh battery within 4 hours.
The 3GPP telecommunications standard defines the **Radio Resource Control (RRC)** finite state machine:

```text
    ┌───────────────────────────────┐
    │           RRC_IDLE            │  <── Minimal power (~5-15 mW). Baseband listens
    └───────────────┬───────────────┘      only to periodic paging frames (DRX cycle).
                    │
            Paging / Inbound Packet
                    │
                    ▼
    ┌───────────────────────────────┐
    │         RRC_CONNECTED         │  <── Full radio power (~800-1500 mW). High throughput,
    └───────────────┬───────────────┘      low latency (15-30ms).
                    │
            Inactivity Timer (e.g. 10s)
                    │
                    ▼
    ┌───────────────────────────────┐
    │     RRC_INACTIVE / DRX        │  <── Intermediate state. Fast dormancy to save battery.
    └───────────────────────────────┘
```

* **Discontinuous Reception (DRX)**: In RRC_IDLE, the smartphone radio powers down its receiver for 98% of the time, waking up every 1.28s or 2.56s for a few milliseconds to check the cell tower's Paging Channel (PCH).
* **First-Packet Latency Spike**: When an agent sends a request to an idle phone, the cell tower must send an RRC Paging message during the phone's next DRX cycle. The phone then transmits a Random Access Preamble on the RACH channel, negotiates radio bearers, and enters RRC_CONNECTED. This physical radio process takes **100ms to 250ms**. Subsequent packets arrive in **15ms to 25ms**.
* **Argala Wake-Lock Optimization**: Android's OS-level power manager attempts to suspend the CPU while the radio is idle. Argala's persistent partial wake-lock prevents the application processor from going into deep sleep, ensuring that as soon as the baseband modem receives the radio frames, the kernel executes socket processing without CPU warm-up delays.

#### 2.2.5 Transport Layer Dynamics: TCP Head-of-Line (HoL) Blocking vs. WireGuard UDP
Traditional tunnels (e.g. OpenVPN over TCP) suffer from the catastrophic **TCP-over-TCP meltdown effect**:
* If an inner TCP packet is lost, inner TCP retransmits.
* Simultaneously, outer TCP detects the loss and retransmits, resulting in exponential backoff and bufferbloat.
* Furthermore, TCP enforces strict byte-stream ordering. A single lost packet halts delivery of all subsequent packets in the socket buffer (**Head-of-Line Blocking**).

Tailscale and Argala use **WireGuard over UDP**:
* WireGuard is strictly connectionless at the outer transport layer (UDP).
* Inner TCP packets are encapsulated independently. A lost inner packet does not trigger outer transport retransmissions.
* If packet $N$ is dropped over the cellular link, packet $N+1$ is delivered to userspace immediately without waiting for retransmission of $N$, eliminating outer Head-of-Line blocking.

---

### 2.3 Applied Cryptography & Information Security Foundations

#### 2.3.1 Kerckhoffs's Principle, Shannon Entropy & the 256-Bit Search Space
In 1883, Auguste Kerckhoffs formulated the foundation of modern cryptography:
> *"A cryptosystem should be secure even if everything about the system, except the key, is public knowledge."*

Argala adheres to this axiom: every line of source code, every API route, every database schema, and every wire protocol is completely open. The entire security of the Sovereign Control Plane rests strictly upon the secrecy and entropy of the 256-bit Master Key.

##### Claude Shannon's Information Entropy
For a key $K$ chosen uniformly at random from a keyspace $\mathcal{K}$ of length $n$ bits, the Shannon Entropy $H(K)$ is maximal:
$$H(K) = -\sum_{i=1}^{|\mathcal{K}|} P(k_i) \log_2 P(k_i) = \log_2 (2^{256}) = 256\text{ bits of true entropy}$$

* The search space is:
  $$2^{256} = 115,792,089,237,316,195,423,570,985,008,687,907,853,269,984,665,640,564,039,457,584,007,913,129,639,936$$
* To brute-force this keyspace, a quantum or supercomputing cluster computing $10^{18}$ hashes per second would require approximately:
  $$\frac{2^{256}}{10^{18} \times 3.15 \times 10^7\text{ seconds/year}} \approx 3.67 \times 10^{51}\text{ years}$$
  which exceeds the age of the universe ($1.38 \times 10^{10}$ years) by 41 orders of magnitude.

#### 2.3.2 Merkle-Damgård Construction & Resistance to Length-Extension Attacks
The Secure Hash Algorithm (SHA-256) is built upon the **Merkle-Damgård construction**:
A compression function $f$ iteratively updates an internal state vector $S_i$ using fixed-size 512-bit message blocks $M_i$:
$$S_0 = \text{IV}, \quad S_{i} = f(S_{i-1}, M_i), \quad H(M) = S_n$$

```text
Message M ──> [ Block M_1 ] ──> [ Block M_2 ] ──> [ Block M_n + Padding ]
                   │                 │                      │
IV (Fixed) ──> [ f(S_0, M_1) ] ──> [ f(S_1, M_2) ] ───> [ f(S_{n-1}, M_n) ] ──> Final Hash H(M)
```

##### The Length-Extension Attack Vulnerability in Naive Signatures
Suppose a naive system signs a message by prepending a secret key:
$$\text{Signature}_{\text{naive}} = \text{SHA256}(K \parallel M)$$
Because the final output of SHA-256 *is* the exact internal state $S_n$ of the compression function after processing $M$:
1. An attacker who intercepts $M$ and $\text{Signature}_{\text{naive}}$ does **not** need to know $K$.
2. The attacker sets the initial state of their own SHA-256 engine to $S_n = \text{Signature}_{\text{naive}}$.
3. The attacker appends malicious payload $M'$ and standard SHA-256 padding.
4. The attacker computes:
   $$\text{ForgedSignature} = \text{SHA256}(K \parallel M \parallel \text{Padding} \parallel M')$$
5. The naive system validates the forged signature as authentic, allowing unauthorized execution.

##### The Mathematical Proof of HMAC Immunity
To prevent length-extension attacks, Argala employs **HMAC (Keyed-Hash Message Authentication Code - RFC 2104)**:
$$\text{HMAC}(K, M) = H\Big(\big(K \oplus opad\big) \parallel H\big((K \oplus ipad) \parallel M\big)\Big)$$
where:
* $ipad = \text{0x36}$ repeated 64 times (inner padding)
* $opad = \text{0x5C}$ repeated 64 times (outer padding)

**Mathematical Proof of Immunity**:
1. The inner hash produces an intermediate digest:
   $$D_{\text{inner}} = H\big((K \oplus ipad) \parallel M\big)$$
2. The outer hash computes:
   $$\text{Final Digest} = H\big((K \oplus opad) \parallel D_{\text{inner}}\big)$$
3. Even if an attacker knows $D_{\text{inner}}$, appending data to $M$ alters $D_{\text{inner}}$.
4. More crucially, an attacker cannot compute the outer hash without the secret $(K \oplus opad)$. The inner digest is never exposed in raw state transitions, rendering length-extension attacks mathematically impossible.

#### 2.3.3 Microarchitectural Timing Side-Channels, CPU Branch Prediction & Constant-Time Logic
A foundational vulnerability in naive security software is reliance on standard equality operators (`string1 == string2`).
In standard C/Python implementations:
```c
// Naive string comparison (VULNERABLE)
int strcmp(const char *s1, const char *s2) {
    while (*s1 && (*s1 == *s2)) {
        s1++;
        s2++;
    }
    return *(const unsigned char*)s1 - *(const unsigned char*)s2;
}
```

##### Microarchitectural Attack Mechanism
1. **Early Termination**: The CPU terminates comparison at the **first byte that differs**.
2. **Timing Variance**: If byte 0 fails, execution takes $\sim 5\text{ ns}$. If bytes 0–3 match and byte 4 fails, execution takes $\sim 25\text{ ns}$.
3. **Branch Predictor & Cache Side-Channels**: The CPU's Branch Target Buffer (BTB) and L1 instruction cache exhibit different branch hit/miss latencies depending on how deep the comparison loop progressed.
4. **Statistical Amplification**: Over an array of 1,000 requests, an attacker measuring roundtrip times with high-resolution timers can deduce the correct key byte-by-byte in $256 \times 32$ attempts rather than $2^{256}$.

##### Argala's Constant-Time XOR Accumulator
Argala utilizes `secrets.compare_digest` ([`app/vault/crypto.py`](file:///c:/Projects/and/app/vault/crypto.py)), which maps to constant-time bitwise operations:
```python
def constant_time_compare(val_a: bytes, val_b: bytes) -> bool:
    if len(val_a) != len(val_b):
        return False
    accumulator = 0
    for byte_a, byte_b in zip(val_a, val_b):
        accumulator |= (byte_a ^ byte_b)
    return accumulator == 0
```
* The bitwise XOR operation (`byte_a ^ byte_b`) yields zero if and only if both bytes are identical.
* The bitwise OR accumulator (`accumulator |= ...`) accumulates any non-zero difference across the entire buffer.
* **No conditional branches (`if`/`else`) are executed inside the loop**.
* The execution path and cycle count are strictly independent of the byte values or mismatch positions ($\Delta t = 0$), eliminating all timing side-channels.

#### 2.3.4 Concurrency Anomalies: Formal TOCTOU Vulnerability Definition & Invariants
In concurrent systems, a **Time-of-Check to Time-of-Use (TOCTOU)** vulnerability occurs when a system checks a precondition at time $t_1$, but executes the privileged operation at time $t_2$, during which the underlying state was altered:

$$\Delta t_{\text{vulnerability}} = t_2 - t_1 > 0$$

```text
Time (t)        Agent (Attacker)                   Argala Gateway                   Target (Production DB)
  │                    │                                 │                                    │
  t_1                  │── Request Approval ────────────>│                                    │
                       │   "SELECT * FROM users"         │── Human Reviews & Approves ──┐     │
                       │                                 │<─────────────────────────────┘     │
  t_mutate             │   [Attacker mutates intent]     │                                    │
                       │   "DROP TABLE users"            │                                    │
  t_2                  │── Present Approved Token ──────>│                                    │
                       │                                 │── Naive Check: "Is token valid?" ──│
                       │                                 │── Executes: "DROP TABLE users" ───>│ [DISASTER]
```

##### Argala's Cryptographic Invariant Proof
Argala eliminates TOCTOU by making approval tokens mathematically **state-bound**:
1. The approval token does not sign a generic boolean (`approved=true`).
2. The approval token signs the **exact cryptographic SHA-256 hash** of the canonicalized parameters:
   $$\text{Token} = \text{HMAC}\Big(K, \text{SHA256}\big(\text{CanonicalJSON}(\text{ActionIntent})\big)\Big)$$
3. At time $t_2$, when the token is presented for execution, the verification engine recalculates:
   $$H_{\text{exec}} = \text{SHA256}\big(\text{CanonicalJSON}(\text{ExecutionPayload})\big)$$
4. If the payload was mutated between $t_1$ and $t_2$:
   $$H_{\text{exec}} \neq H_{\text{intent}} \implies \text{HMAC}(K, H_{\text{exec}}) \neq \text{Signature}$$
5. Verification fails instantly with `TOCTOU violation`. The privileged action is physically unexecutable.

#### 2.3.5 Replay Attacks & Cryptographic Nonces as Monotonic State Transitions
An attacker intercepting a valid signed token could attempt to re-execute it repeatedly (e.g. replaying a signed `transfer_funds` or `scale_up_cluster` intent).

Argala models authorization as a **Monotonic State Machine**:
* Every action intent includes a 128-bit random UUIDv4 `nonce`.
* The verification engine maintains an append-only SQLite table:
  $$\mathcal{U} = \{ \text{nonce}_1, \text{nonce}_2, \dots, \text{nonce}_k \}$$
* Verification invariant:
  $$\text{Verify}(\text{intent}) = \text{Valid}(\text{signature}) \land (\text{intent.nonce} \notin \mathcal{U}) \land (\text{intent.timestamp} + \text{TTL} > t_{\text{current}})$$
* Upon successful verification, the state transition executes atomically:
  $$\mathcal{U}' = \mathcal{U} \cup \{ \text{intent.nonce} \}$$
* Subsequent submissions with the same nonce evaluate to $\text{intent.nonce} \in \mathcal{U}'$, triggering immediate rejection.

---

### 2.4 Operating Systems & Database Storage Engine Theory

#### 2.4.1 Linux Process Lifecycle: POSIX `fork`, `execve`, `setsid` & PID 1 Orphan Adoption
To run an uninterrupted 24/7 daemon on Android without an active terminal or IDE connection, one must navigate POSIX process semantics:

```text
Interactive Shell (PID 17754) ─── POSIX fork() ───> Child Process (PID 18473)
             │                                              │
      Terminal Hangup (SIGHUP)                              │ setsid() (New Session Leader, No TTY)
             │                                              │
             ▼ (Terminated)                                 ▼
   [Shell Dies on Exit]                             Orphaned Process (PID 18473)
                                                            │
                                              Reparented to init (PID 1)
                                                            │
                                                    Continues 24/7 Execution
```

1. **`fork()`**: Duplicates the calling process, copying page tables via Copy-On-Write (COW).
2. **`setsid()`**: Breaks attachment to the controlling terminal (`/dev/pts/*`). The process becomes a session leader of a new process group, rendering it completely immune to `SIGHUP` (hangup signals) when the SSH or Termux session terminates.
3. **Orphan Adoption by `init` (PID 1)**: When the parent shell exits, the kernel detects an orphaned child process and automatically reparents it to `init` (PID 1). `init` reaps child exit statuses, preventing zombie process accumulation.
4. **File Descriptor Redirection**: Standard streams (`stdin`, `stdout`, `stderr`) are redirected to log files or `/dev/null`, preventing write errors when terminal pipes close.

#### 2.4.2 Linux Seccomp-BPF (Berkeley Packet Filter) & Syscall Trapping (`SIGSYS`)
Android 10 enforces strict **Secure Computing Mode (Seccomp-BPF)** profiles on all untrusted application userspace processes.
* **Mechanism**: When a process executes a software interrupt or `syscall` instruction, the Linux kernel passes the syscall number and architecture through a compiled Berkeley Packet Filter (BPF) bytecode program.
* **The `SIGSYS` Trap**: Standard GNU/Linux utilities like `pkill` and `pgrep` attempt to read `/proc/[pid]/stat` or invoke `process_vm_readv` across process boundaries. On Samsung Android kernels, these syscalls violate the platform's seccomp filter:
  $$\text{Filter Decision: } \text{SECCOMP\_RET\_TRAP} \implies \text{Kernel sends } \text{SIGSYS} \text{ (Bad System Call)}$$
* **Argala POSIX Solution**: Argala circumvents seccomp violations by restricting process management strictly to allowed POSIX interfaces: reading `/proc` via standard directory iteration or using `ps -A` coupled with pure awk/sed text processing.

#### 2.4.3 Storage Engine Theory: Write-Ahead Logging (WAL) vs. Rollback Journals
In traditional SQLite rollback journal mode:
* Before mutating database page $P_k$, the original unmodified page is written to a separate `journal` file.
* The dirty page is written directly to the primary database file.
* **Exclusive Concurrency Lock**: While a writer is modifying the database, **no readers can access the database**, causing high read latency and `SQLITE_BUSY` errors under concurrent agent traffic.

In **Write-Ahead Logging (WAL) mode** ([`PRAGMA journal_mode = WAL;`](file:///c:/Projects/and/app/db/database.py#L18)):
* The original database file `argala.db` is **never modified directly** during active transactions.
* All changes are appended sequentially to a separate write-ahead log file `argala.db-wal`.
* **Lock-Free Concurrency**:
  * Writers append new frames to the WAL without blocking readers.
  * Readers consult the **WAL Index** (`argala.db-shm`), a shared-memory hash table mapping database page numbers to the latest frame in the WAL.
  * Readers read a consistent historical snapshot without acquiring read locks on the database file.
  * Multiple readers and one writer operate with **complete concurrency**.

```text
Writer ────────── Appends New Frames ──────────> [ argala.db-wal ]
                                                        │
Reader 1 ─── Checks Index (.db-shm) ───> Reads WAL Frame 3 (Latest)
Reader 2 ─── Checks Index (.db-shm) ───> Reads Base DB Page (Unchanged)
                                                        │
Checkpoint ────── Merges Log into Main File ────> [ argala.db ]
```

#### 2.4.4 ARIES Recovery Algorithm & Shared-Memory Indexing (`.db-shm`)
SQLite WAL implements the principles of the **ARIES (Algorithms for Recovery and Isolation Exploiting Semantics)** database recovery algorithm:
1. **Analysis Phase**: Upon node restart after a crash or battery depletion, the database engine scans the WAL file forward from the last known checkpoint to identify all active transactions.
2. **Redo Phase**: All committed transactions recorded in the WAL are reapplied to bring the database to the exact state at the moment of the crash (Write-Ahead Logging ensures no committed write is lost).
3. **Undo Phase**: Any uncommitted transactions are rolled back by simply ignoring their trailing WAL frames.
4. **Shared-Memory (`.db-shm`)**: The index is mapped directly into process memory via POSIX `mmap()`, allowing sub-microsecond page lookups without disk I/O.

#### 2.4.5 Solid-State Physics: NAND Flash Block Geometry, Write Amplification & Wear Leveling
Smartphones use eMMC 5.1 or UFS NAND flash memory. Flash storage physics impose strict operational constraints:
* **Page vs. Block Asymmetry**: NAND flash can be read and written in **Pages** (typically $4\text{ KB}$), but can only be erased in **Blocks** (typically $256\text{ KB}$ to $4\text{ MB}$, comprising 64 to 512 pages).
* **In-Place Write Impossibility**: A flash memory cell cannot be overwritten with new data until the entire containing block is erased.
* **Write Amplification ($WA$)**: In rollback journal mode, writing a small 100-byte record forces the flash controller to read an entire $4\text{ MB}$ block, erase it, and rewrite it with the modified page:
  $$WA = \frac{\text{Bytes Written to NAND Flash}}{\text{Bytes Written by Application}} \gg 1$$
* **High Write Amplification Consequences**: Destroys battery charge and rapidly exhausts the flash memory's limited Program/Erase (P/E) cycles (typically 3,000 P/E cycles for TLC NAND).
* **WAL Mitigation**: WAL writes are strictly **sequential appends**. The flash translation layer (FTL) can write sequential pages continuously without triggering expensive block garbage collection and erase cycles, minimizing write amplification and maximizing smartphone hardware lifespan.

---

## 3. End-to-End Network Topology & Wire-Level Traversal

```mermaid
flowchart TD
    subgraph Laptop ["Client: Developer Laptop (100.105.57.62)"]
        UserApp["Agent / Browser / curl"]
        OSNet["Windows Socket Stack"]
        TailscaleClient["Tailscale WireGuard Adapter (100.105.57.62)"]
    end

    subgraph Transit ["Global Encrypted Mesh Fabric"]
        DirectP2P["Direct UDP Hole-Punched Tunnel (Port 41641)"]
        DERP["Tailscale DERP Relay (HTTPS / TLS 443 Fallback)"]
    end

    subgraph Phone ["Sovereign Edge Node: Samsung A6+ (100.68.31.91)"]
        CellRadio["Baseband Modem (LTE / Wi-Fi)"]
        LinuxKernel["Linux Kernel 4.4.x / Netfilter / tun0"]
        
        subgraph TermuxSpace ["Termux Android Userspace"]
            SecurityMiddleware["deps.py: Constant-Time Header / Query Auth"]
            UvicornASGI["Uvicorn ASGI Server (0.0.0.0:8000)"]
            FastAPICore["FastAPI Engine & Route Handlers"]
            SQLiteWAL[("data/argala.db (SQLite WAL Mode)")]
        end

        OpenSSHD["OpenSSH Daemon (0.0.0.0:8022)"]
    end

    UserApp --> OSNet
    OSNet --> TailscaleClient
    TailscaleClient -->|STUN/ICE Success| DirectP2P
    TailscaleClient -.->|Symmetric NAT Block| DERP
    DirectP2P --> CellRadio
    DERP -.-> CellRadio
    CellRadio --> LinuxKernel
    LinuxKernel -->|Port 8022| OpenSSHD
    LinuxKernel -->|Port 8000| UvicornASGI
    UvicornASGI --> SecurityMiddleware
    SecurityMiddleware --> FastAPICore
    FastAPICore --> SQLiteWAL
```

### 3.1 The Mobile Carrier-Grade NAT (CGNAT) Reality
Mobile network operators deploy Carrier-Grade NAT (RFC 6598, `100.64.0.0/10`). In mobile environments:
1. The smartphone has no public IPv4 address.
2. Inbound SYN packets from the internet are immediately dropped by the carrier firewall.
3. Cellular IP leases change constantly as the device roams between cell towers (eNodeB handovers).

### 3.2 Tailscale WireGuard Mesh, ICE/STUN Hole Punching & DERP Relays
Argala circumvents CGNAT completely using a zero-configuration WireGuard overlay:
* **Interactive Connectivity Establishment (ICE) & STUN**:
  When the laptop and phone communicate, both nodes send UDP discovery packets to Tailscale coordination servers (STUN). The coordination server maps the public IP:port assigned by the cellular carrier's NAT gateway. Both endpoints simultaneously send UDP packets to each other's mapped endpoints (`UDP:41641`), establishing stateful hole-punched NAT mappings in the carrier's state table.
* **Encrypted Fallback (DERP Relays)**:
  If a cellular provider implements strict symmetric NAT (where the external port changes per destination IP), direct UDP hole-punching fails. Tailscale seamlessly falls back to a **Designated Encrypted Relay for Packets (DERP)**. The payload is end-to-end encrypted with ChaCha20-Poly1305 between laptop and phone; the DERP server only forwards encrypted byte frames over HTTPS/TLS port 443 and cannot decrypt the data.

### 3.3 Comprehensive Wire Packet Journey (Trace of a Single Request)
When an agent executes:
```powershell
curl.exe -H "X-API-Key: argala-dev-key-change-me" http://100.68.31.91:8000/v1/telemetry
```

1. **User Space (Laptop)**: `curl.exe` initiates a TCP connection to destination `100.68.31.91:8000`.
2. **Kernel Route Table (Laptop)**: Windows routing table directs `100.64.0.0/10` to the Tailscale virtual network interface (`Tailscale Tunnel`).
3. **WireGuard Encryption**: The local Tailscale service encrypts the plaintext TCP SYN packet into a WireGuard data frame using ChaCha20 for encryption and Poly1305 for authentication, signed with the laptop's private Curve25519 key.
4. **Physical Egress**: Encapsulated into an outer UDP datagram with destination `100.68.31.91:41641` and transmitted over the physical Wi-Fi/Ethernet adapter.
5. **Carrier Transit**: Packets traverse the ISP, internet backbone, and the phone carrier's packet gateway (PGW).
6. **Mobile Ingress**: The phone's baseband modem receives the radio frames and delivers the UDP packet to the Android Linux kernel.
7. **Virtual Interface Ingress (`tun0`)**: The kernel routes UDP 41641 to the local Tailscale Android service. Tailscale decrypts the frame using its Curve25519 private key, verifies the Poly1305 MAC, and injects the raw decrypted TCP SYN packet into the virtual network adapter `tun0` at `100.68.31.91`.
8. **Socket Acceptance in Termux**: The Linux kernel routes TCP port 8000 to the listening socket held by Uvicorn.
9. **ASGI Protocol Parsing**: Uvicorn's `h11` HTTP parser parses headers and dispatches the ASGI `http` scope to FastAPI.
10. **Ingress Security Filter**: [`app/api/deps.py`](file:///c:/Projects/and/app/api/deps.py) extracts `X-API-Key` (or `?api_key=`), executes a constant-time comparison, resolves the `Principal`, verifies active lockdown state, and invokes [`app/api/routes_telemetry.py`](file:///c:/Projects/and/app/api/routes_telemetry.py).
11. **System Actuation / Metric Read**: The telemetry handler reads `/proc/meminfo` and battery state asynchronously.
12. **Return Flow**: The JSON response follows the inverse path back through `tun0`, WireGuard encryption, carrier traversal, and unrolls into `curl.exe`.

### 3.4 Port Matrix, Protocols & Bound Interfaces
| Port | Protocol | Binding Address | Network Interface | Function |
|---|---|---|---|---|
| `8000` | TCP / HTTP 1.1 | `0.0.0.0` | `tun0` (Tailscale) & `wlan0` (Local) | Core Argala ASGI API & Web Console |
| `8022` | TCP / SSH-2.0 | `0.0.0.0` | `tun0` & `wlan0` | Termux OpenSSH Administration & SCP Sync |
| `41641`| UDP / WireGuard| `0.0.0.0` | `rmnet_data0` / `wlan0` | Tailscale Peer-to-Peer Transport Tunnel |

### 3.5 Cellular Radio Resource Control (RRC) & Power Management
Mobile radios operate under stateful 3GPP Radio Resource Control (RRC) states to conserve battery:
* **RRC_IDLE**: Minimal battery drain. Baseband listens only to paging channels.
* **RRC_CONNECTED**: High power state. Radio maintains active transmission channels.

When Argala is standing by with no traffic, the phone drops to RRC_IDLE. When a client sends a request over Tailscale, the incoming UDP packet causes the cellular tower to page the device, transitioning the radio to RRC_CONNECTED within ~100–250ms. Argala's persistent wake-lock prevents the Android application processor from sleeping, ensuring immediate socket acceptance as soon as the radio transitions.

---

## 4. Cryptographic Engineering & Vault Protocol Specification

The Cryptographic Vault subsystem ([`app/vault/`](file:///c:/Projects/and/app/vault)) serves as Argala's sovereign core.

```text
ActionIntent (JSON Payload from Agent)
                 │
                 ▼
┌────────────────────────────────────────┐
│  1. RFC 8785 Canonical JSON Encoder    │ ── Sorts keys, eliminates whitespace,
└──────────────────┬─────────────────────┘    enforces standard UTF-8 encoding
                   │
                   ▼
┌────────────────────────────────────────┐
│  2. Deterministic SHA-256 Hasher       │ ── Generates 64-character ActionHash
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│  3. HMAC-SHA256 Signer                 │ ── Signs ActionHash with Sovereign Master Key
└──────────────────┬─────────────────────┘
                   │
                   ▼
SignedActionToken { action_hash, signature, nonce, expires_at, signer_node_id }
```

### 4.1 Canonical JSON Serialization (RFC 8785)
In standard JSON implementations, key order is non-deterministic (e.g. `{"a": 1, "b": 2}` vs `{"b": 2, "a": 1}`). Whitespace and float formatting can also vary across languages.

To guarantee that two independent systems compute the exact same hash for identical semantic intent, Argala implements [RFC 8785 (JSON Canonicalization Scheme)](https://datatracker.ietf.org/doc/html/rfc8785) in [`app/vault/crypto.py`](file:///c:/Projects/and/app/vault/crypto.py):
1. Keys are sorted strictly by lexicographical UTF-16 code unit order.
2. No whitespace allowed between keys, colons, or commas (`separators=(',', ':')`).
3. Strings must be valid UTF-8 without unnecessary escape sequences.

```python
# app/vault/crypto.py
def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")
```

### 4.2 Deterministic Intent Hashing
The canonical intent representation binds every dimension of an execution ticket into a single cryptographic digest:

$$\text{CanonicalString} = \text{CanonicalJSON}\left(\left\{
\begin{array}{ll}
\text{"action"}: & \text{intent.action}, \\
\text{"nonce"}: & \text{intent.nonce}, \\
\text{"parameters"}: & \text{intent.parameters}, \\
\text{"requester"}: & \text{intent.requester}, \\
\text{"target"}: & \text{intent.target}, \\
\text{"timestamp"}: & \text{intent.timestamp}
\end{array}
\right\}\right)$$

$$\text{ActionHash} = \text{SHA256}(\text{CanonicalString})$$

### 4.3 HMAC-SHA256 Signature Issuance & Cryptographic Resistance
Argala uses Hash-based Message Authentication Codes (HMAC) with SHA-256:

$$\text{Signature} = \text{HMAC-SHA256}(K_{\text{master}}, \text{ActionHash})$$

### 4.4 Constant-Time Verification & Timing Side-Channel Defense
A critical flaw in naive authentication systems is character-by-character string comparison (`if token == expected_token`). In naive comparisons, the CPU terminates comparison at the first mismatched byte. An attacker measuring round-trip latency at microsecond resolution can progressively guess the signature byte-by-byte.

Argala enforces constant-time comparisons using [`secrets.compare_digest`](file:///c:/Projects/and/app/vault/crypto.py#L65):
```python
# app/vault/crypto.py
def verify_action_signature(action_hash: str, signature: str, secret_key: str) -> bool:
    expected_signature = sign_action_hash(action_hash, secret_key)
    return secrets.compare_digest(expected_signature, signature)
```
At the machine assembly level, `compare_digest` accumulates bitwise XOR differences across the entire length of both strings, ensuring execution time is completely invariant to match position ($\Delta t \approx 0$).

### 4.5 TOCTOU (Time-of-Check to Time-of-Use) Mitigation Proof
* **Attack Vector**: An agent requests human approval for `database.query` with `{"query": "SELECT * FROM public_posts"}`. The operator clicks approve. The agent intercepts the approved token, but alters the payload to `{"query": "DROP TABLE users"}` before submitting it to the production database executor.
* **Argala Cryptographic Proof**:
  1. The token issued during approval contains $\text{ActionHash} = H(\text{"database.query"} \parallel \text{"SELECT * FROM public_posts"} \parallel \dots)$.
  2. When the executor verifies the request, it provides the actual query to be executed.
  3. Argala recalculates $\text{ActionHash}' = H(\text{"database.query"} \parallel \text{"DROP TABLE users"} \parallel \dots)$.
  4. Because SHA-256 is collision-resistant:
     $$\text{ActionHash}' \neq \text{ActionHash}$$
  5. The signature check fails, returning `valid: false` with reason: `Cryptographic hash mismatch: Parameters or target were altered after signing (TOCTOU violation)`.

### 4.6 Anti-Replay Nonce Monotonic Consumption Engine
To guarantee that a valid signature cannot be captured and replayed:
1. Every intent requires a 128-bit random UUIDv4 `nonce`.
2. The verification engine checks SQLite table `used_nonces`.
3. If the nonce exists $\rightarrow$ immediate rejection.
4. If valid, the nonce is inserted atomically inside the verification transaction with its expiration timestamp.
5. Expired nonces are purged periodically by background sweeps.

### 4.7 PBKDF2-HMAC-SHA256 Envelope Encryption & Local Secrets Store
Stored credentials (e.g. GitHub PATs, AWS access keys) are never stored in plaintext. Argala uses envelope encryption:
1. **Key Derivation**:
   $$\text{KEK} = \text{PBKDF2}(\text{Passphrase}, \text{Salt}, \text{iterations}=100,000, \text{prf}=\text{HMAC-SHA256})$$
2. **Authenticated Encryption (Fernet/AES-128-CBC + HMAC-SHA256 or AES-256-GCM)**:
   Plaintext secrets are encrypted with authenticated data envelopes. Even with physical access to `data/argala.db`, the database contents are indecipherable without the master key.

### 4.8 Secretless Outbound API Brokering Architecture
When an external agent needs to interact with a third-party API (e.g. GitHub):
```text
Agent (Laptop)                     Argala Gateway (Phone)                 External (GitHub API)
      │                                       │                                     │
      │── 1. POST /v1/vault/broker ──────────>│                                     │
      │   { secret_id: "github-pat",          │                                     │
      │     url: "api.github.com/...",        │                                     │
      │     headers: { ... } }                │                                     │
      │                                       │── 2. Decrypt secret in RAM          │
      │                                       │── 3. Inject Authorization header    │
      │                                       │── 4. Outbound HTTPS Call ──────────>│
      │                                       │<─ 5. Response ──────────────────────│
      │                                       │── 6. Strip all credentials          │
      │<─ 7. Return Clean JSON ───────────────│                                     │
```
The agent executes authenticated requests against external cloud APIs without ever possessing, seeing, or leaking the raw credentials.

---

## 5. Storage Engine, SQLite WAL Internals & Durable Queue

Argala relies on an embedded SQLite database ([`app/db/database.py`](file:///c:/Projects/and/app/db/database.py)) located at `data/argala.db`.

### 5.1 SQLite Write-Ahead Logging (WAL) Architecture & eMMC Wear Leveling
Traditional rollback-journal databases write changes to the main database file directly, requiring extensive random-write disk seeks. On smartphone eMMC/UFS flash memory, this causes high write amplification and lock contention.

Argala initializes SQLite in **Write-Ahead Logging (WAL) mode**:
* **Read/Write Concurrency**: Writers append sequentially to `argala.db-wal`. Readers read from `argala.db` and the `.db-shm` (shared memory index) simultaneously without blocking writers. Multiple readers execute concurrently with an active write operation.
* **Flash Wear Reduction**: Sequential appends in WAL mode match the block erase cycle of mobile NAND flash storage, maximizing phone battery and hardware lifespan.

### 5.2 Concurrency Pragmas & Lock Contention Optimization
In [`get_db_connection`](file:///c:/Projects/and/app/db/database.py#L14), every connection applies tuned pragmas:
```sql
PRAGMA journal_mode = WAL;      -- WAL concurrency
PRAGMA busy_timeout = 5000;     -- 5000ms spin-wait before SQLITE_BUSY error
PRAGMA synchronous = NORMAL;    -- Syncs to disk only at checkpoints, saving I/O
PRAGMA foreign_keys = ON;       -- Enforces schema integrity
```

### 5.3 Idempotency Deduplication Key Pattern (HTTP 202 vs 200)
Every task submitted to `/v1/jobs` includes an `idempotency_key`. The repository executes an atomic check:
```python
# app/queue/repository.py
cursor.execute("SELECT ... FROM jobs WHERE idempotency_key = ?;", (idempotency_key,))
existing = cursor.fetchone()
if existing:
    return existing_job, False  # HTTP 200 OK (Deduplicated)

cursor.execute("INSERT INTO jobs (...) VALUES (...);")
return new_job, True            # HTTP 202 Accepted (Created)
```
This guarantees distributed callers can safely retry network calls without creating duplicate tasks.

### 5.4 Distributed Worker Lease Protocol & Automatic Crash Recovery
The queue utilizes a lease-claiming protocol in [`claim_next_job`](file:///c:/Projects/and/app/queue/repository.py#L79):
```sql
UPDATE jobs
SET status = 'RUNNING',
    worker_id = :worker_id,
    lease_expires_at = :lease_expires_at,
    updated_at = :now
WHERE id = (
    SELECT id FROM jobs
    WHERE status = 'PENDING'
       OR (status = 'RUNNING' AND lease_expires_at < :now)
    ORDER BY created_at ASC
    LIMIT 1
)
```
* **Lease Timeout**: When worker `edge-worker-01` claims a job, it acquires a 30-second lease (`lease_expires_at = now + 30`).
* **Crash Recovery**: If the worker process is killed by Android low-memory killer (OOM), its lease expires. The subquery detects `(status = 'RUNNING' AND lease_expires_at < now)` and allows another worker to reclaim the abandoned job automatically.

### 5.5 Dead-Letter Queue (DLQ) & Poison Pill Quarantine
If a malformed task causes worker exceptions:
* The exception is recorded in `jobs.error`.
* `retry_count` is incremented.
* If `retry_count >= max_retries` (default: 3), status transitions to `FAILED`.
* The poison pill is quarantined and will never be picked up by workers again, preventing queue starvation.

---

## 6. Cyber-Physical Human-in-the-Loop (HITL) Subsystem

The HITL subsystem ([`app/hitl/`](file:///c:/Projects/and/app/hitl)) provides physical human verification for autonomous actions.

### 6.1 Android Hardware Abstraction Layer (HAL) Bridge via Termux API
Termux runs in standard Android application userspace and cannot directly call Android Java frameworks (`android.hardware.*`).

Argala bridges this boundary via the **Termux API architecture**:
```text
FastAPI (Python) ──Async Subprocess──> termux-vibrate (C binary)
                                              │
                                     Unix Domain Socket
                                              │
                                              ▼
                                    Termux:API (Android APK)
                                              │
                                       Android Binder IPC
                                              │
                                              ▼
                                  Android OS Vibration Service
                                              │
                                              ▼
                                    Physical Haptic Actuator
```

### 6.2 Multi-Modal Physical Actuation
When an action ticket arrives via `POST /v1/approvals/request`:
1. **Haptic Actuation**: Dispatches `termux-vibrate -d 500` (short pulse) or `1200ms` (emergency alarm).
2. **Text-to-Speech (TTS)**: Dispatches `termux-tts-speak "Approval required for action database drop on target production"`. Android's speech synthesis engine reads the action details aloud through the phone's speaker.
3. **Notification Shade**: Dispatches `termux-notification` with priority `high` or `max`, ensuring the notification breaks through Do Not Disturb.

### 6.3 Ticket Lifecycle State Machine & Anti-Zombie TTL Engine
```mermaid
stateDiagram-v2
    [*] --> PENDING: POST /v1/approvals/request (TTL: 120s)
    PENDING --> APPROVED: Operator clicks "Approve" (Signs Token)
    PENDING --> REJECTED: Operator clicks "Reject"
    PENDING --> EXPIRED: System time > expires_at (Auto-Timeout)
    
    APPROVED --> [*]
    REJECTED --> [*]
    EXPIRED --> [*]
```
To eliminate "zombie tickets" (stale tickets approved hours later after context has changed), every ticket enforces an unextendable `expires_at` timestamp (default: 120 seconds). When `time.time() > expires_at`, resolution attempts throw `ValueError: Ticket has expired`.

### 6.4 Embedded Mobile Web Dashboard (Zero-Dependency Dark-Mode PWA)
Hosted at `http://<phone-ip>:8000/approvals` ([`app/hitl/web_ui.py`](file:///c:/Projects/and/app/hitl/web_ui.py)):
* Zero external CSS/JS frameworks (no React, Tailwind, or CDNs required).
* Completely functional offline on the local network.
* Auto-polls `/v1/approvals` every 2.5 seconds.
* Live countdown timers on all pending tickets.
* Includes the global `🚨 KILL SWITCH` button.

---

## 7. Zero-Trust Identity, Scopes & Emergency Kill Switch

The Identity subsystem ([`app/core/identity.py`](file:///c:/Projects/and/app/core/identity.py)) enforces granular capabilities and emergency system-wide quarantine.

### 7.1 Identity-Based Access Control (IBAC) & Scoped Capability Policies
Every authenticated entity is mapped to an explicit identity policy:
* **`admin-console`**: The phone owner and local web console. Possesses wildcard capability `["*"]`.
* **`laptop-agent`**: The developer workstation AI loop. Scoped to:
  `["jobs:submit", "jobs:read", "hitl:request", "hitl:read", "telemetry:read", "vault:verify"]`.
  *Cannot read vault secrets, cannot resolve approval tickets, cannot trigger lockdown.*
* **`cloud-worker`**: Distributed worker nodes. Scoped strictly to:
  `["jobs:read", "jobs:claim", "jobs:complete", "telemetry:read"]`.

### 7.2 Ingress Scope Enforcement Middleware (`require_scope`)
Implemented in [`app/api/deps.py`](file:///c:/Projects/and/app/api/deps.py):
```python
def require_scope(required_scope: str) -> Callable:
    async def dependency(
        x_api_key: Optional[str] = Header(None),
        api_key: Optional[str] = Query(None),
        x_principal_id: Optional[str] = Header(None),
        principal_id: Optional[str] = Query(None),
    ) -> Principal:
        resolved = await get_current_principal(x_api_key, api_key, x_principal_id, principal_id)
        
        # Check active lockdown
        if lockdown_manager.is_locked() and required_scope not in ("admin:unlock", "admin:status"):
            raise HTTPException(status_code=423, detail="EMERGENCY LOCKDOWN ACTIVE")
            
        if not resolved.has_scope(required_scope):
            raise HTTPException(status_code=403, detail="Scope violation")
            
        return resolved
    return dependency
```

### 7.3 The Emergency Kill Switch Protocol (The "Nuclear Option")
When an operator triggers lockdown (`POST /v1/admin/lockdown` or mobile button):
1. **Atomic State Write**: [`lockdown_manager`](file:///c:/Projects/and/app/core/identity.py#L182) switches in-memory state to `EMERGENCY_LOCKDOWN` and updates SQLite table `gateway_state`.
2. **Instant Quarantine**: Any incoming request requiring capability scopes (other than `admin:unlock`) is rejected with **HTTP 423 Locked** at the ingress dependency layer before route execution.
3. **Queue Freeze**: The edge queue worker loop detects `lockdown_manager.is_locked()` and immediately pauses claiming tasks.
4. **Vault Freeze**: Vault signing and secret decryption methods immediately throw `PermissionError`.
5. **Physical Alarm**: The phone vibrates continuously for 1200ms and announces via TTS: *"Warning! Emergency lockdown initiated. All agent capabilities revoked."*
6. **Mobile UI Red Alert**: The web console displays a pulsing red banner and flips the button to **`🔓 RESTORE SYSTEM`**.

---

## 8. Model Context Protocol (MCP) Standard Implementation

Argala exposes its capabilities to modern AI agents (Antigravity IDE, Claude Desktop) via the standardized **Model Context Protocol (MCP)** ([`app/mcp/`](file:///c:/Projects/and/app/mcp)).

### 8.1 Hybrid SSE & JSON-RPC 2.0 Streaming Architecture
```text
Agent Client (IDE)                                    Argala MCP Router (Phone)
       │                                                          │
       │── 1. GET /v1/mcp/sse ───────────────────────────────────>│
       │<─ 2. HTTP 200 text/event-stream (event: endpoint) ──────│
       │      data: /v1/mcp/messages?session_id=<uuid>            │
       │                                                          │
       │── 3. POST /v1/mcp/messages?session_id=<uuid> ───────────>│
       │      {"jsonrpc": "2.0", "method": "tools/list"}          │
       │<─ 4. Stream response or 200 OK result ───────────────────│
```

### 8.2 Registered MCP Tools
1. `android_get_telemetry`: Returns battery level, thermal state, and RAM metrics.
2. `android_ping`: Verifies mesh roundtrip latency.
3. `android_submit_job`: Submits a task to the durable queue.
4. `android_get_job`: Retrieves the status or result of a queued task.

---

## 9. Hardware Lifecycle, Daemonization & Android Kernel Quirks

Running an always-on server on Android requires navigating strict operating system power constraints.

### 9.1 Android Doze Mode Circumvention & Kernel Wake-Lock Management
* **The Problem**: In Android 6.0+, the OS enforces **Doze Mode**. If a device is unplugged and stationary with the screen off, Android suspends network access, defers background jobs, and halts CPU execution.
* **The Solution**: Argala acquires a Linux kernel wake-lock via `termux-wake-lock`. This calls Android's `PowerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "...")`. The CPU continues executing instructions at minimal clock frequency even when the screen is dark.

### 9.2 Seccomp-BPF Syscall Filtering & Bypassing "Bad System Call" (SIGSYS)
* **The Problem**: Android 10+ enforces seccomp-BPF filters on userspace processes. Linux utilities like `pkill` and `pgrep` attempt to read `/proc` process memory using syscalls restricted by Android seccomp (such as `process_vm_readv`), causing the kernel to instantly terminate the process with `SIGSYS` (`Bad system call`).
* **The Solution**: Argala's shutdown and management scripts ([`scripts/stop_gateway.sh`](file:///c:/Projects/and/scripts/stop_gateway.sh)) use safe POSIX process inspection without `pkill`:
  ```bash
  for pid in $(ps -A | grep '[p]ython' | awk '{print $2}'); do
      kill "$pid" 2>/dev/null
  done
  ```

### 9.3 Watchdog Supervisor Loop & Crash Resilience
[`scripts/watchdog.sh`](file:///c:/Projects/and/scripts/watchdog.sh) wraps the server in an infinite recovery loop:
```bash
while true; do
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_FILE" 2>&1
    EXIT_STATUS=$?
    echo "[$(date)] Exited with code $EXIT_STATUS. Restarting in 2s..." >> "$LOG_FILE"
    sleep 2
done
```

### 9.4 Android `BOOT_COMPLETED` Broadcast & Termux:Boot Pipeline
When the phone boots or recovers from power loss:
1. Android broadcast receiver triggers `Termux:Boot`.
2. `~/.termux/boot/start-argala.sh` executes automatically.
3. The script sleeps 10 seconds to allow the baseband radio and Tailscale interface to bind.
4. Acquires `termux-wake-lock`.
5. Spawns `scripts/watchdog.sh` in the background with `nohup`.
6. Speaks aloud: *"Argala sovereign gateway online."*

---

## 10. STRIDE Threat Model & Security Invariants

| STRIDE Category | Threat Description | Attack Path | Argala Countermeasure |
|---|---|---|---|
| **Spoofing** | Rogue agent impersonates admin | Sends unauthenticated requests to `/v1/vault/secrets` | Zero-Trust Principal resolution requires matching master API key. Scoped principals (`laptop-agent`) cannot spoof `admin-console`. |
| **Tampering** | In-flight payload modification | Attacker alters database query after human approved it | RFC 8785 Canonical JSON hashing permanently binds parameters to the signature. Parameter changes invalidate the hash. |
| **Repudiation** | Agent denies submitting an action | Rogue agent claims it never requested high-risk action | Immutable append-only audit ledger (`audit_ledger` table in SQLite) logs timestamp, requester, action, and signature. |
| **Information Disclosure** | Credential theft | Agent dumps memory or inspects environment variables | Secrets in SQLite are encrypted with PBKDF2 envelope encryption. Secretless broker injects credentials on-device; tokens never touch agent RAM. |
| **Denial of Service** | Resource exhaustion / Poison pill | Agent submits endless looping queries | SQLite WAL mode prevents read locking. Queue limits task retries to 3 before isolating tasks in the Dead-Letter Queue (DLQ). |
| **Elevation of Privilege** | Scope breakout | Scoped agent attempts to trigger emergency lockdown | [`require_scope`](file:///c:/Projects/and/app/api/deps.py#L65) dependency inspects principal capability list. Unauthorized scopes return HTTP 403 Forbidden. |

---

## 11. Exhaustive Wire & API Specification

### Administrative & Security Control
* `GET /v1/admin` / `GET /v1/admin/status`
  * **Auth**: Scope `admin:status` (`X-API-Key` or `?api_key=`)
  * **Response**: `200 OK` `{"state": "NORMAL", "is_locked": false, "principals": [...]}`
* `POST /v1/admin/lockdown`
  * **Auth**: Scope `admin:lockdown`
  * **Body**: `{"reason": str, "initiated_by": str}`
  * **Response**: `200 OK` `{"status": "EMERGENCY_LOCKDOWN_ACTIVATED"}`
* `POST /v1/admin/unlock`
  * **Auth**: Scope `admin:unlock`
  * **Body**: `{"cleared_by": str}`
  * **Response**: `200 OK` `{"status": "NORMAL"}`

### Cryptographic Vault & Signer
* `POST /v1/vault/sign`
  * **Auth**: Scope `vault:sign`
  * **Body**: `ActionIntent`
  * **Response**: `200 OK` `SignedActionToken`
* `POST /v1/vault/verify`
  * **Auth**: Scope `vault:verify`
  * **Body**: `{"intent": ActionIntent, "token": SignedActionToken}`
  * **Response**: `200 OK` `{"valid": bool, "reason": str}`
* `POST /v1/vault/broker`
  * **Auth**: Scope `vault:broker`
  * **Body**: `BrokerRequest`
  * **Response**: `200 OK` (Proxied API Response)

### Human-in-the-Loop (HITL)
* `POST /v1/approvals/request`
  * **Auth**: Scope `hitl:request`
  * **Body**: `ApprovalTicketCreate`
  * **Response**: `201 Created` `ApprovalTicket` (Status: `PENDING`)
* `GET /v1/approvals/{ticket_id}`
  * **Auth**: Scope `hitl:read`
  * **Response**: `200 OK` `ApprovalTicket`
* `POST /v1/approvals/{ticket_id}/resolve`
  * **Auth**: Scope `hitl:resolve`
  * **Body**: `{"approved": bool, "resolved_by": str}`
  * **Response**: `200 OK` `ApprovalTicket` (Signed token issued if approved)

### Durable Task Queue
* `POST /v1/jobs`
  * **Auth**: Scope `jobs:submit`
  * **Body**: `JobCreate` (`idempotency_key`, `capability`, `payload`)
  * **Response**: `202 Accepted` (New) / `200 OK` (Deduplicated)
* `GET /v1/jobs/{id}`
  * **Auth**: Scope `jobs:read`
  * **Response**: `200 OK` `JobRecord`

---

## 12. Latency Budgets & Performance Profile

Benchmarked across Samsung Galaxy A6+ (Snapdragon 450, 3GB RAM, Android 10):

| Operation | Typical Latency | Primary Limiting Factor |
|---|---|---|
| WireGuard Mesh Roundtrip (Laptop $\leftrightarrow$ Phone) | 12ms – 35ms | Wi-Fi / LTE RRC State |
| Zero-Trust Ingress Auth & Constant-Time Compare | 0.08ms | CPU (SHA-256 / XOR loop) |
| Canonical JSON Hash (RFC 8785 + SHA-256) | 0.15ms | Python JSON serialization |
| SQLite WAL Ingestion (`POST /v1/jobs`) | 3.2ms – 6.5ms | eMMC flash write |
| Physical Vibration Actuation (`termux-vibrate`) | 45ms – 85ms | Android Binder IPC to HAL |
| TTS Speech Synthesis (`termux-tts-speak`) | 120ms – 250ms | Android TTS audio engine |
| Secretless Outbound Broker (Roundtrip) | 180ms – 450ms | Upstream target API response |
| Emergency Kill Switch Quarantine Enforcement | < 0.1ms | In-memory atomic boolean check |

---

*Argala is fully open, hardened, and verified for sovereign autonomous AI engineering.*
