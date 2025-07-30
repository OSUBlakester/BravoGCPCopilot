// --- Global Flags ---
let isAuthContextReady = false;
let isDomContentLoaded = false;

// --- DOM Elements ---
// Settings elements
let scanDelayInput = null; 
const wakeWordInterjectionInput = document.getElementById('wakeWordInterjection');
const wakeWordNameInput = document.getElementById('wakeWordName');
const CountryCodeInput = document.getElementById('CountryCode');
const speechRateInput = document.getElementById('speechRate');
const LLMOptionsInput = document.getElementById('LLMOptions');
const scanLoopLimitInput = document.getElementById('scanLoopLimit');
const ScanningOffInput = document.getElementById('ScanningOff');
const SummaryOffInput = document.getElementById('SummaryOff');
const autoCleanInput = document.getElementById('autoClean');
const displaySplashInput = document.getElementById('displaySplash');
const displaySplashTimeInput = document.getElementById('displaySplashTime');
const enableMoodSelectionInput = document.getElementById('enableMoodSelection');
const currentMoodSelect = document.getElementById('currentMood');
const clearMoodBtn = document.getElementById('clearMoodBtn');
const ttsVoiceSelect = document.getElementById('ttsVoiceSelect');
const testTtsVoiceButton = document.getElementById('testTtsVoiceButton');
const ttsVoiceStatus = document.getElementById('tts-voice-status');
const toolbarPINInput = document.getElementById('toolbarPIN');
// Grid slider elements will be assigned in initializePage when DOM is ready
let gridColumnsSlider = null;
let gridColumnsValue = null;

const primaryLlmModelSelect = document.getElementById('primaryLlmModel'); // From admin_settings.html

const saveSettingsButton = document.getElementById('saveSettingsButton');

let settingsStatus = null; // Changed to let


// --- State Variables ---
let currentSettings = {};
let availableVoices = []; // To store loaded voices

// --- Utility Functions ---
function showTemporaryStatus(element, message, isError = false, duration = 3000) {
    if (!element) return;
    element.textContent = message;
    element.style.color = isError ? 'red' : (message.includes('...') ? 'blue' : 'green');
    if (duration > 0) {
        setTimeout(() => {
            if (element.textContent === message) { // Clear only if it's the same message
                element.textContent = '';
            }
        }, duration);
    }
}

/**
 * Loads available TTS voices from the backend and populates the dropdown.
 */
async function loadVoices() {
    // ttsVoiceSelect will be assigned in initializePage, check there if needed
    // For now, assume it will be available if this function is called from initializePage
    try {
        // Use window.authenticatedFetch if this endpoint requires authentication
        // Assuming /api/tts-voices is public or handled by a different auth mechanism if not using window.authenticatedFetch
        const response = await window.authenticatedFetch('/api/tts-voices'); // Using authenticatedFetch
        if (!response.ok) throw new Error(`Failed to load voices: ${response.statusText}`);
        availableVoices = await response.json();
        ttsVoiceSelect.innerHTML = '<option value="">-- Select a Voice --</option>'; // Default option
        availableVoices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.name;
            option.textContent = `${voice.name} (${voice.ssml_gender.toLowerCase()})`;
            ttsVoiceSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading TTS voices:', error);
        ttsVoiceSelect.innerHTML = '<option value="">Error loading voices</option>';
        showTemporaryStatus(ttsVoiceStatus, `Error loading voices: ${error.message}`, true);
    }
}




