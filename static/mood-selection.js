/**
 * Mood Selection Functionality
 * Displays a mood selection interface at session start when enabled
 */

// Predefined mood options with emojis
const MOOD_OPTIONS = [
    { name: 'Happy', emoji: '😊' },
    { name: 'Sad', emoji: '😢' },
    { name: 'Excited', emoji: '🤩' },
    { name: 'Calm', emoji: '😌' },
    { name: 'Angry', emoji: '😠' },
    { name: 'Silly', emoji: '🤪' },
    { name: 'Tired', emoji: '😴' },
    { name: 'Anxious', emoji: '😰' },
    { name: 'Confused', emoji: '😕' },
    { name: 'Surprised', emoji: '😲' },
    { name: 'Proud', emoji: '😎' },
    { name: 'Worried', emoji: '😟' },
    { name: 'Cranky', emoji: '😤' },
    { name: 'Peaceful', emoji: '🕊️' },
    { name: 'Playful', emoji: '😄' },
    { name: 'Frustrated', emoji: '😫' },
    { name: 'Curious', emoji: '🤔' },
    { name: 'Grateful', emoji: '🙏' },
    { name: 'Lonely', emoji: '😔' },
    { name: 'Content', emoji: '😊' }
];

class MoodSelection {
    constructor() {
        this.selectedMood = null;
        this.onComplete = null;
        this.moodOverlay = null;
        
        // Scanning variables (similar to gridpage.js)
        this.scanningInterval = null;
        this.currentButtonIndex = -1;
        this.currentlyScannedButton = null;
        this.moodButtons = [];
        this.defaultDelay = 3500; // Default scanning delay
        this.isScanning = false;
        this.ScanningOff = false; // Will be loaded from settings
        
        // Gamepad variables
        this.gamepadIndex = null;
        this.gamepadPollInterval = null;
        this.lastGamepadInputTime = 0;
        this.gamepadEnabled = false; // Track if we should handle gamepad input
    }

    /**
     * Shows the mood selection interface
     * @param {Function} onComplete - Callback function called when mood selection is complete
     */
    async show(onComplete) {
        this.onComplete = onComplete;
        
        // Check if mood selection is enabled in settings
        const isEnabled = await this.isMoodSelectionEnabled();
        if (!isEnabled) {
            console.log('Mood selection is disabled in settings');
            if (this.onComplete) this.onComplete(null);
            return;
        }

        // Check if mood was already set this session
        const existingMood = sessionStorage.getItem('currentSessionMood');
        if (existingMood) {
            console.log('Mood already set for this session:', existingMood);
            if (this.onComplete) this.onComplete(existingMood);
            return;
        }

        this.createMoodInterface();
    }

