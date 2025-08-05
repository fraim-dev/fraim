
// NOTE: All data should be properly escaped either by Jinja2's "| tojson" feature
// or by it's HTML autoescape feature

const elements = {
    severityFilter: null,
    typeFilter: null,
    severityCounts: {},
    init() {
        this.severityFilter = document.getElementById('severity-filter');
        this.typeFilter = document.getElementById('type-filter');

        ['error', 'warning', 'note', 'none', 'unknown'].forEach(severity => {
            this.severityCounts[severity] = {
                count: document.getElementById(`count-${severity}`),
                container: document.getElementById(`severity-count-${severity}`)
            };
        });
    }
};

function getTabData(tabName) {
    const tab = tabData.find(t => t.name === tabName);
    return tab ? { severityCounts: tab.severity_counts } : { severityCounts: {} };
}

function updateSeverityCounts(tabName) {
    const { severityCounts } = getTabData(tabName);

    Object.entries(severityCounts).forEach(([severity, count]) => {
        const { count: countEl, container } = elements.severityCounts[severity];

        if (countEl) {
            countEl.textContent = count;
        }

        // Hide "Unknown" severity if no unknown entries in current tab.
        if (severity === 'unknown' && container) {
            container.style.display = count > 0 ? '' : 'none';
        }
    });
}

function updateFilters(tabName) {
    const severityOptions = elements.severityFilter.querySelectorAll('option[data-tabs]');
    const currentSeverityValue = elements.severityFilter.value;

    severityOptions.forEach(option => {
        const applicableTabs = option.dataset.tabs.split(',');
        option.style.display = applicableTabs.includes(tabName) ? '' : 'none';
    });

    // Reset selection if current value is no longer visible
    if (currentSeverityValue && !isOptionVisible(elements.severityFilter, currentSeverityValue)) {
        elements.severityFilter.value = '';
    }

    // Update type filter - show only options that belong to current tab
    const typeOptions = elements.typeFilter.querySelectorAll('option[data-tabs]');
    const currentTypeValue = elements.typeFilter.value;

    typeOptions.forEach(option => {
        const applicableTabs = option.dataset.tabs.split(',');
        option.style.display = applicableTabs.includes(tabName) ? '' : 'none';
    });

    // Reset selection if current value is no longer visible
    if (currentTypeValue && !isOptionVisible(elements.typeFilter, currentTypeValue)) {
        elements.typeFilter.value = '';
    }
}

function isOptionVisible(selectElement, value) {
    const option = selectElement.querySelector(`option[value="${value}"]`);
    return option && option.style.display !== 'none';
}

function getTabContent(tabName) {
    const tabIndex = tabData.findIndex(t => t.name === tabName);
    return tabIndex >= 0 ? document.getElementById(`tab-content-${tabIndex}`) : null;
}

function toggleRowDetails(resultIndex) {
    const detailRow = document.getElementById(`detail-${resultIndex}`);
    const mainRow = document.querySelector(`[data-result-index="${resultIndex}"]`);

    if (!detailRow || !mainRow) return;

    const isHidden = detailRow.classList.contains('hidden');

    if (isHidden) {
        // Expand
        detailRow.classList.remove('hidden');
        mainRow.classList.add('expanded');

        // Auto-scroll to vulnerable line within code block container
        setTimeout(() => {
            const vulnerableLine = detailRow.querySelector('.code-line.vulnerable');
            const codeBlock = detailRow.querySelector('.code-block');
            if (vulnerableLine && codeBlock) {
                // Calculate position of vulnerable line relative to code block
                const lineOffset = vulnerableLine.offsetTop - codeBlock.offsetTop;
                const codeBlockHeight = codeBlock.clientHeight;
                const lineHeight = vulnerableLine.clientHeight;

                // Center the vulnerable line in the code block
                const scrollTop = lineOffset - (codeBlockHeight / 2) + (lineHeight / 2);
                codeBlock.scrollTo({ top: scrollTop, behavior: 'smooth' });
            }
        }, 100);
    } else {
        // Collapse
        detailRow.classList.add('hidden');
        mainRow.classList.remove('expanded');
    }
}

function showTab(tabName) {
    // Deactivate all tabs and content
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Activate selected tab
    const selectedButton = document.querySelector(`[data-tab="${tabName}"]`);
    const tabContent = getTabContent(tabName);

    if (selectedButton && tabContent) {
        selectedButton.classList.add('active');
        tabContent.classList.add('active');
    }

    // Update UI for new tab
    collapseAllRows(); // Close any open details
    updateSeverityCounts(tabName);
    updateFilters(tabName);
    filterResults();
}

function filterResults() {
    const severityFilter = elements.severityFilter.value;
    const typeFilter = elements.typeFilter.value;
    const activeTab = document.querySelector('.tab-content.active');

    if (!activeTab) return;

    activeTab.querySelectorAll('.result-row').forEach(row => {
        const severity = row.getAttribute('data-severity');
        const type = row.getAttribute('data-type');
        const resultIndex = row.getAttribute('data-result-index');

        const matches = (!severityFilter || severity === severityFilter) &&
                       (!typeFilter || type === typeFilter);

        // Show/hide row
        row.style.display = matches ? '' : 'none';

        // Hide detail row if main row is filtered out
        if (!matches) {
            const detailRow = document.getElementById(`detail-${resultIndex}`);
            if (detailRow) {
                detailRow.classList.add('hidden');
                row.classList.remove('expanded');
            }
        }
    });
}

function expandAllRows() {
    const activeTab = document.querySelector('.tab-content.active');
    if (!activeTab) return;

    activeTab.querySelectorAll('.result-row:not([style*="display: none"])').forEach(row => {
        const resultIndex = row.getAttribute('data-result-index');
        const detailRow = document.getElementById(`detail-${resultIndex}`);
        if (detailRow) {
            detailRow.classList.remove('hidden');
            row.classList.add('expanded');
        }
    });
}

function collapseAllRows() {
    const activeTab = document.querySelector('.tab-content.active');
    if (!activeTab) return;

    activeTab.querySelectorAll('.result-row').forEach(row => {
        const resultIndex = row.getAttribute('data-result-index');
        const detailRow = document.getElementById(`detail-${resultIndex}`);
        if (detailRow) {
            detailRow.classList.add('hidden');
            row.classList.remove('expanded');
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    elements.init();

    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            showTab(button.getAttribute('data-tab'));
        });
    });

    // Filter changes
    elements.severityFilter.addEventListener('change', filterResults);
    elements.typeFilter.addEventListener('change', filterResults);

    // Bulk operations
    document.getElementById('expand-all-btn').addEventListener('click', expandAllRows);
    document.getElementById('collapse-all-btn').addEventListener('click', collapseAllRows);

    // Row expansion (using event delegation for better performance)
    document.addEventListener('click', (e) => {
        const row = e.target.closest('.result-row');
        if (row) {
            const resultIndex = parseInt(row.getAttribute('data-result-index'));
            toggleRowDetails(resultIndex);
        }
    });

    // Initialize UI for the active tab
    const activeButton = document.querySelector('.tab-button.active');
    if (activeButton) {
        const tabName = activeButton.getAttribute('data-tab');
        updateSeverityCounts(tabName);
        updateFilters(tabName);
    }
});
