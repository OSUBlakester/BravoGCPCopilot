// --- Global Flags ---
let isAuthContextReady = false;
let isDomContentLoaded = false;


// DOM Elements - declare with 'let', assign in initializePage
let locationInput = null;
let peopleInput = null;
let activityInput = null;
let saveButton = null;
let dictationButton = null;

// Favorites DOM elements
let favoritesSelect = null;
let loadFavoriteBtn = null;
let openThreadBtn = null;
let addToFavoritesBtn = null;
let manageFavoritesBtn = null;
let manageFavoritesModal = null;
let closeManageFavoritesModal = null;
let addFavoriteModal = null;
let closeAddFavoriteModal = null;
let favoriteName = null;
let cancelAddFavorite = null;
let confirmAddFavorite = null;
let favoritesManagementList = null;


// Utility function to display status messages
function showStatus(message, isError = false, duration = 3000) {
    // Assuming you'll add a status element to your HTML, e.g., <p id="status-message"></p>
    const statusElement = document.getElementById('status-message'); // Make sure this ID exists in your HTML
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.style.color = isError ? 'red' : 'green';
        if (duration > 0) {
            setTimeout(() => {
                if (statusElement.textContent === message) statusElement.textContent = '';
            }, duration);
        }
    } else { console.log(`Status (${isError ? 'Error' : 'Info'}): ${message}`); }
}

// Function to load current user state
async function loadCurrentUserState() {
    showStatus("Loading current state...", false, 0);
    try {
        // Use the existing GET endpoint from server.py
        const response = await window.authenticatedFetch('/get-user-current'); // No body/headers needed for GET
        if (!response.ok) throw new Error(`Failed to load: ${response.statusText}`);
        const data = await response.json();
        locationInput.value = data.location || '';
        peopleInput.value = data.people || '';
        activityInput.value = data.activity || '';
        
        // Check if there's a loaded favorite and enable thread button if so
        if (data.favorite_name && data.loaded_at && openThreadBtn) {
            openThreadBtn.disabled = false;
            openThreadBtn.setAttribute('data-favorite-name', data.favorite_name);
            console.log(`Thread button enabled for loaded favorite: ${data.favorite_name}`);
        }
        
        showStatus("Current state loaded.", false);
    } catch (error) {
        console.error('Error loading user current state:', error);
        showStatus(`Error loading state: ${error.message}`, true);
    }
}

// Function to load favorites
async function loadFavorites() {
    console.log("loadFavorites() called");
    try {
        console.log("Calling /api/user-current-favorites");
        const response = await window.authenticatedFetch('/api/user-current-favorites');
        console.log("Response received:", response.status, response.statusText);
        if (!response.ok) throw new Error(`Failed to load favorites: ${response.statusText}`);
        const data = await response.json();
        console.log("Favorites data:", data);
        
        // Populate the favorites dropdown
        favoritesSelect.innerHTML = '<option value="">Choose a favorite...</option>';
        data.favorites.forEach(favorite => {
            const option = document.createElement('option');
            option.value = JSON.stringify(favorite);
            option.textContent = favorite.name;
            favoritesSelect.appendChild(option);
        });
        
        console.log("Dropdown populated with", data.favorites.length, "favorites");
        
        // Update load button state
        updateLoadButtonState();
        
    } catch (error) {
        console.error('Error loading favorites:', error);
        showStatus(`Error loading favorites: ${error.message}`, true);
    }
}

// Function to update load button state
function updateLoadButtonState() {
    loadFavoriteBtn.disabled = !favoritesSelect.value;
}

// Function to update open thread button state - only enabled if a favorite was loaded recently
function updateOpenThreadButtonState() {
    // This will be called after loading favorites or checking current state
    // For now, we'll enable it based on the current state having a loaded favorite
    // The real validation will be done server-side
    openThreadBtn.disabled = true; // Default to disabled, will be enabled when we detect a loaded favorite
}

