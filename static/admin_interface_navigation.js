(function () {
    let cachedPreference = null;
    let unsavedIndicatorEl = null;
    let isUnsaved = false;
    let isSaving = false;
    let lastSaveIntentTs = 0;
    let cachedSaveActionElements = [];

    function buildAuthHeaders() {
        const headers = {};
        const token = sessionStorage.getItem('firebaseIdToken');
        const userId = sessionStorage.getItem('currentAacUserId');
        const adminTargetAccountId = sessionStorage.getItem('adminTargetAccountId');

        if (token) {
            headers.Authorization = 'Bearer ' + token;
        }
        if (userId) {
            headers['X-User-ID'] = userId;
        }
        if (adminTargetAccountId) {
            headers['X-Admin-Target-Account'] = adminTargetAccountId;
        }

        return headers;
    }

    async function fetchInterfacePreference() {
        if (cachedPreference !== null) {
            return cachedPreference;
        }

        try {
            const response = await fetch('/api/interface-preference', {
                method: 'GET',
                credentials: 'include',
                headers: buildAuthHeaders()
            });

            if (!response.ok) {
                cachedPreference = false;
                return cachedPreference;
            }

            const data = await response.json();
            cachedPreference = Boolean(data && data.useTapInterface);
            return cachedPreference;
        } catch (error) {
            console.error('Failed to fetch interface preference:', error);
            cachedPreference = false;
            return cachedPreference;
        }
    }

    async function resolveHomeUrl() {
        const useTapInterface = await fetchInterfacePreference();
        return useTapInterface ? 'tap_interface.html' : 'gridpage.html?page=home';
    }

    async function resolvePagesBoardsUrl() {
        const useTapInterface = await fetchInterfacePreference();
        return useTapInterface ? 'tap_board_builder.html' : 'admin_pages.html';
    }

    async function navigateToHome() {
        window.location.href = await resolveHomeUrl();
    }

    async function navigateToPagesBoards() {
        window.location.href = await resolvePagesBoardsUrl();
    }

    function interceptClick(element, destinationResolver) {
        if (!element) {
            return;
        }

        element.addEventListener('click', async function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            try {
                window.location.href = await destinationResolver();
            } catch (error) {
                console.error('Failed to resolve admin toolbar navigation:', error);
            }
        }, true);
    }

    function wireAdminToolbarNavigation() {
        const homeButtons = document.querySelectorAll(".page-banner [title='Home']");
        const pagesBoardsButtons = document.querySelectorAll(".admin-toolbar [title='Pages & Buttons']");

        homeButtons.forEach(function (element) {
            interceptClick(element, resolveHomeUrl);
        });

        pagesBoardsButtons.forEach(function (element) {
            interceptClick(element, resolvePagesBoardsUrl);
        });
    }

    function isAdminPage() {
        const path = (window.location.pathname || '').toLowerCase();
        const title = (document.title || '').toLowerCase();
        return path.includes('admin') || title.includes('admin') || Boolean(document.querySelector('.admin-toolbar'));
    }

    function ensureIndicatorStyles() {
        if (document.getElementById('admin-unsaved-indicator-style')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'admin-unsaved-indicator-style';
        style.textContent = [
            '#admin-unsaved-indicator {',
            'position: fixed;',
            'right: 20px;',
            'bottom: 20px;',
            'z-index: 2147483000;',
            'display: none;',
            'align-items: center;',
            'gap: 8px;',
            'padding: 10px 14px;',
            'border-radius: 999px;',
            'background: #b45309;',
            'color: #ffffff;',
            'font-size: 13px;',
            'font-weight: 700;',
            'box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);',
            'animation: none;',
            '}',
            '@keyframes adminUnsavedPulse {',
            '0% { transform: scale(1); box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25); }',
            '50% { transform: scale(1.04); box-shadow: 0 12px 30px rgba(180, 83, 9, 0.5); }',
            '100% { transform: scale(1); box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25); }',
            '}',
            '#admin-unsaved-indicator.is-dirty {',
            'animation: adminUnsavedPulse 1.35s ease-in-out infinite;',
            '}',
            '#admin-unsaved-indicator.is-saving {',
            'background: #1d4ed8;',
            'animation: none;',
            '}',
            '.admin-save-dirty {',
            'outline: 2px solid #f59e0b !important;',
            'outline-offset: 2px;',
            'box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.18), 0 8px 20px rgba(245, 158, 11, 0.25) !important;',
            'animation: adminSavePulse 1.25s ease-in-out infinite;',
            '}',
            '.admin-save-saving {',
            'outline: 2px solid #3b82f6 !important;',
            'outline-offset: 2px;',
            'box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2), 0 8px 20px rgba(59, 130, 246, 0.28) !important;',
            'animation: none !important;',
            '}',
            '@keyframes adminSavePulse {',
            '0% { transform: scale(1); }',
            '50% { transform: scale(1.03); }',
            '100% { transform: scale(1); }',
            '}',
            '#admin-unsaved-indicator .dot {',
            'width: 8px;',
            'height: 8px;',
            'border-radius: 999px;',
            'background: rgba(255, 255, 255, 0.95);',
            '}',
            '@media (max-width: 640px) {',
            '#admin-unsaved-indicator {',
            'right: 12px;',
            'bottom: 12px;',
            'font-size: 12px;',
            'padding: 8px 12px;',
            '}',
            '}'
        ].join('');
        document.head.appendChild(style);
    }

    function ensureIndicatorElement() {
        if (unsavedIndicatorEl) {
            return unsavedIndicatorEl;
        }

        ensureIndicatorStyles();
        unsavedIndicatorEl = document.createElement('div');
        unsavedIndicatorEl.id = 'admin-unsaved-indicator';
        unsavedIndicatorEl.setAttribute('aria-live', 'polite');
        unsavedIndicatorEl.innerHTML = '<span class="dot" aria-hidden="true"></span><span class="label">Unsaved changes</span>';
        document.body.appendChild(unsavedIndicatorEl);
        return unsavedIndicatorEl;
    }

    function renderIndicator() {
        if (!unsavedIndicatorEl) {
            return;
        }

        if (!isUnsaved && !isSaving) {
            unsavedIndicatorEl.style.display = 'none';
            unsavedIndicatorEl.classList.remove('is-saving');
            unsavedIndicatorEl.classList.remove('is-dirty');
            updateSaveActionHighlights();
            return;
        }

        const label = unsavedIndicatorEl.querySelector('.label');
        if (label) {
            label.textContent = isSaving ? 'Saving changes...' : 'Unsaved changes';
        }

        unsavedIndicatorEl.classList.toggle('is-saving', Boolean(isSaving));
        unsavedIndicatorEl.classList.toggle('is-dirty', Boolean(isUnsaved && !isSaving));
        unsavedIndicatorEl.style.display = 'inline-flex';
        updateSaveActionHighlights();
    }

    function markDirty() {
        isUnsaved = true;
        isSaving = false;
        renderIndicator();
    }

    function markSaving() {
        if (!isUnsaved) {
            return;
        }
        isSaving = true;
        renderIndicator();
    }

    function markSaved() {
        isUnsaved = false;
        isSaving = false;
        renderIndicator();
    }

    function isSaveActionElement(element) {
        if (!element || typeof element.closest !== 'function') {
            return false;
        }

        const control = element.closest('button, input[type="button"], input[type="submit"], a, [role="button"]');
        if (!control) {
            return false;
        }

        const attrs = [
            control.id,
            control.className,
            control.getAttribute('name'),
            control.getAttribute('title'),
            control.getAttribute('aria-label'),
            control.getAttribute('data-action')
        ].filter(Boolean).join(' ').toLowerCase();

        const text = (control.textContent || '').trim().toLowerCase();
        return attrs.includes('save') || text.includes('save');
    }

    function getSaveActionElements() {
        const controls = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a, [role="button"]'));
        return controls.filter(function (element) {
            return isSaveActionElement(element);
        });
    }

    function updateSaveActionHighlights() {
        cachedSaveActionElements = getSaveActionElements();
        cachedSaveActionElements.forEach(function (element) {
            element.classList.remove('admin-save-dirty', 'admin-save-saving');
            if (isSaving) {
                element.classList.add('admin-save-saving');
            } else if (isUnsaved) {
                element.classList.add('admin-save-dirty');
            }
        });
    }

    function isWriteMethod(method) {
        const m = String(method || 'GET').toUpperCase();
        return m !== 'GET' && m !== 'HEAD' && m !== 'OPTIONS';
    }

    function setupUnsavedIndicator() {
        if (!isAdminPage()) {
            return;
        }

        ensureIndicatorElement();
        updateSaveActionHighlights();

        window.adminUnsavedIndicator = {
            markDirty: markDirty,
            markSaved: markSaved,
            markSaving: markSaving,
            isDirty: function () { return Boolean(isUnsaved); }
        };

        document.addEventListener('input', function (event) {
            if (event.isTrusted) {
                markDirty();
            }
        }, true);

        document.addEventListener('change', function (event) {
            if (event.isTrusted) {
                markDirty();
            }
        }, true);

        document.addEventListener('click', function (event) {
            if (!event.isTrusted) {
                return;
            }

            if (isSaveActionElement(event.target)) {
                lastSaveIntentTs = Date.now();
                markSaving();
            }
        }, true);

        document.addEventListener('DOMContentLoaded', updateSaveActionHighlights);

        window.addEventListener('beforeunload', function (event) {
            if (!isUnsaved) {
                return;
            }

            event.preventDefault();
            event.returnValue = '';
        });

        const originalFetch = window.fetch;
        if (typeof originalFetch === 'function') {
            window.fetch = function (input, init) {
                let method = 'GET';
                if (init && init.method) {
                    method = init.method;
                } else if (input && typeof input === 'object' && input.method) {
                    method = input.method;
                }

                return originalFetch.apply(this, arguments).then(function (response) {
                    const recentlyClickedSave = (Date.now() - lastSaveIntentTs) < 12000;
                    if (recentlyClickedSave && isWriteMethod(method) && response && response.ok) {
                        markSaved();
                    }
                    return response;
                });
            };
        }

        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function (method) {
            this.__adminMethod = method;
            return originalOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function () {
            this.addEventListener('load', function () {
                const recentlyClickedSave = (Date.now() - lastSaveIntentTs) < 12000;
                if (recentlyClickedSave && isWriteMethod(this.__adminMethod) && this.status >= 200 && this.status < 300) {
                    markSaved();
                }
            });
            return originalSend.apply(this, arguments);
        };
    }

    window.navigateToHome = navigateToHome;
    window.navigateToPagesBoards = navigateToPagesBoards;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            wireAdminToolbarNavigation();
            setupUnsavedIndicator();
        });
    } else {
        wireAdminToolbarNavigation();
        setupUnsavedIndicator();
    }
})();
