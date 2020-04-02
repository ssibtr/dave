# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import choice
from string import digits
from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
from odoo.exceptions import UserError

# TODO: STEP 1 CHECK IN CREATE NEW ATTENDANCE AND NEW ATTENDANCE LINE
# TODO: STEP 2 SWITCH CLOSE CURRENT LINE AND CREATE NEW ONE
# TODO: STEP 3 CLOSE CLOSE CURRENT LINE AND ATTENDANCE


#! NEXT ACTION CREATES A NEW ATTENDANCE 
#! THE ONLY THING MANIPULATED HERE IS THE CKECK OUT OPTION CLOSING OR NOT THE ATTENDANCE

class HrEmployeeCustom(models.Model):
    _inherit = "hr.employee"

    last_attendance_id = fields.Many2one('hr.attendance', compute='_compute_last_attendance_id', store=True)
    attendance_state = fields.Selection(string="Attendance Status", compute='_compute_attendance_state', selection=[('checked_out', "Checked out"), ('checked_in', "Checked in")])

    @api.multi
    def attendance_manual(self, next_action, entered_pin=None, job=None, wo=None, close=None, end=None):
        self.ensure_one()
        if not (entered_pin is None) or self.env['res.users'].browse(SUPERUSER_ID).has_group('hr_attendance.group_hr_attendance_use_pin') and (self.user_id and self.user_id.id != self._uid or not self.user_id):
            if entered_pin != self.pin:
                return {'warning': _('Wrong PIN')}
        return self.attendance_action(next_action, job, wo, close, end)

    @api.multi
    def attendance_action(self, next_action, job=None, wo=None, close=None, end=None):
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        action_message = self.env.ref('hr_attendance.hr_attendance_action_greeting_message').read()[0]
        action_message['previous_attendance_change_date'] = self.last_attendance_id and (self.last_attendance_id.check_out or self.last_attendance_id.check_in) or False
        action_message['employee_name'] = self.name
        action_message['barcode'] = self.barcode
        action_message['next_action'] = next_action

        if self.user_id:
            if next_action == 'hr_attendance.hr_attendance_action_kiosk_mode':           
                modified_attendance = self.sudo(self.user_id.id).attendance_action_change_k(job, wo, end)
                if close:
                    work_order = self.env['mrp.workorder'].search([('id', '=', wo)], limit=1)
                    if work_order:
                        res = work_order.record_production()
#                         work_order.state = 'done'
            else:
                modified_attendance = self.sudo(self.user_id.id).attendance_action_change()
        else:
            if next_action == 'hr_attendance.hr_attendance_action_kiosk_mode':           
                modified_attendance = self.sudo().attendance_action_change_k(job, wo, end)
                if close:
                    work_order = self.env['mrp.workorder'].search([('id', '=', wo)], limit=1)
                    if work_order:
                        res = work_order.record_production()
