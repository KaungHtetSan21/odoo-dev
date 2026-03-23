from odoo import models, fields, api

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    stock_location_id = fields.Many2one('stock.location', string="Department Stock Location")

    
    def action_create_stock_location(self):
        """Create stock location for department if not exists"""
        for dept in self:
            if not dept.stock_location_id:
                location = self.env['stock.location'].create({
                    'name': f"{dept.name} Stock",
                    'usage': 'internal',
                    'location_id': self.env.ref('stock.stock_location_stock').id,
                })
                dept.stock_location_id = location.id
        return True
