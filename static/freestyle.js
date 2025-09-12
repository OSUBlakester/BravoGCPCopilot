// --- Freestyle Communication JavaScript ---

// --- Global Variables (Similar to gridpage.js) ---
let currentlyScannedButton = null; // Tracks the currently highlighted button
let lastGamepadInputTime = 0; // For gamepad debounce/rate limiting
let isLLMProcessing = false; // Flag to detect if LLM query is running
const clickDebounceDelay = 300; // Debounce for button clicks
let defaultDelay = 3500; // Default auditory scan delay (ms) - Loaded from settings
let scanningInterval; // Holds the interval ID for scanning
let currentButtonIndex = -1; // Tracks the index for scanning
let scanCycleCount = 0; // Tracks how many complete cycles have been performed
let scanLoopLimit = 0; // 0 = unlimited, 1-10 = limit cycles
let isPausedFromScanLimit = false; // Flag to track if scanning is paused due to scan limit
let gamepadIndex = null; // To store the index of the connected gamepad
let gamepadPollInterval = null; // Interval ID for gamepad polling
let scanningPaused = false; // Global scanning pause flag
let gridColumns = 6; // Default number of grid columns for alphabet grid sizing
let autoClean = false; // Auto Clean setting for automatic cleanup on Speak Display

// --- User Management Variables (Same as gridpage.js) ---
let currentAacUserId = null;
let firebaseIdToken = null;
const AAC_USER_ID_SESSION_KEY = "currentAacUserId";
const FIREBASE_TOKEN_SESSION_KEY = "firebaseIdToken";
const SELECTED_DISPLAY_NAME_SESSION_KEY = "selectedDisplayName";
const SPEECH_HISTORY_LOCAL_STORAGE_KEY = (aacUserId) => `speechHistory_${aacUserId}`;

// --- Audio Variables ---
let personalSpeakerId = localStorage.getItem('bravoPersonalSpeakerId') || 'default';
let systemSpeakerId = localStorage.getItem('bravoSystemSpeakerId') || 'default';
let currentTtsVoiceName = 'en-US-Neural2-A';
let currentSpeechRate = 180;

// --- Announcement Queue Variables ---
let announcementQueue = [];
let isAnnouncingNow = false;
let audioContextResumeAttempted = false;

// --- Freestyle Specific Variables ---
let currentBuildSpaceText = "";
let currentWordOptions = [];
let currentSpellingWord = "";
let currentPredictions = [];
let isSpellingModalOpen = false;
let isChooseWordModalOpen = false;
let currentChooseWordCategory = "";
let currentCategoryWords = [];
let currentScanningContext = "main"; // "main", "spelling-letters", "spelling-predictions", "choose-word-categories", "choose-word-options"

// --- Initialize on Page Load ---
document.addEventListener('DOMContentLoaded', async () => {
    const userReady = await initializeUserContext();
    if (!userReady) {
        window.location.href = '/static/auth.html';
        return;
    }

    // Initialize the page (loads settings first)
    await initializeFreestylePage();
    
    // Setup input listeners
    setupKeyboardListener();
    setupGamepadListeners();
    
    // Setup audio context resume listeners
    document.body.addEventListener('mousedown', tryResumeAudioContext, { once: true });
    document.body.addEventListener('touchstart', tryResumeAudioContext, { once: true });
    document.body.addEventListener('keydown', tryResumeAudioContext, { once: true });
    
    // Setup PIN modal functionality
    setupPinModal();
    
    // Start scanning after everything is initialized
    startInitialScanning();
});

// --- User Context Initialization (Same as gridpage.js) ---
async function initializeUserContext() {
    firebaseIdToken = sessionStorage.getItem(FIREBASE_TOKEN_SESSION_KEY);
    currentAacUserId = sessionStorage.getItem(AAC_USER_ID_SESSION_KEY);

    if (!firebaseIdToken || !currentAacUserId) {
        console.error('User authentication not found. Redirecting to auth page.');
        return false;
    }
    console.log(`User context initialized. AAC User ID: ${currentAacUserId}`);
    
    // Load and update page title with profile name
    await updatePageTitleWithProfile();
    
    return true;
}

// Function to update page title with profile name
async function updatePageTitleWithProfile() {
    try {
        const response = await authenticatedFetch('/api/account/users');
        if (!response.ok) return;
        
        const profiles = await response.json();
        const currentProfile = profiles.find(profile => profile.aac_user_id === currentAacUserId);
        
        if (currentProfile && currentProfile.display_name) {
            const titleElement = document.getElementById('dynamic-page-title');
            if (titleElement) {
                const baseTitle = 'Free Style Communication';
                titleElement.textContent = `${baseTitle} - ${currentProfile.display_name}`;
                console.log(`Updated freestyle page title to include profile: ${currentProfile.display_name}`);
            }
        }
    } catch (error) {
        console.error('Error updating page title with profile:', error);
    }
}

// --- Core Fetch Wrapper (Same as gridpage.js) ---
async function authenticatedFetch(url, options = {}) {
    if (!firebaseIdToken || !currentAacUserId) {
        throw new Error('User not authenticated');
    }

    const headers = options.headers || {};
    headers['Authorization'] = `Bearer ${firebaseIdToken}`;
    headers['X-User-ID'] = currentAacUserId;
    
    // Check for admin context and add target account header if needed
    const adminTargetAccountId = sessionStorage.getItem('adminTargetAccountId');
    if (adminTargetAccountId) {
        headers['X-Admin-Target-Account'] = adminTargetAccountId;
    }
    
    options.headers = headers;

    const response = await fetch(url, options);
    if (response.status === 401 || response.status === 403) {
        console.error('Authentication failed. Redirecting to auth page.');
        window.location.href = '/static/auth.html';
        throw new Error('Authentication failed');
    }
    return response;
}

// --- Settings Loading (Similar to gridpage.js) ---
async function loadScanSettings() {
    try {
        const response = await authenticatedFetch('/api/settings');
        if (response.ok) {
            const settings = await response.json();
            defaultDelay = settings.scanDelay || 3500;
            scanLoopLimit = settings.scanLoopLimit || 0;
            currentTtsVoiceName = settings.selected_tts_voice_name || 'en-US-Neural2-A';
            currentSpeechRate = settings.speech_rate || 180;
            autoClean = settings.autoClean || false; // Load Auto Clean setting
            
            // Load gridColumns setting
            if (settings && typeof settings.gridColumns === 'number' && !isNaN(settings.gridColumns)) {
                gridColumns = Math.max(2, Math.min(18, parseInt(settings.gridColumns)));
                console.log(`Grid Columns loaded: ${gridColumns}`);
            } else {
                gridColumns = 6; // Default value for alphabet grid
            }
            
            console.log('Scan settings loaded:', { defaultDelay, scanLoopLimit, gridColumns, autoClean });
        }
    } catch (error) {
        console.error('Error loading scan settings:', error);
    }
}

// --- Grid Layout Update Function (Similar to gridpage.js) ---
function updateAlphabetGridLayout() {
    const grid = document.getElementById('alphabet-grid');
    if (!grid) return;
    
    // Update the CSS grid template columns based on gridColumns setting
    grid.style.gridTemplateColumns = `repeat(${gridColumns}, 1fr)`;
    
    // Calculate font size based on number of columns
    // Fewer columns (larger buttons) = larger font size
    // More columns (smaller buttons) = smaller font size
    const baseFontSize = 16; // Base font size in pixels for letters
    const minFontSize = 10;  // Minimum font size
    const maxFontSize = 20;  // Maximum font size
    
    // Calculate font size: inversely proportional to number of columns
    // Formula: baseFontSize * (baseFactor / gridColumns) where baseFactor is calibrated for good results
    const fontSize = Math.max(minFontSize, Math.min(maxFontSize, baseFontSize * (6 / gridColumns)));
    
    // Set the CSS custom property for letter button font size
    grid.style.setProperty('--letter-font-size', `${fontSize}px`);
    
    console.log(`Alphabet grid layout updated to ${gridColumns} columns with ${fontSize}px font size`);
}

// --- Update Word Options Grid Layout ---
function updateWordOptionsGridLayout() {
    const grid = document.getElementById('word-options-grid');
    if (!grid) return;
    
    // Update the CSS grid template columns based on gridColumns setting
    grid.style.gridTemplateColumns = `repeat(${gridColumns}, 1fr)`;
    
    // Calculate font size for word options
    const baseFontSize = 16; // Base font size for word options
    const minFontSize = 12;  // Minimum font size
    const maxFontSize = 18;  // Maximum font size
    
    const fontSize = Math.max(minFontSize, Math.min(maxFontSize, baseFontSize * (6 / gridColumns)));
    grid.style.setProperty('--word-option-font-size', `${fontSize}px`);
    
    console.log(`Word options grid layout updated to ${gridColumns} columns with ${fontSize}px font size`);
}

