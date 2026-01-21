/**
 * Global AJAX error handler for subscription checks
 * Automatically handles 403 responses from subscription_required decorator
 */

// Add global fetch wrapper
const originalFetch = window.fetch;
window.fetch = function(...args) {
    return originalFetch.apply(this, args)
        .then(response => {
            // Check if subscription error (403)
            if (response.status === 403) {
                response.clone().json().then(data => {
                    if (data.error) {
                        alert(data.error);
                        if (data.redirect) {
                            window.location.href = data.redirect;
                        }
                    }
                }).catch(() => {
                    // If not JSON, just return the response
                });
            }
            return response;
        });
};

// Alternative: Add to each AJAX call
async function handleSubscriptionResponse(response) {
    if (response.status === 403) {
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        }
        return null;
    }
    return response;
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { handleSubscriptionResponse };
}
