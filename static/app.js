// Global variables
let currentJob = null;
let currentBuild = null;
let refreshInterval = null;
let isDarkMode = false;
let selectedJobType = null;
let currentJobName = null;
let currentJobType = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Jenkins UI Application Initialized');
    initializeTheme();
    loadDashboard();
    startAutoRefresh();
    
    // Add event listeners for job type selection
    document.addEventListener('click', function(e) {
        if (e.target.closest('.job-type-option')) {
            const option = e.target.closest('.job-type-option');
            const jobType = option.dataset.type;
            
            // Remove selection from all options
            document.querySelectorAll('.job-type-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            
            // Select clicked option
            option.classList.add('selected');
            selectedJobType = jobType;
            
            // Show dynamic fields based on job type
            showDynamicFields(jobType);
        }
    });
    
    // Add form submit handler
    const createJobForm = document.getElementById('create-job-form');
    if (createJobForm) {
        createJobForm.addEventListener('submit', handleCreateJob);
    }
});

// Theme management
function initializeTheme() {
    const savedTheme = localStorage.getItem('jenkins-theme');
    if (savedTheme === 'dark') {
        toggleDarkMode();
    }
}

function toggleDarkMode() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('dark-mode', isDarkMode);
    localStorage.setItem('jenkins-theme', isDarkMode ? 'dark' : 'light');
    
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        toggleBtn.textContent = isDarkMode ? '☀️' : '🌙';
    }
}

// Navigation functions
function showDashboard() {
    hideAllSections();
    document.getElementById('dashboard-section').style.display = 'block';
    setActiveTab(0);
    loadDashboard();
}

function showJobs() {
    hideAllSections();
    document.getElementById('jobs-section').style.display = 'block';
    setActiveTab(1);
    loadJobs();
}

function showNodes() {
    hideAllSections();
    document.getElementById('nodes-section').style.display = 'block';
    setActiveTab(2);
    loadNodes();
}

function showQueue() {
    hideAllSections();
    document.getElementById('queue-section').style.display = 'block';
    setActiveTab(3);
    loadQueue();
}

function showPlugins() {
    hideAllSections();
    document.getElementById('plugins-section').style.display = 'block';
    setActiveTab(4);
    loadPlugins();
}

function showGit() {
    hideAllSections();
    document.getElementById('git-section').style.display = 'block';
    setActiveTab(5);
    loadGitRepositories();
}

function hideAllSections() {
    const sections = ['dashboard-section', 'jobs-section', 'nodes-section', 'queue-section', 'plugins-section', 'git-section', 'console-section'];
    sections.forEach(section => {
        const element = document.getElementById(section);
        if (element) {
            element.style.display = 'none';
        }
    });
}

function setActiveTab(index) {
    const tabs = document.querySelectorAll('.nav-tabs button');
    tabs.forEach(tab => tab.classList.remove('active'));
    if (tabs[index]) {
        tabs[index].classList.add('active');
    }
}

// Enhanced Status Detection Functions
function getStatusClass(statusInput) {
    if (!statusInput) return 'status-unknown';
    const status = String(statusInput).toLowerCase();
    
    if (status === 'success' || status === 'stable') return 'status-success';
    if (status === 'failure' || status === 'failed') return 'status-failure';
    if (status === 'unstable') return 'status-unstable';
    if (status === 'aborted' || status === 'cancelled') return 'status-aborted';
    if (status === 'not_built' || status === 'disabled') return 'status-disabled';
    
    if (status.includes('blue')) return 'status-success';
    if (status.includes('red')) return 'status-failure';
    if (status.includes('yellow')) return 'status-unstable';
    if (status.includes('grey') || status.includes('gray')) return 'status-disabled';
    if (status.includes('aborted')) return 'status-aborted';
    if (status.includes('anime') || status.includes('blinking')) return 'status-building';
    
    if (status.includes('success') || status.includes('pass')) return 'status-success';
    if (status.includes('fail') || status.includes('error')) return 'status-failure';
    if (status.includes('building') || status.includes('running')) return 'status-building';
    if (status.includes('pending') || status.includes('queued')) return 'status-unknown';
    
    return 'status-unknown';
}

function getStatusText(statusInput) {
    if (!statusInput) return 'Unknown';
    const status = String(statusInput).toLowerCase();
    
    if (status === 'success' || status === 'stable') return 'Success';
    if (status === 'failure' || status === 'failed') return 'Failed';
    if (status === 'unstable') return 'Unstable';
    if (status === 'aborted' || status === 'cancelled') return 'Aborted';
    if (status === 'not_built' || status === 'disabled') return 'Disabled';
    
    if (status.includes('blue')) return 'Success';
    if (status.includes('red')) return 'Failed';
    if (status.includes('yellow')) return 'Unstable';
    if (status.includes('grey') || status.includes('gray')) return 'Disabled';
    if (status.includes('aborted')) return 'Aborted';
    if (status.includes('anime') || status.includes('blinking')) return 'Building';
    
    if (status.includes('success') || status.includes('pass')) return 'Success';
    if (status.includes('fail') || status.includes('error')) return 'Failed';
    if (status.includes('building') || status.includes('running')) return 'Building';
    if (status.includes('pending') || status.includes('queued')) return 'Pending';
    
    return 'Unknown';
}

function getBuildStatus(build) {
    if (build.result) {
        return {
            class: getStatusClass(build.result),
            text: getStatusText(build.result)
        };
    }
    
    if (build.color) {
        return {
            class: getStatusClass(build.color),
            text: getStatusText(build.color)
        };
    }
    
    if (build.status) {
        return {
            class: getStatusClass(build.status),
            text: getStatusText(build.status)
        };
    }
    
    if (build.building === true) {
        return {
            class: 'status-building',
            text: 'Building'
        };
    }
    
    return {
        class: 'status-unknown',
        text: 'Unknown'
    };
}

function getJobTypeBadge(jobType) {
    const badges = {
        'freestyle': '<span class="job-type-badge freestyle">Freestyle</span>',
        'pipeline': '<span class="job-type-badge pipeline">Pipeline</span>',
        'multibranch': '<span class="job-type-badge multibranch">Multibranch</span>',
        'external': '<span class="job-type-badge external">External</span>',
        'matrix': '<span class="job-type-badge matrix">Matrix</span>',
        'folder': '<span class="job-type-badge folder">Folder</span>',
        'organization': '<span class="job-type-badge organization">Organization</span>',
        'unknown': '<span class="job-type-badge unknown">Unknown</span>'
    };
    return badges[jobType] || badges['unknown'];
}

function getJobTypeIcon(jobType) {
    const icons = {
        'freestyle': '🔧',
        'pipeline': '🔄',
        'multibranch': '🌳',
        'external': '🌐',
        'matrix': '🔢',
        'folder': '📁',
        'organization': '🏢',
        'unknown': '❓'
    };
    return icons[jobType] || icons['unknown'];
}

// Dashboard functions
function loadDashboard() {
    loadStatistics();
    loadRecentJobs();
}

function loadStatistics() {
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const stats = data.statistics;
                document.getElementById('total-jobs').textContent = stats.total_jobs;
                document.getElementById('total-nodes').textContent = stats.total_nodes;
                document.getElementById('queue-size').textContent = stats.queue_size;
                document.getElementById('jenkins-version').textContent = stats.jenkins_version;
            } else {
                showError('Failed to load statistics: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
            showError('Failed to load statistics');
        });
}

function loadRecentJobs() {
    fetch('/api/jobs')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayRecentJobs(data.jobs.slice(0, 5));
            } else {
                showError('Failed to load jobs: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading jobs:', error);
            showError('Failed to load jobs');
        });
}

function displayRecentJobs(jobs) {
    const container = document.getElementById('recent-jobs-list');
    if (!container) return;
    
    if (jobs.length === 0) {
        container.innerHTML = '<p>No jobs found</p>';
        return;
    }

    const jobsHtml = jobs.map(job => {
        const buildStatus = getBuildStatus(job);
        const jobType = job.job_type || 'unknown';
        const jobTypeIcon = getJobTypeIcon(jobType);
        
        return `
            <div class="job-card" onclick="showJobPopup('${job.name}')">
                <div class="job-header">
                    <span class="job-icon">${jobTypeIcon}</span>
                    <h4>${job.name}</h4>
                    ${getJobTypeBadge(jobType)}
                </div>
                <div class="status ${buildStatus.class}">${buildStatus.text}</div>
                <p class="job-description">${job.description || 'No description'}</p>
            </div>
        `;
    }).join('');
    
    container.innerHTML = jobsHtml;
}

// Jobs functions - COLUMN LAYOUT
function loadJobs() {
    fetch('/api/jobs')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayJobsInColumns(data.jobs);
            } else {
                showError('Failed to load jobs: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading jobs:', error);
            showError('Failed to load jobs');
        });
}

