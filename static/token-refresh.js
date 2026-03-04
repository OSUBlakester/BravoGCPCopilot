/**
 * Firebase Token Refresh Module
 * 
 * Keeps Firebase ID tokens fresh for pages that rely on sessionStorage tokens.
 * Firebase ID tokens expire after 1 hour. This module:
 * 1. Initializes the Firebase Auth SDK (if not already initialized)
 * 2. Listens for auth state changes and auto-updates the token in sessionStorage
 * 3. Sets up a proactive refresh timer (every 45 minutes)
 * 4. Exposes refreshFirebaseToken() for on-demand refresh (e.g., on 401)
 * 
 * Usage: Include Firebase SDK scripts BEFORE this script:
 *   <script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-app-compat.js"></script>
 *   <script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-auth-compat.js"></script>
 *   <script src="/static/token-refresh.js"></script>
 */

(function() {
    'use strict';

    const TOKEN_KEY = 'firebaseIdToken';
    const REFRESH_INTERVAL_MS = 45 * 60 * 1000; // 45 minutes
    let refreshTimer = null;
    let isInitialized = false;
    let initPromise = null;

    /**
     * Initialize Firebase and set up token auto-refresh.
     * Safe to call multiple times — will only initialize once.
     */
    async function initTokenRefresh() {
        if (initPromise) return initPromise;
        
        initPromise = _doInit();
        return initPromise;
    }

    async function _doInit() {
        if (isInitialized) return;

        try {
            // Initialize Firebase if not already done
            if (!firebase.apps.length) {
                const response = await fetch('/api/frontend-config');
                if (!response.ok) throw new Error(`Config fetch failed: ${response.status}`);
                const config = await response.json();
                if (!config.apiKey) throw new Error('Invalid Firebase config');
                firebase.initializeApp(config);
                console.log('[TokenRefresh] Firebase initialized for project:', config.projectId);
            }

            // Listen for auth state changes
            firebase.auth().onAuthStateChanged(async (user) => {
                if (user) {
                    try {
                        const token = await user.getIdToken();
                        sessionStorage.setItem(TOKEN_KEY, token);
                        console.log('[TokenRefresh] Token updated via onAuthStateChanged');
                    } catch (e) {
                        console.warn('[TokenRefresh] Failed to get token in onAuthStateChanged:', e);
                    }
                } else {
                    console.log('[TokenRefresh] No user signed in');
                }
            });

            // Set up proactive refresh timer
            _startRefreshTimer();

            isInitialized = true;
            console.log('[TokenRefresh] Initialized with', REFRESH_INTERVAL_MS / 60000, 'min refresh interval');
        } catch (e) {
            console.error('[TokenRefresh] Initialization error:', e);
            // Don't block the app — the existing sessionStorage token may still be valid
        }
    }

    /**
     * Force-refresh the Firebase ID token and update sessionStorage.
     * Returns the new token, or null if refresh failed.
     * Use this on 401 responses before retrying the request.
     */
    async function refreshFirebaseToken() {
        try {
            // Ensure Firebase is initialized
            await initTokenRefresh();

            const user = firebase.auth().currentUser;
            if (!user) {
                console.warn('[TokenRefresh] No current user — cannot refresh token');
                return null;
            }

            // Force refresh (true = bypass cache)
            const newToken = await user.getIdToken(true);
            sessionStorage.setItem(TOKEN_KEY, newToken);
            console.log('[TokenRefresh] Token force-refreshed successfully');
            return newToken;
        } catch (e) {
            console.error('[TokenRefresh] Force refresh failed:', e);
            return null;
        }
    }

    function _startRefreshTimer() {
        if (refreshTimer) clearInterval(refreshTimer);
        
        refreshTimer = setInterval(async () => {
            console.log('[TokenRefresh] Proactive refresh triggered');
            await refreshFirebaseToken();
        }, REFRESH_INTERVAL_MS);
    }

    // Expose globally
    window.initTokenRefresh = initTokenRefresh;
    window.refreshFirebaseToken = refreshFirebaseToken;

    // Auto-initialize when the script loads (non-blocking)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initTokenRefresh());
    } else {
        initTokenRefresh();
    }
})();
