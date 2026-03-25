from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    business_unit_id = fields.Many2one(
        'business.unit',
        string='Business Unit',
        domain=lambda self: [('id', 'in', self.env.user.business_unit_ids.ids)],
        help="Select Business Unit first",
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        domain="[('business_unit_id', '=', business_unit_id)]"
    )

    @api.onchange('business_unit_id')
    def _onchange_business_unit_id(self):
        self.department_id = False
        if self.business_unit_id:
            return {
                'domain': {
                    'department_id': [('business_unit_id', '=', self.business_unit_id.id)]
                }
            }
        return {'domain': {'department_id': []}}


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    business_unit_ids = fields.Many2many(
        'business.unit',
        'user_business_unit_rel',
        'user_id',
        'business_unit_id',
        string='Business Units'
    )