function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function updateStatus(bookingId, status) {
    const csrf_token = getCookie('csrftoken');
    const urlPrefix = window.location.pathname.split('/').slice(0, 2).join('/');
    
    try {
        const response = await fetch(`${urlPrefix}/bookings/update-status/${bookingId}/`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': `${csrf_token}`
            },
            body: JSON.stringify({ status: status })
        });
        
        if (response.ok) {
            location.reload();
        } else {
            alert('Error updating booking status');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating booking status');
    }
}

// Confirm booking
async function confirmBooking(bookingId) {
    if (!confirm('Confirm this booking?')) return;
    await updateStatus(bookingId, '1'); // 1 = Confirmed
}

// Edit booking - redirect to edit page
function editBooking(bookingId) {
    const urlPrefix = window.location.pathname.split('/').slice(0, 2).join('/');
    window.location.href = `${urlPrefix}/bookings/edit/${bookingId}/`;
}

// Delete booking
async function deleteBooking(bookingId) {
    if (!confirm('Are you sure you want to delete this booking?')) return;
    
    const csrf_token = getCookie('csrftoken');
    const urlPrefix = window.location.pathname.split('/').slice(0, 2).join('/');
    
    try {
        const response = await fetch(`${urlPrefix}/bookings/api/delete-booking/${bookingId}/`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': `${csrf_token}`
            }
        });
        
        if (response.ok) {
            alert('Booking deleted successfully');
            location.reload();
        } else {
            const data = await response.json();
            alert('Error deleting booking: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting booking: ' + error.message);
    }
}

function buildCalendar(rawBookings, staffList, currentDate, dayStart, dayEnd) {
    const calendarEl = document.getElementById('calendar');
    
    // Generate distinct colors for each staff member
    const staffColors = [
        { bg: '#3b82f6', border: '#1e40af' }, // Blue
        { bg: '#10b981', border: '#047857' }, // Green
        { bg: '#f59e0b', border: '#d97706' }, // Amber
        { bg: '#8b5cf6', border: '#6d28d9' }, // Purple
        { bg: '#ec4899', border: '#be185d' }, // Pink
        { bg: '#14b8a6', border: '#0d9488' }, // Teal
        { bg: '#f97316', border: '#ea580c' }, // Orange
        { bg: '#06b6d4', border: '#0891b2' }, // Cyan
        { bg: '#84cc16', border: '#65a30d' }, // Lime
        { bg: '#a855f7', border: '#7e22ce' }, // Violet
    ];
    
    // Create a map of staff ID to colors
    const staffColorMap = {};
    staffList.forEach((s, index) => {
        const colorIndex = index % staffColors.length;
        staffColorMap[s.id] = staffColors[colorIndex];
    });
    
    // Convert staff to Toast UI Calendar calendars with distinct colors
    const calendars = staffList.map((s, index) => {
        const colorIndex = index % staffColors.length;
        return {
            id: String(s.id),
            name: s.title,
            backgroundColor: staffColors[colorIndex].bg,
            borderColor: staffColors[colorIndex].border
        };
    });
    
    // Add "All Staff" view
    calendars.unshift({
        id: 'all',
        name: 'All Staff',
        backgroundColor: '#e5e7eb',
        borderColor: '#9ca3af'
    });
    
    // Convert events to Toast UI format - use staff colors with opacity for pending
    const allEvents = rawBookings.map(b => {
        const staffColor = staffColorMap[b.extendedProps.staff_id] || staffColors[0];
        const isPending = b.extendedProps.status == 0;
        
        return {
            id: String(b.id),
            calendarId: String(b.extendedProps.staff_id),
            title: b.title,
            start: new Date(b.start),
            end: new Date(b.end),
            backgroundColor: staffColor.bg,
            borderColor: staffColor.border,
            color: '#ffffff', // white text
            isReadOnly: false,
            raw: {
                booking_id: b.id,
                staff_id: b.extendedProps.staff_id,
                status: b.extendedProps.status,
                service: b.extendedProps.service,
                customer: b.extendedProps.customer,
                isPending: isPending
            }
        };
    });
    
    // Initialize Toast UI Calendar
    const calendar = new tui.Calendar(calendarEl, {
        defaultView: 'day',
        isReadOnly: false,
        useFormPopup: false,
        useDetailPopup: false, // Disable default popup to use custom modal
        calendars: calendars,
        template: {
            time(event) {
                const isPending = event.raw.isPending || event.raw.status == 0;
                const opacity = isPending ? 0.7 : 1;
                const startDate = event.start.toDate ? event.start.toDate() : new Date(event.start);
                return `<div style="color: white; opacity: ${opacity};">
                            <span>${event.title}</span><br/>
                            <span>(${staffList.find(s => String(s.id) === String(event.calendarId))?.title || 'Staff'})</span><br/>
                            <span>${startDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        </div>`;
            }
        },
        week: {
            hourStart: dayStart,
            hourEnd: dayEnd,
            eventView: ['time'],
            taskView: false
        },
        month: {
            dayNames: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            startDayOfWeek: 1
        },
        timezone: {
            zones: []
        }
    });
    
    // Set the calendar to the current date from Django
    calendar.setDate(currentDate);
    
    // Set events
    calendar.createEvents(allEvents);

    // Handle clicking on events - show custom modal
    calendar.on('clickEvent', ({ event }) => {
        showBookingModal(event);
    });

    // Handle event updates (drag & drop and resize)
    calendar.on('beforeUpdateEvent', (eventData) => {
        const { event, changes } = eventData;
        const bookingId = event.raw.booking_id;
        
        let startDate = changes.start ? changes.start.toDate() : event.start.toDate();
        const startTime = startDate.toTimeString().substring(0, 5);
        let endDate = changes.end ? changes.end.toDate() : event.end.toDate();
        const endTime = endDate.toTimeString().substring(0, 5);
        
        console.log('Updating booking:', bookingId, 'Start Time:', startTime, 'End Time:', endTime);
        const csrf_token = getCookie('csrftoken');
        // Use current page's path prefix to preserve language code
        const urlPrefix = window.location.pathname.split('/').slice(0, 2).join('/');
        fetch(`${urlPrefix}/bookings/api/update-booking/${bookingId}/`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': `${csrf_token}`
            },
            body: JSON.stringify({ start_time: startTime, end_time: endTime })
        })
        .then(r => {
            console.log('Response status:', r.status, 'URL:', r.url);
            if (!r.ok) {
                throw new Error(`HTTP error! status: ${r.status}`);
            }
            return r.json();
        })
        .then(data => {
            console.log('Response data:', data);
            if (data.success) {
                calendar.updateEvent(event.id, event.calendarId, changes);
                console.log('Booking updated successfully');
            } else {
                alert('Error: ' + (data.error || 'Could not update booking'));
                location.reload();
            }
        })
        .catch(err => {
            console.error('Update error:', err);
            alert('Error updating booking: ' + err.message);
            location.reload();
        });
    });
    
    // Staff filtering via tabs
    let currentFilter = 'all';
    
    function filterEvents(staffId) {
        currentFilter = staffId;
        calendar.clear();
        
        if (staffId === 'all') {
            calendar.createEvents(allEvents);
        } else {
            const filtered = allEvents.filter(e => String(e.calendarId) === String(staffId));
            calendar.createEvents(filtered);
        }
    }
    
    // Setup tabs
    const tabs = document.querySelectorAll('.staff-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => {
                t.classList.remove('bg-blue-600','text-white');
                t.classList.add('bg-gray-100', 'text-gray-700');
            });
            tab.classList.remove('bg-gray-100', 'text-gray-700');
            tab.classList.add('bg-blue-600','text-white');
            
            const staffId = tab.dataset.staffId || 'all';
            filterEvents(staffId);
        });
    });
    
    // Make calendar globally accessible for debugging
    window.calendar = calendar;
}

