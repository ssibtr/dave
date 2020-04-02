# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from datetime import datetime
from odoo.tools import float_compare, float_round
from odoo.exceptions import Warning, UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # SHOULD BE RELATED TO JOB IN MANUFACTURING ORDER FROM OLD STUDIo production_id.x_studio_job
    # ssi_job_id = fields.Many2one(
    # 'ssi_jobs', string='Job')
    ssi_job_id = fields.Many2one(
        'ssi_jobs', related='production_id.ssi_job_id', string='Job', store=True)
    duration_expected_hours = fields.Float(
        'Expected Hours',
        compute='_compute_expected_hours',
        readonly=True, store=True,
        help="Expected duration (in hours)")
    duration_hours = fields.Float(
        'Real Hours', compute='_compute_duration_hours',
        readonly=True, store=True)
    job_urgency = fields.Selection(related='ssi_job_id.urgency', string="Urgency", store=True, readonly=True)
    job_deadline = fields.Datetime(related='ssi_job_id.deadline_date', string="Deadline", store=True, readonly=True)
    job_stage = fields.Many2one('ssi_jobs_stage', related='ssi_job_id.stage_id', string="Job Stage", store=True, readonly=True)
    hide_in_kiosk = fields.Boolean(related='operation_id.hide_in_kiosk', string="Hide in Kiosk", store=True, readonly=True)
    # Work Order Readiness
    custom_sequence = fields.Integer(string="Custom Sequence")
    quality_check_ids = fields.One2many('quality.check', 'workorder_id', string='Quality Checks')
    quality_check_count = fields.Integer(compute='_compute_quality_checks', string="Quality Check Count")

    
    @api.depends('production_id')
    def _compute_quality_checks(self):
        for record in self:
            qc_count = self.env['quality.check'].sudo().search_count([('workorder_id', '=', record.id)])
            record.quality_check_count = qc_count
            
    @api.model
    def create(self,vals):
        #This method will update the custom sequence to the workorder's sequence.
        res = super(MrpWorkorder, self).create(vals)
        res.production_id.routing_id.calculate_custom_sequence()
        res.update({'custom_sequence': res.operation_id.custom_sequence})
        return res

    @api.depends('duration_expected')
    def _compute_expected_hours(self):
        for record in self:
            record.duration_expected_hours = record.duration_expected / 60

    @api.depends('duration')
    def _compute_duration_hours(self):
        for record in self:
            record.duration_hours = record.duration / 60

    @api.multi
    def name_get(self):
        return [(wo.id, "%s(%s) %s" % (wo.ssi_job_id.name, wo.production_id.name, wo.name)) for wo in self]
#         return [(wo.id, "%s - %s - %s" % (wo.production_id.name, wo.product_id.name, wo.name)) for wo in self]

    @api.multi
    def button_start(self):
        self.ensure_one()
        
        #WO Readiness - Method will inherit and change the logic for that.
        self.production_id.routing_id.calculate_custom_sequence()
        if self.operation_id.is_all_precending_wo_complete == True and self.operation_id.custom_sequence > 1:
            workorders = self.find_preceding_workorders(self.production_id)
            if workorders:
                if any(workorder.state != 'done' for workorder in workorders):
                    raise Warning(_('You can not process this work order, please finish preceding work order first!'))

        # As button_start is automatically called in the new view
        if self.state in ('done', 'cancel'):
            return True

        for workorder in self:
            if workorder.production_id.state != 'progress':
                workorder.production_id.write({
                    'state': 'progress',
                    'date_start': datetime.now(),
                })
        test = self.write({'state': 'progress',
                    'date_start': datetime.now(),
        })
        return test
#         return super(MrpWorkorder,self).button_start()
    

    @api.multi
    def _start_nextworkorder_ssi(self):
        rounding = self.product_id.uom_id.rounding
        next_work_order = self.search([
            ('production_id','=',self.production_id.id),
            ('state','not in',('done','cancel')),
            ('id','!=',self.id)
        ],order='custom_sequence', limit=1)
        if next_work_order.state == 'pending' and (
                (self.operation_id.batch == 'no' and
                 float_compare(self.qty_production, self.qty_produced, precision_rounding=rounding) <= 0) or
                (self.operation_id.batch == 'yes' and
                 float_compare(self.operation_id.batch_size, self.qty_produced, precision_rounding=rounding) <= 0)):
            if next_work_order.operation_id.is_all_precending_wo_complete == True and next_work_order.operation_id.custom_sequence > 1:
                workorders = self.find_next_preceding_workorders(next_work_order)
                if workorders:
                    if all(workorder.state == 'done' for workorder in workorders):
                        next_work_order.state = 'ready'
            else:
                next_work_order.state = 'ready'

    @api.multi
    def find_preceding_workorders(self,production_id):
        #Method will find work orders and returns them
        workorders = self.search([('production_id','=',production_id.id),('custom_sequence','<',self.custom_sequence)])
        if workorders:
            return workorders
        else:
            return False
        
    @api.multi
    def find_next_preceding_workorders(self,next_wo):
        #Method will find work orders and returns them
        workorders = self.search([
            ('production_id','=',next_wo.production_id.id),
            ('custom_sequence','<',next_wo.operation_id.custom_sequence),
            ('id','!=',self.id)
        ])
        if workorders:
            return workorders
        else:
            return False
    
class Workcenter(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    ssi_job_id = fields.Many2one('ssi_jobs', related='workorder_id.ssi_job_id', string='Job', store=True)
#    ssi_job_id = fields.Many2one(
#        'workorder_id.ssi_job_id', string='Job')
    # ssi_job_id = fields.Many2one(
    #     related='workorder_id.ssi_job_id', relation="ssi_jobs.ssi_jobs", string='Job', domain=[])
    
class Produciton(models.Model):
    _inherit = 'mrp.production'

    ssi_job_id = fields.Many2one('ssi_jobs', string='Job')
    job_stage = fields.Many2one('ssi_jobs_stage', related='ssi_job_id.stage_id', string="Job Stage", store=True, readonly=True)
    product_category = fields.Many2one('product.category', related='product_id.categ_id', string="Product Category", store=True, readonly=True)
    
class MrpRouting(models.Model):

    _inherit = 'mrp.routing'

    # Custom for Workorder Readiness
    @api.multi
    def calculate_custom_sequence(self):
        #Calculates custom sequence
        sequence = 0
        if self.operation_ids:
            for operation in self.operation_ids:
                operation.sudo().write({'custom_sequence': sequence + 1})
                sequence += 1

class RoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    time_cycle_hours = fields.Float(
        'Hour Duration', compute='_compute_cycle_hours',
        help="Time in hours.")
    time_cycle_manual_hours = fields.Float(
        'Manual Hour Duration', compute='_compute_cycle_manual_hours',
        help="Time in hours.")
    hide_in_kiosk = fields.Boolean(default=False, string="Hide in Kiosk")
    # Work Order Readiness
    is_all_precending_wo_complete = fields.Boolean('Is All Preceding WO Complete',default=False,copy=False)
    custom_sequence = fields.Integer('Custom Sequence',copy=False)
    
    @api.depends('time_cycle')
    def _compute_cycle_hours(self):
        for record in self:
            record.time_cycle_hours = record.time_cycle / 60

    @api.depends('time_cycle_manual')
    def _compute_cycle_manual_hours(self):
        for record in self:
            record.time_cycle_manual_hours = record.time_cycle_manual / 60

