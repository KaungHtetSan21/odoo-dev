from odoo import models, fields, api

class BusinessUnit(models.Model):
    _name = 'business.unit'
    _description = 'Business Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'business_code' 


    name = fields.Char(string='Business Name', required=True)
    business_code = fields.Char(string='Business Code', required=True)
    business_type = fields.Selection([
        ('bu', 'BU'),
        ('br', 'BR'),
        ('div', 'DIV'),
    ], tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True)
    
    bu_br_div_loc = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    holding_business_id = fields.Many2one(
        'stock.warehouse',
        string="Holding Business",
        required=True
    )
