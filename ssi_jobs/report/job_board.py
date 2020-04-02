# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class JobBoardReport(models.Model):
    _name = "ssi_jobs.board"
    _description = "Job Board Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done', 'paid']

    name = fields.Char('Job Name', readonly=True)
    date = fields.Datetime('Create Date', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    rating = fields.Char('Rating', readonly=True)
    urgency = fields.Char('Urgency', readonly=True)
    deadline = fields.Datetime('Customer Deadline', readonly=True)
    stage_id = fields.Many2one('ssi_jobs_stage', string='Stage', readonly=True)
    disassembly = fields.Integer('Disassembly', readonly=True)
    bake_oven = fields.Integer('Bake Oven', readonly=True)
    utilities = fields.Integer('Utilities', readonly=True)
    machine = fields.Integer('Machine Shop', readonly=True)
    winding = fields.Integer('Winding', readonly=True)
    balancing = fields.Integer('Balancing', readonly=True)
    electrical = fields.Integer('Electrical Testing', readonly=True)
    paint = fields.Integer('Paint', readonly=True)
    assembly = fields.Integer('Assembly', readonly=True)
    total = fields.Integer('Total', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(j.id) as id,
            j.name as name,
            j.create_date as date,
            j.partner_id as partner_id,
            CONCAT(TO_CHAR(me.rating, '9999.'), ' ', me.rating_unit) as rating,
            j.urgency as urgency,
            j.deadline_date as deadline,
            j.stage_id as stage_id,
            count(wo.id) FILTER (WHERE wc.name = 'Disassembly' AND state in ('pending','ready','progress')) AS disassembly, 
            count(wo.id) FILTER (WHERE wc.name = 'Bake Oven' AND state in ('pending','ready','progress')) AS bake_oven, 
            count(wo.id) FILTER (WHERE wc.name = 'Utilities' AND state in ('pending','ready','progress')) AS utilities, 
            count(wo.id) FILTER (WHERE wc.name = 'Machine Shop' AND state in ('pending','ready','progress')) AS machine, 
            count(wo.id) FILTER (WHERE wc.name = 'Winding' AND state in ('pending','ready','progress')) AS winding, 
            count(wo.id) FILTER (WHERE wc.name = 'Balancing' AND state in ('pending','ready','progress')) AS balancing, 
            count(wo.id) FILTER (WHERE wc.name = 'Electrical Testing' AND state in ('pending','ready','progress')) AS electrical, 
            count(wo.id) FILTER (WHERE wc.name = 'Paint' AND state in ('pending','ready','progress')) AS paint, 
            count(wo.id) FILTER (WHERE wc.name = 'Assembly' AND state in ('pending','ready','progress')) AS assembly, 
            count(wo.id)FILTER (WHERE state in ('pending','ready','progress')) AS total
        """

        for field in fields.values():
            select_ += field

        from_ = """
                ssi_jobs j
                      left join maintenance_equipment me on (me.id=j.equipment_id)
                      left join mrp_workorder wo on (j.id=wo.ssi_job_id)
                      left join mrp_workcenter wc on (wo.workcenter_id=wc.id)
                    %s
        """ % from_clause

        groupby_ = """
            j.id,
            j.name,
            date,
            j.partner_id,
            rating,
            rating_unit,
            urgency,
            deadline,
            stage_id %s
        """ % (groupby)

        return "%s (SELECT %s FROM %s WHERE wo.workcenter_id IN (1,2,3,4,6,7,8,9,15) GROUP BY %s)" % (with_, select_, from_, groupby_)

    @api.model_cr
    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
