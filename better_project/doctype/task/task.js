frappe.provide('better_project.task');

better_project.task.TaskTimer = class TaskTimer {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.task_name = wrapper.cur_frm.doc.name;
        this.setup();
    }

    setup() {
        this.wrapper.cur_frm.custom_buttons = {
            start_timer: () => this.start_timer(),
            stop_timer: () => this.stop_timer(),
            complete_task: () => this.complete_task()
        };

        this.wrapper.cur_frm.set_df_property('status', 'read_only', 1);
        this.setup_timer_buttons();
        this.setup_timer_display();
        this.start_timer_check();
    }

    setup_timer_buttons() {
        this.wrapper.cur_frm.add_custom_button(__('Start Timer'), () => this.start_timer(), __('Timer'));
        this.wrapper.cur_frm.add_custom_button(__('Stop Timer'), () => this.stop_timer(), __('Timer'));
        this.wrapper.cur_frm.add_custom_button(__('Complete Task'), () => this.complete_task(), __('Timer'));
        
        // Hide buttons initially
        this.wrapper.cur_frm.toggle_display('stop_timer', false);
        this.wrapper.cur_frm.toggle_display('complete_task', false);
    }

    setup_timer_display() {
        this.timer_display = $(`
            <div class="task-timer-display" style="margin: 10px 0;">
                <div class="timer-value" style="font-size: 1.2em; font-weight: bold;"></div>
            </div>
        `).insertAfter(this.wrapper.cur_frm.fields_dict.status.$wrapper);
        
        this.timer_display.hide();
    }

    async start_timer() {
        try {
            const result = await frappe.call({
                method: 'better_project.better_project.doctype.task.task.start_timer',
                args: {
                    task_name: this.task_name
                }
            });

            if (result.message) {
                this.time_log = result.message.time_log;
                this.start_time = new Date();
                this.update_timer_display();
                this.timer_display.show();
                this.wrapper.cur_frm.toggle_display('start_timer', false);
                this.wrapper.cur_frm.toggle_display('stop_timer', true);
                this.wrapper.cur_frm.toggle_display('complete_task', true);
                
                // Update navbar task indicator
                this.update_navbar_task();
            }
        } catch (e) {
            frappe.msgprint(e.message);
        }
    }

    async stop_timer() {
        try {
            await frappe.call({
                method: 'better_project.better_project.doctype.task.task.stop_timer',
                args: {
                    task_name: this.task_name
                }
            });

            this.timer_display.hide();
            this.wrapper.cur_frm.toggle_display('start_timer', true);
            this.wrapper.cur_frm.toggle_display('stop_timer', false);
            this.wrapper.cur_frm.toggle_display('complete_task', false);
            
            // Update navbar task indicator
            this.update_navbar_task();
            
            // Refresh the form
            this.wrapper.cur_frm.reload_doc();
        } catch (e) {
            frappe.msgprint(e.message);
        }
    }

    async complete_task() {
        try {
            await frappe.call({
                method: 'better_project.better_project.doctype.task.task.complete_task',
                args: {
                    task_name: this.task_name
                }
            });

            this.timer_display.hide();
            this.wrapper.cur_frm.toggle_display('start_timer', false);
            this.wrapper.cur_frm.toggle_display('stop_timer', false);
            this.wrapper.cur_frm.toggle_display('complete_task', false);
            
            // Update navbar task indicator
            this.update_navbar_task();
            
            // Refresh the form
            this.wrapper.cur_frm.reload_doc();
        } catch (e) {
            frappe.msgprint(e.message);
        }
    }

    update_timer_display() {
        if (!this.start_time) return;
        
        const update_timer = () => {
            const now = new Date();
            const diff = now - this.start_time;
            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            
            this.timer_display.find('.timer-value').text(
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
            );
        };
        
        update_timer();
        this.timer_interval = setInterval(update_timer, 1000);
    }

    async start_timer_check() {
        try {
            const result = await frappe.call({
                method: 'better_project.better_project.doctype.task.task.get_active_task',
                args: {}
            });

            if (result.message && result.message.name === this.task_name) {
                this.time_log = result.message.time_log;
                this.start_time = new Date(result.message.start_time);
                this.update_timer_display();
                this.timer_display.show();
                this.wrapper.cur_frm.toggle_display('start_timer', false);
                this.wrapper.cur_frm.toggle_display('stop_timer', true);
                this.wrapper.cur_frm.toggle_display('complete_task', true);
            }
        } catch (e) {
            console.error(e);
        }
    }

    update_navbar_task() {
        frappe.call({
            method: 'better_project.better_project.doctype.task.task.get_active_task',
            callback: (r) => {
                if (r.message) {
                    frappe.navbar.update_task_indicator(r.message);
                } else {
                    frappe.navbar.clear_task_indicator();
                }
            }
        });
    }
};

// Extend frappe.navbar to add task indicator
frappe.navbar.update_task_indicator = function(task) {
    if (!this.task_indicator) {
        this.task_indicator = $(`
            <li class="task-indicator">
                <a class="dropdown-toggle" data-toggle="dropdown" href="#">
                    <i class="fa fa-tasks"></i>
                    <span class="task-timer"></span>
                </a>
                <ul class="dropdown-menu task-dropdown">
                    <li class="task-info"></li>
                    <li class="divider"></li>
                    <li><a class="stop-task" href="#">Stop Task</a></li>
                    <li><a class="complete-task" href="#">Complete Task</a></li>
                </ul>
            </li>
        `).insertAfter(this.notification_dropdown);
        
        this.task_indicator.find('.stop-task').on('click', (e) => {
            e.preventDefault();
            frappe.call({
                method: 'better_project.better_project.doctype.task.task.stop_timer',
                args: { task_name: task.name },
                callback: () => {
                    frappe.set_route('Form', 'Task', task.name);
                }
            });
        });
        
        this.task_indicator.find('.complete-task').on('click', (e) => {
            e.preventDefault();
            frappe.call({
                method: 'better_project.better_project.doctype.task.task.complete_task',
                args: { task_name: task.name },
                callback: () => {
                    frappe.set_route('Form', 'Task', task.name);
                }
            });
        });
    }
    
    this.task_indicator.find('.task-info').html(`
        <a href="/app/task/${task.name}">
            <strong>${task.subject}</strong>
        </a>
    `);
    
    this.task_indicator.show();
    
    // Start timer update
    if (!this.task_timer_interval) {
        const start_time = new Date(task.start_time);
        const update_timer = () => {
            const now = new Date();
            const diff = now - start_time;
            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            
            this.task_indicator.find('.task-timer').text(
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
            );
        };
        
        update_timer();
        this.task_timer_interval = setInterval(update_timer, 1000);
    }
};

frappe.navbar.clear_task_indicator = function() {
    if (this.task_indicator) {
        this.task_indicator.hide();
    }
    if (this.task_timer_interval) {
        clearInterval(this.task_timer_interval);
        this.task_timer_interval = null;
    }
};

// Initialize task timer when form loads
frappe.ui.form.on('Task', {
    refresh: function(frm) {
        new better_project.task.TaskTimer(frm);
    }
}); 