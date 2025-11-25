document.addEventListener('DOMContentLoaded', function() {
    // Enhanced Auto-dismiss alerts with progress
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        const progressBar = document.createElement('div');
        progressBar.className = 'alert-progress';
        progressBar.style.cssText = `
            position: absolute;
            bottom: 0;
            left: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--mcd-red), var(--mcd-yellow));
            width: 100%;
            animation: progress 5s linear forwards;
            border-radius: 0 0 12px 12px;
        `;
        alert.style.position = 'relative';
        alert.style.overflow = 'hidden';
        alert.appendChild(progressBar);

        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover'
        });
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add loading state to all buttons with data-loading attribute
    document.querySelectorAll('[data-loading]').forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.setAttribute('data-original-text', originalText);
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
            this.disabled = true;

            // Revert after 5 seconds if still loading
            setTimeout(() => {
                if (this.disabled) {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }
            }, 5000);
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Auto-hide alerts after delay
    const autoHideAlerts = document.querySelectorAll('.alert-auto-hide');
    autoHideAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 3000);
    });
});

// Enhanced print functionality
function printPage() {
    document.body.classList.add('printing');
    window.print();
    setTimeout(() => {
        document.body.classList.remove('printing');
    }, 1000);
}

// Enhanced export functionality
function exportToCSV(tableId, filename = 'export.csv') {
    Alpine.store('app').loading = true;

    const table = document.getElementById(tableId);
    if (!table) {
        console.error('Table not found');
        Alpine.store('app').loading = false;
        return;
    }

    let csv = [];
    const rows = table.querySelectorAll('tr');

    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');

        for (let j = 0; j < cols.length; j++) {
            let data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ');
            data = data.replace(/"/g, '""');
            row.push('"' + data + '"');
        }

        csv.push(row.join(','));
    }

    // Download CSV file
    const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);

    Alpine.store('app').loading = false;
}

// Form validation enhancement
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Global loading state management
document.addEventListener('alpine:init', () => {
    Alpine.store('app', {
        loading: false,
        sidebarOpen: window.innerWidth >= 992,
        darkMode: false,

        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            document.body.classList.toggle('dark-mode', this.darkMode);
            localStorage.setItem('darkMode', this.darkMode);
        },

        init() {
            // Load dark mode preference
            const savedDarkMode = localStorage.getItem('darkMode');
            if (savedDarkMode !== null) {
                this.darkMode = savedDarkMode === 'true';
                document.body.classList.toggle('dark-mode', this.darkMode);
            }
        }
    });
});

// Enhanced error handling
window.addEventListener('error', function(e) {
    console.error('Application error:', e.error);
    // You could send this to your error tracking service
});

// Utility functions
const McDUtils = {
    // Format date
    formatDate: (date) => {
        return new Date(date).toLocaleDateString('en-PK', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    // Format time
    formatTime: (date) => {
        return new Date(date).toLocaleTimeString('en-PK', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Debounce function
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Copy to clipboard
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy text: ', err);
            return false;
        }
    }
};

// Corrective Action Specific Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize corrective action functionality
    initCorrectiveActions();

    // Initialize filters
    initActionFilters();

    // Initialize due date calculations
    initDueDateCalculations();
});

// Corrective Actions Management
function initCorrectiveActions() {
    // Toggle completion status
    document.querySelectorAll('.completion-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const actionId = this.dataset.actionId;
            const isCompleted = this.dataset.completed === 'true';
            toggleCorrectiveAction(actionId, !isCompleted, this);
        });
    });

    // Risk level color coding
    document.querySelectorAll('.risk-badge').forEach(badge => {
        const riskLevel = badge.textContent.trim().toLowerCase();
        badge.classList.add(`risk-badge-${riskLevel}`);
    });

    // Initialize due date status
    updateDueDateStatus();
}

// Filter functionality for corrective actions
function initActionFilters() {
    const filterForm = document.getElementById('actionFilters');
    if (filterForm) {
        filterForm.addEventListener('change', function() {
            // Add loading state
            filterForm.classList.add('loading');

            // Submit form via AJAX or regular form submission
            setTimeout(() => {
                this.submit();
            }, 300);
        });
    }

    // Clear filters
    const clearFilters = document.getElementById('clearFilters');
    if (clearFilters) {
        clearFilters.addEventListener('click', function() {
            const form = this.closest('form');
            form.reset();
            form.submit();
        });
    }
}

// Due date calculations and status updates
function initDueDateCalculations() {
    document.querySelectorAll('.due-date').forEach(element => {
        const dueDate = new Date(element.dataset.dueDate);
        const today = new Date();
        const diffTime = dueDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        element.classList.remove('overdue', 'upcoming', 'normal');

        if (diffDays < 0) {
            element.classList.add('overdue');
            element.title = `${Math.abs(diffDays)} days overdue`;
        } else if (diffDays <= 7) {
            element.classList.add('upcoming');
            element.title = `Due in ${diffDays} days`;
        } else {
            element.classList.add('normal');
            element.title = `Due in ${diffDays} days`;
        }
    });
}