function displayJobsInColumns(jobs) {
    const container = document.getElementById('jobs-list');
    if (!container) return;
    
    if (jobs.length === 0) {
        container.innerHTML = '<p>No jobs found. <a href="#" onclick="showCreateJobModal()">Create your first job</a></p>';
        return;
    }

    const jobsHtml = jobs.map(job => {
        const buildStatus = getBuildStatus(job);
        const jobType = job.job_type || 'unknown';
        const jobTypeIcon = getJobTypeIcon(jobType);
        
        const nonBuildableTypes = ['folder', 'organization'];
        const isBuildable = !nonBuildableTypes.includes(jobType);
        
        return `
            <div class="job-item" onclick="showJobPopup('${job.name}')">
                <div class="job-info">
                    <div class="job-title">
                        <span class="job-icon">${jobTypeIcon}</span>
                        <span class="job-name">${job.name}</span>
                        ${getJobTypeBadge(jobType)}
                    </div>
                    <div class="job-status">
                        <span class="status ${buildStatus.class}">${buildStatus.text}</span>
                    </div>
                </div>
                <div class="job-description">${job.description || 'No description'}</div>
                <div class="job-actions">
                    ${isBuildable ? `<button onclick="event.stopPropagation(); triggerBuild('${job.name}')" class="btn btn-primary">🚀 Build</button>` : ''}
                    <button onclick="event.stopPropagation(); showJobConfig('${job.name}')" class="btn btn-secondary">⚙️ Configure</button>
                    <button onclick="event.stopPropagation(); showJobPopup('${job.name}')" class="btn btn-info">📋 View Details</button>
                    <button onclick="event.stopPropagation(); deleteJob('${job.name}')" class="btn btn-danger">🗑️ Delete</button>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = jobsHtml;
}

// NEW: Enhanced Job Configuration Functions - NOW AS POPUP MODAL
function showJobConfig(jobName) {
    currentJobName = jobName;
    const configModal = document.getElementById('job-config-modal');
    const configModalBody = document.querySelector('.config-modal-body');
    
    if (configModal && configModalBody) {
        configModal.style.display = 'block';
        configModalBody.innerHTML = '<div class="loading">Loading job configuration...</div>';
        
        // Setup button event listeners
        setupConfigModalButtons(jobName);
    }
    
    fetch(`/api/job/${encodeURIComponent(jobName)}/config`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentJobType = data.job_type;
                displayJobConfigModal(jobName, data.job_type, data.config);
            } else {
                showError('Failed to load job configuration: ' + data.error);
                closeJobConfig();
            }
        })
        .catch(error => {
            console.error('Error loading job configuration:', error);
            showError('Failed to load job configuration');
            closeJobConfig();
        });
}

function setupConfigModalButtons(jobName) {
    const saveBtn = document.getElementById('save-config-btn');
    const applyBtn = document.getElementById('apply-config-btn');
    
    if (saveBtn) {
        saveBtn.onclick = () => saveJobConfig(jobName, currentJobType, true);
    }
    
    if (applyBtn) {
        applyBtn.onclick = () => saveJobConfig(jobName, currentJobType, false);
    }
}

function displayJobConfigModal(jobName, jobType, config) {
    const configModalBody = document.querySelector('.config-modal-body');
    const modalHeader = document.querySelector('#job-config-modal .modal-header h2');
    
    if (modalHeader) {
        modalHeader.innerHTML = `⚙️ Configure: ${jobName} ${getJobTypeBadge(jobType)}`;
    }
    
    if (!configModalBody) return;
    
    const jobTypeIcon = getJobTypeIcon(jobType);
    
    let configContent = '';
    
    switch(jobType) {
        case 'freestyle':
            // ENHANCED: Freestyle with SCM support (like Jenkins interface)
            const currentBuildStepType = config.build_step_type || 'shell';
            const currentScmType = config.scm_type || 'none';
            configContent = `
                <h4>${jobTypeIcon} Freestyle Project Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Job description...">${config.description || ''}</textarea>
                    </div>
                    
                    <!-- Source Code Management Section (like Jenkins interface) -->
                    <div class="config-section scm-section">
                        <h5>📁 Source Code Management</h5>
                        <div class="scm-selector">
                            <div class="scm-radio-group">
                                <div class="scm-option">
                                    <input type="radio" id="scm-none" name="scm_type" value="none" ${currentScmType === 'none' ? 'checked' : ''}>
                                    <label for="scm-none">None</label>
                                </div>
                                <div class="scm-option">
                                    <input type="radio" id="scm-git" name="scm_type" value="git" ${currentScmType === 'git' ? 'checked' : ''}>
                                    <label for="scm-git">📁 Git</label>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Git Configuration Fields (Enhanced like Jenkins) -->
                    <div id="git-config-fields" class="conditional-fields git-config-panel" style="display: ${currentScmType === 'git' ? 'block' : 'none'}">
                        <!-- Repositories Section -->
                        <div class="config-subsection">
                            <h6>🔗 Repositories</h6>
                            <div class="repository-config-group">
                                <div class="form-field">
                                    <label for="config-repository-url">Repository URL <span class="required">*</span></label>
                                    <input type="url" id="config-repository-url" name="repository_url" 
                                           placeholder="https://github.com/user/repo.git" 
                                           value="${config.repository_url || ''}"
                                           class="form-control">
                                    <small class="error-message" id="repo-url-error" style="display: none;">
                                        ⚠️ Please enter a valid Git repository URL
                                    </small>
                                </div>
                                
                                <div class="form-field">
                                    <label for="config-credentials">Credentials</label>
                                    <div class="credentials-row">
                                        <select id="config-credentials" name="credentials_id" class="form-control">
                                            <option value="">- none -</option>
                                        </select>
                                        <button type="button" class="btn btn-sm btn-secondary" onclick="loadCredentials()" title="Refresh credentials list">
                                            🔄
                                        </button>
                                        <button type="button" class="btn btn-sm btn-info" onclick="addCredential()" title="Add new credential">
                                            ➕ Add
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Branches to build Section -->
                        <div class="config-subsection">
                            <h6>🌿 Branches to build</h6>
                            <div class="branches-config">
                                <div class="form-field">
                                    <label for="config-branch-specifier">Branch Specifier (blank for 'any')</label>
                                    <input type="text" id="config-branch-specifier" name="branch_specifier" 
                                           placeholder="*/master" 
                                           value="${config.branch_specifier || '*/master'}"
                                           class="form-control">
                                    <small class="help-text">
                                        💡 Specify the branches to build. Use wildcards like <code>*/master</code>, <code>*/develop</code>, or <code>feature/*</code>
                                    </small>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Repository browser Section -->
                        <div class="config-subsection">
                            <h6>🌐 Repository browser</h6>
                            <div class="form-field">
                                <select id="config-repository-browser" name="repository_browser" class="form-control">
                                    <option value="auto" ${(config.repository_browser || 'auto') === 'auto' ? 'selected' : ''}>(Auto)</option>
                                    <option value="github" ${config.repository_browser === 'github' ? 'selected' : ''}>GitHub</option>
                                    <option value="gitlab" ${config.repository_browser === 'gitlab' ? 'selected' : ''}>GitLab</option>
                                    <option value="bitbucket" ${config.repository_browser === 'bitbucket' ? 'selected' : ''}>Bitbucket</option>
                                    <option value="cgit" ${config.repository_browser === 'cgit' ? 'selected' : ''}>cgit</option>
                                    <option value="gitweb" ${config.repository_browser === 'gitweb' ? 'selected' : ''}>GitWeb</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- Additional Behaviours Section (like Jenkins) -->
                        <div class="config-subsection">
                            <h6>⚙️ Additional Behaviours</h6>
                            <div class="behaviours-config">
                                <select id="additional-behaviours" class="form-control" onchange="addBehaviour(this.value)">
                                    <option value="">Add</option>
                                    <option value="clean-checkout">🧹 Clean before checkout</option>
                                    <option value="shallow-clone">📦 Shallow clone (--depth 1)</option>
                                    <option value="sparse-checkout">📂 Sparse Checkout paths</option>
                                    <option value="submodule">🔗 Git LFS pull after checkout</option>
                                    <option value="polling-ignores-commits">⏭️ Polling ignores commits in certain paths</option>
                                </select>
                                <div id="selected-behaviours" class="selected-behaviours"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <label for="config-build-step-type">Build Step Type:</label>
                        <select id="config-build-step-type" name="build_step_type" class="form-control">
                            <option value="shell" ${currentBuildStepType === 'shell' ? 'selected' : ''}>🐧 Execute shell (Unix/Linux)</option>
                            <option value="batch" ${currentBuildStepType === 'batch' ? 'selected' : ''}>🪟 Execute Windows batch command</option>
                        </select>
                        <p class="help-text">Choose the appropriate build step type based on your Jenkins agent's operating system.</p>
                    </div>
                    
                    <div class="config-section">
                        <label for="config-build-steps">Build Commands:</label>
                        <textarea id="config-build-steps" name="build_steps" rows="8" 
                                  placeholder="Enter build commands..." class="form-control">${config.build_steps || ''}</textarea>
                        <p class="help-text" id="build-step-help">
                            ${currentBuildStepType === 'batch' ? 
                                '💻 Windows batch commands (e.g., echo Hello World, dir, cd /d "C:\\path")' : 
                                '🐧 Shell commands (e.g., echo "Hello World", ls, cd /path)'
                            }
                        </p>
                    </div>
                    
                    <div class="config-section">
                        <label>
                            <input type="checkbox" name="disabled" ${config.disabled ? 'checked' : ''}> 
                            Disable this project
                        </label>
                    </div>
                </form>
            `;
            break;
            
        case 'matrix':
            // ENHANCED: Matrix with SCM support
            const matrixScmType = config.scm_type || 'none';
            configContent = `
                <h4>${jobTypeIcon} Multi-configuration Project</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Job description...">${config.description || ''}</textarea>
                    </div>
                    
                    <!-- Source Code Management Section for Matrix -->
                    <div class="config-section scm-section">
                        <h5>📁 Source Code Management</h5>
                        <div class="scm-selector">
                            <div class="scm-radio-group">
                                <div class="scm-option">
                                    <input type="radio" id="matrix-scm-none" name="scm_type" value="none" ${matrixScmType === 'none' ? 'checked' : ''}>
                                    <label for="matrix-scm-none">None</label>
                                </div>
                                <div class="scm-option">
                                    <input type="radio" id="matrix-scm-git" name="scm_type" value="git" ${matrixScmType === 'git' ? 'checked' : ''}>
                                    <label for="matrix-scm-git">📁 Git</label>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Git Configuration Fields for Matrix -->
                    <div id="matrix-git-config-fields" class="conditional-fields git-config-panel" style="display: ${matrixScmType === 'git' ? 'block' : 'none'}">
                        <div class="config-subsection">
                            <h6>🔗 Repositories</h6>
                            <div class="form-field">
                                <label for="matrix-config-repository-url">Repository URL <span class="required">*</span></label>
                                <input type="url" id="matrix-config-repository-url" name="repository_url" 
                                       placeholder="https://github.com/user/repo.git" 
                                       value="${config.repository_url || ''}" class="form-control">
                            </div>
                            
                            <div class="form-field">
                                <label for="matrix-config-credentials">Credentials</label>
                                <select id="matrix-config-credentials" name="credentials_id" class="form-control">
                                    <option value="">- none -</option>
                                </select>
                            </div>
                            
                            <div class="form-field">
                                <label for="matrix-config-branch-specifier">Branch Specifier</label>
                                <input type="text" id="matrix-config-branch-specifier" name="branch_specifier" 
                                       placeholder="*/master" value="${config.branch_specifier || '*/master'}" class="form-control">
                            </div>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <label for="config-axis-name">Configuration Axis Name:</label>
                        <input type="text" id="config-axis-name" name="axis_name" placeholder="environment" value="${config.axis_name || 'environment'}">
                    </div>
                    <div class="config-section">
                        <label for="config-axis-values">Axis Values (comma-separated):</label>
                        <input type="text" id="config-axis-values" name="axis_values" placeholder="dev,test,prod" value="${config.axis_values || 'dev,test,prod'}">
                    </div>
                    <div class="config-section">
                        <label for="config-build-steps">Build Steps:</label>
                        <textarea id="config-build-steps" name="build_steps" rows="6" placeholder="Enter build commands...">${config.build_steps || ''}</textarea>
                    </div>
                </form>
            `;
            break;
            
        // Keep all other existing job type configurations unchanged
        case 'pipeline':
            const isScmPipeline = config.pipeline_definition_type === 'scm';
            configContent = `
                <h4>${jobTypeIcon} Pipeline Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Job description...">${config.description || ''}</textarea>
                    </div>
                    
                    <div class="config-section">
                        <label>Pipeline Definition:</label>
                        <div class="pipeline-definition-selector">
                            <div class="definition-option">
                                <input type="radio" id="config-pipeline-script" name="pipeline_definition_type" value="script" ${!isScmPipeline ? 'checked' : ''}>
                                <label for="config-pipeline-script">Pipeline script</label>
                            </div>
                            <div class="definition-option">
                                <input type="radio" id="config-pipeline-scm" name="pipeline_definition_type" value="scm" ${isScmPipeline ? 'checked' : ''}>
                                <label for="config-pipeline-scm">Pipeline script from SCM</label>
                            </div>
                        </div>
                    </div>
                    
                    <div id="config-script-fields" class="conditional-fields" style="display: ${!isScmPipeline ? 'block' : 'none'}">
                        <div class="config-section">
                            <label for="config-pipeline-script-content">Pipeline Script:</label>
                            <textarea id="config-pipeline-script-content" name="pipeline_script" rows="12" placeholder="Enter Jenkinsfile content...">${config.pipeline_script || ''}</textarea>
                        </div>
                    </div>
                    
                    <div id="config-scm-fields" class="conditional-fields" style="display: ${isScmPipeline ? 'block' : 'none'}">
                        <div class="config-section">
                            <label for="config-repository-url">Repository URL:</label>
                            <input type="url" id="config-repository-url" name="repository_url" placeholder="https://github.com/user/repo.git" value="${config.repository_url || ''}">
                        </div>
                        <div class="config-section">
                            <label for="config-branch">Branch Specifier:</label>
                            <input type="text" id="config-branch" name="branch" placeholder="main" value="${config.branch || 'main'}">
                        </div>
                        <div class="config-section">
                            <label for="config-script-path">Script Path:</label>
                            <input type="text" id="config-script-path" name="script_path" placeholder="Jenkinsfile" value="${config.script_path || 'Jenkinsfile'}">
                        </div>
                        <div class="config-section">
                            <label for="config-credentials-id">Credentials ID:</label>
                            <input type="text" id="config-credentials-id" name="credentials_id" placeholder="Enter credentials ID (optional)" value="${config.credentials_id || ''}">
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <label>
                            <input type="checkbox" name="disabled" ${config.disabled ? 'checked' : ''}> 
                            Do not allow concurrent builds
                        </label>
                    </div>
                </form>
            `;
            break;
            
        case 'multibranch':
            configContent = `
                <h4>${jobTypeIcon} Multibranch Pipeline Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Job description...">${config.description || ''}</textarea>
                    </div>
                    <div class="config-section">
                        <label for="config-repository-url">Repository URL:</label>
                        <input type="url" id="config-repository-url" name="repository_url" placeholder="https://github.com/user/repo.git" value="${config.repository_url || ''}">
                    </div>
                    <div class="config-section">
                        <label for="config-repo-id">Repository ID:</label>
                        <input type="text" id="config-repo-id" name="repo_id" placeholder="Repository identifier" value="${config.repo_id || ''}">
                    </div>
                    <div class="config-section">
                        <label>Build Configuration:</label>
                        <p class="help-text">Branches are automatically discovered and built based on Jenkinsfile presence.</p>
                    </div>
                </form>
            `;
            break;
            
        case 'external':
            configContent = `
                <h4>${jobTypeIcon} External Job Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Job description...">${config.description || ''}</textarea>
                    </div>
                    <div class="config-section">
                        <label>External Job Information:</label>
                        <p class="help-text">External jobs record execution of processes run outside Jenkins. Configure your external process to report results back to Jenkins using the Jenkins API.</p>
                    </div>
                </form>
            `;
            break;
            
        case 'folder':
            configContent = `
                <h4>${jobTypeIcon} Folder Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Folder description...">${config.description || ''}</textarea>
                    </div>
                    <div class="config-section">
                        <label>Folder Properties:</label>
                        <p class="help-text">Folders create containers for organizing Jenkins items into separate namespaces. Items in different folders can have the same name.</p>
                    </div>
                </form>
            `;
            break;
            
        case 'organization':
            configContent = `
                <h4>${jobTypeIcon} Organization Folder Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Organization description...">${config.description || ''}</textarea>
                    </div>
                    <div class="config-section">
                        <label for="config-organization-name">Organization Name:</label>
                        <input type="text" id="config-organization-name" name="organization_name" placeholder="GitHub/Bitbucket organization" value="${config.organization_name || ''}">
                    </div>
                    <div class="config-section">
                        <label>Scan Configuration:</label>
                        <p class="help-text">Organization folders automatically scan for repositories and create multibranch projects. Requires appropriate SCM plugins.</p>
                    </div>
                </form>
            `;
            break;
            
        default:
            configContent = `
                <h4>${jobTypeIcon} Job Configuration</h4>
                <form id="config-form">
                    <div class="config-section">
                        <label for="config-description">Description:</label>
                        <textarea id="config-description" name="description" rows="3" placeholder="Job description...">${config.description || ''}</textarea>
                    </div>
                    <div class="config-section">
                        <p>Advanced configuration options not available in this interface.</p>
                    </div>
                </form>
            `;
    }
    
    configModalBody.innerHTML = configContent;
    
    // Add event listeners for SCM type changes (Enhanced like Jenkins)
    if (jobType === 'freestyle' || jobType === 'matrix') {
        const scmRadios = document.querySelectorAll(`input[name="scm_type"]`);
        scmRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                const gitFields = document.getElementById(jobType === 'matrix' ? 'matrix-git-config-fields' : 'git-config-fields');
                const repoUrlError = document.getElementById('repo-url-error');
                
                if (this.value === 'git') {
                    gitFields.style.display = 'block';
                    loadCredentials(); // Load available credentials
                } else {
                    gitFields.style.display = 'none';
                    if (repoUrlError) repoUrlError.style.display = 'none';
                }
            });
        });
        
        // Load credentials on initial display if Git is selected
        if ((jobType === 'freestyle' && config.scm_type === 'git') || 
            (jobType === 'matrix' && config.scm_type === 'git')) {
            loadCredentials();
        }
    }
    
    // Keep existing event listeners for other features
    if (jobType === 'freestyle') {
        const buildStepTypeSelect = document.getElementById('config-build-step-type');
        const buildStepHelp = document.getElementById('build-step-help');
        
        if (buildStepTypeSelect && buildStepHelp) {
            buildStepTypeSelect.addEventListener('change', function() {
                const selectedType = this.value;
                if (selectedType === 'batch') {
                    buildStepHelp.innerHTML = '💻 Windows batch commands (e.g., echo Hello World, dir, cd /d "C:\\path")';
                } else {
                    buildStepHelp.innerHTML = '🐧 Shell commands (e.g., echo "Hello World", ls, cd /path)';
                }
            });
        }
    }
    
    if (jobType === 'pipeline') {
        document.addEventListener('change', function(e) {
            if (e.target.name === 'pipeline_definition_type') {
                const scriptFields = document.getElementById('config-script-fields');
                const scmFields = document.getElementById('config-scm-fields');
                
                if (e.target.value === 'script') {
                    scriptFields.style.display = 'block';
                    scmFields.style.display = 'none';
                } else if (e.target.value === 'scm') {
                    scriptFields.style.display = 'none';
                    scmFields.style.display = 'block';
                }
            }
        });
    }
}

// NEW: Load credentials function (Enhanced)
function loadCredentials() {
    fetch('/api/credentials')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const credentialsSelects = document.querySelectorAll('select[name="credentials_id"]');
                credentialsSelects.forEach(select => {
                    // Save current selection
                    const currentValue = select.value;
                    
                    // Clear existing options except the first one
                    select.innerHTML = '<option value="">- none -</option>';
                    
                    // Add credentials options
                    data.credentials.forEach(credential => {
                        const option = document.createElement('option');
                        option.value = credential.id;
                        option.textContent = `${credential.id} (${credential.description})`;
                        if (credential.id === currentValue) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                });
            } else {
                console.warn('Failed to load credentials:', data.error);
                showNotification('Failed to load credentials: ' + data.error, 'warning');
            }
        })
        .catch(error => {
            console.warn('Error loading credentials:', error);
            showNotification('Error loading credentials', 'warning');
        });
}

// NEW: Add credential function (Mock)
function addCredential() {
    // This would typically open a modal to add new credentials
    const credentialId = prompt('Enter credential ID:');
    const description = prompt('Enter description:');
    
    if (credentialId && description) {
        // Mock adding credential - in real implementation, this would make API call
        showNotification(`Credential "${credentialId}" would be added (mock implementation)`, 'info');
        loadCredentials(); // Refresh the list
    }
}

// NEW: Add behaviour function (Enhanced like Jenkins)
function addBehaviour(behaviourType) {
    if (!behaviourType) return;
    
    const behaviourContainer = document.getElementById('selected-behaviours');
    if (!behaviourContainer) return;
    
    const behaviourNames = {
        'clean-checkout': '🧹 Clean before checkout',
        'shallow-clone': '📦 Shallow clone (--depth 1)',
        'sparse-checkout': '📂 Sparse Checkout paths',
        'submodule': '🔗 Git LFS pull after checkout',
        'polling-ignores-commits': '⏭️ Polling ignores commits in certain paths'
    };
    
    const behaviourDiv = document.createElement('div');
    behaviourDiv.className = 'selected-behaviour';
    behaviourDiv.innerHTML = `
        <div class="behaviour-item">
            <span class="behaviour-name">${behaviourNames[behaviourType] || behaviourType}</span>
            <button type="button" class="btn btn-sm btn-danger" onclick="this.parentElement.parentElement.remove()">❌</button>
        </div>
    `;
    
    behaviourContainer.appendChild(behaviourDiv);
    
    // Reset dropdown
    document.getElementById('additional-behaviours').value = '';
}

// ENHANCED: Save Configuration Function with SCM support (FOR MODAL)
function saveJobConfig(jobName, jobType, shouldClose = true) {
    const form = document.getElementById('config-form');
    if (!form) {
        showError('Configuration form not found');
        return;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('save-config-btn');
    const applyBtn = document.getElementById('apply-config-btn');
    
    if (!saveBtn) {
        showError('Save button not found');
        return;
    }
    
    const originalSaveText = saveBtn.textContent;
    const originalApplyText = applyBtn ? applyBtn.textContent : '';
    
    if (shouldClose) {
        saveBtn.textContent = '💾 Saving...';
        saveBtn.disabled = true;
    } else {
        if (applyBtn) {
            applyBtn.textContent = '✅ Applying...';
            applyBtn.disabled = true;
        }
    }
    
    try {
        // Collect form data safely
        const formData = new FormData(form);
        const configData = {
            name: jobName,
            type: jobType,
            description: formData.get('description') || '',
            disabled: formData.has('disabled')
        };
        
        // Add job-type specific fields with validation
        switch(jobType) {
            case 'freestyle':
                configData.build_steps = formData.get('build_steps') || '';
                configData.build_step_type = formData.get('build_step_type') || 'shell';
                
                // Handle SCM configuration (Enhanced)
                configData.scm_type = formData.get('scm_type') || 'none';
                if (configData.scm_type === 'git') {
                    const repoUrl = formData.get('repository_url');
                    if (!repoUrl || repoUrl.trim() === '') {
                        showError('Repository URL is required for Git SCM');
                        const repoUrlError = document.getElementById('repo-url-error');
                        if (repoUrlError) repoUrlError.style.display = 'block';
                        resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
                        return;
                    }
                    configData.repository_url = repoUrl;
                    configData.credentials_id = formData.get('credentials_id') || '';
                    configData.branch_specifier = formData.get('branch_specifier') || '*/master';
                    configData.repository_browser = formData.get('repository_browser') || 'auto';
                }
                break;
                
            case 'matrix':
                configData.axis_name = formData.get('axis_name') || 'environment';
                configData.axis_values = formData.get('axis_values') || 'dev,test,prod';
                configData.build_steps = formData.get('build_steps') || '';
                
                // Handle SCM configuration for matrix jobs
                configData.scm_type = formData.get('scm_type') || 'none';
                if (configData.scm_type === 'git') {
                    const repoUrl = formData.get('repository_url');
                    if (!repoUrl || repoUrl.trim() === '') {
                        showError('Repository URL is required for Git SCM');
                        resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
                        return;
                    }
                    configData.repository_url = repoUrl;
                    configData.credentials_id = formData.get('credentials_id') || '';
                    configData.branch_specifier = formData.get('branch_specifier') || '*/master';
                }
                break;
                
            case 'pipeline':
                const pipelineDefType = formData.get('pipeline_definition_type') || 'script';
                configData.pipeline_definition_type = pipelineDefType;
                
                if (pipelineDefType === 'script') {
                    const pipelineScript = formData.get('pipeline_script');
                    if (!pipelineScript || pipelineScript.trim() === '') {
                        showError('Pipeline script is required');
                        resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
                        return;
                    }
                    configData.pipeline_script = pipelineScript;
                } else if (pipelineDefType === 'scm') {
                    const repoUrl = formData.get('repository_url');
                    if (!repoUrl || repoUrl.trim() === '') {
                        showError('Repository URL is required for SCM-based pipelines');
                        resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
                        return;
                    }
                    configData.repository_url = repoUrl;
                    configData.branch = formData.get('branch') || 'main';
                    configData.script_path = formData.get('script_path') || 'Jenkinsfile';
                    configData.credentials_id = formData.get('credentials_id') || '';
                }
                break;
                
            case 'multibranch':
                const multiRepoUrl = formData.get('repository_url');
                if (!multiRepoUrl || multiRepoUrl.trim() === '') {
                    showError('Repository URL is required for multibranch projects');
                    resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
                    return;
                }
                configData.repository_url = multiRepoUrl;
                configData.repo_id = formData.get('repo_id') || 'repo-1';
                break;
                
            case 'organization':
                const orgName = formData.get('organization_name');
                if (!orgName || orgName.trim() === '') {
                    showError('Organization name is required');
                    resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
                    return;
                }
                configData.organization_name = orgName;
                break;
                
            default:
                // For external, folder, and other types
                break;
        }
        
        console.log('Sending configuration data:', configData);
        
        // Save configuration with proper error handling
        fetch(`/api/job/${encodeURIComponent(jobName)}/config/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify(configData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                if (shouldClose) {
                    showSuccess(`✅ Configuration saved successfully for job: ${jobName}`);
                    closeJobConfig();
                } else {
                    showSuccess(`✅ Configuration applied successfully for job: ${jobName}`);
                }
                
                // Refresh job list if visible
                const jobsSection = document.getElementById('jobs-section');
                if (jobsSection && jobsSection.style.display !== 'none') {
                    setTimeout(() => loadJobs(), 500);
                }
                
                // Refresh dashboard if visible
                const dashboardSection = document.getElementById('dashboard-section');
                if (dashboardSection && dashboardSection.style.display !== 'none') {
                    setTimeout(() => loadDashboard(), 500);
                }
            } else {
                throw new Error(data.error || 'Unknown server error');
            }
        })
        .catch(error => {
            console.error('Error saving configuration:', error);
            const errorMessage = error.message || 'Failed to save configuration';
            showError(`❌ ${errorMessage}`);
        })
        .finally(() => {
            resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
        });
        
    } catch (error) {
        console.error('Form processing error:', error);
        showError(`❌ Form error: ${error.message}`);
        resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText);
    }
}