// Function to load selected favorite and automatically save
async function loadSelectedFavorite() {
    console.log("loadSelectedFavorite() called");
    const selectedValue = favoritesSelect.value;
    console.log("Selected value:", selectedValue);
    if (!selectedValue) return;
    
    try {
        const favorite = JSON.parse(selectedValue);
        console.log("Parsed favorite:", favorite);
        
        // Update the form fields
        locationInput.value = favorite.location || '';
        peopleInput.value = favorite.people || '';
        activityInput.value = favorite.activity || '';
        
        // Automatically save the loaded data to the database
        const loadTimestamp = new Date().toISOString(); // Use same timestamp for both loaded_at and saved_at
        const saveData = {
            location: favorite.location || '',
            people: favorite.people || '',
            activity: favorite.activity || '',
            loaded_at: loadTimestamp,  // Timestamp when favorite is loaded
            favorite_name: favorite.name,  // Include the favorite name for tracking
            saved_at: loadTimestamp  // Use same timestamp to indicate this save is part of loading, not manual
        };
        
        const response = await window.authenticatedFetch('/user_current', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData)
        });
        
        if (response.ok) {
            showStatus(`Loaded and saved favorite: ${favorite.name}`, false);
            // Enable the Open Thread button since we just loaded a favorite
            openThreadBtn.disabled = false;
            // Store the loaded favorite name for the thread functionality
            openThreadBtn.setAttribute('data-favorite-name', favorite.name);
        } else {
            showStatus(`Loaded favorite: ${favorite.name} (but failed to auto-save)`, true);
        }
        
    } catch (error) {
        console.error('Error loading favorite:', error);
        showStatus('Error loading selected favorite', true);
    }
}

// Function to open thread for the loaded favorite
async function openThreadForLoadedFavorite() {
    console.log("openThreadForLoadedFavorite() called");
    
    const favoriteName = openThreadBtn.getAttribute('data-favorite-name');
    if (!favoriteName) {
        showStatus('No favorite loaded. Please load a favorite first.', true);
        return;
    }
    
    try {
        // Navigate to the threads page with the favorite name as a parameter
        const encodedFavoriteName = encodeURIComponent(favoriteName);
        window.location.href = `/static/threads.html?favorite=${encodedFavoriteName}`;
    } catch (error) {
        console.error('Error opening thread:', error);
        showStatus('Error opening thread for favorite', true);
    }
}

// Function to show add favorite modal
function showAddFavoriteModal() {
    console.log("showAddFavoriteModal() called");
    // Update preview with current values
    document.getElementById('favoritePreviewLocation').textContent = `Location: ${locationInput.value || '(empty)'}`;
    document.getElementById('favoritePreviewPeople').textContent = `People: ${peopleInput.value || '(empty)'}`;
    document.getElementById('favoritePreviewActivity').textContent = `Activity: ${activityInput.value || '(empty)'}`;
    
    // Clear the name input
    favoriteName.value = '';
    
    // Show modal
    addFavoriteModal.classList.remove('hidden');
    favoriteName.focus();
}

// Function to save favorite
async function saveFavorite() {
    const name = favoriteName.value.trim();
    if (!name) {
        showStatus('Please enter a name for the favorite', true);
        return;
    }
    
    const favoriteData = {
        name: name,
        location: locationInput.value || '',
        people: peopleInput.value || '',
        activity: activityInput.value || ''
    };
    
    try {
        const response = await window.authenticatedFetch('/api/user-current-favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(favoriteData)
        });
        
        const result = await response.json();
        if (result.success) {
            showStatus(result.message, false);
            addFavoriteModal.classList.add('hidden');
            await loadFavorites(); // Refresh the list
        } else {
            showStatus(result.message, true);
        }
    } catch (error) {
        console.error('Error saving favorite:', error);
        showStatus('Error saving favorite', true);
    }
}

