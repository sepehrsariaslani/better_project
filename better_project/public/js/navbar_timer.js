// Navbar Timer for ERPNext
// فایل: better_project/public/js/navbar_timer.js

console.log('Navbar Timer JS loaded'); // Debug log

// Helper function to find the correct navbar element
function findNavbarContainer() {
    // Try different possible selectors
    const selectors = [
        '.navbar .navbar-nav', // Bootstrap 4/5
        '.navbar .ms-auto',    // Bootstrap 5
        '.navbar .ml-auto',    // Bootstrap 4
        '.navbar-right',       // Legacy
        '#navbar-user',        // User menu area
        '.navbar .nav'         // Generic nav
    ];
    
    for (const selector of selectors) {
        const element = $(selector);
        if (element.length) {
            console.log('Found navbar using selector:', selector);
            return element;
        }
    }
    
    console.log('No navbar found with any selector');
    return null;
}

function setup_navbar_timer() {
    console.log('Setting up navbar timer...'); // Debug log
    
    // Check if user is logged in
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        console.log('User not logged in, skipping navbar timer setup');
        return;
    }
    
    // Remove any existing timer elements first
    $('#navbar-timer').remove();
    
    // پیدا کردن Navbar مناسب با استفاده از تابع کمکی
    const navbar = findNavbarContainer();
    console.log('Found navbar:', navbar ? true : false); // Debug log
    
    // اگر navbar پیدا شد
    if (navbar) {
        console.log('Adding timer to navbar...'); // Debug log
        
        // استفاده از data-bs-toggle برای Bootstrap 5
        const timer_html = `
            <li class="nav-item dropdown" id="navbar-timer">
                <a class="nav-link dropdown-toggle timer-nav-link" href="#" role="button" 
                   data-bs-toggle="dropdown" aria-expanded="false" title="وضعیت تسک‌ها">
                    <span class="timer-icon">
                        <i class="fa fa-tasks" style="font-size: 18px;"></i>
                    </span>
                </a>
                <div class="dropdown-menu dropdown-menu-end timer-dropdown">
                    <!-- Today's Time Chart Summary -->
                    <div id="today-chart-summary" class="today-chart-summary">
                        <div class="chart-container" style="height: 100px;">
                            <canvas id="todayTimeChart"></canvas>
                        </div>
                    </div>

                    <!-- Tabs Navigation -->
                    <ul class="nav nav-tabs timer-tabs" role="tablist">
                        <li class="nav-item">
                            <a class="nav-link active" data-bs-toggle="tab" data-bs-target="#current-status" role="tab">
                                <i class="fa fa-users"></i> وضعیت جاری
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" data-bs-target="#overdue-tasks" role="tab">
                                <i class="fa fa-exclamation-triangle"></i> تسک‌های معوق
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" data-bs-target="#today-tasks" role="tab">
                                <i class="fa fa-clock-o"></i> تسک‌های امروز
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" data-bs-target="#time-chart" role="tab">
                                <i class="fa fa-bar-chart"></i> نمودار زمانی
                            </a>
                        </li>
                    </ul>

                    <!-- Tab Content -->
                    <div class="tab-content timer-tab-content">
                        <!-- Current Status Tab -->
                        <div class="tab-pane fade show active" id="current-status" role="tabpanel">
                            <div class="current-status-content">
                                <!-- Content will be loaded here -->
                            </div>
                        </div>

                        <!-- Overdue Tasks Tab -->
                        <div class="tab-pane fade" id="overdue-tasks" role="tabpanel">
                            <div class="overdue-tasks-content">
                                <!-- Content will be loaded here -->
                            </div>
                        </div>

                        <!-- Today's Tasks Tab -->
                        <div class="tab-pane fade" id="today-tasks" role="tabpanel">
                            <div class="today-tasks-content">
                                <!-- Content will be loaded here -->
                            </div>
                        </div>

                        <!-- Time Chart Tab -->
                        <div class="tab-pane fade" id="time-chart" role="tabpanel">
                            <div class="time-chart-content">
                                <div class="chart-container" style="height: 300px;">
                                    <canvas id="detailedTimeChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </li>
        `;
        
        navbar.prepend(timer_html);
        console.log('Timer HTML added to navbar'); // Debug log
        
        setup_timer_events();
        add_timer_styles();
        
        // بروزرسانی اولیه محتوا
        refresh_navbar_timer();
    } else {
        console.log('Navbar not found'); // Debug log
    }
}