// --- Update Word Predictions Grid Layout ---
function updateWordPredictionsGridLayout() {
    const grid = document.getElementById('word-predictions');
    if (!grid) return;
    
    // Update the CSS grid template columns based on gridColumns setting
    grid.style.gridTemplateColumns = `repeat(${gridColumns}, 1fr)`;
    
    // Calculate font size for predictions
    const baseFontSize = 14; // Base font size for predictions
    const minFontSize = 10;  // Minimum font size
    const maxFontSize = 16;  // Maximum font size
    
    const fontSize = Math.max(minFontSize, Math.min(maxFontSize, baseFontSize * (6 / gridColumns)));
    grid.style.setProperty('--prediction-font-size', `${fontSize}px`);
    
    console.log(`Word predictions grid layout updated to ${gridColumns} columns with ${fontSize}px font size`);
}

// --- Initialize Freestyle Page ---
async function initializeFreestylePage() {
    // Load settings first before setting up PIN modal
    await loadScanSettings();
    
    // Setup event listeners for control buttons (only the remaining ones)
    document.getElementById('speak-display-btn').addEventListener('click', speakDisplayText);
    document.getElementById('clear-display-btn').addEventListener('click', clearDisplayText);
    document.getElementById('go-back-btn').addEventListener('click', goBackToGrid);
    
    // Setup build space text area
    const buildSpaceTextarea = document.getElementById('build-space');
    buildSpaceTextarea.addEventListener('input', onBuildSpaceChange);
    
    // Setup spelling modal
    setupSpellingModal();
    
    // Setup choose word modal
    setupChooseWordModal();
    
    // Load initial word options and wait for completion before starting scanning
    await loadWordOptions();
    
    console.log('Freestyle page initialized');
}

// Function to start scanning after page is fully ready
function startInitialScanning() {
    console.log('startInitialScanning called');
    console.log('scanningPaused:', scanningPaused);
    console.log('currentScanningContext:', currentScanningContext);
    
    // Wait a bit longer and ensure buttons exist
    setTimeout(() => {
        const wordButtons = document.querySelectorAll('.word-option-btn');
        const controlButtons = document.querySelectorAll('#speak-display-btn, #go-back-btn, #clear-display-btn');
        console.log(`Found ${wordButtons.length} word buttons and ${controlButtons.length} control buttons`);
        
        if (wordButtons.length === 0) {
            console.warn('No word buttons found, retrying in 1 second...');
            setTimeout(startInitialScanning, 1000);
            return;
        }
        
        scanningPaused = false;
        startScanning();
        console.log('Initial scanning started with buttons available');
    }, 1000); // Increased delay to ensure buttons are rendered
}

// --- Build Space Management ---
function onBuildSpaceChange() {
    const buildSpaceTextarea = document.getElementById('build-space');
    currentBuildSpaceText = buildSpaceTextarea.value;
    
    // Debounced reload of word options when build space changes
    clearTimeout(window.buildSpaceDebounceTimer);
    window.buildSpaceDebounceTimer = setTimeout(() => {
        loadWordOptions();
    }, 1000); // Wait 1 second after user stops typing
}

function addWordToBuildSpace(word) {
    const buildSpaceTextarea = document.getElementById('build-space');
    if (currentBuildSpaceText.trim()) {
        currentBuildSpaceText += ' ' + word;
    } else {
        currentBuildSpaceText = word;
    }
    buildSpaceTextarea.value = currentBuildSpaceText;
    
    // Reload word options with new context
    loadWordOptions();
}

async function speakDisplayText() {
    if (!currentBuildSpaceText.trim()) {
        await announce("Nothing to speak", "system", false);
        return;
    }
    console.log('Auto Clean enabled? ', autoClean);
    // If Auto Clean is enabled, automatically clean up the text first
    if (autoClean) {
        console.log('Auto Clean enabled - cleaning text before speaking');
        await cleanupTextInternal(); // Use internal cleanup to avoid duplicate loading indicators
    }
    
    await announce(currentBuildSpaceText, "system", true);
    
    // Record to speech history (following gridpage.js pattern)
    recordToSpeechHistory(currentBuildSpaceText);
    
    // Pause scanning for the scanning interval duration, then reset to Go Back button
    if (scanningInterval) {
        stopScanning();
        
        setTimeout(() => {
            // Reset to Go Back button and resume scanning
            if (!scanningPaused && currentScanningContext === "main") {
                console.log('Resuming scanning after Speak Display');
                
                // Build the same button list as in startMainScanning() - exactly matching that logic
                let controlButtons = [];
                if (currentBuildSpaceText.trim()) {
                    controlButtons = Array.from(document.querySelectorAll('#speak-display-btn, #go-back-btn, #clear-display-btn'));
                }
                
                const wordButtons = Array.from(document.querySelectorAll('.word-option-btn'));
                const allButtons = [...controlButtons, ...wordButtons];
                
                console.log(`Total buttons found: ${allButtons.length}, Control buttons: ${controlButtons.length}`);
                
                // Find the index of the Go Back button - it should be index 1 (after Speak Display at index 0)
                const goBackIndex = allButtons.findIndex(btn => btn && btn.id === 'go-back-btn');
                console.log(`Go Back button found at index: ${goBackIndex}`);
                
                if (goBackIndex !== -1 && goBackIndex > 0) {
                    // Set to Go Back button index
                    currentButtonIndex = goBackIndex;
                    console.log(`✅ Reset scanning to Go Back button at index ${goBackIndex}`);
                } else {
                    // Fallback to first word button if Go Back not found or is at wrong position
                    currentButtonIndex = Math.max(1, controlButtons.length); // Skip Speak Display button
                    console.log(`⚠️ Go Back button issue, starting with button at index ${currentButtonIndex}`);
                }
                
                startScanning();
            }
        }, 1000); // Use fixed 1 second delay instead of defaultDelay to make it more predictable
    }
}

function clearDisplayText() {
    const buildSpaceTextarea = document.getElementById('build-space');
    currentBuildSpaceText = "";
    buildSpaceTextarea.value = "";
    
    // Reload word options
    loadWordOptions();
}

async function cleanupDisplayText() {
    if (!currentBuildSpaceText.trim()) {
        await announce("Nothing to clean up", "system", false);
        return;
    }
    
    if (isLLMProcessing) {
        await announce("Please wait, processing", "system", false);
        return;
    }
    
    try {
        isLLMProcessing = true;
        showLoadingIndicator(true);
        
        await cleanupTextInternal();
        
        // Announce the change
        await announce("Text cleaned up", "system", false);
    } catch (error) {
        console.error('Error cleaning up text:', error);
        await announce("Cleanup error", "system", false);
    } finally {
        isLLMProcessing = false;
        showLoadingIndicator(false);
    }
}

// Internal cleanup function without loading indicators (for auto-clean)
async function cleanupTextInternal() {
    const response = await authenticatedFetch('/api/freestyle/cleanup-text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            text_to_cleanup: currentBuildSpaceText
        })
    });
    
    if (response.ok) {
        const data = await response.json();
        const cleanedText = data.cleaned_text || currentBuildSpaceText;
        console.log("Original text:", currentBuildSpaceText);
        console.log("Cleaned text:", cleanedText);
        // Update the build space with cleaned text
        currentBuildSpaceText = cleanedText;
        const buildSpaceTextarea = document.getElementById('build-space');
        buildSpaceTextarea.value = currentBuildSpaceText;
        
        // Reload word options with new context
        loadWordOptions();
    } else {
        console.error('Failed to cleanup text:', response.statusText);
        throw new Error('Cleanup failed');
    }
}

function goBackToGrid() {
    // Navigate back to gridpage.html with the home page
    window.location.href = '/static/gridpage.html?page=home';
}

