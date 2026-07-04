// --- Pre-warm SpeechSynthesis Voices ---
if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.getVoices();
}

// --- Global Flags ---
let isAuthContextReady = false;
let isDomContentLoaded = false;

function markAdminSaving() {
    window.adminUnsavedIndicator?.markSaving?.();
}

function markAdminSaved() {
    window.adminUnsavedIndicator?.markSaved?.();
}

// Volume Slider Handler
function volumeSliderHandler() {
    console.log('Volume slider moved to:', this.value);
    const display = document.getElementById('volumeDisplay');
    if (display) {
        display.textContent = `${this.value}/10`;
        console.log('Volume display updated to:', display.textContent);
    } else {
        console.error('Volume display element not found during slider change');
    }
}

// Setup volume slider function
function setupVolumeSliderNow() {
    console.log('Setting up volume slider...');
    const slider = document.getElementById('applicationVolume');
    const display = document.getElementById('volumeDisplay');
    
    if (slider && display) {
        slider.addEventListener('input', function() {
            display.textContent = `${this.value}/10`;
            console.log('Volume changed to:', this.value);
        });
        console.log('Volume slider setup complete');
        return true;
    } else {
        console.error('Volume slider elements not found');
        return false;
    }
}

// Try setup immediately
setupVolumeSliderNow();

// --- DOM Elements ---
// Settings elements
let scanDelayInput = null; 
const wakeWordInterjectionInput = document.getElementById('wakeWordInterjection');
const wakeWordNameInput = document.getElementById('wakeWordName');
const CountryCodeInput = document.getElementById('CountryCode');
const speechRateInput = document.getElementById('speechRate');
const LLMOptionsInput = document.getElementById('LLMOptions');
const FreestyleOptionsInput = document.getElementById('FreestyleOptions');
const tapWordsRowsInput = document.getElementById('tapWordsRows');
const tapPhrasesRowsInput = document.getElementById('tapPhrasesRows');
const scanLoopLimitInput = document.getElementById('scanLoopLimit');
const scanModeInput = document.getElementById('scanMode');
const ScanningOffInput = document.getElementById('ScanningOff');
const waitForSwitchToScanInput = document.getElementById('waitForSwitchToScan');
const playWaitForSwitchChimeInput = document.getElementById('playWaitForSwitchChime');
// const useTapInterfaceInput = document.getElementById('useTapInterface'); // Removed from UI
const interfaceAuditoryInput = document.getElementById('interfaceAuditory');
const interfaceTapInput = document.getElementById('interfaceTap');
const SummaryOffInput = document.getElementById('SummaryOff');
const enablePictogramsInput = document.getElementById('enablePictograms');
const disableTapPictogramsInput = document.getElementById('disableTapPictograms');
const useHybridPagesCheckbox = document.getElementById('useHybridPages');
const tapDynamicRowsInput = document.getElementById('tapDynamicRows');
const tapStaticRowsDisplay = document.getElementById('tapStaticRowsDisplay');
const dynamicRowsContainer = null; // removed from UI
const enableSightWordsInput = document.getElementById('enableSightWords');
const sightWordGradeLevelInput = document.getElementById('sightWordGradeLevel');
const autoCleanInput = document.getElementById('autoClean');
const displaySplashInput = document.getElementById('displaySplash');
const displaySplashTimeInput = document.getElementById('displaySplashTime');
const enableMoodSelectionInput = document.getElementById('enableMoodSelection');
const vocabularyLevelSelect = document.getElementById('vocabularyLevel');
const ttsVoiceSelect = document.getElementById('ttsVoiceSelect');
const testTtsVoiceButton = document.getElementById('testTtsVoiceButton');
const ttsVoiceStatus = document.getElementById('tts-voice-status');
const userLanguageSelect = document.getElementById('userLanguage');
const defaultPartnerLanguageSelect = document.getElementById('defaultPartnerLanguage');
const defaultPartnerVoiceSelect = document.getElementById('defaultPartnerVoiceSelect');
const voiceStyleInputs = document.querySelectorAll('input[name="voiceStyle"]');
const locationOverrideLanguagesSelect = document.getElementById('locationOverrideLanguages');
const locationOverrideLanguagesTable = document.getElementById('locationOverrideLanguagesTable');
const addLocationOverrideRowButton = document.getElementById('addLocationOverrideRowButton');
const locationOverrideVoiceContainer = document.getElementById('locationOverrideVoiceContainer');
const toolbarPINInput = document.getElementById('toolbarPIN');
const spellLetterOrderSelect = document.getElementById('spellLetterOrder');
const mascotSelect = document.getElementById('mascot');
// Grid columns input assigned in initializePage when DOM is ready
let gridColumnsSlider = null;
let gridColumnsValue = null;

function updateStaticRowsDisplay() {
    if (!tapWordsRowsInput || !tapDynamicRowsInput || !tapStaticRowsDisplay) return;
    let total = Math.max(1, Math.min(7, parseInt(tapWordsRowsInput.value) || 3));
    let dynamic = Math.max(0, Math.min(total, parseInt(tapDynamicRowsInput.value) || 0));
    tapWordsRowsInput.value = total;
    tapDynamicRowsInput.value = dynamic;
    tapDynamicRowsInput.max = total;
    tapStaticRowsDisplay.value = total - dynamic;
}
// Volume slider elements
let applicationVolumeSlider = null;
let volumeDisplay = null;

// Backup volume slider initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded - Setting up volume slider as backup...');
    const slider = document.getElementById('applicationVolume');
    const display = document.getElementById('volumeDisplay');
    
    if (slider && display) {
        console.log('DOMContentLoaded found volume elements, adding listener...');
        slider.addEventListener('input', function() {
            display.textContent = `${this.value}/10`;
            console.log('DOMContentLoaded listener - Volume updated to:', this.value);
        });
    } else {
        console.error('DOMContentLoaded - Volume elements still not found!');
    }
});

const emailProviderStatusEl = document.getElementById('email-provider-status');
const emailServerPrereqEl = document.getElementById('email-server-prereq');
const refreshEmailStatusButton = document.getElementById('refreshEmailStatusButton');
const connectEmailButton = document.getElementById('connectEmailButton');
const disconnectEmailButton = document.getElementById('disconnectEmailButton');
const exportProfileSettingsButton = document.getElementById('exportProfileSettingsButton');
const importProfileSettingsButton = document.getElementById('importProfileSettingsButton');
const importProfileSettingsFileInput = document.getElementById('importProfileSettingsFileInput');

const saveSettingsButton = document.getElementById('saveSettingsButton');

let settingsStatus = null; // Changed to let


// --- State Variables ---
let currentSettings = {};
let availableVoices = []; // To store loaded voices

function getSelectedVoiceStyle() {
    const selected = document.querySelector('input[name="voiceStyle"]:checked');
    return selected ? selected.value : 'adult';
}

function shouldUseBrowserSpeechFallback(error) {
    const errorStr = String(error?.message || error?.detail || error || '');
    const message = errorStr.toLowerCase();
    const shouldFallback = (
        message.includes('google') ||
        message.includes('credential') ||
        message.includes('reauth') ||
        message.includes('login') ||
        message.includes('gcloud') ||
        message.includes('auth') ||
        message.includes('azure') ||
        message.includes('unavailable') ||
        message.includes('not configured') ||
        message.includes('tts') ||
        message.includes('503') ||
        message.includes('500') ||
        message.includes('failed')
    );
    console.log(`[TTS Fallback] shouldUseBrowserSpeechFallback checking error: "${errorStr}". Result: ${shouldFallback}`);
    return shouldFallback;
}

function inferLocaleFromVoiceName(voiceName) {
    const match = String(voiceName || '').match(/^([a-z]{2}-[A-Za-z]{2,4})/);
    return match ? match[1].replace('_', '-') : 'en-US';
}

function getBrowserSpeechRate(voiceStyle) {
    switch (voiceStyle) {
        case 'child':
            return 1.15;
        default:
            return 1.0;
    }
}

// Keep loadBrowserVoices for backward compatibility, but we avoid calling it synchronously to prevent losing user gesture.
function loadBrowserVoices() {
    return new Promise((resolve) => {
        const synth = window.speechSynthesis;
        if (!synth) {
            resolve([]);
            return;
        }

        const existingVoices = synth.getVoices();
        if (existingVoices.length > 0) {
            resolve(existingVoices);
            return;
        }

        const handleVoicesChanged = () => {
            synth.removeEventListener('voiceschanged', handleVoicesChanged);
            resolve(synth.getVoices());
        };

        synth.addEventListener('voiceschanged', handleVoicesChanged);
        window.setTimeout(() => {
            synth.removeEventListener('voiceschanged', handleVoicesChanged);
            resolve(synth.getVoices());
        }, 1000);
    });
}

