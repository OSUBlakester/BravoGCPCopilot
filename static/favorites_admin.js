// --- Global Flags ---
let isAuthContextReady = false;
let isDomContentLoaded = false;

// DOM Elements
let buttonGrid = null;
let buttonEditorModal = null;
let scrapingWizardModal = null;

// State Variables
let favoritesData = { buttons: [] };
let currentEditingButton = null; // {row, col} of button being edited
let draggedButton = null;
let currentScrapingConfig = null;

// Constants
const GRID_ROWS = 10;
const GRID_COLS = 10;

const DEFAULT_SCRAPING_CONFIG = {
    url: "",
    headline_selector: "",
    url_selector: "",
    url_attribute: "href",
    url_prefix: "",
    keywords: []
};

// --- Initialization Function ---
async function initializePage() {
    if (isAuthContextReady && isDomContentLoaded) {
        console.log("favorites_admin.js: Auth context and DOM ready. Initializing page.");

        // Assign DOM Elements
        assignDOMElements();
        
        if (!validateDOMElements()) {
            console.error("CRITICAL ERROR: Essential DOM elements not found.");
            return;
        }

        // Setup Event Listeners
        setupEventListeners();

        // Load initial data
        await loadFavorites();
        renderGrid();
    }
}

function assignDOMElements() {
    buttonGrid = document.getElementById('buttonGrid');
    buttonEditorModal = document.getElementById('buttonEditorModal');
    scrapingWizardModal = document.getElementById('scrapingWizardModal');
}

function validateDOMElements() {
    const required = [buttonGrid, buttonEditorModal, scrapingWizardModal];
    return required.every(element => element !== null);
}

function setupEventListeners() {
    // Navigation
    document.getElementById('backButton').addEventListener('click', () => {
        window.location.href = 'admin.html';
    });

    document.getElementById('logout-button').addEventListener('click', async () => {
        if (window.authContext && window.authContext.signOut) {
            await window.authContext.signOut();
            window.location.href = 'auth.html';
        }
    });

    // Action buttons
    document.getElementById('saveChangesBtn').addEventListener('click', saveFavorites);
    document.getElementById('addTopicBtn').addEventListener('click', addNewTopic);
    document.getElementById('clearAllBtn').addEventListener('click', clearAllTopics);

    // Button Editor Modal
    document.getElementById('closeEditorModal').addEventListener('click', closeButtonEditor);
    document.getElementById('cancelEditorBtn').addEventListener('click', closeButtonEditor);
    document.getElementById('buttonEditorForm').addEventListener('submit', saveButtonChanges);
    document.getElementById('deleteButtonBtn').addEventListener('click', deleteButton);
    document.getElementById('configureScrapingBtn').addEventListener('click', openScrapingWizard);

    // Scraping Wizard Modal
    document.getElementById('closeWizardModal').addEventListener('click', closeScrapingWizard);
    document.getElementById('step1NextBtn').addEventListener('click', () => showWizardStep(2));
    document.getElementById('step2BackBtn').addEventListener('click', () => showWizardStep(1));
    document.getElementById('step2NextBtn').addEventListener('click', () => showWizardStep(3));
    document.getElementById('step3BackBtn').addEventListener('click', () => showWizardStep(2));
    document.getElementById('testScrapingBtn').addEventListener('click', testScrapingConfiguration);
    document.getElementById('saveScrapingConfigBtn').addEventListener('click', saveScrapingConfiguration);

    // Auto-fill URL prefix when base URL changes
    document.getElementById('baseUrl').addEventListener('input', (e) => {
        const url = e.target.value;
        try {
            const urlObj = new URL(url);
            document.getElementById('urlPrefix').value = `${urlObj.protocol}//${urlObj.host}`;
        } catch (err) {
            // Invalid URL, clear prefix
            document.getElementById('urlPrefix').value = '';
        }
    });
}

