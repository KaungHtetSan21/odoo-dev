{
    'name': "Auth Provider",

    'summary': """
        JWT Authentication For Third Party Application""",

    'description': """
        JWT Authentication For Third Party Application""",
    'sequence' : 3,
    'author': "Bibek Ranjan Jena",
    "category": "Extra Tools",
    'version': '15.0.0.1.0',
    'license': 'LGPL-3',
    'depends': ['web', 'auth_signup'],

    'external_dependencies': {
        'python': ['jwt', 'simplejson'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/group_api_user_view.xml',
        'views/group_user_view.xml',
        'views/set_access_key_view.xml'
    ],
    'assets': {
        "web.assets_backend": [
            "prepend", "jwt_provider/static/src/css/jwt_provider.css",
            "prepend", "jwt_provider/static/src/js/password_preview.js",
            "prepend", "jwt_provider/static/src/js/copy_clipboard.js",
        ]
    },
    'images': ['static/description/banner.png'],
    'demo' : [],
    'qweb' : [],
    'installable' : True,
    'application' : True,
    'auto-install' : False,
}