async function playBrowserSpeechFallback(text, voiceName, voiceStyle) {
    if (!window.speechSynthesis) {
        throw new Error('Browser speech preview is not supported in this browser.');
    }

    const runSpeech = (useVoice) => {
        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            window.activeUtterance = utterance; // Keep global reference to prevent GC

            const locale = inferLocaleFromVoiceName(voiceName);
            utterance.lang = locale;
            utterance.rate = getBrowserSpeechRate(voiceStyle);

            if (useVoice) {
                const voices = window.speechSynthesis.getVoices() || [];
                const localeLower = locale.toLowerCase();
                const matchingVoice = voices.find((voice) => String(voice.lang || '').toLowerCase() === localeLower)
                    || voices.find((voice) => String(voice.lang || '').toLowerCase().startsWith(localeLower.split('-')[0]))
                    || null;

                if (matchingVoice) {
                    console.log(`[TTS Fallback] Attempting with voice: ${matchingVoice.name} (${matchingVoice.lang})`);
                    utterance.voice = matchingVoice;
                }
            } else {
                console.log(`[TTS Fallback] Attempting with default browser voice for locale: ${locale}`);
            }

            const startTime = Date.now();
            let hasCompleted = false;

            utterance.onend = () => {
                const duration = Date.now() - startTime;
                console.log(`[TTS Fallback] onend fired. Duration: ${duration}ms`);
                window.activeUtterance = null;
                hasCompleted = true;
                
                // If it completed in less than 75ms, it's a silent failure/skipped play
                if (duration < 75) {
                    reject(new Error(`Speech completed too quickly (${duration}ms) - silent abort.`));
                } else {
                    resolve();
                }
            };

            utterance.onerror = (event) => {
                console.error('[TTS Fallback] onerror fired. Event:', event);
                window.activeUtterance = null;
                hasCompleted = true;
                reject(new Error(event?.error || event?.message || 'Browser speech preview failed.'));
            };

            window.speechSynthesis.speak(utterance);
        });
    };

    const speaking = window.speechSynthesis.speaking;
    if (speaking) {
        window.speechSynthesis.cancel();
    }

    const startSpeak = async () => {
        try {
            // First attempt using the matched voice
            await runSpeech(true);
        } catch (err) {
            console.warn('[TTS Fallback] Primary voice attempt failed or was silent:', err.message);
            console.log('[TTS Fallback] Trying secondary attempt using browser default voice...');
            
            // Second attempt using the browser default voice
            try {
                await runSpeech(false);
            } catch (err2) {
                console.error('[TTS Fallback] Secondary fallback attempt also failed:', err2.message);
                throw new Error('Browser speech preview failed to produce sound.');
            }
        }
    };

    if (speaking) {
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    await startSpeak();
}

async function handleVoiceTestFailure(error, text, selectedVoice, targetElement, successMessage) {
    if (!shouldUseBrowserSpeechFallback(error)) {
        console.warn('[TTS Fallback] Fallback not allowed for this error. Throwing original error.');
        throw error;
    }

    console.log(`[TTS Fallback] Executing browser speech fallback. Text: "${text}", Voice: "${selectedVoice}"`);
    await playBrowserSpeechFallback(text, selectedVoice, getSelectedVoiceStyle());
    console.log('[TTS Fallback] Browser speech fallback completed successfully.');
    showTemporaryStatus(targetElement, `${successMessage} (browser preview)`, false, 4000);
}

function setSelectedVoiceStyle(style) {
    let normalized = ['adult', 'child'].includes(style) ? style : 'adult';
    if (style === 'teen') {
        normalized = 'child';
    }
    voiceStyleInputs.forEach(input => {
        input.checked = input.value === normalized;
    });
}

const SUPPORTED_LANGUAGE_OPTIONS = [
    { value: 'en-US', label: 'English (US)' },
    { value: 'es-US', label: 'Spanish (US)' },
    { value: 'fr-FR', label: 'French (France)' },
    { value: 'de-DE', label: 'German (Germany)' },
    { value: 'it-IT', label: 'Italian (Italy)' },
    { value: 'pt-BR', label: 'Portuguese (Brazil)' },
    { value: 'ar-XA', label: 'Arabic' }
];

// Style configuration hints removed. Filtering is now done strictly by provider (Google vs Azure).

function getSelectedMultiValues(selectEl) {
    if (!selectEl) return [];
    return Array.from(selectEl.selectedOptions || []).map(option => option.value).filter(Boolean);
}

function setSelectedMultiValues(selectEl, values) {
    if (!selectEl) return;
    const selectedSet = new Set(Array.isArray(values) ? values : []);
    Array.from(selectEl.options).forEach(option => {
        option.selected = selectedSet.has(option.value);
    });
}

function populateLanguageSelectors() {
    const makeOptions = (target) => {
        if (!target) return;
        target.innerHTML = '';
        SUPPORTED_LANGUAGE_OPTIONS.forEach(lang => {
            const opt = document.createElement('option');
            opt.value = lang.value;
            opt.textContent = lang.label;
            target.appendChild(opt);
        });
    };

    makeOptions(userLanguageSelect);
    makeOptions(defaultPartnerLanguageSelect);
    makeOptions(locationOverrideLanguagesSelect);
}

function getVoicesForLocale(locale) {
    if (!locale) return availableVoices;
    const localeLower = locale.toLowerCase();
    return availableVoices.filter(voice => {
        const languageCodes = Array.isArray(voice.language_codes) ? voice.language_codes : [];
        return languageCodes.some(code => String(code).toLowerCase() === localeLower);
    });
}

function filterVoicesByStyle(voices, voiceStyle) {
    if (!Array.isArray(voices) || voices.length === 0) return [];
    let style = ['adult', 'child'].includes(voiceStyle) ? voiceStyle : 'adult';
    if (voiceStyle === 'teen') style = 'child';

    let filtered = [];
    if (style === 'child') {
        filtered = voices.filter(v => v.provider === 'azure');
    } else {
        filtered = voices.filter(v => v.provider === 'google');
    }

    // Never strand the user with an empty list.
    return filtered.length > 0 ? filtered : voices;
}