// --- Word Options Management ---
async function loadWordOptions() {
    if (isLLMProcessing) return;
    
    try {
        isLLMProcessing = true;
        showLoadingIndicator(true);
        
        const response = await authenticatedFetch('/api/freestyle/word-options', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                build_space_text: currentBuildSpaceText
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log(`Loaded word options: ${JSON.stringify(data.word_options)}`);
            currentWordOptions = data.word_options || [];
            renderWordOptionsGrid();
        } else {
            console.error('Failed to load word options:', response.statusText);
            // Show fallback options
            currentWordOptions = ["I", "want", "need", "can", "please", "thank you", "help", "yes", "no", "good"];
            renderWordOptionsGrid();
        }
    } catch (error) {
        console.error('Error loading word options:', error);
        currentWordOptions = ["I", "want", "need", "can", "please", "thank you", "help", "yes", "no", "good"];
        renderWordOptionsGrid();
    } finally {
        isLLMProcessing = false;
        showLoadingIndicator(false);
        
        // Restart scanning after new options are loaded and rendered
        if (currentScanningContext === "main" && !scanningInterval && !scanningPaused) {
            setTimeout(() => {
                if (!scanningInterval) { // Double check
                    startScanning();
                }
            }, 500);
        }
    }
}

function renderWordOptionsGrid() {
    const grid = document.getElementById('word-options-grid');
    grid.innerHTML = '';
    
    // Update grid layout to use current gridColumns setting
    updateWordOptionsGridLayout();
    
    currentWordOptions.forEach((word, index) => {
        const button = document.createElement('button');
        button.className = 'word-option-btn';
        button.textContent = word;
        button.setAttribute('data-index', index);
        button.addEventListener('click', () => handleWordOptionClick(word));
        grid.appendChild(button);
    });
    
    // Add Choose Word button (comes first)
    const chooseWordButton = document.createElement('button');
    chooseWordButton.className = 'word-option-btn choose-word-button';
    chooseWordButton.innerHTML = '<i class="fas fa-list"></i> Choose Word';
    chooseWordButton.id = 'choose-word-btn-lower';
    chooseWordButton.addEventListener('click', () => openChooseWordModal());
    grid.appendChild(chooseWordButton);
    
    // Add Spell button (comes second)
    const spellButton = document.createElement('button');
    spellButton.className = 'word-option-btn spell-button';
    spellButton.innerHTML = '<i class="fas fa-keyboard"></i> Spell';
    spellButton.id = 'spell-btn-lower';
    spellButton.addEventListener('click', () => openSpellingModal());
    grid.appendChild(spellButton);
    
    // Add "More Options" button
    const moreButton = document.createElement('button');
    moreButton.className = 'word-option-btn more-options-btn';
    moreButton.textContent = 'More Options';
    moreButton.addEventListener('click', () => loadMoreWordOptions());
    grid.appendChild(moreButton);
    
    console.log(`Rendered ${currentWordOptions.length} word options + Spell + Choose Word + More Options buttons`);
}

async function loadMoreWordOptions() {
    if (isLLMProcessing) return;
    
    try {
        isLLMProcessing = true;
        showLoadingIndicator(true);
        
        const response = await authenticatedFetch('/api/freestyle/word-options', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                build_space_text: currentBuildSpaceText,
                request_different_options: true // Signal to generate different options
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            currentWordOptions = data.word_options || [];
            renderWordOptionsGrid();
        } else {
            console.error('Failed to load more word options:', response.statusText);
        }
    } catch (error) {
        console.error('Error loading more word options:', error);
    } finally {
        isLLMProcessing = false;
        showLoadingIndicator(false);
        
        // Restart scanning after new options are loaded
        if (currentScanningContext === "main" && !scanningInterval && !scanningPaused) {
            setTimeout(() => {
                if (!scanningInterval) { // Double check
                    startScanning();
                }
            }, 500);
        }
    }
}

async function handleWordOptionClick(word) {
    // Announce the selected word
    await announce(word, "system", true);
    
    addWordToBuildSpace(word);
    
    // Stop scanning completely and restart only after word options are reloaded
    if (scanningInterval) {
        stopScanning();
    }
}

// --- Spelling Modal Management ---
function setupSpellingModal() {
    // Setup close modal listeners
    document.getElementById('cancel-spelling-btn').addEventListener('click', closeSpellingModal);
    document.getElementById('spelling-modal').addEventListener('click', (e) => {
        if (e.target.id === 'spelling-modal') {
            closeSpellingModal();
        }
    });
    
    // Setup word control buttons
    document.getElementById('add-word-btn').addEventListener('click', addCurrentWordToBuildSpace);
    document.getElementById('clear-word-btn').addEventListener('click', clearCurrentWord);
    document.getElementById('backspace-btn').addEventListener('click', backspaceCurrentWord);
    
    // Generate alphabet grid
    generateAlphabetGrid();
}


// Add this after the existing spelling modal setup
document.getElementById('current-word').addEventListener('input', async (e) => {
    const currentWord = e.target.value;
    
    // Update letter availability based on current word
    updateLetterAvailability(currentWord);
    
    const fullText = currentBuildSpaceText + ' ' + currentWord;
    if (currentWord.length > 0) {
        await getWordPredictionsForSpelling(fullText);
    } else {
        currentPredictions = [];
        renderWordPredictions();
    }
});

async function getWordPredictionsForSpelling(fullText) {
    if (isLLMProcessing) return;
    
    try {
        isLLMProcessing = true;
        
        // Extract the current word from the full text
        const currentWord = currentSpellingWord || "";
        
        const response = await authenticatedFetch('/api/freestyle/word-prediction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: currentBuildSpaceText || "", // Context from build space
                spelling_word: currentWord, // Current partial word
                predict_full_words: true // Flag to ensure complete words are returned
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            currentPredictions = data.predictions || [];
            renderWordPredictions();
        } else {
            console.error('Failed to get word predictions for spelling:', response.statusText);
            currentPredictions = [];
            renderWordPredictions();
        }
    } catch (error) {
        console.error('Error getting word predictions for spelling:', error);
        currentPredictions = [];
        renderWordPredictions();
    } finally {
        isLLMProcessing = false;
    }
}

function openSpellingModal() {
    isSpellingModalOpen = true;
    document.getElementById('spelling-modal').classList.remove('hidden');
    currentSpellingWord = "";
    document.getElementById('current-word').value = "";
    
    // COMPLETELY stop any current scanning
    stopScanning();
    scanningPaused = true; // Prevent auto-restart
    
    // Initialize smart letter filtering
    updateLetterAvailability("");
    
    // Clear predictions
    currentPredictions = [];
    renderWordPredictions();
    
    // Change context and start spell modal scanning
    currentScanningContext = "spelling-letters";
    
    // Start scanning for the spell modal after a brief delay
    setTimeout(() => {
        scanningPaused = false; // Re-enable scanning for spell modal
        startScanning();
    }, 800);
    
    console.log('Spelling modal opened, main scanning stopped');
}

function closeSpellingModal() {
    isSpellingModalOpen = false;
    document.getElementById('spelling-modal').classList.add('hidden');
    
    // Stop spell modal scanning completely
    stopScanning();
    scanningPaused = true; // Prevent auto-restart
    
    // Change context back to main
    currentScanningContext = "main";
    
    // Restart main scanning after a delay
    setTimeout(() => {
        scanningPaused = false; // Re-enable scanning
        startScanning();
    }, 800);
    
    console.log('Spelling modal closed, returning to main scanning');
}

function generateAlphabetGrid() {
    const grid = document.getElementById('alphabet-grid');
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    
    // Update grid layout to use current gridColumns setting
    updateAlphabetGridLayout();
    
    alphabet.forEach((letter, index) => {
        const button = document.createElement('button');
        button.className = 'letter-btn';
        button.textContent = letter;
        button.setAttribute('data-letter', letter);
        button.setAttribute('data-index', index);
        button.addEventListener('click', () => handleLetterClick(letter));
        grid.appendChild(button);
    });
}

async function handleLetterClick(letter) {
    currentSpellingWord += letter.toLowerCase();
    document.getElementById('current-word').value = currentSpellingWord;
    
    // Update letter availability immediately
    updateLetterAvailability(currentSpellingWord);
    
    // Get word predictions
    await getWordPredictions();
    
    // If scanning is active, restart with updated button list
    if (scanningInterval) {
        stopScanning();
        setTimeout(() => {
            if (!scanningPaused) {
                startScanning();
            }
        }, 400);
    }
}

