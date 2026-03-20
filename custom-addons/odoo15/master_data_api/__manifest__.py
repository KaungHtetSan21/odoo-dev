{
    'name': 'Master Data Api',
    'version': '1.0',
    'summary': 'Manage Business Units Api',
    'description': 'Custom module for Business Unit management Api',
    'author': 'Your Name',
    'depends': ['base', 'mail', 'stock', 'master_data' ],  # IMPORTANT
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/business_unit_views.xml',
        # 'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}