function fillVoiceSelect(selectEl, locale, selectedVoice = '', options = {}) {
    if (!selectEl) return;
    const applyStyleFilter = options.applyStyleFilter === true;
    const voiceStyle = options.voiceStyle || getSelectedVoiceStyle();

    const localeVoices = getVoicesForLocale(locale);
    const voices = applyStyleFilter ? filterVoicesByStyle(localeVoices, voiceStyle) : localeVoices;

    selectEl.innerHTML = '<option value="">-- Select a Voice --</option>';
    voices.forEach(voice => {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.name} (${String(voice.ssml_gender || 'unknown').toLowerCase()})`;
        selectEl.appendChild(option);
    });

    // Preserve already-saved voices even when the style filter hides them.
    if (selectedVoice && !voices.some((voice) => voice.name === selectedVoice)) {
        const selectedOption = document.createElement('option');
        selectedOption.value = selectedVoice;
        selectedOption.textContent = `${selectedVoice} (currently selected)`;
        selectEl.appendChild(selectedOption);
    }

    if (selectedVoice) {
        selectEl.value = selectedVoice;
    }
}

function renderLocationOverrideVoiceControls(selectedLocales, selectedVoiceMap = {}) {
    if (!locationOverrideVoiceContainer) return;
    locationOverrideVoiceContainer.innerHTML = '';

    if (!selectedLocales.length) {
        const emptyText = document.createElement('p');
        emptyText.className = 'text-sm text-gray-500';
        emptyText.textContent = 'No location override languages selected.';
        locationOverrideVoiceContainer.appendChild(emptyText);
        return;
    }

    selectedLocales.forEach(locale => {
        const wrapper = document.createElement('div');
        wrapper.className = 'grid grid-cols-1 md:grid-cols-3 gap-3 items-center';

        const label = document.createElement('label');
        label.className = 'text-sm font-medium text-gray-700';
        label.textContent = `Voice for ${locale}`;

        const select = document.createElement('select');
        select.className = 'md:col-span-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full rounded-md sm:text-sm border-gray-300 shadow-sm';
        select.dataset.locale = locale;

        fillVoiceSelect(select, locale, selectedVoiceMap[locale] || '');

        wrapper.appendChild(label);
        wrapper.appendChild(select);
        locationOverrideVoiceContainer.appendChild(wrapper);
    });
}

// New table-based location override management functions
function renderLocationOverrideLanguagesTable(localeVoiceMap = {}) {
    if (!locationOverrideLanguagesTable) return;
    locationOverrideLanguagesTable.innerHTML = '';

    if (!localeVoiceMap || Object.keys(localeVoiceMap).length === 0) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 3;
        emptyCell.className = 'text-center py-4 text-gray-500';
        emptyCell.textContent = 'No location override languages configured yet.';
        emptyRow.appendChild(emptyCell);
        locationOverrideLanguagesTable.appendChild(emptyRow);
        return;
    }

    Object.entries(localeVoiceMap).forEach(([locale, voiceName]) => {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-300 hover:bg-gray-50';
        row.dataset.locale = locale;

        // Language cell
        const langCell = document.createElement('td');
        langCell.className = 'border border-gray-300 px-4 py-3';
        const langSelect = document.createElement('select');
        langSelect.className = 'w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500';
        langSelect.dataset.locale = locale;
        SUPPORTED_LANGUAGE_OPTIONS.forEach(lang => {
            const opt = document.createElement('option');
            opt.value = lang.value;
            opt.textContent = lang.label;
            langSelect.appendChild(opt);
        });
        langSelect.value = locale;
        langSelect.addEventListener('change', (e) => {
            // Update row's data-locale attribute when language changes
            row.dataset.locale = e.target.value;
            // Refresh voices for the new locale
            updateVoiceSelectInRow(row, e.target.value, voiceName || '');
        });
        langCell.appendChild(langSelect);
        row.appendChild(langCell);

        // Voice cell
        const voiceCell = document.createElement('td');
        voiceCell.className = 'border border-gray-300 px-4 py-3';
        const voiceSelect = document.createElement('select');
        voiceSelect.className = 'w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500';
        voiceSelect.dataset.locale = locale;
        fillVoiceSelect(voiceSelect, locale, voiceName || '');
        voiceCell.appendChild(voiceSelect);
        row.appendChild(voiceCell);

        // Delete button cell
        const actionCell = document.createElement('td');
        actionCell.className = 'border border-gray-300 px-4 py-3 text-center flex gap-2 justify-center';
        const testBtn = document.createElement('button');
        testBtn.type = 'button';
        testBtn.className = 'inline-flex items-center gap-1 px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded transition-colors';
        testBtn.innerHTML = '<i class=\"fas fa-volume-up\"></i>';
        testBtn.title = 'Test this voice';
        testBtn.addEventListener('click', () => testLocationOverrideVoice(voiceSelect));
        actionCell.appendChild(testBtn);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'inline-flex items-center gap-1 px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded transition-colors';
        deleteBtn.innerHTML = '<i class=\"fas fa-trash\"></i> Delete';
        deleteBtn.addEventListener('click', () => deleteLocationOverrideRow(row));
        actionCell.appendChild(deleteBtn);
        row.appendChild(actionCell);

        locationOverrideLanguagesTable.appendChild(row);
    });
}

function updateVoiceSelectInRow(row, locale, currentVoice = '') {
    const voiceSelect = row.querySelector('td:nth-child(2) select');
    if (voiceSelect) {
        fillVoiceSelect(voiceSelect, locale, currentVoice);
    }
}

function addLocationOverrideRow() {
    // Find the first unused language from SUPPORTED_LANGUAGE_OPTIONS
    const existingLocales = new Set(
        Array.from(locationOverrideLanguagesTable?.querySelectorAll('tr[data-locale]') || [])
            .map(row => row.dataset.locale)
    );

    const availableLanguage = SUPPORTED_LANGUAGE_OPTIONS.find(lang => !existingLocales.has(lang.value));
    if (!availableLanguage) {
        alert('All supported languages are already in the table.');
        return;
    }

    // Create new row with the suggested language
    const newLocale = availableLanguage.value;
    const newMap = { [newLocale]: '' };
    
    // Render just the new row
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-300 hover:bg-gray-50';
    row.dataset.locale = newLocale;

    // Language cell
    const langCell = document.createElement('td');
    langCell.className = 'border border-gray-300 px-4 py-3';
    const langSelect = document.createElement('select');
    langSelect.className = 'w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500';
    langSelect.dataset.locale = newLocale;
    SUPPORTED_LANGUAGE_OPTIONS.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang.value;
        opt.textContent = lang.label;
        langSelect.appendChild(opt);
    });
    langSelect.value = newLocale;
    langSelect.addEventListener('change', (e) => {
        row.dataset.locale = e.target.value;
        updateVoiceSelectInRow(row, e.target.value, '');
    });
    langCell.appendChild(langSelect);
    row.appendChild(langCell);

    // Voice cell
    const voiceCell = document.createElement('td');
    voiceCell.className = 'border border-gray-300 px-4 py-3';
    const voiceSelect = document.createElement('select');
    voiceSelect.className = 'w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500';
    voiceSelect.dataset.locale = newLocale;
    fillVoiceSelect(voiceSelect, newLocale, '');
    voiceCell.appendChild(voiceSelect);
    row.appendChild(voiceCell);

    // Delete button cell
    const actionCell = document.createElement('td');
    actionCell.className = 'border border-gray-300 px-4 py-3 text-center flex gap-2 justify-center';
    const testBtn = document.createElement('button');
    testBtn.type = 'button';
    testBtn.className = 'inline-flex items-center gap-1 px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded transition-colors';
    testBtn.innerHTML = '<i class=\"fas fa-volume-up\"></i>';
    testBtn.title = 'Test this voice';
    testBtn.addEventListener('click', () => testLocationOverrideVoice(voiceSelect));
    actionCell.appendChild(testBtn);
    
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'inline-flex items-center gap-1 px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded transition-colors';
    deleteBtn.innerHTML = '<i class=\"fas fa-trash\"></i> Delete';
    deleteBtn.addEventListener('click', () => deleteLocationOverrideRow(row));
    actionCell.appendChild(deleteBtn);
    row.appendChild(actionCell);

    locationOverrideLanguagesTable.appendChild(row);
}

function deleteLocationOverrideRow(row) {
    if (confirm('Are you sure you want to delete this location override language?')) {
        row.remove();
    }
}

function getLocationOverrideLanguagesFromTable() {
    const map = {};
    if (!locationOverrideLanguagesTable) return map;
    const rows = locationOverrideLanguagesTable.querySelectorAll('tr[data-locale]');
    rows.forEach(row => {
        const locale = row.dataset.locale;
        const voiceSelect = row.querySelector('td:nth-child(2) select');
        const voiceName = voiceSelect?.value || '';
        if (locale && voiceName) {
            map[locale] = voiceName;
        }
    });
    return map;
}

function getLocationOverrideVoiceMapFromUI() {
    // Now using table-based approach instead
    return getLocationOverrideLanguagesFromTable();
}

function refreshLanguageDependentVoiceControls() {
    const partnerLocale = defaultPartnerLanguageSelect ? defaultPartnerLanguageSelect.value : 'en-US';
    const selectedPartnerVoice = defaultPartnerVoiceSelect ? defaultPartnerVoiceSelect.value : '';
    const currentVoiceStyle = getSelectedVoiceStyle();
    fillVoiceSelect(defaultPartnerVoiceSelect, partnerLocale, selectedPartnerVoice, {
        applyStyleFilter: true,
        voiceStyle: currentVoiceStyle
    });
    
    // Also update test voice select to stay in sync
    if (ttsVoiceSelect) {
        fillVoiceSelect(ttsVoiceSelect, partnerLocale, selectedPartnerVoice, {
            applyStyleFilter: true,
            voiceStyle: currentVoiceStyle
        });
    }
    
    // Also update voice options in table rows
    if (locationOverrideLanguagesTable) {
        const rows = locationOverrideLanguagesTable.querySelectorAll('tr[data-locale]');
        rows.forEach(row => {
            const locale = row.dataset.locale;
            const voiceSelect = row.querySelector('td:nth-child(2) select');
            const currentVoice = voiceSelect?.value || '';
            if (voiceSelect) {
                fillVoiceSelect(voiceSelect, locale, currentVoice);
            }
        });
    }
}

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
    try {
        // This endpoint is public in backend and should not depend on /api/settings auth state.
        const response = await fetch('/api/tts-voices');
        if (!response.ok) throw new Error(`Failed to load voices: ${response.statusText}`);
        availableVoices = await response.json();
        refreshLanguageDependentVoiceControls();
        console.log(`Loaded ${availableVoices.length} total voices`);
    } catch (error) {
        console.error('Error loading TTS voices:', error);
        if (defaultPartnerVoiceSelect) {
            defaultPartnerVoiceSelect.innerHTML = '<option value="">Error loading voices</option>';
        }
        if (ttsVoiceSelect) {
            ttsVoiceSelect.innerHTML = '<option value="">Error loading voices</option>';
        }
        showTemporaryStatus(ttsVoiceStatus, `Error loading voices: ${error.message}`, true);
        showTemporaryStatus(settingsStatus, `Error loading voices: ${error.message}`, true);
    }
}

// --- Provider selection is now static, no need to load models dynamically ---

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
        
        // Initialize volume slider elements
        if (!applicationVolumeSlider) {
            applicationVolumeSlider = document.getElementById('applicationVolume');
            volumeDisplay = document.getElementById('volumeDisplay');
            
            if (applicationVolumeSlider && volumeDisplay) {
                applicationVolumeSlider.addEventListener('input', function() {
                    volumeDisplay.textContent = `${this.value}/10`;
                    console.log('Volume slider updated to:', this.value);
                });
                console.log('Volume slider event listener added');
            }
        }
        
        if (applicationVolumeSlider && volumeDisplay) {
            const volume = currentSettings.applicationVolume !== undefined ? currentSettings.applicationVolume : 8;
            applicationVolumeSlider.value = volume;
            volumeDisplay.textContent = `${volume}/10`;
            console.log('Application volume set to:', volume);
        }
        if (LLMOptionsInput) {
            LLMOptionsInput.value = currentSettings.LLMOptions !== null && currentSettings.LLMOptions !== undefined
                ? currentSettings.LLMOptions
                : '';
        }
        if (FreestyleOptionsInput) { 
            console.log('DEBUG FreestyleOptions - Element found:', !!FreestyleOptionsInput);
            console.log('DEBUG FreestyleOptions - currentSettings.FreestyleOptions:', currentSettings.FreestyleOptions);
            FreestyleOptionsInput.value = currentSettings.FreestyleOptions !== null && currentSettings.FreestyleOptions !== undefined ? currentSettings.FreestyleOptions : ''; 
        }
        if (tapWordsRowsInput) {
            tapWordsRowsInput.value = currentSettings.tapWordsRows !== null && currentSettings.tapWordsRows !== undefined ? currentSettings.tapWordsRows : 4;
        }
        if (tapPhrasesRowsInput) {
            tapPhrasesRowsInput.value = currentSettings.tapPhrasesRows !== null && currentSettings.tapPhrasesRows !== undefined ? currentSettings.tapPhrasesRows : 0;
        }
        if (tapDynamicRowsInput) {
            tapDynamicRowsInput.value = currentSettings.tapDynamicRows !== null && currentSettings.tapDynamicRows !== undefined ? currentSettings.tapDynamicRows : 0;
        }
        updateStaticRowsDisplay();
        if (scanLoopLimitInput) { scanLoopLimitInput.value = currentSettings.scanLoopLimit !== undefined ? currentSettings.scanLoopLimit : 0; }
        if (scanModeInput) { scanModeInput.value = currentSettings.scanMode === 'step' ? 'step' : 'auto'; }
        
        // Handle Interface Mode Radio Buttons
        if (interfaceAuditoryInput && interfaceTapInput) {
            if (currentSettings.useTapInterface) {
                interfaceTapInput.checked = true;
            } else {
                interfaceAuditoryInput.checked = true;
            }
        }

        // if (ScanningOffInput) { ScanningOffInput.checked = currentSettings.ScanningOff || false; } // Removed from UI
        if (SummaryOffInput) { SummaryOffInput.checked = currentSettings.SummaryOff || false; }
        if (autoCleanInput) { autoCleanInput.checked = currentSettings.autoClean || false; }
        if (displaySplashInput) { displaySplashInput.checked = currentSettings.displaySplash || false; }
        if (displaySplashTimeInput) { displaySplashTimeInput.value = currentSettings.displaySplashTime || 3000; }
        if (enableMoodSelectionInput) { enableMoodSelectionInput.checked = currentSettings.enableMoodSelection || false; }
        // if (useTapInterfaceInput) { useTapInterfaceInput.checked = currentSettings.useTapInterface || false; } // Removed from UI
        if (enablePictogramsInput) { enablePictogramsInput.checked = currentSettings.enablePictograms !== false; }
        if (disableTapPictogramsInput) { disableTapPictogramsInput.checked = currentSettings.disableTapPictograms || false; }
        if (ScanningOffInput) { ScanningOffInput.checked = currentSettings.ScanningOff || false; }
        if (waitForSwitchToScanInput) { waitForSwitchToScanInput.checked = currentSettings.waitForSwitchToScan || false; }
        if (playWaitForSwitchChimeInput) { playWaitForSwitchChimeInput.checked = currentSettings.playWaitForSwitchChime || false; }
        if (enableSightWordsInput) { enableSightWordsInput.checked = currentSettings.enableSightWords !== false; }
        if (sightWordGradeLevelInput) { sightWordGradeLevelInput.value = currentSettings.sightWordGradeLevel || 'pre_k'; }
        if (userLanguageSelect) userLanguageSelect.value = currentSettings.userLanguage || 'en-US';
        if (defaultPartnerLanguageSelect) defaultPartnerLanguageSelect.value = currentSettings.defaultPartnerLanguage || 'en-US';
        if (locationOverrideLanguagesSelect) {
            setSelectedMultiValues(locationOverrideLanguagesSelect, currentSettings.locationOverrideLanguages || []);
        }
        // Load location override languages table
        const locationOverrideVoices = currentSettings.locationOverrideVoices || {};
        if (Object.keys(locationOverrideVoices).length > 0) {
            renderLocationOverrideLanguagesTable(locationOverrideVoices);
        } else {
            renderLocationOverrideLanguagesTable({});
        }
        // Set voice style first so the dropdown is filtered correctly before populating
        setSelectedVoiceStyle(currentSettings.voice_style || 'adult');
        refreshLanguageDependentVoiceControls();
        const savedVoice = currentSettings.defaultPartnerVoice || currentSettings.selected_tts_voice_name || '';
        if (defaultPartnerVoiceSelect) {
            defaultPartnerVoiceSelect.value = savedVoice;
        }
        if (ttsVoiceSelect) {
            ttsVoiceSelect.value = savedVoice;
        }
        // Load spellLetterOrder setting
        if (spellLetterOrderSelect) {
            spellLetterOrderSelect.value = currentSettings.spellLetterOrder || 'alphabetical';
        }
        // Load vocabularyLevel setting
        if (vocabularyLevelSelect) {
            vocabularyLevelSelect.value = currentSettings.vocabularyLevel || 'functional';
        }
        // Load mascot setting
        if (mascotSelect) {
            mascotSelect.value = currentSettings.mascot || 'buddy';
        }
        // Load gridColumns setting
        if (gridColumnsSlider) {
            gridColumnsSlider.value = currentSettings.gridColumns !== undefined ? currentSettings.gridColumns : 6;
        }
        // Load toolbar PIN (account level)
        await loadToolbarPIN();
        await loadEmailProviderStatus();

         console.log("Settings loaded:", currentSettings);
         showTemporaryStatus(settingsStatus, 'Settings loaded.', false);

    } catch (error) {
        console.error('Error loading settings:', error);
        showTemporaryStatus(settingsStatus, `Error loading settings: ${error.message}`, true, 5000);
    }
}

async function loadEmailProviderStatus() {
    if (!emailProviderStatusEl || !window.authenticatedFetch) return;

    emailProviderStatusEl.textContent = 'Checking…';
    emailProviderStatusEl.style.color = '#4b5563';
    if (emailServerPrereqEl) emailServerPrereqEl.classList.add('hidden');

    // First check Firestore connection state
    let connected = false;
    let address = '';
    try {
        const response = await window.authenticatedFetch('/api/email/status');
        if (response.ok) {
            const statusData = await response.json();
            const gmailStatus = statusData?.provider_status?.gmail || {};
            connected = gmailStatus.connected === true;
            address = gmailStatus.email_address || '';
        }
    } catch (_) { /* fall through to config probe */ }

    if (connected) {
        emailProviderStatusEl.style.color = '#047857';
        emailProviderStatusEl.textContent = `✓ Connected${address ? ` as ${address}` : ''}`;
        if (emailServerPrereqEl) emailServerPrereqEl.classList.add('hidden');
        return;
    }

    // Probe whether server OAuth credentials are configured by calling connect-url
    // (400/500 vs 200 tells us if env vars are missing)
    try {
        const probeResp = await window.authenticatedFetch('/api/email/connect-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: 'gmail' })
        });
        if (!probeResp.ok) {
            const errText = await probeResp.text().catch(() => '');
            if (errText.includes('Missing Google OAuth') || probeResp.status === 500) {
                emailProviderStatusEl.style.color = '#92400e';
                emailProviderStatusEl.textContent = '⚠ Server not configured — see setup requirements below';
                if (emailServerPrereqEl) emailServerPrereqEl.classList.remove('hidden');
                return;
            }
        }
        // connect-url returned OK, meaning config is present but no account linked yet
        emailProviderStatusEl.style.color = '#1d4ed8';
        emailProviderStatusEl.textContent = 'Not connected — click Connect Gmail to authorize';
        if (emailServerPrereqEl) emailServerPrereqEl.classList.add('hidden');
    } catch (_) {
        emailProviderStatusEl.style.color = '#1d4ed8';
        emailProviderStatusEl.textContent = 'Not connected — click Connect Gmail to authorize';
        if (emailServerPrereqEl) emailServerPrereqEl.classList.add('hidden');
    }
}

async function connectEmailProvider() {
    const response = await window.authenticatedFetch('/api/email/connect-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'gmail' })
    });
    if (!response.ok) {
        const text = await response.text().catch(() => 'Unable to create Gmail connect URL');
        if (text.includes('Missing Google OAuth') || response.status === 500) {
            throw new Error('Server OAuth credentials are not configured. Add GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET to your .env file, then restart the server.');
        }
        throw new Error(text);
    }

    const data = await response.json();
    if (!data?.connect_url) {
        throw new Error('Missing Gmail connect URL');
    }

    window.location.href = data.connect_url;
}

async function disconnectEmailProvider() {
    const response = await window.authenticatedFetch('/api/email/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) {
        const text = await response.text().catch(() => 'Unable to disconnect Gmail');
        throw new Error(text);
    }

    await loadEmailProviderStatus();
}

function sanitizeFilenamePart(value, fallback = 'profile') {
    const normalized = String(value || '').trim();
    if (!normalized) return fallback;
    const cleaned = normalized
        .replace(/[^a-zA-Z0-9_-]+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
    return cleaned || fallback;
}

async function exportProfileSettings() {
    if (!window.authenticatedFetch) {
        showTemporaryStatus(settingsStatus, 'Authentication is not ready. Please refresh.', true, 4000);
        return;
    }

    showTemporaryStatus(settingsStatus, 'Exporting profile settings...', false, 0);
    try {
        const response = await window.authenticatedFetch('/api/profile-settings/export', {
            method: 'GET'
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Export failed: ${response.status} ${errorText}`);
        }

        const exportData = await response.json();
        const profileName = sanitizeFilenamePart(exportData?.profile?.display_name, 'profile');
        const dateStamp = new Date().toISOString().slice(0, 10);
        const filename = `bravo_profile_settings_${profileName}_${dateStamp}.json`;

        const jsonText = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonText], { type: 'application/json' });
        const blobUrl = window.URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);

        showTemporaryStatus(settingsStatus, 'Profile settings export complete.', false, 4000);
    } catch (error) {
        console.error('Error exporting profile settings:', error);
        showTemporaryStatus(settingsStatus, `Export failed: ${error.message}`, true, 5000);
    }
}