// --- Data Management ---
async function loadFavorites() {
    try {
        showStatus('Loading favorites...', false);
        const response = await window.authenticatedFetch('/api/favorites');
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        favoritesData = await response.json();
        showStatus('Favorites loaded successfully', false);
        setTimeout(() => showStatus('', false), 3000);
    } catch (error) {
        console.error('Error loading favorites:', error);
        showStatus(`Error loading favorites: ${error.message}`, true);
        favoritesData = { buttons: [] };
    }
}

async function saveFavorites() {
    try {
        showStatus('Saving favorites...', false);
        const response = await window.authenticatedFetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(favoritesData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        
        showStatus('Favorites saved successfully!', false);
        setTimeout(() => showStatus('', false), 3000);
    } catch (error) {
        console.error('Error saving favorites:', error);
        showStatus(`Error saving favorites: ${error.message}`, true);
    }
}

// --- Grid Management ---
function renderGrid() {
    buttonGrid.innerHTML = '';
    
    for (let row = 0; row < GRID_ROWS; row++) {
        for (let col = 0; col < GRID_COLS; col++) {
            const cell = createGridCell(row, col);
            buttonGrid.appendChild(cell);
        }
    }
}

function createGridCell(row, col) {
    const cell = document.createElement('div');
    cell.className = 'visual-button empty';
    cell.dataset.row = row;
    cell.dataset.col = col;
    
    // Find button data for this position
    const buttonData = findButtonAt(row, col);
    
    if (buttonData) {
        cell.className = 'visual-button filled';
        cell.textContent = buttonData.text;
        
        // Add action buttons
        const actions = document.createElement('div');
        actions.className = 'button-actions';
        actions.innerHTML = `
            <button class="action-btn edit-btn" title="Edit">
                <i class="fas fa-edit"></i>
            </button>
        `;
        cell.appendChild(actions);
        
        // Edit button click
        actions.querySelector('.edit-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            editButton(row, col);
        });
    } else {
        cell.textContent = 'Empty';
    }
    
    // Make draggable if filled
    if (buttonData) {
        cell.draggable = true;
        cell.addEventListener('dragstart', (e) => handleDragStart(e, row, col));
    }
    
    // Drop handlers for all cells
    cell.addEventListener('dragover', handleDragOver);
    cell.addEventListener('drop', (e) => handleDrop(e, row, col));
    cell.addEventListener('dragleave', handleDragLeave);
    
    // Click to add new button if empty
    if (!buttonData) {
        cell.addEventListener('click', () => addButtonAt(row, col));
    }
    
    return cell;
}

function findButtonAt(row, col) {
    return favoritesData.buttons.find(btn => btn.row === row && btn.col === col);
}

// --- Button Management ---
function addNewTopic() {
    // Find first empty position
    for (let row = 0; row < GRID_ROWS; row++) {
        for (let col = 0; col < GRID_COLS; col++) {
            if (!findButtonAt(row, col)) {
                addButtonAt(row, col);
                return;
            }
        }
    }
    showStatus('Grid is full! Please delete a topic first.', true);
}

function addButtonAt(row, col) {
    currentEditingButton = { row, col, isNew: true };
    currentScrapingConfig = { ...DEFAULT_SCRAPING_CONFIG };
    
    // Reset form
    document.getElementById('buttonText').value = '';
    document.getElementById('speechPhrase').value = '';
    updateScrapingConfigStatus();
    
    // Hide delete button for new buttons
    document.getElementById('deleteButtonBtn').style.display = 'none';
    
    showButtonEditor();
}

function editButton(row, col) {
    const buttonData = findButtonAt(row, col);
    if (!buttonData) return;
    
    currentEditingButton = { row, col, isNew: false };
    currentScrapingConfig = { ...buttonData.scraping_config };
    
    // Populate form
    document.getElementById('buttonText').value = buttonData.text;
    document.getElementById('speechPhrase').value = buttonData.speechPhrase || '';
    updateScrapingConfigStatus();
    
    // Show delete button for existing buttons
    document.getElementById('deleteButtonBtn').style.display = 'inline-block';
    
    showButtonEditor();
}

