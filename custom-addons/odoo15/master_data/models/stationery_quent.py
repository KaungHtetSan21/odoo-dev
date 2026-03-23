from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    office_issued_qty = fields.Float(
        string="Issued Qty",
        compute="_compute_office_quant_stock",
        store=False
    )

    office_remaining_qty = fields.Float(
        string="Available Qty",
        compute="_compute_office_quant_stock",
        store=False
    )

    def _compute_office_quant_stock(self):
        IssueLine = self.env['internal.issue.request.line']

        for quant in self:
            issued_qty = sum(
                IssueLine.search([
                    ('product_id', '=', quant.product_id.id),
                    ('request_id.state', '=', 'approved'),
                    ('request_id.office_location_id', '=', quant.location_id.id),
                ]).mapped('issue_qty')
            )

            quant.office_issued_qty = issued_qty
            quant.office_remaining_qty = max(quant.quantity - issued_qty, 0)
            