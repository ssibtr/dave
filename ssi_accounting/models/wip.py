# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import json
from odoo import api, models, _
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError
from odoo.addons.web.controllers.main import clean_action
from datetime import datetime, timedelta
from pytz import timezone, UTC


class ReportWip(models.AbstractModel):
    _name = "account.report.wip"
    _description = "WIP Report"
    _inherit = 'account.report'

#     filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_month'}
#     filter_unfold_all = True
#     filter_partner = True
    filter_date = {'date_from': '', 'filter': 'this_month'}
    filter_analytic = True
    filter_all_entries = False

#     def _get_super_columns(self, options):
#         if options.get('custom') == 'jeanne':
#             columns = [{'string': _('Disassembly')}]
#             columns += [{'string': _('Machine Shop')}]
#             columns += [{'string': _('Winding')}]
#             columns += [{'string': _('Assembly')}]
#             columns += [{'string': _('Field Services')}]
#             columns += [{'string': _('New Product Sales')}]
#             columns += [{'string': _('Training')}]
#             columns += [{'string': _('Storage')}]
#             columns += [{'string': _('Total')}]

#             return {'columns': columns, 'x_offset': 9, 'merge': 4}

    def _get_columns_name(self, options):
        if options.get('custom') != 'jeanne':
            return [{'name': _('Job')},
                    {'name': _('Cust #')},
                    {'name': _('Customer')},
                    {'name': _('Job Type')},
                    {'name': _('Job Stage')},
                    {'name': _('Customer Cat')},
                    {'name': _('Project Manager')},
                    {'name': _('Account Manager')},
                    {'name': _('Order')},
                    {'name': _('Invoice')},
                    {'name': _('Lab'), 'class': 'number'},
#                     {'name': _('Lab Burden'), 'class': 'number'},
                    {'name': _('Mat'), 'class': 'number'},
                    {'name': _('ACS Lab'), 'class': 'number'},
                    {'name': _('ACS Mat'), 'class': 'number'}
            ]
        else:
            return [{'name': _('Job #')},
                    {'name': _('Cust #')},
                    {'name': _('Customer Name')},
                    {'name': _('Customer PO Number')},
                    {'name': _('Job Type')},
                    {'name': _('Job Stage')},
                    {'name': _('Job Desc')},
                    {'name': _('Urgency')},
                    {'name': _('Customer Cat')},
                    {'name': _('Project Manager')},
                    {'name': _('Account Manager')},
                    {'name': _('Order')},
                    {'name': _('Confirmation Date')},
                    {'name': _('Estimate Amount')},
                    {'name': _('Invoice')},
                    {'name': _('Opened Date')},
                    {'name': _('Customer Deadline')},
                    {'name': _('Delivery Date')},
                    {'name': _('Est. Hours'), 'class': 'number'},
                    {'name': _('Actual Hours'), 'class': 'number'},
                    {'name': _('Lab'), 'class': 'number'},
#                     {'name': _('Lab Burden'), 'class': 'number'},
                    {'name': _('Mat'), 'class': 'number'},
                    {'name': _('ACS Lab'), 'class': 'number'},
                    {'name': _('ACS Mat'), 'class': 'number'},
                    {'name': _('Rating')},
                    {'name': _('Poles')},
                    {'name': _('Voltage')},
                    {'name': _('Mounting')},
                    {'name': _('Manufacturer')},
                    {'name': _('First Labor Date')},
                    {'name': _('Last Labor Date')}
            ]

    @api.model
    def _get_lines(self, options, line_id=None):
        if options.get('custom') != 'jeanne':
            return self._get_lines_regular(options, line_id)
        else:
            return self._get_lines_custom(options, line_id)

    @api.model
    def _get_lines_regular(self, options, line_id=None):
        lines = []
        tables, where_clause, where_params = self.env['account.move.line'].with_context(strict_range=True)._query_get()
