(function () {
    let cachedPreference = null;

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

    window.navigateToHome = navigateToHome;
    window.navigateToPagesBoards = navigateToPagesBoards;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireAdminToolbarNavigation);
    } else {
        wireAdminToolbarNavigation();
    }
})();
