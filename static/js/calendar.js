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

    /* ---------------------------------------------------------
     * 1. Staff colors
     * --------------------------------------------------------- */
    const staffColors = [
        { bg: '#3b82f6', border: '#1e40af' },
        { bg: '#10b981', border: '#047857' },
        { bg: '#f59e0b', border: '#d97706' },
        { bg: '#8b5cf6', border: '#6d28d9' },
        { bg: '#ec4899', border: '#be185d' },
        { bg: '#14b8a6', border: '#0d9488' },
        { bg: '#f97316', border: '#ea580c' },
        { bg: '#06b6d4', border: '#0891b2' },
        { bg: '#84cc16', border: '#65a30d' },
        { bg: '#a855f7', border: '#7e22ce' }
    ];

    const staffColorMap = {};
    staffList.forEach((s, i) => {
        staffColorMap[s.id] = staffColors[i % staffColors.length];
    });

    /* ---------------------------------------------------------
     * 2. Convert bookings → Syncfusion event format
     * --------------------------------------------------------- */
    const events = rawBookings.map(b => {
        const color = staffColorMap[b.extendedProps.staff_id];
        const isPending = b.extendedProps.status == 0;

        return {
            Id: b.id,
            Subject: b.title,
            StartTime: new Date(b.start),
            EndTime: new Date(b.end),
            StaffId: b.extendedProps.staff_id,
            IsReadonly: false,
            Color: color.bg,
            Border: color.border,
            IsPending: isPending,
            Raw: b.extendedProps
        };
    });

    /* ---------------------------------------------------------
     * 3. Staff → Syncfusion resources
     * --------------------------------------------------------- */
    const resources = [{
        field: 'StaffId',
        title: 'Staff',
        name: 'Staff',
        allowMultiple: false,
        dataSource: staffList.map((s, i) => ({
            Id: s.id,
            Name: s.title,
            Avatar: s.avatar,
            Occupancy: s.occupancy || 0,
            Color: staffColors[i % staffColors.length].bg
        })),
        textField: 'Name',
        idField: 'Id',
        colorField: 'Color'
    }];

    /* ---------------------------------------------------------
     * 4. Create Syncfusion Scheduler
     * --------------------------------------------------------- */
    const schedule = new ej.schedule.Schedule({
        height: '100%',
        width: '100%',
        currentView: 'TimelineDay',
        selectedDate: new Date(currentDate),

        /* 15-хвилинні слоти */
        timeScale: {
            enable: true,
            interval: 15,
            slotCount: 1
        },

        /* Робочі години */
        workHours: {
            highlight: true,
            start: `${dayStart}:00`,
            end: `${dayEnd}:00`
        },

        /* Показувати тільки робочі години */
        startHour: `${dayStart}:00`,
        endHour: `${dayEnd}:00`,

        /* Staff columns */
        group: {
            resources: ['Staff']
        },

        resources: resources,

        /* Події */
        eventSettings: {
            dataSource: events,
            fields: {
                id: 'Id',
                subject: { name: 'Subject' },
                startTime: { name: 'StartTime' },
                endTime: { name: 'EndTime' }
            }
        },

        /* -----------------------------------------------------
         * 5. Custom templates
         * ----------------------------------------------------- */

        /* Staff header template (avatar → name → occupancy) */
        resourceHeaderTemplate: function(props) {
            const staff = props.resourceData;

            const occ = staff.Occupancy;
            const occColor =
                occ >= 80 ? 'bg-red-500' :
                occ >= 50 ? 'bg-yellow-500' :
                'bg-green-500';

            return `
                <div class="flex flex-col items-center py-2">
                    ${staff.Avatar
                        ? `<img src="${staff.Avatar}" class="w-12 h-12 rounded-full object-cover border border-gray-300">`
                        : `<div class="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center border border-gray-300">
                            <i class="fas fa-user text-gray-500 text-sm"></i>
                        </div>`
                    }
                    <div class="text-sm font-semibold text-gray-700 mt-1 text-center truncate max-w-[80px]">
                        ${staff.Name}
                    </div>
                    <div class="w-14 h-1.5 bg-gray-200 rounded-full mt-1 overflow-hidden">
                        <div class="h-full ${occColor}" style="width:${occ}%"></div>
                    </div>
                </div>
            `;
        },

        /* Custom event template */
        eventTemplate: function(props) {
            const opacity = props.IsPending ? 0.7 : 1;
            return `
                <div style="
                    background:${props.Color};
                    border-left:4px solid ${props.Border};
                    height:100%;
                    padding:4px;
                    color:white;
                    opacity:${opacity};
                    font-size:12px;
                    font-weight:600;
                ">
                    ${props.Subject}
                </div>
            `;
        },

        actionBegin: async function(args) {
            if (args.requestType === "dateNavigate") {
                const newDate = this.selectedDate;
                const dateStr = newDate.toISOString().slice(0, 10);
                
                try {
                    const response = await fetch(`/bookings/calendar-api/?date=${dateStr}`);
                    
                    if (!response.ok) {
                        throw new Error('Failed to fetch calendar data');
                    }
                    
                    const data = await response.json();

                    const events = data.map(b => ({
                        Id: b.id,
                        Subject: b.title,
                        StartTime: new Date(b.start),
                        EndTime: new Date(b.end),
                        StaffId: b.extendedProps.staff_id,
                        IsReadonly: false,
                        Color: b.backgroundColor,
                        Border: b.borderColor,
                        IsPending: b.extendedProps.status === 'Pending',
                        Raw: b.extendedProps
                    }));

                    this.eventSettings.dataSource = events;
                    this.refreshEvents();
                    this.refreshLayout();
                } catch (error) {
                    console.error('Error fetching calendar data:', error);
                    alert('Error loading calendar data. Please refresh the page.');
                }
            }
        },

        /* Click → open modal */
        eventClick: function(args) {
            showBookingModal({
                id: args.event.Id,
                start: args.event.StartTime,
                end: args.event.EndTime,
                title: args.event.Subject,
                raw: args.event.Raw
            });
        }
    });

    schedule.appendTo(calendarEl);
    window.calendar = schedule;
}

// Show custom booking modal
function showBookingModal(event) {
    const raw = event.raw || {};
    const startDate = event.start.toDate ? event.start.toDate() : new Date(event.start);
    const endDate = event.end.toDate ? event.end.toDate() : new Date(event.end);
    
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
        
        <div class="flex flex-col gap-2 mt-4">
            <button onclick="editBooking(${raw.booking_id})" 
                    class="w-full bg-gray-800 text-gray-200 py-2 text-center rounded-lg font-semibold hover:bg-gray-600 transition">
                Edit
            </button>
            <button onclick="deleteBooking(${raw.booking_id})" 
                    class="w-full bg-red-200 text-red-700 py-2 text-center rounded-lg font-semibold hover:bg-red-300 transition">
                Delete
            </button>
            <button onclick="closeBookingDetailModal()" 
                    class="w-full bg-gray-300 text-gray-800 py-2 text-center rounded-lg font-semibold hover:bg-gray-400 transition">
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