#         user_type_id = self.env['account.account.type'].search([('type', '=', 'receivable')])
        if where_clause:
            where_clause = 'AND ' + where_clause
        # When unfolding, only fetch sum for the job we are unfolding and
        # fetch all partners for that country
        if line_id != None:
            if isinstance(line_id, int):
                where_clause = 'AND \"account_move_line\".analytic_account_id = %s ' + where_clause
                where_params = [line_id] + where_params
            else:
                where_clause = 'AND am.ref = %s ' + where_clause
                where_params = [line_id] + where_params

            unfold_query = """
                SELECT 
                    sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4) AS lab_debit, 
                    sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4) AS lab_credit,
                    sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 5) AS mat_debit, 
                    sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 5) AS mat_credit,
                    sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 6) AS lab_a_debit, 
                    sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 6) AS lab_a_credit,
                    sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 7) AS mat_a_debit, 
                    sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 7) AS mat_a_credit,
                    \"account_move_line\".analytic_account_id AS aa_id, MIN(\"account_move_line\".id) AS aml_id, pc.profit_center
                    FROM """+tables+"""
                    LEFT JOIN account_account ac on \"account_move_line\".account_id = ac.id
                    LEFT JOIN account_analytic_account aa on \"account_move_line\".analytic_account_id = aa.id
                    LEFT JOIN account_move am on \"account_move_line\".move_id = am.id
                    LEFT JOIN product_product pp on \"account_move_line\".product_id = pp.id
                    LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                    LEFT JOIN product_category pc on pt.categ_id = pc.id
                    WHERE ac.group_id IN (4, 5) """+where_clause+"""
                    GROUP BY aa_id, pc.profit_center ORDER BY pc.profit_center
            """


#                 sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Labor%%') AS lab_debit, 
#                 sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Labor%%') AS lab_credit,
#                 sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Burden%%') AS lab_b_debit, 
#                 sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Burden%%') AS lab_b_credit,
        sql_query = """
            SELECT sum(\"account_move_line\".balance)*-1 AS balance, 
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4) AS lab_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4) AS lab_credit,
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 5) AS mat_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 5) AS mat_credit,
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 6) AS lab_a_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 6) AS lab_a_credit,
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 7) AS mat_a_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 7) AS mat_a_credit,
                \"account_move_line\".analytic_account_id AS aa_id, 
                j.id as job_id, aa.name as job_name, j.type as job_type
                FROM """+tables+"""
                LEFT JOIN res_partner p ON \"account_move_line\".partner_id = p.id
                LEFT JOIN account_account ac on \"account_move_line\".account_id = ac.id
                LEFT JOIN account_move am on \"account_move_line\".move_id = am.id
                LEFT JOIN account_analytic_account aa on \"account_move_line\".analytic_account_id = aa.id
                LEFT JOIN ssi_jobs j on aa.ssi_job_id = j.id
                WHERE \"account_move_line\".analytic_account_id IS NOT NULL AND ac.group_id IN (4, 5, 6, 7) """+where_clause+"""
                GROUP BY \"account_move_line\".analytic_account_id, p.ref, p.id, j.id, job_name, job_type 
                ORDER BY job_name
        """

        params = where_params
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.dictfetchall()

        total_l = 0
        total_m = 0
#         total_l_b = 0
        total_l_a = 0
        total_m_a = 0
        count = 0
        line_l = 0
        line_m = 0
#         line_l_b = 0
        line_l_a = 0
        line_m_a = 0
        for k, line in enumerate(results):
            if not line.get('lab_credit'):
                line['lab_credit'] = 0 
            if not line.get('lab_debit'):
                line['lab_debit'] = 0 
#             if not line.get('lab_b_credit'):
#                 line['lab_b_credit'] = 0 
#             if not line.get('lab_b_debit'):
#                 line['lab_b_debit'] = 0 
            if not line.get('mat_credit'):
                line['mat_credit'] = 0 
            if not line.get('mat_debit'):
                line['mat_debit'] = 0 
            if not line.get('lab_a_credit'):
                line['lab_a_credit'] = 0 
            if not line.get('lab_a_debit'):
                line['lab_a_debit'] = 0 
            if not line.get('mat_a_credit'):
                line['mat_a_credit'] = 0 
            if not line.get('mat_a_debit'):
                line['mat_a_debit'] = 0 
            total_l += line.get('lab_debit') - line.get('lab_credit', 0)
            total_m += line.get('mat_debit', 0) - line.get('mat_credit', 0)
