# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class JobCostStructure(models.AbstractModel):
    _name = 'report.ssi_jobs.job_cost_structure'
    _description = 'Job Cost Structure Report'

    @api.multi
    def get_lines(self, jobs):
        ProductProduct = self.env['product.product']
        StockMove = self.env['stock.move']
        res = []
        lines = []
        
        # Revenue Compnennt
        sales = self.env['sale.order'].search([('ssi_job_id', 'in', jobs.ids), ('state', '!=', 'cancel')])
        so = []
        so = []
        for sale in sales:
            revenue = []
            cost = []
            for line in sale.order_line:
                if line.product_id:
                    revenue.append([line.product_id, line.name, line.product_uom_qty, line.price_unit, line.discount, line.price_subtotal])
                if line.purchase_price:
                    query_str = """SELECT sm.product_id, SUM(sm.product_qty), MAX(sm.price_unit)
                                    FROM stock_move AS sm
                                    LEFT JOIN mrp_bom AS mb on sm.product_id = mb.product_id
                                    LEFT JOIN product_product AS pp on sm.product_id = pp.id
                                    LEFT JOIN product_template AS pt on pp.product_tmpl_id = pt.id
                                    WHERE sale_line_id = %s AND state != 'cancel' AND mb.product_id IS NULL
                                     AND pt.type != 'consu'
                                    GROUP BY sm.product_id"""
                    self.env.cr.execute(query_str, (line.id, ))
                    for product_id, qty, pur_price in self.env.cr.fetchall():
                        if pur_price != 0 and pur_price:
                            cost.append([line.product_id, line.name, qty, pur_price*-1, pur_price*qty*-1])
            so.append({
                'sale': sale,
                'revenue': revenue,
                'cost': cost
            })
#         for product in sales.mapped('product_id'):
#             mos = productions.filtered(lambda m: m.product_id == product)
#             total_cost = 0.0

#             #get the cost of operations
#             operations = []
#             Workorders = self.env['mrp.workorder'].search([('production_id', 'in', mos.ids)])
#             if Workorders:
#                 query_str = """SELECT w.operation_id, op.name, partner.name, sum(t.duration), wc.costs_hour, 
#                                 w.labor_cost, w.burden_cost, w.total_cost
#                                 FROM mrp_workcenter_productivity t
#                                 LEFT JOIN mrp_workorder w ON (w.id = t.workorder_id)
#                                 LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id )
#                                 LEFT JOIN res_users u ON (t.user_id = u.id)
#                                 LEFT JOIN res_partner partner ON (u.partner_id = partner.id)
#                                 LEFT JOIN mrp_routing_workcenter op ON (w.operation_id = op.id)
#                                 WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
#                                 GROUP BY w.operation_id, op.name, partner.name, t.user_id, wc.costs_hour,
#                                 w.labor_cost, w.burden_cost, w.total_cost
#                                 ORDER BY op.name, partner.name
#                             """
#                 self.env.cr.execute(query_str, (tuple(Workorders.ids), ))
#                 for op_id, op_name, user, duration, cost_hour, labor, burden, total_cst in self.env.cr.fetchall():
#                     operations.append([user, op_id, op_name, duration / 60.0, cost_hour, labor, burden, total_cst])

