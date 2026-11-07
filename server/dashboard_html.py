"""HTML Dashboard template for Ship Court."""

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ship Court — Adversarial Release Arena</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --text: #f3f4f6;
      --muted: #9ca3af;
      --prosecution: #ef4444;
      --defense: #10b981;
      --accent: #3b82f6;
      --gold: #f59e0b;
      --purple: #8b5cf6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      padding: 24px;
      line-height: 1.5;
    }
    .container { max-width: 1180px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .title-group h1 { font-size: 26px; font-weight: 800; display: flex; align-items: center; gap: 10px; }
    .title-group p { color: var(--muted); font-size: 14px; margin-top: 4px; }
    .badge {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 9999px;
      letter-spacing: 0.5px;
    }
    .badge-live { background: #064e3b; color: #34d399; border: 1px solid #059669; }
    .badge-gold { background: #78350f; color: #fbbf24; border: 1px solid #d97706; }
    
    .keys-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .key-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      position: relative;
    }
    .key-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .key-title { font-weight: 700; font-size: 14px; }
    .key-code { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #60a5fa; background: #1e293b; padding: 3px 8px; border-radius: 6px; word-break: break-all; }
    .key-role { font-size: 12px; color: var(--muted); margin-top: 6px; }
    
    .court-layout { display: grid; grid-template-columns: 1fr; gap: 24px; }
    @media(min-width: 900px) {
      .court-layout { grid-template-columns: 420px 1fr; }
    }
    
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
    }
    .panel h2 { font-size: 16px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
    
    .form-group { margin-bottom: 14px; }
    label { display: block; font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; }
    input, textarea, select {
      width: 100%;
      background: #0b0f19;
      border: 1px solid #374151;
      border-radius: 8px;
      color: #fff;
      padding: 10px 12px;
      font-size: 14px;
      font-family: inherit;
    }
    input:focus, textarea:focus { outline: none; border-color: var(--accent); }
    .preset-btn {
      background: #1f2937;
      color: #d1d5db;
      border: 1px solid #374151;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      margin-right: 6px;
      margin-bottom: 6px;
      transition: all 0.2s;
    }
    .preset-btn:hover { background: #374151; color: #fff; }
    
    .btn-run {
      width: 100%;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #fff;
      font-weight: 700;
      padding: 12px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
      transition: all 0.2s;
    }
    .btn-run:hover { opacity: 0.95; transform: translateY(-1px); }
    
    .transcript {
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: 580px;
      overflow-y: auto;
      padding-right: 6px;
    }
    .msg {
      background: #0b0f19;
      border-radius: 10px;
      padding: 14px;
      border-left: 4px solid var(--accent);
      font-size: 13px;
    }
    .msg-clerk { border-left-color: #3b82f6; }
    .msg-historian { border-left-color: #f59e0b; }
    .msg-prosecutor { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
    .msg-defender { border-left-color: #10b981; background: rgba(16, 185, 129, 0.05); }
    .msg-rollback { border-left-color: #8b5cf6; }
    .msg-judge { border-left-color: #ec4899; background: rgba(236, 72, 153, 0.05); }
    
    .msg-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      font-weight: 700;
      font-size: 12px;
    }
    .msg-content { white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #e5e7eb; }
    
    .power-meter {
      background: #1f2937;
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .meter-bar {
      height: 14px;
      background: #374151;
      border-radius: 7px;
      overflow: hidden;
      display: flex;
      margin: 10px 0;
    }
    .meter-prosecution { background: var(--prosecution); transition: width 0.5s; }
    .meter-defense { background: var(--defense); transition: width 0.5s; }
    .meter-labels { display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; }
    
    #loading { display: none; text-align: center; padding: 20px; color: var(--accent); font-weight: 600; }
    .spinner {
      display: inline-block;
      width: 20px;
      height: 20px;
      border: 3px solid rgba(255,255,255,.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 1s ease-in-out infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .tag-live {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      background: #064e3b;
      color: #34d399;
      border: 1px solid #059669;
      margin-left: 8px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="title-group">
        <h1>⚖️ SHIP COURT <span class="badge badge-gold">Track 01: Best Business Workflow</span></h1>
        <p>No Deploy Survives Cross-Examination — Multi-Agent Adversarial Release Arena</p>
      </div>
      <div>
        <span class="badge badge-live">● 100% Dynamic Inference Active</span>
      </div>
    </header>

    <!-- Dynamic API Keys Grid loaded live via /api/keys -->
    <div class="keys-grid" id="keys-grid">
      <div style="grid-column: 1 / -1; padding: 12px; background: var(--card-bg); border-radius: 8px; color: var(--muted); font-size: 13px;">
        Loading live connected LLM inference providers...
      </div>
    </div>

    <!-- Main Court Layout -->
    <div class="court-layout">
      <!-- Input Panel -->
      <div class="panel">
        <h2>📑 Docket Case on Trial</h2>
        
        <div class="form-group">
          <label>Quick Fill Shortcuts</label>
          <div>
            <button class="preset-btn" onclick="setPreset(1)">1. Dynamic Pricing Rollout</button>
            <button class="preset-btn" onclick="setPreset(2)">2. Drop user_sessions Table</button>
            <button class="preset-btn" onclick="setPreset(3)">3. Redis Caching Layer</button>
          </div>
        </div>

        <div class="form-group">
          <label>Proposed Deployment / Change Petition</label>
          <textarea id="task_desc" rows="4" placeholder="Type ANY deployment petition, pull request, or architectural change to put on trial..."></textarea>
        </div>

        <div class="form-group">
          <label>Repository & PR Target</label>
          <input type="text" id="repo_target" placeholder="e.g. acme/shop (PR #482)">
        </div>

        <div class="form-group">
          <label>Presiding Human Judge (Exclusive Gate)</label>
          <input type="text" id="judge_name" placeholder="Enter human judge name (e.g. Priya)" value="Priya">
        </div>

        <button class="btn-run" id="btn-run" onclick="runTrial()">
          <span>⚔️ Convene Courtroom & Run Trial</span>
        </button>

        <div id="error-toast" style="display:none; margin-top:12px; padding:10px 14px; background:#450a0a; border:1px solid #dc2626; border-radius:8px; color:#fca5a5; font-size:12px;"></div>

        <div id="loading">
          <div class="spinner"></div>
          <p style="margin-top: 8px;" id="loading-msg">Court in session... Cross-examining petition across 3 live LLM agents...</p>
        </div>

        <div style="margin-top: 20px; padding: 12px; background: #1f2937; border-radius: 8px; font-size: 12px; color: var(--muted);">
          <strong>Governance Invariant:</strong> AI courtroom agents cross-examine evidence and compute leverage power scores, but CANNOT self-approve deployments. Only the human gatekeeper holds binding signature authority.
        </div>
      </div>

      <!-- Live Adversarial Arena -->
      <div class="panel">
        <h2>🏛️ Adversarial Arena & Verdict Output</h2>

        <!-- Power Meter -->
        <div class="power-meter" id="power-box" style="display:none;">
          <div class="meter-labels">
            <span style="color:var(--prosecution);" id="pros-label">Prosecution Power: 0%</span>
            <span style="color:#fbbf24;" id="winner-label">STANDSTILL</span>
            <span style="color:var(--defense);" id="def-label">Defense Power: 0%</span>
          </div>
          <div class="meter-bar">
            <div class="meter-prosecution" id="pros-bar" style="width: 50%;"></div>
            <div class="meter-defense" id="def-bar" style="width: 50%;"></div>
          </div>
          <p id="rationale-text" style="font-size: 12px; color: #d1d5db; margin-top: 6px;"></p>
        </div>

        <!-- Dedicated Conditions / Verdict Card -->
        <div id="verdict-box" style="display:none; margin-bottom: 16px;"></div>

        <!-- Transcript -->
        <div class="transcript" id="transcript">
          <div class="msg msg-clerk">
            <div class="msg-header">
              <span style="color:#60a5fa;">@court-clerk (Bailiff)</span>
              <span>STANDBY</span>
            </div>
            <div class="msg-content">Welcome to Ship Court. Type ANY deployment petition into the text box and click 'Convene Courtroom & Run Trial'. Every change undergoes live unscripted adversarial cross-examination.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    async function loadApiKeys() {
      try {
        const resp = await fetch('/api/keys');
        if (!resp.ok) return;
        const keys = await resp.json();
        const grid = document.getElementById('keys-grid');
        grid.innerHTML = '';
        for (const [k, v] of Object.entries(keys)) {
          const div = document.createElement('div');
          div.className = 'key-card';
          div.innerHTML = `
            <div class="key-header">
              <span class="key-title">${escapeHtml(v.name || k)}</span>
              <span class="badge ${v.status === 'LIVE' ? 'badge-live' : 'badge-gold'}">${escapeHtml(v.status || 'INACTIVE')}</span>
            </div>
            <div class="key-code">${escapeHtml(v.env_var)}: ${escapeHtml(v.masked)}</div>
            <div class="key-role">Model: <strong>${escapeHtml(v.default_model || 'Standard')}</strong><br>Function: ${escapeHtml(v.role)}</div>
          `;
          grid.appendChild(div);
        }
      } catch (err) {
        console.error('Failed to load keys dynamically:', err);
      }
    }
    window.addEventListener('DOMContentLoaded', loadApiKeys);

    function setPreset(n) {
      const desc = document.getElementById('task_desc');
      hideError();
      if (n === 1) {
        desc.value = "Dynamic checkout pricing rollout";
      } else if (n === 2) {
        desc.value = "Drop database table user_sessions during active peak hours without backup";
      } else if (n === 3) {
        desc.value = "Add Redis caching to product search queries with 60s TTL and automatic fallback to SQL database";
      }
    }

    function showError(msg) {
      const toast = document.getElementById('error-toast');
      toast.style.display = 'block';
      toast.innerText = msg;
    }

    function hideError() {
      const toast = document.getElementById('error-toast');
      toast.style.display = 'none';
      toast.innerText = '';
    }

    async function runTrial() {
      hideError();
      const task = document.getElementById('task_desc').value;
      const judge = document.getElementById('judge_name').value;
      const repo = document.getElementById('repo_target').value;
      const btn = document.getElementById('btn-run');
      const loader = document.getElementById('loading');
      const transcript = document.getElementById('transcript');
      const powerBox = document.getElementById('power-box');
      const verdictBox = document.getElementById('verdict-box');

      if (!task || !task.trim()) {
        showError('Please enter a change or deployment petition to put on trial.');
        return;
      }

      btn.disabled = true;
      btn.style.opacity = '0.5';
      loader.style.display = 'block';
      document.getElementById('loading-msg').innerText = 'Court in session... Cross-examining petition across 3 live LLM agents...';

      try {
        const resp = await fetch('/api/debate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task: task.trim(),
            judge: judge ? judge.trim() : 'Release-Judge',
            repo: repo ? repo.trim() : 'unspecified-repo'
          })
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.error || ('Server returned HTTP ' + resp.status));
        }

        // Update Power Bar
        const pScore = data.prosecution_power || 0;
        const dScore = data.defense_power || 0;
        const total = Math.max(pScore + dScore, 1);
        const pPct = Math.round((pScore / total) * 100);
        const dPct = 100 - pPct;

        powerBox.style.display = 'block';
        document.getElementById('pros-bar').style.width = pPct + '%';
        document.getElementById('def-bar').style.width = dPct + '%';
        document.getElementById('pros-label').innerText = 'Prosecution: ' + pScore + ' pts (' + pPct + '%)';
        document.getElementById('def-label').innerText = 'Defense: ' + dScore + ' pts (' + dPct + '%)';
        document.getElementById('winner-label').innerText = 'RULING: ' + (data.priority || data.verdict);
        document.getElementById('rationale-text').innerText = 'Dominant Side: ' + data.winner + '. Verdict: ' + data.verdict;

        // Populate Conditions Box
        verdictBox.style.display = 'block';
        let conditionsHtml = '';
        if (data.conditions && data.conditions.length > 0) {
          conditionsHtml = data.conditions.map((c, idx) => `
            <li style="margin-bottom: 8px; display: flex; align-items: flex-start; gap: 8px;">
              <span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700; white-space: nowrap;">REQ ${idx + 1}</span>
              <span style="color: #f3f4f6; font-size: 13px;">${escapeHtml(c)}</span>
            </li>
          `).join('');
        } else {
          conditionsHtml = '<li style="color: #9ca3af; font-size: 12px;">No explicit operational conditions required by the Judge.</li>';
        }

        let tasksHtml = '';
        if (data.tasks && data.tasks.length > 0) {
          tasksHtml = `
            <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
              <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #9ca3af; letter-spacing: 0.5px;">📋 Assigned Court Action Items:</span>
              <ul style="list-style: disc; padding-left: 20px; margin-top: 6px;">
                ${data.tasks.map(t => `<li style="font-size: 12px; color: #e5e7eb; margin-bottom: 4px;">${escapeHtml(t)}</li>`).join('')}
              </ul>
            </div>
          `;
        }

        const effectiveJudge = data.judge || judge || 'Release-Judge';
        const vNorm = (data.verdict || '').toUpperCase();

        if (vNorm.includes('COND')) {
          verdictBox.innerHTML = `
            <div style="background: #1e1b10; border: 2px solid #d97706; border-radius: 10px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #fbbf24; font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 6px;">
                  ⚡ MANDATORY OPERATIONAL CONDITIONS FOR ROLLOUT
                </span>
                <span class="badge badge-gold">CONDITIONS BINDING</span>
              </div>
              <p style="font-size: 12px; color: #d1d5db; margin-bottom: 12px;">
                The Court ruled that deployment may proceed <strong>ONLY</strong> if the following mandatory operational guardrails are satisfied and signed by human gatekeeper <strong>@${escapeHtml(effectiveJudge)}</strong>:
              </p>
              <ul style="list-style: none; padding-left: 0; margin-bottom: 14px;">
                ${conditionsHtml}
              </ul>
              ${tasksHtml}
              <div style="margin-top: 12px; background: rgba(217, 119, 6, 0.15); border: 1px dashed #d97706; border-radius: 6px; padding: 10px; font-size: 11px; color: #fbbf24;">
                ⚖️ <strong>Exclusive Authority Lock:</strong> AI agents cannot self-ship. Only @${escapeHtml(effectiveJudge)} can authorize canary traffic ramp.
              </div>
            </div>
          `;
        } else if (vNorm.includes('BLOCK') || vNorm.includes('REJECT') || vNorm.includes('DENI') || vNorm.includes('DENY')) {
          verdictBox.innerHTML = `
            <div style="background: #200d0d; border: 2px solid #ef4444; border-radius: 10px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #ef4444; font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 6px;">
                  🚫 DEPLOYMENT STRICTLY BLOCKED BY SHIP COURT
                </span>
                <span class="badge" style="background:#7f1d1d; color:#fca5a5; border:1px solid #b91c1c;">BLOCK RULING</span>
              </div>
              <p style="font-size: 12px; color: #fca5a5; margin-bottom: 12px;">
                Catastrophic or unmitigated risks identified during cross-examination. Deployment is blocked under penalty of governance violation.
              </p>
              <ul style="list-style: none; padding-left: 0;">
                ${conditionsHtml}
              </ul>
              ${tasksHtml}
            </div>
          `;
        } else if (vNorm.includes('APPROV') || vNorm.includes('PASS') || vNorm.includes('SHIP')) {
          verdictBox.innerHTML = `
            <div style="background: #062b1e; border: 2px solid #10b981; border-radius: 10px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #34d399; font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 6px;">
                  ✅ DEPLOYMENT APPROVED BY SHIP COURT
                </span>
                <span class="badge badge-live">APPROVED</span>
              </div>
              <p style="font-size: 12px; color: #a7f3d0; margin-bottom: 10px;">
                The Defense decisively mitigated all prosecutor objections. Standard rollout approved.
              </p>
              <ul style="list-style: none; padding-left: 0;">
                ${conditionsHtml}
              </ul>
              ${tasksHtml}
            </div>
          `;
        } else {
          verdictBox.innerHTML = `
            <div style="background: #251b08; border: 2px solid #eab308; border-radius: 10px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #facc15; font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 6px;">
                  ⚠️ ARBITRATION REQUIRED / INCONCLUSIVE
                </span>
                <span class="badge badge-gold">${escapeHtml(data.verdict || 'UNKNOWN')}</span>
              </div>
              <p style="font-size: 12px; color: #fef08a; margin-bottom: 10px;">
                The courtroom debate requires direct human magistrate arbitration.
              </p>
              <ul style="list-style: none; padding-left: 0;">
                ${conditionsHtml}
              </ul>
              ${tasksHtml}
            </div>
          `;
        }

        // Populate Transcript with Live Telemetry Badges
        transcript.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(m => {
            const div = document.createElement('div');
            let senderClass = 'msg-clerk';
            let color = '#60a5fa';
            if (m.sender.includes('historian')) { senderClass = 'msg-historian'; color = '#f59e0b'; }
            else if (m.sender.includes('prosecutor')) { senderClass = 'msg-prosecutor'; color = '#ef4444'; }
            else if (m.sender.includes('defender')) { senderClass = 'msg-defender'; color = '#10b981'; }
            else if (m.sender.includes('rollback')) { senderClass = 'msg-rollback'; color = '#8b5cf6'; }
            else if (m.sender.includes('judge')) { senderClass = 'msg-judge'; color = '#ec4899'; }

            const badgeTag = m.is_live
              ? '<span class="tag-live">● LIVE LLM (qwen3.8-27b)</span>'
              : '';

            div.className = 'msg ' + senderClass;
            div.innerHTML = `
              <div class="msg-header">
                <div>
                  <span style="color:${color};">@${m.sender}</span>
                  ${badgeTag}
                </div>
                <span style="color:#9ca3af; font-size:11px;">${new Date(m.timestamp * 1000).toLocaleTimeString()}</span>
              </div>
              <div class="msg-content">${escapeHtml(m.content)}</div>
            `;
            transcript.appendChild(div);
          });
        }
      } catch (err) {
        showError('Courtroom Execution Error: ' + err.message + '. Ensure the Ship Court backend daemon is active on port 8080.');
      } finally {
        btn.disabled = false;
        btn.style.opacity = '1';
        loader.style.display = 'none';
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
  </script>
</body>
</html>
"""