#             total_l_b += line.get('lab_b_debit') - line.get('lab_b_credit', 0)
            total_l_a += line.get('lab_a_debit') - line.get('lab_a_credit', 0)
            total_m_a += line.get('mat_a_debit', 0) - line.get('mat_a_credit', 0)
            line_l += line.get('lab_debit', 0) - line.get('lab_credit', 0)
            line_m += line.get('mat_debit', 0) - line.get('mat_credit', 0)
#             line_l_b += line.get('lab_b_debit', 0) - line.get('lab_b_credit', 0)
            line_l_a += line.get('lab_a_debit', 0) - line.get('lab_a_credit', 0)
            line_m_a += line.get('mat_a_debit', 0) - line.get('mat_a_credit', 0)
            if k+1 < len(results):
                next_job = results[k+1].get('job_name')
            else:
                next_job = ''
            if line.get('job_name') != next_job or not line.get('job_name'):
#             if True:
                ++count
                order = self.env['sale.order'].search([('analytic_account_id', '=', line.get('aa_id')), ('state', '!=', 'cancel')], limit=1)
                job = self.env['ssi_jobs'].search([('id', '=', line.get('job_id'))], limit=1)
                id = line.get('aa_id')
                if order.invoice_ids:
                    amref = order.invoice_ids[0].move_id.name
                else:
                    amref = ''
#                 browsed_partner = self.env['res.partner'].browse(line.get('partner_id'))
                partner_name = job.partner_id.parent_id.name and str(job.partner_id.parent_id.name) + ', ' + job.partner_id.name or job.partner_id.name
#                 if (round(line_l) + round(line_m) + round(line_l_a) + round(line_m_a)) != 0:
                if (line_l + line_m + line_l_a + line_m_a) != 0:
                    lines.append({
                            'id': id,
                            'name': line.get('job_name'),
                            'level': 2,
                            'unfoldable': True,
                            'unfolded': line_id == id and True or False,
                            'columns': [{'name': job.partner_id.ref}, 
                                        {'name': partner_name}, 
                                        {'name': line.get('job_type')},
                                        {'name': job.stage_id.name}, 
                                        {'name': job.customer_category}, 
                                        {'name': job.project_manager.name}, 
                                        {'name': job.user_id.name},
                                        {'name': order.name},
                                        {'name': amref},
                                        {'name': self.format_value(line_l)},
    #                                     {'name': self.format_value(line_l_b)},
                                        {'name': self.format_value(line_m)},
                                        {'name': self.format_value(line_l_a)},
                                        {'name': self.format_value(line_m_a)}
                            ],
                    })
                line_m = 0
                line_l = 0
#                 line_l_b = 0
                line_m_a = 0
                line_l_a = 0
        # Adding profit center lines
        if line_id:
            self.env.cr.execute(unfold_query, params)
            results = self.env.cr.dictfetchall()
            for child_line in results:
                if not child_line.get('lab_credit'):
                    child_line['lab_credit'] = 0 
                if not child_line.get('lab_debit'):
                    child_line['lab_debit'] = 0 