    /**
     * Checks if mood selection is enabled in settings
     */
    async isMoodSelectionEnabled() {
        try {
            // Check if authenticatedFetch is available
            const fetchFunction = window.authenticatedFetch || fetch;
            
            const response = await fetchFunction('/api/settings', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (response.ok) {
                const settings = await response.json();
                
                // Load scanning settings
                this.ScanningOff = settings.ScanningOff === true;
                this.defaultDelay = settings.scanDelay || 3500;
                
                return settings.enableMoodSelection === true;
            }
        } catch (error) {
            console.error('Failed to check mood selection setting:', error);
        }
        return false; // Default to disabled if we can't check
    }

    /**
     * Creates the mood selection interface
     */
    createMoodInterface() {
        // Remove existing overlay if it exists
        this.removeMoodInterface();

        // Create overlay
        this.moodOverlay = document.createElement('div');
        this.moodOverlay.className = 'mood-selection-overlay';
        this.moodOverlay.id = 'mood-selection-overlay';

        // Create container
        const container = document.createElement('div');
        container.className = 'mood-selection-container';

        // Create title
        const title = document.createElement('h2');
        title.className = 'mood-selection-title';
        title.textContent = 'How are you feeling today?';

        // Create subtitle
        const subtitle = document.createElement('p');
        subtitle.className = 'mood-selection-subtitle';
        subtitle.textContent = 'Select your current mood to help personalize your experience';

        // Create mood grid
        const moodGrid = document.createElement('div');
        moodGrid.className = 'mood-grid';

        // Add mood buttons
        MOOD_OPTIONS.forEach(mood => {
            const button = document.createElement('button');
            button.className = 'mood-button';
            button.setAttribute('data-mood', mood.name);
            
            const emoji = document.createElement('div');
            emoji.className = 'mood-emoji';
            emoji.textContent = mood.emoji;
            
            const name = document.createElement('div');
            name.textContent = mood.name;
            
            button.appendChild(emoji);
            button.appendChild(name);
            
            button.addEventListener('click', () => this.selectMood(mood.name, button));
            moodGrid.appendChild(button);
        });

        // Create action buttons (only Skip button now)
        const actions = document.createElement('div');
        actions.className = 'mood-actions';

        const skipButton = document.createElement('button');
        skipButton.className = 'mood-action-button mood-skip-button';
        skipButton.textContent = 'Skip';
        skipButton.addEventListener('click', () => this.skipMoodSelection());

        actions.appendChild(skipButton);

        // Assemble the interface
        container.appendChild(title);
        container.appendChild(subtitle);
        container.appendChild(moodGrid);
        container.appendChild(actions);
        this.moodOverlay.appendChild(container);

        // Add to page
        document.body.appendChild(this.moodOverlay);

        // Store references to buttons for scanning
        this.moodButtons = [...moodGrid.querySelectorAll('.mood-button'), skipButton];

        // Focus the modal container to capture keyboard events
        container.setAttribute('tabindex', '-1');
        
        // Add keydown event directly to the container to ensure we catch spacebar
        container.addEventListener('keydown', (event) => this.handleKeyPress(event));
        
        container.focus();

        // Setup gamepad support
        this.setupGamepadSupport();

        // Start scanning if enabled
        if (!this.ScanningOff) {
            console.log('Starting mood selection scanning...');
            this.startScanning();
        } else {
            // Focus first mood button for accessibility when scanning is off
            const firstButton = moodGrid.querySelector('.mood-button');
            if (firstButton) {
                firstButton.focus();
            }
        }
    }

    /**
     * Handles mood selection
     * @param {string} moodName - The selected mood name
     * @param {HTMLElement} buttonElement - The clicked button element
     */
    selectMood(moodName, buttonElement) {
        console.log('Mood selected:', moodName);
        
        // Stop scanning when mood is selected
        this.stopScanning();
        
        // Remove previous selection
        const previousSelected = this.moodOverlay.querySelector('.mood-button.selected');
        if (previousSelected) {
            previousSelected.classList.remove('selected');
        }

        // Add selection to clicked button
        buttonElement.classList.add('selected');
        this.selectedMood = moodName;

        // Show brief confirmation then proceed automatically
        setTimeout(() => {
            this.completeMoodSelection();
        }, 500); // Brief delay to show selection feedback
    }

    /**
     * Completes the mood selection process
     */
    async completeMoodSelection() {
        if (!this.selectedMood) {
            console.warn('No mood selected');
            return;
        }

        try {
            // Save mood to session storage
            sessionStorage.setItem('currentSessionMood', this.selectedMood);

            // Save mood to user info (optional - persists across sessions)
            await this.saveMoodToSettings(this.selectedMood);

            console.log('Mood selection completed:', this.selectedMood);
            
            // Remove interface
            this.removeMoodInterface();

            // Call completion callback
            if (this.onComplete) {
                this.onComplete(this.selectedMood);
            }
        } catch (error) {
            console.error('Error completing mood selection:', error);
            // Continue anyway with session storage
            this.removeMoodInterface();
            if (this.onComplete) {
                this.onComplete(this.selectedMood);
            }
        }
    }

    /**
     * Skips the mood selection
     */
    skipMoodSelection() {
        console.log('Mood selection skipped');
        
        // Set session storage to indicate mood was skipped
        sessionStorage.setItem('currentSessionMood', 'none');
        
        // Remove interface
        this.removeMoodInterface();

        // Call completion callback with null
        if (this.onComplete) {
            this.onComplete(null);
        }
    }

    /**
     * Saves the selected mood to user info
     * @param {string} mood - The selected mood
     */
    async saveMoodToSettings(mood) {
        try {
            const fetchFunction = window.authenticatedFetch || fetch;
            
            // First get current user info to preserve it
            const getCurrentResponse = await fetchFunction('/api/user-info', {
                method: 'GET',
                credentials: 'include'
            });
            
            let currentUserInfo = "";
            if (getCurrentResponse.ok) {
                const current = await getCurrentResponse.json();
                currentUserInfo = current.userInfo || "";
            }
            
            // Save mood along with existing user info
            const response = await fetchFunction('/api/user-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    userInfo: currentUserInfo,
                    currentMood: mood
                })
            });

