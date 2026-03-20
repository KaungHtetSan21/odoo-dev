import datetime
import traceback
from odoo import http
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from . import user_jwt_util

import logging
_logger = logging.getLogger(__name__)

class JwtRequest:

    def parse_request(self):
        # This can only be called inside controller method.
        # Parse and store request info { method, body, headers, token }
        method = str(request.httprequest.method).lower()
        try:
            body = http.request.params
        except Exception:
            body = {}
        headers = dict(list(request.httprequest.headers.items()))
        token = ''
        # checking headers
        if 'wsgi.input' in headers:
            del headers['wsgi.input']
        if 'wsgi.errors' in headers:
            del headers['wsgi.errors']
        if 'HTTP_AUTHORIZATION' in headers:
            headers['Authorization'] = headers['HTTP_AUTHORIZATION']
        if 'Authorization' in headers:
            try:
                # Bearer token_string
                token = headers['Authorization'].split(' ')[1]
            except Exception:
                pass
        self.method = method
        self.headers = headers
        self.body = body
        self.token = token
        return method, body, headers, token

    def is_rpc(self):
        return 'application/json' in request.httprequest._parsed_content_type

    def is_ok_response(self, status=200):
        return status >= 200 and status < 300

    def rpc_response(self, data={}, status=200):
        # Response json rpc request (with controller type='json')
        r = {
            'success': True if self.is_ok_response(status) else False,
            'code': status,
        }
        if not self.is_ok_response(status):
            return { **r, **data }
        return { **r, 'data': data }

    def response(self, data={}, status=200):
        # Create a response to rpc request
        if self.is_rpc():
            return self.rpc_response(data, status)

    def login(self, login, password, with_token=True):
        # Try logging user by using login & password.
        state = self.get_state()
        uid = request.session.authenticate(state['d'], login, password)
        if not uid:
            return False
        if with_token:
            return self.create_token(request.env.user)
        return True

    def get_state(self):
        # get database state
        return {
            'd': request.session.db
        }

    def create_token(self, user):
            # Create a token based on user model.
        try:
            exp = datetime.datetime.utcnow() + datetime.timedelta(days=2)
            payload = {
                'exp': exp,
                'iat': datetime.datetime.utcnow(),
                'sub': user.id,
                'lgn': user.login,
            }
            refresh_token = self.create_refresh_token(request.env.user)
            token = user_jwt_util.sign_token(payload)
            self.save_token(token, user.id, exp)
            return token, refresh_token

        except Exception as ex:
            _logger.error(traceback.format_exc())
            raise

    def create_new_access_token(self, payload):
          # Create a new token using the refresh token.
        try:
            get_user_id = payload['sub']
            get_user_lgn = payload['lgn']
            exp = datetime.datetime.utcnow() + datetime.timedelta(days=2)
            payload = {
                'exp': exp,
                'iat': datetime.datetime.utcnow(),
                'sub': get_user_id,
                'lgn': get_user_lgn,
            }
            token = user_jwt_util.sign_token(payload)
            self.save_token(token, get_user_id, exp)
            return token

        except Exception as ex:
            _logger.error(traceback.format_exc())
            raise
    
    def save_token(self, token, uid, exp):
            # Save access token to database
        res = request.env['group.details'].sudo().search([('related_user','=',uid)]).id
        request.env['jwt_provider.access_token'].sudo().create({
            'user_id': uid,
            'expires': exp.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'token': token,
        })

    def create_refresh_token(self,user):
        try:
            exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            payload = {
                'exp': exp,
                'iat': datetime.datetime.utcnow(),
                'sub': user.id,
                'lgn': user.login,
                'grant_type':"refresh",
            }
            refresh_token = user_jwt_util.sign_refresh_token(payload)
            self.save_refresh_token(refresh_token, user.id, exp)
            return refresh_token
        except Exception as ex:
            _logger.error(traceback.format_exc())
            raise

    def save_refresh_token(self, refresh_token, uid, exp):
          # Save refresh token to database
        res = request.env['group.details'].sudo().search([('related_user','=',uid)]).id
        request.env['jwt_provider.refresh_token'].sudo().create({
            'user_id': uid,
            'expires': exp.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'refresh_token': refresh_token,
        })

    def validate_refresh_token(self,token):
        # validate refresh token after getting from header
        record = request.env['jwt_provider.refresh_token'].sudo().search([('refresh_token','=',token)]).id
        if record:
            return True
        else:
            return False
    
    def verify(self, token):
       # Check if jwt token existed in db and is not expired
        record = request.env['jwt_provider.access_token'].sudo().search([
            ('token', '=', token)
        ])
        if len(record) != 1 or record.is_expired:
            return False
        return record.user_id

    def validate_access_token(self, token):
       # Validate a given jwt access token. Return True on success or return false on failure.
        if not self.verify(token):
            return False
        else:
            # decode token using access_key
            payload = user_jwt_util.decode_access_token(token)
            uid = request.session.authenticate(
                request.session.db, login=payload['lgn'], password=token)
            if not uid:
                return False

            return True

jwt_request = JwtRequest()
