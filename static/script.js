// ---------- Toast notifications ----------
// Converts server-side flash messages into animated toasts
document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash');
    if (flashes.length > 0) {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);

        flashes.forEach(flash => {
            const isError = flash.classList.contains('flash-error');
            const toast = document.createElement('div');
            toast.className = `toast ${isError ? 'toast-error' : 'toast-success'}`;
            toast.textContent = flash.textContent;
            toastContainer.appendChild(toast);
            flash.remove();

            setTimeout(() => toast.remove(), 3500);
        });
    }

    animateCounters();
    setupLiveSearch();
});

// ---------- Animated dashboard counters ----------
function animateCounters() {
    const counters = document.querySelectorAll('.stat-value');
    counters.forEach(counter => {
        const target = parseInt(counter.textContent, 10);
        if (isNaN(target)) return;

        let current = 0;
        const duration = 600; // ms
        const steps = 30;
        const increment = target / steps;
        const stepTime = duration / steps;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, stepTime);
    });
}

// ---------- Live search (no page reload) ----------
function setupLiveSearch() {
    const searchInput = document.querySelector('.search-form input[name="q"]');
    if (!searchInput) return;

    const table = document.querySelector('.data-table tbody');
    if (!table) return;

    let debounceTimer;
    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const query = searchInput.value.toLowerCase().trim();
            const rows = table.querySelectorAll('tr');

            rows.forEach(row => {
                if (row.querySelector('.empty-state')) return;
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        }, 150);
    });
}
// ---------- Sortable table columns ----------
document.addEventListener('DOMContentLoaded', () => {
    setupSortableTables();
});

function setupSortableTables() {
    const tables = document.querySelectorAll('.data-table');

    tables.forEach(table => {
        const headers = table.querySelectorAll('thead th');
        headers.forEach((header, index) => {
            if (header.textContent.trim().toLowerCase() === 'actions') return;

            header.classList.add('sortable');
            header.dataset.sortDir = '';

            header.addEventListener('click', () => {
                sortTableByColumn(table, index, header, headers);
            });
        });
    });
}

function sortTableByColumn(table, columnIndex, clickedHeader, allHeaders) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr')).filter(
        row => !row.querySelector('.empty-state')
    );
    if (rows.length === 0) return;

    const currentDir = clickedHeader.dataset.sortDir;
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';

    allHeaders.forEach(h => {
        h.dataset.sortDir = '';
        h.classList.remove('sort-asc', 'sort-desc');
    });
    clickedHeader.dataset.sortDir = newDir;
    clickedHeader.classList.add(newDir === 'asc' ? 'sort-asc' : 'sort-desc');

    const getCellValue = (row) => {
        const cell = row.children[columnIndex];
        return cell ? cell.textContent.trim() : '';
    };

    rows.sort((rowA, rowB) => {
        const valA = getCellValue(rowA);
        const valB = getCellValue(rowB);

        const numA = parseFloat(valA);
        const numB = parseFloat(valB);
        const bothNumeric = !isNaN(numA) && !isNaN(numB) &&
                             /^-?\d+(\.\d+)?/.test(valA) && /^-?\d+(\.\d+)?/.test(valB);

        let result;
        if (bothNumeric) {
            result = numA - numB;
        } else {
            result = valA.localeCompare(valB, undefined, { sensitivity: 'base' });
        }

        return newDir === 'asc' ? result : -result;
    });

    rows.forEach(row => tbody.appendChild(row));
}
// ---------- Loading spinner on form submit ----------
document.addEventListener('DOMContentLoaded', () => {
    setupFormSpinners();
});

function setupFormSpinners() {
    const forms = document.querySelectorAll('form.form');

    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (!submitBtn) return;

            if (!form.checkValidity()) return;

            const originalText = submitBtn.textContent;
            submitBtn.dataset.originalText = originalText;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Please wait...';
        });
    });
}
// ---------- Styled confirm modal (replaces browser confirm()) ----------
document.addEventListener('DOMContentLoaded', () => {
    setupConfirmModal();
});

function setupConfirmModal() {
    const overlay = document.getElementById('confirm-modal-overlay');
    if (!overlay) return;

    const messageEl = document.getElementById('confirm-modal-message');
    const cancelBtn = document.getElementById('confirm-modal-cancel');
    const confirmBtn = document.getElementById('confirm-modal-confirm');

    document.querySelectorAll('a.confirm-action').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            messageEl.textContent = link.dataset.confirmMessage || 'Are you sure?';
            confirmBtn.href = link.getAttribute('href');
            overlay.classList.add('open');
        });
    });

    const closeModal = () => overlay.classList.remove('open');

    cancelBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}
// ---------- Dark mode toggle ----------
document.addEventListener('DOMContentLoaded', () => {
    setupThemeToggle();
});

function setupThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) return;

    const applyIcon = () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        toggleBtn.textContent = isDark ? '☀️' : '🌙';
    };

    applyIcon();

    toggleBtn.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
        applyIcon();
    });
}