// Toggle corrective action completion status
async function toggleCorrectiveAction(actionId, completed, element) {
    try {
        // Show loading state
        const originalHTML = element.innerHTML;
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        element.disabled = true;

        const response = await fetch(`/corrective-actions/${actionId}/complete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ completed: completed })
        });

        const data = await response.json();

        if (data.success) {
            // Update UI
            element.dataset.completed = completed;
            element.innerHTML = completed ?
                '<i class="fas fa-check-circle text-success"></i>' :
                '<i class="fas fa-circle text-secondary"></i>';

            // Update completion date if available
            if (data.completion_date) {
                const completionElement = document.querySelector(`[data-completion-date="${actionId}"]`);
                if (completionElement) {
                    completionElement.textContent = data.completion_date;
                }
            }

            // Show success message
            showAlert('Corrective action updated successfully!', 'success');

            // Update statistics if on dashboard
            updateActionStatistics();
        } else {
            throw new Error(data.message || 'Failed to update corrective action');
        }
    } catch (error) {
        console.error('Error toggling corrective action:', error);
        showAlert('Error updating corrective action. Please try again.', 'danger');
        element.innerHTML = originalHTML;
    } finally {
        element.disabled = false;
    }
}

// Update corrective action statistics
function updateActionStatistics() {
    // This would typically refresh statistics via AJAX
    const statsContainer = document.getElementById('actionStatistics');
    if (statsContainer) {
        fetch('/corrective-actions/dashboard/stats/')
            .then(response => response.json())
            .then(data => {
                updateStatsDisplay(data);
            })
            .catch(error => {
                console.error('Error updating statistics:', error);
            });
    }
}

// Update stats display
function updateStatsDisplay(stats) {
    const elements = {
        total: document.getElementById('stats-total'),
        completed: document.getElementById('stats-completed'),
        pending: document.getElementById('stats-pending'),
        overdue: document.getElementById('stats-overdue'),
        completionRate: document.getElementById('stats-completion-rate')
    };

    Object.keys(elements).forEach(key => {
        if (elements[key] && stats[key] !== undefined) {
            elements[key].textContent = stats[key];
        }
    });
}

// Update due date status
function updateDueDateStatus() {
    document.querySelectorAll('[data-due-date]').forEach(element => {
        const dueDate = new Date(element.dataset.dueDate);
        const today = new Date();
        const timeDiff = dueDate.getTime() - today.getTime();
        const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));

        element.classList.remove('overdue', 'warning', 'normal');

        if (daysDiff < 0) {
            element.classList.add('overdue');
        } else if (daysDiff <= 3) {
            element.classList.add('warning');
        } else {
            element.classList.add('normal');
        }
    });
}

// Get CSRF token for AJAX requests
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer') || createAlertContainer();

    const alertId = 'alert-' + Date.now();
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    alertContainer.insertAdjacentHTML('beforeend', alertHTML);

    // Auto remove after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            alertElement.remove();
        }
    }, 5000);
}

// Create alert container if it doesn't exist
function createAlertContainer() {
    const container = document.createElement('div');
    container.id = 'alertContainer';
    container.className = 'position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// Export corrective actions to CSV
function exportCorrectiveActionsCSV() {
    const table = document.querySelector('.mcd-table');
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll('tr');

    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');

        for (let j = 0; j < cols.length; j++) {
            // Clean data and remove HTML
            let data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ');
            data = data.replace(/"/g, '""');
            row.push('"' + data + '"');
        }

        csv.push(row.join(','));
    }

    // Download CSV
    const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.download = 'corrective_actions_export.csv';
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Chart initialization for dashboard
function initActionCharts() {
    const riskChart = document.getElementById('riskDistributionChart');
    const completionChart = document.getElementById('completionTrendChart');

    if (riskChart) {
        // Initialize risk distribution chart
        // This would use Chart.js or similar library
        console.log('Initializing risk distribution chart');
    }

    if (completionChart) {
        // Initialize completion trend chart
        console.log('Initializing completion trend chart');
    }
}

// Search and filter actions
function searchActions(query) {
    const actionCards = document.querySelectorAll('.action-card');
    const searchTerm = query.toLowerCase();

    actionCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Initialize when Alpine.js is ready
document.addEventListener('alpine:init', () => {
    // Add corrective actions store
    Alpine.store('correctiveActions', {
        filters: {
            risk_level: '',
            completed: '',
            overdue: ''
        },

        applyFilters() {
            // This would typically make an AJAX request to update the list
            const form = document.getElementById('actionFilters');
            if (form) {
                form.submit();
            }
        },

        clearFilters() {
            this.filters = {
                risk_level: '',
                completed: '',
                overdue: ''
            };
            this.applyFilters();
        }
    });
});

// Utility function for date formatting
function formatDateForInput(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().split('T')[0];
}

// Auto-save for corrective action forms
function initAutoSave() {
    const form = document.getElementById('correctiveActionForm');
    if (!form) return;

    let timeoutId;

    form.addEventListener('input', McDUtils.debounce(() => {
        // Auto-save logic would go here
        console.log('Auto-saving corrective action...');
    }, 1000));
}