async function getWordPredictions() {
    if (isLLMProcessing) return;
    
    try {
        isLLMProcessing = true;
        
        // Send spelling word and build space separately to ensure full word predictions
        const response = await authenticatedFetch('/api/freestyle/word-prediction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: currentBuildSpaceText || "", // Context from build space
                spelling_word: currentSpellingWord || "", // Current partial word
                predict_full_words: true // Flag to ensure complete words are returned
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            currentPredictions = data.predictions || [];
            renderWordPredictions();
        } else {
            console.error('Failed to get word predictions:', response.statusText);
            currentPredictions = [];
            renderWordPredictions();
        }
    } catch (error) {
        console.error('Error getting word predictions:', error);
        currentPredictions = [];
        renderWordPredictions();
    } finally {
        isLLMProcessing = false;
    }
}

function renderWordPredictions() {
    const grid = document.getElementById('word-predictions');
    grid.innerHTML = '';
    
    // Update grid layout to use current gridColumns setting
    updateWordPredictionsGridLayout();
    
    currentPredictions.forEach((word, index) => {
        const button = document.createElement('button');
        button.className = 'prediction-btn';
        button.textContent = word;
        button.setAttribute('data-index', index);
        button.addEventListener('click', () => handlePredictionClick(word));
        grid.appendChild(button);
    });
}

async function handlePredictionClick(word) {
    // Announce the selected word
    await announce(word, "system", true);
    
    // Immediately add the selected prediction to Build Space and close modal
    currentSpellingWord = word;
    document.getElementById('current-word').value = currentSpellingWord;
    
    // Add word to build space and close modal
    addWordToBuildSpace(currentSpellingWord);
    clearCurrentWord();
    closeSpellingModal();
}

async function addCurrentWordToBuildSpace() {
    if (currentSpellingWord.trim()) {
        // Announce the selected word
        await announce(currentSpellingWord, "system", true);
        
        addWordToBuildSpace(currentSpellingWord);
        clearCurrentWord();
        closeSpellingModal();
    }
}

function clearCurrentWord() {
    currentSpellingWord = "";
    document.getElementById('current-word').value = "";
    
    // Reset letter availability
    updateLetterAvailability("");
    
    currentPredictions = [];
    renderWordPredictions();
    
    // If scanning is active, restart to account for all letters being enabled again
    if (scanningInterval) {
        stopScanning();
        setTimeout(() => {
            if (!scanningPaused) {
                startScanning();
            }
        }, 400);
    }
}

function backspaceCurrentWord() {
    if (currentSpellingWord.length > 0) {
        currentSpellingWord = currentSpellingWord.slice(0, -1);
        document.getElementById('current-word').value = currentSpellingWord;
        
        // Update letter availability immediately
        updateLetterAvailability(currentSpellingWord);
        
        getWordPredictions();
        
        // If scanning is active, restart to account for newly enabled letters
        if (scanningInterval) {
            stopScanning();
            setTimeout(() => {
                if (!scanningPaused) {
                    startScanning();
                }
            }, 400);
        }
    }
}

// --- Choose Word Modal Management ---
function setupChooseWordModal() {
    // Setup event listeners
    document.getElementById('cancel-choose-word-btn').addEventListener('click', closeChooseWordModal);
    document.getElementById('back-to-categories-btn').addEventListener('click', showCategorySelection);
    document.getElementById('something-else-words-btn').addEventListener('click', generateDifferentWords);
    document.getElementById('go-back-from-words-btn').addEventListener('click', closeChooseWordModal);
    
    // Handle modal background click
    document.getElementById('choose-word-modal').addEventListener('click', (e) => {
        if (e.target.id === 'choose-word-modal') {
            closeChooseWordModal();
        }
    });
}

function openChooseWordModal() {
    console.log('Opening Choose Word modal');
    
    // Set modal state
    isChooseWordModalOpen = true;
    currentScanningContext = "choose-word-categories";
    
    // Reset modal state
    currentChooseWordCategory = "";
    currentCategoryWords = [];
    
    // Show modal
    document.getElementById('choose-word-modal').classList.remove('hidden');
    
    // Show category selection
    showCategorySelection();
    
    // Update scanning
    if (scanningInterval) {
        stopScanning();
        setTimeout(() => {
            if (!scanningPaused) {
                startScanning();
            }
        }, 300);
    }
}

function closeChooseWordModal() {
    console.log('Closing Choose Word modal');
    
    // Set modal state
    isChooseWordModalOpen = false;
    currentScanningContext = "main";
    
    // Reset state
    currentChooseWordCategory = "";
    currentCategoryWords = [];
    
    // Hide modal
    document.getElementById('choose-word-modal').classList.add('hidden');
    
    // Update scanning
    if (scanningInterval) {
        stopScanning();
        setTimeout(() => {
            if (!scanningPaused) {
                startScanning();
            }
        }, 300);
    }
}

function showCategorySelection() {
    console.log('Showing category selection');
    
    // Update scanning context
    currentScanningContext = "choose-word-categories";
    
    // Show category section, hide word options section
    document.getElementById('category-section').classList.remove('hidden');
    document.getElementById('word-options-section').classList.add('hidden');
    
    // Generate category buttons
    generateCategoryButtons();
    
    // Update scanning
    if (scanningInterval) {
        stopScanning();
        setTimeout(() => {
            if (!scanningPaused) {
                startScanning();
            }
        }, 300);
    }
}

function generateCategoryButtons() {
    const categoryGrid = document.getElementById('category-grid');
    
    // Define categories with additional suggestions
    const categories = [
        { name: "People", icon: "fas fa-users" },
        { name: "Places", icon: "fas fa-map-marker-alt" },
        { name: "Animals", icon: "fas fa-paw" },
        { name: "Around the House", icon: "fas fa-home" },
        { name: "In the Room", icon: "fas fa-couch" },
        { name: "General things", icon: "fas fa-cube" },
        { name: "Actions", icon: "fas fa-running" },
        { name: "Feelings & Emotions", icon: "fas fa-heart" },
        { name: "Questions & Comments", icon: "fas fa-question-circle" },
        { name: "Times and Dates", icon: "fas fa-calendar" },
        { name: "Activities & Hobbies", icon: "fas fa-gamepad" },
        { name: "Medical & Health", icon: "fas fa-heartbeat" },
        { name: "Food & Drinks", icon: "fas fa-utensils" },
        { name: "Colors & Descriptions", icon: "fas fa-palette" },
        { name: "Numbers & Quantities", icon: "fas fa-calculator" },
        { name: "School & Learning", icon: "fas fa-graduation-cap" },
        { name: "Transportation", icon: "fas fa-car" },
        { name: "Weather", icon: "fas fa-cloud-sun" },
        { name: "Technology", icon: "fas fa-laptop" },
        { name: "Sports & Games", icon: "fas fa-trophy" }
    ];
    
    // Clear existing categories
    categoryGrid.innerHTML = '';
    
    // Create category buttons
    categories.forEach((category, index) => {
        const button = document.createElement('button');
        button.className = 'freestyle-modal-btn category-btn';
        button.innerHTML = `<i class="${category.icon}"></i> ${category.name}`;
        button.addEventListener('click', () => selectCategory(category.name));
        categoryGrid.appendChild(button);
    });
}

async function selectCategory(categoryName) {
    console.log('Selected category:', categoryName);
    
    // Set current category
    currentChooseWordCategory = categoryName;
    
    // Update title
    document.getElementById('selected-category-title').textContent = `${categoryName}:`;
    
    // Show word options section, hide category section
    document.getElementById('category-section').classList.add('hidden');
    document.getElementById('word-options-section').classList.remove('hidden');
    
    // Update scanning context
    currentScanningContext = "choose-word-options";
    
    // Generate words for the category
    await generateCategoryWords(categoryName);
}

