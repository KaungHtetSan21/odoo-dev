from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import hashlib

import logging
_logger = logging.getLogger(__name__)


class GroupDetails(models.Model):
    _name = 'group.details'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Group Details'
    _rec_name = "group_name"

    _sql_constraints = [
        ('group_email_uniq', 'UNIQUE (group_email)', 'Group User Email is already exist. Please use another Group User Email.'),
        ('group_api_key_uniq', 'UNIQUE (group_api_key)','Group API Key already Exist, Please provide another API Key.')
    ]
    
    #Group User Information
    group_name = fields.Char(string="group Name : ", required=True)
    group_email = fields.Char(string="Group User Email : ", required=True)
    group_phone = fields.Char(string="Phone Number : ", required=False)
    group_api_key= fields.Char(string="Group API Key : ", readonly=True)
    group_api_user_password = fields.Char(string="Group API User Password : ", required=True)
    related_user = fields.Many2one('res.users', string="Group API User",readonly=True)

    #Group Address
    street = fields.Char(string="Street : ")
    street2 = fields.Char(string="Street2 : ")
    country_id = fields.Many2one('res.country', string='Country', help='Select Country', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", string='State', help='Enter State', ondelete='restrict')
    city = fields.Char('City', help='Enter City')
    zip = fields.Char("Zip")


    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}
        else:
            return {'domain': {'state_id': []}}

    @api.model
    def create(self, vals):
        unique_sep = 'Group Connector'
        key_string = vals['group_email'] + unique_sep + vals['group_api_user_password']
        key = hashlib.md5(key_string.encode("utf-8")).hexdigest()
        result = super(GroupDetails, self).create(vals)
        if key:
            result.group_api_key = key
        result['related_user'] = self.env['res.users'].create({'name': result['group_name'],
                                                               'login': result['group_email'],
                                                               'password': result['group_api_user_password']
                                                              })
        return result
     
    # Validate Group E-mail
    @api.onchange('group_email')
    def validate_group_email(self):
        if self.group_email:
            match = re.match(
                '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', self.group_email)
            if match == None:
                raise ValidationError('Not a valid E-mail ID')
       
    # Validate API User password. 
    # This password validation takes atleast 1 Uppercase, 1 Lowercase, 1 Digit, 1 Special Character.
    # If You don't need comment it out.                   
    @api.onchange('group_api_user_password')
    def validate_password(self):
        if self.group_api_user_password:
            match = re.match(
                '^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,20}$', self.group_api_user_password)
            if match == None:
                raise ValidationError('Entered password should be * One Uppercase Letter * One Lowercase Letter * One Special Character * One digit * Length Should be 8-20')