#                 if not child_line.get('lab_b_credit'):
#                     child_line['lab_b_credit'] = 0 
#                 if not child_line.get('lab_b_debit'):
#                     child_line['lab_b_debit'] = 0 
                if not child_line.get('mat_credit'):
                    child_line['mat_credit'] = 0 
                if not child_line.get('mat_debit'):
                    child_line['mat_debit'] = 0 
                if not child_line.get('lab_a_credit'):
                    child_line['lab_a_credit'] = 0 
                if not child_line.get('lab_a_debit'):
                    child_line['lab_a_debit'] = 0 
                if not child_line.get('mat_a_credit'):
                    child_line['mat_a_credit'] = 0 
                if not child_line.get('mat_a_debit'):
                    child_line['mat_a_debit'] = 0 
                lines.append({
                        'id': child_line.get('aa_id'),
                        'name': child_line.get('profit_center'),
                        'level': 4,
                        'caret_options': '',
                        'parent_id': line_id,
                        'columns': [{'name': v} for v in [
                            '', 
                            '', 
                            '', 
                            '', 
                            '', 
                            '', 
                            '', 
                            '', 
                            '', 
                            self.format_value(child_line.get('lab_debit')-child_line.get('lab_credit')), 
#                             self.format_value(child_line.get('lab_b_debit')-child_line.get('lab_b_credit')), 
                            self.format_value(child_line.get('mat_debit')-child_line.get('mat_credit')),
                            self.format_value(child_line.get('lab_a_debit')-child_line.get('lab_a_credit')),
                            self.format_value(child_line.get('mat_a_debit')-child_line.get('mat_a_credit')),
                        ]],
                    })
#             # Sum of all the partner lines
#             lines.append({
#                     'id': 'total_%s' % (line_id,),
#                     'class': 'o_account_reports_domain_total',
#                     'name': _('Total '),
#                     'parent_id': line_id,
#                     'columns': [{'name': v} for v in ['', '', '', '', '', child_line.get('total_l')]],
#                 })

        # Don't display level 0 total line in case we are unfolding
        if total_l and not line_id:
            lines.append({
                'id': 'total',
                'name': _('Total'),
                'level': 0,
                'class': 'total',
                'columns': [{'name': v} for v in [
                        '', 
                        '',
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        self.format_value(total_l), 
#                         self.format_value(total_l_b),
                        self.format_value(total_m), 
                        self.format_value(total_l_a), 
                        self.format_value(total_m_a), 
                    ]],
                })
#             raise UserError(_(lines))
        return lines

    @api.model
    def _get_lines_custom(self, options, line_id=None):
        lines = []
        tables, where_clause, where_params = self.env['account.move.line'].with_context(strict_range=True)._query_get()
#         user_type_id = self.env['account.account.type'].search([('type', '=', 'receivable')])
        if where_clause:
            where_clause = 'AND ' + where_clause
            
#                 sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Labor%%') AS lab_debit, 
#                 sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Labor%%') AS lab_credit,
#                 sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Burden%%') AS lab_b_debit, 
#                 sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4 and \"account_move_line\".ref LIKE '%%Burden%%') AS lab_b_credit,
#         date_from = options['date']['date_from']
        date_from = datetime.strptime(options['date']['date_from'], '%Y-%m-%d')
        date_to = datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
        date_to = date_to + timedelta(days=1)
#         date_to = options['date']['date_to']
        sql_query = """
            SELECT sum(\"account_move_line\".balance)*-1 AS balance, 
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 4) AS lab_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 4) AS lab_credit,
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 5) AS mat_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 5) AS mat_credit,
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 6) AS lab_a_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 6) AS lab_a_credit,
                sum(\"account_move_line\".debit) FILTER (WHERE ac.group_id = 7) AS mat_a_debit, 
                sum(\"account_move_line\".credit) FILTER (WHERE ac.group_id = 7) AS mat_a_credit,
                (SELECT coalesce(sum(duration_expected), 0) from mrp_workorder where ssi_job_id = j.id) AS exp_mins,
                (SELECT coalesce(sum(duration), 0) from mrp_workorder where ssi_job_id = j.id) AS real_mins,
                \"account_move_line\".analytic_account_id AS aa_id, 
                j.name as job_name, j.type as job_type, j.notes, j.urgency, j.equipment_id,
                j.po_number as po, j.create_date, j.deadline_date, j.completed_on, j.id as job_id FROM """+tables+"""
                LEFT JOIN account_account ac on \"account_move_line\".account_id = ac.id
                LEFT JOIN account_move am on \"account_move_line\".move_id = am.id
                LEFT JOIN account_analytic_account aa on \"account_move_line\".analytic_account_id = aa.id
                LEFT JOIN ssi_jobs j on aa.ssi_job_id = j.id
                WHERE \"account_move_line\".analytic_account_id IS NOT NULL AND ac.group_id IN (4, 5, 6, 7) """+where_clause+"""
                GROUP BY \"account_move_line\".analytic_account_id, job_name, job_type, po, j.id, j.create_date, j.deadline_date, j.completed_on, j.notes, j.urgency, j.equipment_id
                ORDER BY job_name
        """

        params = where_params
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.dictfetchall()

        total_l = 0
        total_m = 0