async function generateCategoryWords(categoryName, excludeWords = []) {
    if (isLLMProcessing) return;
    
    try {
        isLLMProcessing = true;
        showLoadingIndicator();
        
        // Get current build space content for context
        const buildSpaceContent = document.getElementById('build-space').value.trim();
        
        // Prepare the request
        const requestData = {
            category: categoryName,
            build_space_content: buildSpaceContent,
            exclude_words: excludeWords
        };
        
        console.log('Generating category words:', requestData);
        
        const response = await authenticatedFetch('/api/freestyle/category-words', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Category words response:', data);
        
        if (data.words && Array.isArray(data.words)) {
            currentCategoryWords = data.words;
            displayCategoryWords();
        } else {
            console.error('Invalid category words response format');
            announceText('Error generating word options. Please try again.');
        }
        
    } catch (error) {
        console.error('Error generating category words:', error);
        announceText('Error generating word options. Please try again.');
    } finally {
        isLLMProcessing = false;
        showLoadingIndicator(false);
    }
}

function displayCategoryWords() {
    const wordOptionsGrid = document.getElementById('category-word-options-grid');
    
    // Clear existing words
    wordOptionsGrid.innerHTML = '';
    
    // Add word buttons
    currentCategoryWords.forEach((word) => {
        const button = document.createElement('button');
        button.className = 'freestyle-modal-btn word-option-btn';
        button.textContent = word;
        button.addEventListener('click', () => selectCategoryWord(word));
        wordOptionsGrid.appendChild(button);
    });
    
    // Update scanning
    if (scanningInterval) {
        stopScanning();
        setTimeout(() => {
            if (!scanningPaused) {
                startScanning();
            }
        }, 300);
    }
}

async function generateDifferentWords() {
    console.log('Generating different words for category:', currentChooseWordCategory);
    
    // Generate new words excluding current ones
    await generateCategoryWords(currentChooseWordCategory, currentCategoryWords);
}

async function selectCategoryWord(word) {
    console.log('Selected word:', word);
    
    // Announce the selected word
    await announce(word, "system", true);
    
    // Add word to build space
    addWordToBuildSpace(word);
    
    // Close modal
    closeChooseWordModal();
    
    // Follow same flow as freestyle options - speak display
    setTimeout(() => {
        speakDisplayText();
    }, 500);
}

// --- Speech History Management (Following gridpage.js pattern) ---
function recordToSpeechHistory(textToRecord) {
    if (!currentAacUserId || !textToRecord.trim()) {
        return;
    }
    
    try {
        // Get existing history from localStorage
        let history = (localStorage.getItem(SPEECH_HISTORY_LOCAL_STORAGE_KEY(currentAacUserId)) || '').split('\n').filter(Boolean);
        
        // Add new text to the beginning of the array
        history.unshift(textToRecord.trim());
        
        // Limit to 20 entries (same as gridpage.js)
        if (history.length > 20) { 
            history = history.slice(0, 20); 
        }
        
        // Save back to localStorage
        localStorage.setItem(SPEECH_HISTORY_LOCAL_STORAGE_KEY(currentAacUserId), history.join('\n'));
        
        console.log('Speech history recorded:', textToRecord);
    } catch (error) {
        console.error('Error recording speech history:', error);
    }
}

// --- Auditory Scanning (Similar to gridpage.js but adapted for freestyle) ---
function startScanning() {
    if (scanningPaused) {
        console.log('Scanning is paused, not starting');
        return;
    }
    
    if (scanningInterval) {
        stopScanning();
    }
    
    scanCycleCount = 0;
    isPausedFromScanLimit = false;
    
    if (currentScanningContext === "main") {
        startMainScanning();
    } else if (currentScanningContext === "spelling-letters") {
        startSpellingLettersScanning();
    } else if (currentScanningContext === "spelling-predictions") {
        startSpellingPredictionsScanning();
    } else if (currentScanningContext === "choose-word-categories") {
        startChooseWordCategoriesScanning();
    } else if (currentScanningContext === "choose-word-options") {
        startChooseWordOptionsScanning();
    }
}

function startMainScanning() {
    console.log('Starting main scanning');
    
    // Context-aware scanning: control buttons first, then word options
    // Skip Speak Display, Go Back, and Clear Display buttons if Build Space is empty
    let controlButtons = [];
    if (currentBuildSpaceText.trim()) {
        controlButtons = Array.from(document.querySelectorAll('#speak-display-btn, #go-back-btn, #clear-display-btn'));
    }
    
    const wordButtons = Array.from(document.querySelectorAll('.word-option-btn'));
    const allButtons = [...controlButtons, ...wordButtons];
    
    if (allButtons.length === 0) {
        console.log('No buttons found for main scanning');
        return;
    }
    
    console.log(`Found ${allButtons.length} buttons for main scanning (Build space ${currentBuildSpaceText.trim() ? 'has content' : 'is empty'})`);
    currentButtonIndex = 0;
    
    const scanNext = async () => {
        // Remove highlight from previous button
        if (currentlyScannedButton) {
            currentlyScannedButton.classList.remove('scanning-highlight');
        }
        
        // Check scan limit
        if (scanLoopLimit > 0 && scanCycleCount >= scanLoopLimit) {
            stopScanning();
            isPausedFromScanLimit = true;
            return;
        }
        
        // Get current button
        const button = allButtons[currentButtonIndex];
        if (button) {
            currentlyScannedButton = button;
            speakAndHighlight(button);
        }
        
        // Move to next button
        currentButtonIndex++;
        if (currentButtonIndex >= allButtons.length) {
            currentButtonIndex = 0;
            scanCycleCount++;
        }
    };
    
    scanNext(); // Start immediately
    scanningInterval = setInterval(scanNext, defaultDelay);
}

function startSpellingLettersScanning() {
    console.log('Starting spell letters scanning');
    
    const scanNext = async () => {
        // Get fresh button lists each time to account for disabled letters and current word content
        // Skip Add Word, Clear, and Backspace buttons if Current Word is empty
        let controlButtonSelectors = '#cancel-spelling-btn';
        if (currentSpellingWord.trim()) {
            controlButtonSelectors = '#add-word-btn, #clear-word-btn, #backspace-btn, #cancel-spelling-btn';
        }
        
        const controlButtons = document.querySelectorAll(controlButtonSelectors);
        const predictionButtons = document.querySelectorAll('.prediction-btn');
        const letterButtons = document.querySelectorAll('.letter-btn:not(.disabled-letter):not([disabled])'); // Skip disabled letters
        const allButtons = [...controlButtons, ...predictionButtons, ...letterButtons];
        
        if (allButtons.length === 0) {
            console.log('No available buttons for spell scanning');
            return;
        }
        
        // Remove highlight from previous button
        if (currentlyScannedButton) {
            currentlyScannedButton.classList.remove('scanning-highlight');
        }
        
        // Check scan limit
        if (scanLoopLimit > 0 && scanCycleCount >= scanLoopLimit) {
            stopScanning();
            isPausedFromScanLimit = true;
            return;
        }
        
        // Reset index if we've gone beyond the updated list
        if (currentButtonIndex >= allButtons.length) {
            currentButtonIndex = 0;
            scanCycleCount++;
        }
        
        // Get current button
        const button = allButtons[currentButtonIndex];
        if (button && !button.disabled && !button.classList.contains('disabled-letter')) {
            currentlyScannedButton = button;
            speakAndHighlight(button);
        }
        
        // Move to next button
        currentButtonIndex++;
        if (currentButtonIndex >= allButtons.length) {
            currentButtonIndex = 0;
            scanCycleCount++;
        }
    };
    
    currentButtonIndex = 0;
    scanNext(); // Start immediately
    scanningInterval = setInterval(scanNext, defaultDelay);
}

function startSpellingPredictionsScanning() {
    const buttons = document.querySelectorAll('.prediction-btn');
    if (buttons.length === 0) return;
    
    currentButtonIndex = 0;
    
    const scanNext = () => {
        // Remove highlight from previous button
        if (currentlyScannedButton) {
            currentlyScannedButton.classList.remove('scanning-highlight');
        }
        
        // Check scan limit
        if (scanLoopLimit > 0 && scanCycleCount >= scanLoopLimit) {
            stopScanning();
            isPausedFromScanLimit = true;
            return;
        }
        
        // Get current button
        const button = buttons[currentButtonIndex];
        if (button) {
            currentlyScannedButton = button;
            speakAndHighlight(button);
        }
        
        // Move to next button
        currentButtonIndex++;
        if (currentButtonIndex >= buttons.length) {
            currentButtonIndex = 0;
            scanCycleCount++;
        }
    };
    
    scanNext(); // Start immediately
    scanningInterval = setInterval(scanNext, defaultDelay);
}

function startChooseWordCategoriesScanning() {
    // Only scan buttons within the choose word modal
    const modal = document.getElementById('choose-word-modal');
    const categoryButtons = modal.querySelectorAll('.category-btn');
    const controlButtons = modal.querySelectorAll('#cancel-choose-word-btn');
    const allButtons = [...categoryButtons, ...controlButtons];
    if (allButtons.length === 0) return;
    const buttons = allButtons;
    
    currentButtonIndex = 0;
    
    const scanNext = () => {
        // Remove highlight from previous button
        if (currentlyScannedButton) {
            currentlyScannedButton.classList.remove('scanned');
        }
        
        // Check scan limit
        if (scanLoopLimit > 0 && scanCycleCount >= scanLoopLimit) {
            stopScanning();
            isPausedFromScanLimit = true;
            return;
        }
        
        // Get current button
        const button = buttons[currentButtonIndex];
        if (button) {
            currentlyScannedButton = button;
            speakAndHighlight(button);
        }
        
        // Move to next button
        currentButtonIndex++;
        if (currentButtonIndex >= buttons.length) {
            currentButtonIndex = 0;
            scanCycleCount++;
        }
    };
    
    scanNext(); // Start immediately
    scanningInterval = setInterval(scanNext, defaultDelay);
}

function startChooseWordOptionsScanning() {
    // Only scan buttons within the choose word modal
    const modal = document.getElementById('choose-word-modal');
    const wordButtons = modal.querySelectorAll('.word-option-btn');
    const controlButtons = modal.querySelectorAll('#back-to-categories-btn, #something-else-words-btn, #go-back-from-words-btn');
    const allButtons = [...wordButtons, ...controlButtons];
    if (allButtons.length === 0) return;
    const buttons = allButtons;
    
    currentButtonIndex = 0;
    
    const scanNext = () => {
        // Remove highlight from previous button
        if (currentlyScannedButton) {
            currentlyScannedButton.classList.remove('scanned');
        }
        
        // Check scan limit
        if (scanLoopLimit > 0 && scanCycleCount >= scanLoopLimit) {
            stopScanning();
            isPausedFromScanLimit = true;
            return;
        }
        
        // Get current button
        const button = buttons[currentButtonIndex];
        if (button) {
            currentlyScannedButton = button;
            speakAndHighlight(button);
        }
        
        // Move to next button
        currentButtonIndex++;
        if (currentButtonIndex >= buttons.length) {
            currentButtonIndex = 0;
            scanCycleCount++;
        }
    };
    
    scanNext(); // Start immediately
    scanningInterval = setInterval(scanNext, defaultDelay);
}

function stopScanning() {
    if (scanningInterval) {
        clearInterval(scanningInterval);
        scanningInterval = null;
        console.log('Scanning stopped');
    }
    
    // Remove highlight from current button
    if (currentlyScannedButton) {
        currentlyScannedButton.classList.remove('scanning-highlight');
        currentlyScannedButton = null;
    }
    
    currentButtonIndex = -1;
    window.speechSynthesis.cancel(); // Cancel any ongoing speech
}

function speakAndHighlight(button) {
    // Remove scanning class from all buttons
    document.querySelectorAll('.scanning-highlight').forEach(btn => {
        btn.classList.remove('scanning-highlight');
    });
    
    // Add scanning class to current button
    button.classList.add('scanning-highlight');
    
    try {
        let textToSpeak = button.textContent;
        
        // Special case: if this is the Speak Display button, use Build Space text instead
        if (button.id === 'speak-display-btn' && currentBuildSpaceText.trim()) {
            textToSpeak = currentBuildSpaceText.trim();
        }
        
        // Special case: if this is the Add Word button, use Current Word text instead
        if (button.id === 'add-word-btn' && currentSpellingWord.trim()) {
            textToSpeak = currentSpellingWord.trim();
        }
        
        // Use speech synthesis for scanning (personal speaker, not announced)
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    } catch (e) {
        console.error("Speech synthesis error:", e);
    }
}

function resumeScanning() {
    if (isPausedFromScanLimit) {
        scanCycleCount = 0;
        isPausedFromScanLimit = false;
        startScanning();
    }
}

// --- Input Handling (Same as gridpage.js) ---
function setupKeyboardListener() {
    document.addEventListener('keydown', (event) => {
        if (event.code === 'Space') {
            event.preventDefault();
            handleSpacebarPress();
        }
    });
}

function handleSpacebarPress() {
    if (currentlyScannedButton) {
        // Simulate click on the currently scanned button
        currentlyScannedButton.click();
    } else if (!scanningInterval && !isPausedFromScanLimit) {
        // Start scanning if not active
        startScanning();
    } else if (isPausedFromScanLimit) {
        // Resume scanning if paused
        resumeScanning();
    }
}

function setupGamepadListeners() {
    window.addEventListener('gamepadconnected', (e) => {
        console.log('Gamepad connected:', e.gamepad);
        gamepadIndex = e.gamepad.index;
        startGamepadPolling();
    });

    window.addEventListener('gamepaddisconnected', (e) => {
        console.log('Gamepad disconnected:', e.gamepad);
        if (gamepadIndex === e.gamepad.index) {
            gamepadIndex = null;
            stopGamepadPolling();
        }
    });
}

function startGamepadPolling() {
    if (gamepadPollInterval) return;
    
    const pollGamepad = () => {
        if (gamepadIndex === null) return;
        
        const gamepad = navigator.getGamepads()[gamepadIndex];
        if (gamepad) {
            const currentTime = Date.now();
            if (currentTime - lastGamepadInputTime > clickDebounceDelay) {
                if (gamepad.buttons[0] && gamepad.buttons[0].pressed) {
                    lastGamepadInputTime = currentTime;
                    handleSpacebarPress();
                }
            }
        }
        
        gamepadPollInterval = requestAnimationFrame(pollGamepad);
    };
    
    gamepadPollInterval = requestAnimationFrame(pollGamepad);
}

function stopGamepadPolling() {
    if (gamepadPollInterval) {
        cancelAnimationFrame(gamepadPollInterval);
        gamepadPollInterval = null;
    }
}

// --- Audio Functions (Similar to gridpage.js) ---
function base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

async function playAudioToDevice(audioDataBuffer, sampleRate, announcementType) {
    try {
        if (!window.AudioContext && !window.webkitAudioContext) {
            console.error('Web Audio API not supported');
            return;
        }

        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const audioContext = new AudioContext();

        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        const audioBuffer = await audioContext.decodeAudioData(audioDataBuffer);
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();

        return new Promise((resolve) => {
            source.onended = () => {
                audioContext.close();
                resolve();
            };
        });
    } catch (error) {
        console.error('Error playing audio:', error);
    }
}

async function processAnnouncementQueue() {
    if (isAnnouncingNow || announcementQueue.length === 0) {
        return;
    }

    isAnnouncingNow = true;

    while (announcementQueue.length > 0) {
        const announcement = announcementQueue.shift();
        const { textToAnnounce, announcementType, recordHistory } = announcement;

        // Show splash screen if enabled
        if (typeof showSplashScreen === 'function') {
            showSplashScreen(textToAnnounce);
        }

        try {
            const routingTarget = announcementType === "personal" ? "personal" : "system";
            
            const response = await authenticatedFetch('/play-audio', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: textToAnnounce,
                    routing_target: routingTarget
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.audio_data) {
                    const audioBuffer = base64ToArrayBuffer(data.audio_data);
                    await playAudioToDevice(audioBuffer, data.sample_rate || 24000, announcementType);
                }
            } else {
                console.error('TTS request failed:', response.statusText);
            }

            if (recordHistory && announcementType === "personal") {
                await recordChatHistory(textToAnnounce, null);
            }

        } catch (error) {
            console.error('Error in announcement processing:', error);
        }
    }

    isAnnouncingNow = false;
}