// راه‌اندازی اولیه با تاخیر مناسب
$(document).ready(function() {
    console.log('Document ready, waiting for navbar...'); // Debug log
    
    // چک کردن وجود Chart.js
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded!');
        // لود کردن Chart.js از CDN
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
        script.onload = function() {
            console.log('Chart.js loaded successfully');
            initializeTimer();
        };
        document.head.appendChild(script);
    } else {
        initializeTimer();
    }
});

function initializeTimer() {
    // تاخیر 1 ثانیه‌ای برای اطمینان از لود شدن کامل صفحه
    setTimeout(function() {
        console.log('Initial setup timeout reached'); // Debug log
        
        // تلاش برای راه‌اندازی timer در navbar
        setup_navbar_timer();
        
        // اگر navbar هنوز لود نشده، منتظر بمان و دوباره تلاش کن
        if (!$('#navbar-timer').length) {
            console.log('Timer not found, starting interval check...'); // Debug log
            
            const checkNavbar = setInterval(function() {
                console.log('Checking for navbar...'); // Debug log
                
                if (findNavbarContainer()) {
                    console.log('Navbar found in interval check'); // Debug log
                    setup_navbar_timer();
                    if ($('#navbar-timer').length) {
                        console.log('Timer successfully added'); // Debug log
                        clearInterval(checkNavbar);
                    }
                }
            }, 500);
            
            // توقف چک کردن بعد از 10 ثانیه
            setTimeout(function() {
                console.log('Stopping navbar check interval'); // Debug log
                clearInterval(checkNavbar);
            }, 10000);
        }
        
        // بروزرسانی هر 30 ثانیه
        setInterval(refresh_navbar_timer, 30000);
    }, 1000);
}

function setup_timer_events() {
    // کلیک روی آیکون Timer
    $(document).on('click', '#navbar-timer .timer-nav-link', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const dropdown = $(this).next('.dropdown-menu');
        dropdown.toggleClass('show');
        
        if (dropdown.hasClass('show')) {
            refresh_navbar_timer();
        }
    });
    
    // بستن dropdown با کلیک خارجی
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#navbar-timer').length) {
            $('#navbar-timer .dropdown-menu').removeClass('show');
        }
    });
    
    // جلوگیری از بسته شدن dropdown با کلیک داخلی
    $(document).on('click', '#navbar-timer .dropdown-menu', function(e) {
        e.stopPropagation();
    });

    // تغییر تب با جلوگیری از navigation
    $('#navbar-timer .nav-tabs .nav-link').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // حذف کلاس active از همه تب‌ها
        $('#navbar-timer .nav-tabs .nav-link').removeClass('active');
        $('#navbar-timer .tab-pane').removeClass('show active');
        
        // اضافه کردن کلاس active به تب انتخاب شده
        $(this).addClass('active');
        const targetId = $(this).attr('data-bs-target').substring(1);
        $(`#${targetId}`).addClass('show active');
        
        // بروزرسانی محتوای تب
        refresh_current_tab(targetId);
    });
}

function refresh_navbar_timer() {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        return;
    }
    // بروزرسانی همه تب‌ها
    refresh_current_status();
    refresh_overdue_tasks();
    refresh_today_tasks();
    refresh_time_charts();
}

function refresh_current_tab(tabId) {
    switch(tabId) {
        case 'current-status':
            refresh_current_status();
            break;
        case 'overdue-tasks':
            refresh_overdue_tasks();
            break;
        case 'today-tasks':
            refresh_today_tasks();
            break;
        case 'time-chart':
            refresh_time_charts();
            break;
    }
}

