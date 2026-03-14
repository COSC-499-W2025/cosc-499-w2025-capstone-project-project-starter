/**
 * Core utility functions for dashboard
 */

/**
 * Escape HTML special characters to prevent XSS attacks
 * @param {string} str - String to be escaped
 * @returns {string} - Escaped safe string
 */
function escapeHtml(str) {
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

/**
 * Display message notification
 * @param {string} text - Message text
 * @param {string} type - Message type: 'success', 'error', 'info'
 */
function showMessage(text, type) {
    const msg = document.getElementById('messageBox');
    msg.textContent = text;
    msg.className = `message ${type}`;
    msg.style.display = 'block';
    setTimeout(() => msg.style.display = 'none', 5000);
}

/**
 * Show error toast notification
 * @param {string} message - Error message
 * @param {string} requestId - Request ID
 */
function showErrorToast(message, requestId) {
    const toast = document.getElementById('error-toast');
    document.getElementById('toast-message').innerText = message;
    
    // Display the specific X-Request-ID or a fallback
    document.getElementById('toast-request-id').innerText = requestId || "N/A";
    
    toast.classList.add('show');
    toast.classList.remove('hidden');

    setTimeout(() => {
        closeErrorToast();
    }, 8000);
}

/**
 * Close error toast notification
 */
function closeErrorToast() {
    const toast = document.getElementById('error-toast');
    toast.classList.remove('show');
}

/**
 * Render result to container
 * @param {HTMLElement} container - Target container
 * @param {string} html - HTML content
 */
function renderResult(container, html) {
    container.innerHTML = html;
}

/**
 * Render error message
 * @param {HTMLElement} container - Target container
 * @param {string} message - Error message
 */
function renderError(container, message) {
    const safe = escapeHtml(message);
    if (container) {
        // Do not overwrite complex HTML and prepend a message block instead.
        container.insertAdjacentHTML('afterbegin', `<div class="message error">${safe}</div>`);
    }
    showMessage(safe, "error");
}

/**
 * Render success message
 * @param {HTMLElement} container - Target container
 * @param {string} message - Success message
 */
function renderSuccess(container, message) {
    const safe = escapeHtml(message);
    if (container) {
        // Do not overwrite complex HTML and prepend a message block instead.
        container.insertAdjacentHTML('afterbegin', `<div class="message success">${safe}</div>`);
    }
    showMessage(safe, "success");
}

/**
 * Safely set element text content
 * @param {string} id - Element ID
 * @param {any} val - Value to set
 */
function setTextSafe(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}