async function announce(textToAnnounce, announcementType = "system", recordHistory = true) {
    if (!textToAnnounce || textToAnnounce.trim() === "") {
        return;
    }

    announcementQueue.push({
        textToAnnounce: textToAnnounce.trim(),
        announcementType,
        recordHistory
    });

    processAnnouncementQueue();
}

async function recordChatHistory(question, response) {
    try {
        await authenticatedFetch('/record_chat_history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question || "",
                response: response || ""
            })
        });
    } catch (error) {
        console.error('Failed to record chat history:', error);
    }
}

function tryResumeAudioContext() {
    if (audioContextResumeAttempted) return;
    audioContextResumeAttempted = true;
    
    if (window.AudioContext || window.webkitAudioContext) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const tempContext = new AudioContext();
        if (tempContext.state === 'suspended') {
            tempContext.resume().then(() => {
                tempContext.close();
                console.log('AudioContext resumed successfully');
            }).catch(err => {
                console.error('Failed to resume AudioContext:', err);
            });
        } else {
            tempContext.close();
        }
    }
}

// --- Loading Indicator ---
function showLoadingIndicator(show) {
    const indicator = document.getElementById('loading-indicator');
    if (show) {
        indicator.style.display = 'flex';
    } else {
        indicator.style.display = 'none';
    }
}