// Helper function to reset both save and apply button states
function resetSaveButtons(saveBtn, applyBtn, originalSaveText, originalApplyText) {
    if (saveBtn) {
        saveBtn.textContent = originalSaveText;
        saveBtn.disabled = false;
    }
    if (applyBtn) {
        applyBtn.textContent = originalApplyText;
        applyBtn.disabled = false;
    }
}

// NEW: Close Job Config Modal
function closeJobConfig() {
    const configModal = document.getElementById('job-config-modal');
    if (configModal) {
        configModal.style.display = 'none';
    }
    currentJobName = null;
    currentJobType = null;
}

// [Keep all other existing functions from the original app.js - they remain exactly the same]
// - Create Job Modal Functions
// - Job Management Functions (trigger, delete, etc.)
// - Popup Functions
// - Node, Queue, Plugin Functions
// - Utility Functions
// - Notification Functions

// Create Job Modal Functions with SCM support (keep all existing functions)
function showCreateJobModal() {
    const modal = document.getElementById('create-job-modal');
    if (modal) {
        modal.style.display = 'block';
        resetCreateJobForm();
    }
}

function closeCreateJobModal() {
    const modal = document.getElementById('create-job-modal');
    if (modal) {
        modal.style.display = 'none';
        resetCreateJobForm();
    }
}
function resetCreateJobForm() {
    const form = document.getElementById('create-job-form');
    if (form) {
        form.reset();
    }
    
    // Reset job type selection
    selectedJobType = null;
    document.querySelectorAll('.job-type-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Clear dynamic fields
    const dynamicFields = document.getElementById('dynamic-fields');
    if (dynamicFields) {
        dynamicFields.innerHTML = '';
    }
}

function showDynamicFields(jobType) {
    const dynamicFields = document.getElementById('dynamic-fields');
    if (!dynamicFields) return;
    
    let fieldsHtml = '';
    
    switch(jobType) {
        case 'freestyle':
            // ENHANCED: Freestyle with SCM support in create modal
            fieldsHtml = `
                <!-- Source Code Management Section -->
                <div class="form-group">
                    <label>📁 Source Code Management</label>
                    <div class="scm-selector">
                        <div class="scm-radio-group">
                            <div class="scm-option">
                                <input type="radio" id="create-scm-none" name="scm_type" value="none" checked>
                                <label for="create-scm-none">None</label>
                            </div>
                            <div class="scm-option">
                                <input type="radio" id="create-scm-git" name="scm_type" value="git">
                                <label for="create-scm-git">📁 Git</label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Git Configuration Fields -->
                <div id="create-git-config-fields" class="conditional-fields" style="display: none;">
                    <div class="form-group">
                        <label for="create-repository-url">Repository URL <span class="required">*</span></label>
                        <input type="url" id="create-repository-url" name="repository_url" 
                               placeholder="https://github.com/user/repo.git" class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label for="create-credentials">Credentials</label>
                        <select id="create-credentials" name="credentials_id" class="form-control">
                            <option value="">- none -</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="create-branch-specifier">Branch Specifier</label>
                        <input type="text" id="create-branch-specifier" name="branch_specifier" 
                               placeholder="*/master" value="*/master" class="form-control">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="build-step-type">Build Step Type</label>
                    <select id="build-step-type" name="build_step_type" class="form-control">
                        <option value="shell">🐧 Execute shell (Unix/Linux)</option>
                        <option value="batch">🪟 Execute Windows batch command</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="build-steps">Build Commands</label>
                    <textarea id="build-steps" name="build_steps" placeholder="Enter build commands (e.g., echo 'Hello World')" rows="4" class="form-control"></textarea>
                </div>
            `;
            break;
            
        case 'matrix':
            // ENHANCED: Matrix with SCM support in create modal
            fieldsHtml = `
                <!-- Source Code Management Section -->
                <div class="form-group">
                    <label>📁 Source Code Management</label>
                    <div class="scm-selector">
                        <div class="scm-radio-group">
                            <div class="scm-option">
                                <input type="radio" id="matrix-create-scm-none" name="scm_type" value="none" checked>
                                <label for="matrix-create-scm-none">None</label>
                            </div>
                            <div class="scm-option">
                                <input type="radio" id="matrix-create-scm-git" name="scm_type" value="git">
                                <label for="matrix-create-scm-git">📁 Git</label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Git Configuration Fields for Matrix -->
                <div id="matrix-create-git-config-fields" class="conditional-fields" style="display: none;">
                    <div class="form-group">
                        <label for="matrix-create-repository-url">Repository URL <span class="required">*</span></label>
                        <input type="url" id="matrix-create-repository-url" name="repository_url" 
                               placeholder="https://github.com/user/repo.git" class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label for="matrix-create-credentials">Credentials</label>
                        <select id="matrix-create-credentials" name="credentials_id" class="form-control">
                            <option value="">- none -</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="matrix-create-branch-specifier">Branch Specifier</label>
                        <input type="text" id="matrix-create-branch-specifier" name="branch_specifier" 
                               placeholder="*/master" value="*/master" class="form-control">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="axis-name">Configuration Axis Name</label>
                    <input type="text" id="axis-name" name="axis_name" placeholder="environment" value="environment" class="form-control">
                </div>
                <div class="form-group">
                    <label for="axis-values">Axis Values (comma-separated)</label>
                    <input type="text" id="axis-values" name="axis_values" placeholder="dev,test,prod" value="dev,test,prod" class="form-control">
                </div>
                <div class="form-group">
                    <label for="build-steps">Build Steps</label>
                    <textarea id="build-steps" name="build_steps" placeholder="Enter build commands" rows="4" class="form-control">echo "Matrix build for $environment"</textarea>
                </div>
            `;
            break;
            
        case 'pipeline':
            fieldsHtml = `
                <div class="form-group">
                    <label>Pipeline Definition *</label>
                    <div class="pipeline-definition-selector">
                        <div class="definition-option" data-definition="script">
                            <input type="radio" id="pipeline-script" name="pipeline_definition_type" value="script" checked>
                            <label for="pipeline-script">Pipeline script</label>
                            <p class="help-text">Define the pipeline script directly in Jenkins</p>
                        </div>
                        <div class="definition-option" data-definition="scm">
                            <input type="radio" id="pipeline-scm" name="pipeline_definition_type" value="scm">
                            <label for="pipeline-scm">Pipeline script from SCM</label>
                            <p class="help-text">Pipeline script is loaded from version control (recommended)</p>
                        </div>
                    </div>
                </div>
                
                <div id="pipeline-script-fields" class="conditional-fields">
                    <div class="form-group">
                        <label for="pipeline-script-content">Pipeline Script *</label>
                        <textarea id="pipeline-script-content" name="pipeline_script" placeholder="Enter Jenkinsfile content" rows="8">pipeline {
    agent any
    stages {
        stage('Hello') {
            steps {
                echo 'Hello World'
            }
        }
    }
}</textarea>
                    </div>
                </div>
                
                <div id="pipeline-scm-fields" class="conditional-fields" style="display: none;">
                    <div class="form-group">
                        <label for="scm-repository-url">Repository URL *</label>
                        <input type="url" id="scm-repository-url" name="repository_url" placeholder="https://github.com/user/repo.git">
                    </div>
                    <div class="form-group">
                        <label for="scm-branch">Branch Specifier</label>
                        <input type="text" id="scm-branch" name="branch" placeholder="main" value="main">
                    </div>
                    <div class="form-group">
                        <label for="script-path">Script Path</label>
                        <input type="text" id="script-path" name="script_path" placeholder="Jenkinsfile" value="Jenkinsfile">
                    </div>
                    <div class="form-group">
                        <label for="credentials-id">Credentials (optional)</label>
                        <input type="text" id="credentials-id" name="credentials_id" placeholder="Enter credentials ID if repository is private">
                    </div>
                </div>
            `;
            break;
            
        case 'multibranch':
            fieldsHtml = `
                <div class="form-group">
                    <label for="repository-url">Repository URL *</label>
                    <input type="url" id="repository-url" name="repository_url" placeholder="https://github.com/user/repo.git" required>
                </div>
                <div class="form-group">
                    <label for="repo-id">Repository ID</label>
                    <input type="text" id="repo-id" name="repo_id" placeholder="repo-1" value="repo-1">
                </div>
            `;
            break;
            
        case 'external':
            fieldsHtml = `
                <div class="form-group">
                    <label>Configuration Note</label>
                    <p class="help-text">External jobs record execution of processes run outside Jenkins. Configure your external process to report results back to Jenkins.</p>
                </div>
            `;
            break;
            
        case 'folder':
            fieldsHtml = `
                <div class="form-group">
                    <label>Folder Configuration</label>
                    <p class="help-text">Folders are containers that store nested items. They create separate namespaces allowing multiple items with the same name in different folders.</p>
                </div>
            `;
            break;
            
        case 'organization':
            fieldsHtml = `
                <div class="form-group">
                    <label for="organization-name">Organization/Owner Name *</label>
                    <input type="text" id="organization-name" name="organization_name" placeholder="myorg" required>
                </div>
                <div class="form-group">
                    <label>Configuration Note</label>
                    <p class="help-text">Organization folders scan GitHub/Bitbucket organizations for repositories and create multibranch projects automatically. Requires GitHub/Bitbucket plugins.</p>
                </div>
            `;
            break;
    }
    
    dynamicFields.innerHTML = fieldsHtml;
    
    // Add event listeners for SCM type switching in create modal
    if (jobType === 'freestyle') {
        const scmRadios = document.querySelectorAll('input[name="scm_type"]');
        scmRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                const gitFields = document.getElementById('create-git-config-fields');
                if (this.value === 'git') {
                    gitFields.style.display = 'block';
                    loadCredentials(); // Load available credentials
                } else {
                    gitFields.style.display = 'none';
                }
            });
        });
    }
    
    if (jobType === 'matrix') {
        const matrixScmRadios = document.querySelectorAll('input[name="scm_type"]');
        matrixScmRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                const gitFields = document.getElementById('matrix-create-git-config-fields');
                if (this.value === 'git') {
                    gitFields.style.display = 'block';
                    loadCredentials(); // Load available credentials
                } else {
                    gitFields.style.display = 'none';
                }
            });
        });
    }
    
    // Add event listeners for Pipeline definition type switching
    if (jobType === 'pipeline') {
        document.addEventListener('change', function(e) {
            if (e.target.name === 'pipeline_definition_type') {
                const scriptFields = document.getElementById('pipeline-script-fields');
                const scmFields = document.getElementById('pipeline-scm-fields');
                
                if (e.target.value === 'script') {
                    scriptFields.style.display = 'block';
                    scmFields.style.display = 'none';
                } else if (e.target.value === 'scm') {
                    scriptFields.style.display = 'none';
                    scmFields.style.display = 'block';
                }
            }
        });
    }
}

