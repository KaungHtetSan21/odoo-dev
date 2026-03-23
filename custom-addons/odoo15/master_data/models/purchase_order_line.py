from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    office_issued_qty = fields.Float(
        string="Issued Qty",
        compute='_compute_office_quant_fields',
        readonly=True,
        store=False
    )

    office_remaining_qty = fields.Float(
        string="Available Qty",
        compute='_compute_office_quant_fields',
        readonly=True,
        store=False
    )

    @api.depends('product_id', 'order_id.office_location_id')
    def _compute_office_quant_fields(self):
        Quant = self.env['stock.quant']
        for line in self:
            if not line.product_id or not line.order_id.office_location_id:
                line.office_issued_qty = 0
                line.office_remaining_qty = 0
                continue

            # Use the office_location_id from the Purchase Order
            location = line.order_id.office_location_id

            # Get all quants for this product and the office location
            quants = Quant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', location.id)
            ])

            # Sum issued and remaining quantities
            line.office_issued_qty = sum(quants.mapped('office_issued_qty'))
            line.office_remaining_qty = sum(quants.mapped('office_remaining_qty'))