// --- PIN Modal Setup (Same as gridpage.js) ---
function setupPinModal() {
    // --- PIN Protection for Admin Toolbar ---
    const lockButton = document.getElementById('lock-icon');
    const adminIcons = document.getElementById('admin-icons');
    const pinModal = document.getElementById('pin-modal');
    const pinInput = document.getElementById('pin-input');
    const pinSubmitButton = document.getElementById('pin-submit');
    const pinCancelButton = document.getElementById('pin-cancel');
    const pinError = document.getElementById('pin-error');

    // Function to show PIN modal
    function showPinModal() {
        if (pinModal) {
            pinModal.classList.remove('hidden');
            if (pinInput) {
                pinInput.value = '';
                pinInput.focus();
            }
            if (pinError) {
                pinError.classList.add('hidden');
            }
        }
    }

    // Function to hide PIN modal
    function hidePinModal() {
        if (pinModal) {
            pinModal.classList.add('hidden');
        }
        if (pinInput) {
            pinInput.value = '';
        }
        if (pinError) {
            pinError.classList.add('hidden');
        }
    }

    // Function to validate PIN with backend
    async function validatePin(pin) {
        try {
            const response = await authenticatedFetch('/api/account/toolbar-pin', {
                method: 'GET'
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.pin === pin;
            }
        } catch (error) {
            console.error('Error validating PIN:', error);
        }
        return false;
    }

    // Function to unlock admin toolbar
    function unlockToolbar() {
        if (adminIcons) {
            adminIcons.classList.remove('hidden');
        }
        if (lockButton) {
            lockButton.style.display = 'none';
        }
        hidePinModal();
    }

    // Function to lock admin toolbar
    function lockToolbar() {
        if (adminIcons) {
            adminIcons.classList.add('hidden');
        }
        if (lockButton) {
            lockButton.style.display = 'block';
        }
    }

    // Event listener for lock button
    if (lockButton) {
        lockButton.addEventListener('click', showPinModal);
    }

    // Event listener for lock toolbar button (locks the toolbar back)
    const lockToolbarButton = document.getElementById('lock-toolbar-button');
    if (lockToolbarButton) {
        lockToolbarButton.addEventListener('click', lockToolbar);
    }

    // Event listener for back to grid admin button
    const backToGridAdmin = document.getElementById('back-to-grid-admin');
    if (backToGridAdmin) {
        backToGridAdmin.addEventListener('click', () => {
            window.location.href = '/static/gridpage.html?page=home';
        });
    }

    // Event listener for switch user button
    const switchUserButton = document.getElementById('switch-user-button');
    if (switchUserButton) {
        switchUserButton.addEventListener('click', () => {
            console.log("Switching user profile. Clearing session and redirecting to auth page for profile selection.");
            // Only set flag to prevent auto-proceed with default user - keep user authenticated
            localStorage.setItem('bravoSkipDefaultUser', 'true');
            console.log('Set bravoSkipDefaultUser flag for profile selection');
            sessionStorage.clear();
            
            // Small delay to ensure localStorage is written before navigation
            setTimeout(() => {
                window.location.href = '/static/auth.html';
            }, 100);
        });
    }

    // Event listener for logout button
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            console.log("Logging out. Clearing session and redirecting to auth page for login.");
            // Set both flags to prevent automatic re-login and auto-profile selection
            localStorage.setItem('bravoIntentionalLogout', 'true');
            localStorage.setItem('bravoSkipDefaultUser', 'true');
            console.log('Set bravoIntentionalLogout and bravoSkipDefaultUser flags');
            sessionStorage.clear();
            
            // Small delay to ensure localStorage is written before navigation
            setTimeout(() => {
                window.location.href = '/static/auth.html';
            }, 100);
        });
    }

    // Event listener for PIN submit
    if (pinSubmitButton) {
        pinSubmitButton.addEventListener('click', async () => {
            const pin = pinInput.value;
            if (pin.length >= 3 && pin.length <= 10) {
                const isValid = await validatePin(pin);
                if (isValid) {
                    unlockToolbar();
                } else {
                    if (pinError) {
                        pinError.textContent = 'Invalid PIN. Please try again.';
                        pinError.classList.remove('hidden');
                    }
                    if (pinInput) {
                        pinInput.value = '';
                        pinInput.focus();
                    }
                }
            } else {
                if (pinError) {
                    pinError.textContent = 'PIN must be 3-10 characters.';
                    pinError.classList.remove('hidden');
                }
            }
        });
    }

    // Event listener for PIN cancel
    if (pinCancelButton) {
        pinCancelButton.addEventListener('click', hidePinModal);
    }

    // Event listener for Enter key in PIN input
    if (pinInput) {
        pinInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (pinSubmitButton) {
                    pinSubmitButton.click();
                }
            }
        });
    }

    // Event listener for Escape key to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && pinModal && !pinModal.classList.contains('hidden')) {
            hidePinModal();
        }
    });

    // Initialize toolbar state on page load
    lockToolbar();
}