#             #get the cost of raw material effectively used
#             raw_material_moves = []
#             query_str = """SELECT product_id, bom_line_id, SUM(product_qty), abs(SUM(price_unit * product_qty))
#                             FROM stock_move WHERE raw_material_production_id in %s AND state != 'cancel'
#                             GROUP BY bom_line_id, product_id"""
#             self.env.cr.execute(query_str, (tuple(mos.ids), ))
#             for product_id, bom_line_id, qty, cost in self.env.cr.fetchall():
#                 raw_material_moves.append({
#                     'qty': qty,
#                     'cost': cost,
#                     'product_id': ProductProduct.browse(product_id),
#                     'bom_line_id': bom_line_id
#                 })
#                 total_cost += cost

        # Cost Compnent        
        productions = self.env['mrp.production'].search([('ssi_job_id', 'in', jobs.ids)])
        for product in productions.mapped('product_id'):
            mos = productions.filtered(lambda m: m.product_id == product)
            total_cost = 0.0

            #get the cost of operations
            operations = []
            Workorders = self.env['mrp.workorder'].search([('production_id', 'in', mos.ids)])
            if Workorders:
                query_str = """SELECT w.operation_id, op.name, sum(t.duration), wc.costs_hour, 
                                w.labor_cost, w.burden_cost, w.total_cost, w.duration_expected
                                FROM mrp_workcenter_productivity t
                                LEFT JOIN mrp_workorder w ON (w.id = t.workorder_id)
                                LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id )
                                LEFT JOIN res_users u ON (t.user_id = u.id)
                                LEFT JOIN res_partner partner ON (u.partner_id = partner.id)
                                LEFT JOIN mrp_routing_workcenter op ON (w.operation_id = op.id)
                                WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
                                GROUP BY w.operation_id, op.name, wc.costs_hour,
                                w.labor_cost, w.burden_cost, w.total_cost, w.duration_expected
                                ORDER BY op.name
                            """
                self.env.cr.execute(query_str, (tuple(Workorders.ids), ))
                user =''
                for op_id, op_name, duration, cost_hour, labor, burden, total_cst, expected in self.env.cr.fetchall():
                    operations.append([user, op_id, op_name, duration / 60.0, cost_hour, labor, burden, total_cst, expected / 60.0])

            #get the cost of raw material effectively used
            raw_material_moves = []
            query_str = """SELECT product_id, bom_line_id, SUM(product_qty), abs(SUM(price_unit * product_qty))
                            FROM stock_move WHERE raw_material_production_id in %s AND state != 'cancel'
                            GROUP BY bom_line_id, product_id"""
            self.env.cr.execute(query_str, (tuple(mos.ids), ))
            for product_id, bom_line_id, qty, cost in self.env.cr.fetchall():
                raw_material_moves.append({
                    'qty': qty,
                    'cost': cost,
                    'product_id': ProductProduct.browse(product_id),
                    'bom_line_id': bom_line_id
                })
                total_cost += cost

            #get the cost of scrapped materials
            scraps = StockMove.search([('production_id', 'in', mos.ids), ('scrapped', '=', True), ('state', '=', 'done')])
            uom = mos and mos[0].product_uom_id
            mo_qty = 0
            if not all(m.product_uom_id.id == uom.id for m in mos):
                uom = product.uom_id
                for m in mos:
                    qty = sum(m.move_finished_ids.filtered(lambda mo: mo.state != 'cancel' and mo.product_id == product).mapped('product_qty'))
                    if m.product_uom_id.id == uom.id:
                        mo_qty += qty
                    else:
                        mo_qty += m.product_uom_id._compute_quantity(qty, uom)
            else:
                for m in mos:
                    mo_qty += sum(m.move_finished_ids.filtered(lambda mo: mo.state != 'cancel' and mo.product_id == product).mapped('product_qty'))
            for m in mos:
                sub_product_moves = m.move_finished_ids.filtered(lambda mo: mo.state != 'cancel' and mo.product_id != product)
            lines.append({
                'product': product,
                'mo_qty': mo_qty,
                'mo_uom': uom,
                'operations': operations,
                'currency': self.env.user.company_id.currency_id,
                'raw_material_moves': raw_material_moves,
                'total_cost': total_cost,
                'scraps': scraps,
                'mocount': len(mos),
                'sub_product_moves': sub_product_moves
            })
        res.append({
            'lines': lines,
            'orders': so,
        })
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        jobs = self.env['ssi_jobs']\
            .browse(docids)
#             .filtered(lambda p: p.status != 'blocked')
        res = None
#         if all([jobs.status == 'done' for job in jobs]):
        res = self.get_lines(jobs)
#         raise UserError (_(res))
        return {'rows': res}

