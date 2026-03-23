from odoo import models, api

class ReportStockQuantity(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    # We use *args and **kwargs to capture all possible inputs 
    # passed by the Odoo system (like product_variant_ids)
    def _get_report_data(self, *args, **kwargs):
        res = super()._get_report_data(*args, **kwargs)
        # Your custom logic can go here if needed
        return res