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
     * 1. Convert bookings → Syncfusion event format
     * --------------------------------------------------------- */
    const events = rawBookings.map(b => {
        const isConfirmed = b.extendedProps.status == 1 || b.extendedProps.status === 'Confirmed';

        return {
            Id: b.id,
            Subject: b.title,
            StartTime: new Date(b.start),
            EndTime: new Date(b.end),
            StaffId: b.extendedProps.staff_id,
            IsReadonly: false,
            Color: b.backgroundColor,
            Border: b.borderColor,
            IsConfirmed: isConfirmed,
            Raw: b.extendedProps
        };
    });

    /* ---------------------------------------------------------
     * 2. Staff → Syncfusion resources
     * --------------------------------------------------------- */
    const resources = [{
        field: 'StaffId',
        title: 'Staff',
        name: 'Staff',
        allowMultiple: false,
        dataSource: staffList.map(s => ({
            Id: s.id,
            Name: s.title,
            Avatar: s.avatar,
            Occupancy: s.occupancy || 0
        })),
        textField: 'Name',
        idField: 'Id'
    }];

    /* ---------------------------------------------------------
     * 4. Create Syncfusion Scheduler
     * --------------------------------------------------------- */
    const schedule = new ej.schedule.Schedule({
        height: '100%',
        width: '100%',
        currentView: 'TimelineDay',
        selectedDate: new Date(currentDate),
        firstDayOfWeek: 1,  // Start week on Monday (0=Sunday, 1=Monday)
        
        /* Configure visible views (excludes WorkWeek) */
        views: [
            { option: 'Day' },
            { option: 'Week' },
            { option: 'Month' },
            { option: 'Agenda' }
        ],
        
        /* Disable drag and drop and resize */
        allowDragAndDrop: false,
        allowResizing: false,

        /* 15-хвилинні слоти */
        timeScale: {
            enable: true,
            interval: 15,
            slotCount: 1
        },
        
        /* 24-hour time format */
        timeFormat: 'HH:mm',

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
            },
            enableTooltip: true
        },

        /* Use custom colors from backend */
        cssClass: 'custom-event-colors',

        /* -----------------------------------------------------
         * 3. Custom templates
         * ----------------------------------------------------- */

        /* Show weekday and day of month in date header (internationalized) */
        dateHeaderTemplate: function(props) {
            const date = new Date(props.date);
            const locale = document.documentElement.lang || 'en';
            const weekday = date.toLocaleDateString(locale, { weekday: 'short' });
            const dayOfMonth = date.getDate();
            return `<div class="text-center">
                <div class="font-semibold text-sm">${weekday}</div>
                <div class="text-lg font-bold">${dayOfMonth}</div>
            </div>`;
        },

        /* Staff header template (avatar → name → occupancy) */
        resourceHeaderTemplate: function(props) {
            const staff = props.resourceData;

            const occ = staff.Occupancy;
            const occColor =
                occ >= 80 ? 'bg-red-500' :
                occ >= 50 ? 'bg-yellow-500' :
                'bg-green-500';

            return `
                <div class="flex flex-col items-center py-1">
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

        /* Apply custom colors from backend */
        eventRendered: function(args) {
            if (args.data.Color) {
                args.element.style.backgroundColor = args.data.Color;
            }
            if (args.data.Border) {
                args.element.style.borderLeftColor = args.data.Border;
                args.element.style.borderLeftWidth = '4px';
                args.element.style.borderLeftStyle = 'solid';
            }
        },

        actionComplete: async function(args) {
            if (args.requestType === "dateNavigate") {
                const newDate = this.selectedDate;
                // Format date in local timezone, not UTC
                const year = newDate.getFullYear();
                const month = String(newDate.getMonth() + 1).padStart(2, '0');
                const day = String(newDate.getDate()).padStart(2, '0');
                const dateStr = `${year}-${month}-${day}`;
                
                try {
                    const response = await fetch(`/bookings/calendar-api/?date=${dateStr}`);
                    
                    if (!response.ok) {
                        throw new Error('Failed to fetch calendar data');
                    }
                    
                    const data = await response.json();

                    const events = data.bookings.map(b => ({
                        Id: b.id,
                        Subject: b.title,
                        StartTime: new Date(b.start),
                        EndTime: new Date(b.end),
                        StaffId: b.extendedProps.staff_id,
                        IsReadonly: false,
                        Color: b.backgroundColor,
                        Border: b.borderColor,
                        isConfirmed: b.extendedProps.status === 1 || b.extendedProps.status === 'Confirmed',
                        Raw: b.extendedProps
                    }));

                    // Update staff resources with new occupancy
                    const staffResources = data.staff.map(s => ({
                        Id: s.id,
                        Name: s.title,
                        Avatar: s.avatar,
                        Occupancy: s.occupancy || 0
                    }));
                    
                    this.resources[0].dataSource = staffResources;
                    
                    // Update working hours
                    if (data.dayStart && data.dayEnd) {
                        this.startHour = `${data.dayStart}:00`;
                        this.endHour = `${data.dayEnd}:00`;
                        this.workHours.start = `${data.dayStart}:00`;
                        this.workHours.end = `${data.dayEnd}:00`;
                    }

                    this.eventSettings.dataSource = events;
                    this.refreshEvents();
                    this.refreshLayout();
                } catch (error) {
                    console.error('Error fetching calendar data:', error);
                    alert('Error loading calendar data. Please refresh the page.');
                }
            }
        },

        /* Click → open custom modal and prevent default */
        eventClick: function(args) {
            args.cancel = true;  // Prevent default Syncfusion popup
            showBookingModal({
                id: args.event.Id,
                start: args.event.StartTime,
                end: args.event.EndTime,
                title: args.event.Subject,
                raw: args.event.Raw
            });
        },

        /* Prevent all default Syncfusion popups */
        popupOpen: function(args) {
            args.cancel = true;  // Prevent quick info popup, editor dialog, etc.
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