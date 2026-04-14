/* ─── State ─────────────────────────────────────── */
let processes = [];
let nextPid = 1;

console.log("Scheduler Script Version 2.0 Loaded");

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
        process_type: "CPU-bound",
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
    if (processes.length === 0) {
        alert('Please add at least one process first.');
        return;
    }

    predictBtn.disabled  = true;
    predictBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

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
        alert('Prediction failed:\n' + err.message);
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
    runSimBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Launching...';

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

        runStatus.classList.remove('hidden');
        runStatus.classList.remove('error');
        runStatus.textContent = 'Simulation launched locally.';
    } catch (err) {
        console.error(err);
        runStatus.classList.remove('hidden');
        runStatus.classList.add('error');
        runStatus.textContent = 'Simulation launch failed.';
    } finally {
        runSimBtn.disabled = false;
        runSimBtn.innerHTML = '<i class="fas fa-play"></i> Run Simulation';
    }
});

/* ─── Display Results ───────────────────────────── */
function showResults(result) {
    resultsSection.classList.remove('hidden');
    runStatus.classList.add('hidden');
    
    // Update central hero
    const algoEl = document.getElementById('overall-algo');
    algoEl.innerText = result.predicted_algorithm;
    algoEl.className = `algo-hero-tag ${algoClass(result.predicted_algorithm)}`;
    
    document.getElementById('overall-reason').innerHTML = result.reason;

    // Render stats
    const statsGrid = document.getElementById('stats-grid');
    const s = result.stats;
    
    const descriptions = {
        "Total Processes": "Calculated by counting every entry in the ready queue. This tells us the volume of tasks waiting for execution.",
        "Mean Burst": "Calculated as (Sum of all burst times) / (Number of processes). It determines if the workload is generally quick or CPU-heavy.",
        "Burst Std Dev": "Calculated as the standard deviation of all burst times. High variation (high std dev) indicates a mix of short and long tasks, favoring algorithms like SJF.",
        "Min / Max Burst": "Identifies the shortest and longest single tasks in the queue, helping detect outliers that might block other processes.",
        "Arrival Spread": "The difference between the last arrival time and the first arrival time. It shows the distribution of incoming traffic over time.",
        "Mean Priority": "The average priority level across the queue, used to decide if priority-based logic should take precedence.",
        "Priority Var": "The variance in priorities. High variance means some tasks are much more critical than others, requiring careful prioritization."
    };

    const statsData = [
        { label: "Total Processes", value: s.num_processes },
        { label: "Mean Burst", value: s.mean_burst.toFixed(2) },
        { label: "Burst Std Dev", value: s.std_burst.toFixed(2) },
        { label: "Min / Max Burst", value: `${s.min_burst} / ${s.max_burst}` },
        { label: "Arrival Spread", value: s.arrival_spread.toFixed(1) },
        { label: "Mean Priority", value: s.mean_priority.toFixed(2) },
        { label: "Priority Var", value: s.priority_var.toFixed(2) }
    ];

    statsGrid.innerHTML = '';
    statsData.forEach(item => {
        const box = document.createElement('div');
        box.className = 'stat-box';
        box.style.cursor = 'pointer';
        box.innerHTML = `
            <div class="stat-label">${item.label}</div>
            <div class="stat-value">${item.value}</div>
        `;
        box.onclick = () => showModal(item.label, descriptions[item.label]);
        statsGrid.appendChild(box);
    });


    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ─── Modal Handling ────────────────────────────── */
function showModal(title, description) {
    const modal = document.getElementById('stat-modal');
    document.getElementById('modal-title').innerText = title;
    document.getElementById('modal-description').innerText = description;
    modal.classList.remove('hidden');
}

document.querySelector('.close-modal').onclick = () => {
    document.getElementById('stat-modal').classList.add('hidden');
};

window.onclick = (e) => {
    const modal = document.getElementById('stat-modal');
    if (e.target === modal) modal.classList.add('hidden');
};

function algoClass(algo) {
    const a = algo.toUpperCase();
    if (a.includes('SRTF')) return 'tag-srtf';
    if (a.includes('SJF')) return 'tag-sjf';
    if (a.includes('PRIORITY')) return 'tag-priority';
    if (a.includes('RR') || a.includes('ROUND ROBIN')) return 'tag-rr';
    return 'tag-fcfs';
}