function refresh_current_status() {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        return;
    }
    frappe.call({
        method: 'better_project.doctype.task.task.get_current_employees_status',
        callback: function(r) {
            const content = $('#current-status .current-status-content');
            
            if (!r.message || !r.message.length) {
                content.html('<div class="text-muted text-center p-3">هیچ کارمندی در حال حاضر مشغول کار نیست</div>');
            } else {
                content.html(r.message.map(employee => `
                    <div class="employee-status-card">
                        <div class="employee-info">
                            <img src="${employee.user_image || '/assets/frappe/images/default-avatar.png'}" 
                                 class="employee-avatar" alt="${employee.employee_name}">
                            <div class="employee-details">
                                <div class="employee-name">${employee.employee_name}</div>
                                ${employee.task_name ? `
                                    <div class="task-info">
                                        <a href="/app/task/${employee.task_name}" target="_blank">
                                            ${employee.task_subject}
                                        </a>
                                        <div class="task-time">
                                            <i class="fa fa-clock-o"></i>
                                            از ${employee.start_time}
                                        </div>
                                    </div>
                                ` : '<div class="text-muted">در حال حاضر مشغول کار نیست</div>'}
                            </div>
                        </div>
                    </div>
                `).join(''));
            }
        }
    });
}

function refresh_overdue_tasks() {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        return;
    }
    frappe.call({
        method: 'better_project.doctype.task.task.get_my_overdue_tasks',
        callback: function(r) {
            const content = $('#overdue-tasks .overdue-tasks-content');
            
            if (!r.message || !r.message.length) {
                content.html('<div class="text-muted text-center p-3">هیچ تسک معوقی ندارید</div>');
                return;
            }

            content.html(r.message.map(task => `
                <div class="task-card overdue">
                    <div class="task-header">
                        <a href="/app/task/${task.name}" target="_blank" class="task-subject">
                            ${task.subject}
                        </a>
                        <span class="days-overdue">${task.days_overdue} روز تاخیر</span>
                    </div>
                    <div class="task-details">
                        <div class="detail-item">
                            <i class="fa fa-calendar"></i>
                            موعد: ${task.exp_end_date}
                        </div>
                        <div class="detail-item">
                            <i class="fa fa-folder"></i>
                            ${task.project}
                        </div>
                    </div>
                    <div class="task-progress">
                        <div class="progress">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: ${task.progress}%"></div>
                        </div>
                        <small>${task.progress}% تکمیل شده</small>
                    </div>
                    <button class="btn btn-sm btn-primary start-task-btn" 
                            onclick="start_task('${task.name}')">
                        <i class="fa fa-play"></i> شروع کار
                    </button>
                </div>
            `).join(''));
        }
    });
}

function refresh_today_tasks() {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        return;
    }
    frappe.call({
        method: 'better_project.doctype.task.task.get_my_today_tasks',
        callback: function(r) {
            const content = $('#today-tasks .today-tasks-content');
            
            if (!r.message || !r.message.length) {
                content.html('<div class="text-muted text-center p-3">امروز هنوز روی هیچ تسکی کار نکرده‌اید</div>');
                return;
            }

            content.html(r.message.map(task => `
                <div class="task-card">
                    <div class="task-header">
                        <a href="/app/task/${task.name}" target="_blank" class="task-subject">
                            ${task.subject}
                        </a>
                        <span class="total-time">${task.total_time} ساعت</span>
                    </div>
                    <div class="task-details">
                        <div class="detail-item">
                            <i class="fa fa-folder"></i>
                            ${task.project}
                        </div>
                        <div class="detail-item">
                            <i class="fa fa-clock-o"></i>
                            آخرین فعالیت: ${task.last_activity}
                        </div>
                    </div>
                    <div class="task-progress">
                        <div class="progress">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: ${task.progress}%"></div>
                        </div>
                        <small>${task.progress}% تکمیل شده</small>
                    </div>
                    ${task.is_active ? `
                        <button class="btn btn-sm btn-warning stop-task-btn" 
                                onclick="stop_task('${task.name}')">
                            <i class="fa fa-pause"></i> توقف
                        </button>
                    ` : `
                        <button class="btn btn-sm btn-primary start-task-btn" 
                                onclick="start_task('${task.name}')">
                            <i class="fa fa-play"></i> شروع کار
                        </button>
                    `}
                </div>
            `).join(''));
        }
    });
}