#         total_l_b = 0
        total_l_a = 0
        total_m_a = 0
        count = 0
        line_l = 0
        line_m = 0
#         line_l_b = 0
        line_l_a = 0
        line_m_a = 0
        for k, line in enumerate(results):
            if not line.get('lab_credit'):
                line['lab_credit'] = 0 
            if not line.get('lab_debit'):
                line['lab_debit'] = 0 
#             if not line.get('lab_b_credit'):
#                 line['lab_b_credit'] = 0 
#             if not line.get('lab_b_debit'):
#                 line['lab_b_debit'] = 0 
            if not line.get('mat_credit'):
                line['mat_credit'] = 0 
            if not line.get('mat_debit'):
                line['mat_debit'] = 0 
            if not line.get('lab_a_credit'):
                line['lab_a_credit'] = 0 
            if not line.get('lab_a_debit'):
                line['lab_a_debit'] = 0 
            if not line.get('mat_a_credit'):
                line['mat_a_credit'] = 0 
            if not line.get('mat_a_debit'):
                line['mat_a_debit'] = 0 
            total_l += line.get('lab_debit') - line.get('lab_credit', 0)
            total_m += line.get('mat_debit', 0) - line.get('mat_credit', 0)
#             total_l_b += line.get('lab_b_debit') - line.get('lab_b_credit', 0)
            total_l_a += line.get('lab_a_debit') - line.get('lab_a_credit', 0)
            total_m_a += line.get('mat_a_debit', 0) - line.get('mat_a_credit', 0)
            line_l += line.get('lab_debit', 0) - line.get('lab_credit', 0)
            line_m += line.get('mat_debit', 0) - line.get('mat_credit', 0)
#             line_l_b += line.get('lab_b_debit', 0) - line.get('lab_b_credit', 0)
            line_l_a += line.get('lab_a_debit', 0) - line.get('lab_a_credit', 0)
            line_m_a += line.get('mat_a_debit', 0) - line.get('mat_a_credit', 0)
            if k+1 < len(results):
                next_job = results[k+1].get('job_name')
            else:
                next_job = ''
#             if line.get('job_name') != next_job or not line.get('job_name'):
            if True:
                ++count
                equip = self.env['maintenance.equipment'].search([('id', '=', line.get('equipment_id'))], limit=1)
                order = self.env['sale.order'].search([('analytic_account_id', '=', line.get('aa_id')), ('state', '!=', 'cancel')], limit=1)
                job = self.env['ssi_jobs'].search([('id', '=', line.get('job_id'))], limit=1)
                # Get Delivery Date
                delivery_date = ''
                if order.picking_ids:
                    for transfer in (order.picking_ids).filtered(lambda t: t.picking_type_id.id == 2):
                        delivery_date = transfer.date_done

                # Get Labor Dates
                wos = self.env['mrp.workorder'].search([('ssi_job_id', '=', line.get('job_id'))])
                times = []
                first = datetime(2100, 1, 1)
                last = datetime(1978, 1, 1)
                for wo in wos:
                    try:
                        times = (wo.time_ids).filtered(lambda r: r.date_end).sorted(key=lambda r: r.date_end)
    #                     times = (wo.time_ids).filtered(lambda t: t.date_end <= date_to).sorted(key=lambda r: r.date_end)
                        if times:
                            if times[0].date_end <= first: 
                                first = times[0].date_end
                            if times[-1].date_end >= last:
                                last = times[-1].date_end
                    except:
                        first = datetime(2100, 1, 1)
                        last = datetime(1978, 1, 1)
                rating = ''
                if equip.rating and not equip.rating_unit:
                    rating = str(equip.rating)
                elif equip.rating and equip.rating_unit:
                    rating = str(equip.rating) + ' ' + equip.rating_unit
                id = line.get('aa_id')
                if order.invoice_ids:
                    amref = order.invoice_ids[0].move_id.name
                else:
                    amref = ''
