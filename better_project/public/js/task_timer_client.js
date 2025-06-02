// Task Timer Client Script
// این کد باید در hooks.py فایل اضافه شود به عنوان app_include_js

class TaskTimer {
    constructor(frm) {
        this.frm = frm;
        this.task_name = frm.doc.name;
        this.timer_interval = null;
        this.start_time = null;
        this.elapsed_time = 0;
        this.is_running = false;
        
        this.setup();
    }
    
    setup() {
            // اضافه کردن دکمه‌های Timer
        this.add_timer_section();
        
        // بررسی وضعیت Timer
        this.check_timer_status();
        
        // تنظیم Status به Read Only در صورت لزوم
        this.configure_status_field();
    }
    
    add_timer_section() {
        // حذف بخش قبلی در صورت وجود
        $('.task-timer-section').remove();
        
        // ایجاد بخش Timer
        const timer_html = `
            <div class="task-timer-section" style="margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                <!-- دکمه‌های کنترل -->
                <div class="timer-buttons" style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                    <button class="btn btn-success" id="start-timer-btn">
                        <i class="fa fa-play"></i> شروع زمان‌سنج
                    </button>
                    <button class="btn btn-warning" id="stop-timer-btn" style="display: none;">
                        <i class="fa fa-pause"></i> توقف زمان‌سنج
                    </button>
                    <button class="btn btn-primary" id="complete-task-btn">
                        <i class="fa fa-check"></i> تکمیل تسک
                    </button>
                </div>
                
                <!-- نمایش Timer -->
                <div id="timer-display" class="timer-display" style="display: none;">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="timer-info">
                                <h5 style="color: #28a745; margin: 0;">
                                    <i class="fa fa-clock-o"></i> زمان فعلی
                                </h5>
                                <div class="timer-value" style="font-family: monospace; font-size: 28px; font-weight: bold; color: #28a745; margin: 10px 0;">
                                    <span id="current-timer">00:00:00</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="total-time-info">
                                <h6 style="color: #6c757d; margin: 0;">مجموع زمان این تسک</h6>
                                <div style="font-family: monospace; font-size: 18px; color: #495057; margin: 10px 0;">
                                    <span id="total-time">محاسبه در حال انجام...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="timer-status" style="margin-top: 10px; padding: 8px; background: #e8f5e8; border-radius: 4px; border-left: 4px solid #28a745;">
                        <small class="text-success">
                            <i class="fa fa-info-circle"></i> 
                            زمان‌سنج در حال اجرا - شروع: <span id="start-time-display">--:--:--</span>
                        </small>
                    </div>
                </div>
            </div>
        `;
        
        // اضافه کردن به فرم
        $(this.frm.fields_dict.subject.wrapper).after(timer_html);
        
        // اضافه کردن Event Handlers
        $('#start-timer-btn').on('click', () => this.start_timer());
        $('#stop-timer-btn').on('click', () => this.stop_timer());
        $('#complete-task-btn').on('click', () => this.complete_task());
    }
    
    async start_timer() {
        try {
            // نمایش لودینگ
            $('#start-timer-btn').prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> در حال شروع...');
            
            const response = await frappe.call({
        method: 'better_project.api.task_timer.start_timer',
        args: {
                    task: this.task_name
                }
            });
            
            if (response.message && response.message.success) {
                this.is_running = true;
                this.start_time = new Date();
                this.elapsed_time = 0;
                
                // بروزرسانی UI
                this.update_ui_for_running_timer();
                
                // شروع بروزرسانی Timer
                this.start_timer_update();
                
                // بروزرسانی Navbar
                this.refresh_navbar_timer();
                
                // نمایش پیام موفقیت
                frappe.show_alert({
                    message: 'زمان‌سنج با موفقیت شروع شد',
                    indicator: 'green'
                });
                
                // اگر تسک دیگری متوقف شده، اطلاع دهی
                if (response.message.stopped_task) {
                    setTimeout(() => {
                    frappe.show_alert({
                            message: `زمان‌سنج تسک "${response.message.stopped_task}" متوقف شد`,
                        indicator: 'orange'
                    });
                    }, 1500);
                }
                
            } else {
                frappe.show_alert({
                    message: response.message?.error || 'خطا در شروع زمان‌سنج',
                    indicator: 'red'
                });
            }
        } catch (error) {
            console.error('Timer start error:', error);
            frappe.show_alert({
                message: 'خطا در شروع زمان‌سنج',
                indicator: 'red'
    });
        } finally {
            // بازگردانی دکمه
            $('#start-timer-btn').prop('disabled', false).html('<i class="fa fa-play"></i> شروع زمان‌سنج');
        }
    }
    