function handleCreateJob(e) {
    e.preventDefault();
    
    if (!selectedJobType) {
        showError('Please select a job type');
        return;
    }
    
    const formData = new FormData(e.target);
    const jobData = {
        name: formData.get('name'),
        type: selectedJobType,
        description: formData.get('description') || '',
    };
    
    // Add type-specific fields with SCM support
    switch(selectedJobType) {
        case 'freestyle':
            jobData.build_steps = formData.get('build_steps') || 'echo "Hello World"';
            jobData.build_step_type = formData.get('build_step_type') || 'shell';
            
            // Handle SCM configuration for freestyle
            jobData.scm_type = formData.get('scm_type') || 'none';
            if (jobData.scm_type === 'git') {
                const repoUrl = formData.get('repository_url');
                if (!repoUrl || repoUrl.trim() === '') {
                    showError('Repository URL is required for Git SCM');
                    return;
                }
                jobData.repository_url = repoUrl;
                jobData.credentials_id = formData.get('credentials_id') || '';
                jobData.branch_specifier = formData.get('branch_specifier') || '*/master';
                jobData.repository_browser = 'auto';
            }
            break;
            
        case 'matrix':
            jobData.axis_name = formData.get('axis_name') || 'environment';
            jobData.axis_values = formData.get('axis_values') || 'dev,test,prod';
            jobData.build_steps = formData.get('build_steps') || 'echo "Matrix build for $environment"';
            
            // Handle SCM configuration for matrix
            jobData.scm_type = formData.get('scm_type') || 'none';
            if (jobData.scm_type === 'git') {
                const repoUrl = formData.get('repository_url');
                if (!repoUrl || repoUrl.trim() === '') {
                    showError('Repository URL is required for Git SCM');
                    return;
                }
                jobData.repository_url = repoUrl;
                jobData.credentials_id = formData.get('credentials_id') || '';
                jobData.branch_specifier = formData.get('branch_specifier') || '*/master';
            }
            break;
            
        case 'pipeline':
            jobData.pipeline_definition_type = formData.get('pipeline_definition_type') || 'script';
            if (jobData.pipeline_definition_type === 'script') {
                jobData.pipeline_script = formData.get('pipeline_script');
            } else {
                jobData.repository_url = formData.get('repository_url');
                jobData.branch = formData.get('branch') || 'main';
                jobData.script_path = formData.get('script_path') || 'Jenkinsfile';
                jobData.credentials_id = formData.get('credentials_id') || '';
            }
            break;
            
        case 'multibranch':
            jobData.repository_url = formData.get('repository_url');
            jobData.repo_id = formData.get('repo_id') || 'repo-1';
            
            if (!jobData.repository_url) {
                showError('Repository URL is required for multibranch projects');
                return;
            }
            break;
            
        case 'organization':
            jobData.organization_name = formData.get('organization_name');
            
            if (!jobData.organization_name) {
                showError('Organization name is required for organization folders');
                return;
            }
            break;
    }
    
    // Create the job
    createJob(jobData);
}

