{
    'name': "POS Z Report",

    'summary': """ Point of Sale Z Report """,
    'description': """ Point of Sale Z Report """,

    'category': 'Sales/Point of Sale',
    'author': 'Adevx',
    'license': "OPL-1",
    'website': 'https://adevx.com',
    "price": 0,
    "currency": 'USD',

    'depends': ['point_of_sale'],
    'data': [
        # Views
        'views/pos_config.xml',
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "adevx_pos_z_report/static/src/**/*"
        ]
    },

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
