document.addEventListener("DOMContentLoaded", () => {
    const clientIdInput = document.getElementById("client-id-input");
    const nodeSelect = document.getElementById("node-select");
    const endpointInput = document.getElementById("endpoint-input");

    const btnSingle = document.getElementById("btn-send-single");
    const btnBurst = document.getElementById("btn-send-burst");
    const btnScan = document.getElementById("btn-scan-abuse");
    const btnOutage = document.getElementById("btn-toggle-outage");
    const btnSync = document.getElementById("btn-trigger-sync");

    const sliderCap = document.getElementById("slider-cap");
    const sliderRefill = document.getElementById("slider-refill");
    const valCap = document.getElementById("val-cap");
    const valRefill = document.getElementById("val-refill");

    const nodesContainer = document.getElementById("nodes-container");
    const storageBadge = document.getElementById("storage-badge");
    const storageContent = document.getElementById("storage-content");
    const storageStatusPill = document.getElementById("storage-status-pill");
    const latestResponseJson = document.getElementById("latest-response-json");
    const logStream = document.getElementById("log-stream");

    let storageDown = false;

    // Refresh cluster status
    async function fetchClusterStatus() {
        try {
            const res = await fetch("/api/v1/cluster/status");
            const data = await res.json();
            renderClusterNodes(data.nodes);
            
            storageDown = !data.storage_healthy;
            updateStorageUI(data.storage_healthy);
        } catch (err) {
            console.error("Failed to fetch cluster status", err);
        }
    }

    function updateStorageUI(healthy) {
        if (healthy) {
            storageBadge.textContent = "HEALTHY";
            storageBadge.className = "badge closed";
            storageStatusPill.innerHTML = '<span class="status-dot green"></span> Storage: Online';
        } else {
            storageBadge.textContent = "OUTAGE (PARTITION)";
            storageBadge.className = "badge open";
            storageStatusPill.innerHTML = '<span class="status-dot red"></span> Storage: DOWN (Degraded Mode)';
        }
    }

    function renderClusterNodes(nodes) {
        nodesContainer.innerHTML = "";
        nodes.forEach(node => {
            const nodeEl = document.createElement("div");
            nodeEl.className = "node-box";
            
            const isCBClosed = node.circuit_breaker_state === "CLOSED";
            const cbBadgeClass = isCBClosed ? "badge closed" : "badge open";

            nodeEl.innerHTML = `
                <div class="node-header">
                    <span class="node-title">🖥️ ${node.node_id}</span>
                    <span class="${cbBadgeClass}">CB: ${node.circuit_breaker_state}</span>
                </div>
                <div class="bucket-status">
                    <div>Failures: <strong>${node.consecutive_failures}</strong></div>
                    <div>Active Buckets: <strong>${node.active_buckets}</strong></div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${isCBClosed ? '100%' : '30%'}"></div>
                    </div>
                </div>
            `;
            nodesContainer.appendChild(nodeEl);
        });
    }

    async function sendRequest(statusCode = 200, tokens = 1.0) {
        const payload = {
            client_id: clientIdInput.value.trim() || "client-alpha",
            endpoint: endpointInput.value.trim() || "/api/v1/resource",
            status_code: statusCode,
            tokens_requested: tokens,
            node_id: nodeSelect.value || null
        };

        try {
            const res = await fetch("/api/v1/request", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            latestResponseJson.textContent = JSON.stringify(data, null, 2);
            
            addLogEntry(data);
            fetchClusterStatus();
        } catch (err) {
            console.error("API Request Error", err);
        }
    }

    function addLogEntry(data) {
        const entry = document.createElement("div");
        let typeClass = "allowed";
        if (!data.allowed) {
            typeClass = data.tier === "BLOCKED" ? "abuse" : "throttled";
        }
        
        entry.className = `log-entry ${typeClass}`;
        const timeStr = new Date().toLocaleTimeString();
        entry.innerHTML = `
            <strong>[${timeStr}] ${data.node_id}</strong>: 
            Status ${data.status_code} | Mode: <em>${data.execution_mode}</em> | Tier: ${data.tier}
            <br><small>Headers: Limit=${data.headers['X-RateLimit-Limit']}, Rem=${data.headers['X-RateLimit-Remaining']}, Reset=${data.headers['X-RateLimit-Reset']}s</small>
        `;

        logStream.insertBefore(entry, logStream.firstChild);
    }

    // Event Listeners
    btnSingle.addEventListener("click", () => sendRequest(200, 1.0));

    btnBurst.addEventListener("click", async () => {
        for (let i = 0; i < 15; i++) {
            await sendRequest(200, 1.0);
        }
    });

    btnScan.addEventListener("click", async () => {
        for (let i = 0; i < 6; i++) {
            await sendRequest(404, 1.0);
        }
    });

    btnOutage.addEventListener("click", async () => {
        storageDown = !storageDown;
        await fetch("/api/v1/sim/outage", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ storage_down: storageDown })
        });
        fetchClusterStatus();
    });

    btnSync.addEventListener("click", async () => {
        const res = await fetch("/api/v1/sync", { method: "POST" });
        const data = await res.json();
        latestResponseJson.textContent = JSON.stringify(data, null, 2);
        fetchClusterStatus();
    });

    sliderCap.addEventListener("input", (e) => {
        valCap.textContent = e.target.value;
        updateConfig();
    });

    sliderRefill.addEventListener("input", (e) => {
        valRefill.textContent = e.target.value;
        updateConfig();
    });

    async function updateConfig() {
        await fetch("/api/v1/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                capacity: parseFloat(sliderCap.value),
                refill_rate: parseFloat(sliderRefill.value)
            })
        });
    }

    // Initial load & periodic poll
    fetchClusterStatus();
    setInterval(fetchClusterStatus, 3000);
});
