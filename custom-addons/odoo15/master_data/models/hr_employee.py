from odoo import models, fields,api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    business_unit_ids = fields.Many2many('business.unit',
        'employee_business_unit_rel',
        'employee_id',
        'business_unit_id',
        string='Business Units')



class ResUsers(models.Model):
    _inherit = 'res.users'

    business_unit_ids = fields.Many2many(
        'business.unit',
        'user_business_unit_rel',
        'user_id',
        'business_unit_id',
        string='Business Units'
    )