#                         work_order.state = 'done'
            else:
                modified_attendance = self.sudo().attendance_action_change()
        action_message['attendance'] = modified_attendance.read()[0]
        return {'action': action_message}
        
    @api.multi
    def attendance_action_change_k(self, job=None, wo=None, end=None):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        if len(self) > 1:
            raise exceptions.UserError(_('Cannot perform check in or check out on multiple employees.'))
        action_date = fields.Datetime.now()

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
            }
            attendance = self.env['hr.attendance'].create(vals)
            vals_l = {
                'employee_id': self.id,
                'check_in': action_date,
                'attendance_id': attendance.id,
            }
            self.env['hr.attendance.line'].create(vals_l)
            return attendance
        else:
            attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_out', '=', False)], limit=1)
            attendance_line = self.env['hr.attendance.line'].search([('employee_id', '=', self.id), ('check_out', '=', False)], limit=1)
            if attendance:
                if end == 'True':
                    attendance.check_out = action_date
                    if attendance_line:
                        if not job or not wo:
                            raise exceptions.UserError(_('Must choose a job and work order to log time.'))
                        else:
                            attendance_line.check_out = action_date
                            attendance_line.job_id = job
                            attendance_line.workorder_id = wo
                else:
                    if attendance_line:
                        if not job or not wo:
                            raise exceptions.UserError(_('Must choose a job and work order to log time.'))
                        else:
                            attendance_line.check_out = action_date
                            attendance_line.job_id = job
                            attendance_line.workorder_id = wo
                    vals_l = {
                        'employee_id': self.id,
                        'check_in': action_date,
                        'attendance_id': attendance.id,
                    }
                    self.env['hr.attendance.line'].create(vals_l)
            else:
                raise exceptions.UserError(_('Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                    'Your attendances have probably been modified manually by human resources.') % {'empl_name': self.name, })
            return attendance

    @api.multi
    def attendance_check_pin(self, next_action, entered_pin=None):
        self.ensure_one()
        if not (entered_pin is None) or self.env['res.users'].browse(SUPERUSER_ID).has_group('hr_attendance.group_hr_attendance_use_pin') and (self.user_id and self.user_id.id != self._uid or not self.user_id):
            if entered_pin != self.pin:
                return {'warning': _('Wrong PIN')}
        return {'warning': ''}

    @api.multi
    def attendance_split_time(self, next_action, job=None, wo=None, close=None, end=None):
        """ Allows employee to split time.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        action_message = self.env.ref('hr_attendance.hr_attendance_action_greeting_message').read()[0]
        action_message['previous_attendance_change_date'] = self.last_attendance_id and (self.last_attendance_id.check_out or self.last_attendance_id.check_in) or False
        action_message['employee_name'] = self.name
        action_message['barcode'] = self.barcode
        action_message['next_action'] = next_action

        if self.user_id:
            modified_attendance = self.sudo(self.user_id.id).attendance_action_split_change(job, wo, end)
        else:
            modified_attendance = self.sudo().attendance_action_split_change(job, wo, end)
        action_message['attendance'] = modified_attendance.read()[0]
        return {'action': action_message}
        
    @api.multi
    def attendance_action_split_change(self, job=None, wo=None, end=None):
        """ Check In/Check Out action - for Split Time
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        if len(self) > 1:
            raise exceptions.UserError(_('Cannot perform check in or check out on multiple employees.'))
        action_date = fields.Datetime.now()

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
            }
            attendance = self.env['hr.attendance'].create(vals)
            vals_l = {
                'employee_id': self.id,
                'check_in': action_date,
                'attendance_id': attendance.id,
            }
            self.env['hr.attendance.line'].create(vals_l)
            return attendance
        else:
            attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_out', '=', False)], limit=1)
            attendance_line = self.env['hr.attendance.line'].search([('employee_id', '=', self.id), ('check_out', '=', False)], limit=1)
            if attendance:
                if end == 'True':
                    attendance.check_out = action_date
                    if attendance_line:
                        if not job or not wo:
                            raise exceptions.UserError(_('Must choose a job and work order to log time.'))
                        else:
                            ct = len(job)
                            delta = (action_date - attendance_line.check_in) / ct
                            check = attendance_line.check_in + delta
                            for key, val in enumerate(job):
                                if key == 0:
                                    attendance_line.check_out = check
                                    attendance_line.job_id = val
                                    attendance_line.workorder_id = wo[key]
                                else:
                                    c_in = check
                                    check = c_in + delta
                                    vals_l = {
                                        'employee_id': self.id,
                                        'check_in': c_in,
                                        'check_out': check,
                                        'attendance_id': attendance.id,
                                        'job_id': val,
                                        'workorder_id': wo[key],
                                    }
                                    self.env['hr.attendance.line'].create(vals_l)

                else:
                    if attendance_line:
                        if not job or not wo:
                            raise exceptions.UserError(_('Must choose a job and work order to log time.'))
                        else:
                            ct = len(job)
                            delta = (action_date - attendance_line.check_in) / ct
                            check = attendance_line.check_in + delta
                            for key, val in enumerate(job):
                                if key == 0:
                                    attendance_line.check_out = check
                                    attendance_line.job_id = val
                                    attendance_line.workorder_id = wo[key]
                                else:
                                    c_in = check
                                    check = c_in + delta
                                    vals_l = {
                                        'employee_id': self.id,
                                        'check_in': c_in,
                                        'check_out': check,
                                        'attendance_id': attendance.id,
                                        'job_id': val,
                                        'workorder_id': wo[key],
                                    }
                                    self.env['hr.attendance.line'].create(vals_l)
                    vals_l = {
                        'employee_id': self.id,
                        'check_in': action_date,
                        'attendance_id': attendance.id,
                    }
                    self.env['hr.attendance.line'].create(vals_l)
            else:
                raise exceptions.UserError(_('Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                    'Your attendances have probably been modified manually by human resources.') % {'empl_name': self.name, })
            return attendance

    @api.depends('last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state(self):
        for employee in self:
#             att = employee.last_attendance_id.sudo()
            att = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('check_out', '=', False)], limit=1)
            employee.attendance_state = att and not att.check_out and 'checked_in' or 'checked_out'

    @api.depends('attendance_ids')
    def _compute_last_attendance_id(self):
        for employee in self:
            employee.last_attendance_id = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id), ('hour_type', '=', False)
            ], limit=1)