function deleteButton() {
    if (!currentEditingButton || currentEditingButton.isNew) return;
    
    if (confirm('Are you sure you want to delete this topic?')) {
        // Remove from data
        favoritesData.buttons = favoritesData.buttons.filter(btn => 
            !(btn.row === currentEditingButton.row && btn.col === currentEditingButton.col)
        );
        
        closeButtonEditor();
        renderGrid();
        showStatus('Topic deleted', false);
    }
}

function clearAllTopics() {
    if (confirm('Are you sure you want to delete ALL topics? This cannot be undone.')) {
        favoritesData.buttons = [];
        renderGrid();
        showStatus('All topics cleared', false);
    }
}

// --- Drag and Drop ---
function handleDragStart(e, row, col) {
    draggedButton = { row, col };
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    e.target.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.target.classList.remove('drag-over');
}

function handleDrop(e, targetRow, targetCol) {
    e.preventDefault();
    e.target.classList.remove('drag-over');
    
    if (!draggedButton) return;
    
    const sourceButton = findButtonAt(draggedButton.row, draggedButton.col);
    const targetButton = findButtonAt(targetRow, targetCol);
    
    if (sourceButton) {
        // Remove source button
        favoritesData.buttons = favoritesData.buttons.filter(btn => 
            !(btn.row === draggedButton.row && btn.col === draggedButton.col)
        );
        
        // If target position has a button, swap positions
        if (targetButton) {
            targetButton.row = draggedButton.row;
            targetButton.col = draggedButton.col;
        }
        
        // Move source button to target position
        sourceButton.row = targetRow;
        sourceButton.col = targetCol;
        
        // Add source button back
        favoritesData.buttons.push(sourceButton);
        
        renderGrid();
        showStatus('Topic moved', false);
    }
    
    draggedButton = null;
}

// --- Modal Management ---
function showButtonEditor() {
    buttonEditorModal.classList.add('show');
}

function closeButtonEditor() {
    buttonEditorModal.classList.remove('show');
    currentEditingButton = null;
}

function openScrapingWizard() {
    // Populate wizard with current config
    if (currentScrapingConfig) {
        document.getElementById('baseUrl').value = currentScrapingConfig.url || '';
        document.getElementById('headlineSelector').value = currentScrapingConfig.headline_selector || '';
        document.getElementById('linkSelector').value = currentScrapingConfig.url_selector || '';
        document.getElementById('urlAttribute').value = currentScrapingConfig.url_attribute || 'href';
        document.getElementById('urlPrefix').value = currentScrapingConfig.url_prefix || '';
        document.getElementById('keywords').value = currentScrapingConfig.keywords ? currentScrapingConfig.keywords.join(', ') : '';
    }
    
    showWizardStep(1);
    scrapingWizardModal.classList.add('show');
}

function closeScrapingWizard() {
    scrapingWizardModal.classList.remove('show');
    hideTestResults();
}

function showWizardStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Show target step
    document.getElementById(`wizardStep${stepNumber}`).classList.add('active');
}

// --- Form Handling ---
function saveButtonChanges(e) {
    e.preventDefault();
    
    const text = document.getElementById('buttonText').value.trim();
    const speechPhrase = document.getElementById('speechPhrase').value.trim();
    
    if (!text) {
        showStatus('Topic name is required', true);
        return;
    }
    
    if (!currentScrapingConfig || !currentScrapingConfig.url) {
        showStatus('Web scraping configuration is required', true);
        return;
    }
    
    const buttonData = {
        row: currentEditingButton.row,
        col: currentEditingButton.col,
        text: text,
        speechPhrase: speechPhrase || null,
        scraping_config: { ...currentScrapingConfig },
        hidden: false
    };
    
    if (currentEditingButton.isNew) {
        // Add new button
        favoritesData.buttons.push(buttonData);
    } else {
        // Update existing button
        const index = favoritesData.buttons.findIndex(btn => 
            btn.row === currentEditingButton.row && btn.col === currentEditingButton.col
        );
        if (index >= 0) {
            favoritesData.buttons[index] = buttonData;
        }
    }
    
    closeButtonEditor();
    renderGrid();
    showStatus('Topic saved', false);
}