// --- Smart Letter Filtering ---
function getValidLetters(currentWord) {
    console.log(`DEBUG: getValidLetters called with: "${currentWord}"`);
    
    if (!currentWord || currentWord.length === 0) {
        console.log(`DEBUG: Empty word, returning all letters`);
        return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    }
    
    const lastChar = currentWord.slice(-1).toUpperCase();
    const lastTwoChars = currentWord.slice(-2).toUpperCase();
    const wordSoFar = currentWord.toUpperCase();
    
    console.log(`DEBUG: Last char: "${lastChar}", Last two chars: "${lastTwoChars}", Word so far: "${wordSoFar}"`);
    
    // Define likely letter combinations based on common English patterns
    const likelyAfter = {
        // Single letters - what commonly follows each letter
        'A': ['B', 'C', 'D', 'F', 'G', 'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'Y'],
        'B': ['A', 'E', 'I', 'L', 'O', 'R', 'U', 'Y'], // BA, BE, BI, BL, BO, BR, BU, BY
        'C': ['A', 'E', 'H', 'I', 'L', 'O', 'R', 'U'], // CA, CE, CH, CI, CL, CO, CR, CU
        'D': ['A', 'E', 'I', 'O', 'R', 'U', 'Y'], // DA, DE, DI, DO, DR, DU, DY
        'E': ['A', 'D', 'L', 'M', 'N', 'R', 'S', 'T', 'V', 'W', 'X'], // EA, ED, EL, EM, EN, ER, ES, ET, EV, EW, EX
        'F': ['A', 'E', 'I', 'L', 'O', 'R', 'U'], // FA, FE, FI, FL, FO, FR, FU
        'G': ['A', 'E', 'I', 'L', 'O', 'R', 'U'], // GA, GE, GI, GL, GO, GR, GU
        'H': ['A', 'E', 'I', 'O', 'U', 'Y'], // HA, HE, HI, HO, HU, HY
        'I': ['C', 'D', 'F', 'G', 'L', 'M', 'N', 'R', 'S', 'T'], // IC, ID, IF, IG, IL, IM, IN, IR, IS, IT
        'J': ['A', 'E', 'O', 'U'], // JA, JE, JO, JU
        'K': ['A', 'E', 'I', 'N'], // KA, KE, KI, KN
        'L': ['A', 'E', 'I', 'O', 'U', 'Y'], // LA, LE, LI, LO, LU, LY
        'M': ['A', 'E', 'I', 'O', 'U', 'Y'], // MA, ME, MI, MO, MU, MY
        'N': ['A', 'C', 'D', 'E', 'G', 'I', 'K', 'O', 'S', 'T', 'U', 'Y', 'Z'], // NA, NC, ND, NE, NG, NI, NK, NO, NS, NT, NU, NY, NZ
        'O': ['B', 'C', 'D', 'F', 'G', 'K', 'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W'], // OB, OC, OD, OF, OG, OK, OL, OM, ON, OP, OR, OS, OT, OV, OW
        'P': ['A', 'E', 'I', 'L', 'O', 'R', 'U'], // PA, PE, PI, PL, PO, PR, PU
        'Q': ['U'], // QU (almost always)
        'R': ['A', 'E', 'I', 'O', 'U', 'Y'], // RA, RE, RI, RO, RU, RY
        'S': ['A', 'C', 'E', 'H', 'I', 'K', 'L', 'M', 'N', 'O', 'P', 'T', 'U', 'W'], // SA, SC, SE, SH, SI, SK, SL, SM, SN, SO, SP, ST, SU, SW
        'T': ['A', 'E', 'H', 'I', 'O', 'R', 'U', 'W'], // TA, TE, TH, TI, TO, TR, TU, TW
        'U': ['B', 'C', 'G', 'L', 'M', 'N', 'P', 'R', 'S', 'T'], // UB, UC, UG, UL, UM, UN, UP, UR, US, UT
        'V': ['A', 'E', 'I', 'O'], // VA, VE, VI, VO
        'W': ['A', 'E', 'H', 'I', 'O'], // WA, WE, WH, WI, WO
        'X': ['A', 'E', 'I'], // XA, XE, XI (rare)
        'Y': ['A', 'E', 'O', 'U'], // YA, YE, YO, YU
        'Z': ['A', 'E', 'I', 'O'] // ZA, ZE, ZI, ZO
    };
    
    // Two-letter patterns - what commonly follows specific two-letter combinations
    const likelyAfterTwoLetters = {
        'TH': ['A', 'E', 'I', 'O', 'R'], // THE, THI, THO, THR
        'CH': ['A', 'E', 'I', 'O', 'U'], // CHA, CHE, CHI, CHO, CHU
        'SH': ['A', 'E', 'I', 'O', 'U'], // SHA, SHE, SHI, SHO, SHU
        'WH': ['A', 'E', 'I', 'O', 'U'], // WHA, WHE, WHI, WHO, WHU
        'PH': ['A', 'E', 'I', 'O', 'U'], // PHA, PHE, PHI, PHO, PHU
        'ST': ['A', 'E', 'I', 'O', 'R', 'U'], // STA, STE, STI, STO, STR, STU
        'SP': ['A', 'E', 'I', 'O', 'R'], // SPA, SPE, SPI, SPO, SPR
        'SC': ['A', 'E', 'I', 'O', 'R'], // SCA, SCE, SCI, SCO, SCR
        'FL': ['A', 'E', 'I', 'O', 'U'], // FLA, FLE, FLI, FLO, FLU
        'BL': ['A', 'E', 'I', 'O', 'U'], // BLA, BLE, BLI, BLO, BLU
        'CL': ['A', 'E', 'I', 'O', 'U'], // CLA, CLE, CLI, CLO, CLU
        'GL': ['A', 'E', 'I', 'O', 'U'], // GLA, GLE, GLI, GLO, GLU
        'PL': ['A', 'E', 'I', 'O', 'U'], // PLA, PLE, PLI, PLO, PLU
        'BR': ['A', 'E', 'I', 'O', 'U'], // BRA, BRE, BRI, BRO, BRU
        'CR': ['A', 'E', 'I', 'O', 'U'], // CRA, CRE, CRI, CRO, CRU
        'DR': ['A', 'E', 'I', 'O', 'U'], // DRA, DRE, DRI, DRO, DRU
        'FR': ['A', 'E', 'I', 'O', 'U'], // FRA, FRE, FRI, FRO, FRU
        'GR': ['A', 'E', 'I', 'O', 'U'], // GRA, GRE, GRI, GRO, GRU
        'PR': ['A', 'E', 'I', 'O', 'U'], // PRA, PRE, PRI, PRO, PRU
        'TR': ['A', 'E', 'I', 'O', 'U'], // TRA, TRE, TRI, TRO, TRU
        'ON': ['A', 'C', 'D', 'E', 'G', 'K', 'S', 'T', 'Y', 'Z'], // ONA, ONC, OND, ONE, ONG, ONK, ONS, ONT, ONY, ONZ - for words like "bronze", "bronco"
        'RO': ['A', 'B', 'C', 'D', 'E', 'G', 'L', 'M', 'N', 'O', 'P', 'S', 'T', 'U', 'W'], // Common RO combinations
        'RN': ['A', 'E', 'I', 'O'], // RNA, RNE, RNI, RNO - for words ending in -orn, -urn
    };
    
    let validLetters = [];
    
    // For longer words (4+ letters), be more permissive to allow complex combinations
    if (currentWord.length >= 4) {
        // For longer words, use a combination approach:
        // 1. Check for specific three/four letter patterns
        const lastThreeChars = currentWord.slice(-3).toUpperCase();
        const lastFourChars = currentWord.slice(-4).toUpperCase();
        
        // Specific patterns for common word endings/structures
        const longerPatterns = {
            'RON': ['C', 'G', 'T', 'Y', 'Z'], // bronco, strong, front, sony, bronze
            'ION': ['A', 'E', 'S'], // iona, ione, ions
            'ING': ['A', 'E', 'L', 'S', 'T'], // inga, inge, ingl, ings, ingt
            'ING': ['E', 'L', 'S'], // inge, ingl, ings
            'URN': ['A', 'E', 'I', 'S'], // urna, urne, urni, urns
            'ORN': ['E', 'I', 'S'], // orne, orni, orns
        };
        
        if (longerPatterns[lastThreeChars]) {
            validLetters = longerPatterns[lastThreeChars];
            console.log(`DEBUG: Using three-letter pattern "${lastThreeChars}": ${validLetters.length} letters`);
        }
        // If no specific pattern found for longer words, be more permissive
        else {
            // Use two-letter pattern if available, but expand it
            if (likelyAfterTwoLetters[lastTwoChars]) {
                validLetters = likelyAfterTwoLetters[lastTwoChars];
                // Add common consonants for longer words
                const additionalConsonants = ['C', 'D', 'G', 'K', 'S', 'T', 'W', 'Y', 'Z'];
                additionalConsonants.forEach(letter => {
                    if (!validLetters.includes(letter)) {
                        validLetters.push(letter);
                    }
                });
                console.log(`DEBUG: Using expanded two-letter pattern "${lastTwoChars}": ${validLetters.length} letters`);
            }
            // Fall back to single letter with expansion
            else if (likelyAfter[lastChar]) {
                validLetters = likelyAfter[lastChar];
                // For longer words, add more consonants that commonly appear
                const extraConsonants = ['C', 'D', 'G', 'K', 'S', 'T', 'W', 'Z'];
                extraConsonants.forEach(letter => {
                    if (!validLetters.includes(letter)) {
                        validLetters.push(letter);
                    }
                });
                console.log(`DEBUG: Using expanded single letter pattern "${lastChar}": ${validLetters.length} letters`);
            }
            // Ultimate fallback for long words - allow most common letters
            else {
                validLetters = 'ABCDEFGHIKLMNOPRSTUVWYZ'.split(''); // Exclude less common J, Q, X
                console.log(`DEBUG: Using permissive pattern for long word: ${validLetters.length} letters`);
            }
        }
    }
    // For shorter words (2-3 letters), use existing logic but be slightly more permissive
    else if (currentWord.length >= 2 && likelyAfterTwoLetters[lastTwoChars]) {
        validLetters = likelyAfterTwoLetters[lastTwoChars];
        console.log(`DEBUG: Using two-letter pattern "${lastTwoChars}": ${validLetters.length} letters`);
    }
    // Otherwise use single letter pattern
    else if (likelyAfter[lastChar]) {
        validLetters = likelyAfter[lastChar];
        console.log(`DEBUG: Using single letter pattern "${lastChar}": ${validLetters.length} letters`);
    }
    // Fallback to all letters if no pattern found
    else {
        validLetters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
        console.log(`DEBUG: No pattern found, allowing all letters: ${validLetters.length} letters`);
    }
    
    console.log(`DEBUG: Final valid letters for "${currentWord}":`, validLetters);
    return validLetters;
}

function updateLetterAvailability(currentWord) {
    const validLetters = getValidLetters(currentWord);
    const letterButtons = document.querySelectorAll('.letter-btn');
    
    console.log(`DEBUG: updateLetterAvailability called with word: "${currentWord}"`);
    console.log(`DEBUG: Valid letters calculated:`, validLetters);
    console.log(`DEBUG: Found ${letterButtons.length} letter buttons`);
    
    letterButtons.forEach(button => {
        const letter = button.textContent.toUpperCase();
        if (validLetters.includes(letter)) {
            button.classList.remove('disabled-letter');
            button.disabled = false;
            console.log(`DEBUG: Enabled letter: ${letter}`);
        } else {
            button.classList.add('disabled-letter');
            button.disabled = true;
            console.log(`DEBUG: Disabled letter: ${letter}`);
        }
    });
    
    console.log(`DEBUG: After update, disabled buttons:`, 
        document.querySelectorAll('.letter-btn.disabled-letter').length);
}

// --- Cleanup on page unload ---
window.addEventListener('beforeunload', () => {
    stopScanning();
    stopGamepadPolling();
});
