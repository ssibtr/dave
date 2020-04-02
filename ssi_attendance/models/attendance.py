# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from datetime import datetime
from pytz import timezone, UTC

class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'mail.thread', 'mail.activity.mixin']

    status = fields.Selection(string="Status", selection=[(
        'open', 'Open'), ('approved', 'Approved')], default='open', track_visibility='onchange')
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True, store=True)
#     hour_type = fields.Selection(string="Type of Hours", selection=[
#         ('Regular', 'Regular'), 
#         ('PTO-I', 'PTO-I'),
#         ('PTO-E', 'PTO-E'), 
#         ('PTO Sell', 'PTO Sell'), 
#         ('Jury Duty', 'Jury Duty'), 
#         ('Holiday', 'Holiday'), 
#         ('Bereavement', 'Bereavement')], default='Regular')
    check_in = fields.Datetime(string="Check In", track_visibility='onchange')
    check_out = fields.Datetime(string="Check Out", track_visibility='onchange')
    worked_hours = fields.Float(string="Worked Hours", track_visibility='onchange')
    hour_type = fields.Many2one('hr.leave.type', string="Leave Type", readonly=True)
    attendance_lines = fields.One2many('hr.attendance.line', 'attendance_id', string='Attendance Lines', copy=True, track_visibility='always')
    manager_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager", store=True, track_visibility='always')
    check_in_inv = fields.Datetime(string="Check In")
    check_out_inv = fields.Datetime(string="Check Out")
    worked_actual_inv = fields.Float(string='Worked Hours Actual')
    worked_hours_inv = fields.Float(string='Worked Hours')
    line_count = fields.Integer(string='Attedance Line Count', compute='_get_line_count')
    worked_hours_actual = fields.Float(string='Worked Hours Actual', compute='_compute_actual_hours')
    show_approve = fields.Boolean(string="Show Approval Button", compute='_check_show_approve')
    hide_in_kiosk = fields.Many2one('ssi_jobs', string="Hide in Kiosk")

    @api.depends('attendance_lines')
    def _get_line_count(self):
        for record in self:
            record.line_count = len(record.attendance_lines)

    @api.depends('check_in')
    def _check_show_approve(self):
        if self.env.user.tz:
            tz = self.env.user.tz
        else:
            tz = 'US/Central'
        if self.check_in.astimezone(timezone(tz)).date() >= datetime.now().date():
            self.show_approve = False
        else:
            self.show_approve = True

    @api.depends('attendance_lines')
    def _compute_actual_hours(self):
        total = 0
        for line in self.attendance_lines.sorted(key=lambda r: r.check_in):
            total += line.worked_hours
        self.worked_hours_actual = total

    @api.one
    def approve_attendance(self):
        for line in self.attendance_lines:
            data = {
                'workorder_id': line.workorder_id.id,
                'workcenter_id': line.workorder_id.workcenter_id.id,
                'loss_id': 7,
                'user_id': line.employee_id.user_id.id,
                'date_start': line.check_in,
                'date_end': line.check_out,
                # 'x_studio_labor_codes': self.labor_code_id.id
            }
            line.status = 'approved'
            self.env['mrp.workcenter.productivity'].sudo().create(data)
        self.status = 'approved'

    @api.onchange('attendance_lines')
    def _onchange_attendance_line(self):
        # sync the start / stop times.
        first = True
        vals = {}
        total = 0
        for line in self.attendance_lines.sorted(key=lambda r: r.check_in):
            if first:
                self.check_in_inv = line.check_in
                self.check_in = line.check_in
                first = False
            self.check_out_inv = line.check_out
            self.check_out = line.check_out
        self.worked_actual_inv = self.worked_hours_actual
        self.worked_hours_inv = self.worked_hours
                
    @api.model
    def create(self, vals):
        if 'check_in_inv' in vals:
            vals['check_in'] = not vals['check_in_inv'] and vals['check_in'] or vals['check_in_inv']
#             vals['check_in'] = vals['check_in_inv']
        if 'check_out_inv' in vals:
            vals['check_out'] = not vals['check_out_inv'] and vals['check_out'] or vals['check_out_inv']
#             vals['check_out'] = vals['check_out_inv']
        if 'worked_actual_inv' in vals:
            if round(vals['worked_hours_inv'],2) != round(vals['worked_actual_inv'],2) and vals['worked_actual_inv'] > 0:
                raise UserError(_('Warning: The hours and job hours do not balance.'))
        if 'worked_actual_inv' in vals:
            del vals['worked_actual_inv']
        if 'worked_hours_inv' in vals:
            del vals['worked_hours_inv']
        res = super(HrAttendance, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if 'check_in_inv' in vals:
            vals['check_in'] = not vals['check_in_inv'] and vals['check_in'] or vals['check_in_inv']
#             vals['check_in'] = vals['check_in_inv']
        if 'check_out_inv' in vals:
            vals['check_out'] = not vals['check_out_inv'] and vals['check_out'] or vals['check_out_inv']
#             vals['check_out'] = vals['check_out_inv']
        if 'worked_actual_inv' in vals:
            if round(vals['worked_hours_inv'],2) != round(vals['worked_actual_inv'],2) and vals['worked_actual_inv'] > 0:
                raise UserError(_('Warning: The hours and job hours do not balance.'))
        if 'worked_actual_inv' in vals:
            del vals['worked_actual_inv']
        if 'worked_hours_inv' in vals:
            del vals['worked_hours_inv']
        res = super(HrAttendance, self).write(vals)
        return res
        
class HrAttendanceLine(models.Model):
    _name = "hr.attendance.line"
    _description = "Attendance  Detail"

    def _default_employee(self):
        if self.env.context.get('employee_id'):
            return self.env.context.get('employee_id')
        else:
            return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True, ondelete='cascade', index=True)
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True, store=True)
    manager_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager", store=True)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance ID', required=True, ondelete='cascade', index=True, copy=False)
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True)
    check_out = fields.Datetime(string="Check Out")
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    status = fields.Selection(string="Status", selection=[(
        'open', 'Open'), ('approved', 'Approved')], default='open', track_visibility='onchange')

    job_id = fields.Many2one(
       'ssi_jobs', ondelete='set null', string="Job", index=True)
    workorder_id = fields.Many2one(
       'mrp.workorder', ondelete='set null', string="Work Order", index=True)

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for line in self:
            if line.check_out:
                delta = line.check_out - line.check_in
                line.worked_hours = delta.total_seconds() / 3600.0

    @api.multi
    def write(self, values):
        """Override default Odoo write function and extend."""
        # Do your custom logic here
        if self.attendance_id.check_in and self.attendance_id.check_in == self.check_in and 'check_in' in values:
            self.attendance_id.check_in = values['check_in']
        if self.attendance_id.check_out and self.attendance_id.check_out == self.check_out and 'check_out' in values:
            self.attendance_id.check_out = values['check_out']
        # Check for adjustments to other detial lines
#         alo = self.env['hr.attendance.line'].search([('attendance_id', '=', self.attendance_id.id),('check_out', '=', self.check_in)])
#         if alo:
#             alo.check_out = values['check_in']
#         ali = self.env['hr.attendance.line'].search([('attendance_id', '=', self.attendance_id.id),('check_in', '=', self.check_out)])
#         if ali:
#             ali.check_in = values['check_out']
        return super(HrAttendanceLine, self).write(values)

    @api.onchange('job_id')
    def _onchange_job_id(self):
        # When updating jobs dropdown, blank out wo.
        self.workorder_id = 0