async function importProfileSettingsFromText(fileText) {
    if (!window.authenticatedFetch) {
        showTemporaryStatus(settingsStatus, 'Authentication is not ready. Please refresh.', true, 4000);
        return;
    }

    let parsed;
    try {
        parsed = JSON.parse(fileText);
    } catch (e) {
        showTemporaryStatus(settingsStatus, 'Invalid JSON file. Please choose a valid export file.', true, 5000);
        return;
    }

    const sourceName = parsed?.profile?.display_name || parsed?.profile?.aac_user_id || 'unknown profile';
    const confirmed = window.confirm(
        `Import settings from "${sourceName}" into the currently selected profile? This will overwrite matching settings sections.`
    );
    if (!confirmed) {
        showTemporaryStatus(settingsStatus, 'Import cancelled.', false, 2500);
        return;
    }

    showTemporaryStatus(settingsStatus, 'Importing profile settings...', false, 0);
    try {
        const response = await window.authenticatedFetch('/api/profile-settings/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parsed)
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Import failed: ${response.status} ${errorText}`);
        }

        const result = await response.json();
        const importedSections = Array.isArray(result.imported_sections) ? result.imported_sections : [];
        await loadSettings();
        showTemporaryStatus(
            settingsStatus,
            importedSections.length > 0
                ? `Import complete: ${importedSections.join(', ')}`
                : 'Import complete.',
            false,
            5000
        );
    } catch (error) {
        console.error('Error importing profile settings:', error);
        showTemporaryStatus(settingsStatus, `Import failed: ${error.message}`, true, 6000);
    }
}

async function handleImportProfileSettingsFileSelection(event) {
    const file = event?.target?.files?.[0];
    if (!file) {
        return;
    }

    try {
        const fileText = await file.text();
        await importProfileSettingsFromText(fileText);
    } catch (error) {
        console.error('Error reading import file:', error);
        showTemporaryStatus(settingsStatus, 'Could not read import file.', true, 5000);
    } finally {
        // Allow selecting the same file again after import.
        event.target.value = '';
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
    const newApplicationVolume = applicationVolumeSlider ? parseInt(applicationVolumeSlider.value) : 8;
    const newLLMOptions = LLMOptionsInput.value; 
    const newFreestyleOptions = FreestyleOptionsInput.value;
    console.log('DEBUG FreestyleOptions - Save value:', newFreestyleOptions);
    const newTapWordsRows = tapWordsRowsInput ? tapWordsRowsInput.value : '';
    const newTapPhrasesRows = tapPhrasesRowsInput ? tapPhrasesRowsInput.value : '';
    const newTapDynamicRows = tapDynamicRowsInput ? tapDynamicRowsInput.value : '';
    const newUseHybridPages = newTapDynamicRows !== '' && parseInt(newTapDynamicRows) > 0;
    const newScanLoopLimit = scanLoopLimitInput.value;
    const newScanMode = scanModeInput ? scanModeInput.value : 'auto';
    
    // Determine Interface Mode
    let newUseTapInterface = false;

    if (interfaceTapInput && interfaceTapInput.checked) {
        newUseTapInterface = true;
    } else {
        newUseTapInterface = false;
    }

    // const newScanningOff = ScanningOffInput.checked; // Removed from UI
    const newSummaryOff = SummaryOffInput.checked;
    const newAutoClean = autoCleanInput.checked;
    const newDisplaySplash = displaySplashInput.checked;
    const newDisplaySplashTime = displaySplashTimeInput.value ? parseInt(displaySplashTimeInput.value) : 3000;
    const newEnableMoodSelection = enableMoodSelectionInput.checked;
    // const newUseTapInterface = useTapInterfaceInput.checked; // Removed from UI
    const newEnablePictograms = enablePictogramsInput ? enablePictogramsInput.checked : true;
    const newDisableTapPictograms = disableTapPictogramsInput ? disableTapPictogramsInput.checked : false;
    const newScanningOff = ScanningOffInput ? ScanningOffInput.checked : false;
    const newWaitForSwitchToScan = waitForSwitchToScanInput ? waitForSwitchToScanInput.checked : false;
    const newPlayWaitForSwitchChime = playWaitForSwitchChimeInput ? playWaitForSwitchChimeInput.checked : false;
    const newEnableSightWords = enableSightWordsInput.checked;
    const newSightWordGradeLevel = sightWordGradeLevelInput.value;
    // Keep legacy selected_tts_voice_name aligned to the default partner voice.
    const newSelectedTtsVoice = defaultPartnerVoiceSelect
        ? defaultPartnerVoiceSelect.value
        : (ttsVoiceSelect ? ttsVoiceSelect.value : null);
    const newUserLanguage = userLanguageSelect ? userLanguageSelect.value : 'en-US';
    const newDefaultPartnerLanguage = defaultPartnerLanguageSelect ? defaultPartnerLanguageSelect.value : 'en-US';
    const newDefaultPartnerVoice = defaultPartnerVoiceSelect ? defaultPartnerVoiceSelect.value : '';
    const newVoiceStyle = getSelectedVoiceStyle();
    // Read from table-based location override languages
    const locationOverrideTableMap = getLocationOverrideLanguagesFromTable();
    const newLocationOverrideLanguages = Object.keys(locationOverrideTableMap);
    const newLocationOverrideVoices = locationOverrideTableMap;
    const newGridColumns = gridColumnsSlider ? parseInt(gridColumnsSlider.value) : 6;
    const newToolbarPIN = toolbarPINInput ? toolbarPINInput.value.trim() : null;
    const newSpellLetterOrder = spellLetterOrderSelect ? spellLetterOrderSelect.value : 'alphabetical';
    const newVocabularyLevel = vocabularyLevelSelect ? vocabularyLevelSelect.value : 'functional';
    const newMascot = mascotSelect ? mascotSelect.value : 'buddy';
    
    console.log(`DEBUG vocabularyLevel - Save value:
        - vocabularyLevelSelect exists: ${!!vocabularyLevelSelect}
        - vocabularyLevelSelect.value: ${vocabularyLevelSelect ? vocabularyLevelSelect.value : 'N/A'}
        - newVocabularyLevel: ${newVocabularyLevel}`);

    console.log(`Save Settings Debug - Spell Letter Order:
        - spellLetterOrderSelect exists: ${!!spellLetterOrderSelect}
        - spellLetterOrderSelect.value: ${spellLetterOrderSelect ? spellLetterOrderSelect.value : 'N/A'}
        - newSpellLetterOrder: ${newSpellLetterOrder}`);
    
    console.log(`Save Settings Debug:
        - gridColumnsSlider exists: ${!!gridColumnsSlider}
        - gridColumnsSlider.value: ${gridColumnsSlider ? gridColumnsSlider.value : 'N/A'}
        - newGridColumns (parsed): ${newGridColumns}`);

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
      if (newLLMOptions === '' || isNaN(parseInt(newLLMOptions)) || parseInt(newLLMOptions) < 0 || parseInt(newLLMOptions) > 50) {
          settingsStatus.textContent = 'Invalid LLM Options. Must be a number (e.g., 0-50).';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
     if (newFreestyleOptions !== '' && (isNaN(parseInt(newFreestyleOptions)) || parseInt(newFreestyleOptions) < 1 || parseInt(newFreestyleOptions) > 50)) {
        settingsStatus.textContent = 'Invalid Freestyle Options. Must be a number (e.g., 1-50).';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (newTapWordsRows !== '' && (isNaN(parseInt(newTapWordsRows)) || parseInt(newTapWordsRows) < 1 || parseInt(newTapWordsRows) > 10)) {
        settingsStatus.textContent = 'Invalid Tap Words Rows. Must be a number between 1 and 10.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (newTapPhrasesRows !== '' && (isNaN(parseInt(newTapPhrasesRows)) || parseInt(newTapPhrasesRows) < 0 || parseInt(newTapPhrasesRows) > 10)) {
        settingsStatus.textContent = 'Invalid Tap Phrases Rows. Must be a number between 0 and 10.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (newTapDynamicRows !== '' && (isNaN(parseInt(newTapDynamicRows)) || parseInt(newTapDynamicRows) < 0 || parseInt(newTapDynamicRows) > 10)) {
        settingsStatus.textContent = 'Invalid Tap Dynamic Rows. Must be a number between 0 and 10.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (newScanLoopLimit !== '' && (isNaN(parseInt(newScanLoopLimit)) || parseInt(newScanLoopLimit) < 0 || parseInt(newScanLoopLimit) > 10)) {
        settingsStatus.textContent = 'Invalid Scan Loop Limit. Must be 0 (unlimited) or 1-10.';
        settingsStatus.style.color = 'red'; setTimeout(() => { settingsStatus.textContent = ''; }, 4000); return;
    }
    if (!['auto', 'step'].includes(newScanMode)) {
        settingsStatus.textContent = 'Invalid Scanning Mode. Must be Auto or Step.';
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
    if (!newDefaultPartnerVoice && availableVoices.length > 0) { // Always require a default partner voice when voices are available
        showTemporaryStatus(settingsStatus, 'Please select a Default Partner Voice (required for announcements).', true, 4000); return;
    }
    if (!newUserLanguage) {
        showTemporaryStatus(settingsStatus, 'Please select a user language.', true, 4000); return;
    }
    if (!newDefaultPartnerLanguage) {
        showTemporaryStatus(settingsStatus, 'Please select a default partner language.', true, 4000); return;
    }
    const missingOverrideVoices = newLocationOverrideLanguages.filter(locale => !newLocationOverrideVoices[locale]);
    if (missingOverrideVoices.length > 0) {
        showTemporaryStatus(settingsStatus, `Select voices for override language(s): ${missingOverrideVoices.join(', ')}`, true, 5000); return;
    }
    // Provider selection is always valid since it has default values
    // Remove the old LLM model validation

    const settingsToSave = {
        scanDelay: parseInt(newDelay),
        wakeWordInterjection: newInterjection,
        wakeWordName: newName,
        CountryCode: newCountryCode,
        speech_rate: parseInt(newSpeechRate),
        applicationVolume: newApplicationVolume,
        LLMOptions: parseInt(newLLMOptions),
        FreestyleOptions: newFreestyleOptions !== '' ? parseInt(newFreestyleOptions) : null,
        tapWordsRows: newTapWordsRows !== '' ? parseInt(newTapWordsRows) : 4,
        tapPhrasesRows: newTapPhrasesRows !== '' ? parseInt(newTapPhrasesRows) : 0,
        useHybridPages: newUseHybridPages,
        tapDynamicRows: newTapDynamicRows !== '' ? parseInt(newTapDynamicRows) : 0,
        scanLoopLimit: newScanLoopLimit !== '' ? parseInt(newScanLoopLimit) : 0,
        scanMode: newScanMode,
        ScanningOff: newScanningOff,    
        waitForSwitchToScan: newWaitForSwitchToScan,
        playWaitForSwitchChime: newPlayWaitForSwitchChime,
        SummaryOff: newSummaryOff,
        autoClean: newAutoClean,
        displaySplash: newDisplaySplash,
        displaySplashTime: newDisplaySplashTime,
        enableMoodSelection: newEnableMoodSelection,
        useTapInterface: newUseTapInterface,
        enablePictograms: newEnablePictograms,
        disableTapPictograms: newDisableTapPictograms,
        enableSightWords: newEnableSightWords,
        sightWordGradeLevel: newSightWordGradeLevel,
        selected_tts_voice_name: newDefaultPartnerVoice,
        userLanguage: newUserLanguage,
        defaultPartnerLanguage: newDefaultPartnerLanguage,
        defaultPartnerVoice: newDefaultPartnerVoice,
        voice_style: newVoiceStyle,
        locationOverrideLanguages: newLocationOverrideLanguages,
        locationOverrideVoices: newLocationOverrideVoices,
        gridColumns: newGridColumns, // Add gridColumns to save payload
        spellLetterOrder: newSpellLetterOrder, // Add spell letter order setting
        vocabularyLevel: newVocabularyLevel, // Add vocabulary level setting
        mascot: newMascot
    };
    console.log('DEBUG FreestyleOptions - Payload value:', settingsToSave.FreestyleOptions);
    console.log('DEBUG enablePictograms - Payload value:', settingsToSave.enablePictograms);
    console.log('DEBUG spellLetterOrder - Payload value:', settingsToSave.spellLetterOrder);
    console.log('DEBUG vocabularyLevel - Payload value:', settingsToSave.vocabularyLevel);

    console.log("Saving settings:", settingsToSave);
    console.log("FULL PAYLOAD:", JSON.stringify(settingsToSave, null, 2));
    markAdminSaving();
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
        console.log('DEBUG enablePictograms - Server response value:', currentSettings.enablePictograms);
        console.log('DEBUG vocabularyLevel - Server response value:', currentSettings.vocabularyLevel);
        console.log('DEBUG spellLetterOrder - Server response value:', currentSettings.spellLetterOrder);
        
        if (scanDelayInput) scanDelayInput.value = currentSettings.scanDelay || '';
        if (wakeWordInterjectionInput) wakeWordInterjectionInput.value = currentSettings.wakeWordInterjection || '';
        if (wakeWordNameInput) wakeWordNameInput.value = currentSettings.wakeWordName || '';
        if (CountryCodeInput) CountryCodeInput.value = currentSettings.CountryCode || '';
        if (speechRateInput) speechRateInput.value = currentSettings.speech_rate || 180;
        if (applicationVolumeSlider && volumeDisplay) {
            const volume = currentSettings.applicationVolume !== undefined ? currentSettings.applicationVolume : 8;
            applicationVolumeSlider.value = volume;
            volumeDisplay.textContent = `${volume}/10`;
        }
        if (LLMOptionsInput) {
            LLMOptionsInput.value = currentSettings.LLMOptions !== null && currentSettings.LLMOptions !== undefined
                ? currentSettings.LLMOptions
                : '';
        }
        if (FreestyleOptionsInput) {
            console.log('DEBUG FreestyleOptions - Reload value:', currentSettings.FreestyleOptions);
            FreestyleOptionsInput.value = currentSettings.FreestyleOptions !== null && currentSettings.FreestyleOptions !== undefined ? currentSettings.FreestyleOptions : '';
        }
        if (tapWordsRowsInput) {
            tapWordsRowsInput.value = currentSettings.tapWordsRows !== null && currentSettings.tapWordsRows !== undefined ? currentSettings.tapWordsRows : 4;
        }
        if (tapPhrasesRowsInput) {
            tapPhrasesRowsInput.value = currentSettings.tapPhrasesRows !== null && currentSettings.tapPhrasesRows !== undefined ? currentSettings.tapPhrasesRows : 0;
        }
        if (tapDynamicRowsInput) {
            tapDynamicRowsInput.value = currentSettings.tapDynamicRows !== undefined ? currentSettings.tapDynamicRows : 0;
        }
        updateStaticRowsDisplay();
        if (scanLoopLimitInput) scanLoopLimitInput.value = currentSettings.scanLoopLimit !== undefined ? currentSettings.scanLoopLimit : 0;
        if (scanModeInput) scanModeInput.value = currentSettings.scanMode === 'step' ? 'step' : 'auto';
        if (ScanningOffInput) ScanningOffInput.checked = currentSettings.ScanningOff || false;
        if (waitForSwitchToScanInput) waitForSwitchToScanInput.checked = currentSettings.waitForSwitchToScan || false;
        if (playWaitForSwitchChimeInput) playWaitForSwitchChimeInput.checked = currentSettings.playWaitForSwitchChime || false;
        if (SummaryOffInput) SummaryOffInput.checked = currentSettings.SummaryOff || false;
        if (autoCleanInput) autoCleanInput.checked = currentSettings.autoClean || false;
        if (displaySplashInput) displaySplashInput.checked = currentSettings.displaySplash || false;
        if (displaySplashTimeInput) displaySplashTimeInput.value = currentSettings.displaySplashTime || 3000;
        if (enableMoodSelectionInput) enableMoodSelectionInput.checked = currentSettings.enableMoodSelection || false;
        if (enablePictogramsInput) enablePictogramsInput.checked = currentSettings.enablePictograms !== false;
        if (enableSightWordsInput) enableSightWordsInput.checked = currentSettings.enableSightWords !== false;
        if (sightWordGradeLevelInput) sightWordGradeLevelInput.value = currentSettings.sightWordGradeLevel || 'pre_k';
        if (userLanguageSelect) userLanguageSelect.value = currentSettings.userLanguage || 'en-US';
        if (defaultPartnerLanguageSelect) defaultPartnerLanguageSelect.value = currentSettings.defaultPartnerLanguage || 'en-US';
        if (locationOverrideLanguagesSelect) {
            setSelectedMultiValues(locationOverrideLanguagesSelect, currentSettings.locationOverrideLanguages || []);
        }
        refreshLanguageDependentVoiceControls();
        if (defaultPartnerVoiceSelect) {
            defaultPartnerVoiceSelect.value = currentSettings.defaultPartnerVoice || currentSettings.selected_tts_voice_name || '';
        }
        setSelectedVoiceStyle(currentSettings.voice_style || 'adult');
        if (ttsVoiceSelect) ttsVoiceSelect.value = currentSettings.defaultPartnerVoice || currentSettings.selected_tts_voice_name || '';
        if (gridColumnsSlider && currentSettings.gridColumns !== undefined) {
            gridColumnsSlider.value = currentSettings.gridColumns;
        }
        // Update spellLetterOrder select
        if (spellLetterOrderSelect) {
            const savedValue = currentSettings.spellLetterOrder || 'alphabetical';
            console.log('DEBUG spellLetterOrder - Setting dropdown to:', savedValue);
            spellLetterOrderSelect.value = savedValue;
            console.log('DEBUG spellLetterOrder - Dropdown now shows:', spellLetterOrderSelect.value);
        }
        // Update vocabularyLevel select
        if (vocabularyLevelSelect) {
            vocabularyLevelSelect.value = currentSettings.vocabularyLevel || 'functional';
        }
        // Update mascot select
        if (mascotSelect) {
            mascotSelect.value = currentSettings.mascot || 'buddy';
        }

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
        
        // Update sight word service settings if the function exists
        if (typeof window.updateSightWordSettings === 'function') {
            window.updateSightWordSettings(currentSettings);
        }

        markAdminSaved();
        
        showTemporaryStatus(settingsStatus, 'Settings saved successfully!', false);

    } catch (error) {
        console.error('Error saving settings:', error);
        showTemporaryStatus(settingsStatus, `Error saving: ${error.message}`, true, 5000);
    }
}

/**
 * Tests the Default Partner Voice
 */
async function testDefaultPartnerVoice() {
    if (!defaultPartnerVoiceSelect) return;
    const selectedVoice = defaultPartnerVoiceSelect.value;
    const testText = "This is a test of the Default Partner Voice.";
    if (!selectedVoice) {
        showTemporaryStatus(settingsStatus, "Please select a Default Partner Voice to test.", true, 3000);
        return;
    }

    // Synchronously unlock browser speech synthesis inside user gesture before the async fetch
    if (window.speechSynthesis) {
        try {
            const unlockUtterance = new SpeechSynthesisUtterance('');
            window.speechSynthesis.speak(unlockUtterance);
        } catch (e) {
            console.warn('[TTS Fallback] Failed to play silent unlock utterance:', e);
        }
    }

    showTemporaryStatus(settingsStatus, `Testing voice: ${selectedVoice}...`, false, 0);
    try {
        const response = await window.authenticatedFetch('/api/test-tts-voice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                voice_name: selectedVoice, 
                text: testText,
                voice_style: getSelectedVoiceStyle()
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `Test failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        if (result.audio_url) {
            const audioResponse = await fetch(result.audio_url);
            if (!audioResponse.ok) throw new Error(`Failed to fetch audio file: ${audioResponse.status}`);
            const audioArrayBuffer = await audioResponse.arrayBuffer();
            await playTestAudio(audioArrayBuffer, result.sample_rate || 22050);
            showTemporaryStatus(settingsStatus, "Default Partner Voice tested successfully!", false, 3000);
        } else if (result.audio_data) {
            const binaryString = window.atob(result.audio_data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            await playTestAudio(bytes.buffer, result.sample_rate || 22050);
            showTemporaryStatus(settingsStatus, "Default Partner Voice tested successfully!", false, 3000);
        } else {
            throw new Error('No playable audio returned from test endpoint.');
        }
    } catch (error) {
        console.error('Error testing voice:', error);
        try {
            console.log('[TTS Fallback] Attempting browser speech fallback for:', selectedVoice);
            await handleVoiceTestFailure(error, testText, selectedVoice, settingsStatus, 'Default Partner Voice tested successfully');
        } catch (fallbackError) {
            console.error('[TTS Fallback] Fallback failed:', fallbackError);
            showTemporaryStatus(settingsStatus, `Error testing voice: ${fallbackError.message}`, true, 4000);
        }
    }
}

/**
 * Tests a specific Location Override Voice
 */
async function testLocationOverrideVoice(voiceSelect) {
    if (!voiceSelect) return;
    const selectedVoice = voiceSelect.value;
    const testText = "This is a test of the location override voice.";
    if (!selectedVoice) {
        alert("Please select a voice to test.");
        return;
    }

    // Synchronously unlock browser speech synthesis inside user gesture before the async fetch
    if (window.speechSynthesis) {
        try {
            const unlockUtterance = new SpeechSynthesisUtterance('');
            window.speechSynthesis.speak(unlockUtterance);
        } catch (e) {
            console.warn('[TTS Fallback] Failed to play silent unlock utterance:', e);
        }
    }

    try {
        showTemporaryStatus(settingsStatus, `Testing voice: ${selectedVoice}...`, false, 0);
        const response = await window.authenticatedFetch('/api/test-tts-voice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                voice_name: selectedVoice, 
                text: testText,
                voice_style: getSelectedVoiceStyle()
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `Test failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        if (result.audio_url) {
            const audioResponse = await fetch(result.audio_url);
            if (!audioResponse.ok) throw new Error(`Failed to fetch audio file: ${audioResponse.status}`);
            const audioArrayBuffer = await audioResponse.arrayBuffer();
            await playTestAudio(audioArrayBuffer, result.sample_rate || 22050);
            showTemporaryStatus(settingsStatus, "Location override voice tested successfully!", false, 3000);
        } else if (result.audio_data) {
            const binaryString = window.atob(result.audio_data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            await playTestAudio(bytes.buffer, result.sample_rate || 22050);
            showTemporaryStatus(settingsStatus, "Location override voice tested successfully!", false, 3000);
        } else {
            throw new Error('No playable audio returned from test endpoint.');
        }
    } catch (error) {
        console.error('Error testing voice:', error);
        try {
            console.log('[TTS Fallback] Attempting browser speech fallback for:', selectedVoice);
            await handleVoiceTestFailure(error, testText, selectedVoice, settingsStatus, 'Location override voice tested successfully');
        } catch (fallbackError) {
            console.error('[TTS Fallback] Fallback failed:', fallbackError);
            showTemporaryStatus(settingsStatus, `Error testing voice: ${fallbackError.message}`, true, 4000);
        }
    }
}

/**
 * Tests the currently selected TTS voice.
 */
async function testSelectedVoice() {
    if (!ttsVoiceSelect || !ttsVoiceStatus) return;
    const selectedVoice = ttsVoiceSelect.value;
    const testText = "This is a test of the selected voice.";
    if (!selectedVoice) {
        showTemporaryStatus(ttsVoiceStatus, "Please select a voice to test.", true);
        return;
    }

    // Synchronously unlock browser speech synthesis inside user gesture before the async fetch
    if (window.speechSynthesis) {
        try {
            const unlockUtterance = new SpeechSynthesisUtterance('');
            window.speechSynthesis.speak(unlockUtterance);
        } catch (e) {
            console.warn('[TTS Fallback] Failed to play silent unlock utterance:', e);
        }
    }

    showTemporaryStatus(ttsVoiceStatus, `Testing voice: ${selectedVoice}...`, false, 0);
    try {
        // Use the /api/test-tts-voice endpoint which is specifically for voice testing
        const response = await window.authenticatedFetch('/api/test-tts-voice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                voice_name: selectedVoice, 
                text: testText,
                voice_style: getSelectedVoiceStyle()
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
        try {
            console.log('[TTS Fallback] Attempting browser speech fallback for:', selectedVoice);
            await handleVoiceTestFailure(error, testText, selectedVoice, ttsVoiceStatus, 'Test voice played successfully');
        } catch (fallbackError) {
            console.error('[TTS Fallback] Fallback failed:', fallbackError);
            showTemporaryStatus(ttsVoiceStatus, `Error testing voice: ${fallbackError.message}`, true, 5000);
        }
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
        markAdminSaving();
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
        markAdminSaved();
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
        // The following are already assigned globally as const, no need to re-assign:
        // wakeWordInterjectionInput, wakeWordNameInput, CountryCodeInput, speechRateInput,
        // LLMOptionsInput, ScanningOffInput, SummaryOffInput, ttsVoiceSelect,
        // testTtsVoiceButton, ttsVoiceStatus, llmProviderSelect, saveSettingsButton.

        settingsStatus = document.getElementById('settings-status'); // This was 'let', so assign it.

        // Basic check for essential elements
        if (!saveSettingsButton || !settingsStatus) {
            console.error("CRITICAL ERROR: One or more essential DOM elements for admin_settings.js not found.");
            return;
        }

        // Add Event Listeners
        if (saveSettingsButton) saveSettingsButton.addEventListener('click', saveSettings);
        if (testTtsVoiceButton) testTtsVoiceButton.addEventListener('click', testSelectedVoice);
        const testDefaultPartnerVoiceButton = document.getElementById('testDefaultPartnerVoiceButton');
        if (testDefaultPartnerVoiceButton) testDefaultPartnerVoiceButton.addEventListener('click', testDefaultPartnerVoice);
        if (defaultPartnerLanguageSelect) defaultPartnerLanguageSelect.addEventListener('change', refreshLanguageDependentVoiceControls);
        voiceStyleInputs.forEach((input) => {
            input.addEventListener('change', refreshLanguageDependentVoiceControls);
        });
        if (addLocationOverrideRowButton) addLocationOverrideRowButton.addEventListener('click', addLocationOverrideRow);
        if (locationOverrideLanguagesSelect) locationOverrideLanguagesSelect.addEventListener('change', refreshLanguageDependentVoiceControls);
        if (refreshEmailStatusButton) {
            refreshEmailStatusButton.addEventListener('click', () => {
                loadEmailProviderStatus().catch((error) => {
                    showTemporaryStatus(settingsStatus, `Email status error: ${error.message}`, true, 4000);
                });
            });
        }
        if (connectEmailButton) {
            connectEmailButton.addEventListener('click', () => {
                connectEmailProvider().catch((error) => {
                    showTemporaryStatus(settingsStatus, `Email connect error: ${error.message}`, true, 4000);
                });
            });
        }
        if (disconnectEmailButton) {
            disconnectEmailButton.addEventListener('click', () => {
                disconnectEmailProvider().catch((error) => {
                    showTemporaryStatus(settingsStatus, `Email disconnect error: ${error.message}`, true, 4000);
                });
            });
        }
        if (exportProfileSettingsButton) {
            exportProfileSettingsButton.addEventListener('click', () => {
                exportProfileSettings().catch((error) => {
                    showTemporaryStatus(settingsStatus, `Export error: ${error.message}`, true, 4000);
                });
            });
        }
        if (importProfileSettingsButton && importProfileSettingsFileInput) {
            importProfileSettingsButton.addEventListener('click', () => {
                importProfileSettingsFileInput.click();
            });
            importProfileSettingsFileInput.addEventListener('change', handleImportProfileSettingsFileSelection);
        }
        
        // Words rows static calculation listeners
        if (tapWordsRowsInput) tapWordsRowsInput.addEventListener('input', updateStaticRowsDisplay);
        if (tapWordsRowsInput) tapWordsRowsInput.addEventListener('change', updateStaticRowsDisplay);
        if (tapDynamicRowsInput) tapDynamicRowsInput.addEventListener('input', updateStaticRowsDisplay);
        if (tapDynamicRowsInput) tapDynamicRowsInput.addEventListener('change', updateStaticRowsDisplay);


        // Initial data loading
        populateLanguageSelectors();
        await loadVoices();
        // Static provider selection - no need to populate dropdown
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
// --- Admin Toolbar Button Handlers ---
function setupAdminToolbarButtons() {
    const switchUserButton = document.getElementById('switch-user-button');
    const logoutButton = document.getElementById('logout-button');

    function handleSwitchUser() {
        console.log("Switching user profile. Clearing session and redirecting to auth page for profile selection.");
        // Only set flag to prevent auto-proceed with default user - keep user authenticated
        localStorage.setItem('bravoSkipDefaultUser', 'true');
        console.log('Set bravoSkipDefaultUser flag for profile selection');
        sessionStorage.clear();
        
        // Small delay to ensure localStorage is written before navigation
        setTimeout(() => {
            window.location.href = 'auth.html';
        }, 100);
    }

    function handleLogout() {
        console.log("Logging out. Clearing session and redirecting to auth page for login.");
        // Set both flags to prevent automatic re-login and auto-profile selection
        localStorage.setItem('bravoIntentionalLogout', 'true');
        localStorage.setItem('bravoSkipDefaultUser', 'true');
        console.log('Set bravoIntentionalLogout and bravoSkipDefaultUser flags');
        sessionStorage.clear();
        
        // Small delay to ensure localStorage is written before navigation
        setTimeout(() => {
            window.location.href = 'auth.html';
        }, 100);
    }

    if (switchUserButton) {
        switchUserButton.addEventListener('click', handleSwitchUser);
        console.log("admin_settings.js: Switch User button event listener added");
    }
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
        console.log("admin_settings.js: Logout button event listener added");
    }
}

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
    setupAdminToolbarButtons(); // Add toolbar button functionality
});