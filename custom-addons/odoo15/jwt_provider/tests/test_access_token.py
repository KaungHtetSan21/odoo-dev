from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install')
class TestArtisanAccessToken(TransactionCase):
    def setUp(self):
        super(TestArtisanAccessToken, self).setUp()
        self.task = self.env['jwt_provider.access_token']
        self.user = self.env['res.users']

        self.create_task=self.task.create({
            'token' : 'tehfgrvhdufndjcrknfcijfyrufjdniehcfbvecnefjsjj',
            'user_id' : 2,
            'expires' : '2021-12-21 17:01:06',
            'is_expired' : ''
        })

    def test_create(self):
        self.assertTrue(bool(self.task.search([('id', '=', self.create_task.id)], limit=1)))

        self.assertEqual(self.create_task.token, 'tehfgrvhdufndjcrknfcijfyrufjdniehcfbvecnefjsjj')
        self.assertEqual(str(self.create_task.expires), str('2021-12-21 17:01:06'))
        self.assertEqual(bool(self.create_task.is_expired), bool('True'))
        

    def test_get_user(self):
        self.assertTrue(bool(self.user.search([('id', '=', self.create_task.user_id.id)], limit=1)))