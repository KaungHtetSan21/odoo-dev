from odoo import models, fields, api
import logging

class StockMove(models.Model):
    _inherit = 'stock.move'

    transfer_qty = fields.Float(string='Transfer Qty')
    line_remark = fields.Char(string='Remark')
    is_stationery_transfer = fields.Boolean(default=False)

    # product dropdown အတွက် required field
    product_uom_category_id = fields.Many2one(
        'uom.category', related='product_id.uom_id.category_id', store=True, readonly=True
    )
    
    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
        readonly=True,
        store=False  # Keep store=False since it's computed
    )

    @api.depends('product_id', 'location_id', 'picking_id.state')
    def _compute_available_qty(self):
        for move in self:
            if move.product_id and move.location_id:
                # Get all quants for this product at this location
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', move.product_id.id),
                    ('location_id', '=', move.location_id.id)
                ])
                
                # Calculate available quantity
                total_quantity = sum(quants.mapped('quantity'))
                total_reserved = sum(quants.mapped('reserved_quantity'))
                move.available_qty = total_quantity - total_reserved
                
                # Debug - Find what's reserving
                if total_reserved > 0:
                    # Find moves that are reserving this product
                    reserved_moves = self.env['stock.move'].search([
                        ('product_id', '=', move.product_id.id),
                        ('state', 'in', ['assigned', 'partially_available']),
                        ('reservation_date', '!=', False)
                    ])
                    
                    # Use logger instead of print for production
                    _logger = logging.getLogger(__name__)
                    _logger.info("=== RESERVED QUANTITY DETAILS ===")
                    _logger.info(f"Product: {move.product_id.name}")
                    _logger.info(f"Location: {move.location_id.name}")
                    _logger.info(f"Total Reserved: {total_reserved}")
                    _logger.info("Reserved by:")
                    
                    for rm in reserved_moves:
                        if rm.picking_id:
                            _logger.info(f"  - Picking: {rm.picking_id.name}")
                            _logger.info(f"    State: {rm.picking_id.state}")
                            _logger.info(f"    Origin: {rm.picking_id.origin}")
                            _logger.info(f"    Reserved Qty: {rm.reserved_availability}")
                    _logger.info("================================")
                
                # Optional: Also print to console for development
                # print(f"Move ID: {move.id}")
                # print(f"Product: {move.product_id.name}")
                # print(f"Location: {move.location_id.name}")
                # print(f"Total Quantity: {total_quantity}")
                # print(f"Total Reserved: {total_reserved}")
                # print(f"Available: {move.available_qty}")
                # print("---")
            else:
                move.available_qty = 0.0