function createJob(jobData) {
    // Show loading state
    const submitBtn = document.querySelector('#create-job-form button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating...';
    submitBtn.disabled = true;
    
    fetch('/api/jobs/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(jobData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`Job "${data.job_name}" created successfully!`);
            closeCreateJobModal();
            
            // Refresh jobs list if we're on the jobs page
            const jobsSection = document.getElementById('jobs-section');
            if (jobsSection && jobsSection.style.display !== 'none') {
                loadJobs();
            }
            
            // Refresh dashboard stats
            loadStatistics();
        } else {
            showError('Failed to create job: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error creating job:', error);
        showError('Failed to create job: ' + error.message);
    })
    .finally(() => {
        // Reset button state
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    });
}

// Trigger Build Function
function triggerBuild(jobName) {
    fetch(`/api/job/${encodeURIComponent(jobName)}/build`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`Build triggered for job: ${jobName}`);
            if (currentJob === jobName) {
                setTimeout(() => {
                    loadJobBuildsForPopup(jobName);
                }, 2000);
            }
            setTimeout(() => {
                loadJobs();
                loadDashboard();
            }, 1000);
        } else {
            showError('Failed to trigger build: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error triggering build:', error);
        showError('Failed to trigger build: ' + error.message);
    });
}

// Delete Job Function
function deleteJob(jobName) {
    if (!confirm(`Are you sure you want to delete job "${jobName}"? This action cannot be undone.`)) {
        return;
    }
    
    fetch(`/api/jobs/${encodeURIComponent(jobName)}/delete`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            loadJobs();
            loadStatistics();
            closeJobPopup();
        } else {
            showError('Failed to delete job: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error deleting job:', error);
        showError('Failed to delete job: ' + error.message);
    });
}

// [Include ALL remaining functions from the original app.js]
// Job Popup Functions, Node Functions, Queue Functions, etc.
// All remain exactly the same as in the original implementation

// Job Popup Functions
function showJobPopup(jobName) {
    currentJob = jobName;
    const popup = document.getElementById('job-popup');
    if (!popup) return;
    
    popup.style.display = 'block';
    loadJobDetailsForPopup(jobName);
    loadJobBuildsForPopup(jobName);
}

function closeJobPopup() {
    const popup = document.getElementById('job-popup');
    if (popup) {
        popup.style.display = 'none';
    }
    currentJob = null;
    currentBuild = null;
}