    async stop_timer() {
        try {
            $('#stop-timer-btn').prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> در حال توقف...');
            
            const response = await frappe.call({
        method: 'better_project.api.task_timer.stop_timer',
        args: {
                    task: this.task_name
                }
            });
            
            if (response.message && response.message.success) {
                this.is_running = false;
                this.start_time = null;
                
                // بروزرسانی UI
                this.update_ui_for_stopped_timer();
                
                // توقف بروزرسانی Timer
                this.stop_timer_update();
                
                // بروزرسانی Navbar
                this.refresh_navbar_timer();
                
                // بروزرسانی مجموع زمان
                this.update_total_time();
                
                frappe.show_alert({
                    message: 'زمان‌سنج متوقف شد',
                    indicator: 'orange'
                });
                
            } else {
                frappe.show_alert({
                    message: response.message?.error || 'خطا در توقف زمان‌سنج',
                    indicator: 'red'
                });
            }
        } catch (error) {
            console.error('Timer stop error:', error);
            frappe.show_alert({
                message: 'خطا در توقف زمان‌سنج',
                indicator: 'red'
    });
        } finally {
            $('#stop-timer-btn').prop('disabled', false).html('<i class="fa fa-pause"></i> توقف زمان‌سنج');
        }
    }
    
    async complete_task() {
    frappe.confirm(
            'آیا مطمئن هستید که می‌خواهید این تسک را تکمیل کنید؟<br><small class="text-muted">در صورت تکمیل، زمان‌سنج متوقف شده و وضعیت تسک به "تکمیل شده" تغییر خواهد کرد.</small>',
            async () => {
                try {
                    $('#complete-task-btn').prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> در حال تکمیل...');
                    
                    const response = await frappe.call({
                method: 'better_project.api.task_timer.complete_task',
                args: {
                            task: this.task_name
                        }
                    });
                    
                    if (response.message && response.message.success) {
                        this.is_running = false;
                        this.start_time = null;
                        
                        // مخفی کردن کل بخش Timer
                        $('.task-timer-section').slideUp();
                        
                        // توقف بروزرسانی Timer
                        this.stop_timer_update();
                        
                        // بروزرسانی Navbar
                        this.refresh_navbar_timer();
                        
                        frappe.show_alert({
                            message: 'تسک با موفقیت تکمیل شد',
                            indicator: 'green'
                        });
                        
                        // بروزرسانی فرم
                        setTimeout(() => {
                            this.frm.reload_doc();
                        }, 1500);
                        
                    } else {
                        frappe.show_alert({
                            message: response.message?.error || 'خطا در تکمیل تسک',
                            indicator: 'red'
                        });
                    }
                } catch (error) {
                    console.error('Task completion error:', error);
                    frappe.show_alert({
                        message: 'خطا در تکمیل تسک',
                        indicator: 'red'
            });
                } finally {
                    $('#complete-task-btn').prop('disabled', false).html('<i class="fa fa-check"></i> تکمیل تسک');
}
            }
        );
    }
    
    update_ui_for_running_timer() {
        // نمایش Timer
        $('#timer-display').slideDown();
        
        // تغییر دکمه‌ها
        $('#start-timer-btn').hide();
        $('#stop-timer-btn').show();
        
        // نمایش زمان شروع
        const now = new Date();
        $('#start-time-display').text(now.toLocaleTimeString('fa-IR'));
    }
    
    update_ui_for_stopped_timer() {
        // مخفی کردن Timer
        $('#timer-display').slideUp();
        
        // تغییر دکمه‌ها
        $('#start-timer-btn').show();
        $('#stop-timer-btn').hide();
    }
    
