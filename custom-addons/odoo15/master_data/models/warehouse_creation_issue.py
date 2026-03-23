from odoo import models, api, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def create(self, vals):
        warehouse = super().create(vals)

        # Check if "Internal Issue" picking type exists for this warehouse
        picking_type = self.env['stock.picking.type'].search([
            ('sequence_code', '=', 'internal.issue.request'),
            ('warehouse_id', '=', warehouse.id)
        ], limit=1)

        if not picking_type:
            self.env['stock.picking.type'].create({
                'name': 'Internal Issue',
                'code': 'internal',
                'sequence_code': 'internal.issue.request',
                'warehouse_id': warehouse.id,
                'default_location_src_id': warehouse.lot_stock_id.id,
                'default_location_dest_id': warehouse.lot_stock_id.id,
                'active': True,
            })

        return warehouse