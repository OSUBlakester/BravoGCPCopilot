// --- Global Flags ---
let isAuthContextReady = false;
let isDomContentLoaded = false;

// DOM Elements
let pageForm = null;
let deletePageButton = null;
let selectPage = null;
let buttonGrid = null;
// let newPageNameInput = null; // Removed: Page Name input no longer used
let newPageDisplayNameInput = null;
let createNewPageBtn = null;
let updatePageBtn = null;
let revertPageBtn = null;
let saveButtonsBtn = null; // New button for saving changes
let helpWizardBtn = null;
let runTranslatePagesBtn = null;

// Modal Elements
let buttonEditorModal = null;
let helpWizardModal = null;
let imagePickerModal = null;


// --- State Variables ---
let allUserPages = [];
let currentPageData = null;
let initialPageDataString = '';
let currentEditingButton = null; // {row, col} of button being edited
let draggedButton = null;

const TRANSLATE_LOCALE_OPTIONS = [
    { value: 'en-US', label: 'English (US)' },
    { value: 'es-US', label: 'Spanish (US)' },
    { value: 'fr-FR', label: 'French (France)' },
    { value: 'de-DE', label: 'German (Germany)' },
    { value: 'it-IT', label: 'Italian (Italy)' },
    { value: 'pt-BR', label: 'Portuguese (Brazil)' },
    { value: 'ar-XA', label: 'Arabic' }
];

const UNSAVED_SCOPE_PAGE_SETTINGS = 'page-settings';
const UNSAVED_SCOPE_BUTTON_GRID = 'button-grid';

function markAdminDirty(scope) {
    window.adminUnsavedIndicator?.markDirty?.(scope);
}

function markAdminSaving(scope) {
    window.adminUnsavedIndicator?.markSaving?.(scope);
}

function markAdminSaved() {
    window.adminUnsavedIndicator?.markSaved?.();
}

// --- Special Predefined Pages ---
const SPECIAL_PAGES = [
    { name: 'freestyle', displayName: 'Freestyle Page' },
    { name: 'spelling', displayName: 'Spelling Page' },
    { name: 'numbers', displayName: 'Numbers Page' },
    { name: 'threads', displayName: 'Threads Page' },
    { name: 'favorites', displayName: 'Favorites Page' },
    { name: 'mood', displayName: 'Mood Selection Page' },
    { name: 'email', displayName: 'Email Page' },
    { name: 'compose', displayName: 'Compose Page' },
    { name: 'text', displayName: 'Text Message Page' },
    { name: 'music', displayName: 'Music Page' },
    { name: 'games', displayName: 'Games Page' },
    { name: 'jokes', displayName: 'Jokes Page' },
    // Add more special pages here as needed
];

// --- Constants ---
const GRID_ROWS = 10;
const GRID_COLS = 15; // Increased to accommodate more buttons

const DEFAULT_PAGE_BUTTON_STRUCTURE = {
    text: "",
    LLMQuery: "",
    targetPage: "",
    queryType: "options", // Always options now
    speechPhrase: null,
    hidden: false
};

// --- Initialization Function ---
async function initializePage() {
    if (isAuthContextReady && isDomContentLoaded) {
        console.log("admin_pages.js: Auth context and DOM ready. Initializing page.");

        // Assign DOM Elements
        assignDOMElements();
        
        if (!validateDOMElements()) {
            console.error("CRITICAL ERROR: Essential DOM elements not found.");
            return;
        }

        // Setup Event Listeners
        setupEventListeners();

        // Load initial data
        await loadPages();
        
        // Update page title with profile name
        if (window.updatePageTitleWithProfile) {
            await window.updatePageTitleWithProfile('Page & Button Administration');
        }
    }
}

function assignDOMElements() {
    pageForm = document.getElementById('pageForm');
    deletePageButton = document.getElementById('deletePage');
    selectPage = document.getElementById('selectPage');
    buttonGrid = document.getElementById('buttonGrid');
    // newPageNameInput = document.getElementById('newPageName'); // Removed
    newPageDisplayNameInput = document.getElementById('newPageDisplayName');
    createNewPageBtn = document.getElementById('createNewPageBtn');
    updatePageBtn = document.getElementById('updatePageBtn');
    revertPageBtn = document.getElementById('revertPageBtn');
    saveButtonsBtn = document.getElementById('saveButtonsBtn');
    helpWizardBtn = document.getElementById('helpWizardBtn');
    runTranslatePagesBtn = document.getElementById('runTranslatePagesBtn');

    // Modal elements
    buttonEditorModal = document.getElementById('buttonEditorModal');
    helpWizardModal = document.getElementById('helpWizardModal');
    imagePickerModal = document.getElementById('imagePickerModal');

    if (pageForm) {
        pageForm.setAttribute('data-unsaved-scope', UNSAVED_SCOPE_PAGE_SETTINGS);
    }
    if (buttonGrid) {
        buttonGrid.setAttribute('data-unsaved-scope', UNSAVED_SCOPE_BUTTON_GRID);
    }
    if (buttonEditorModal) {
        buttonEditorModal.setAttribute('data-unsaved-scope', UNSAVED_SCOPE_BUTTON_GRID);
    }
    if (updatePageBtn) {
        updatePageBtn.setAttribute('data-unsaved-scope', UNSAVED_SCOPE_PAGE_SETTINGS);
    }
    if (saveButtonsBtn) {
        saveButtonsBtn.setAttribute('data-unsaved-scope', UNSAVED_SCOPE_BUTTON_GRID);
    }

}

function validateDOMElements() {
    const required = [
        pageForm, selectPage, buttonGrid, 
        newPageDisplayNameInput, createNewPageBtn, updatePageBtn, deletePageButton, 
        revertPageBtn, saveButtonsBtn, helpWizardBtn,
        buttonEditorModal, helpWizardModal, imagePickerModal
    ];
    return required.every(element => element !== null);
}