// --- NEW: Function to populate LLM models dropdown ---
async function populateLlmModelsDropdown() {
    if (!primaryLlmModelSelect) {
        // This element might not be on all pages if this script is shared.
        console.info('Primary LLM Model select element not found on this page.');
        return;
    }
    primaryLlmModelSelect.innerHTML = '<option value="">Loading models...</option>'; // Placeholder

    try {
        // Assuming /api/available-llm-models is public or handled by a different auth mechanism
        const response = await window.authenticatedFetch('/api/available-llm-models'); // Using authenticatedFetch
        if (!response.ok) throw new Error(`Failed to fetch LLM models: ${response.statusText}`);
        const data = await response.json();
        primaryLlmModelSelect.innerHTML = ''; // Clear placeholder
        if (data.models && data.models.length > 0) {
            primaryLlmModelSelect.add(new Option("-- Select Primary LLM Model --", "")); // Add a default blank option
            data.models.forEach(model => {
                // Handle both old format (strings) and new format (objects)
                if (typeof model === 'string') {
                    primaryLlmModelSelect.add(new Option(model, model));
                } else {
                    // New format with display_name and description
                    const displayText = model.display_name || model.name;
                    const optionText = model.description ? 
                        `${displayText} - ${model.description}` : displayText;
                    primaryLlmModelSelect.add(new Option(optionText, model.name));
                }
            });
        } else {
            primaryLlmModelSelect.innerHTML = '<option value="">No models available</option>';
        }
    } catch (error) {
        console.error('Error populating LLM models dropdown:', error);
        primaryLlmModelSelect.innerHTML = '<option value="">Error loading models</option>';
        showTemporaryStatus(settingsStatus, `Error loading LLM models: ${error.message}`, true, 5000);
    }
}

// --- Functions ---

/**
 * Loads global settings from the backend.
 */
async function loadSettings() {
    settingsStatus.textContent = 'Loading settings...';
    settingsStatus.style.color = 'gray';
    try {
        // Ensure window.currentAacUserId is available before fetching
        if (!window.currentAacUserId) {
            console.error("loadSettings: window.currentAacUserId is not set. Cannot fetch pages.");
            alert("Critical error: User ID not available for loading pages.");
            return;
        }
        console.log(`Attempting to fetch settings for user: ${window.currentAacUserId}`); // window.currentAacUserId from inline script
        const response = await window.authenticatedFetch('/api/settings'); // Use window.authenticatedFetch

        if (!response.ok) { const errorText = await response.text(); throw new Error(`HTTP error ${response.status}: ${errorText}`); }
        currentSettings = await response.json();

        if (scanDelayInput) { scanDelayInput.value = currentSettings.scanDelay || ''; }
        if (wakeWordInterjectionInput) { wakeWordInterjectionInput.value = currentSettings.wakeWordInterjection || ''; }
        if (wakeWordNameInput) { wakeWordNameInput.value = currentSettings.wakeWordName || ''; }
        if (CountryCodeInput) { CountryCodeInput.value = currentSettings.CountryCode || ''; }
        if (speechRateInput) { speechRateInput.value = currentSettings.speech_rate || 180; } // Populate speech rate
        if (LLMOptionsInput) { LLMOptionsInput.value = currentSettings.LLMOptions || ''; }
        if (scanLoopLimitInput) { scanLoopLimitInput.value = currentSettings.scanLoopLimit !== undefined ? currentSettings.scanLoopLimit : 0; }
        if (ScanningOffInput) { ScanningOffInput.checked = currentSettings.ScanningOff || false; }
        if (SummaryOffInput) { SummaryOffInput.checked = currentSettings.SummaryOff || false; }
        if (autoCleanInput) { autoCleanInput.checked = currentSettings.autoClean || false; }
        if (displaySplashInput) { displaySplashInput.checked = currentSettings.displaySplash || false; }
        if (displaySplashTimeInput) { displaySplashTimeInput.value = currentSettings.displaySplashTime || 3000; }
        if (enableMoodSelectionInput) { enableMoodSelectionInput.checked = currentSettings.enableMoodSelection || false; }
        if (currentMoodSelect) { 
            currentMoodSelect.value = currentSettings.currentMood || ''; 
            // Also update from session storage to show current session mood
            const sessionMood = getCurrentMood ? getCurrentMood() : null;
            if (sessionMood && sessionMood !== 'none') {
                currentMoodSelect.value = sessionMood;
            }
        }
        if (ttsVoiceSelect && currentSettings.selected_tts_voice_name) {
            ttsVoiceSelect.value = currentSettings.selected_tts_voice_name;
        }
        // Load gridColumns setting
        if (gridColumnsSlider && currentSettings.gridColumns !== undefined) {
            gridColumnsSlider.value = currentSettings.gridColumns;
            if (gridColumnsValue) gridColumnsValue.textContent = currentSettings.gridColumns;
            console.log(`Loaded gridColumns setting: ${currentSettings.gridColumns}`);
        } else if (gridColumnsSlider) {
            gridColumnsSlider.value = 6; // Default value
            if (gridColumnsValue) gridColumnsValue.textContent = 6;
            console.log("Using default gridColumns value: 6");
        }
         // Load primary LLM model
        if (primaryLlmModelSelect && currentSettings.primary_llm_model) {
            primaryLlmModelSelect.value = currentSettings.primary_llm_model;
        } else if (primaryLlmModelSelect) {
            primaryLlmModelSelect.value = ''; // Default to no selection if not set
        }

        // Load toolbar PIN (account level)
        await loadToolbarPIN();

         console.log("Settings loaded:", currentSettings);
         showTemporaryStatus(settingsStatus, 'Settings loaded.', false);

    } catch (error) {
        console.error('Error loading settings:', error);
        showTemporaryStatus(settingsStatus, `Error loading settings: ${error.message}`, true, 5000);
    }
}