function refresh_time_charts() {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        return;
    }

    // Get data for the 7-day summary chart (daily hours by project)
    frappe.call({
        method: 'better_project.doctype.task.task.get_my_daily_project_time_data', // Get daily project time
        callback: function(r) {
            if (!r.message || !r.message.length) {
                // If no data, clear the summary chart
                if (window.todayTimeChartChart) {
                    window.todayTimeChartChart.destroy();
                }
                 // Display a message in the chart container
                const summaryChartContainer = $('#today-chart-summary .chart-container');
                summaryChartContainer.empty(); // Clear previous chart
                summaryChartContainer.html('<div class="text-muted text-center p-3">آمار کاری هفتگی در دسترس نیست</div>');

                // Remove any previous text summary (already handled, but good to be sure)
                $('#today-chart-summary .summary-text').remove();
                $('#today-chart-summary h6').remove();

                return;
            }

            const timeData = r.message;
            const dates = [...new Set(timeData.map(item => item.work_date))].sort(); // Get unique sorted dates
            const projects = [...new Set(timeData.map(item => item.project_name || 'بدون پروژه'))]; // Get unique projects

            // Create datasets for stacked bar chart
            const datasets = projects.map(project => {
                const projectData = timeData.filter(item => (item.project_name || 'بدون پروژه') === project);
                const color = projectData.length > 0 ? (projectData[0].color || getRandomColor()) : getRandomColor(); // Get project color or random

                return {
                    label: project,
                    data: dates.map(date => {
                        const dayData = projectData.find(item => item.work_date === date);
                        return dayData ? dayData.total_hours : 0;
                    }),
                    backgroundColor: color,
                    borderColor: color,
                    borderWidth: 1
                };
            });

            // Update summary chart
            update_time_chart('todayTimeChart', { labels: dates.map(date => moment(date).format('YYYY-MM-DD')), datasets: datasets }, true, true); // isSummary = true, isStacked = true
            
            // Remove any previous text summary (already handled, but good to be sure)
            $('#today-chart-summary .summary-text').remove();
            $('#today-chart-summary h6').remove();
        }
    });

    // Get data for the detailed chart (today's tasks time)
    frappe.call({
        method: 'better_project.doctype.task.task.get_my_today_time_data', // Get today's tasks time
        callback: function(r) {
            if (!r.message) return;

            console.log('Detailed Chart Data received:', r.message); // Debug log

            // Update detailed chart
            update_time_chart('detailedTimeChart', r.message, false, false); // isSummary = false, isStacked = false
        }
    });
}

