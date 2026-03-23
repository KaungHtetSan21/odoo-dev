from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    office_issued_qty = fields.Float(
        string="Issued Qty",
        compute="_compute_office_stock",
        store=False
    )

    office_remaining_qty = fields.Float(
        string="Remaining Qty",
        compute="_compute_office_stock",
        store=False
    )

    internal_issue_line_ids = fields.One2many(
        'internal.issue.request.line',
        'product_id',
        string="Issue Lines"
    )

    @api.depends('internal_issue_line_ids.issue_qty', 'internal_issue_line_ids.request_id.state')
    def _compute_office_stock(self):
        for product in self:
            # Only sum approved issue lines
            issued_qty = sum(
                line.issue_qty
                for line in product.internal_issue_line_ids
                if line.request_id.state == 'approved'
            )

            # Remaining = qty_available (On Hand) - issued
            product.office_issued_qty = issued_qty
            product.office_remaining_qty = product.qty_available - issued_qty
            
    # Button Methods
    def action_open_office_issued(self):
        self.ensure_one()

        issue_requests = self.env['internal.issue.request.line'].search([
            ('product_id', '=', self.id),
            ('request_id.state', '=', 'approved')
        ]).mapped('request_id')

        return {
            'name': f'Internal Issues - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'internal.issue.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', issue_requests.ids)],
            'target': 'current',
        }


    def action_open_office_remaining(self):
        self.ensure_one()
        # Open issued lines but maybe filtered differently if needed
        return {
            'name': 'Remaining Qty',
            'type': 'ir.actions.act_window',
            'res_model': 'internal.issue.request.line',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id), ('request_id.state', '=', 'approved')],
        }
 