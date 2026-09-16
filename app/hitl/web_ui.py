"""
Embedded Mobile Web Console for Human-in-the-Loop Approvals & Emergency Kill Switch.
Zero-dependency, dark-mode, responsive single-page dashboard.
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Argala - Sovereign Control Console</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-bright: #f0f6fc;
      --primary: #58a6ff;
      --success: #238636;
      --danger: #da3633;
      --warning: #d29922;
      --critical: #f85149;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 16px; max-width: 600px; margin: 0 auto; line-height: 1.5; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
    h1 { font-size: 1.25rem; color: var(--text-bright); display: flex; align-items: center; gap: 8px; }
    .header-actions { display: flex; align-items: center; gap: 8px; }
    .status-pill { font-size: 0.75rem; padding: 3px 8px; border-radius: 12px; background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid rgba(63, 185, 80, 0.4); }
    
    /* Emergency Kill Switch Button */
    .btn-panic { background: #da3633; color: #ffffff; padding: 6px 12px; font-size: 0.75rem; font-weight: 700; border-radius: 6px; border: 1px solid #f85149; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 4px; }
    .btn-panic:active { transform: scale(0.96); filter: brightness(0.9); }
    .btn-restore { background: #238636; border-color: #3fb950; color: #ffffff; }

    /* Lockdown Alert Banner */
    #lockdown-banner { display: none; background: rgba(218, 54, 51, 0.2); border: 2px solid var(--critical); border-radius: 8px; padding: 12px; margin-bottom: 16px; color: #ff7b72; font-weight: 600; text-align: center; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }

    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: transform 0.1s; }
    .card.pending { border-color: var(--primary); box-shadow: 0 0 12px rgba(88, 166, 255, 0.2); }
    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .action-title { font-size: 1.05rem; font-weight: 600; color: var(--text-bright); }
    .badge { font-size: 0.7rem; font-weight: bold; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
    .badge-CRITICAL { background: rgba(248, 81, 73, 0.2); color: var(--critical); border: 1px solid var(--critical); }
    .badge-HIGH { background: rgba(210, 153, 34, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    .badge-MEDIUM { background: rgba(88, 166, 255, 0.2); color: var(--primary); border: 1px solid var(--primary); }
    .badge-LOW { background: rgba(59, 185, 80, 0.2); color: #3fb950; border: 1px solid #3fb950; }
    .summary { font-size: 0.9rem; color: #8b949e; margin-bottom: 12px; }
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.8rem; background: #0d1117; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; border: 1px solid #21262d; }
    .meta-item span { color: #8b949e; }
    pre { background: #040d1a; padding: 10px; border-radius: 6px; font-size: 0.75rem; color: #79c0ff; overflow-x: auto; margin-bottom: 14px; max-height: 120px; border: 1px solid #1f2937; }
    .btn-row { display: grid; grid-template-columns: 2fr 1fr; gap: 10px; }
    button { padding: 12px; font-size: 0.95rem; font-weight: 600; border-radius: 6px; border: none; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 6px; }
    .btn-approve { background: var(--success); color: #ffffff; }
    .btn-approve:active { background: #2ea043; }
    .btn-reject { background: #21262d; color: var(--critical); border: 1px solid var(--border); }
    .btn-reject:active { background: #30363d; }
    .empty-state { text-align: center; padding: 40px 20px; color: #8b949e; font-size: 0.95rem; }
    .countdown { font-size: 0.75rem; color: #8b949e; text-align: right; margin-top: 6px; }
  </style>
</head>
<body>
  <header>
    <h1>🛡️ Argala</h1>
    <div class="header-actions">
      <button id="panic-btn" class="btn-panic" onclick="toggleKillSwitch()">🚨 KILL SWITCH</button>
      <div class="status-pill" id="conn-status">Connected</div>
    </div>
  </header>

  <div id="lockdown-banner">
    🚨 EMERGENCY LOCKDOWN ACTIVE<br>
    <span style="font-size: 0.8rem; font-weight: normal;">All agent access has been revoked and the vault is locked.</span>
  </div>

  <main id="tickets-container">
    <div class="empty-state">Loading sovereign console...</div>
  </main>

  <script>
    const API_KEY = "argala-dev-key-change-me";

    let isLockedDown = false;

    async function checkAdminStatus() {
      try {
        const resp = await fetch("/v1/admin/status", {
          headers: { "X-API-Key": API_KEY }
        });
        if (resp.ok) {
          const data = await resp.json();
          isLockedDown = data.is_locked;
          updateLockdownUI(data);
        }
      } catch (err) {
        console.warn("Could not check admin status", err);
      }
    }

    function updateLockdownUI(data) {
      const banner = document.getElementById("lockdown-banner");
      const panicBtn = document.getElementById("panic-btn");
      if (data.is_locked) {
        banner.style.display = "block";
        panicBtn.textContent = "🔓 RESTORE SYSTEM";
        panicBtn.className = "btn-panic btn-restore";
      } else {
        banner.style.display = "none";
        panicBtn.textContent = "🚨 KILL SWITCH";
        panicBtn.className = "btn-panic";
      }
    }

    async function toggleKillSwitch() {
      if (!isLockedDown) {
        if (!confirm("🚨 ACTIVATE EMERGENCY LOCKDOWN?\\n\\nThis will instantly revoke all AI agent credentials, halt queued jobs, and freeze the sovereign vault.")) {
          return;
        }
        try {
          const resp = await fetch("/v1/admin/lockdown", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-API-Key": API_KEY
            },
            body: JSON.stringify({ reason: "Emergency kill switch pressed on mobile web console", initiated_by: "mobile-touch" })
          });
          if (resp.ok) {
            await checkAdminStatus();
            await loadTickets();
          } else {
            alert("Failed to initiate lockdown.");
          }
        } catch (err) {
          alert("Error contacting gateway: " + err);
        }
      } else {
        if (!confirm("🔓 DISARM EMERGENCY LOCKDOWN?\\n\\nThis will restore normal operational status and re-enable capability routing.")) {
          return;
        }
        try {
          const resp = await fetch("/v1/admin/unlock", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-API-Key": API_KEY
            },
            body: JSON.stringify({ cleared_by: "mobile-touch" })
          });
          if (resp.ok) {
            await checkAdminStatus();
            await loadTickets();
          } else {
            alert("Failed to disarm lockdown.");
          }
        } catch (err) {
          alert("Error contacting gateway: " + err);
        }
      }
    }

    async function loadTickets() {
      try {
        const resp = await fetch("/v1/approvals", {
          headers: { "X-API-Key": API_KEY }
        });
        if (!resp.ok) throw new Error("Failed to fetch tickets");
        const data = await resp.json();
        renderTickets(data.tickets);
        document.getElementById("conn-status").textContent = isLockedDown ? "Quarantined" : "Connected";
        document.getElementById("conn-status").style.color = isLockedDown ? "#f85149" : "#3fb950";
      } catch (err) {
        document.getElementById("conn-status").textContent = "Offline";
        document.getElementById("conn-status").style.color = "#f85149";
      }
    }

    function renderTickets(tickets) {
      const container = document.getElementById("tickets-container");
      if (!tickets || tickets.length === 0) {
        container.innerHTML = `<div class="empty-state">✨ No pending approvals.<br><span style="font-size:0.8rem">Edge gateway is standing by.</span></div>`;
        return;
      }

      container.innerHTML = tickets.map(t => {
        const isPending = t.status === "PENDING";
        const timeLeft = Math.max(0, Math.round(t.expires_at - (Date.now() / 1000)));

        return `
          <div class="card ${isPending ? 'pending' : ''}">
            <div class="card-header">
              <div>
                <div class="action-title">${t.action}</div>
                <div style="font-size:0.75rem; color:#8b949e">Target: ${t.target}</div>
              </div>
              <span class="badge badge-${t.risk_level}">${t.risk_level}</span>
            </div>
            <div class="summary">${t.summary}</div>
            <div class="meta-grid">
              <div class="meta-item"><span>Requester:</span> ${t.requester}</div>
              <div class="meta-item"><span>Status:</span> <b>${t.status}</b></div>
            </div>
            <pre>${JSON.stringify(t.parameters, null, 2)}</pre>
            ${isPending ? `
              <div class="btn-row">
                <button class="btn-approve" onclick="resolveTicket('${t.id}', true)">✓ Approve & Sign</button>
                <button class="btn-reject" onclick="resolveTicket('${t.id}', false)">✗ Reject</button>
              </div>
              <div class="countdown">Expires in: ${timeLeft}s</div>
            ` : `
              <div style="font-size:0.8rem; color:#8b949e; text-align:center">
                Resolved by: <b>${t.resolved_by || 'system'}</b> at ${new Date(t.resolved_at * 1000).toLocaleTimeString()}
              </div>
            `}
          </div>
        `;
      }).join("");
    }

    async function resolveTicket(ticketId, approved) {
      try {
        const resp = await fetch(`/v1/approvals/${ticketId}/resolve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
          },
          body: JSON.stringify({ approved: approved, resolved_by: "mobile-touch" })
        });
        if (resp.ok) {
          loadTickets();
        } else {
          const err = await resp.json();
          alert("Error: " + (err.detail || "Action failed"));
        }
      } catch (err) {
        alert("Failed to resolve: " + err);
      }
    }

    // Initial load and periodic polling
    checkAdminStatus();
    loadTickets();
    setInterval(() => {
      checkAdminStatus();
      loadTickets();
    }, 2500);
  </script>
</body>
</html>
"""