    start_timer_update() {
        this.stop_timer_update(); // توقف Timer قبلی
        this.timer_interval = setInterval(() => {
            this.update_timer_display();
        }, 1000);
    }
    
    stop_timer_update() {
        if (this.timer_interval) {
            clearInterval(this.timer_interval);
            this.timer_interval = null;
        }
    }
    
    update_timer_display() {
        if (!this.is_running || !this.start_time) return;
        
        const now = new Date();
        const elapsed_seconds = Math.floor((now - this.start_time) / 1000);
        
        const hours = Math.floor(elapsed_seconds / 3600);
        const minutes = Math.floor((elapsed_seconds % 3600) / 60);
        const seconds = elapsed_seconds % 60;
        
        const display = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        $('#current-timer').text(display);
    }
    
    async check_timer_status() {
        try {
            const response = await frappe.call({
        method: 'better_project.api.task_timer.get_timer_status',
        args: {
                    task_name: this.task_name
                }
            });
            
            if (response.message && response.message.is_running) {
                this.is_running = true;
                this.start_time = new Date(response.message.start_time);
                
                // بروزرسانی UI
                this.update_ui_for_running_timer();
                
                // شروع بروزرسانی Timer
                this.start_timer_update();
}

            // بروزرسانی مجموع زمان
            this.update_total_time();
            
        } catch (error) {
            console.error('Error checking timer status:', error);
        }
    }
    
    async update_total_time() {
        try {
            const response = await frappe.call({
        method: 'better_project.api.task_timer.get_task_time_info',
        args: {
                    task_name: this.task_name
                }
            });
            
            if (response.message) {
                const total_formatted = response.message.total_time_formatted || '00:00:00';
                $('#total-time').text(total_formatted);
            }
        } catch (error) {
            console.error('Error updating total time:', error);
        }
    }
    
    configure_status_field() {
        // اگر تسک تکمیل شده، Timer را نمایش نده
        if (this.frm.doc.status === 'Completed') {
            $('.task-timer-section').hide();
        }
    }
    
    refresh_navbar_timer() {
        // بروزرسانی Timer در Navbar
        if (window.refresh_navbar_timer) {
            window.refresh_navbar_timer();
        }
    }
}

// راه‌اندازی Timer در فرم Task
frappe.ui.form.on('Task', {
    refresh: function(frm) {
        // فقط برای تسک‌های ذخیره شده Timer را نمایش بده
        if (!frm.doc.__islocal && frm.doc.name) {
            // تاخیر کوتاه برای اطمینان از بارگذاری کامل فرم
            setTimeout(() => {
                new TaskTimer(frm);
            }, 500);
                }
    },
    
    before_save: function(frm) {
        // اگر وضعیت به تکمیل شده تغییر کرد، Timer را متوقف کن
        if (frm.doc.status === 'Completed' && frm.doc.__original_status !== 'Completed') {
            // این کار در سمت سرور انجام می‌شود
        }
    }
});

// استایل‌های CSS
$(document).ready(function() {
    if (!$('#task-timer-styles').length) {
        $('head').append(`
            <style id="task-timer-styles">
                .task-timer-section {
                    border-left: 4px solid #28a745;
                    transition: all 0.3s ease;
}

                .task-timer-section:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .timer-buttons button {
                    min-width: 130px;
                    font-weight: 500;
                }
                
                .timer-display {
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    animation: fadeIn 0.5s ease-in;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .timer-value {
                    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                }
                
                /* سازگاری با تم تیره */
                .dark .task-timer-section {
                    background: #2d3748 !important;
                    border-color: #4a5568;
                }
                
                .dark .timer-display {
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%) !important;
                }
                
                .dark .timer-status {
                    background: #2d5a3d !important;
                    border-left-color: #48bb78 !important;
                }
                
                /* انیمیشن برای دکمه‌ها */
                .timer-buttons button {
                    transition: all 0.2s ease;
                }
                
                .timer-buttons button:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                
                /* Responsive Design */
                @media (max-width: 768px) {
                    .timer-buttons {
                        flex-direction: column;
                    }
                    
                    .timer-buttons button {
                        margin-bottom: 5px;
                    }
                    
                    .timer-value {
                        font-size: 24px !important;
                    }
                }
            </style>
        `);
    }
});