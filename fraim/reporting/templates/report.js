// SARIF Data Parsing and Rendering
const UNKNOWN = 'unknown';
const SEVERITY_ORDER = { error: 1, warning: 2, note: 3, none: 4, unknown: 5 };

// Global state
let processedData = null;
let currentTab = null;
let sarifData = null;
let showOnlyExploitable = true; // By default, show only exploitable findings
let currentSortColumn = 'severity';
let currentSortDirection = 'asc';

// Theme management
function initTheme() {
    // Check for saved theme preference, otherwise use browser preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);
    } else {
        // Use browser preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        updateThemeIcon(prefersDark ? 'dark' : 'light');
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const browserPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const effectiveTheme = currentTheme || (browserPrefersDark ? 'dark' : 'light');
    
    const newTheme = effectiveTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    
    if (theme === 'dark') {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    } else {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    }
}

// Get threat model filename from HTML filename
function getThreatModelFilename() {
    const htmlPath = window.location.pathname;
    const htmlFilename = htmlPath.substring(htmlPath.lastIndexOf('/') + 1);
    const baseName = htmlFilename.replace(/\.html$/, '');
    return baseName + '.md';
}

// Initialize the application
async function init() {
    try {
        // Use embedded SARIF data
        sarifData = embeddedSarifData;

        processedData = processSarifData(sarifData);
        renderReport(processedData);
        setupEventListeners();

        // Load and display threat model if available
        loadThreatModel();

        // Show first tab by default
        if (processedData.tabs.length > 0) {
            showTab(processedData.tabs[0].name);
        }
    } catch (error) {
        console.error('Error processing embedded SARIF data:', error);

        const errorDetails = error.message;

        document.body.innerHTML = `
            <div style="padding: 3rem 2rem; max-width: 800px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <h1 style="color: #DC2626; font-size: 1.5rem; font-weight: 500; margin-bottom: 1.5rem;">Unable to Load Report</h1>
                <div style="background: #FEF2F2; border-left: 3px solid #DC2626; padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem;">
                    <p style="margin: 0; color: #1A1A1A; line-height: 1.65;">
                        <strong>Error:</strong> Failed to process embedded SARIF data
                    </p>
                    <p style="margin: 0.75rem 0 0 0; color: #737373; font-size: 0.9375rem;">
                        ${errorDetails}
                    </p>
                </div>
                <div style="color: #737373; line-height: 1.75; font-size: 0.9375rem;">
                    The embedded SARIF data may be corrupted or invalid. Please regenerate the report.
                </div>
            </div>
        `;
    }
}

// Process SARIF data into renderable format
function processSarifData(sarif) {
    const runs = sarif.runs || [];
    const tabs = [];
    const allResults = [];
    const allSeverities = new Set();
    const allTypes = new Set();
    
    let resultIndex = 0;
    
    runs.forEach(run => {
        const workflowName = run.tool?.driver?.name || UNKNOWN;
        const results = run.results || [];
        
        const severityCounts = { error: 0, warning: 0, note: 0, none: 0, unknown: 0 };
        const tabResults = [];
        
        results.forEach(result => {
            const severity = normalizeSeverity(result.level);
            const type = result.properties?.type || UNKNOWN;
            const description = result.message?.text || 'No description available';
            const confidence = result.properties?.confidence || UNKNOWN;
            const filePath = getFilePath(result);
            
            const exploitable = result.properties?.exploitable || false;
            
            const processedResult = {
                index: resultIndex,
                type,
                severity,
                description,
                file: filePath,
                confidence,
                exploitable,
                rawResult: result
            };
            
            tabResults.push(processedResult);
            allResults.push(processedResult);
            severityCounts[severity]++;
            allSeverities.add(severity);
            allTypes.add(type);
            resultIndex++;
        });
        
        // Sort by severity
        tabResults.sort((a, b) => {
            return (SEVERITY_ORDER[a.severity] || 999) - (SEVERITY_ORDER[b.severity] || 999);
        });
        
        tabs.push({
            name: workflowName,
            count: results.length,
            results: tabResults,
            severityCounts
        });
    });
    
    return {
        tabs,
        allResults,
        allSeverities: Array.from(allSeverities).sort((a, b) => 
            (SEVERITY_ORDER[a] || 999) - (SEVERITY_ORDER[b] || 999)
        ),
        allTypes: Array.from(allTypes).sort()
    };
}