function setupEventListeners() {
    // Page management
    selectPage.addEventListener('change', handlePageSelected);
    createNewPageBtn.addEventListener('click', openCreatePageWizard);
    _cpwWireEvents();
    updatePageBtn.addEventListener('click', () => updatePage(UNSAVED_SCOPE_PAGE_SETTINGS));
    deletePageButton.addEventListener('click', deletePage);
    revertPageBtn.addEventListener('click', revertPage);
    
    // Button grid controls
    saveButtonsBtn.addEventListener('click', () => updatePage(UNSAVED_SCOPE_BUTTON_GRID));
    helpWizardBtn.addEventListener('click', openHelpWizard);
    const bravoButtonWizardBtn = document.getElementById('bravoButtonWizardBtn');
    if (bravoButtonWizardBtn) bravoButtonWizardBtn.addEventListener('click', openBravoButtonWizard);
    document.getElementById('closeBravoButtonWizard')?.addEventListener('click', closeBravoButtonWizard);
    document.getElementById('bbwCancelBtn')?.addEventListener('click', closeBravoButtonWizard);
    document.getElementById('bbwGenerateBtn')?.addEventListener('click', _bbwGenerate);
    document.getElementById('bbwAddOptionBtn')?.addEventListener('click', () => {
        _bbwOptions.push({ label: '' });
        _bbwRenderOptions();
        const inputs = document.getElementById('bbwOptionsList').querySelectorAll('input');
        if (inputs.length) inputs[inputs.length - 1].focus();
    });
    document.getElementById('bbwStep2BackBtn')?.addEventListener('click', () => _bbwGoToStep(1));
    document.getElementById('bbwStep2NextBtn')?.addEventListener('click', () => {
        const valid = _bbwOptions.filter(o => o.label.trim());
        if (!valid.length) { alert('Add at least one option.'); return; }
        _bbwGoToStep(3);
    });
    document.getElementById('bbwStep3BackBtn')?.addEventListener('click', () => _bbwGoToStep(2));
    document.getElementById('bbwSaveBtn')?.addEventListener('click', _bbwSaveButtons);
    document.querySelectorAll('input[name="bbwMode"]').forEach(r =>
        r.addEventListener('change', _bbwUpdateSummary)
    );
    document.getElementById('bbwTargetPage')?.addEventListener('change', _bbwUpdateSummary);
    if (runTranslatePagesBtn) {
        runTranslatePagesBtn.addEventListener('click', runPageTranslation);
    }

    const selectAllPagesBtn = document.getElementById('selectAllPagesBtn');
    if (selectAllPagesBtn) {
        selectAllPagesBtn.addEventListener('click', () => {
            const list = document.getElementById('translateScopeList');
            if (!list) return;
            const allChecked = list.querySelectorAll('input[type="checkbox"]');
            const anyUnchecked = Array.from(allChecked).some(cb => !cb.checked);
            allChecked.forEach(cb => { cb.checked = anyUnchecked; });
            selectAllPagesBtn.textContent = anyUnchecked ? 'Deselect All' : 'Select All';
        });
    }

    const selectAccentSourceInline = document.getElementById('selectAccentSourceInline');
    const backToMigrationSourcesBtn = document.getElementById('backToMigrationSourcesBtn');
    const migrationSourceSelection = document.getElementById('migrationSourceSelection');
    const accentMigrationInterfaceInline = document.getElementById('accentMigrationInterfaceInline');
    if (selectAccentSourceInline) {
        selectAccentSourceInline.addEventListener('click', () => {
            migrationSourceSelection.classList.add('hidden');
            accentMigrationInterfaceInline.classList.remove('hidden');
        });
    }
    if (backToMigrationSourcesBtn) {
        backToMigrationSourcesBtn.addEventListener('click', () => {
            accentMigrationInterfaceInline.classList.add('hidden');
            migrationSourceSelection.classList.remove('hidden');
        });
    }
    
    // Button Editor Modal
    document.getElementById('closeButtonEditor').addEventListener('click', closeButtonEditor);
    document.getElementById('cancelButtonEdit').addEventListener('click', closeButtonEditor);
    document.getElementById('saveButtonEdit').addEventListener('click', saveButtonEdit);
    document.getElementById('clearButtonBtn').addEventListener('click', clearCurrentButton);
    
    // Audio File Upload
    const customAudioFileInput = document.getElementById('customAudioFile');
    const audioUploadStatus = document.getElementById('audioUploadStatus');
    
    if (customAudioFileInput) {
        customAudioFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                audioUploadStatus.className = 'text-xs mt-1 text-blue-600';
                audioUploadStatus.textContent = 'Uploading audio file...';
                audioUploadStatus.classList.remove('hidden');
                
                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    const response = await window.authenticatedFetch('/api/admin/upload-button-audio', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        document.getElementById('customAudioFileUrl').value = result.audio_url;
                        audioUploadStatus.className = 'text-xs mt-1 text-green-600';
                        audioUploadStatus.textContent = `Audio uploaded: ${file.name}`;
                        console.log('Audio uploaded successfully:', result.audio_url);
                    } else {
                        throw new Error('Upload failed');
                    }
                } catch (error) {
                    console.error('Error uploading audio:', error);
                    audioUploadStatus.className = 'text-xs mt-1 text-red-600';
                    audioUploadStatus.textContent = 'Upload failed. Please try again.';
                    document.getElementById('customAudioFileUrl').value = '';
                }
            }
        });
    }

    // Image Assignment
    const browseImagesBtn = document.getElementById('browseImagesBtn');
    const clearImageBtn = document.getElementById('clearImageBtn');
    
    if (browseImagesBtn) {
        browseImagesBtn.addEventListener('click', openImagePicker);
    } else {
        console.error('browseImagesBtn not found in DOM');
    }
    
    if (clearImageBtn) {
        clearImageBtn.addEventListener('click', clearAssignedImage);
    } else {
        console.error('clearImageBtn not found in DOM');
    }
    
    // Image Picker Modal
    const imagePickerElements = [
        'closeImagePicker', 'cancelImageSelection', 'selectImageBtn', 
        'imageSearchBtn', 'clearImageSearch', 'imagePrevPage', 'imageNextPage', 'imageSearchInput'
    ];
    
    imagePickerElements.forEach(id => {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`Image picker element '${id}' not found in DOM`);
        }
    });
    
    const closeImagePickerBtn = document.getElementById('closeImagePicker');
    const cancelImageSelectionBtn = document.getElementById('cancelImageSelection');
    const selectImageBtn = document.getElementById('selectImageBtn');
    const imageSearchBtn = document.getElementById('imageSearchBtn');
    const clearImageSearchBtn = document.getElementById('clearImageSearch');
    const imagePrevPageBtn = document.getElementById('imagePrevPage');
    const imageNextPageBtn = document.getElementById('imageNextPage');
    const imageSearchInput = document.getElementById('imageSearchInput');
    
    if (closeImagePickerBtn) closeImagePickerBtn.addEventListener('click', closeImagePicker);
    if (cancelImageSelectionBtn) cancelImageSelectionBtn.addEventListener('click', closeImagePicker);
    if (selectImageBtn) selectImageBtn.addEventListener('click', selectAssignedImage);
    if (imageSearchBtn) imageSearchBtn.addEventListener('click', searchImages);
    if (clearImageSearchBtn) clearImageSearchBtn.addEventListener('click', clearImageSearch);
    if (imagePrevPageBtn) imagePrevPageBtn.addEventListener('click', () => navigateImagePage(-1));
    if (imageNextPageBtn) imageNextPageBtn.addEventListener('click', () => navigateImagePage(1));
    
    // Image search on Enter key
    if (imageSearchInput) {
        imageSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchImages();
        });
    }
    
    // Help Wizard Modal
    document.getElementById('closeHelpWizard').addEventListener('click', closeHelpWizard);
    document.getElementById('wizardCancelBtn').addEventListener('click', closeHelpWizard);
    document.getElementById('wizardNextBtn').addEventListener('click', wizardNext);
    document.getElementById('wizardPrevBtn').addEventListener('click', wizardPrev);
    document.getElementById('wizardAcceptBtn').addEventListener('click', wizardAccept);
    document.getElementById('wizardRejectBtn').addEventListener('click', wizardReject);
    
    // Real-time preview updates in button editor
    ['buttonText', 'speechPhrase', 'targetPage', 'temporaryNavigation', 'llmQuery', 'buttonHidden', 'assignedImageUrl'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('input', updateButtonPreview);
            // Also listen for 'change' event for checkboxes
            if (element.type === 'checkbox') {
                element.addEventListener('change', updateButtonPreview);
            }
        }
    });

    setupAdminToolbarButtons();
    

function setupAdminToolbarButtons() {
    const switchUserButton = document.getElementById('switch-user-button');
    const logoutButton = document.getElementById('logout-button');

    function handleSwitchUser() {
        console.log('Switching user profile. Clearing session and redirecting to auth page for profile selection.');
        localStorage.setItem('bravoSkipDefaultUser', 'true');
        sessionStorage.clear();
        setTimeout(() => {
            window.location.href = 'auth.html';
        }, 100);
    }

    function handleLogout() {
        console.log('Logging out. Clearing session and redirecting to auth page for login.');
        localStorage.setItem('bravoIntentionalLogout', 'true');
        localStorage.setItem('bravoSkipDefaultUser', 'true');
        sessionStorage.clear();
        setTimeout(() => {
            window.location.href = 'auth.html';
        }, 100);
    }

    if (switchUserButton) {
        switchUserButton.addEventListener('click', handleSwitchUser);
        console.log('admin_pages.js: Switch User button event listener added');
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
        console.log('admin_pages.js: Logout button event listener added');
    }
}
    // ...existing code...
}

// --- Visual Button Grid Functions ---
function getMaxGridDimensions() {
    if (!currentPageData || !currentPageData.buttons) {
        return { maxRow: GRID_ROWS - 1, maxCol: GRID_COLS - 1 };
    }
    
    let maxRow = GRID_ROWS - 1;
    let maxCol = GRID_COLS - 1;
    
    currentPageData.buttons.forEach(button => {
        if (button.row !== undefined && button.row > maxRow) {
            maxRow = button.row;
        }
        if (button.col !== undefined && button.col > maxCol) {
            maxCol = button.col;
        }
    });
    
    return { maxRow, maxCol };
}

function checkForOutOfBoundsButtons() {
    if (!currentPageData || !currentPageData.buttons) return;
    
    const outOfBounds = currentPageData.buttons.filter(button => 
        button.row >= GRID_ROWS || button.col >= GRID_COLS
    );
    
    if (outOfBounds.length > 0) {
        const message = `Warning: Found ${outOfBounds.length} button(s) positioned outside the default grid area:\n` +
            outOfBounds.map(btn => `"${btn.text}" at row ${btn.row + 1}, column ${btn.col + 1}`).join('\n') +
            '\n\nThe grid has been automatically expanded to show all buttons.';
        
        console.warn('Out of bounds buttons detected:', outOfBounds);
        // Show a less intrusive warning - you could replace this with a toast notification
        if (outOfBounds.length <= 3) { // Only show alert for small numbers
            setTimeout(() => {
                if (confirm(message + '\n\nWould you like to automatically reposition these buttons to fit within the standard grid?')) {
                    repositionOutOfBoundsButtons();
                }
            }, 500);
        }
    }
}

function repositionOutOfBoundsButtons() {
    if (!currentPageData || !currentPageData.buttons) return;
    
    // Find available positions within the standard grid
    const occupiedPositions = new Set();
    currentPageData.buttons.forEach(btn => {
        if (btn.row < GRID_ROWS && btn.col < GRID_COLS) {
            occupiedPositions.add(`${btn.row}-${btn.col}`);
        }
    });
    
    // Find buttons that need repositioning
    const outOfBounds = currentPageData.buttons.filter(button => 
        button.row >= GRID_ROWS || button.col >= GRID_COLS
    );
    
    // Reposition each out-of-bounds button
    let repositioned = 0;
    for (const button of outOfBounds) {
        // Find first available position
        let found = false;
        for (let row = 0; row < GRID_ROWS && !found; row++) {
            for (let col = 0; col < GRID_COLS && !found; col++) {
                const posKey = `${row}-${col}`;
                if (!occupiedPositions.has(posKey)) {
                    console.log(`Repositioning "${button.text}" from ${button.row},${button.col} to ${row},${col}`);
                    button.row = row;
                    button.col = col;
                    occupiedPositions.add(posKey);
                    repositioned++;
                    found = true;
                }
            }
        }
    }
    
    if (repositioned > 0) {
        renderButtonGrid();
        alert(`Successfully repositioned ${repositioned} button(s). Please save the page to persist these changes.`);
    }
}

function renderButtonGrid() {
    if (!currentPageData || !buttonGrid) return;
    
    buttonGrid.innerHTML = '';
    
    // Get dynamic grid dimensions
    const { maxRow, maxCol } = getMaxGridDimensions();
    const actualRows = Math.max(GRID_ROWS, maxRow + 1);
    const actualCols = Math.max(GRID_COLS, maxCol + 1);
    
    // Update CSS grid template
    buttonGrid.style.gridTemplateColumns = `repeat(${actualCols}, 1fr)`;
    
    for (let row = 0; row < actualRows; row++) {
        for (let col = 0; col < actualCols; col++) {
            const button = createVisualButton(row, col);
            buttonGrid.appendChild(button);
        }
    }
}

