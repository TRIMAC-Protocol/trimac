/**
 * TRIMAC 旗艦門戶 - 艦隊狀態模組
 * 模擬即時心跳與健康狀態更新
 */

(function() {
    'use strict';

    const fleetData = {
        'orchestrator-a': { name: 'ORCHESTRATOR-A', role: '中央調度中樞 A', spec: '端口 9901 | 任務分解技能注入', status: 'online', baseHeartbeat: 4, baseHash: 15428 },
        'orchestrator-b': { name: 'ORCHESTRATOR-B', role: '中央調度中樞 B (熱備援)', spec: '端口 9902 | 10s TTL 租約接管', status: 'standby', baseHeartbeat: 9, baseHash: 15420 },
        'datacore': { name: 'DATACORE', role: '數據核心', spec: 'PostgreSQL 16 + pgvector | MCP 8080', status: 'online', baseHeartbeat: 2, baseHash: 15421 },
        'worker-01': { name: 'WORKER-01', role: '純執行工 1', spec: '無狀態 | 零技能 | 端口 9903', status: 'online', baseHeartbeat: 1, baseHash: 15428 },
        'worker-02': { name: 'WORKER-02', role: '純執行工 2', spec: '無狀態 | 零技能 | 端口 9904', status: 'online', baseHeartbeat: 4, baseHash: 15425 },
        'worker-03': { name: 'WORKER-03', role: '純執行工 3', spec: '無狀態 | 零技能 | 端口 9905', status: 'online', baseHeartbeat: 9, baseHash: 15428 },
        'auditor': { name: 'AUDITOR', role: '獨立審計員 / 錦衣衛', spec: '內部 | 全域獨立監督權', status: 'online', baseHeartbeat: 0, baseHash: 15422 },
        'supervisor': { name: 'SUPERVISOR', role: 'SRE 監督守護進程', spec: '內部 | 3秒巡檢週期', status: 'online', baseHeartbeat: 1, baseHash: 15429 }
    };

    let updateInterval = null;
    let hashCounter = 0;

    function initFleetStatus() {
        const grid = document.getElementById('fleet-grid');
        if (!grid) return;

        // 初始渲染
        renderFleet(grid);
        
        // 開始模擬更新
        startSimulation();
        
        // 頁面可見性變更時暫停/恢復
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stopSimulation();
            } else {
                startSimulation();
            }
        });
    }

    function renderFleet(grid) {
        grid.innerHTML = Object.entries(fleetData).map(([key, node]) => `
            <article class="fleet-card reveal" data-node="${key}">
                <div class="fleet-status ${node.status}"></div>
                <div class="fleet-info">
                    <h3>${node.name}</h3>
                    <p class="fleet-role">${node.role}</p>
                    <p class="fleet-spec">${node.spec}</p>
                </div>
                <div class="fleet-metrics">
                    <span>最後心跳 <span class="heartbeat" data-heartbeat="${node.baseHeartbeat}">${node.baseHeartbeat}秒前</span></span>
                    <span>哈希高度 <span class="hash-height" data-hash="${node.baseHash}">#${node.baseHash.toLocaleString()}</span></span>
                </div>
            </article>
        `).join('');
    }

    function startSimulation() {
        if (updateInterval) return;
        
        updateInterval = setInterval(() => {
            updateFleetMetrics();
        }, 3000); // 每 3 秒更新一次
    }

    function stopSimulation() {
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
    }

    function updateFleetMetrics() {
        hashCounter++;
        
        Object.entries(fleetData).forEach(([key, node]) => {
            const card = document.querySelector(`.fleet-card[data-node="${key}"]`);
            if (!card) return;
            
            // 更新心跳
            const heartbeatEl = card.querySelector('.heartbeat');
            if (heartbeatEl) {
                let hb = parseInt(heartbeatEl.getAttribute('data-heartbeat'), 10);
                // 模擬心跳變化：0-15 秒之間
                hb = (hb + Math.floor(Math.random() * 3) + 1) % 16;
                if (hb === 0) hb = 1;
                heartbeatEl.setAttribute('data-heartbeat', hb);
                heartbeatEl.textContent = hb + '秒前';
            }
            
            // 更新哈希高度
            const hashEl = card.querySelector('.hash-height');
            if (hashEl) {
                let hash = parseInt(hashEl.getAttribute('data-hash'), 10);
                hash += Math.floor(Math.random() * 3) + 1;
                hashEl.setAttribute('data-hash', hash);
                hashEl.textContent = '#' + hash.toLocaleString();
            }
            
            // 偶爾切換 ORCHESTRATOR-B 狀態
            if (key === 'orchestrator-b' && Math.random() < 0.05) {
                const statusEl = card.querySelector('.fleet-status');
                const newStatus = node.status === 'standby' ? 'online' : 'standby';
                node.status = newStatus;
                statusEl.className = 'fleet-status ' + newStatus;
            }
        });
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFleetStatus);
    } else {
        initFleetStatus();
    }

    // 導出控制函數
    window.TRIMAC.modules.fleet = {
        init: initFleetStatus,
        start: startSimulation,
        stop: stopSimulation,
        getData: () => fleetData
    };
})();