function normalizeSeverity(level) {
    const normalized = (level || '').toLowerCase();
    return ['error', 'warning', 'note', 'none'].includes(normalized) ? normalized : UNKNOWN;
}

function getFilePath(result) {
    if (!result.locations || result.locations.length === 0) return UNKNOWN;
    const location = result.locations[0].physicalLocation;
    if (!location || !location.artifactLocation) return UNKNOWN;
    
    let uri = location.artifactLocation.uri || UNKNOWN;
    uri = uri.replace(/^file:\/\//, '');
    
    if (uri.includes('../') || uri.includes('..\\')) return UNKNOWN;
    
    return uri.replace(/\\/g, '/').replace(/^\//, '') || UNKNOWN;
}

// Render the report
function renderReport(data) {
    // Update content header with repo name
    document.getElementById('repo-name').textContent = 
        sarifData.repoName || 'Security Analysis';
    
    // Render security score if provided
    if (sarifData.securityScore !== undefined && sarifData.securityScore !== null) {
        renderSecurityScore(sarifData.securityScore);
    }
    
    const timestamp = new Date().toLocaleString();
    document.getElementById('footer-timestamp').textContent = timestamp;
    
    // Render overall metrics
    renderMetrics(data);
    
    // Render filter options
    renderFilterOptions(data);
    
    // Update footer metadata
    const totalFindings = data.allResults.length;
    document.getElementById('total-findings').textContent = totalFindings;
    
    const scannerVersion = sarifData.runs?.[0]?.tool?.driver?.version || '1.0.0';
    document.getElementById('scanner-version').textContent = scannerVersion;
}

// Render security score circle
function renderSecurityScore(score) {
    const scoreCircle = document.getElementById('score-circle');
    const scoreValue = document.getElementById('score-value');
    
    // Show the score circle
    scoreCircle.style.display = 'flex';
    
    scoreValue.textContent = score;
    
    // Remove any existing color classes
    scoreCircle.classList.remove('excellent', 'good', 'fair', 'poor', 'critical');
    
    // Add appropriate color class based on score
    if (score >= 90) {
        scoreCircle.classList.add('excellent'); // Dark green
    } else if (score >= 80) {
        scoreCircle.classList.add('good'); // Light green
    } else if (score >= 70) {
        scoreCircle.classList.add('fair'); // Yellow
    } else if (score >= 60) {
        scoreCircle.classList.add('poor'); // Orange
    } else {
        scoreCircle.classList.add('critical'); // Red
    }
}

// Render metrics section
function renderMetrics(data) {
    const metricsGrid = document.getElementById('metrics-grid');
    const overallCounts = { error: 0, warning: 0, note: 0, none: 0, unknown: 0 };
    
    // Calculate overall counts
    data.tabs.forEach(tab => {
        Object.keys(tab.severityCounts).forEach(severity => {
            overallCounts[severity] += tab.severityCounts[severity];
        });
    });
    
    metricsGrid.innerHTML = '';
    
    // Render metric cards
    const metrics = [
        { key: 'error', label: 'Critical', colorClass: 'critical' },
        { key: 'error', label: 'Errors', colorClass: 'error' },
        { key: 'warning', label: 'Warnings', colorClass: 'warning' },
        { key: 'note', label: 'Info', colorClass: 'info' }
    ];
    
    const metricData = [
        { 
            count: overallCounts.error, 
            label: 'Errors', 
            colorClass: overallCounts.error > 0 ? 'critical' : 'success',
            filterType: 'severity',
            filterValue: 'error'
        },
        { 
            count: overallCounts.warning, 
            label: 'Warnings', 
            colorClass: overallCounts.warning > 5 ? 'warning' : overallCounts.warning > 0 ? 'warning' : 'success',
            filterType: 'severity',
            filterValue: 'warning'
        },
        { 
            count: overallCounts.note, 
            label: 'Info', 
            colorClass: 'info',
            filterType: 'severity',
            filterValue: 'note'
        }
    ];
    
    const exploitableCount = data.allResults.filter(r => r.exploitable).length;
    
    metricData.forEach(metric => {
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.dataset.filterType = metric.filterType;
        card.dataset.filterValue = metric.filterValue;
        card.innerHTML = `
            <div class="metric-score ${metric.colorClass}">
                ${metric.count}
            </div>
            <div class="metric-label">${metric.label}</div>
        `;
        metricsGrid.appendChild(card);
    });
}

// Render filter options
function renderFilterOptions(data) {
    const severityFilter = document.getElementById('severity-filter');
    const typeFilter = document.getElementById('type-filter');
    
    severityFilter.innerHTML = '<option value="">All Severities</option>';
    typeFilter.innerHTML = '<option value="">All Types</option>';
    
    // Add severity options
    data.allSeverities.forEach(severity => {
        const option = document.createElement('option');
        option.value = severity;
        option.textContent = severity.charAt(0).toUpperCase() + severity.slice(1);
        severityFilter.appendChild(option);
    });
    
    // Add type options
    data.allTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeFilter.appendChild(option);
    });
}