function update_time_chart(canvasId, data, isSummary = false, isStacked = false) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return; // Ensure canvas exists

    console.log(`Updating chart ${canvasId} with data:`, data); // Debug log
    console.log(`isSummary: ${isSummary}, isStacked: ${isStacked}`); // Debug log

    const chartType = isStacked ? 'bar' : 'bar'; // Both are bar charts, just stacked for summary

    // Destroy existing chart if it exists
    if (window[canvasId + 'Chart']) {
        window[canvasId + 'Chart'].destroy();
    }

    let chartData, options;

    if (isStacked) {
        // Data for the stacked summary chart (daily project hours)
        chartData = {
            labels: data.labels, // Dates
            datasets: data.datasets // Datasets per project
        };

        options = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                         display: true,
                         text: 'روز'
                     }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'ساعت'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true // Show legend for stacked chart
                },
                 tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${formatDuration(value * 3600)}`;
                        }
                    }
                }
            }
        };
    } else {
        // Data for the detailed chart (today's task hours)
        chartData = {
            labels: data.map(item => item.task_subject), // Use task subject as label
            datasets: [{
                label: 'زمان (ساعت)',
                data: data.map(item => item.hours),
                backgroundColor: data.map(item => item.project_color || '#6c757d'), // Use project color or default
                borderColor: data.map(item => item.project_color || '#6c757d'), // Use project color or default
                borderWidth: 1
            }]
        };

        options = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'ساعت'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false // Hide legend for detailed chart
                },
                tooltip: {
                    callbacks: {
                         label: function(context) {
                            const dataItem = data[context.dataIndex];
                            const taskName = dataItem.task_subject || dataItem.task_name || '';
                            const projectName = dataItem.project_name || dataItem.project || 'بدون پروژه';
                            const value = context.raw || 0;
                            return `${taskName} (${projectName}): ${formatDuration(value * 3600)}`;
                        }
                    }
                }
            }
        };
    }
    
    // Add data labels plugin if needed (can be added later if required)
    // For now, relying on tooltips for hour display
    
    window[canvasId + 'Chart'] = new Chart(ctx, {
        type: chartType,
        data: chartData,
        options: options
    });
}

function start_task(taskName) {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        frappe.show_alert({
            message: 'لطفا ابتدا وارد سیستم شوید',
            indicator: 'red'
        });
        return;
    }
    frappe.call({
        method: 'better_project.api.task_timer.start_timer',
        args: { task: taskName },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: 'تایمر با موفقیت شروع شد',
                    indicator: 'green'
                });
                refresh_navbar_timer();
            } else {
                frappe.show_alert({
                    message: r.message?.error || 'خطا در شروع تایمر',
                    indicator: 'red'
                });
            }
        }
    });
}

function stop_task(taskName) {
    if (!frappe.session.user || frappe.session.user === 'Guest') {
        frappe.show_alert({
            message: 'لطفا ابتدا وارد سیستم شوید',
            indicator: 'red'
        });
        return;
    }
    frappe.call({
        method: 'better_project.api.task_timer.stop_timer',
        args: { task: taskName },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: 'تایمر با موفقیت متوقف شد',
                    indicator: 'orange'
                });
                refresh_navbar_timer();
            } else {
                frappe.show_alert({
                    message: r.message?.error || 'خطا در توقف تایمر',
                    indicator: 'red'
                });
            }
        }
    });
}

function add_timer_styles() {
    if (!$('#navbar-timer-styles').length) {
        $('head').append(`
            <style id="navbar-timer-styles">
                /* Navbar Timer Container */
                #navbar-timer .timer-dropdown {
                    width: 400px;
                    padding: 0;
                    border: 1px solid #ced4da; /* Adjusted border color */
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    background-color: #ffffff; /* Explicit background for light mode */
                }

                /* Today's Chart Summary */
                #navbar-timer .today-chart-summary {
                    padding: 10px;
                    border-bottom: 1px solid #ced4da; /* Adjusted border color */
                    background-color: #f8f9fa; /* Light background */
                    color: #212529; /* Dark text color */
                }
                
                #navbar-timer .today-chart-summary h6 {
                    margin-top: 5px;
                    margin-bottom: 5px;
                    color: #495057; /* Slightly lighter text */
                }
                
                #navbar-timer .today-chart-summary .summary-text {
                    font-size: 12px;
                    color: #495057;
                }

                /* Tabs */
                #navbar-timer .timer-tabs {
                    border-bottom: 1px solid #ced4da; /* Adjusted border color */
                    padding: 0 10px;
                    margin: 0;
                }

                #navbar-timer .timer-tabs .nav-link {
                    padding: 8px 12px;
                    font-size: 12px;
                    color: #6c757d; /* Text muted color */
                    border: none;
                }

                #navbar-timer .timer-tabs .nav-link.active {
                    color: #007bff; /* Primary color */
                    border-bottom: 2px solid #007bff; /* Primary color */
                    background: none;
                }

                #navbar-timer .timer-tabs .nav-link i {
                    margin-left: 4px;
                }

                /* Tab Content */
                #navbar-timer .timer-tab-content {
                    padding: 10px;
                    max-height: 400px;
                    overflow-y: auto;
                }

                /* Employee Status Card */
                #navbar-timer .employee-status-card {
                    padding: 10px;
                    border-bottom: 1px solid #ced4da; /* Adjusted border color */
                }

                #navbar-timer .employee-info {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }

                #navbar-timer .employee-avatar {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                }

                #navbar-timer .employee-details {
                    flex: 1;
                }

                #navbar-timer .employee-name {
                    font-weight: 500;
                    margin-bottom: 4px;
                    color: #212529; /* Ensure visibility */
                }

                #navbar-timer .task-info {
                    font-size: 12px;
                    color: #495057; /* Ensure visibility */
                }

                #navbar-timer .task-time {
                    color: #6c757d; /* Text muted color */
                    font-size: 11px;
                    margin-top: 2px;
                }

                /* Task Card */
                #navbar-timer .task-card {
                    padding: 10px;
                    border: 1px solid #ced4da; /* Adjusted border color */
                    border-radius: 4px;
                    margin-bottom: 10px;
                    background-color: #ffffff; /* Explicit background for light mode */
                }

                #navbar-timer .task-card.overdue {
                    border-right: 3px solid #dc3545; /* Danger color */
                }

                #navbar-timer .task-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }

                #navbar-timer .task-subject {
                    font-weight: 500;
                    color: #212529; /* Ensure visibility */
                    text-decoration: none;
                }

                #navbar-timer .days-overdue {
                    color: #dc3545; /* Danger color */
                    font-size: 11px;
                }

                #navbar-timer .total-time {
                    color: #007bff; /* Primary color */
                    font-weight: 500;
                }

                #navbar-timer .task-details {
                    display: flex;
                    gap: 15px;
                    margin-bottom: 8px;
                    font-size: 12px;
                    color: #6c757d; /* Text muted color */
                }

                #navbar-timer .detail-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }

                #navbar-timer .task-progress {
                    margin: 8px 0;
                }

                #navbar-timer .task-progress .progress {
                    height: 4px;
                    margin-bottom: 2px;
                }

                #navbar-timer .task-progress small {
                    font-size: 11px;
                    color: #6c757d; /* Text muted color */
                }

                /* Buttons */
                #navbar-timer .start-task-btn,
                #navbar-timer .stop-task-btn {
                    width: 100%;
                    margin-top: 8px;
                }

                /* Dark Mode Support */
                .dark #navbar-timer .timer-dropdown,
                .dark #navbar-timer .task-card {
                    background-color: #343a40 !important; /* Dark background */
                    border-color: #495057 !important; /* Dark border */
                    color: #f8f9fa !important; /* Light text */
                }

                 .dark #navbar-timer .today-chart-summary {
                    background-color: #454d55 !important; /* Slightly lighter dark background */
                    border-color: #495057 !important; /* Dark border */
                    color: #f8f9fa !important; /* Light text */
                }
                
                .dark #navbar-timer .today-chart-summary h6,
                .dark #navbar-timer .today-chart-summary .summary-text {
                     color: #ced4da !important; /* Lighter text in dark mode */
                }

                .dark #navbar-timer .timer-tabs .nav-link {
                    color: #ced4da !important; /* Lighter text in dark mode */
                }
                
                .dark #navbar-timer .timer-tabs .nav-link.active {
                    color: #00aaff !important; /* Brighter primary in dark mode */
                    border-bottom-color: #00aaff !important; /* Brighter primary in dark mode */
                }

                .dark #navbar-timer .employee-name,
                .dark #navbar-timer .task-subject {
                    color: #f8f9fa !important; /* Light text */
                }

                .dark #navbar-timer .task-time,
                .dark #navbar-timer .task-details,
                .dark #navbar-timer .detail-item,
                .dark #navbar-timer .task-progress small {
                    color: #ced4da !important; /* Lighter text in dark mode */
                }

                /* Responsive Design */
                @media (max-width: 768px) {
                    #navbar-timer .timer-dropdown {
                        position: fixed !important;
                        top: 60px !important;
                        left: 0 !important;
                        right: 0 !important;
                        width: 100% !important;
                        max-width: none !important;
                        margin: 0 !important;
                        border-radius: 0 !important;
                        border-left: none !important;
                        border-right: none !important;
                    }

                    #navbar-timer .timer-tabs {
                        overflow-x: auto;
                        white-space: nowrap;
                        -webkit-overflow-scrolling: touch;
                    }

                    #navbar-timer .timer-tabs .nav-link {
                        padding: 8px;
                    }
                }
            </style>
        `);
    }
}

// Helper function for formatting duration (re-using logic from backend or similar)
function formatDuration(seconds) {
    if (seconds === null || seconds === undefined || seconds < 0) {
        return "0 دقیقه";
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${remainingSeconds}s`;
    } else {
        return `${remainingSeconds}s`;
    }
}

// Helper function to generate a random color
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// تابع Global برای استفاده در Client Script
window.refresh_navbar_timer = refresh_navbar_timer;
window.start_task = start_task;
window.stop_task = stop_task;