// Function to show manage favorites modal
async function showManageFavoritesModal() {
    console.log("showManageFavoritesModal() called");
    try {
        const response = await window.authenticatedFetch('/api/user-current-favorites');
        if (!response.ok) throw new Error(`Failed to load favorites: ${response.statusText}`);
        const data = await response.json();
        console.log("Management modal favorites data:", data);
        
        // Populate the management list
        favoritesManagementList.innerHTML = '';
        
        if (data.favorites.length === 0) {
            favoritesManagementList.innerHTML = '<p class="text-gray-500 text-center py-4">No favorites saved yet.</p>';
        } else {
            data.favorites.forEach(favorite => {
                const favoriteDiv = document.createElement('div');
                favoriteDiv.className = 'border border-gray-200 rounded-lg p-4';
                favoriteDiv.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <h4 class="font-medium text-gray-800 mb-2">${favorite.name}</h4>
                            <p class="text-sm text-gray-600">Location: ${favorite.location || '(empty)'}</p>
                            <p class="text-sm text-gray-600">People: ${favorite.people || '(empty)'}</p>
                            <p class="text-sm text-gray-600">Activity: ${favorite.activity || '(empty)'}</p>
                        </div>
                        <div class="flex gap-2 ml-4">
                            <button onclick="editFavorite('${favorite.name}')" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                                Edit
                            </button>
                            <button onclick="deleteFavorite('${favorite.name}')" class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                                Delete
                            </button>
                        </div>
                    </div>
                `;
                favoritesManagementList.appendChild(favoriteDiv);
            });
        }
        
        manageFavoritesModal.classList.remove('hidden');
        console.log("Management modal shown");
    } catch (error) {
        console.error('Error loading favorites for management:', error);
        showStatus('Error loading favorites', true);
    }
}

// Function to edit favorite
async function editFavorite(favoriteName) {
    const newName = prompt('Enter new name:', favoriteName);
    if (!newName || newName.trim() === '') return;
    
    const newLocation = prompt('Enter location:');
    if (newLocation === null) return;
    
    const newPeople = prompt('Enter people:');
    if (newPeople === null) return;
    
    const newActivity = prompt('Enter activity:');
    if (newActivity === null) return;
    
    try {
        const response = await window.authenticatedFetch('/api/user-current-favorites/manage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'edit',
                old_name: favoriteName,
                favorite: {
                    name: newName.trim(),
                    location: newLocation,
                    people: newPeople,
                    activity: newActivity
                }
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showStatus(result.message, false);
            await showManageFavoritesModal(); // Refresh the modal
            await loadFavorites(); // Refresh the dropdown
        } else {
            showStatus(result.message, true);
        }
    } catch (error) {
        console.error('Error editing favorite:', error);
        showStatus('Error editing favorite', true);
    }
}

// Function to delete favorite
async function deleteFavorite(favoriteName) {
    if (!confirm(`Are you sure you want to delete the favorite "${favoriteName}"?`)) return;
    
    try {
        const response = await window.authenticatedFetch('/api/user-current-favorites/manage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'delete',
                old_name: favoriteName
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showStatus(result.message, false);
            await showManageFavoritesModal(); // Refresh the modal
            await loadFavorites(); // Refresh the dropdown
        } else {
            showStatus(result.message, true);
        }
    } catch (error) {
        console.error('Error deleting favorite:', error);
        showStatus('Error deleting favorite', true);
    }
}

// Make functions available globally for onclick handlers
window.editFavorite = editFavorite;
window.deleteFavorite = deleteFavorite;



let recognition;
let isDictating = false;


// --- Initialization Function ---
async function initializePage() {
    if (isAuthContextReady && isDomContentLoaded) {
        console.log("admin_current_admin.js: Auth context and DOM ready. Initializing page.");

        // Assign DOM Elements
        locationInput = document.getElementById('location');
        peopleInput = document.getElementById('people');
        activityInput = document.getElementById('activity');
        saveButton = document.getElementById('saveButton');
        dictationButton = document.getElementById('dictationButton');
        
        // Favorites DOM elements
        favoritesSelect = document.getElementById('favoritesSelect');
        loadFavoriteBtn = document.getElementById('loadFavoriteBtn');
        openThreadBtn = document.getElementById('openThreadBtn');
        addToFavoritesBtn = document.getElementById('addToFavoritesBtn');
        manageFavoritesBtn = document.getElementById('manageFavoritesBtn');
        manageFavoritesModal = document.getElementById('manageFavoritesModal');
        closeManageFavoritesModal = document.getElementById('closeManageFavoritesModal');
        addFavoriteModal = document.getElementById('addFavoriteModal');
        closeAddFavoriteModal = document.getElementById('closeAddFavoriteModal');
        favoriteName = document.getElementById('favoriteName');
        cancelAddFavorite = document.getElementById('cancelAddFavorite');
        confirmAddFavorite = document.getElementById('confirmAddFavorite');
        favoritesManagementList = document.getElementById('favoritesManagementList');

        // Basic check for essential elements
        if (!locationInput || !peopleInput || !activityInput || !saveButton || !dictationButton || !favoritesSelect || !loadFavoriteBtn || !openThreadBtn || !addToFavoritesBtn || !manageFavoritesBtn) {
            console.error("CRITICAL ERROR: One or more essential DOM elements for user_current_admin.js not found.");
            return;
        }

        // Add Event Listeners
        if (saveButton) saveButton.addEventListener('click', saveCurrentUserState);
        if (dictationButton) dictationButton.addEventListener('click', dictationButtonHandler);
        
        // Favorites event listeners
        if (favoritesSelect) favoritesSelect.addEventListener('change', updateLoadButtonState);
        if (loadFavoriteBtn) {
            loadFavoriteBtn.addEventListener('click', loadSelectedFavorite);
            console.log("Load favorite button event listener added");
        }
        if (openThreadBtn) {
            openThreadBtn.addEventListener('click', openThreadForLoadedFavorite);
            console.log("Open thread button event listener added");
        }
        if (addToFavoritesBtn) {
            addToFavoritesBtn.addEventListener('click', showAddFavoriteModal);
            console.log("Add to favorites button event listener added");
        }
        if (manageFavoritesBtn) {
            manageFavoritesBtn.addEventListener('click', showManageFavoritesModal);
            console.log("Manage favorites button event listener added");
        }
        
        // Modal event listeners
        if (closeManageFavoritesModal) closeManageFavoritesModal.addEventListener('click', () => manageFavoritesModal.classList.add('hidden'));
        if (closeAddFavoriteModal) closeAddFavoriteModal.addEventListener('click', () => addFavoriteModal.classList.add('hidden'));
        if (cancelAddFavorite) cancelAddFavorite.addEventListener('click', () => addFavoriteModal.classList.add('hidden'));
        if (confirmAddFavorite) confirmAddFavorite.addEventListener('click', saveFavorite);
        
        // Close modals when clicking outside
        manageFavoritesModal.addEventListener('click', (e) => {
            if (e.target === manageFavoritesModal) {
                manageFavoritesModal.classList.add('hidden');
            }
        });
        addFavoriteModal.addEventListener('click', (e) => {
            if (e.target === addFavoriteModal) {
                addFavoriteModal.classList.add('hidden');
            }
        });


        // Initial data loading
        await loadCurrentUserState();
        console.log("About to call loadFavorites()");
        await loadFavorites();
        console.log("loadFavorites() completed");
    }
}


// --- DOMContentLoaded Initialization ---
async function saveCurrentUserState() { 
        console.log("location input value", locationInput.value);
        console.log("people input value", peopleInput.value);
        console.log("activity input value", activityInput.value);
        const location = locationInput.value;
        const people = peopleInput.value;
        const activity = activityInput.value;

        console.log('Data sent to backend:', { location, people, activity }); // Add this line
        showStatus("Saving...", false, 0);

        try {
            // Use the existing POST endpoint from server.py
            const response = await window.authenticatedFetch('/user_current', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }, // X-User-ID added by authenticatedFetch
                body: JSON.stringify({ location, people, activity })
            });

            if (response.ok) {
                console.log('User current updated successfully.');
                showStatus("Current state saved successfully!", false);
            } else {
                console.error('Failed to update user current:', response.statusText);
                showStatus(`Save failed: ${response.statusText}`, true);
            }
        } catch (error) {
            console.error('Error updating user current:', error);
            showStatus(`Error saving: ${error.message}`, true);
        }
}


function dictationButtonHandler() { 
    if (!isDictating) {
        startDictation();
    } else {
        stopDictation();
    }
}

async function startDictation() {
    recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)();
    recognition.continuous = true;
    recognition.lang = 'en-US';

    recognition.onstart = function() {
        console.log('Dictation started.');
        dictationButton.textContent = 'Stop Dictation';
        isDictating = true;
    };

    recognition.onresult = function(event) {
        const transcript = event.results[event.results.length - 1][0].transcript;
        console.log("transcript", transcript);
    
        const locationMatch = transcript.match(/location\s+(.+?)\s*people/i);
        const peopleMatch = transcript.match(/people\s+(.+?)\s*activity/i);
        const activityMatch = transcript.match(/activity\s+(.+)/i);
    
        if (locationMatch && locationMatch[1]) {
            locationInput.value = locationMatch[1].trim();
            console.log("location input updated", locationInput.value);
        }
    
        if (peopleMatch && peopleMatch[1]) {
            peopleInput.value = peopleMatch[1].trim();
            console.log("people input updated", peopleInput.value);
        }
    
        if (activityMatch && activityMatch[1]) {
            activityInput.value = activityMatch[1].trim();
            console.log("activity input updated", activityInput.value);
        }
    };

    recognition.onerror = function(event) {
        console.error('Dictation error:', event); // Log the entire event object
        stopDictation();
    };

    recognition.onend = function() {
        console.log('Dictation ended.');
        setTimeout(function() {
            if (isDictating) {
                console.log("restarting dictation");
                recognition.start();
            } else {
                stopDictation();
            }
        }, 100); // 100 milliseconds delay
    };

    recognition.start();
}

function stopDictation() {
    if (recognition) {
        recognition.stop();
        recognition = null;
    }
    dictationButton.textContent = 'Start Dictation';
    isDictating = false;
}


// --- Auth Context Ready Handler ---
function authContextIsReady() {
    if (isAuthContextReady) return;
    console.log("admin_current_admin.js: Authentication context is now marked as ready.");
    isAuthContextReady = true;
    initializePage();
}

// --- Event Listeners ---
// Listener for when the authentication context is ready
document.addEventListener('adminUserContextReady', () => {
    console.log("admin_current_admin.js: 'adminUserContextReady' event received.");
    authContextIsReady();
});

if (window.adminContextInitializedByInlineScript === true) {
    console.log("admin_current_admin.js: Global flag 'adminContextInitializedByInlineScript' was already true.");
    authContextIsReady();
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("admin_current_admin.js: DOMContentLoaded event.");
    isDomContentLoaded = true;
    initializePage();
});