// Show tab content
function showTab(tabName) {
    currentTab = tabName;
    
    // Render findings for this tab
    const tab = processedData.tabs.find(t => t.name === tabName);
    if (tab) {
        renderFindings(tab.results);
    }
}

// Render findings as table
function renderFindings(results) {
    const container = document.getElementById('tab-contents');
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 4rem 2rem; color: var(--color-text-secondary);">
                <svg style="width: 64px; height: 64px; margin-bottom: 1rem; opacity: 0.5;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <path d="M9 12l2 2 4-4"/>
                </svg>
                <p style="font-size: 1.125rem; font-weight: 500; margin: 0;">No findings to display</p>
            </div>
        `;
        return;
    }
    
    // Create table
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'table-wrapper';
    
    const table = document.createElement('table');
    table.className = 'findings-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th class="expand-col"></th>
                <th class="sortable ${currentSortColumn === 'severity' ? 'sorted sorted-' + currentSortDirection : ''}" data-column="severity">
                    Severity
                    <svg class="sort-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M7 10l5-5 5 5M7 14l5 5 5-5"/>
                    </svg>
                </th>
                <th class="sortable ${currentSortColumn === 'type' ? 'sorted sorted-' + currentSortDirection : ''}" data-column="type">
                    Type
                    <svg class="sort-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M7 10l5-5 5 5M7 14l5 5 5-5"/>
                    </svg>
                </th>
                <th class="sortable ${currentSortColumn === 'description' ? 'sorted sorted-' + currentSortDirection : ''}" data-column="description">
                    Description
                    <svg class="sort-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M7 10l5-5 5 5M7 14l5 5 5-5"/>
                    </svg>
                </th>
                <th class="sortable ${currentSortColumn === 'file' ? 'sorted sorted-' + currentSortDirection : ''}" data-column="file">
                    File
                    <svg class="sort-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M7 10l5-5 5 5M7 14l5 5 5-5"/>
                    </svg>
                </th>
                <th class="sortable ${currentSortColumn === 'exploitable' ? 'sorted sorted-' + currentSortDirection : ''}" data-column="exploitable">
                    Exploitable
                    <svg class="sort-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M7 10l5-5 5 5M7 14l5 5 5-5"/>
                    </svg>
                </th>
            </tr>
        </thead>
        <tbody id="table-body"></tbody>
    `;
    
    tableWrapper.appendChild(table);
    container.appendChild(tableWrapper);
    
    // Sort and render rows
    const sortedResults = sortResults(results, currentSortColumn, currentSortDirection);
    const tbody = document.getElementById('table-body');
    
    sortedResults.forEach(result => {
        const row = createTableRow(result);
        tbody.appendChild(row);
    });
    
    // Apply filters
    filterResults();
}

