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
     * 2. Convert bookings → unified event format
     * --------------------------------------------------------- */
    const allEvents = rawBookings.map(b => {
        const color = staffColorMap[b.extendedProps.staff_id] || staffColors[0];
        const isPending = b.extendedProps.status == 0;

        return {
            id: String(b.id),
            calendarId: String(b.extendedProps.staff_id),
            title: b.title,
            start: new Date(b.start),
            end: new Date(b.end),
            backgroundColor: color.bg,
            borderColor: color.border,
            color: '#ffffff',
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

    /* ---------------------------------------------------------
     * 3. DAYPILOT MODE (preferred)
     * --------------------------------------------------------- */
    if (window.DayPilot && window.DayPilot.Scheduler) {
        const scheduler = new DayPilot.Scheduler(calendarEl.id);

        // Base config
        scheduler.startDate = currentDate;
        scheduler.days = 1;
        scheduler.scale = "CellDuration";
        scheduler.cellDuration = 30;
        scheduler.businessBeginsHour = dayStart;
        scheduler.businessEndsHour = dayEnd;
        scheduler.allowEventOverlap = false;
        scheduler.cellHeight = 80; // ширші лінії
        scheduler.timeHeaders = [
            { groupBy: "Hour", format: "HH:mm" }
        ];

        // Timeline strictly within working hours
        const timeline = []; for (let hour = dayStart; hour < dayEnd; hour++) { timeline.push({ start: new DayPilot.Date(currentDate).addHours(hour), end: new DayPilot.Date(currentDate).addHours(hour + 1) }); } scheduler.timeline = timeline;

        // Staff as columns
        scheduler.resources = staffList.map(s => ({
            id: String(s.id),
            name: s.title
        }));

        // Custom row header: avatar → name → occupancy
        scheduler.onBeforeRowHeaderRender = args => {
            const staff = staffList.find(s => String(s.id) === String(args.row.id));
            if (!staff) return;

            const occupancy = staff.occupancy || 0;
            const occColor =
                occupancy >= 80 ? '#ef4444' :
                occupancy >= 50 ? '#eab308' :
                '#10b981';

            const avatar = staff.avatar
                ? `<img src="${staff.avatar}" class="w-12 h-12 rounded-full object-cover border-2 border-gray-300 mx-auto" />`
                : `<div class="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center border-2 border-gray-300 mx-auto">
                       <i class="fas fa-user text-gray-500 text-sm"></i>
                   </div>`;

            args.row.html = `
                <div style="display:flex; flex-direction:column; align-items:center; padding:6px 0;">
                    ${avatar}
                    <div style="font-size:13px; font-weight:600; color:#374151; margin-top:6px; text-align:center;">
                        ${staff.title}
                    </div>
                    <div style="width:80%; height:6px; background:#e5e7eb; border-radius:3px; margin-top:4px; overflow:hidden;">
                        <div style="width:${occupancy}%; height:100%; background:${occColor};"></div>
                    </div>
                </div>
            `;
        };

        // Custom event rendering (чисті блоки)
        scheduler.onBeforeEventRender = args => {
            const d = args.data.data || args.data;
            const isPending = d.isPending;
            const opacity = isPending ? 0.7 : 1;

            args.data.html = `
                <div style="padding:4px; font-size:12px; font-weight:600; color:white; opacity:${opacity};">
                    ${args.data.text}
                </div>
            `;
        };

        // Map events to DayPilot format
        scheduler.events.list = allEvents.map(e => ({
            id: e.id,
            text: e.title,
            start: e.start.toISOString(),
            end: e.end.toISOString(),
            resource: e.calendarId,
            backColor: e.backgroundColor,
            borderColor: e.borderColor,
            data: e.raw
        }));

        // Click → open modal
        scheduler.onEventClick = args => {
            const ev = args.e;
            const d = ev.data || {};
            showBookingModal({
                id: ev.id(),
                start: new Date(ev.start.value),
                end: new Date(ev.end.value),
                title: ev.text(),
                raw: d
            });
        };

        scheduler.init();
        window.calendar = scheduler;
        return;
    }

    /* ---------------------------------------------------------
     * 4. TOAST UI FALLBACK
     * --------------------------------------------------------- */
    const calendars = staffList.map((s, i) => ({
        id: String(s.id),
        name: s.title,
        backgroundColor: staffColors[i % staffColors.length].bg,
        borderColor: staffColors[i % staffColors.length].border
    }));

    const tuiCal = new tui.Calendar(calendarEl, {
        defaultView: 'day',
        isReadOnly: true,
        calendars: calendars,
        day: {
            hourStart: dayStart,
            hourEnd: dayEnd,
            eventView: ['time'],
            taskView: false
        },
        template: {
            time(event) {
                const opacity = event.raw.isPending ? 0.7 : 1;
                return `
                    <div style="color:white; opacity:${opacity}; font-size:12px; line-height:1.2;">
                        ${event.title}
                    </div>
                `;
            }
        }
    });

    tuiCal.setDate(currentDate);
    tuiCal.createEvents(allEvents);

    // Sidebar: avatar → name → occupancy
    setTimeout(() => {
        const items = document.querySelectorAll('.tui-calendar-list-item');
        items.forEach((item, i) => {
            const staff = staffList[i];
            if (!staff) return;

            const occ = staff.occupancy || 0;
            const occColor =
                occ >= 80 ? 'bg-red-500' :
                occ >= 50 ? 'bg-yellow-500' :
                'bg-green-500';

            item.innerHTML = `
                <div class="flex flex-col items-center py-1">
                    ${staff.avatar
                        ? `<img src="${staff.avatar}" class="w-10 h-10 rounded-full object-cover border border-gray-300">`
                        : `<div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center border border-gray-300">
                               <i class="fas fa-user text-gray-500 text-sm"></i>
                           </div>`
                    }
                    <div class="text-[11px] font-semibold text-gray-700 mt-1 text-center truncate max-w-[72px]">
                        ${staff.title}
                    </div>
                    <div class="w-12 h-1.5 bg-gray-200 rounded-full mt-1 overflow-hidden">
                        <div class="h-full ${occColor}" style="width:${occ}%"></div>
                    </div>
                </div>
            `;
        });
    }, 100);

    window.calendar = tuiCal;
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