function loadJobDetailsForPopup(jobName) {
    const container = document.getElementById('popup-job-details');
    if (!container) return;
    
    container.innerHTML = '<div class="loading">Loading job details...</div>';
    
    fetch(`/api/job/${encodeURIComponent(jobName)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayJobDetailsInPopup(data.job_info);
            } else {
                showError('Failed to load job details: ' + data.error);
                container.innerHTML = '<p class="error">Failed to load job details</p>';
            }
        })
        .catch(error => {
            console.error('Error loading job details:', error);
            showError('Failed to load job details');
            container.innerHTML = '<p class="error">Failed to load job details</p>';
        });
}

function displayJobDetailsInPopup(jobInfo) {
    const container = document.getElementById('popup-job-details');
    if (!container) return;
    
    const jobType = jobInfo.job_type || 'unknown';
    const jobTypeIcon = getJobTypeIcon(jobType);
    
    container.innerHTML = `
        <div class="job-detail-card">
            <div class="job-detail-header">
                <h3>
                    <span class="job-icon">${jobTypeIcon}</span>
                    ${jobInfo.name}
                    ${getJobTypeBadge(jobType)}
                </h3>
            </div>
            <div class="job-detail-content">
                <table class="detail-table">
                    <tr><td><strong>Name:</strong></td><td>${jobInfo.name}</td></tr>
                    <tr><td><strong>Type:</strong></td><td>${getJobTypeBadge(jobType)}</td></tr>
                    <tr><td><strong>Description:</strong></td><td>${jobInfo.description || 'No description'}</td></tr>
                    <tr><td><strong>Buildable:</strong></td><td>${jobInfo.buildable ? 'Yes' : 'No'}</td></tr>
                    <tr><td><strong>In Queue:</strong></td><td>${jobInfo.inQueue ? 'Yes' : 'No'}</td></tr>
                    <tr><td><strong>Total Builds:</strong></td><td>${jobInfo.builds ? jobInfo.builds.length : 0}</td></tr>
                    <tr><td><strong>Last Build:</strong></td><td>${jobInfo.lastBuild ? `#${jobInfo.lastBuild.number}` : 'N/A'}</td></tr>
                    <tr><td><strong>Last Successful Build:</strong></td><td>${jobInfo.lastSuccessfulBuild ? `#${jobInfo.lastSuccessfulBuild.number}` : 'N/A'}</td></tr>
                    <tr><td><strong>Last Failed Build:</strong></td><td>${jobInfo.lastFailedBuild ? `#${jobInfo.lastFailedBuild.number}` : 'N/A'}</td></tr>
                </table>
            </div>
            <div class="job-actions">
                ${jobInfo.buildable && !['folder', 'organization'].includes(jobType) ? 
                    `<button onclick="triggerBuild('${jobInfo.name}')" class="btn btn-primary">🚀 Build Now</button>` : 
                    `<span class="btn btn-secondary disabled">Not Buildable</span>`
                }
                <button onclick="showJobConfig('${jobInfo.name}')" class="btn btn-secondary">⚙️ Configure</button>
            </div>
        </div>
    `;
}

function loadJobBuildsForPopup(jobName) {
    const container = document.getElementById('popup-job-builds');
    if (!container) return;
    
    container.innerHTML = '<div class="loading">Loading builds...</div>';
    
    fetch(`/api/job/${encodeURIComponent(jobName)}/builds`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayJobBuildsInPopup(data.builds);
            } else {
                showError('Failed to load builds: ' + data.error);
                container.innerHTML = '<p class="error">Failed to load builds</p>';
            }
        })
        .catch(error => {
            console.error('Error loading builds:', error);
            showError('Failed to load builds');
            container.innerHTML = '<p class="error">Failed to load builds</p>';
        });
}

function displayJobBuildsInPopup(builds) {
    const container = document.getElementById('popup-job-builds');
    if (!container) return;
    
    if (!builds || builds.length === 0) {
        container.innerHTML = '<div class="no-builds"><p>No builds found for this job</p></div>';
        return;
    }

    const buildsHtml = `
        <div class="builds-header">
            <h3>📋 Builds for ${currentJob} (${builds.length} total)</h3>
        </div>
        <div class="builds-list">
            ${builds.map(build => {
                const buildStatus = getBuildStatus(build);
                let date = 'Unknown date';
                
                if (build.timestamp) {
                    try {
                        date = new Date(build.timestamp).toLocaleString();
                    } catch (e) {
                        console.warn('Invalid timestamp:', build.timestamp);
                    }
                }
                
                return `
                    <div class="build-item ${currentBuild === build.number ? 'selected' : ''}" onclick="selectBuildInPopup(${build.number})">
                        <div class="build-info">
                            <div class="build-number">#${build.number}</div>
                            <div class="build-status">
                                <span class="status ${buildStatus.class}">${buildStatus.text}</span>
                            </div>
                            <div class="build-date">${date}</div>
                        </div>
                        <div class="build-actions">
                            <button onclick="event.stopPropagation(); showConsoleOutput(${build.number})" class="btn btn-sm btn-console">📋 Console</button>
                            <button onclick="event.stopPropagation(); loadBuildDetailsInPopup(${build.number})" class="btn btn-sm btn-details">ℹ️ Details</button>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    
    container.innerHTML = buildsHtml;
}

function selectBuildInPopup(buildNumber) {
    currentBuild = buildNumber;
    
    document.querySelectorAll('.build-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    const selectedBuild = document.querySelector(`[onclick*="selectBuildInPopup(${buildNumber})"]`);
    if (selectedBuild) {
        selectedBuild.classList.add('selected');
    }
    
    loadBuildDetailsInPopup(buildNumber);
}

function loadBuildDetailsInPopup(buildNumber) {
    if (!currentJob) return;
    
    const detailsContainer = document.getElementById('popup-build-details');
    if (!detailsContainer) return;
    
    detailsContainer.innerHTML = '<div class="loading">Loading build details...</div>';
    
    fetch(`/api/job/${encodeURIComponent(currentJob)}/build/${buildNumber}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayBuildDetailsInPopup(data.build_info);
            } else {
                showError('Failed to load build details: ' + data.error);
                detailsContainer.innerHTML = '<p class="error">Failed to load build details</p>';
            }
        })
        .catch(error => {
            console.error('Error loading build details:', error);
            showError('Failed to load build details');
            detailsContainer.innerHTML = '<p class="error">Failed to load build details</p>';
        });
}

function displayBuildDetailsInPopup(buildInfo) {
    const container = document.getElementById('popup-build-details');
    if (!container) return;
    
    const buildStatus = getBuildStatus(buildInfo);
    const duration = formatDuration(buildInfo.duration);
    const startTime = buildInfo.timestamp ? new Date(buildInfo.timestamp).toLocaleString() : 'Unknown';
    
    container.innerHTML = `
        <div class="build-detail-card">
            <div class="build-detail-header">
                <h3>🔧 Build #${buildInfo.number} Details</h3>
                <span class="status ${buildStatus.class}">${buildStatus.text}</span>
            </div>
            <div class="build-detail-content">
                <table class="detail-table">
                    <tr><td><strong>Job:</strong></td><td>${currentJob}</td></tr>
                    <tr><td><strong>Build Number:</strong></td><td>#${buildInfo.number}</td></tr>
                    <tr><td><strong>Status:</strong></td><td><span class="status ${buildStatus.class}">${buildStatus.text}</span></td></tr>
                    <tr><td><strong>Duration:</strong></td><td>${duration}</td></tr>
                    <tr><td><strong>Started:</strong></td><td>${startTime}</td></tr>
                    <tr><td><strong>URL:</strong></td><td>${buildInfo.url}</td></tr>
                </table>
            </div>
            <div class="build-actions">
                <button onclick="showConsoleOutput(${buildInfo.number})" class="btn btn-primary">📋 View Console Output</button>
                <button onclick="downloadConsoleOutput(${buildInfo.number})" class="btn btn-secondary">💾 Download Console</button>
            </div>
        </div>
    `;
}

function showConsoleOutput(buildNumber) {
    if (!currentJob) {
        showError('No job selected');
        return;
    }
    
    hideAllSections();
    const consoleSection = document.getElementById('console-section');
    if (consoleSection) {
        consoleSection.style.display = 'block';
    }
    
    const consoleContainer = document.getElementById('console-output');
    if (!consoleContainer) return;
    
    consoleContainer.innerHTML = '<div class="loading">Loading console output...</div>';
    
    fetch(`/api/job/${encodeURIComponent(currentJob)}/build/${buildNumber}/console`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayConsoleOutput(data.console_output, buildNumber);
            } else {
                showError('Failed to load console output: ' + data.error);
                consoleContainer.innerHTML = '<p class="error">Failed to load console output</p>';
            }
        })
        .catch(error => {
            console.error('Error loading console output:', error);
            showError('Failed to load console output');
            consoleContainer.innerHTML = '<p class="error">Failed to load console output</p>';
        });
}

function displayConsoleOutput(consoleOutput, buildNumber) {
    const container = document.getElementById('console-output');
    if (!container) return;
    
    container.innerHTML = `
        <div class="console-header">
            <h3>🖥️ Console Output - ${currentJob} #${buildNumber}</h3>
            <div class="console-actions">
                <button onclick="downloadConsoleOutput(${buildNumber})" class="btn btn-secondary">💾 Download</button>
                <button onclick="showJobs()" class="btn btn-primary">← Back to Jobs</button>
            </div>
        </div>
        <div class="console-content">
            <pre class="console-text">${consoleOutput || 'No console output available'}</pre>
        </div>
    `;
}

function downloadConsoleOutput(buildNumber) {
    if (!currentJob) return;
    
    const consoleText = document.querySelector('.console-text');
    if (!consoleText) return;
    
    const content = consoleText.textContent;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentJob}-build-${buildNumber}-console.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Utility functions
function formatDuration(milliseconds) {
    if (!milliseconds) return '0s';
    
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

// Enhanced notification functions with better error handling
function showError(message) {
    console.error('Error:', message);
    showNotification(message, 'error');
}

function showSuccess(message) {
    console.log('Success:', message);
    showNotification(message, 'success');
}

function showNotification(message, type) {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    });
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add close button for errors
    if (type === 'error') {
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            margin-left: 10px;
            padding: 0 5px;
        `;
        closeBtn.onclick = () => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        };
        notification.appendChild(closeBtn);
    }
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Auto-hide notification
    const hideTimeout = type === 'error' ? 8000 : 4000; // Errors stay longer
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, hideTimeout);
}

function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        const dashboardSection = document.getElementById('dashboard-section');
        if (dashboardSection && dashboardSection.style.display !== 'none') {
            loadStatistics();
            loadRecentJobs();
        }
    }, 30000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

function searchJobs(query) {
    const jobItems = document.querySelectorAll('.job-item');
    jobItems.forEach(item => {
        const jobName = item.querySelector('.job-name').textContent.toLowerCase();
        const jobDescription = item.querySelector('.job-description').textContent.toLowerCase();
        
        if (jobName.includes(query.toLowerCase()) || jobDescription.includes(query.toLowerCase())) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// [Include all remaining functions from the original app.js]
// These include loadNodes, loadQueue, loadPlugins, loadGitRepositories, etc.
// They remain exactly the same as in the original implementation

// Load remaining sections (keeping all existing functions)
function loadNodes() {
    fetch('/api/nodes')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayNodesWithActions(data.nodes);
            } else {
                showError('Failed to load nodes: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading nodes:', error);
            showError('Failed to load nodes');
        });
}

function displayNodesWithActions(nodes) {
    const container = document.getElementById('nodes-list');
    if (!container) return;
    
    if (nodes.length === 0) {
        container.innerHTML = '<p>No nodes found</p>';
        return;
    }

    const nodesHtml = nodes.map(node => {
        const isOffline = node.offline || node.temporarilyOffline;
        const statusClass = isOffline ? 'status-failure' : 'status-success';
        const statusText = isOffline ? 'Offline' : 'Online';
        const toggleText = isOffline ? 'Bring Online' : 'Take Offline';
        const toggleIcon = isOffline ? '🟢' : '🔴';
        const isMaster = node.name === 'master' || node.name === 'built-in' || node.displayName === 'Built-In Node';
        
        return `
            <div class="node-item">
                <div class="node-header">
                    <div class="node-title">
                        <span class="node-icon">🖥️</span>
                        <span class="node-name">${node.displayName || node.name}</span>
                    </div>
                    <div class="node-status">
                        <span class="status ${statusClass}">${statusText}</span>
                    </div>
                </div>
                <div class="node-details">
                    <p><strong>Executors:</strong> ${node.executors || node.numExecutors || 0}</p>
                    <p><strong>Description:</strong> ${node.description || 'No description'}</p>
                    ${node.offlineCause ? `<p><strong>Offline Reason:</strong> ${node.offlineCause}</p>` : ''}
                    ${node.monitorData ? `<p><strong>Architecture:</strong> ${node.monitorData['hudson.node_monitors.ArchitectureMonitor'] || 'Unknown'}</p>` : ''}
                </div>
                <div class="node-actions">
                    <button onclick="toggleNode('${node.name}')" class="btn btn-primary">${toggleIcon} ${toggleText}</button>
                    ${!isMaster ? `<button onclick="deleteNode('${node.name}')" class="btn btn-danger">🗑️ Delete Node</button>` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = nodesHtml;
}

function toggleNode(nodeName) {
    fetch(`/api/nodes/${encodeURIComponent(nodeName)}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            loadNodes();
        } else {
            showError('Failed to toggle node: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error toggling node:', error);
        showError('Failed to toggle node: ' + error.message);
    });
}

function deleteNode(nodeName) {
    if (!confirm(`Are you sure you want to delete node "${nodeName}"? This action cannot be undone.`)) {
        return;
    }
    
    fetch(`/api/nodes/${encodeURIComponent(nodeName)}/delete`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            loadNodes();
            loadStatistics();
        } else {
            showError('Failed to delete node: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error deleting node:', error);
        showError('Failed to delete node: ' + error.message);
    });
}

function loadQueue() {
    fetch('/api/queue')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayQueueWithActions(data.queue);
            } else {
                showError('Failed to load queue: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading queue:', error);
            showError('Failed to load queue');
        });
}

function displayQueueWithActions(queue) {
    const container = document.getElementById('queue-list');
    if (!container) return;
    
    if (queue.length === 0) {
        container.innerHTML = '<p>Queue is empty</p>';
        return;
    }

    const queueHtml = queue.map(item => {
        const date = new Date(item.inQueueSince).toLocaleString();
        const taskName = item.task?.name || 'Unknown Task';
        const statusClass = item.stuck ? 'status-failure' : (item.blocked ? 'status-warning' : 'status-unknown');
        const statusText = item.stuck ? 'Stuck' : (item.blocked ? 'Blocked' : 'Waiting');
        
        return `
            <div class="queue-item">
                <div class="queue-header">
                    <div class="queue-title">
                        <span class="queue-icon">⏳</span>
                        <span class="queue-job-name">${taskName}</span>
                    </div>
                    <div class="queue-status">
                        <span class="status ${statusClass}">${statusText}</span>
                    </div>
                </div>
                <div class="queue-details">
                    <p><strong>Queued since:</strong> ${date}</p>
                    <p><strong>Reason:</strong> ${item.why}</p>
                    <p><strong>Buildable:</strong> ${item.buildable ? 'Yes' : 'No'}</p>
                    ${item.params ? `<p><strong>Parameters:</strong> ${item.params}</p>` : ''}
                </div>
                <div class="queue-actions">
                    <button onclick="cancelQueueItem(${item.id})" class="btn btn-danger">❌ Cancel</button>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = queueHtml;
}

function cancelQueueItem(queueId) {
    if (!confirm(`Are you sure you want to cancel this queued build?`)) {
        return;
    }
    
    fetch(`/api/queue/${queueId}/cancel`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
            loadQueue();
            loadStatistics();
        } else {
            showError('Failed to cancel queue item: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error cancelling queue item:', error);
        showError('Failed to cancel queue item: ' + error.message);
    });
}

function loadPlugins() {
    fetch('/api/plugins')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayPlugins(data.plugins);
            } else {
                showError('Failed to load plugins: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading plugins:', error);
            showError('Failed to load plugins');
        });
}