// Sort results by column
function sortResults(results, column, direction) {
    const sorted = [...results];
    
    sorted.sort((a, b) => {
        let aVal, bVal;
        
        switch (column) {
            case 'severity':
                aVal = SEVERITY_ORDER[a.severity] || 999;
                bVal = SEVERITY_ORDER[b.severity] || 999;
                break;
            case 'exploitable':
                aVal = a.exploitable ? 1 : 0;
                bVal = b.exploitable ? 1 : 0;
                break;
            case 'type':
                aVal = a.type.toLowerCase();
                bVal = b.type.toLowerCase();
                break;
            case 'description':
                aVal = a.description.toLowerCase();
                bVal = b.description.toLowerCase();
                break;
            case 'file':
                aVal = a.file.toLowerCase();
                bVal = b.file.toLowerCase();
                break;
            default:
                return 0;
        }
        
        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    return sorted;
}

// Create a table row element
function createTableRow(result) {
    // Create main row
    const row = document.createElement('tr');
    row.className = 'finding-row';
    row.dataset.severity = result.severity;
    row.dataset.type = result.type;
    row.dataset.exploitable = result.exploitable;
    row.dataset.resultIndex = result.index;
    
    // Determine severity color
    let severityClass = 'note';
    if (result.severity === 'error') severityClass = 'error';
    else if (result.severity === 'warning') severityClass = 'warning';
    else if (result.severity === 'unknown') severityClass = 'unknown';
    
    row.innerHTML = `
        <td class="expand-cell">
            <svg class="expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 5l7 7-7 7"/>
            </svg>
        </td>
        <td class="severity-cell">
            <span class="severity-badge ${severityClass}">${result.severity.toUpperCase()}</span>
        </td>
        <td class="type-cell" title="${escapeHtml(result.type)}">${escapeHtml(result.type)}</td>
        <td class="description-cell" title="${escapeHtml(result.description)}">
            ${escapeHtml(result.description)}
        </td>
        <td class="file-cell" title="${escapeHtml(result.file)}">${escapeHtml(result.file)}</td>
        <td class="exploitable-cell">
            ${result.exploitable ? `
                <span class="exploitable-badge">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L1 21h22L12 2zm0 3.83L19.53 19H4.47L12 5.83zM11 16v2h2v-2h-2zm0-6v4h2v-4h-2z"/>
                    </svg>
                    Yes
                </span>
            ` : `<span class="not-exploitable">No</span>`}
        </td>
    `;
    
    // Create detail row
    const detailRow = document.createElement('tr');
    detailRow.className = 'detail-row';
    detailRow.dataset.resultIndex = result.index;
    detailRow.innerHTML = `
        <td colspan="6" class="detail-cell">
            <div class="detail-content">
                ${renderFindingDetails(result.rawResult)}
            </div>
        </td>
    `;
    
    // Add both rows to a fragment
    const fragment = document.createDocumentFragment();
    fragment.appendChild(row);
    fragment.appendChild(detailRow);
    
    return fragment;
}

// Render finding details
function renderFindingDetails(result) {
    let html = '';

    // Type + Location (combined section)
    const ruleId = result.rule?.id || result.ruleId || 'Unknown';
    const location = result.locations?.[0]?.physicalLocation;
    if (location) {
        const uri = location.artifactLocation?.uri?.replace(/^file:\/\//, '') || 'Unknown';
        const startLine = location.region?.startLine || 'N/A';
        const endLine = location.region?.endLine || startLine;

        html += `
            <div class="detail-section">
                <h4>Type + Location</h4>
                <div class="type-location-info">
                    <div class="type-info"><strong>Type:</strong> ${escapeHtml(ruleId)}</div>
                    <div class="location-info">
                        <div class="location-file">${escapeHtml(uri)}</div>
                        <div class="location-line">Lines ${startLine}${startLine !== endLine ? `-${endLine}` : ''}</div>
                    </div>
                </div>
            </div>
        `;
    }

    // Description (full text, not ellipsized)
    const description = result.message?.text || 'No description available';
    html += `
        <div class="detail-section">
            <h4>Description</h4>
            <div class="detail-content">${escapeHtml(description)}</div>
        </div>
    `;

    // Details (explanation)
    const explanation = result.properties?.explanation?.text;
    if (explanation) {
        html += `
            <div class="detail-section">
                <h4>Details</h4>
                <div class="detail-content">${escapeHtml(explanation)}</div>
            </div>
        `;
    }

    // Code Context
    if (location) {
        const snippet = location.contextRegion?.snippet?.text || location.region?.snippet?.text;
        if (snippet) {
            html += `
                <div class="detail-section">
                    <h4>Code Context</h4>
                    <div class="code-snippet">
                        <pre>${renderCodeSnippet(snippet, location)}</pre>
                    </div>
                </div>
            `;
        }
    }
    
    // Additional properties
    const additionalProps = getAdditionalProperties(result);
    if (additionalProps.length > 0) {
        html += `
            <div class="detail-section">
                <h4>Additional Information</h4>
                <div class="properties-grid">
                    ${additionalProps.map(prop => `
                        <div class="property-key">${escapeHtml(prop.key)}:</div>
                        <div class="property-value">${escapeHtml(formatPropertyValue(prop.value))}</div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Code flows
    const codeFlows = result.codeFlows || [];
    if (codeFlows.length > 0) {
        html += `<div class="detail-section"><h4>Execution Flow</h4>`;
        codeFlows.forEach((flow, flowIndex) => {
            const threadFlows = flow.threadFlows || [];
            threadFlows.forEach(threadFlow => {
                const locations = threadFlow.locations || [];
                html += `<div class="code-flow">`;
                locations.forEach((loc, idx) => {
                    const msg = loc.location?.message?.text || threadFlow.message?.text || 'Step';
                    const locInfo = loc.location?.physicalLocation;
                    const locUri = locInfo?.artifactLocation?.uri?.replace(/^file:\/\//, '') || '';
                    const locLine = locInfo?.region?.startLine || '';
                    
                    html += `
                        <div class="flow-step">
                            <div class="flow-number">${idx + 1}</div>
                            <div class="flow-content">
                                <div class="flow-message">${escapeHtml(msg)}</div>
                                ${locUri ? `<div class="flow-location">${escapeHtml(locUri)}${locLine ? `:${locLine}` : ''}</div>` : ''}
                            </div>
                        </div>
                    `;
                });
                html += `</div>`;
            });
        });
        html += `</div>`;
    }
    
    return html || '<div class="detail-content">No additional details available.</div>';
}

// Render code snippet with line numbers
function renderCodeSnippet(snippet, location) {
    const lines = snippet.split('\n');
    const startLine = location.contextRegion?.startLine || location.region?.startLine || 1;
    const vulnerableStart = location.region?.startLine || 0;
    const vulnerableEnd = location.region?.endLine || 0;
    
    return lines.map((line, idx) => {
        const lineNum = startLine + idx;
        const isVulnerable = lineNum >= vulnerableStart && lineNum <= vulnerableEnd;
        const style = isVulnerable ? ' style="background: rgba(220, 38, 38, 0.1);"' : '';
        return `<span class="code-line"${style}><span class="code-line-number">${lineNum}</span>${escapeHtml(line)}</span>`;
    }).join('\n');
}

// Get additional properties from result
function getAdditionalProperties(result) {
    const props = [];
    const properties = result.properties || {};
    const skipKeys = ['type', 'confidence', 'exploitable', 'explanation', 'test_purpose'];
    
    Object.keys(properties).forEach(key => {
        if (skipKeys.includes(key)) return;
        
        const value = properties[key];
        if (value !== null && value !== undefined && value !== '') {
            props.push({ key, value });
        }
    });
    
    // Add confidence if present
    if (properties.confidence !== undefined) {
        props.unshift({ key: 'Confidence', value: properties.confidence });
    }
    
    return props;
}

// Format property value
function formatPropertyValue(value) {
    if (typeof value === 'object') {
        return JSON.stringify(value, null, 2);
    }
    return String(value);
}

// Handle metric card clicks for filtering
function handleMetricCardClick(card) {
    const filterType = card.dataset.filterType;
    const filterValue = card.dataset.filterValue;
    
    if (filterType !== 'severity') return; // Only handle severity filters
    
    // Update active state on cards
    document.querySelectorAll('.metric-card').forEach(c => c.classList.remove('active'));
    
    const severityFilter = document.getElementById('severity-filter');
    // Toggle filter - if already selected, clear it
    if (severityFilter.value === filterValue) {
        severityFilter.value = '';
    } else {
        severityFilter.value = filterValue;
        card.classList.add('active');
    }
    
    filterResults();
}

// Filter results
function filterResults() {
    const severityFilter = document.getElementById('severity-filter').value;
    const typeFilter = document.getElementById('type-filter').value;
    
    // Update active state on metric cards based on current filters
    document.querySelectorAll('.metric-card').forEach(card => {
        const filterType = card.dataset.filterType;
        const filterValue = card.dataset.filterValue;
        
        if (filterType === 'severity' && severityFilter === filterValue) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
    
    const rows = document.querySelectorAll('.finding-row');
    rows.forEach(row => {
        const severity = row.dataset.severity;
        const type = row.dataset.type;
        const exploitable = row.dataset.exploitable === 'true';
        const resultIndex = row.dataset.resultIndex;
        
        const matchesSeverity = !severityFilter || severity === severityFilter;
        const matchesType = !typeFilter || type === typeFilter;
        
        // Exploitable filter logic:
        // - If showOnlyExploitable is true, only show exploitable items
        // - Otherwise show all
        const matchesExploitable = !showOnlyExploitable || exploitable;
        
        const visible = matchesSeverity && matchesType && matchesExploitable;
        row.style.display = visible ? '' : 'none';
        
        // Also hide/show the corresponding detail row
        const detailRow = document.querySelector(`.detail-row[data-result-index="${resultIndex}"]`);
        if (detailRow) {
            detailRow.style.display = visible ? '' : 'none';
        }
    });
}

// Toggle exploitable visibility
function toggleExploitableVisibility() {
    const btn = document.getElementById('toggle-exploitable-btn');
    
    // Toggle between showing only exploitable and showing all
    showOnlyExploitable = !showOnlyExploitable;
    
    if (showOnlyExploitable) {
        // Now showing only exploitable
        btn.innerHTML = `
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            Show Non-exploitable
        `;
        btn.classList.add('secondary');
    } else {
        // Now showing all
        btn.innerHTML = `
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
            </svg>
            Hide Non-exploitable
        `;
        btn.classList.remove('secondary');
    }
    
    filterResults();
}

// Expand all findings
function expandAllRows() {
    document.querySelectorAll('.finding-row').forEach(row => {
        if (row.style.display !== 'none') {
            row.classList.add('expanded');
            const resultIndex = row.dataset.resultIndex;
            const detailRow = document.querySelector(`.detail-row[data-result-index="${resultIndex}"]`);
            if (detailRow) {
                detailRow.classList.add('visible');
            }
        }
    });
}

// Collapse all findings
function collapseAllRows() {
    document.querySelectorAll('.finding-row').forEach(row => {
        row.classList.remove('expanded');
    });
    document.querySelectorAll('.detail-row').forEach(row => {
        row.classList.remove('visible');
    });
}

// Sort table by column
function sortTable(column) {
    if (currentSortColumn === column) {
        // Toggle direction
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        // New column, default to ascending
        currentSortColumn = column;
        currentSortDirection = 'asc';
    }
    
    // Re-render current tab with new sort
    const tab = processedData.tabs.find(t => t.name === currentTab);
    if (tab) {
        renderFindings(tab.results);
    }
}

// Threat model functionality
async function loadThreatModel() {
    try {
        // Check if embedded threat model data exists
        if (!embeddedThreatModelData) {
            // If no embedded threat model data, hide the section
            return;
        }

        // Decode the base64 encoded threat model data
        const markdownText = atob(embeddedThreatModelData);
        const htmlContent = markdownToHtml(markdownText);

        // Show the threat model section
        const section = document.getElementById('threat-model-section');
        section.style.display = 'block';

        // Create preview (first few sections)
        const previewContainer = document.getElementById('threat-model-preview');
        const fullContainer = document.getElementById('threat-model-full');

        // Extract preview content (up to "Architecture" section or first 500 characters)
        const previewContent = createPreviewContent(htmlContent);
        previewContainer.innerHTML = previewContent;
        fullContainer.innerHTML = htmlContent;

    } catch (error) {
        console.log('Threat model not available:', error.message);
        // Hide section if file doesn't exist or can't be loaded
    }
}

function createPreviewContent(fullHtml) {
    // Simple preview: show content until we hit an h2 or reach character limit
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = fullHtml;

    const elements = tempDiv.children;
    let previewHtml = '';
    let charCount = 0;
    const maxChars = 800;

    for (let element of elements) {
        if (element.tagName === 'H2' && charCount > 100) {
            // Stop at second h2 if we have some content
            break;
        }

        const elementText = element.textContent || '';
        if (charCount + elementText.length > maxChars && charCount > 200) {
            break;
        }

        previewHtml += element.outerHTML;
        charCount += elementText.length;
    }

    return previewHtml;
}

function markdownToHtml(markdown) {
    // Simple markdown to HTML converter for basic elements
    let html = escapeHtml(markdown);

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Tables (simple)
    html = html.replace(/^\|(.+)\|$/gm, (match) => {
        const cells = match.split('|').slice(1, -1).map(cell => cell.trim());
        if (match.includes('---')) {
            return '<tr>' + cells.map(cell => `<th>${cell}</th>`).join('') + '</tr>';
        } else {
            return '<tr>' + cells.map(cell => `<td>${cell}</td>`).join('') + '</tr>';
        }
    });

    // Wrap table rows
    html = html.replace(/(<tr>.*<\/tr>\s*)+/g, '<table>$&</table>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code blocks
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Lists
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\s*)+/g, '<ul>$&</ul>');

    // Paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';

    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>\s*<h/g, '<h');
    html = html.replace(/<\/h[1-6]>\s*<\/p>/g, '</h1>');
    html = html.replace(/<p>\s*<ul>/g, '<ul>');
    html = html.replace(/<\/ul>\s*<\/p>/g, '</ul>');
    html = html.replace(/<p>\s*<table>/g, '<table>');
    html = html.replace(/<\/table>\s*<\/p>/g, '</table>');
    html = html.replace(/<p>\s*<pre>/g, '<pre>');
    html = html.replace(/<\/pre>\s*<\/p>/g, '</pre>');

    return html;
}

function toggleThreatModel() {
    const btn = document.getElementById('threat-model-toggle-btn');
    const preview = document.getElementById('threat-model-preview');
    const full = document.getElementById('threat-model-full');

    const isExpanded = btn.classList.contains('expanded');

    if (isExpanded) {
        // Collapse to preview
        btn.classList.remove('expanded');
        btn.classList.add('collapsed');
        preview.style.display = 'block';
        full.style.display = 'none';
        btn.querySelector('.toggle-text').textContent = 'See More';
    } else {
        // Expand to full
        btn.classList.remove('collapsed');
        btn.classList.add('expanded');
        preview.style.display = 'none';
        full.style.display = 'block';
        btn.querySelector('.toggle-text').textContent = 'See Less';
    }
}

// Event listeners
// Mobile menu toggle functionality
function toggleMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (mobileMenuToggle && navMenu) {
        mobileMenuToggle.classList.toggle('active');
        navMenu.classList.toggle('active');
    }
}

function closeMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (mobileMenuToggle && navMenu) {
        mobileMenuToggle.classList.remove('active');
        navMenu.classList.remove('active');
    }
}

function setupEventListeners() {
    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', toggleMobileMenu);
    }

    // Close mobile menu when clicking nav links
    const navMenu = document.getElementById('nav-menu');
    if (navMenu) {
        navMenu.addEventListener('click', (e) => {
            if (e.target.classList.contains('nav-link')) {
                closeMobileMenu();
            }
        });
    }

    document.addEventListener('click', (e) => {
        // Theme toggle
        const themeToggle = e.target.closest('#theme-toggle-btn');
        if (themeToggle) {
            toggleTheme();
            return;
        }

        // Close mobile menu when clicking outside
        const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
        const navMenu = document.getElementById('nav-menu');
        if (mobileMenuToggle && navMenu) {
            const isClickInsideMenu = navMenu.contains(e.target);
            const isClickOnToggle = mobileMenuToggle.contains(e.target);

            if (!isClickInsideMenu && !isClickOnToggle && navMenu.classList.contains('active')) {
                closeMobileMenu();
            }
        }
        
        // Metric card filtering
        const metricCard = e.target.closest('.metric-card');
        if (metricCard) {
            handleMetricCardClick(metricCard);
            return;
        }
        
        // Table row expansion
        const findingRow = e.target.closest('.finding-row');
        if (findingRow) {
            const resultIndex = findingRow.dataset.resultIndex;
            const detailRow = document.querySelector(`.detail-row[data-result-index="${resultIndex}"]`);
            
            findingRow.classList.toggle('expanded');
            if (detailRow) {
                detailRow.classList.toggle('visible');
            }
            return;
        }
        
        // Column sorting
        const sortable = e.target.closest('.sortable');
        if (sortable) {
            const column = sortable.dataset.column;
            sortTable(column);
            return;
        }
    });
    
    // Filters
    document.getElementById('severity-filter').addEventListener('change', filterResults);
    document.getElementById('type-filter').addEventListener('change', filterResults);
    
    // Control buttons
    document.getElementById('expand-all-btn').addEventListener('click', expandAllRows);
    document.getElementById('collapse-all-btn').addEventListener('click', collapseAllRows);
    document.getElementById('toggle-exploitable-btn').addEventListener('click', toggleExploitableVisibility);

    // Threat model toggle
    const threatModelToggle = document.getElementById('threat-model-toggle-btn');
    if (threatModelToggle) {
        threatModelToggle.addEventListener('click', toggleThreatModel);
    }
}

// Escape HTML to prevent XSS
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Initialize theme before page load to prevent flash
initTheme();

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