function createVisualButton(row, col) {
    const buttonDiv = document.createElement('div');
    buttonDiv.className = 'visual-button';
    buttonDiv.dataset.row = row;
    buttonDiv.dataset.col = col;
    
    // Find button data for this position
    const buttonData = findButtonAtPosition(row, col);
    
    if (buttonData && buttonData.text) {
        buttonDiv.classList.add('has-content');
        
        // Show assigned image if available
        if (buttonData.assigned_image_url) {
            buttonDiv.style.backgroundImage = `url('${buttonData.assigned_image_url}')`;
            buttonDiv.style.backgroundSize = 'cover';
            buttonDiv.style.backgroundPosition = 'center';
            buttonDiv.style.color = 'white';
            buttonDiv.style.textShadow = '1px 1px 2px rgba(0,0,0,0.8)';
            buttonDiv.innerHTML = `<div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); padding: 4px; font-size: 12px;">${buttonData.text}</div>`;
        } else {
            buttonDiv.textContent = buttonData.text;
        }
        
        // Add indicators based on button type
        addButtonIndicators(buttonDiv, buttonData);
        
        // Add visual styling based on content
        if (buttonData.LLMQuery) {
            buttonDiv.classList.add('has-ai');
        }
        if (buttonData.targetPage) {
            buttonDiv.classList.add('has-navigation');
        }
    } else {
        buttonDiv.textContent = 'Undefined';
        buttonDiv.classList.add('undefined');
    }
    
    // Add event listeners
    buttonDiv.addEventListener('click', () => openButtonEditor(row, col));
    
    // Drag and drop
    buttonDiv.draggable = true;
    buttonDiv.addEventListener('dragstart', handleDragStart);
    buttonDiv.addEventListener('dragover', handleDragOver);
    buttonDiv.addEventListener('drop', handleDrop);
    buttonDiv.addEventListener('dragend', handleDragEnd);
    
    return buttonDiv;
}

function addButtonIndicators(buttonDiv, buttonData) {
    if (buttonData.LLMQuery) {
        const indicator = document.createElement('div');
        indicator.className = 'button-indicator indicator-ai';
        indicator.textContent = 'AI';
        indicator.title = 'Has AI Query';
        buttonDiv.appendChild(indicator);
    }
    
    if (buttonData.targetPage) {
        const indicator = document.createElement('div');
        indicator.className = 'button-indicator indicator-nav';
        indicator.textContent = '→';
        indicator.title = 'Navigates to page';
        buttonDiv.appendChild(indicator);
    }
    
    if (buttonData.speechPhrase) {
        const indicator = document.createElement('div');
        indicator.className = 'button-indicator indicator-speech';
        indicator.textContent = '♪';
        indicator.title = 'Has speech phrase';
        buttonDiv.appendChild(indicator);
    }
}

function findButtonAtPosition(row, col) {
    if (!currentPageData || !currentPageData.buttons) return null;
    return currentPageData.buttons.find(btn => btn.row === row && btn.col === col);
}

// --- Drag and Drop Functions ---
function handleDragStart(e) {
    draggedButton = {
        row: parseInt(e.target.dataset.row),
        col: parseInt(e.target.dataset.col)
    };
    e.target.classList.add('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
    e.target.classList.add('drop-target');
}

function handleDrop(e) {
    e.preventDefault();
    e.target.classList.remove('drop-target');
    
    const targetRow = parseInt(e.target.dataset.row);
    const targetCol = parseInt(e.target.dataset.col);
    
    if (draggedButton && (draggedButton.row !== targetRow || draggedButton.col !== targetCol)) {
        swapButtons(draggedButton.row, draggedButton.col, targetRow, targetCol);
        renderButtonGrid(); // Re-render to show changes
    }
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.drop-target').forEach(el => {
        el.classList.remove('drop-target');
    });
    draggedButton = null;
}

function swapButtons(fromRow, fromCol, toRow, toCol) {
    if (!currentPageData || !currentPageData.buttons) return;
    
    const fromButton = currentPageData.buttons.find(btn => btn.row === fromRow && btn.col === fromCol);
    const toButton = currentPageData.buttons.find(btn => btn.row === toRow && btn.col === toCol);
    
    // Remove both buttons from array
    currentPageData.buttons = currentPageData.buttons.filter(btn => 
        !(btn.row === fromRow && btn.col === fromCol) && 
        !(btn.row === toRow && btn.col === toCol)
    );
    
    // Add them back with swapped positions
    if (fromButton) {
        fromButton.row = toRow;
        fromButton.col = toCol;
        currentPageData.buttons.push(fromButton);
    }
    
    if (toButton) {
        toButton.row = fromRow;
        toButton.col = fromCol;
        currentPageData.buttons.push(toButton);
    }

    markAdminDirty(UNSAVED_SCOPE_BUTTON_GRID);
}

// --- Button Editor Functions ---
function openButtonEditor(row, col) {
    currentEditingButton = { row, col };
    const buttonData = findButtonAtPosition(row, col) || { ...DEFAULT_PAGE_BUTTON_STRUCTURE };
    
    // Populate form
    document.getElementById('buttonText').value = buttonData.text || '';
    document.getElementById('speechPhrase').value = buttonData.speechPhrase || '';
    document.getElementById('llmQuery').value = buttonData.LLMQuery || '';
    document.getElementById('buttonHidden').checked = buttonData.hidden || false;
    document.getElementById('assignedImageUrl').value = buttonData.assigned_image_url || '';
    document.getElementById('customAudioFileUrl').value = buttonData.customAudioFile || '';
    
    // Update audio upload status if audio file exists
    const audioUploadStatus = document.getElementById('audioUploadStatus');
    if (buttonData.customAudioFile) {
        audioUploadStatus.className = 'text-xs mt-1 text-green-600';
        audioUploadStatus.textContent = 'Audio file assigned';
        audioUploadStatus.classList.remove('hidden');
    } else {
        audioUploadStatus.classList.add('hidden');
    }
    
    // Update image preview
    updateAssignedImagePreview(buttonData.assigned_image_url);
    
    // Populate target page dropdown
    populateTargetPageDropdown();
    document.getElementById('targetPage').value = buttonData.targetPage || '';
    document.getElementById('temporaryNavigation').checked = (buttonData.navigationType === 'TEMPORARY');
    
    // Update position info
    document.getElementById('positionInfo').textContent = `Row ${row + 1}, Column ${col + 1}`;
    
    // Update preview
    updateButtonPreview();
    
    // Show modal
    buttonEditorModal.classList.remove('hidden');
}

function closeButtonEditor() {
    buttonEditorModal.classList.add('hidden');
    currentEditingButton = null;
}

function saveButtonEdit() {
    if (!currentEditingButton) return;
    
    const assignedImageUrl = document.getElementById('assignedImageUrl').value.trim();
    const targetPage = document.getElementById('targetPage').value.trim();
    const isTemporary = document.getElementById('temporaryNavigation').checked;
    
    const buttonData = {
        row: currentEditingButton.row,
        col: currentEditingButton.col,
        text: document.getElementById('buttonText').value.trim(),
        speechPhrase: document.getElementById('speechPhrase').value.trim() || null,
        customAudioFile: document.getElementById('customAudioFileUrl').value.trim() || null,
        targetPage: targetPage,
        navigationType: (targetPage && isTemporary) ? 'TEMPORARY' : (targetPage ? 'PERMANENT' : ''),
        LLMQuery: document.getElementById('llmQuery').value.trim(),
        queryType: "options", // Always options
        hidden: document.getElementById('buttonHidden').checked,
        assigned_image_url: assignedImageUrl || null
    };
    
    console.log('Saving button data:', buttonData);
    console.log('Assigned image URL:', assignedImageUrl);
    
    // Remove existing button at this position
    if (!currentPageData.buttons) currentPageData.buttons = [];
    currentPageData.buttons = currentPageData.buttons.filter(btn => 
        !(btn.row === currentEditingButton.row && btn.col === currentEditingButton.col)
    );
    
    // Add new button if it has content
    if (buttonData.text || buttonData.LLMQuery || buttonData.targetPage) {
        currentPageData.buttons.push(buttonData);
    }

    markAdminDirty(UNSAVED_SCOPE_BUTTON_GRID);
    
    // Re-render grid and close modal
    renderButtonGrid();
    closeButtonEditor();
}

function clearCurrentButton() {
    if (!currentEditingButton) return;
    
    // Remove button from data
    if (currentPageData && currentPageData.buttons) {
        currentPageData.buttons = currentPageData.buttons.filter(btn => 
            !(btn.row === currentEditingButton.row && btn.col === currentEditingButton.col)
        );
    }

    markAdminDirty(UNSAVED_SCOPE_BUTTON_GRID);
    
    // Re-render and close
    renderButtonGrid();
    closeButtonEditor();
}

function updateButtonPreview() {
    const preview = document.getElementById('buttonPreview');
    const configSummary = document.getElementById('configSummary');
    
    const text = document.getElementById('buttonText').value.trim();
    const speechPhrase = document.getElementById('speechPhrase').value.trim();
    const targetPage = document.getElementById('targetPage').value.trim();
    const llmQuery = document.getElementById('llmQuery').value.trim();
    const hidden = document.getElementById('buttonHidden').checked;
    const assignedImageUrl = document.getElementById('assignedImageUrl').value.trim();
    
    // Update preview button
    if (text) {
        let buttonHTML = `<div class="visual-button has-content">`;
        if (assignedImageUrl) {
            buttonHTML += `<div style="position: relative; width: 100%; height: 80px; background-image: url('${assignedImageUrl}'); background-size: cover; background-position: center; border-radius: 6px;">`;
            buttonHTML += `<div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); color: white; padding: 4px; font-size: 12px; text-align: center;">${text}</div>`;
            buttonHTML += `</div>`;
        } else {
            buttonHTML += text;
        }
        buttonHTML += `</div>`;
        preview.innerHTML = buttonHTML;
    } else {
        preview.innerHTML = `<div class="visual-button undefined">Undefined</div>`;
    }
    
    // Update configuration summary
    let buttonType = 'Empty';
    let action = 'No action';
    
    if (text) {
        if (llmQuery && targetPage) {
            buttonType = 'AI + Navigation';
            action = `Generate AI options, then navigate to "${targetPage}"`;
        } else if (llmQuery) {
            buttonType = 'AI Generation';
            action = 'Generate options using AI';
        } else if (targetPage) {
            buttonType = 'Navigation';
            action = `Navigate to "${targetPage}"`;
        } else {
            buttonType = 'Simple Button';
            action = speechPhrase ? `Say "${speechPhrase}"` : 'Display button text';
        }
    }
    
    document.getElementById('buttonTypeInfo').textContent = buttonType;
    document.getElementById('actionInfo').textContent = action;
}

