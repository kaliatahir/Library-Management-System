document.addEventListener('DOMContentLoaded', function () {
    // Theme toggle
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            if (isDark) {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            }
        });
    }

    // Reusable confirm modal for .confirm-action links
    const overlay = document.getElementById('confirm-modal-overlay');
    const message = document.getElementById('confirm-modal-message');
    const confirmBtn = document.getElementById('confirm-modal-confirm');
    const cancelBtn = document.getElementById('confirm-modal-cancel');

    if (overlay) {
        document.querySelectorAll('.confirm-action').forEach(function (link) {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                message.textContent = link.dataset.confirmMessage || 'Are you sure?';
                confirmBtn.href = link.getAttribute('href');
                overlay.classList.add('active');
            });
        });

        cancelBtn.addEventListener('click', function () {
            overlay.classList.remove('active');
        });

        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) overlay.classList.remove('active');
        });
    }
});
