// User Info & Birthdays Admin — Help Modal & Interactive Guide System

document.addEventListener('DOMContentLoaded', function() {

    // ── Help Modal ─────────────────────────────────────────────────────────
    function buildHelpModal() {
        const modal = document.createElement('div');
        modal.id = 'help-modal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 hidden z-[1000] flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
                <div class="p-6 border-b border-gray-200 bg-gradient-to-r from-orange-50 to-red-50 flex justify-between items-center">
                    <h2 class="text-2xl font-bold text-gray-800">
                        <i class="fas fa-info-circle text-[#FB4F14] mr-2"></i>User Info &amp; Birthdays Guide
                    </h2>
                    <button id="close-help-modal" class="text-gray-500 hover:text-gray-700 transition-colors">
                        <i class="fas fa-times text-2xl"></i>
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-6">
                    <div class="prose max-w-none">
                        <p class="text-gray-700 mb-6">
                            Manage user profiles, moods, personalization settings, family &amp; friends, and custom images — organized in the sidebar sections.
                        </p>
                        <div class="space-y-3">

                            <!-- Personalization -->
                            <div class="settings-guide-item cursor-pointer" onclick="toggleUserInfoGuideDetails(this)">
                                <div class="flex items-start p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                    <div class="flex-shrink-0 mt-1"><i class="fas fa-sliders-h text-indigo-600 text-lg"></i></div>
                                    <div class="ml-3 flex-1">
                                        <div class="flex items-center justify-between">
                                            <div class="font-semibold text-gray-900">Personalization</div>
                                            <div class="flex items-center space-x-2">
                                                <button onclick="event.stopPropagation(); startUserInfoGuide('personalization');" class="px-3 py-1 bg-indigo-500 text-white text-xs rounded-lg hover:bg-indigo-600 transition flex items-center">
                                                    <i class="fas fa-route mr-1"></i>Guide Me
                                                </button>
                                                <i class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                                            </div>
                                        </div>
                                        <div class="guide-details hidden mt-2">
                                            <div class="text-sm text-gray-700 space-y-2">
                                                <p><strong>Purpose:</strong> Control whether user profile data and AI learning are active, and set COPPA compliance for younger users.</p>
                                                <div class="bg-indigo-50 border-l-4 border-indigo-500 p-3 rounded">
                                                    <p class="text-sm font-semibold text-indigo-900 mb-1">Settings:</p>
                                                    <ul class="text-xs text-gray-700 ml-4 space-y-1">
                                                        <li>• <strong>Age Group:</strong> Mark as Under 13 or 13 or older to set COPPA compliance requirements</li>
                                                        <li>• <strong>Use Entered Details:</strong> When on, the User Profile narrative and People data personalize AI responses</li>
                                                        <li>• <strong>Learn from History:</strong> When on, Bravo analyses conversations to learn user preferences automatically</li>
                                                        <li>• <strong>Auto-approve Learned Facts:</strong> Sub-option (visible when Learn from History is on) — skips the approval queue and applies learned facts to the profile immediately</li>
                                                        <li>• <strong>Save Personalization:</strong> Saves all personalization toggle settings</li>
                                                        <li>• <strong>Download User Data:</strong> Exports narrative, learned facts, interview answers, chat history, activity log, and consent record as a file</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Current Mood -->
                            <div class="settings-guide-item cursor-pointer" onclick="toggleUserInfoGuideDetails(this)">
                                <div class="flex items-start p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                    <div class="flex-shrink-0 mt-1"><i class="fas fa-smile text-blue-600 text-lg"></i></div>
                                    <div class="ml-3 flex-1">
                                        <div class="flex items-center justify-between">
                                            <div class="font-semibold text-gray-900">Current Mood</div>
                                            <div class="flex items-center space-x-2">
                                                <button onclick="event.stopPropagation(); startUserInfoGuide('mood');" class="px-3 py-1 bg-blue-500 text-white text-xs rounded-lg hover:bg-blue-600 transition flex items-center">
                                                    <i class="fas fa-route mr-1"></i>Guide Me
                                                </button>
                                                <i class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                                            </div>
                                        </div>
                                        <div class="guide-details hidden mt-2">
                                            <div class="text-sm text-gray-700 space-y-2">
                                                <p><strong>Purpose:</strong> Set the user's current session mood to personalize how Bravo interacts during this session.</p>
                                                <div class="bg-blue-50 border-l-4 border-blue-500 p-3 rounded">
                                                    <ul class="text-xs text-gray-700 ml-4 space-y-1">
                                                        <li>• <strong>Mood Dropdown:</strong> Choose from available mood options (e.g., Happy, Calm, Excited, Thoughtful)</li>
                                                        <li>• <strong>Save:</strong> Applies the selected mood for the current session</li>
                                                        <li>• <strong>Clear:</strong> Removes the current mood setting, resetting to no mood</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- User Profile -->
                            <div class="settings-guide-item cursor-pointer" onclick="toggleUserInfoGuideDetails(this)">
                                <div class="flex items-start p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                    <div class="flex-shrink-0 mt-1"><i class="fas fa-user text-green-600 text-lg"></i></div>
                                    <div class="ml-3 flex-1">
                                        <div class="flex items-center justify-between">
                                            <div class="font-semibold text-gray-900">User Profile</div>
                                            <div class="flex items-center space-x-2">
                                                <button onclick="event.stopPropagation(); startUserInfoGuide('profile');" class="px-3 py-1 bg-green-500 text-white text-xs rounded-lg hover:bg-green-600 transition flex items-center">
                                                    <i class="fas fa-route mr-1"></i>Guide Me
                                                </button>
                                                <i class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                                            </div>
                                        </div>
                                        <div class="guide-details hidden mt-2">
                                            <div class="text-sm text-gray-700 space-y-2">
                                                <p><strong>Purpose:</strong> Enter the user's name, profile picture, narrative, AI overrides, and birthday.</p>
                                                <div class="bg-green-50 border-l-4 border-green-500 p-3 rounded">
                                                    <ul class="text-xs text-gray-700 ml-4 space-y-1">
                                                        <li>• <strong>Start Interview:</strong> AI-guided interview that fills Name, Birthday, and Narrative automatically via voice or text answers</li>
                                                        <li>• <strong>User's Name:</strong> The user's preferred name — used for pronouns and personal references in AI responses (I, me, myself, mine)</li>
                                                        <li>• <strong>Profile Picture:</strong> Upload a photo for the user's identity, used to represent personal pronouns on the communication board</li>
                                                        <li>• <strong>User Narrative:</strong> Free-text biography — include personality, interests, hobbies, family, and anything relevant for personalization</li>
                                                        <li>• <strong>AI Option Overrides:</strong> Set hard include/exclude rules for AI-generated options (e.g., exclude eating independently, allow adult topics)</li>
                                                        <li>• <strong>User's Birthday:</strong> Full birthdate used to calculate age and enable birthday features</li>
                                                        <li>• <strong>COPPA Consent Banner:</strong> Appears when the user is marked under 13 — send a consent email and check for parental verification before learning features activate</li>
                                                        <li>• <strong>Save:</strong> Saves name, narrative, and birthday together</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Learning & History -->
                            <div class="settings-guide-item cursor-pointer" onclick="toggleUserInfoGuideDetails(this)">
                                <div class="flex items-start p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                    <div class="flex-shrink-0 mt-1"><i class="fas fa-robot text-purple-600 text-lg"></i></div>
                                    <div class="ml-3 flex-1">
                                        <div class="flex items-center justify-between">
                                            <div class="font-semibold text-gray-900">Learning &amp; History</div>
                                            <div class="flex items-center space-x-2">
                                                <button onclick="event.stopPropagation(); startUserInfoGuide('history');" class="px-3 py-1 bg-purple-500 text-white text-xs rounded-lg hover:bg-purple-600 transition flex items-center">
                                                    <i class="fas fa-route mr-1"></i>Guide Me
                                                </button>
                                                <i class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                                            </div>
                                        </div>
                                        <div class="guide-details hidden mt-2">
                                            <div class="text-sm text-gray-700 space-y-2">
                                                <p><strong>Purpose:</strong> View and manage what Bravo has learned from the user's conversation history.</p>
                                                <div class="bg-purple-50 border-l-4 border-purple-500 p-3 rounded">
                                                    <ul class="text-xs text-gray-700 ml-4 space-y-1">
                                                        <li>• <strong>AI-Extracted Narrative:</strong> A summary, approved facts, known preferences, and recent greetings extracted from chat messages older than 7 days</li>
                                                        <li>• <strong>Refresh (Narrative):</strong> Reload the latest extracted narrative from the server</li>
                                                        <li>• <strong>Pending Learned Facts:</strong> Facts learned from conversation history waiting for a guardian to approve or discard</li>
                                                        <li>• <strong>Refresh (Pending):</strong> Reload the latest pending proposals</li>
                                                        <li>• <strong>Note:</strong> Learn from History must be enabled in Personalization for this section to be active</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Family & Friends -->
                            <div class="settings-guide-item cursor-pointer" onclick="toggleUserInfoGuideDetails(this)">
                                <div class="flex items-start p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                    <div class="flex-shrink-0 mt-1"><i class="fas fa-users text-orange-600 text-lg"></i></div>
                                    <div class="ml-3 flex-1">
                                        <div class="flex items-center justify-between">
                                            <div class="font-semibold text-gray-900">Family &amp; Friends</div>
                                            <div class="flex items-center space-x-2">
                                                <button onclick="event.stopPropagation(); startUserInfoGuide('family');" class="px-3 py-1 bg-orange-500 text-white text-xs rounded-lg hover:bg-orange-600 transition flex items-center">
                                                    <i class="fas fa-route mr-1"></i>Guide Me
                                                </button>
                                                <i class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                                            </div>
                                        </div>
                                        <div class="guide-details hidden mt-2">
                                            <div class="text-sm text-gray-700 space-y-2">
                                                <p><strong>Purpose:</strong> Add and manage people important to the user — family members, friends, caregivers — with their relationship, background, and birthday.</p>
                                                <div class="bg-orange-50 border-l-4 border-orange-500 p-3 rounded">
                                                    <ul class="text-xs text-gray-700 ml-4 space-y-1">
                                                        <li>• <strong>Start Interview:</strong> An audio interview to add a family member or friend by answering questions about them</li>
                                                        <li>• <strong>Friends &amp; Family Table:</strong> Add/edit entries with Name, Relationship, About (background/interests), and Birthday (MM-DD)</li>
                                                        <li>• <strong>Add Person:</strong> Appends a new empty row to the table for manual entry</li>
                                                        <li>• <strong>Manage Relationship Types:</strong> Add, edit, or remove custom relationship labels (e.g., Therapist, Neighbor)</li>
                                                        <li>• <strong>Save Family &amp; Friends:</strong> Saves all entries in the table</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Custom Images -->
                            <div class="settings-guide-item cursor-pointer" onclick="toggleUserInfoGuideDetails(this)">
                                <div class="flex items-start p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                    <div class="flex-shrink-0 mt-1"><i class="fas fa-images text-cyan-600 text-lg"></i></div>
                                    <div class="ml-3 flex-1">
                                        <div class="flex items-center justify-between">
                                            <div class="font-semibold text-gray-900">Custom Images</div>
                                            <div class="flex items-center space-x-2">
                                                <button onclick="event.stopPropagation(); startUserInfoGuide('images');" class="px-3 py-1 bg-cyan-500 text-white text-xs rounded-lg hover:bg-cyan-600 transition flex items-center">
                                                    <i class="fas fa-route mr-1"></i>Guide Me
                                                </button>
                                                <i class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                                            </div>
                                        </div>
                                        <div class="guide-details hidden mt-2">
                                            <div class="text-sm text-gray-700 space-y-2">
                                                <p><strong>Purpose:</strong> Upload profile-specific images that are automatically matched to communication board buttons using tags.</p>
                                                <div class="bg-cyan-50 border-l-4 border-cyan-500 p-3 rounded">
                                                    <ul class="text-xs text-gray-700 ml-4 space-y-1">
                                                        <li>• <strong>Upload Custom Image:</strong> Choose an image file (JPG, PNG, WebP, max 5MB) and assign tags to it</li>
                                                        <li>• <strong>Tags:</strong> Comma-separated words matched against button labels (e.g., "dad, daddy, father" displays this image on buttons with those labels)</li>
                                                        <li>• <strong>Upload Image:</strong> Saves the file and its tags to the user's profile</li>
                                                        <li>• <strong>Uploaded Images Grid:</strong> Shows all custom images — click one to edit its tags or delete it</li>
                                                        <li>• <strong>Refresh:</strong> Reloads the list of uploaded images from the server</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
                <div class="p-6 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
                    <button id="contact-support-btn" class="inline-block bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition">
                        <i class="fas fa-envelope mr-2"></i>Contact Support
                    </button>
                    <button id="close-help-modal-footer" class="px-4 py-2 bg-[#FB4F14] text-white rounded-lg hover:bg-orange-600 transition-colors">
                        Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    window.toggleUserInfoGuideDetails = function(element) {
        const details = element.querySelector('.guide-details');
        const chevron = element.querySelector('.fa-chevron-down');
        if (details.classList.contains('hidden')) {
            details.classList.remove('hidden');
            chevron.style.transform = 'rotate(180deg)';
        } else {
            details.classList.add('hidden');
            chevron.style.transform = 'rotate(0deg)';
        }
    };

    // ── Modal open/close ───────────────────────────────────────────────────
    let helpModal = null;

    function openHelpModal() {
        if (!helpModal) {
            helpModal = buildHelpModal();
            helpModal.querySelector('#close-help-modal').addEventListener('click', closeHelpModal);
            helpModal.querySelector('#close-help-modal-footer').addEventListener('click', closeHelpModal);
            helpModal.querySelector('#contact-support-btn').addEventListener('click', openContactModal);
            helpModal.addEventListener('click', function(e) { if (e.target === helpModal) closeHelpModal(); });
        }
        helpModal.classList.remove('hidden');
    }

    function closeHelpModal() {
        if (helpModal) helpModal.classList.add('hidden');
    }

    const helpIcon = document.getElementById('help-icon');
    if (helpIcon) helpIcon.addEventListener('click', openHelpModal, true);

    // ── Contact Support ────────────────────────────────────────────────────
    function openContactModal() {
        closeHelpModal();
        let contactModal = document.getElementById('contact-modal-userinfo');
        if (!contactModal) {
            contactModal = document.createElement('div');
            contactModal.id = 'contact-modal-userinfo';
            contactModal.className = 'fixed inset-0 bg-black bg-opacity-50 z-[1001] flex items-center justify-center p-4';
            contactModal.innerHTML = `
                <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md">
                    <div class="p-6 border-b border-gray-200 bg-gradient-to-r from-orange-50 to-red-50">
                        <h3 class="text-xl font-bold text-gray-800"><i class="fas fa-envelope text-[#FB4F14] mr-2"></i>Contact Support</h3>
                    </div>
                    <div class="p-6">
                        <form id="contact-form-userinfo">
                            <div class="space-y-4">
                                <div>
                                    <label for="contact-name-ui" class="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
                                    <input type="text" id="contact-name-ui" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500">
                                </div>
                                <div>
                                    <label for="contact-email-ui" class="block text-sm font-medium text-gray-700 mb-1">Your Email</label>
                                    <input type="email" id="contact-email-ui" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500">
                                </div>
                                <div>
                                    <label for="contact-message-ui" class="block text-sm font-medium text-gray-700 mb-1">Message</label>
                                    <textarea id="contact-message-ui" rows="4" required class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"></textarea>
                                </div>
                            </div>
                            <div class="flex gap-3 mt-6">
                                <button type="button" id="cancel-contact-ui" class="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors">Cancel</button>
                                <button type="submit" class="flex-1 px-4 py-2 bg-[#FB4F14] text-white rounded-lg hover:bg-orange-600 transition-colors">Send Message</button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
            document.body.appendChild(contactModal);
            contactModal.querySelector('#cancel-contact-ui').addEventListener('click', function() { contactModal.classList.add('hidden'); });
            contactModal.addEventListener('click', function(e) { if (e.target === contactModal) contactModal.classList.add('hidden'); });
            contactModal.querySelector('#contact-form-userinfo').addEventListener('submit', async function(e) {
                e.preventDefault();
                try {
                    const response = await fetch('/api/support/contact', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: document.getElementById('contact-name-ui').value.trim(),
                            email: document.getElementById('contact-email-ui').value.trim(),
                            message: document.getElementById('contact-message-ui').value.trim(),
                        })
                    });
                    if (response.ok) {
                        alert("Thank you for contacting support! We'll get back to you soon.");
                        this.reset();
                        contactModal.classList.add('hidden');
                    } else {
                        alert('There was a problem sending your message. Please try again.');
                    }
                } catch (_) {
                    alert('There was a problem sending your message. Please try again.');
                }
            });
        }
        contactModal.classList.remove('hidden');
    }

    // ── Interactive Guide Objects ──────────────────────────────────────────
    let currentUserInfoGuide = null;

    function rowOf(id) {
        const el = document.getElementById(id);
        return el ? (el.closest('.srow') || el.closest('label') || el) : null;
    }

    const personalizationGuide = {
        id: 'personalization',
        steps: [
            {
                title: 'Age Group',
                content: 'Set whether the user is under 13 or 13+. Marking a user as under 13 triggers COPPA compliance — parental consent is required before personalized learning features activate.',
                action: function() {
                    window.showUserInfoSection && window.showUserInfoSection('section-personalization');
                    setTimeout(function() {
                        const el = rowOf('flag-age-group');
                        if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                    }, 300);
                },
                cleanup: function() {
                    const el = rowOf('flag-age-group');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Use Entered Details',
                content: 'When enabled, the User Profile narrative and People data are used to personalize AI responses. Turn this on after entering a user narrative to activate personalization.',
                action: function() {
                    const el = rowOf('flag-use-entered-details');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = rowOf('flag-use-entered-details');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Learn from History',
                content: 'When enabled, Bravo analyses past conversations to automatically learn and remember user preferences. Enabling this reveals the Auto-approve sub-option.',
                action: function() {
                    const el = rowOf('flag-learn-from-history');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = rowOf('flag-learn-from-history');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Auto-approve Learned Facts',
                content: 'When Learn from History is on, this sub-option lets learned facts bypass the approval queue and be applied to the profile immediately. Leave off to review facts manually in Learning & History.',
                action: function() {
                    const el = rowOf('flag-auto-approve');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = rowOf('flag-auto-approve');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Save Personalization',
                content: 'Click this button to save the Age Group, Use Entered Details, and Learn from History settings.',
                action: function() {
                    const el = document.getElementById('flags-save-btn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('flags-save-btn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Download User Data',
                content: "Downloads a file containing the user's narrative, learned facts, interview answers, chat history, activity log, and consent record. Use this for data portability or compliance requests.",
                action: function() {
                    const el = rowOf('download-my-data-btn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = rowOf('download-my-data-btn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            }
        ]
    };

    const moodGuide = {
        id: 'mood',
        steps: [
            {
                title: 'Mood Dropdown',
                content: "Choose the user's current session mood. The mood affects how Bravo interacts — for example, a happy mood produces upbeat responses, while a calm mood produces gentler interactions.",
                action: function() {
                    window.showUserInfoSection && window.showUserInfoSection('section-mood');
                    setTimeout(function() {
                        const el = document.getElementById('currentMood');
                        if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                    }, 300);
                },
                cleanup: function() {
                    const el = document.getElementById('currentMood');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Save Mood',
                content: 'Click Save to apply the selected mood to the current session. The mood remains active until it is changed or cleared.',
                action: function() {
                    const el = document.getElementById('saveMoodBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('saveMoodBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Clear Mood',
                content: 'Click Clear to remove the current mood setting, resetting Bravo to its default interaction style with no mood modifier.',
                action: function() {
                    const el = document.getElementById('clearMoodBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('clearMoodBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            }
        ]
    };

    const profileGuide = {
        id: 'profile',
        steps: [
            {
                title: 'Start Interview',
                content: "Click Start Interview to launch an AI-guided interview that asks questions about the user and automatically fills in their name, birthday, and narrative. This is the fastest way to build a complete profile.",
                action: function() {
                    window.showUserInfoSection && window.showUserInfoSection('section-profile');
                    setTimeout(function() {
                        const el = document.getElementById('startInterviewButton');
                        if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                    }, 300);
                },
                cleanup: function() {
                    const el = document.getElementById('startInterviewButton');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: "User's Name",
                content: "Enter the user's preferred name. This is how Bravo will refer to the user — used for pronouns like I, me, myself, and mine in AI responses.",
                action: function() {
                    const el = document.getElementById('userName');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('userName');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Profile Picture',
                content: "Upload a photo for the user. This image represents the user's personal pronouns (I, me, mine) on the communication board. Supported formats: JPG, PNG, WebP.",
                action: function() {
                    const el = document.getElementById('uploadProfileImageBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('uploadProfileImageBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'User Narrative',
                content: "Enter a detailed narrative about the user — personality traits, hobbies, interests, family, pets, favorite topics, and anything relevant. The more detail, the better Bravo can personalize responses. Use Entered Details must be on in Personalization for this to take effect.",
                action: function() {
                    const el = document.getElementById('user-info');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('user-info');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'AI Option Overrides',
                content: 'Define hard inclusion and exclusion rules for AI-generated options. Exclusions prevent specific activities from appearing (e.g., eating independently, walking independently). Inclusions allow topics that are normally restricted (e.g., adult topics, profanity).',
                action: function() {
                    const el = document.getElementById('openAiOverridesModalBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('openAiOverridesModalBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: "User's Birthday",
                content: "Enter the user's full birthdate including the year so Bravo can calculate age, provide age-appropriate content, and acknowledge birthdays.",
                action: function() {
                    const el = document.getElementById('userBirthdate');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('userBirthdate');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Save User Name, Info & Birthday',
                content: "Click this button to save the user's name, narrative, and birthday together. A success message will appear when saved.",
                action: function() {
                    const el = document.getElementById('saveInfoButton');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('saveInfoButton');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            }
        ]
    };

    const historyGuide = {
        id: 'history',
        steps: [
            {
                title: 'AI-Extracted Narrative',
                content: "This section shows what Bravo has learned from the user's conversation history — including a summary, approved facts, known preferences, and recent greetings. It is automatically extracted from messages older than 7 days.",
                action: function() {
                    window.showUserInfoSection && window.showUserInfoSection('section-history');
                    setTimeout(function() {
                        const el = document.getElementById('chat-narrative-content');
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 300);
                },
                cleanup: function() {}
            },
            {
                title: 'Refresh Narrative',
                content: 'Click Refresh to reload the latest extracted narrative, facts, preferences, and greetings from the server.',
                action: function() {
                    const el = document.getElementById('refreshChatNarrativeBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('refreshChatNarrativeBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Pending Learned Facts',
                content: "These are facts Bravo learned from conversation history that are waiting for a guardian to approve or discard. Approved facts are added to the user's profile. Enable Auto-approve in Personalization to skip this queue.",
                action: function() {
                    const el = document.getElementById('refreshPendingBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('refreshPendingBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            }
        ]
    };

    const familyGuide = {
        id: 'family',
        steps: [
            {
                title: 'Start Interview (Family & Friends)',
                content: 'Click Start Interview to add a family member or friend via a guided audio interview. Bravo asks you questions about the person and automatically fills in their name, relationship, and background.',
                action: function() {
                    window.showUserInfoSection && window.showUserInfoSection('section-family');
                    setTimeout(function() {
                        const el = document.getElementById('startFamilyFriendsInterviewBtn');
                        if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                    }, 300);
                },
                cleanup: function() {
                    const el = document.getElementById('startFamilyFriendsInterviewBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Friends & Family Table',
                content: 'Add and edit entries manually. Each row has: Name (how they are addressed), Relationship (dropdown), About (background and interests), and Birthday in MM-DD format.',
                action: function() {
                    const el = document.getElementById('friendsFamilyTable');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('friendsFamilyTable');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Add Person',
                content: 'Click Add Person to append a new empty row to the table for manual entry. Fill in the fields and then click Save Family & Friends.',
                action: function() {
                    const el = document.getElementById('addFriendsFamilyRow');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('addFriendsFamilyRow');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Manage Relationship Types',
                content: 'Click this button to open the Relationship Types modal where you can add new relationship labels (e.g., Therapist, Neighbor) or remove ones you no longer need.',
                action: function() {
                    const el = document.getElementById('manageRelationshipsBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('manageRelationshipsBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Save Family & Friends',
                content: 'Click this button to save all entries in the Friends & Family table. A success message will appear when saved.',
                action: function() {
                    const el = document.getElementById('saveFriendsFamilyButton');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('saveFriendsFamilyButton');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            }
        ]
    };

    const imagesGuide = {
        id: 'images',
        steps: [
            {
                title: 'Select Image File',
                content: 'Choose an image file to upload for this user profile. Supported formats: JPG, PNG, WebP. Maximum file size: 5MB.',
                action: function() {
                    window.showUserInfoSection && window.showUserInfoSection('section-images');
                    setTimeout(function() {
                        const el = document.getElementById('customImageFile');
                        if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                    }, 300);
                },
                cleanup: function() {
                    const el = document.getElementById('customImageFile');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Tags',
                content: 'Enter comma-separated tags that describe who or what the image shows. Tags are matched against button labels on communication boards — e.g., "dad, daddy, father" displays this image on any button with those labels.',
                action: function() {
                    const el = document.getElementById('customImagePrimaryTag');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('customImagePrimaryTag');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Upload Image',
                content: "Click Upload Image to save the selected file and its tags to the user's profile. A progress bar appears during upload.",
                action: function() {
                    const el = document.getElementById('uploadCustomImageBtn');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('uploadCustomImageBtn');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            },
            {
                title: 'Uploaded Images Grid',
                content: 'All uploaded custom images appear here. Click any image to open a management modal where you can edit its tags or delete it.',
                action: function() {
                    const el = document.getElementById('customImagesList');
                    if (el) { el.classList.add('guide-highlight-target'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                },
                cleanup: function() {
                    const el = document.getElementById('customImagesList');
                    if (el) el.classList.remove('guide-highlight-target');
                }
            }
        ]
    };

    // ── Guide launcher ─────────────────────────────────────────────────────
    window.startUserInfoGuide = function(guideId) {
        closeHelpModal();
        const guides = {
            'personalization': personalizationGuide,
            'mood': moodGuide,
            'profile': profileGuide,
            'history': historyGuide,
            'family': familyGuide,
            'images': imagesGuide
        };
        const guide = guides[guideId];
        if (guide) {
            currentUserInfoGuide = { guide: guide, currentStep: 0 };
            showUserInfoGuideWindow();
        }
    };

    // ── Guide window ───────────────────────────────────────────────────────
    function showUserInfoGuideWindow() {
        if (!currentUserInfoGuide) return;
        let guideWindow = document.getElementById('userinfo-guide-window');
        if (!guideWindow) {
            guideWindow = document.createElement('div');
            guideWindow.id = 'userinfo-guide-window';
            guideWindow.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 400px; max-height: 500px; background: white; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); z-index: 9999; display: flex; flex-direction: column;';
            guideWindow.innerHTML = `
                <div style="background: linear-gradient(135deg, #FB4F14 0%, #F97316 100%); color: white; padding: 16px; border-radius: 12px 12px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div id="userinfo-guide-title" style="font-weight: bold; font-size: 18px;"></div>
                        <div id="userinfo-guide-progress" style="font-size: 12px; opacity: 0.9; margin-top: 4px;"></div>
                    </div>
                    <button id="userinfo-guide-close" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer; padding: 0; width: 32px; height: 32px;">&times;</button>
                </div>
                <div id="userinfo-guide-content" style="padding: 20px; flex: 1; overflow-y: auto;"></div>
                <div style="border-top: 1px solid #e5e7eb; padding: 16px; display: flex; justify-content: space-between; align-items: center; background: #f9fafb; border-radius: 0 0 12px 12px;">
                    <button id="userinfo-guide-prev" style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                        <i class="fas fa-arrow-left"></i> Previous
                    </button>
                    <div id="userinfo-guide-step-indicator" style="display: flex; gap: 8px;"></div>
                    <button id="userinfo-guide-next" style="padding: 8px 16px; background: #FB4F14; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                        Next <i class="fas fa-arrow-right"></i>
                    </button>
                </div>
            `;
            document.body.appendChild(guideWindow);
            document.getElementById('userinfo-guide-close').addEventListener('click', closeUserInfoGuide);
            document.getElementById('userinfo-guide-prev').addEventListener('click', previousUserInfoGuideStep);
            document.getElementById('userinfo-guide-next').addEventListener('click', nextUserInfoGuideStep);
        }
        guideWindow.style.display = 'flex';
        updateUserInfoGuideStep();
    }

    function updateUserInfoGuideStep() {
        if (!currentUserInfoGuide) return;
        const guide = currentUserInfoGuide.guide;
        const step = guide.steps[currentUserInfoGuide.currentStep];

        document.getElementById('userinfo-guide-title').textContent = step.title;
        document.getElementById('userinfo-guide-progress').textContent =
            'Step ' + (currentUserInfoGuide.currentStep + 1) + ' of ' + guide.steps.length;
        document.getElementById('userinfo-guide-content').innerHTML =
            '<p style="color: #374151; line-height: 1.6;">' + step.content + '</p>';

        const indicatorContainer = document.getElementById('userinfo-guide-step-indicator');
        indicatorContainer.innerHTML = '';
        for (let i = 0; i < guide.steps.length; i++) {
            const dot = document.createElement('div');
            dot.style.cssText = 'width: 10px; height: 10px; border-radius: 50%; transition: all 0.3s;';
            if (i < currentUserInfoGuide.currentStep) dot.style.background = '#10b981';
            else if (i === currentUserInfoGuide.currentStep) { dot.style.background = '#FB4F14'; dot.style.transform = 'scale(1.3)'; }
            else dot.style.background = '#d1d5db';
            indicatorContainer.appendChild(dot);
        }

        const prevBtn = document.getElementById('userinfo-guide-prev');
        const nextBtn = document.getElementById('userinfo-guide-next');
        prevBtn.disabled = currentUserInfoGuide.currentStep === 0;
        prevBtn.style.opacity = prevBtn.disabled ? '0.5' : '1';
        prevBtn.style.cursor = prevBtn.disabled ? 'not-allowed' : 'pointer';
        const isLastStep = currentUserInfoGuide.currentStep === guide.steps.length - 1;
        nextBtn.innerHTML = isLastStep ? 'Complete <i class="fas fa-check"></i>' : 'Next <i class="fas fa-arrow-right"></i>';

        if (step.action) {
            if (currentUserInfoGuide.currentStep > 0) {
                const prevStep = guide.steps[currentUserInfoGuide.currentStep - 1];
                if (prevStep.cleanup) prevStep.cleanup();
            }
            step.action();
        }
    }

    function nextUserInfoGuideStep() {
        if (!currentUserInfoGuide) return;
        const guide = currentUserInfoGuide.guide;
        if (currentUserInfoGuide.currentStep < guide.steps.length - 1) {
            currentUserInfoGuide.currentStep++;
            updateUserInfoGuideStep();
        } else {
            closeUserInfoGuide();
        }
    }

    function previousUserInfoGuideStep() {
        if (!currentUserInfoGuide) return;
        if (currentUserInfoGuide.currentStep > 0) {
            currentUserInfoGuide.currentStep--;
            updateUserInfoGuideStep();
        }
    }

    function closeUserInfoGuide() {
        if (!currentUserInfoGuide) return;
        const guide = currentUserInfoGuide.guide;
        const step = guide.steps[currentUserInfoGuide.currentStep];
        if (step.cleanup) step.cleanup();
        const guideWindow = document.getElementById('userinfo-guide-window');
        if (guideWindow) guideWindow.style.display = 'none';
        currentUserInfoGuide = null;
    }
});
