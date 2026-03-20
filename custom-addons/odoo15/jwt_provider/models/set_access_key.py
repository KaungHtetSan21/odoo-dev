from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class KeyConfig(models.Model):
    _name = 'key.config'
    _description = 'Set Key Configuration'

    access_key=fields.Char(string = 'Access Key')
    refresh_key=fields.Char(string = 'Refresh Key')

    @api.model
    def create(self, vals):
        limit = len(self.search([]))
        if(limit >= 1):
            raise ValidationError("You Cannot Add More Than One record")
        else:
            return super(KeyConfig, self).create(vals)