/**
 * Saves global settings to the backend.
 */
async function saveSettings() {
    const newDelay = scanDelayInput.value;
    const newInterjection = wakeWordInterjectionInput.value.trim();
    const newName = wakeWordNameInput.value.trim();
    const newCountryCode = CountryCodeInput.value.trim();
    const newSpeechRate = speechRateInput.value; // Get speech rate value
    const newLLMOptions = LLMOptionsInput.value; 
    const newScanLoopLimit = scanLoopLimitInput.value;
    const newScanningOff = ScanningOffInput.checked;
    const newSummaryOff = SummaryOffInput.checked;
    const newAutoClean = autoCleanInput.checked;
    const newDisplaySplash = displaySplashInput.checked;
    const newDisplaySplashTime = displaySplashTimeInput.value ? parseInt(displaySplashTimeInput.value) : 3000;
    const newEnableMoodSelection = enableMoodSelectionInput.checked;
    const newCurrentMood = currentMoodSelect.value || null;
    const newSelectedTtsVoice = ttsVoiceSelect ? ttsVoiceSelect.value : null;
    const newGridColumns = gridColumnsSlider ? parseInt(gridColumnsSlider.value) : 6;
    const newToolbarPIN = toolbarPINInput ? toolbarPINInput.value.trim() : null;

    console.log(`Save Settings Debug:
        - gridColumnsSlider exists: ${!!gridColumnsSlider}
        - gridColumnsSlider.value: ${gridColumnsSlider ? gridColumnsSlider.value : 'N/A'}
        - newGridColumns (parsed): ${newGridColumns}`);


    const newPrimaryLlmModel = primaryLlmModelSelect ? primaryLlmModelSelect.value : null;


    // Validation
    if (!newDelay || isNaN(parseInt(newDelay)) || parseInt(newDelay) < 100) {
         settingsStatus.textContent = 'Invalid delay value. Must be >= 100 ms.';
         settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (!newInterjection) {
        settingsStatus.textContent = 'Wake Word Interjection required.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
     if (!newName) {
        settingsStatus.textContent = 'Wake Word Name required.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (!newCountryCode) {
        settingsStatus.textContent = 'Country Code required.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (!newSpeechRate || isNaN(parseInt(newSpeechRate)) || parseInt(newSpeechRate) < 50 || parseInt(newSpeechRate) > 400) { // Example validation for speech rate
        settingsStatus.textContent = 'Invalid Speech Rate. Must be a number (e.g., 50-400).';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
     if (!newLLMOptions || isNaN(parseInt(newLLMOptions)) || parseInt(newLLMOptions) < 1 || parseInt(newLLMOptions) > 20) {
        settingsStatus.textContent = 'Invalid LLM Options. Must be a number (e.g., 1-20).';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (newScanLoopLimit !== '' && (isNaN(parseInt(newScanLoopLimit)) || parseInt(newScanLoopLimit) < 0 || parseInt(newScanLoopLimit) > 10)) {
        settingsStatus.textContent = 'Invalid Scan Loop Limit. Must be 0 (unlimited) or 1-10.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    // Validate gridColumns
    if (newGridColumns < 2 || newGridColumns > 18) {
        settingsStatus.textContent = 'Invalid Button Size. Must be between 2 and 18.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    // Validate toolbar PIN
    if (newToolbarPIN && (newToolbarPIN.length < 3 || newToolbarPIN.length > 10)) {
        settingsStatus.textContent = 'Toolbar PIN must be between 3 and 10 characters.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (ttsVoiceSelect && !newSelectedTtsVoice && availableVoices.length > 0) { // Check if voices loaded but none selected
        showTemporaryStatus(settingsStatus, 'Please select a TTS voice.', true, 4000); return;
    }
    // Validate Primary LLM Model if the select element exists and a value is expected
    if (primaryLlmModelSelect && !newPrimaryLlmModel) {
        showTemporaryStatus(settingsStatus, 'Please select a Primary LLM Model.', true, 4000); return;
    
    }

    const settingsToSave = {
        scanDelay: parseInt(newDelay),
        wakeWordInterjection: newInterjection,
        wakeWordName: newName,
        CountryCode: newCountryCode,
        speech_rate: parseInt(newSpeechRate),
        LLMOptions: parseInt(newLLMOptions),
        scanLoopLimit: newScanLoopLimit !== '' ? parseInt(newScanLoopLimit) : 0,
        ScanningOff: newScanningOff,    
        SummaryOff: newSummaryOff,
        autoClean: newAutoClean,
        displaySplash: newDisplaySplash,
        displaySplashTime: newDisplaySplashTime,
        enableMoodSelection: newEnableMoodSelection,
        currentMood: newCurrentMood,
        selected_tts_voice_name: newSelectedTtsVoice,
        primary_llm_model: newPrimaryLlmModel, // Add to payload
        gridColumns: newGridColumns // Add gridColumns to save payload
    };

    console.log("Saving settings:", settingsToSave);
    showTemporaryStatus(settingsStatus, 'Saving...', false, 0)

    try {
        // Save user settings
        const response = await window.authenticatedFetch('/api/settings', { // Use window.authenticatedFetch
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(settingsToSave)
        });
        if (!response.ok) { const errorText = await response.text(); throw new Error(`Save failed: ${response.status} ${errorText}`); }

        currentSettings = await response.json(); // Update local state with response
        if (scanDelayInput) scanDelayInput.value = currentSettings.scanDelay || '';
        if (wakeWordInterjectionInput) wakeWordInterjectionInput.value = currentSettings.wakeWordInterjection || '';
        if (wakeWordNameInput) wakeWordNameInput.value = currentSettings.wakeWordName || '';
        if (CountryCodeInput) CountryCodeInput.value = currentSettings.CountryCode || '';
        if (speechRateInput) speechRateInput.value = currentSettings.speech_rate || 180;
        if (LLMOptionsInput) LLMOptionsInput.value = currentSettings.LLMOptions || '';
        if (scanLoopLimitInput) scanLoopLimitInput.value = currentSettings.scanLoopLimit !== undefined ? currentSettings.scanLoopLimit : 0;
        if (ScanningOffInput) ScanningOffInput.checked = currentSettings.ScanningOff || false;
        if (SummaryOffInput) SummaryOffInput.checked = currentSettings.SummaryOff || false;
        if (autoCleanInput) autoCleanInput.checked = currentSettings.autoClean || false;
        if (displaySplashInput) displaySplashInput.checked = currentSettings.displaySplash || false;
        if (displaySplashTimeInput) displaySplashTimeInput.value = currentSettings.displaySplashTime || 3000;
        if (ttsVoiceSelect) ttsVoiceSelect.value = currentSettings.selected_tts_voice_name || '';
        // Update gridColumns slider after save
        if (gridColumnsSlider && currentSettings.gridColumns !== undefined) {
            gridColumnsSlider.value = currentSettings.gridColumns;
            if (gridColumnsValue) gridColumnsValue.textContent = currentSettings.gridColumns;
        }
        // Update primary LLM model select
        if (primaryLlmModelSelect) primaryLlmModelSelect.value = currentSettings.primary_llm_model || '';
        
        // Save toolbar PIN separately (account level)
        if (newToolbarPIN) {
            await saveToolbarPIN(newToolbarPIN);
        }
        
        // Update splash screen settings if the function exists
        if (typeof updateSplashScreenSettings === 'function') {
            updateSplashScreenSettings({
                displaySplash: newDisplaySplash,
                displaySplashTime: newDisplaySplashTime
            });
        }
        
        showTemporaryStatus(settingsStatus, 'Settings saved successfully!', false);

    } catch (error) {
        console.error('Error saving settings:', error);
        showTemporaryStatus(settingsStatus, `Error saving: ${error.message}`, true, 5000);
    }
}

/**
 * Tests the currently selected TTS voice.
 */
async function testSelectedVoice() {
    if (!ttsVoiceSelect || !ttsVoiceStatus) return;
    const selectedVoice = ttsVoiceSelect.value;
    if (!selectedVoice) {
        showTemporaryStatus(ttsVoiceStatus, "Please select a voice to test.", true);
        return;
    }
    showTemporaryStatus(ttsVoiceStatus, `Testing voice: ${selectedVoice}...`, false, 0);
    try {
        // Use the /api/test-tts-voice endpoint which is specifically for voice testing
        const response = await window.authenticatedFetch('/api/test-tts-voice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                voice_name: selectedVoice, 
                text: "This is a test of the selected voice."
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `Test failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('TTS Test Response:', result); // Debug log
        
        if (result.audio_url) {
            // Backend returns a URL to the audio file - fetch and play it
            console.log('Audio URL received:', result.audio_url);
            
            try {
                // Fetch the audio file from the URL
                const audioResponse = await fetch(result.audio_url);
                if (!audioResponse.ok) {
                    throw new Error(`Failed to fetch audio file: ${audioResponse.status}`);
                }
                
                const audioArrayBuffer = await audioResponse.arrayBuffer();
                console.log('Fetched audio buffer size:', audioArrayBuffer.byteLength);
                
                await playTestAudio(audioArrayBuffer, result.sample_rate || 22050);
                
                showTemporaryStatus(ttsVoiceStatus, "Test voice played successfully!", false);
                
                // Optional: Clean up the temporary file by calling a cleanup endpoint
                // (You could add a cleanup endpoint to the backend if needed)
                
            } catch (audioError) {
                console.error('Error fetching/playing audio from URL:', audioError);
                showTemporaryStatus(ttsVoiceStatus, `Error playing audio: ${audioError.message}`, true, 5000);
            }
            
        } else if (result.audio_data) {
            // Fallback: Handle base64 audio data if provided
            console.log('Audio data received, length:', result.audio_data.length);
            console.log('Sample rate:', result.sample_rate);
            
            const audioData = result.audio_data;
            const sampleRate = result.sample_rate || 22050;
            
            // Convert base64 to ArrayBuffer
            const base64ToArrayBuffer = (base64) => {
                const binaryString = window.atob(base64);
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                return bytes.buffer;
            };
            
            const audioDataArrayBuffer = base64ToArrayBuffer(audioData);
            console.log('Converted audio buffer size:', audioDataArrayBuffer.byteLength);
            
            await playTestAudio(audioDataArrayBuffer, sampleRate);
            
            showTemporaryStatus(ttsVoiceStatus, "Test voice played successfully!", false);
            
        } else if (result.success && result.message) {
            // Backend says it worked but didn't return audio data or URL
            console.log('Backend response indicates success but no audio_data or audio_url field');
            console.log('Full response:', result);
            showTemporaryStatus(ttsVoiceStatus, result.message + " (No audio data returned)", true);
            
        } else {
            console.log('Unexpected response format:', result);
            showTemporaryStatus(ttsVoiceStatus, "Test completed but unexpected response format.", true);
        }
    } catch (error) {
        console.error('Error testing TTS voice:', error);
        showTemporaryStatus(ttsVoiceStatus, `Error testing voice: ${error.message}`, true, 5000);
    }
}

/**
 * Plays test audio for TTS voice testing
 */
async function playTestAudio(audioDataBuffer, sampleRate) {
    if (!audioDataBuffer) {
        throw new Error('No audio data buffer provided.');
    }

    let audioContext;
    let source;

    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Handle suspended AudioContext (required for Chrome's autoplay policy)
        if (audioContext.state === 'suspended') {
            console.log('AudioContext is suspended, attempting to resume...');
            try {
                await audioContext.resume();
                console.log('AudioContext resumed successfully');
            } catch (resumeError) {
                console.warn("AudioContext resume failed:", resumeError);
                // Continue anyway - sometimes audio still works
            }
        }

        const audioBuffer = await audioContext.decodeAudioData(audioDataBuffer);
        source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start(0);

        return new Promise((resolve, reject) => {
            source.onended = () => {
                if (audioContext && audioContext.state !== 'closed') {
                    audioContext.close();
                }
                resolve();
            };
            
            source.onerror = (error) => {
                if (audioContext && audioContext.state !== 'closed') {
                    audioContext.close();
                }
                reject(error);
            };
        });

    } catch (error) {
        console.error('Error playing test audio:', error);
        if (audioContext && audioContext.state !== 'closed') {
            try {
                audioContext.close();
            } catch (closeError) {
                console.warn('Error closing AudioContext:', closeError);
            }
        }
        throw error;
    }
}

/**
 * Loads the toolbar PIN from account settings.
 */
async function loadToolbarPIN() {
    try {
        const response = await window.authenticatedFetch('/api/account/toolbar-pin');
        if (!response.ok) throw new Error(`Failed to load toolbar PIN: ${response.statusText}`);
        const data = await response.json();
        if (toolbarPINInput) {
            toolbarPINInput.value = data.toolbarPIN || '1234';
        }
        console.log("Toolbar PIN loaded from account settings");
    } catch (error) {
        console.error('Error loading toolbar PIN:', error);
        if (toolbarPINInput) {
            toolbarPINInput.value = '1234'; // Default fallback
        }
        showTemporaryStatus(settingsStatus, `Error loading toolbar PIN: ${error.message}`, true, 3000);
    }
}

/**
 * Saves the toolbar PIN to account settings.
 */
async function saveToolbarPIN(newPIN) {
    try {
        const response = await window.authenticatedFetch('/api/account/toolbar-pin', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ toolbarPIN: newPIN })
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Failed to save toolbar PIN: ${response.statusText}`);
        }
        
        // Update the PIN immediately in the gridpage if it's open in another tab
        // This allows for immediate integration without restart
        if (window.opener && window.opener.updateToolbarPIN) {
            window.opener.updateToolbarPIN(newPIN);
        }
        
        console.log("Toolbar PIN saved successfully");
        return true;
    } catch (error) {
        console.error('Error saving toolbar PIN:', error);
        throw error;
    }
}

// --- Initialization Function ---
async function initializePage() {
    if (isAuthContextReady && isDomContentLoaded) {
        console.log("admin_settings.js: Auth context and DOM ready. Initializing page.");

        // Assign DOM Elements
        scanDelayInput = document.getElementById('scanDelay');
        gridColumnsSlider = document.getElementById('gridColumnsSlider');
        gridColumnsValue = document.getElementById('gridColumnsValue');
        // The following are already assigned globally as const, no need to re-assign:
        // wakeWordInterjectionInput, wakeWordNameInput, CountryCodeInput, speechRateInput,
        // LLMOptionsInput, ScanningOffInput, SummaryOffInput, ttsVoiceSelect,
        // testTtsVoiceButton, ttsVoiceStatus, primaryLlmModelSelect, saveSettingsButton.

        settingsStatus = document.getElementById('settings-status'); // This was 'let', so assign it.

        // Basic check for essential elements
        if (!saveSettingsButton || !settingsStatus) {
            console.error("CRITICAL ERROR: One or more essential DOM elements for admin_settings.js not found.");
            return;
        }

        // Debug: Check if slider elements were found
        console.log("Slider elements found:", {
            gridColumnsSlider: !!gridColumnsSlider,
            gridColumnsValue: !!gridColumnsValue
        });

        if (gridColumnsSlider) {
            console.log("gridColumnsSlider details:", {
                id: gridColumnsSlider.id,
                value: gridColumnsSlider.value,
                min: gridColumnsSlider.min,
                max: gridColumnsSlider.max
            });
        }

        if (gridColumnsValue) {
            console.log("gridColumnsValue details:", {
                id: gridColumnsValue.id,
                textContent: gridColumnsValue.textContent,
                innerHTML: gridColumnsValue.innerHTML
            });
        }

        // Add Event Listeners
        if (saveSettingsButton) saveSettingsButton.addEventListener('click', saveSettings);
        if (testTtsVoiceButton) testTtsVoiceButton.addEventListener('click', testSelectedVoice);
        
        // Mood-related event listeners
        if (clearMoodBtn) {
            clearMoodBtn.addEventListener('click', function() {
                // Clear session storage mood
                if (typeof clearCurrentMood === 'function') {
                    clearCurrentMood();
                }
                // Reset dropdown to no selection
                if (currentMoodSelect) {
                    currentMoodSelect.value = '';
                }
                showTemporaryStatus(settingsStatus, 'Session mood cleared', false, 2000);
            });
        }
        
        // Update session storage when mood is manually changed
        if (currentMoodSelect) {
            currentMoodSelect.addEventListener('change', function() {
                const selectedMood = this.value;
                if (selectedMood) {
                    // Update session storage
                    sessionStorage.setItem('currentSessionMood', selectedMood);
                    console.log('Mood manually updated to:', selectedMood);
                } else {
                    sessionStorage.removeItem('currentSessionMood');
                    console.log('Mood manually cleared');
                }
            });
        }
        
        // Grid columns slider event listener
        if (gridColumnsSlider && gridColumnsValue) {
            // Update value display when slider moves
            const updateSliderValue = function() {
                gridColumnsValue.textContent = gridColumnsSlider.value;
                console.log(`Grid columns slider updated to: ${gridColumnsSlider.value}`);
            };
            
            gridColumnsSlider.addEventListener('input', updateSliderValue);
            gridColumnsSlider.addEventListener('change', updateSliderValue);
            
            // Set initial value
            updateSliderValue();
            console.log("Grid columns slider event listeners added successfully");
        } else {
            console.error("Grid columns slider elements not found:", {
                gridColumnsSlider: !!gridColumnsSlider,
                gridColumnsValue: !!gridColumnsValue
            });
        }


        // Initial data loading
        if (ttsVoiceSelect) await loadVoices();
        if (primaryLlmModelSelect) await populateLlmModelsDropdown();
        await loadSettings();
        await loadToolbarPIN(); // Load the toolbar PIN on page initialization
    }
}

// --- Auth Context Ready Handler ---
function authContextIsReady() {
    if (isAuthContextReady) return;
    console.log("admin_settings.js: Authentication context is now marked as ready.");
    isAuthContextReady = true;
    initializePage();
}


// --- Event Listeners ---
// Listener for when the authentication context is ready
document.addEventListener('adminUserContextReady', () => {
    console.log("admin_settings.js: 'adminUserContextReady' event received.");
    authContextIsReady();
});

if (window.adminContextInitializedByInlineScript === true) {
    console.log("admin_settings.js: Global flag 'adminContextInitializedByInlineScript' was already true.");
    authContextIsReady();
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("admin_settings.js: DOMContentLoaded event.");
    isDomContentLoaded = true;
    initializePage();
});