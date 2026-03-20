from odoo import http
from odoo.http import request
from ..user_jwt_request import jwt_request
from .. import user_jwt_util

import logging
_logger = logging.getLogger(__name__)

class JwtRPCController(http.Controller):

    # Endpoint to generate access token
    @http.route('/api/v1/login', type='json', auth='public', csrf=False, cors='*', methods=['POST'])
    def login(self,**kw):
        
        #Checking correct parameters for Group API User login
        arg_keys= kw.keys()
        if  (not 'api_key' in arg_keys) or (not 'password' in arg_keys):
            return {
                "success": False,
                "message": "Invalid Parameters.",
                "data": ""
            }
        api_key_validation=request.env['group.details'].search([('group_api_key','=',kw['api_key'])])
        api_email = api_key_validation.group_email
        api_password = api_key_validation.group_api_user_password
        if not api_key_validation:
            return {
                "success": False,
                "message": "Invalid API Key",
                "data": ""
            }
        
        if kw["password"] != api_password:
            return {
                "success": False,
                "message": "Invalid Password",
                "data": ""
            }
        
        token = jwt_request.login(api_email, api_password)
        return self._response_auth(token)
      
    # Endpoint to generate refresh token 
    @http.route('/api/v1/refresh', type='json', auth='public', csrf=False, cors='*', methods=['POST'])
    def refresh_token(self, **kw):
        method, body, headers, token = jwt_request.parse_request()
        refresh_token = jwt_request.validate_refresh_token(token) 
        if refresh_token!=True:
            return {
                "success": False,
                "message": "Invalid Refresh Token",
                "data":""
            }

        payload = user_jwt_util.decode_refresh_token(token)
        new_access_token = jwt_request.create_new_access_token(payload)
        return self._response_auth_refresh_token(new_access_token)

    # Endpoint to Create group inside Group User model
    @http.route('/api/v1/create-group', type='json' , auth='public', csrf=False, cors='*', methods=['POST'])
    def createGroup(self, **rec):
        if request.jsonrequest:
            group_data = {
                'group_name': rec['group_name'],
                'group_email': rec['group_email'],
                'group_phone': rec['group_phone'],
                'group_api_user_password': rec['group_api_user_password']
                #'responsible_id':users.name
            }     
            new_group = request.env['group.details'].sudo().create(group_data)
            args = {'status':200, 'message':'success','New Group':new_group}
            return args
        
    # Endpoint to fetch group details from Group User model
    @http.route('/api/v1/get-group', type='json', auth='public', csrf=False, cors='*', methods=['GET'])
    def getGroup(self):
        groups_rec = request.env['group.details'].search([])
        group = []
        for rec in groups_rec:
            vals = {
                'Group Name':rec.group_name,
                'Group Email':rec.group_email,
                'Group Phone':rec.group_phone,
                'Group API Key':rec.group_api_key,
                'Group API User Password':rec.group_api_user_password
            }
            group.append(vals)
        data = {'status':200, 'response':group ,'message':'success'}
        return data
                     
    def _response_auth(self, token: str):
        return jwt_request.response({
            "access_token": token[0],
            "refresh_token": token[1],
        })

    def _response_auth_refresh_token(self, new_access_token: str):
        return jwt_request.response({
            "new_access_token": new_access_token,
        })