function displayPlugins(plugins) {
    const container = document.getElementById('plugins-list');
    if (!container) return;
    
    if (plugins.length === 0) {
        container.innerHTML = '<p>No plugins found</p>';
        return;
    }

    const pluginsHtml = plugins.map(plugin => {
        const statusClass = plugin.enabled ? 'status-success' : 'status-disabled';
        const statusText = plugin.enabled ? 'Enabled' : 'Disabled';
        
        return `
            <div class="plugin-item">
                <div class="plugin-header">
                    <div class="plugin-title">
                        <span class="job-icon">🔌</span>
                        <span class="plugin-name">${plugin.shortName}</span>
                    </div>
                    <div class="plugin-status">
                        <span class="status ${statusClass}">${statusText}</span>
                    </div>
                </div>
                <div class="plugin-details">
                    <p><strong>Version:</strong> ${plugin.version}</p>
                    <p><strong>Long Name:</strong> ${plugin.longName || 'N/A'}</p>
                    <p><strong>Status:</strong> ${statusText}</p>
                    <p><strong>Has Update:</strong> ${plugin.hasUpdate ? 'Yes' : 'No'}</p>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = pluginsHtml;
}

function loadGitRepositories() {
    fetch('/api/git/repositories')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayGitRepositories(data.repositories);
            } else {
                showError('Failed to load repositories: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading repositories:', error);
            showError('Failed to load repositories');
        });
}

function displayGitRepositories(repositories) {
    const container = document.getElementById('git-repositories');
    if (!container) return;
    
    if (repositories.length === 0) {
        container.innerHTML = '<p>No Git repositories found</p>';
        return;
    }

    const reposHtml = repositories.map(repo => {
        const statusClass = repo.status === 'clean' ? 'status-success' : 'status-warning';
        
        return `
            <div class="git-repo-item">
                <div class="repo-header">
                    <h4>📁 ${repo.name}</h4>
                    <div class="status ${statusClass}">${repo.status}</div>
                </div>
                <div class="repo-details">
                    <p><strong>Path:</strong> ${repo.path}</p>
                    <p><strong>Branch:</strong> ${repo.branch}</p>
                    <p><strong>Last Commit:</strong> ${repo.lastCommit || 'N/A'}</p>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = reposHtml;
}

function exportConfig() {
    const config = {
        theme: isDarkMode ? 'dark' : 'light',
        currentJob: currentJob,
        timestamp: new Date().toISOString()
    };
    
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = 'jenkins-config.json';
    link.click();
}

// [Keep all existing JavaScript code and add these new functions]

// AI Analyzer Functions
function showAIAnalyzer() {
    hideAllSections();
    const aiSection = document.getElementById('ai-analyzer-section');
    if (aiSection) {
        aiSection.style.display = 'block';
        setActiveTab(6); // Adjust tab index as needed
    }
}

function clearAIAnalysis() {
    document.getElementById('ai-analysis-results').style.display = 'none';
    document.getElementById('ai-analysis-results').innerHTML = '';
    document.getElementById('ai-analysis-form').reset();
    document.getElementById('ai-branch').value = 'main';
}

// Handle AI analysis form submission
document.addEventListener('DOMContentLoaded', function() {
    const aiForm = document.getElementById('ai-analysis-form');
    if (aiForm) {
        aiForm.addEventListener('submit', handleAIAnalysis);
    }
});

function handleAIAnalysis(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const repositoryUrl = formData.get('repository_url').trim();
    const branch = formData.get('branch').trim() || 'main';
    
    if (!repositoryUrl) {
        showError('Repository URL is required');
        return;
    }
    
    if (!repositoryUrl.includes('github.com')) {
        showError('Only GitHub repositories are supported');
        return;
    }
    
    // Show loading state
    showAIAnalysisLoading();
    
    // Disable form
    const analyzeBtn = document.getElementById('analyze-btn');
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🔍 Analyzing...';
    
    // Make API request
    fetch('/api/ai/analyze-repository', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({
            repository_url: repositoryUrl,
            branch: branch
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayAIAnalysisResults(data);
        } else {
            showError('Analysis failed: ' + data.error);
            hideAIAnalysisLoading();
        }
    })
    .catch(error => {
        console.error('Error during analysis:', error);
        showError('Analysis failed: ' + error.message);
        hideAIAnalysisLoading();
    })
    .finally(() => {
        // Reset form state
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🔍 Analyze Repository';
    });
}

function showAIAnalysisLoading() {
    const resultsContainer = document.getElementById('ai-analysis-results');
    resultsContainer.innerHTML = `
        <div class="ai-loading">
            <div class="ai-spinner"></div>
            <h4>🤖 AI is analyzing your repository...</h4>
            <p>This may take 30-60 seconds. Please wait while we:</p>
            <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
                <li>📥 Fetch repository structure</li>
                <li>🔍 Analyze project files</li>
                <li>🧠 Generate optimal pipeline</li>
                <li>📄 Create Jenkinsfile</li>
            </ul>
        </div>
    `;
    resultsContainer.style.display = 'block';
}

function hideAIAnalysisLoading() {
    const resultsContainer = document.getElementById('ai-analysis-results');
    resultsContainer.style.display = 'none';
}

function displayAIAnalysisResults(data) {
    const resultsContainer = document.getElementById('ai-analysis-results');
    const analysis = data.analysis.analysis || {};
    const jenkinsfile = data.analysis.jenkinsfile || '';
    const explanation = data.analysis.explanation || '';
    const recommendations = data.analysis.recommendations || [];
    
    const resultsHtml = `
        <div class="ai-analysis-result">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h4 style="margin: 0; color: #28a745;">✅ Analysis Complete</h4>
                <span class="ai-status-success">🤖 AI Analysis Successful</span>
            </div>
            
            <!-- Analysis Summary -->
            <div class="analysis-summary">
                <div class="analysis-item">
                    <h6>Project Type</h6>
                    <p>${analysis.project_type || 'Unknown'}</p>
                </div>
                <div class="analysis-item">
                    <h6>Build System</h6>
                    <p>${analysis.build_system || 'Unknown'}</p>
                </div>
                <div class="analysis-item">
                    <h6>Test Framework</h6>
                    <p>${analysis.test_framework || 'Unknown'}</p>
                </div>
                <div class="analysis-item">
                    <h6>Complexity</h6>
                    <p>${analysis.complexity || 'Moderate'}</p>
                </div>
            </div>
            
            <!-- Dependencies -->
            ${analysis.dependencies && analysis.dependencies.length > 0 ? `
                <div class="analysis-item" style="margin-bottom: 1rem;">
                    <h6>Dependencies</h6>
                    <p>${analysis.dependencies.join(', ')}</p>
                </div>
            ` : ''}
            
            <!-- Explanation -->
            ${explanation ? `
                <div style="background: white; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #17a2b8; margin-bottom: 1rem;">
                    <h6 style="margin: 0 0 1rem 0; color: #17a2b8;">📋 AI Analysis Explanation</h6>
                    <p style="margin: 0; line-height: 1.6;">${explanation}</p>
                </div>
            ` : ''}
            
            <!-- Generated Jenkinsfile -->
            <div style="margin: 1.5rem 0;">
                <h5 style="color: #2c3e50;">📄 Generated Jenkinsfile</h5>
                <div class="jenkinsfile-preview">
                    <pre>${jenkinsfile}</pre>
                </div>
                <div style="text-align: right; margin-top: 0.5rem;">
                    <button onclick="copyJenkinsfile()" class="btn btn-sm btn-info">📋 Copy Jenkinsfile</button>
                    <button onclick="downloadJenkinsfile()" class="btn btn-sm btn-secondary">💾 Download</button>
                </div>
            </div>
            
            <!-- Recommendations -->
            ${recommendations.length > 0 ? `
                <div class="recommendations-list">
                    <h6>💡 AI Recommendations</h6>
                    <ul>
                        ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <!-- Pipeline Creation -->
            <div class="pipeline-creation-section">
                <h5 style="color: #2c3e50; margin-bottom: 1rem;">🚀 Create Jenkins Pipeline</h5>
                <p style="margin-bottom: 1rem; color: #6c757d;">Create a new Jenkins pipeline job with the generated configuration:</p>
                
                <form id="create-pipeline-form">
                    <div class="ai-form-group">
                        <label for="pipeline-job-name">Job Name *</label>
                        <input type="text" id="pipeline-job-name" name="job_name" 
                               placeholder="my-ai-generated-pipeline" 
                               required>
                    </div>
                    
                    <div class="ai-form-group">
                        <label for="pipeline-credentials">Git Credentials (Optional)</label>
                        <select id="pipeline-credentials" name="credentials_id">
                            <option value="">- none -</option>
                        </select>
                        <small style="color: #6c757d;">Select credentials if your repository is private</small>
                    </div>
                    
                    <div class="ai-actions">
                        <button type="submit" class="btn-ai" id="create-pipeline-btn">
                            🚀 Create Pipeline Job
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    resultsContainer.innerHTML = resultsHtml;
    resultsContainer.style.display = 'block';
    
    // Load credentials for pipeline creation
    loadCredentials();
    
    // Add form submit handler for pipeline creation
    const pipelineForm = document.getElementById('create-pipeline-form');
    if (pipelineForm) {
        pipelineForm.addEventListener('submit', function(e) {
            handlePipelineCreation(e, data);
        });
    }
}

function copyJenkinsfile() {
    const jenkinsfileContent = document.querySelector('.jenkinsfile-preview pre').textContent;
    
    navigator.clipboard.writeText(jenkinsfileContent).then(() => {
        showSuccess('Jenkinsfile copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        showError('Failed to copy Jenkinsfile');
    });
}

function downloadJenkinsfile() {
    const jenkinsfileContent = document.querySelector('.jenkinsfile-preview pre').textContent;
    const blob = new Blob([jenkinsfileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Jenkinsfile';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showSuccess('Jenkinsfile downloaded successfully!');
}

function handlePipelineCreation(e, analysisData) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const jobName = formData.get('job_name').trim();
    const credentialsId = formData.get('credentials_id') || '';
    
    if (!jobName) {
        showError('Job name is required');
        return;
    }
    
    // Validate job name
    if (!jobName.match(/^[a-zA-Z0-9_.-]+$/)) {
        showError('Job name can only contain letters, numbers, underscores, dots, and hyphens');
        return;
    }
    
    // Show loading state
    const createBtn = document.getElementById('create-pipeline-btn');
    const originalText = createBtn.textContent;
    createBtn.disabled = true;
    createBtn.textContent = '🚀 Creating Pipeline...';
    
    // Prepare data for pipeline creation
    const pipelineData = {
        job_name: jobName,
        analysis: analysisData.analysis,
        repository_url: analysisData.repository_url,
        branch: analysisData.branch,
        credentials_id: credentialsId
    };
    
    // Create pipeline job
    fetch('/api/ai/create-pipeline-from-analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(pipelineData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`🎉 Pipeline job "${data.job_name}" created successfully!`);
            
            // Show additional success information
            setTimeout(() => {
                const confirmSwitch = confirm(
                    `Pipeline created successfully!\n\n` +
                    `Job Name: ${data.job_name}\n` +
                    `Repository: ${analysisData.repository_url}\n` +
                    `Branch: ${analysisData.branch}\n\n` +
                    `Would you like to view the jobs list now?`
                );
                
                if (confirmSwitch) {
                    showJobs();
                }
            }, 1000);
            
        } else {
            showError('Failed to create pipeline: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error creating pipeline:', error);
        showError('Failed to create pipeline: ' + error.message);
    })
    .finally(() => {
        // Reset button state
        createBtn.disabled = false;
        createBtn.textContent = originalText;
    });
}

// Update navigation to include AI analyzer
function setActiveTab(index) {
    const tabs = document.querySelectorAll('.nav-tabs button');
    tabs.forEach(tab => tab.classList.remove('active'));
    if (tabs[index]) {
        tabs[index].classList.add('active');
    }
}
// Add these functions to your existing app.js file (continuing from the previous code)

// NEW: AI Analyzer Functions (continued)
function showAIAnalyzer() {
    hideAllSections();
    const aiSection = document.getElementById('ai-analyzer-section');
    if (aiSection) {
        aiSection.style.display = 'block';
        setActiveTab(6); // Adjust tab index based on your navigation
        
        // Update the sections list to include ai-analyzer-section
        const sections = ['dashboard-section', 'jobs-section', 'nodes-section', 'queue-section', 'plugins-section', 'git-section', 'console-section', 'ai-analyzer-section'];
        sections.forEach(section => {
            if (section !== 'ai-analyzer-section') {
                const element = document.getElementById(section);
                if (element) {
                    element.style.display = 'none';
                }
            }
        });
    }
}


function analyzeRepository() {
    const repositoryUrl = document.getElementById('repository-url').value.trim();
    const branch = document.getElementById('repository-branch').value.trim() || 'main';
    const envShellType = document.getElementById('env-shell-type').value || 'sh';  // GET ENVIRONMENT TYPE

    if (!repositoryUrl) {
        showError('Please enter a GitHub repository URL');
        return;
    }

    // Validate GitHub URL
    if (!repositoryUrl.includes('github.com')) {
        showError('Please enter a valid GitHub repository URL');
        return;
    }

    // Show analysis progress
    const analysisContainer = document.getElementById('analysis-results');
    const loadingContainer = document.getElementById('analysis-loading');
    const analyzeButton = document.getElementById('analyze-button');

    if (loadingContainer) loadingContainer.style.display = 'block';
    if (analysisContainer) analysisContainer.style.display = 'none';
    if (analyzeButton) analyzeButton.disabled = true;

    const requestData = {
        repository_url: repositoryUrl,
        branch: branch,
        env_shell_type: envShellType  // SEND ENVIRONMENT TYPE TO BACKEND
    };

    fetch('/api/ai/analyze-repository', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayAnalysisResults(data.analysis, data.repository_url, data.branch, data.env_shell_type);
        } else {
            showError('Analysis failed: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Analysis request failed');
    })
    .finally(() => {
        if (loadingContainer) loadingContainer.style.display = 'none';
        if (analyzeButton) analyzeButton.disabled = false;
    });
}

function displayAnalysisResults(analysis, repositoryUrl, branch, envShellType) {
    const container = document.getElementById('analysis-results');
    if (!container) return;

    // Store analysis results globally for later use
    window.currentAnalysisResults = analysis;

    const analysisData = analysis.analysis || {};
    const jenkinsfile = analysis.jenkinsfile || '';
    const explanation = analysis.explanation || '';
    const recommendations = analysis.recommendations || [];

    // Environment-specific display text
    const envDisplayNames = {
        'sh': 'Linux/Unix (sh)',
        'bat': 'Windows (bat)', 
        'osascript': 'macOS (osascript)'
    };
    const envDisplay = envDisplayNames[envShellType] || envShellType;

    container.innerHTML = `
        <div class="analysis-header">
            <h3>🤖 AI Analysis Results</h3>
            <div class="analysis-meta">
                <p><strong>Repository:</strong> ${repositoryUrl}</p>
                <p><strong>Branch:</strong> ${branch}</p>
                <p><strong>Target Environment:</strong> ${envDisplay}</p>
                <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
            </div>
        </div>

        <div class="analysis-summary">
            <h4>📊 Project Analysis</h4>
            <div class="analysis-grid">
                <div class="analysis-item">
                    <strong>Project Type:</strong>
                    <span class="badge badge-primary">${analysisData.project_type || 'Unknown'}</span>
                </div>
                <div class="analysis-item">
                    <strong>Build System:</strong>
                    <span class="badge badge-secondary">${analysisData.build_system || 'Unknown'}</span>
                </div>
                <div class="analysis-item">
                    <strong>Test Framework:</strong>
                    <span class="badge badge-info">${analysisData.test_framework || 'Unknown'}</span>
                </div>
                <div class="analysis-item">
                    <strong>Complexity:</strong>
                    <span class="badge badge-warning">${analysisData.complexity || 'Moderate'}</span>
                </div>
                <div class="analysis-item">
                    <strong>Shell Environment:</strong>
                    <span class="badge badge-success">${analysisData.shell_environment || envShellType}</span>
                </div>
            </div>
            ${analysisData.dependencies && analysisData.dependencies.length > 0 ? `
            <div class="dependencies">
                <strong>Dependencies:</strong>
                <div class="dependency-tags">
                    ${analysisData.dependencies.map(dep => `<span class="dependency-tag">${dep}</span>`).join('')}
                </div>
            </div>` : ''}
        </div>

        ${explanation ? `
        <div class="analysis-explanation">
            <h4>💡 Analysis Explanation</h4>
            <p>${explanation}</p>
        </div>` : ''}

        <div class="jenkinsfile-section">
            <h4>📝 Generated Jenkinsfile (${envDisplay})</h4>
            <div class="code-container">
                <button class="copy-button" onclick="copyJenkinsfile()">📋 Copy</button>
                <pre><code id="jenkinsfile-code">${jenkinsfile}</code></pre>
            </div>
        </div>

        ${recommendations && recommendations.length > 0 ? `
        <div class="recommendations">
            <h4>🔧 Recommendations</h4>
            <ul class="recommendation-list">
                ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        </div>` : ''}

        <div class="pipeline-actions">
            <h4>🚀 Create Jenkins Pipeline</h4>
            <p>Create a new Jenkins pipeline job with the generated configuration:</p>
            <div class="form-group">
                <label for="pipeline-job-name">Job Name:</label>
                <input type="text" id="pipeline-job-name" class="form-control" 
                       placeholder="e.g., my-app-pipeline" required>
            </div>
            <div class="form-group">
                <label for="pipeline-credentials">Git Credentials (Optional):</label>
                <select id="pipeline-credentials" class="form-control">
                    <option value="">No credentials</option>
                    <option value="github-token">GitHub Token</option>
                    <option value="gitlab-key">GitLab Key</option>
                    <option value="bitbucket-oauth">Bitbucket OAuth</option>
                </select>
            </div>
            <div class="button-group">
                <button class="btn btn-primary" onclick="createPipelineFromAnalysis('${repositoryUrl}', '${branch}', '${envShellType}')">
                    🔧 Create Pipeline Job
                </button>
                <button class="btn btn-secondary" onclick="downloadJenkinsfile()">
                    💾 Download Jenkinsfile
                </button>
            </div>
        </div>
    `;

    container.style.display = 'block';
}


function createPipelineFromAnalysis(repositoryUrl, branch, envShellType) {
    const jobName = document.getElementById('pipeline-job-name').value.trim();
    const credentialsId = document.getElementById('pipeline-credentials').value;

    if (!jobName) {
        showError('Please enter a job name');
        return;
    }

    // Validate job name
    if (!/^[a-zA-Z0-9_.-]+$/.test(jobName)) {
        showError('Job name can only contain letters, numbers, underscores, dots, and hyphens');
        return;
    }

    const analysisResults = window.currentAnalysisResults;
    if (!analysisResults) {
        showError('No analysis results available');
        return;
    }

    const requestData = {
        job_name: jobName,
        analysis: analysisResults,
        repository_url: repositoryUrl,
        branch: branch,
        credentials_id: credentialsId,
        env_shell_type: envShellType  // PASS ENVIRONMENT TYPE
    };

    fetch('/api/ai/create-pipeline-from-analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`Pipeline job "${data.job_name}" created successfully! Generated for ${envShellType} environment.`);
            // Optionally redirect to jobs page
            setTimeout(() => showJobs(), 2000);
        } else {
            showError('Failed to create pipeline: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Failed to create pipeline job');
    });
}

function getCurrentAnalysisResults() {
    // Get current analysis results from the global variable
    return window.currentAnalysisResults || null;
}

// Utility functions
function copyJenkinsfile() {
    const jenkinsfileCode = document.getElementById('jenkinsfile-code');
    if (jenkinsfileCode) {
        const text = jenkinsfileCode.textContent;
        navigator.clipboard.writeText(text).then(() => {
            showSuccess('Jenkinsfile copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy: ', err);
            showError('Failed to copy Jenkinsfile');
        });
    }
}

function downloadJenkinsfile() {
    const jenkinsfileCode = document.getElementById('jenkinsfile-code');
    if (jenkinsfileCode) {
        const text = jenkinsfileCode.textContent;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Jenkinsfile';
        a.click();
        window.URL.revokeObjectURL(url);
        showSuccess('Jenkinsfile downloaded!');
    }
}

// Make sure hideAllSections includes the AI analyzer section
function hideAllSections() {
    const sections = ['dashboard-section', 'jobs-section', 'nodes-section', 'queue-section', 'plugins-section', 'git-section', 'console-section', 'ai-analyzer-section'];
    sections.forEach(section => {
        const element = document.getElementById(section);
        if (element) {
            element.style.display = 'none';
        }
    });
}

