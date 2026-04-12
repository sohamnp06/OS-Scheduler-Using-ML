/* ─── State ─────────────────────────────────────── */
let processes = [];
let nextPid = 1;

/* ─── DOM Refs ──────────────────────────────────── */
const processForm    = document.getElementById('process-form');
const tableBody      = document.getElementById('table-body');
const predictBtn     = document.getElementById('predict-btn');
const clearBtn       = document.getElementById('clear-btn');
const resultsSection = document.getElementById('results-section');
const runSimBtn      = document.getElementById('run-sim-btn');
const runStatus      = document.getElementById('run-status');

// Empty-row placeholder
const emptyRow = document.getElementById('empty-row');

/* ─── Add Process ───────────────────────────────── */
processForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const p = {
        id:           document.getElementById('p_id').value.trim() || `P${nextPid}`,
        arrival_time: parseFloat(document.getElementById('arrival').value),
        burst_time:   parseFloat(document.getElementById('burst').value),
        priority:     parseInt(document.getElementById('priority').value),
        process_type: document.getElementById('type').value,
    };

    if (processes.find(x => x.id === p.id)) {
        alert(`Process "${p.id}" already exists.`);
        return;
    }

    processes.push(p);
    nextPid += 1;
    document.getElementById('p_id').value = `P${nextPid}`;
    renderTable();
    processForm.reset();
    document.getElementById('p_id').value = `P${nextPid}`;
});

/* ─── Render Table ──────────────────────────────── */
function renderTable() {
    tableBody.innerHTML = '';

    if (processes.length === 0) {
        tableBody.appendChild(emptyRow);
        resultsSection.classList.add('hidden');
        return;
    }

    processes.forEach((p, idx) => {
        const tr = document.createElement('tr');
        tr.id = `row-${p.id}`;
        tr.innerHTML = `
            <td><strong>${p.id}</strong></td>
            <td>${p.arrival_time}</td>
            <td>${p.burst_time}</td>
            <td>${p.priority}</td>
            <td><span class="type-badge ${p.process_type === 'CPU-bound' ? 'cpu' : 'io'}">${p.process_type}</span></td>
            <td>
                <button class="btn-icon" onclick="removeProcess(${idx})" title="Remove">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

/* ─── Remove Process ────────────────────────────── */
window.removeProcess = function(idx) {
    processes.splice(idx, 1);
    renderTable();
}

/* ─── Clear All ─────────────────────────────────── */
clearBtn.addEventListener('click', () => {
    processes = [];
    renderTable();
});

/* ─── Predict ───────────────────────────────────── */
predictBtn.addEventListener('click', async () => {
    // Need at least 3 processes, but we'll let API handle it or just enforce 1
    if (processes.length === 0) {
        alert('Please add at least one process first.');
        return;
    }

    predictBtn.disabled  = true;
    predictBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing Workload…';

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(processes),
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(err);
        }

        const result = await response.json();
        showResults(result);

    } catch (err) {
        console.error(err);
        alert('❌ Prediction failed:\n' + err.message);
    } finally {
        predictBtn.disabled  = false;
        predictBtn.innerHTML = '<i class="fas fa-brain"></i> Predict Workload Algorithm';
    }
});

runSimBtn.addEventListener('click', async () => {
    if (processes.length === 0) {
        alert('Please add processes before starting the simulation.');
        return;
    }

    runSimBtn.disabled = true;
    runSimBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Launching Simulation…';

    try {
        const response = await fetch('/run-simulation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(processes),
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(err);
        }

        const result = await response.json();
        runStatus.classList.remove('hidden');
        runStatus.classList.remove('error');
        runStatus.textContent = '✅ Simulation launched locally. Check your desktop for the Pygame window.';
    } catch (err) {
        console.error(err);
        runStatus.classList.remove('hidden');
        runStatus.classList.add('error');
        runStatus.textContent = '❌ Simulation launch failed. See console for details.';
        alert('❌ Simulation launch failed:\n' + err.message);
    } finally {
        runSimBtn.disabled = false;
        runSimBtn.innerHTML = '<i class="fas fa-play"></i> Run Simulation';
    }
});

/* ─── Display Results ───────────────────────────── */
function showResults(result) {
    resultsSection.classList.remove('hidden');
    runStatus.classList.add('hidden');
    runStatus.textContent = '';
    
    // Update central hero
    const algoEl = document.getElementById('overall-algo');
    algoEl.innerText = result.predicted_algorithm;
    algoEl.className = `algo-hero-tag ${algoClass(result.predicted_algorithm)}`;
    
    document.getElementById('overall-reason').innerHTML = result.reason;

    // Render stats
    const statsGrid = document.getElementById('stats-grid');
    const s = result.stats;
    
    statsGrid.innerHTML = `
        <div class="stat-box"><span class="stat-label">Total Processes</span><span class="stat-value">${s.num_processes}</span></div>
        <div class="stat-box"><span class="stat-label">Mean Burst</span><span class="stat-value">${s.mean_burst.toFixed(2)}</span></div>
        <div class="stat-box"><span class="stat-label">Burst Std Dev</span><span class="stat-value">${s.std_burst.toFixed(2)}</span></div>
        <div class="stat-box"><span class="stat-label">Min / Max Burst</span><span class="stat-value">${s.min_burst} / ${s.max_burst}</span></div>
        
        <div class="stat-box"><span class="stat-label">Arrival Spread</span><span class="stat-value">${s.arrival_spread.toFixed(1)}</span></div>
        <div class="stat-box"><span class="stat-label">Mean Priority</span><span class="stat-value">${s.mean_priority.toFixed(2)}</span></div>
        <div class="stat-box"><span class="stat-label">Priority Var</span><span class="stat-value">${s.priority_var.toFixed(2)}</span></div>
        
        <div class="stat-box"><span class="stat-label">CPU Bound</span><span class="stat-value">${(s.pct_cpu_bound * 100).toFixed(0)}%</span></div>
        <div class="stat-box"><span class="stat-label">I/O Bound</span><span class="stat-value">${(s.pct_io_bound * 100).toFixed(0)}%</span></div>
    `;

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ─── Helpers ───────────────────────────────────── */
function algoClass(algo) {
    const a = algo.toUpperCase();
    if (a.includes('SRTF'))         return 'tag-srtf';
    if (a.includes('SJF'))          return 'tag-sjf';
    if (a.includes('PRIORITY'))     return 'tag-priority';
    if (a.includes('ROUND ROBIN') || a.includes('RR')) return 'tag-rr';
    if (a.includes('FCFS'))         return 'tag-fcfs';
    return 'tag-fcfs';
}