// Show custom booking modal
function showBookingModal(event) {
    const raw = event.raw || {};
    const startDate = event.start.toDate ? event.start.toDate() : new Date(event.start);
    const endDate = event.end.toDate ? event.end.toDate() : new Date(event.end);
    const isPending = raw.status == 0;
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('booking-detail-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'booking-detail-modal';
        modal.className = 'hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = '<div class="bg-white rounded-lg p-6 max-w-md w-full mx-4"><div id="booking-detail-content"></div></div>';
        document.body.appendChild(modal);
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
    
    const content = `
        <h3 class="text-xl font-bold mb-4">Booking Details</h3>
        <p class="mb-2"><strong>Customer:</strong> ${raw.customer || 'N/A'}</p>
        <p class="mb-2"><strong>Service:</strong> ${raw.service || 'N/A'}</p>
        <p class="mb-2"><strong>Time:</strong> ${startDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - ${endDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
        
        <div class="mt-6 flex gap-2 flex-wrap">
            <button onclick="editBooking(${raw.booking_id})" 
                    class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                Edit
            </button>
            <button onclick="deleteBooking(${raw.booking_id})" 
                    class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
                Delete
            </button>
            ${isPending ? `
                <button onclick="confirmBooking(${raw.booking_id})" 
                        class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                    Confirm
                </button>
            ` : ''}
            <button onclick="closeBookingDetailModal()" 
                    class="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400">
                Close
            </button>
        </div>
    `;
    
    document.getElementById('booking-detail-content').innerHTML = content;
    modal.classList.remove('hidden');
}

function closeBookingDetailModal() {
    const modal = document.getElementById('booking-detail-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}