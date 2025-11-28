{
    'name': "POS Session Balance",

    'summary': """ Point of Sale Session Balance """,
    'description': """ Point of Sale Session Balance """,

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
        'views/pos_session.xml',
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "adevx_pos_session_balance/static/src/**/*"
        ]
    },

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
