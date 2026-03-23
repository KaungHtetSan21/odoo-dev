from odoo import fields, models, api


class Product(models.Model):
    _inherit = 'product.template'
    stationery_brand = fields.Char(string='Brand',
        help='Brand name for stationery products', tracking=True, copy=True)
    is_stationery_product = fields.Boolean(
        string='Created from Stationery Module',
        default=False)


    @api.model
    def create(self, vals):
        if vals.get('is_stationery_product') and not vals.get('categ_id'):
            vals['categ_id'] = self.env.ref('stationery.product_category_stationery').id
        return super().create(vals)
