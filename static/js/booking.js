// Load available dates for selected staff (calendar version)
async function loadAvailableDates() {
    if (!selectedStaff) return;
    
    try {
        const response = await fetch(`/bookings/api/dates/${companyId}/${selectedStaff}/`);
        const data = await response.json();
        
        availableDates = data.available_dates ? data.available_dates.map(d => d.date) : [];
        
        if (availableDates.length > 0) {
            datesContainer.classList.add('hidden');
            calendarContainer.classList.remove('hidden');
            monthNavigation.classList.remove('hidden');
            renderCalendar();
        } else {
            datesContainer.classList.remove('hidden');
            datesContainer.innerHTML = '<p class="text-red-500 text-sm">No available dates</p>';
            calendarContainer.classList.add('hidden');
            monthNavigation.classList.add('hidden');
        }
        
        selectedDate = null;
        selectedDateInput.value = '';
        timeSlotsSection.classList.add('hidden');
        
    } catch (error) {
        console.error('Error loading dates:', error);
        datesContainer.classList.remove('hidden');
        datesContainer.innerHTML = '<p class="text-red-500 text-sm">Error loading dates</p>';
    }
}

// Render calendar for current month
function renderCalendar() {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    
    // Update month display
    currentMonthSpan.textContent = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    
    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    datesGrid.innerHTML = '';
    
    // Add empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
        const emptyCell = document.createElement('div');
        emptyCell.className = 'aspect-square';
        datesGrid.appendChild(emptyCell);
    }
    
    // Add days of month
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dateStr = date.toISOString().split('T')[0];
        const isAvailable = availableDates.includes(dateStr);
        const isPast = date < today;
        
        const dayCell = document.createElement('button');
        dayCell.type = 'button';
        dayCell.className = 'aspect-square flex items-center justify-center text-sm rounded-lg transition';
        dayCell.textContent = day;
        
        if (isPast || !isAvailable) {
            dayCell.className += ' bg-red-50 text-red-300 cursor-not-allowed';
            dayCell.disabled = true;
        } else {
            dayCell.className += ' border border-gray-300 hover:bg-blue-50 hover:border-blue-500 cursor-pointer';
            dayCell.dataset.date = dateStr;
            dayCell.addEventListener('click', function() {
                selectDate(dateStr, this);
            });
        }
        
        datesGrid.appendChild(dayCell);
    }
}

// Select a date
function selectDate(date, element) {
    selectedDate = date;
    selectedDateInput.value = date;
    
    // Update visual selection
    document.querySelectorAll('#datesGrid button[data-date]').forEach(btn => {
        btn.classList.remove('bg-blue-600', 'text-white', 'border-blue-600');
        btn.classList.add('border-gray-300');
    });
    element.classList.add('bg-blue-600', 'text-white', 'border-blue-600');
    element.classList.remove('border-gray-300');
    
    loadAvailableTimes();
}

// Load available time slots for selected date
async function loadAvailableTimes() {
    const serviceId = serviceSelect.value;
    
    if (!selectedStaff || !selectedDate || !serviceId) {
        return;
    }

    try {
        const response = await fetch(`/bookings/api/times/${companyId}/${selectedStaff}/${serviceId}/${selectedDate}/`);
        const data = await response.json();
        
        timeSlotsGrid.innerHTML = '';
        
        if (data.available_times && data.available_times.length > 0) {
            data.available_times.forEach(time => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'time-btn px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-blue-50 hover:border-blue-500 transition whitespace-nowrap';
                button.textContent = time;
                button.dataset.time = time;
                
                button.addEventListener('click', function() {
                    selectTime(time, this);
                });
                
                timeSlotsGrid.appendChild(button);
            });
            
            timeSlotsSection.classList.remove('hidden');
        } else {
            const noTimesMsg = document.createElement('p');
            noTimesMsg.className = 'text-red-500 text-sm';
            noTimesMsg.textContent = 'No available time slots';
            timeSlotsGrid.appendChild(noTimesMsg);
            timeSlotsSection.classList.remove('hidden');
        }
        
        selectedTimeInput.value = '';
        
    } catch (error) {
        console.error('Error loading times:', error);
        timeSlotsGrid.innerHTML = '<p class="text-red-500 text-sm">Error loading times</p>';
        timeSlotsSection.classList.remove('hidden');
    }
}

// Select a time
function selectTime(time, element) {
    selectedTimeInput.value = time;
    
    // Update visual selection
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.remove('bg-blue-600', 'text-white', 'border-blue-600');
        btn.classList.add('border-gray-300');
    });
    element.classList.add('bg-blue-600', 'text-white', 'border-blue-600');
    element.classList.remove('border-gray-300');
}

// Reset dates and times display
function resetDatesAndTimes() {
    datesContainer.innerHTML = '<p class="text-gray-500 text-sm">Please select a specialist first</p>';
    datesContainer.classList.remove('hidden');
    calendarContainer.classList.add('hidden');
    monthNavigation.classList.add('hidden');
    datesGrid.innerHTML = '';
    timeSlotsSection.classList.add('hidden');
    timeSlotsGrid.innerHTML = '';
    selectedDate = null;
    selectedStaff = null;
    selectedDateInput.value = '';
    selectedStaffInput.value = '';
    selectedTimeInput.value = '';
    availableDates = [];
}