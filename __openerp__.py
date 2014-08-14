{
    'name': 'clubit_deliveries_to_essers',
    'version': '1.0',
    'category': 'Warehouse',
    'description': "Send deliveries to Essers using the EDI framework",
    'author': 'Niels Ruelens',
    'website': 'http://clubit.be',
    'summary': 'Send deliveries to Essers using the EDI framework',
    'sequence': 9,
    'depends': [
        'stock',
        'clubit_recheck_availability',
        'clubit_delivery_extensions',
        'clubit_tools',
        'clubit_expertm',
    ],
    'data': [
        'config.xml',
        'wizard/delivery_out.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'css': [
    ],
    'images': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}