function populateTargetPageDropdown() {
    const select = document.getElementById('targetPage');
    select.innerHTML = '<option value="">No page navigation</option>';

    // Add special pages first
    SPECIAL_PAGES.forEach(sp => {
        const option = document.createElement('option');
        option.value = '!' + sp.name;
        option.textContent = sp.displayName + ' (Special)';
        select.appendChild(option);
    });

    // Add user pages
    allUserPages.forEach(page => {
        const option = document.createElement('option');
        option.value = page.name;
        option.textContent = page.displayName || page.name;
        select.appendChild(option);
    });
}

// --- Clear All Buttons Function ---
function clearAllButtons() {
    if (confirm('Are you sure you want to clear all buttons on this page? This action cannot be undone.')) {
        if (currentPageData) {
            currentPageData.buttons = [];
            markAdminDirty(UNSAVED_SCOPE_BUTTON_GRID);
            renderButtonGrid();
        }
    }
}

// --- Comprehensive Guide Integration ---
function startComprehensiveGuide() {
    console.log('startComprehensiveGuide called');
    console.log('window.guideInstance:', window.guideInstance);
    
    // Check if the comprehensive guide is available
    if (window.guideInstance && typeof window.guideInstance.startComprehensiveGuide === 'function') {
        console.log('guideInstance found, checking properties...');
        console.log('guideInstance.smartHelp:', window.guideInstance.smartHelp);
        console.log('guideInstance.multimedia:', window.guideInstance.multimedia);
        
        // Check if the guide is fully initialized
        if (window.guideInstance.smartHelp && window.guideInstance.multimedia) {
            console.log('Comprehensive guide fully initialized, starting...');
            try {
                window.guideInstance.startComprehensiveGuide();
            } catch (error) {
                console.error('Error starting comprehensive guide:', error);
                openHelpWizard();
            }
        } else {
            // Wait a bit for initialization to complete
            console.log('Waiting for comprehensive guide to initialize...');
            setTimeout(() => {
                if (window.guideInstance && window.guideInstance.smartHelp && window.guideInstance.multimedia) {
                    console.log('Comprehensive guide now ready, starting...');
                    try {
                        window.guideInstance.startComprehensiveGuide();
                    } catch (error) {
                        console.error('Error starting comprehensive guide after wait:', error);
                        openHelpWizard();
                    }
                } else {
                    console.warn('Comprehensive guide still not ready after wait, falling back to old help wizard');
                    console.log('Final state - guideInstance:', window.guideInstance);
                    if (window.guideInstance) {
                        console.log('Final state - smartHelp:', window.guideInstance.smartHelp);
                        console.log('Final state - multimedia:', window.guideInstance.multimedia);
                    }
                    openHelpWizard();
                }
            }, 1000); // Wait longer (1 second)
        }
    } else {
        // Fallback to old help wizard if comprehensive guide is not available
        console.warn('Comprehensive guide not available, falling back to old help wizard');
        console.log('window.guideInstance exists:', !!window.guideInstance);
        if (window.guideInstance) {
            console.log('startComprehensiveGuide method exists:', typeof window.guideInstance.startComprehensiveGuide);
        }
        openHelpWizard();
    }
}

// --- Help Wizard Functions ---
let wizardStep = 1;
let wizardData = {};

function openHelpWizard() {
    wizardStep = 1;
    wizardData = {};

    // Populate wizard page dropdown
    const wizardTargetPage = document.getElementById('wizardTargetPage');
    wizardTargetPage.innerHTML = '<option value="">No, stay on current page</option>';

    // Add special pages first
    SPECIAL_PAGES.forEach(sp => {
        const option = document.createElement('option');
        option.value = '!' + sp.name;
        option.textContent = sp.displayName + ' (Special)';
        wizardTargetPage.appendChild(option);
    });

    // Add user pages
    allUserPages.forEach(page => {
        const option = document.createElement('option');
        option.value = page.name;
        option.textContent = page.displayName || page.name;
        wizardTargetPage.appendChild(option);
    });

    showWizardStep(1);
    helpWizardModal.classList.remove('hidden');
}

function closeHelpWizard() {
    helpWizardModal.classList.add('hidden');
    wizardStep = 1;
    wizardData = {};
}

function wizardNext() {
    // Collect current step data
    switch (wizardStep) {
        case 1:
            wizardData.name = document.getElementById('wizardButtonName').value.trim();
            if (!wizardData.name) {
                alert('Please enter a button name.');
                return;
            }
            break;
        case 2:
            wizardData.speechPhrase = document.getElementById('wizardSpeechPhrase').value.trim();
            break;
        case 3:
            wizardData.targetPage = document.getElementById('wizardTargetPage').value.trim();
            break;
        case 4:
            wizardData.aiDescription = document.getElementById('wizardAiDescription').value.trim();
            break;
    }
    
    wizardStep++;
    
    if (wizardStep > 4) {
        // Show preview
        showWizardPreview();
    } else {
        showWizardStep(wizardStep);
    }
}

function wizardPrev() {
    wizardStep--;
    if (wizardStep < 1) wizardStep = 1;
    showWizardStep(wizardStep);
}

function showWizardStep(step) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('hidden'));
    
    // Show current step
    document.getElementById(`wizardStep${step}`).classList.remove('hidden');
    
    // Update navigation buttons
    document.getElementById('wizardPrevBtn').classList.toggle('hidden', step === 1);
    document.getElementById('wizardNextBtn').classList.remove('hidden');
    document.getElementById('wizardAcceptBtn').classList.add('hidden');
    document.getElementById('wizardRejectBtn').classList.add('hidden');
}

function showWizardPreview() {
    // Hide all steps and show preview
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('hidden'));
    document.getElementById('wizardPreview').classList.remove('hidden');
    
    // Show loading state
    const configPreview = document.getElementById('wizardConfigPreview');
    configPreview.innerHTML = '<div class="text-center text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>Generating optimized AI prompt...</div>';
    
    // Generate LLM query from AI description if provided
    if (wizardData.aiDescription) {
        generateLLMPrompt(wizardData.aiDescription);
    } else {
        wizardData.llmQuery = "";
        updateWizardPreview();
    }
    
    // Update navigation buttons
    document.getElementById('wizardNextBtn').classList.add('hidden');
    document.getElementById('wizardAcceptBtn').classList.remove('hidden');
    document.getElementById('wizardRejectBtn').classList.remove('hidden');
}

async function generateLLMPrompt(description) {
    try {
        const response = await window.authenticatedFetch('/api/generate-llm-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: description })
        });
        
        if (response.ok) {
            const result = await response.json();
            wizardData.llmQuery = result.prompt;
        } else {
            // Fallback if API fails
            wizardData.llmQuery = `Generate #LLMOptions ${description}. Each option should be a clear, actionable choice for the user.`;
        }
    } catch (error) {
        console.error('Error generating LLM prompt:', error);
        // Fallback if request fails
        wizardData.llmQuery = `Generate #LLMOptions ${description}. Each option should be a clear, actionable choice for the user.`;
    }
    
    updateWizardPreview();
}

function updateWizardPreview() {
    // Update preview
    const preview = document.getElementById('wizardButtonPreview');
    preview.innerHTML = `<div class="visual-button has-content">${wizardData.name}</div>`;

    // Update configuration preview
    const configPreview = document.getElementById('wizardConfigPreview');
    configPreview.innerHTML = `
        <div><strong>Button Name:</strong> ${wizardData.name}</div>
        ${wizardData.speechPhrase ? `<div><strong>Speech:</strong> "${wizardData.speechPhrase}"</div>` : ''}
        ${wizardData.targetPage ? `<div><strong>Navigation:</strong> Go to "${wizardData.targetPage}"</div>` : ''}
        ${wizardData.llmQuery ? `<div><strong>AI Query:</strong> ${wizardData.llmQuery}</div>` : ''}
        <div style="margin-top:1em;">
            <button id="wizardPreviewResultsBtn" class="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 transition duration-200 ease-in-out" type="button">
                <i class="fas fa-eye mr-2"></i>Preview Results
            </button>
        </div>
        <div id="wizardLLMPreviewTable" style="margin-top:1em;"></div>
    `;

    // Attach event listener for Preview Results button
    setTimeout(() => {
        const previewBtn = document.getElementById('wizardPreviewResultsBtn');
        if (previewBtn) {
            previewBtn.addEventListener('click', previewLLMResults);
        }
    }, 0);
}

