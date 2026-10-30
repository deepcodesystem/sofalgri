{
    'name': "Product Unit Price py Packaging",
    'version': '18.0.6.10.2',
    'summary': """
        Manage sales and invoices with a unit price per packaging.
    """,
    'description': """
        This module extends the functionality of sales orders and customer invoices 
        to allow selecting a specific product packaging on the line.
        The unit price is then automatically calculated based on the product's base price (per Kg)
        and the quantity contained in the selected packaging.

        Ideal for businesses selling products in predefined boxes or cases (e.g., 4 Kg, 10 Kg).
    """,
    'author': "GetapPRO",
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
        'sale_stock',
        'sale_management',
        'account'
    ],
    'data': [
        'reports/report_templates.xml',
        'reports/forwarder_invoice_report.xml',
        'views/product_packaging_views.xml',
        'views/sale_account_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