#                 browsed_partner = self.env['res.partner'].browse(line.get('partner_id'))
                partner_name = job.partner_id.parent_id.name and str(job.partner_id.parent_id.name) + ', ' + job.partner_id.name or job.partner_id.name
                if (line_l + line_m + line_l_a + line_m_a) != 0:
                    tz = self.env.user.tz
                    p_first = ''
                    p_last = ''
                    if first != datetime(2100, 1, 1):
                        p_first = format_date(self.env, first.astimezone(timezone(tz)).date())
                    if last != datetime(1978, 1, 1):
                        p_last = format_date(self.env, last.astimezone(timezone(tz)).date())
                    lines.append({
                            'id': id,
                            'name': line.get('job_name'),
                            'level': 2,
                            'unfoldable': False,
                            'unfolded': line_id == id and True or False,
                            'columns': [{'name': job.partner_id.ref}, 
                                        {'name': partner_name}, 
                                        {'name': order.client_order_ref}, 
                                        {'name': line.get('job_type')},
                                        {'name': job.stage_id.name}, 
                                        {'name': line.get('notes')},
                                        {'name': line.get('urgency')},
                                        {'name': job.customer_category}, 
                                        {'name': job.project_manager.name}, 
                                        {'name': job.user_id.name},
                                        {'name': order.name},
                                        {'name': format_date(self.env, order.confirmation_date)},
                                        {'name': order.amount_total},
                                        {'name': amref},
                                        {'name': format_date(self.env, line.get('create_date'))},
                                        {'name': format_date(self.env, line.get('deadline_date'))},
                                        {'name': format_date(self.env, delivery_date)},
                                        {'name': round(line.get('exp_mins')/60,2)},
                                        {'name': round(line.get('real_mins')/60,2)},
                                        {'name': self.format_value(line_l)},
    #                                     {'name': self.format_value(line_l_b)},
                                        {'name': self.format_value(line_m)},
                                        {'name': self.format_value(line_l_a)},
                                        {'name': self.format_value(line_m_a)},
                                        {'name': rating},
                                        {'name': equip.poles},
                                        {'name': equip.voltage},
                                        {'name': equip.mounting},
                                        {'name': equip.manufacture},
                                        {'name': p_first},
                                        {'name': p_last}
                            ],
                    })
                line_m = 0
                line_l = 0
#                 line_l_b = 0
                line_m_a = 0
                line_l_a = 0
        if total_l and not line_id:
            lines.append({
                'id': 'total',
                'name': _('Total'),
                'level': 0,
                'class': 'total',
                'columns': [{'name': v} for v in [
                        '', 
                        '',
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        '', 
                        self.format_value(total_l), 
#                         self.format_value(total_l_b),
                        self.format_value(total_m), 
                        self.format_value(total_l_a), 
                        self.format_value(total_m_a), 
                    ]],
                })
        return lines

    def _get_report_name(self):
        return _('WIP Report')

    def _get_templates(self):
        templates = super(ReportWip, self)._get_templates()
        templates['main_template'] = 'ssi_accounting.template_wip_report'
        templates['line_template'] = 'ssi_accounting.line_template_wip_report'
        return templates

    def open_analytic_entries(self, options, params):
        aa_id = params.get('aa_id')
        action = self.env.ref('analytic.account_analytic_line_action').read()[0]
        action = clean_action(action)
        action['context'] = {
            'active_id': aa_id,
        }
        return action

    def export_xlsx(self, options):
        options['custom'] ='jeanne'
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xlsx',
                         'financial_id': self.env.context.get('id'),
                         }
        }
    
    def _get_reports_buttons(self):
        return [{'name': _('Print Preview'), 'action': 'print_pdf'}, 
                {'name': _('Export (XLSX)'), 'action': 'print_xlsx'}, 
                {'name': _('Jeanne\'s Export'), 'action': 'export_xlsx'}]