// --- LLM Preview Integration ---
async function previewLLMResults() {
    const previewDiv = document.getElementById('wizardLLMPreviewTable');
    previewDiv.innerHTML = '<div class="text-center text-gray-500 py-4"><i class="fas fa-spinner fa-spin mr-2"></i>Generating preview...</div>';
    let prompt = wizardData.llmQuery || '';
    if (!prompt) {
        previewDiv.innerHTML = '<div class="text-red-500 p-4 bg-red-50 border border-red-200 rounded">No AI Query to preview.</div>';
        return;
    }

    // Use the same authenticatedFetch as elsewhere
    try {
        const response = await window.authenticatedFetch('/llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        if (!response.ok) throw new Error('LLM request failed');
        const data = await response.json();

        // Try to extract options from the LLM response
        let options = [];
        if (Array.isArray(data)) {
            options = data;
        } else if (data.options && Array.isArray(data.options)) {
            options = data.options;
        } else if (typeof data === 'object') {
            for (const key in data) {
                if (Array.isArray(data[key]) && typeof data[key][0] === 'string') {
                    options = data[key];
                    break;
                }
            }
        }
        if (options.length === 0 && typeof data === 'string') {
            options = data.split('\n').map(s => s.trim()).filter(Boolean);
        }

        // Render as a table
        if (options.length > 0) {
            let html = '<div class="border rounded-lg overflow-hidden"><table class="w-full border-collapse"><thead class="bg-gray-100"><tr><th class="border p-2 text-left">#</th><th class="border p-2 text-left">Option</th><th class="border p-2 text-left">Summary</th></tr></thead><tbody>';
            options.forEach((opt, idx) => {
                let optionText = '';
                let summaryText = '';
                
                if (typeof opt === 'object' && opt !== null) {
                    // Handle object format {option: "...", summary: "..."}
                    optionText = opt.option || opt.text || JSON.stringify(opt);
                    summaryText = opt.summary || opt.option || '';
                } else if (typeof opt === 'string') {
                    // Handle string format
                    optionText = opt;
                    summaryText = opt.length > 20 ? opt.substring(0, 20) + '...' : opt;
                } else {
                    // Fallback for any other format
                    optionText = String(opt);
                    summaryText = String(opt);
                }
                
                html += `<tr class="hover:bg-gray-50"><td class="border p-2">${idx + 1}</td><td class="border p-2">${optionText}</td><td class="border p-2">${summaryText}</td></tr>`;
            });
            html += '</tbody></table></div>';
            previewDiv.innerHTML = html;
        } else {
            previewDiv.innerHTML = '<div class="text-red-500 p-4 bg-red-50 border border-red-200 rounded">No options returned by LLM.</div>';
        }
    } catch (err) {
        previewDiv.innerHTML = `<div class="text-red-500 p-4 bg-red-50 border border-red-200 rounded">Error: ${err.message}</div>`;
    }
}

function wizardAccept() {
    // Find empty spot for new button
    const emptySpot = findEmptyGridSpot();
    if (!emptySpot) {
        alert('No empty spots available in the grid. Please clear a button first.');
        return;
    }
    
    // Create button data
    const buttonData = {
        row: emptySpot.row,
        col: emptySpot.col,
        text: wizardData.name,
        speechPhrase: wizardData.speechPhrase || null,
        targetPage: wizardData.targetPage || "",
        LLMQuery: wizardData.llmQuery || "",
        queryType: "options",
        hidden: false
    };
    
    // Add to current page
    if (!currentPageData.buttons) currentPageData.buttons = [];
    currentPageData.buttons.push(buttonData);
    
    // Re-render and close
    renderButtonGrid();
    closeHelpWizard();
}

function wizardReject() {
    wizardStep = 4; // Go back to AI description step
    showWizardStep(4);
}

function findEmptyGridSpot() {
    for (let row = 0; row < GRID_ROWS; row++) {
        for (let col = 0; col < GRID_COLS; col++) {
            if (!findButtonAtPosition(row, col)) {
                return { row, col };
            }
        }
    }
    return null;
}

// --- Page Management Functions (keeping existing logic) ---
function authContextIsReady() {
    if (isAuthContextReady) return;
    isAuthContextReady = true;
    console.log("admin_pages.js: Auth context is ready. Stored flag.");
    initializePage();
}

function handlePageSelected() {
    const selectedPageName = selectPage.value;
    if (!selectedPageName) {
        // Clear display name and grid for new page creation
        newPageDisplayNameInput.value = '';
        document.getElementById('scanPattern').value = 'column';
        currentPageData = null;
        buttonGrid.innerHTML = '';
        for (let row = 0; row < GRID_ROWS; row++) {
            for (let col = 0; col < GRID_COLS; col++) {
                const button = createVisualButton(row, col);
                buttonGrid.appendChild(button);
            }
        }
        return;
    }

    currentPageData = allUserPages.find(page => page.name === selectedPageName);
    if (currentPageData) {
        newPageDisplayNameInput.value = currentPageData.displayName || currentPageData.name;
        document.getElementById('scanPattern').value = currentPageData.scan_pattern || 'column';
        initialPageDataString = JSON.stringify(currentPageData);
        
        // Check for buttons outside normal grid bounds
        checkForOutOfBoundsButtons();
        
        renderButtonGrid();
    }
}

async function loadPages() {
    try {
        console.log("Loading pages from backend...");
        const response = await window.authenticatedFetch('/pages');
        if (!response.ok) throw new Error(`Failed to load pages: ${response.statusText}`);
        
        allUserPages = await response.json();

        populatePageSelect();
        
        if (allUserPages.length > 0) {
            selectPage.value = allUserPages[0].name;
            handlePageSelected();
        }
    } catch (error) {
        console.error('Error loading pages:', error);
        alert('Failed to load pages. Please refresh the page.');
    }
}

function populatePageSelect() {
    selectPage.innerHTML = '<option value="">-- Select or Create New Page --</option>'; // Always first option
    //selectPage.innerHTML = '';
    allUserPages.forEach(page => {
        const option = document.createElement('option');
        option.value = page.name;
        option.textContent = page.displayName || page.name;
        selectPage.appendChild(option);
    });
    populateTranslateScopeList();
}

function populateTranslateScopeList() {
    const list = document.getElementById('translateScopeList');
    if (!list) return;
    list.innerHTML = '';
    allUserPages.forEach(page => {
        const label = document.createElement('label');
        label.className = 'flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer text-sm text-gray-700';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = page.name;
        cb.name = 'translateScopePage';
        cb.className = 'flex-shrink-0';
        label.appendChild(cb);
        const span = document.createElement('span');
        span.textContent = page.displayName || page.name;
        label.appendChild(span);
        list.appendChild(label);
    });
    if (allUserPages.length === 0) {
        list.innerHTML = '<div class="text-sm text-gray-400 p-2">No pages found.</div>';
    }
    const selectAllBtn = document.getElementById('selectAllPagesBtn');
    if (selectAllBtn) selectAllBtn.textContent = 'Select All';
}

// Function to collect any unsaved changes from the modal editor
function collectCurrentFormData() {
    console.log('Collecting current form data...');
    
    // If there's a modal open with unsaved changes, save them first
    if (currentEditingButton && buttonEditorModal && buttonEditorModal.style.display !== 'none') {
        console.log('Found open modal editor, saving current changes...');
        saveButtonEdit(); // Save any unsaved changes in the modal
    }
    
    // Debug: Log current button data
    console.log('Current page data buttons:', currentPageData ? currentPageData.buttons : 'No currentPageData');
}

async function createNewPage() {
    // Prompt for new page display name
    const displayName = prompt('Enter the display name for the new page (e.g., "Daily Greetings", "What to Eat"):');
    
    if (!displayName || !displayName.trim()) {
        return; // User cancelled or entered empty name
    }

    const trimmedDisplayName = displayName.trim();
    
    // Generate page name: all lowercase, only letters
    const pageName = trimmedDisplayName.toLowerCase().replace(/[^a-z]/g, '');
    if (!pageName) {
        alert('Display name must contain at least one letter.');
        return;
    }

    // Check if page already exists
    const pageExists = allUserPages.some(page => page.name === pageName);
    if (pageExists) {
        alert(`A page with the name "${pageName}" already exists. Please choose a different display name.`);
        return;
    }

    const pageData = {
        name: pageName,
        displayName: trimmedDisplayName,
        buttons: [] // New pages start with empty button array
    };

    console.log('Creating new page:', pageData);

    try {
        markAdminSaving(UNSAVED_SCOPE_PAGE_SETTINGS);
        const response = await window.authenticatedFetch('/pages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pageData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Failed to create page:', response.status, errorText);
            throw new Error(`Failed to create page: ${response.statusText}`);
        }

        // Reload pages and select the new page
        await loadPages();
        
        // Select the newly created page
        selectPage.value = pageName;
        await handlePageSelected();
        markAdminSaved();
        
        alert(`Page "${trimmedDisplayName}" created successfully!`);

    } catch (error) {
        console.error('Error creating page:', error);
        alert('Failed to create page. Please try again.');
    }
}

async function updatePage(scope = UNSAVED_SCOPE_PAGE_SETTINGS) {
    // Get the currently selected page
    const selectedPageName = selectPage.value;
    if (!selectedPageName) {
        alert('No page selected to update.');
        return;
    }

    const displayName = newPageDisplayNameInput.value.trim();
    if (!displayName) {
        alert('Please enter a display name.');
        return;
    }

    // Collect current form data to include any button changes
    collectCurrentFormData();

    const pageData = {
        name: selectedPageName,
        displayName: displayName,
        scan_pattern: document.getElementById('scanPattern').value || 'column',
        buttons: currentPageData ? currentPageData.buttons : [],
        originalName: selectedPageName
    };

    console.log('Updating page data:', pageData);

    try {
        markAdminSaving(scope);
        const response = await window.authenticatedFetch('/pages', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pageData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Failed to update page:', response.status, errorText);
            throw new Error(`Failed to update page: ${response.statusText}`);
        }

        await loadPages();
        
        // Maintain selection of the updated page
        selectPage.value = selectedPageName;
        await handlePageSelected();
        markAdminSaved();
        
        alert('Page updated successfully!');

    } catch (error) {
        console.error('Error updating page:', error);
        alert('Failed to update page. Please try again.');
    }
}