// --- Scraping Configuration ---
async function testScrapingConfiguration() {
    const config = getScrapingConfigFromForm();
    
    if (!config.url || !config.headline_selector || !config.url_selector) {
        showStatus('Please fill in all required fields first', true);
        return;
    }
    
    try {
        showTestResults('Testing configuration...', 'info');
        
        const response = await window.authenticatedFetch('/api/favorites/test-scraping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scraping_config: config })
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = `✅ ${result.message}`;
            if (result.sample_articles && result.sample_articles.length > 0) {
                message += '\\n\\nSample articles found:';
                result.sample_articles.slice(0, 3).forEach((article, i) => {
                    message += `\\n${i + 1}. ${article.title}`;
                });
            }
            showTestResults(message, 'success');
        } else {
            showTestResults(`❌ ${result.message}\\n\\nError: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error testing scraping config:', error);
        showTestResults(`❌ Test failed: ${error.message}`, 'error');
    }
}

function saveScrapingConfiguration() {
    const config = getScrapingConfigFromForm();
    
    if (!config.url || !config.headline_selector || !config.url_selector) {
        showStatus('Please fill in all required fields', true);
        return;
    }
    
    currentScrapingConfig = config;
    updateScrapingConfigStatus();
    closeScrapingWizard();
    showStatus('Scraping configuration saved', false);
}

function getScrapingConfigFromForm() {
    const keywords = document.getElementById('keywords').value.trim();
    return {
        url: document.getElementById('baseUrl').value.trim(),
        headline_selector: document.getElementById('headlineSelector').value.trim(),
        url_selector: document.getElementById('linkSelector').value.trim(),
        url_attribute: document.getElementById('urlAttribute').value.trim() || 'href',
        url_prefix: document.getElementById('urlPrefix').value.trim(),
        keywords: keywords ? keywords.split(',').map(k => k.trim()).filter(k => k) : []
    };
}

function updateScrapingConfigStatus() {
    const statusEl = document.getElementById('scrapingConfigStatus');
    if (currentScrapingConfig && currentScrapingConfig.url) {
        statusEl.textContent = `✅ Configured for: ${currentScrapingConfig.url}`;
        statusEl.className = 'mt-2 text-sm text-green-600';
    } else {
        statusEl.textContent = '⚠️ Web scraping not configured';
        statusEl.className = 'mt-2 text-sm text-orange-600';
    }
}

// --- Utility Functions ---
function showStatus(message, isError = false) {
    const statusArea = document.getElementById('status-message-area');
    if (!message) {
        statusArea.innerHTML = '';
        return;
    }
    
    const alertClass = isError ? 'bg-red-100 text-red-700 border-red-300' : 'bg-blue-100 text-blue-700 border-blue-300';
    statusArea.innerHTML = `
        <div class="border ${alertClass} px-4 py-3 rounded-lg">
            ${message}
        </div>
    `;
}

function showTestResults(message, type) {
    const resultsEl = document.getElementById('testResults');
    resultsEl.style.display = 'block';
    resultsEl.className = `test-results ${type}`;
    resultsEl.innerHTML = `<pre style="white-space: pre-wrap; margin: 0;">${message}</pre>`;
}

function hideTestResults() {
    document.getElementById('testResults').style.display = 'none';
}

// --- Event Listeners for DOM and Auth ---
document.addEventListener('DOMContentLoaded', () => {
    isDomContentLoaded = true;
    initializePage();
});

window.addEventListener('authContextReady', () => {
    isAuthContextReady = true;
    initializePage();
});