            if (!response.ok) {
                console.warn('Failed to save mood to user info:', response.statusText);
            }
        } catch (error) {
            console.warn('Error saving mood to user info:', error);
        }
    }

    /**
     * Start scanning through mood options and Skip button
     */
    startScanning() {
        if (this.ScanningOff || this.scanningInterval) {
            return;
        }

        this.currentButtonIndex = 0;
        this.isScanning = true;
        this.scanStep();
    }

    /**
     * Stop scanning
     */
    stopScanning() {
        if (this.scanningInterval) {
            clearTimeout(this.scanningInterval);
            this.scanningInterval = null;
        }
        
        // Remove highlight from currently scanned button
        if (this.currentlyScannedButton) {
            this.currentlyScannedButton.classList.remove('scan-highlight', 'scanning');
            this.currentlyScannedButton.style.border = '';
            this.currentlyScannedButton = null;
        }
        
        // Also remove highlights from all buttons as backup
        this.moodButtons.forEach(button => {
            button.classList.remove('scan-highlight', 'scanning');
            button.style.border = '';
        });
        
        this.isScanning = false;
    }

    /**
     * Scanning step - highlights current button and speaks it
     */
    scanStep() {
        if (this.ScanningOff || !this.moodButtons || this.moodButtons.length === 0) {
            return;
        }

        // Clear previous highlights and remove from currently scanned button
        if (this.currentlyScannedButton) {
            this.currentlyScannedButton.classList.remove('scan-highlight', 'scanning');
            this.currentlyScannedButton.style.border = '';
        }

        // Highlight current button
        this.currentlyScannedButton = this.moodButtons[this.currentButtonIndex];
        if (this.currentlyScannedButton) {
            this.currentlyScannedButton.classList.add('scan-highlight', 'scanning');
            this.currentlyScannedButton.style.border = '3px solid #007bff';
            
            console.log('Scanning mood button:', this.currentButtonIndex, this.currentlyScannedButton.textContent || this.currentlyScannedButton.getAttribute('data-mood'));
            
            // Speak the button text
            this.speakAndHighlight(this.currentlyScannedButton);
        }

        // Move to next button
        this.currentButtonIndex = (this.currentButtonIndex + 1) % this.moodButtons.length;

        // Schedule next scan step
        this.scanningInterval = setTimeout(() => {
            this.scanStep();
        }, this.defaultDelay);
    }

    /**
     * Speak button text for auditory feedback
     */
    speakAndHighlight(button) {
        if (!button) return;

        let textToSpeak;
        if (button.classList.contains('mood-button')) {
            const moodName = button.getAttribute('data-mood');
            textToSpeak = `Mood: ${moodName}`;
        } else if (button.classList.contains('mood-skip-button')) {
            textToSpeak = 'Skip mood selection';
        } else {
            textToSpeak = button.textContent || button.innerText;
        }

        // Use speech synthesis if available
        if ('speechSynthesis' in window && textToSpeak) {
            // Cancel any ongoing speech
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(textToSpeak);
            utterance.rate = 0.8;
            utterance.pitch = 1;
            utterance.volume = 0.8;
            
            window.speechSynthesis.speak(utterance);
        }

        console.log('Scanning:', textToSpeak);
    }

    /**
     * Setup gamepad listeners for mood selection
     */
    setupGamepadSupport() {
        console.log('Setting up gamepad support for mood selection');
        this.gamepadEnabled = true;
        
        // Check for already connected gamepads
        const gamepads = navigator.getGamepads();
        for (let i = 0; i < gamepads.length; i++) {
            if (gamepads[i]) {
                console.log("Found connected gamepad for mood selection:", i, gamepads[i].id);
                if (this.gamepadIndex === null) {
                    this.gamepadIndex = i;
                    this.startGamepadPolling();
                }
                break;
            }
        }
        
        // If no gamepad is found, that's okay - user can still use keyboard/touch
        if (this.gamepadIndex === null) {
            console.log('No gamepad detected for mood selection, keyboard/touch input will work');
        }
    }

    /**
     * Start gamepad polling for mood selection
     */
    startGamepadPolling() {
        if (this.gamepadPollInterval !== null || !this.gamepadEnabled) return;
        console.log("Starting mood selection gamepad polling for index:", this.gamepadIndex);
        let lastButtonState = false;

        const pollGamepads = () => {
            // Stop polling if mood selection is no longer active
            if (!this.moodOverlay || !this.gamepadEnabled) {
                this.stopGamepadPolling();
                return;
            }
            
            if (this.gamepadIndex === null) {
                this.stopGamepadPolling();
                return;
            }
            
            const gp = navigator.getGamepads()[this.gamepadIndex];
            if (!gp) {
                this.gamepadPollInterval = requestAnimationFrame(pollGamepads);
                return;
            }

            const currentButtonState = gp.buttons[0] && gp.buttons[0].pressed;
            if (currentButtonState && !lastButtonState) {
                const now = Date.now();
                if (now - this.lastGamepadInputTime > 300) { // Rate limit
                    this.handleGamepadInput();
                    this.lastGamepadInputTime = now;
                } else {
                    console.log("Mood selection gamepad press ignored (rate limit).");
                }
            }
            
            lastButtonState = currentButtonState;
            this.gamepadPollInterval = requestAnimationFrame(pollGamepads);
        };
        
        this.gamepadPollInterval = requestAnimationFrame(pollGamepads);
    }

    /**
     * Stop gamepad polling for mood selection
     */
    stopGamepadPolling() {
        if (this.gamepadPollInterval !== null) {
            cancelAnimationFrame(this.gamepadPollInterval);
            this.gamepadPollInterval = null;
            console.log("Stopped mood selection gamepad polling.");
        }
    }

    /**
     * Handle gamepad input for mood selection
     */
    handleGamepadInput() {
        console.log('Gamepad input detected in mood selection, ScanningOff:', this.ScanningOff, 'currentlyScannedButton:', this.currentlyScannedButton);
        
        if (this.ScanningOff) {
            // Manual selection mode - activate focused button
            const focusedButton = document.activeElement;
            console.log('Manual mode - focused button:', focusedButton);
            
            if (focusedButton && focusedButton.classList.contains('mood-button')) {
                const moodName = focusedButton.getAttribute('data-mood');
                this.selectMood(moodName, focusedButton);
            } else if (focusedButton && focusedButton.classList.contains('mood-skip-button')) {
                this.skipMoodSelection();
            } else {
                // If no specific button is focused, focus the first mood button
                const firstButton = this.moodOverlay.querySelector('.mood-button');
                if (firstButton) {
                    firstButton.focus();
                }
            }
        } else {
            // Scanning mode - select current highlighted button
            if (this.currentlyScannedButton) {
                const buttonToActivate = this.currentlyScannedButton;
                console.log("Mood selection: Gamepad pressed, activating button:", buttonToActivate.textContent || buttonToActivate.getAttribute('data-mood'));
                
                // Add visual feedback
                buttonToActivate.classList.add('active');
                setTimeout(() => buttonToActivate?.classList.remove('active'), 150);
                
                // Activate the button
                buttonToActivate.click();
            } else {
                console.log('No currently scanned button available in mood selection');
            }
        }
    }

    /**
     * Handle keyboard navigation and scanning controls
     */
    handleKeyPress(event) {
        // Only handle events when mood selection is active
        if (!this.moodOverlay || this.moodOverlay.style.display === 'none') {
            return;
        }

        console.log('Mood selection keypress:', event.code, 'target:', event.target);

        // Prevent all default behaviors for space, enter, and arrows when modal is active
        if (['Space', 'Enter', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Escape'].includes(event.code)) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
        }

        switch (event.code) {
            case 'Space':
                console.log('Space pressed in mood selection, ScanningOff:', this.ScanningOff, 'currentlyScannedButton:', this.currentlyScannedButton);
                
                if (this.ScanningOff) {
                    // Manual selection mode
                    const focusedButton = document.activeElement;
                    console.log('Manual mode - focused button:', focusedButton);
                    if (focusedButton && focusedButton.classList.contains('mood-button')) {
                        const moodName = focusedButton.getAttribute('data-mood');
                        this.selectMood(moodName, focusedButton);
                    } else if (focusedButton && focusedButton.classList.contains('mood-skip-button')) {
                        this.skipMoodSelection();
                    } else {
                        // If no specific button is focused, focus the first mood button
                        const firstButton = this.moodOverlay.querySelector('.mood-button');
                        if (firstButton) {
                            firstButton.focus();
                        }
                    }
                } else {
                    // Scanning mode - select current highlighted button
                    if (this.currentlyScannedButton) {
                        const buttonToActivate = this.currentlyScannedButton;
                        console.log("Mood selection: Spacebar pressed, activating button:", buttonToActivate.textContent || buttonToActivate.getAttribute('data-mood'));
                        buttonToActivate.click();
                        buttonToActivate.classList.add('active');
                        setTimeout(() => buttonToActivate?.classList.remove('active'), 150);
                    } else {
                        console.log('No currently scanned button available');
                    }
                }
                break;

            case 'Enter':
                // Same logic as Space for Enter key
                if (this.ScanningOff) {
                    const focusedButton = document.activeElement;
                    if (focusedButton && focusedButton.classList.contains('mood-button')) {
                        const moodName = focusedButton.getAttribute('data-mood');
                        this.selectMood(moodName, focusedButton);
                    } else if (focusedButton && focusedButton.classList.contains('mood-skip-button')) {
                        this.skipMoodSelection();
                    }
                } else {
                    if (this.currentlyScannedButton) {
                        this.currentlyScannedButton.click();
                    }
                }
                break;

            case 'Escape':
                this.skipMoodSelection();
                break;

            case 'ArrowRight':
            case 'ArrowDown':
                if (this.ScanningOff) {
                    this.navigateButtons(1);
                }
                break;

            case 'ArrowLeft':
            case 'ArrowUp':
                if (this.ScanningOff) {
                    this.navigateButtons(-1);
                }
                break;
        }
    }

    /**
     * Navigate between buttons manually (when scanning is off)
     */
    navigateButtons(direction) {
        const currentFocused = document.activeElement;
        const currentIndex = this.moodButtons.indexOf(currentFocused);
        
        if (currentIndex >= 0) {
            const nextIndex = (currentIndex + direction + this.moodButtons.length) % this.moodButtons.length;
            this.moodButtons[nextIndex].focus();
        } else {
            // Focus first button if none focused
            this.moodButtons[0].focus();
        }
    }
    removeMoodInterface() {
        // Stop scanning
        this.stopScanning();
        
        // Stop gamepad polling and disable gamepad support
        this.gamepadEnabled = false;
        this.stopGamepadPolling();
        this.gamepadIndex = null;
        
        // Remove interface (this will automatically remove the container event listener)
        if (this.moodOverlay) {
            this.moodOverlay.remove();
            this.moodOverlay = null;
        }
        
        // Clear button references
        this.moodButtons = [];
        this.currentButtonIndex = 0;
    }

    /**
     * Gets the current session mood
     * @returns {string|null} The current mood or null if none set
     */
    static getCurrentMood() {
        const mood = sessionStorage.getItem('currentSessionMood');
        return mood === 'none' ? null : mood;
    }

    /**
     * Clears the current session mood (useful for testing or admin reset)
     */
    static clearCurrentMood() {
        sessionStorage.removeItem('currentSessionMood');
    }
}

// Global instance
let globalMoodSelection = null;

// Initialize when script loads
document.addEventListener('DOMContentLoaded', () => {
    globalMoodSelection = new MoodSelection();
});

/**
 * Global function to show mood selection (used by other scripts)
 * @param {Function} onComplete - Callback function when mood selection is complete
 */
function showMoodSelection(onComplete) {
    if (globalMoodSelection) {
        globalMoodSelection.show(onComplete);
    } else {
        console.warn('Mood selection not initialized');
        if (onComplete) onComplete(null);
    }
}

/**
 * Global function to get current mood (used by other scripts)
 * @returns {string|null} The current mood or null if none set
 */
function getCurrentMood() {
    return MoodSelection.getCurrentMood();
}

/**
 * Global function to clear current mood (used by admin scripts)
 */
function clearCurrentMood() {
    MoodSelection.clearCurrentMood();
}

// Export for use in other modules
window.MoodSelection = MoodSelection;
window.showMoodSelection = showMoodSelection;
window.getCurrentMood = getCurrentMood;
window.clearCurrentMood = clearCurrentMood;