async function deletePage() {
    // Use the actual page name from selectPage, not a regenerated one
    const pageName = selectPage.value;
    if (!pageName) {
        alert('No page selected to delete.');
        return;
    }

    if (pageName.toLowerCase() === 'home') {
        alert('The home page cannot be deleted.');
        return;
    }

    if (!confirm(`Are you sure you want to delete the page "${pageName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        markAdminSaving(UNSAVED_SCOPE_PAGE_SETTINGS);
        const response = await window.authenticatedFetch(`/pages/${pageName}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error(`Failed to delete page: ${response.statusText}`);

        await loadPages();
    markAdminSaved();
        alert('Page deleted successfully!');

    } catch (error) {
        console.error('Error deleting page:', error);
        alert('Failed to delete page. Please try again.');
    }
}

function revertPage() {
    if (initialPageDataString) {
        currentPageData = JSON.parse(initialPageDataString);
        renderButtonGrid();
        markAdminSaved();
        alert('Changes reverted.');
    }
}

function openTranslatePagesModal() {
    populateTranslateLocaleDropdowns().catch(error => {
        console.warn('Failed to initialize translate locale dropdowns:', error);
    });
    setTranslateStatus('', 'hidden');
}

async function populateTranslateLocaleDropdowns() {
    const sourceSelect = document.getElementById('translateSourceLocale');
    const targetSelect = document.getElementById('translateTargetLocale');
    if (!sourceSelect || !targetSelect) return;

    const sourceSelectedBefore = sourceSelect.value;
    const targetSelectedBefore = targetSelect.value;

    sourceSelect.innerHTML = '';
    targetSelect.innerHTML = '';

    TRANSLATE_LOCALE_OPTIONS.forEach(locale => {
        const sourceOption = document.createElement('option');
        sourceOption.value = locale.value;
        sourceOption.textContent = `${locale.label} (${locale.value})`;
        sourceSelect.appendChild(sourceOption);

        const targetOption = document.createElement('option');
        targetOption.value = locale.value;
        targetOption.textContent = `${locale.label} (${locale.value})`;
        targetSelect.appendChild(targetOption);
    });

    let userLanguage = '';
    try {
        const response = await window.authenticatedFetch('/api/settings');
        if (response.ok) {
            const settings = await response.json();
            userLanguage = String(settings?.userLanguage || '').trim();
        }
    } catch (error) {
        console.warn('Unable to load user language for translate modal:', error);
    }

    const validLocaleValues = new Set(TRANSLATE_LOCALE_OPTIONS.map(locale => locale.value));
    const fallbackTarget = validLocaleValues.has(userLanguage) ? userLanguage : 'en-US';

    sourceSelect.value = validLocaleValues.has(sourceSelectedBefore) ? sourceSelectedBefore : 'en-US';
    targetSelect.value = validLocaleValues.has(targetSelectedBefore) ? targetSelectedBefore : fallbackTarget;
}

function closeTranslatePagesModal() {
    // No-op: translate is now a full page section, not a modal
}

function setTranslateStatus(message, tone = 'info') {
    const statusEl = document.getElementById('translatePagesStatus');
    if (!statusEl) return;

    if (!message) {
        statusEl.textContent = '';
        statusEl.className = 'hidden text-sm rounded-md px-3 py-2';
        return;
    }

    statusEl.classList.remove('hidden');
    statusEl.textContent = message;

    if (tone === 'success') {
        statusEl.className = 'text-sm rounded-md px-3 py-2 bg-green-100 text-green-800';
    } else if (tone === 'error') {
        statusEl.className = 'text-sm rounded-md px-3 py-2 bg-red-100 text-red-800';
    } else {
        statusEl.className = 'text-sm rounded-md px-3 py-2 bg-blue-100 text-blue-800';
    }
}

async function runPageTranslation() {
    const sourceLocaleRaw = (document.getElementById('translateSourceLocale')?.value || '').trim();
    const targetLocale = (document.getElementById('translateTargetLocale')?.value || '').trim();

    const includeDisplayName = Boolean(document.getElementById('translateIncludeDisplayName')?.checked);
    const includeButtonText = Boolean(document.getElementById('translateIncludeButtonText')?.checked);
    const includeSpeechPhrase = Boolean(document.getElementById('translateIncludeSpeechPhrase')?.checked);
    const includeLlmQuery = Boolean(document.getElementById('translateIncludeLlmQuery')?.checked);

    if (!targetLocale) {
        setTranslateStatus('Please provide a target locale, for example es-US.', 'error');
        return;
    }

    if (!includeDisplayName && !includeButtonText && !includeSpeechPhrase && !includeLlmQuery) {
        setTranslateStatus('Select at least one field to translate.', 'error');
        return;
    }

    const list = document.getElementById('translateScopeList');
    const checkedBoxes = list ? Array.from(list.querySelectorAll('input[type="checkbox"]:checked')) : [];
    if (checkedBoxes.length === 0) {
        setTranslateStatus('Select at least one page to translate.', 'error');
        return;
    }

    const allSelected = checkedBoxes.length === allUserPages.length;
    const selectedPageBeforeRefresh = selectPage?.value || '';

    const basePayload = {
        source_locale: sourceLocaleRaw || null,
        target_locale: targetLocale,
        include_display_name: includeDisplayName,
        include_button_text: includeButtonText,
        include_speech_phrase: includeSpeechPhrase,
        include_llm_query: includeLlmQuery
    };

    try {
        if (runTranslatePagesBtn) runTranslatePagesBtn.disabled = true;
        setTranslateStatus('Translating content. This can take a moment for larger boards...', 'info');

        let totalChanged = 0, totalPages = 0, totalSpecial = 0, totalTapBoards = 0;

        if (allSelected) {
            const payload = { ...basePayload, scope: 'all', page_name: null };
            const response = await window.authenticatedFetch('/api/admin/translate-pages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result?.detail || `Translation failed (${response.status})`);
            totalChanged += Number(result?.strings_changed || 0);
            totalPages += Number(result?.pages_processed || 0);
            totalSpecial += Number(result?.special_pages_changed || 0);
            totalTapBoards += Number(result?.tap_boards_prompts_changed || 0);
        } else {
            for (const cb of checkedBoxes) {
                const payload = { ...basePayload, scope: 'current', page_name: cb.value };
                const response = await window.authenticatedFetch('/api/admin/translate-pages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(result?.detail || `Translation failed for "${cb.value}" (${response.status})`);
                totalChanged += Number(result?.strings_changed || 0);
                totalPages += Number(result?.pages_processed || 0);
                totalSpecial += Number(result?.special_pages_changed || 0);
                totalTapBoards += Number(result?.tap_boards_prompts_changed || 0);
            }
        }

        await loadPages();
        if (selectedPageBeforeRefresh) {
            selectPage.value = selectedPageBeforeRefresh;
            handlePageSelected();
        }

        const specialSuffix = totalSpecial > 0 ? ` Included ${totalSpecial} special page bundle(s).` : '';
        const tapSuffix = totalTapBoards > 0 ? ` Updated ${totalTapBoards} Tap board prompt(s).` : '';
        setTranslateStatus(`Translation complete. Updated ${totalChanged} field(s) across ${totalPages} page(s).${specialSuffix}${tapSuffix}`, 'success');
    } catch (error) {
        console.error('Error translating pages:', error);
        setTranslateStatus(`Translation failed: ${error.message || 'Unknown error'}`, 'error');
    } finally {
        if (runTranslatePagesBtn) runTranslatePagesBtn.disabled = false;
    }
}

// --- Event Listeners for DOM and Auth ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("admin_pages.js: DOM content loaded. Stored flag.");
    isDomContentLoaded = true;
    initializePage();
});

document.addEventListener('adminUserContextReady', function() {
    console.log("admin_pages.js: Received adminUserContextReady event. Calling authContextIsReady().");
    authContextIsReady();
});

// --- Image Assignment Functions ---
let currentImageSearch = '';
let currentImagePage = 0;
let totalImagePages = 0;
let allImages = [];
let selectedImageUrl = null;

function updateAssignedImagePreview(imageUrl) {
    const preview = document.getElementById('assignedImagePreview');
    const thumb = document.getElementById('assignedImageThumb');
    const clearBtn = document.getElementById('clearImageBtn');
    
    if (imageUrl) {
        preview.classList.remove('hidden');
        clearBtn.classList.remove('hidden');
        thumb.src = imageUrl;
        thumb.alt = 'Assigned image';
    } else {
        preview.classList.add('hidden');
        clearBtn.classList.add('hidden');
        thumb.src = '';
        thumb.alt = '';
    }
}

function openImagePicker() {
    console.log('openImagePicker called');
    console.log('imagePickerModal:', imagePickerModal);
    
    selectedImageUrl = null;
    const selectBtn = document.getElementById('selectImageBtn');
    if (selectBtn) {
        selectBtn.disabled = true;
    }
    
    if (imagePickerModal) {
        imagePickerModal.classList.remove('hidden');
        loadImages();
    } else {
        console.error('imagePickerModal is null - cannot open modal');
    }
}

function closeImagePicker() {
    imagePickerModal.classList.add('hidden');
    document.getElementById('imageSearchInput').value = '';
    currentImageSearch = '';
    currentImagePage = 0;
    selectedImageUrl = null;
}

function clearAssignedImage() {
    document.getElementById('assignedImageUrl').value = '';
    updateAssignedImagePreview('');
    updateButtonPreview();
}

async function loadImages(searchTerm = '', page = 0) {
    const loadingIndicator = document.getElementById('imageLoadingIndicator');
    const imageGrid = document.getElementById('imageGrid');
    const resultsInfo = document.getElementById('imageResultsInfo');
    const pageInfo = document.getElementById('imagePageInfo');
    const prevBtn = document.getElementById('imagePrevPage');
    const nextBtn = document.getElementById('imageNextPage');
    
    try {
        loadingIndicator.classList.remove('hidden');
        imageGrid.innerHTML = '';
        
        const params = new URLSearchParams({
            page: page.toString(),
            limit: '48'
        });
        
        if (searchTerm) {
            params.append('search', searchTerm);
        }
        
        const response = await window.authenticatedFetch(`/api/admin/images/browse?${params}`, {
            method: 'GET'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        allImages = data.images || [];
        currentImagePage = data.page || 0;
        totalImagePages = data.total_pages || 0;
        
        // Update UI
        resultsInfo.textContent = `Showing ${allImages.length} of ${data.total_count || 0} images`;
        pageInfo.textContent = `Page ${currentImagePage + 1} of ${totalImagePages}`;
        
        prevBtn.disabled = currentImagePage <= 0;
        nextBtn.disabled = currentImagePage >= totalImagePages - 1;
        
        // Render images
        renderImageGrid();
        
    } catch (error) {
        console.error('Error loading images:', error);
        resultsInfo.textContent = 'Error loading images';
        imageGrid.innerHTML = '<div class="col-span-full text-center text-red-500 py-8">Failed to load images. Please try again.</div>';
    } finally {
        loadingIndicator.classList.add('hidden');
    }
}

function renderImageGrid() {
    const imageGrid = document.getElementById('imageGrid');
    imageGrid.innerHTML = '';
    
    allImages.forEach(image => {
        const imageCard = document.createElement('div');
        imageCard.className = 'relative cursor-pointer border-2 border-transparent hover:border-blue-500 rounded-md overflow-hidden bg-gray-100';
        imageCard.onclick = () => selectImageInGrid(image.image_url, imageCard);
        
        const displayName = image.subconcept || image.concept || 'Image';
        
        imageCard.innerHTML = `
            <img src="${image.image_url}" alt="${displayName}" 
                 class="w-full h-20 object-cover" 
                 loading="lazy"
                 onerror="this.parentElement.innerHTML='<div class=\\'w-full h-20 flex items-center justify-center bg-gray-200 text-gray-500 text-xs\\'>Image failed to load</div>'">
            <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 truncate">
                ${displayName}
            </div>
        `;
        
        imageGrid.appendChild(imageCard);
    });
}

function selectImageInGrid(imageUrl, cardElement) {
    // Remove previous selection
    document.querySelectorAll('#imageGrid > div').forEach(card => {
        card.classList.remove('border-blue-500', 'bg-blue-50');
        card.classList.add('border-transparent');
    });
    
    // Highlight selected
    cardElement.classList.remove('border-transparent');
    cardElement.classList.add('border-blue-500', 'bg-blue-50');
    
    selectedImageUrl = imageUrl;
    document.getElementById('selectImageBtn').disabled = false;
}

function selectAssignedImage() {
    if (selectedImageUrl) {
        document.getElementById('assignedImageUrl').value = selectedImageUrl;
        updateAssignedImagePreview(selectedImageUrl);
        updateButtonPreview();
        closeImagePicker();
    }
}

function searchImages() {
    const searchTerm = document.getElementById('imageSearchInput').value.trim();
    currentImageSearch = searchTerm;
    currentImagePage = 0;
    loadImages(searchTerm, 0);
}

function clearImageSearch() {
    document.getElementById('imageSearchInput').value = '';
    currentImageSearch = '';
    currentImagePage = 0;
    loadImages('', 0);
}

function navigateImagePage(direction) {
    const newPage = currentImagePage + direction;
    if (newPage >= 0 && newPage < totalImagePages) {
        currentImagePage = newPage;
        loadImages(currentImageSearch, newPage);
    }
}

// ── Create New Page Wizard ───────────────────────────────────────────────────

let _cpwOptions = [];

function openCreatePageWizard() {
    _cpwOptions = [];
    document.getElementById('cpwDisplayName').value = '';
    document.getElementById('cpwDupWarn').classList.add('hidden');
    document.getElementById('cpwTopic').value = '';
    document.getElementById('cpwExamples').value = '';
    document.getElementById('cpwExclusions').value = '';
    document.getElementById('cpwCount').value = '20';
    document.getElementById('cpwAiNo').checked = true;
    _cpwUpdateChoiceStyles();
    _cpwGoToStep(1);
    document.getElementById('createPageWizardModal').classList.remove('hidden');
}

function closeCreatePageWizard() {
    document.getElementById('createPageWizardModal').classList.add('hidden');
}

function _cpwUpdateChoiceStyles() {
    const aiChosen = document.getElementById('cpwAiYes').checked;
    document.getElementById('cpwAiYesLabel').className = `flex-1 flex flex-col items-center justify-center gap-1 p-3 border-2 rounded-lg cursor-pointer transition-all ${aiChosen ? 'border-violet-400 bg-violet-50' : 'border-gray-200 hover:border-violet-300'}`;
    document.getElementById('cpwAiNoLabel').className = `flex-1 flex flex-col items-center justify-center gap-1 p-3 border-2 rounded-lg cursor-pointer transition-all ${!aiChosen ? 'border-green-300 bg-green-50' : 'border-gray-200 hover:border-green-300'}`;
}

function _cpwGoToStep(step) {
    [1, 2, 3].forEach(n => {
        document.getElementById(`cpw-step${n}`).classList.toggle('hidden', n !== step);
    });
    const isAi = step > 1;
    document.getElementById('cpwStepIndicator').classList.toggle('hidden', !isAi);
    if (isAi) {
        [1, 2, 3].forEach(n => {
            const dot = document.getElementById(`cpwDot${n}`);
            const lbl = document.getElementById(`cpwLbl${n}`);
            if (n < step) dot.className = 'cbw-step-dot done';
            else if (n === step) dot.className = 'cbw-step-dot active';
            else dot.className = 'cbw-step-dot';
            if (lbl) lbl.className = `flex-1 text-center ${n === step ? 'font-medium text-green-600' : 'text-gray-400'}`;
        });
    }
}

function _cpwRenderOptions() {
    const list = document.getElementById('cpwOptionsList');
    list.innerHTML = '';
    document.getElementById('cpwOptionsCount').textContent = _cpwOptions.length;
    _cpwOptions.forEach((item, idx) => {
        const row = document.createElement('div');
        row.className = 'flex items-center gap-2 bg-white border border-gray-200 rounded px-2 py-1';
        row.draggable = true;
        row.dataset.idx = idx;

        const grip = document.createElement('span');
        grip.className = 'text-gray-300 cursor-grab select-none';
        grip.innerHTML = '<i class="fas fa-grip-vertical"></i>';

        const input = document.createElement('input');
        input.type = 'text';
        input.value = item.label;
        input.className = 'flex-1 text-sm border-none outline-none bg-transparent';
        input.addEventListener('input', () => { _cpwOptions[idx].label = input.value; });

        const del = document.createElement('button');
        del.type = 'button';
        del.className = 'text-red-400 hover:text-red-600 text-xs px-1';
        del.innerHTML = '<i class="fas fa-times"></i>';
        del.addEventListener('click', () => { _cpwOptions.splice(idx, 1); _cpwRenderOptions(); });

        row.appendChild(grip);
        row.appendChild(input);
        row.appendChild(del);

        row.addEventListener('dragstart', e => { e.dataTransfer.setData('text/plain', idx); row.classList.add('opacity-50'); });
        row.addEventListener('dragend', () => row.classList.remove('opacity-50'));
        row.addEventListener('dragover', e => { e.preventDefault(); row.classList.add('bg-violet-50'); });
        row.addEventListener('dragleave', () => row.classList.remove('bg-violet-50'));
        row.addEventListener('drop', e => {
            e.preventDefault();
            row.classList.remove('bg-violet-50');
            const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
            if (fromIdx === idx) return;
            const [moved] = _cpwOptions.splice(fromIdx, 1);
            _cpwOptions.splice(idx, 0, moved);
            _cpwRenderOptions();
        });

        list.appendChild(row);
    });
}

async function _cpwGenerate() {
    const topic = document.getElementById('cpwTopic').value.trim();
    if (!topic) { alert('Please enter a topic first.'); return; }
    const examples = document.getElementById('cpwExamples').value.trim();
    const exclusions = document.getElementById('cpwExclusions').value.trim();
    const maxCount = Math.min(50, Math.max(5, parseInt(document.getElementById('cpwCount').value, 10) || 20));

    const btn = document.getElementById('cpwGenerateBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Generating…';

    try {
        let prompt = `Generate UP TO ${maxCount} UNIQUE button labels for an AAC communication page about: ${topic}.\n`;
        if (examples) prompt += `Examples of the type of options to include: ${examples}\n`;
        if (exclusions) prompt += `Do NOT include any of these: ${exclusions}\n`;
        prompt += `\nRequirements:\n- Short labels (1–4 words each)\n- No duplicates\n- Practical and relevant to the topic\n- Return as a JSON array of strings ONLY — e.g. ["eat","drink","play"]`;

        const response = await window.authenticatedFetch('/llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, response_format: 'json' })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        let labels = [];
        if (Array.isArray(data)) {
            labels = data.map(item => typeof item === 'string' ? item : (item.option || item.label || ''));
        } else if (data && Array.isArray(data.options)) {
            labels = data.options.map(o => typeof o === 'string' ? o : (o.option || o.label || ''));
        } else if (typeof data === 'string') {
            labels = data.split('\n').map(s => s.trim()).filter(Boolean);
        }
        labels = labels.filter(l => l && l.trim()).slice(0, maxCount);

        if (!labels.length) { alert('No options returned — try a different topic.'); return; }

        _cpwOptions = labels.map(l => ({ label: l.trim() }));
        _cpwRenderOptions();
        _cpwGoToStep(3);
    } catch (err) {
        console.error('Create Page Wizard generate error:', err);
        alert('Generation failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i>Generate Options';
    }
}

async function _cpwCreatePage(withAiButtons) {
    const displayName = document.getElementById('cpwDisplayName').value.trim();
    if (!displayName) { alert('Please enter a page name.'); _cpwGoToStep(1); return; }

    const pageName = displayName.toLowerCase().replace(/[^a-z]/g, '');
    if (!pageName) { alert('Display name must contain at least one letter.'); return; }

    const buttons = [];
    if (withAiButtons) {
        const valid = _cpwOptions.filter(o => o.label.trim());
        let row = 0, col = 0;
        valid.forEach(item => {
            buttons.push({ ...DEFAULT_PAGE_BUTTON_STRUCTURE, text: item.label, row, col });
            col++;
            if (col >= GRID_COLS) { col = 0; row++; }
        });
    }

    const pageData = { name: pageName, displayName, buttons };

    const createBtn = document.getElementById('cpwCreateBtn');
    if (createBtn) { createBtn.disabled = true; createBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Creating…'; }

    try {
        markAdminSaving(UNSAVED_SCOPE_PAGE_SETTINGS);
        const response = await window.authenticatedFetch('/pages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pageData)
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to create page: ${errorText || response.statusText}`);
        }
        await loadPages();
        selectPage.value = pageName;
        await handlePageSelected();
        markAdminSaved();
        closeCreatePageWizard();
    } catch (error) {
        console.error('Error creating page:', error);
        alert('Failed to create page. Please try again.');
        markAdminSaved();
    } finally {
        if (createBtn) { createBtn.disabled = false; createBtn.innerHTML = '<i class="fas fa-plus-circle"></i> Create Page'; }
    }
}

function _cpwWireEvents() {
    document.getElementById('closeCreatePageWizard')?.addEventListener('click', closeCreatePageWizard);

    // Update radio choice styles on change
    document.querySelectorAll('input[name="cpwUseAi"]').forEach(r =>
        r.addEventListener('change', _cpwUpdateChoiceStyles)
    );
    // Clicking the label cards also toggles the radio
    document.getElementById('cpwAiYesLabel')?.addEventListener('click', () => {
        document.getElementById('cpwAiYes').checked = true;
        _cpwUpdateChoiceStyles();
    });
    document.getElementById('cpwAiNoLabel')?.addEventListener('click', () => {
        document.getElementById('cpwAiNo').checked = true;
        _cpwUpdateChoiceStyles();
    });

    // Step 1 Next
    document.getElementById('cpwStep1NextBtn')?.addEventListener('click', () => {
        const displayName = document.getElementById('cpwDisplayName').value.trim();
        if (!displayName) { alert('Please enter a page display name.'); return; }
        const pageName = displayName.toLowerCase().replace(/[^a-z]/g, '');
        if (!pageName) { alert('Display name must contain at least one letter.'); return; }

        const useAi = document.getElementById('cpwAiYes').checked;
        if (useAi) {
            document.getElementById('cpwStepIndicator').classList.remove('hidden');
            _cpwGoToStep(2);
        } else {
            _cpwCreatePage(false);
        }
    });

    // Step 2
    document.getElementById('cpwStep2BackBtn')?.addEventListener('click', () => _cpwGoToStep(1));
    document.getElementById('cpwGenerateBtn')?.addEventListener('click', _cpwGenerate);

    // Step 3
    document.getElementById('cpwStep3BackBtn')?.addEventListener('click', () => _cpwGoToStep(2));
    document.getElementById('cpwAddOptionBtn')?.addEventListener('click', () => {
        _cpwOptions.push({ label: '' });
        _cpwRenderOptions();
        const inputs = document.getElementById('cpwOptionsList').querySelectorAll('input');
        if (inputs.length) inputs[inputs.length - 1].focus();
    });
    document.getElementById('cpwCreateBtn')?.addEventListener('click', () => _cpwCreatePage(true));
}

// ── Bravo Button Wizard ─────────────────────────────────────────────────────

let _bbwOptions = []; // [{label}]

function openBravoButtonWizard() {
    if (!currentPageData) {
        alert('Please select a page first.');
        return;
    }
    _bbwOptions = [];
    document.getElementById('bbwTopic').value = '';
    document.getElementById('bbwExamples').value = '';
    document.getElementById('bbwExclusions').value = '';
    document.getElementById('bbwCount').value = '20';
    _bbwGoToStep(1);

    // Populate target page dropdown
    const sel = document.getElementById('bbwTargetPage');
    sel.innerHTML = '<option value="">No page navigation</option>';
    if (Array.isArray(SPECIAL_PAGES)) {
        SPECIAL_PAGES.forEach(sp => {
            const o = document.createElement('option');
            o.value = '!' + sp.name;
            o.textContent = (sp.displayName || sp.name) + ' (Special)';
            sel.appendChild(o);
        });
    }
    if (Array.isArray(allUserPages)) {
        allUserPages.forEach(page => {
            const o = document.createElement('option');
            o.value = page.name;
            o.textContent = page.displayName || page.name;
            sel.appendChild(o);
        });
    }

    // Show/hide replace section based on whether buttons exist
    const hasButtons = currentPageData.buttons && currentPageData.buttons.length > 0;
    document.getElementById('bbwReplaceSection').style.display = hasButtons ? '' : 'none';
    if (!hasButtons) document.getElementById('bbwModeReplace').checked = true;

    document.getElementById('bravoButtonWizardModal').classList.remove('hidden');
}

function closeBravoButtonWizard() {
    document.getElementById('bravoButtonWizardModal').classList.add('hidden');
}

function _bbwGoToStep(step) {
    [1, 2, 3].forEach(n => {
        document.getElementById(`bbw-step${n}`).classList.toggle('hidden', n !== step);
        const dot = document.getElementById(`bbwDot${n}`);
        const lbl = document.getElementById(`bbwLbl${n}`);
        if (n < step) { dot.className = 'cbw-step-dot done'; }
        else if (n === step) { dot.className = 'cbw-step-dot active'; }
        else { dot.className = 'cbw-step-dot'; }
        if (lbl) {
            lbl.className = n === step
                ? 'flex-1 text-center font-medium text-violet-600'
                : 'flex-1 text-center text-gray-400';
        }
    });
    if (step === 3) _bbwUpdateSummary();
}

function _bbwRenderOptions() {
    const list = document.getElementById('bbwOptionsList');
    list.innerHTML = '';
    document.getElementById('bbwOptionsCount').textContent = _bbwOptions.length;
    _bbwOptions.forEach((item, idx) => {
        const row = document.createElement('div');
        row.className = 'flex items-center gap-2 bg-white border border-gray-200 rounded px-2 py-1';
        row.draggable = true;
        row.dataset.idx = idx;

        const grip = document.createElement('span');
        grip.className = 'text-gray-300 cursor-grab select-none';
        grip.innerHTML = '<i class="fas fa-grip-vertical"></i>';

        const input = document.createElement('input');
        input.type = 'text';
        input.value = item.label;
        input.className = 'flex-1 text-sm border-none outline-none bg-transparent';
        input.addEventListener('input', () => { _bbwOptions[idx].label = input.value; });

        const del = document.createElement('button');
        del.type = 'button';
        del.className = 'text-red-400 hover:text-red-600 text-xs px-1';
        del.innerHTML = '<i class="fas fa-times"></i>';
        del.addEventListener('click', () => { _bbwOptions.splice(idx, 1); _bbwRenderOptions(); });

        row.appendChild(grip);
        row.appendChild(input);
        row.appendChild(del);

        // Drag-and-drop reorder
        row.addEventListener('dragstart', e => {
            e.dataTransfer.setData('text/plain', idx);
            row.classList.add('opacity-50');
        });
        row.addEventListener('dragend', () => row.classList.remove('opacity-50'));
        row.addEventListener('dragover', e => { e.preventDefault(); row.classList.add('bg-violet-50'); });
        row.addEventListener('dragleave', () => row.classList.remove('bg-violet-50'));
        row.addEventListener('drop', e => {
            e.preventDefault();
            row.classList.remove('bg-violet-50');
            const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
            const toIdx = idx;
            if (fromIdx === toIdx) return;
            const [moved] = _bbwOptions.splice(fromIdx, 1);
            _bbwOptions.splice(toIdx, 0, moved);
            _bbwRenderOptions();
        });

        list.appendChild(row);
    });
}

function _bbwUpdateSummary() {
    const count = _bbwOptions.filter(o => o.label.trim()).length;
    const hasButtons = currentPageData && currentPageData.buttons && currentPageData.buttons.length > 0;
    const mode = document.querySelector('input[name="bbwMode"]:checked')?.value || 'replace';
    const targetPage = document.getElementById('bbwTargetPage').value;
    let text = `${count} button${count !== 1 ? 's' : ''} will be ${hasButtons && mode === 'replace' ? 'created, replacing existing buttons' : 'added'} on this page.`;
    if (targetPage) text += ` Each button will navigate to "${document.getElementById('bbwTargetPage').selectedOptions[0]?.textContent}".`;
    document.getElementById('bbwSummary').textContent = text;
}

async function _bbwGenerate() {
    const topic = document.getElementById('bbwTopic').value.trim();
    if (!topic) { alert('Please enter a topic first.'); return; }
    const examples = document.getElementById('bbwExamples').value.trim();
    const exclusions = document.getElementById('bbwExclusions').value.trim();
    const maxCount = Math.min(50, Math.max(5, parseInt(document.getElementById('bbwCount').value, 10) || 20));

    const btn = document.getElementById('bbwGenerateBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Generating…';

    try {
        let prompt = `Generate UP TO ${maxCount} UNIQUE button labels for an AAC communication page about: ${topic}.\n`;
        if (examples) prompt += `Examples of the type of options to include: ${examples}\n`;
        if (exclusions) prompt += `Do NOT include any of these: ${exclusions}\n`;
        prompt += `\nRequirements:\n- Short labels (1–4 words each)\n- No duplicates\n- Practical and relevant to the topic\n- Return as a JSON array of strings ONLY — e.g. ["eat","drink","play"]`;

        const response = await window.authenticatedFetch('/llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, response_format: 'json' })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        let labels = [];
        if (Array.isArray(data)) {
            labels = data.map(item => typeof item === 'string' ? item : (item.option || item.label || JSON.stringify(item)));
        } else if (data && Array.isArray(data.options)) {
            labels = data.options.map(o => typeof o === 'string' ? o : (o.option || o.label || ''));
        } else if (typeof data === 'string') {
            labels = data.split('\n').map(s => s.trim()).filter(Boolean);
        }
        labels = labels.filter(l => l && l.trim()).slice(0, maxCount);

        if (!labels.length) { alert('No options returned — try a different topic.'); return; }

        _bbwOptions = labels.map(l => ({ label: l.trim() }));
        _bbwRenderOptions();
        _bbwGoToStep(2);
    } catch (err) {
        console.error('Bravo Button Wizard generate error:', err);
        alert('Generation failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i>Generate Options';
    }
}

function _bbwSaveButtons() {
    if (!currentPageData) return;
    const valid = _bbwOptions.filter(o => o.label.trim());
    if (!valid.length) { alert('No buttons to save.'); return; }

    const hasButtons = currentPageData.buttons && currentPageData.buttons.length > 0;
    const mode = document.querySelector('input[name="bbwMode"]:checked')?.value || 'replace';
    const targetPage = document.getElementById('bbwTargetPage').value.trim();

    if (!currentPageData.buttons) currentPageData.buttons = [];

    if (hasButtons && mode === 'replace') {
        currentPageData.buttons = [];
    }

    valid.forEach(item => {
        const spot = findEmptyGridSpot();
        if (!spot) return;
        currentPageData.buttons.push({
            ...DEFAULT_PAGE_BUTTON_STRUCTURE,
            text: item.label,
            targetPage: targetPage || '',
            navigationType: targetPage ? 'PERMANENT' : '',
            row: spot.row,
            col: spot.col
        });
    });

    markAdminDirty(UNSAVED_SCOPE_BUTTON_GRID);
    renderButtonGrid();
    closeBravoButtonWizard();
}

// Fallback: Check if auth context already exists
if (typeof window.adminContextInitializedByInlineScript !== 'undefined' && window.adminContextInitializedByInlineScript) {
    console.log("admin_pages.js: Auth context already available. Calling authContextIsReady().");
    authContextIsReady();
}
