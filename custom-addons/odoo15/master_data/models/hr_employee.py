from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Department ကနေ Business Unit ကို ဆက်ခံယူမယ်
    business_unit_id = fields.Many2one(
        'business.unit',
        string='Business Unit',
        related='department_id.business_unit_id',
        readonly=True,
        store=False
    )
    
    # လိုချင်ရင် business unit name ကို ပြဖို့
    business_unit_name = fields.Char(
        string='Business Unit Name',
        related='department_id.business_unit_id.name',
        readonly=True
    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    # User အတွက်လည်း employee ကနေ ဆက်ခံယူမယ်
    business_unit_id = fields.Many2one(
        'business.unit',
        string='Business Unit',
        related='employee_id.department_id.business_unit_id',
        readonly=True,
        store=False
    )