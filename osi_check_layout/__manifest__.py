# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'OSI Check Layout',
    'version': '12.0.1.0.0',
    'author': 'Open Source Integrators',
    'license': 'AGPL-3',
    'category': 'Localization',
    'summary': 'Change check layout',
    'description': """
This module prints checks on pre-printed or plain paper using top, middle or
bottom format. Configure the layout in the company settings, and manage the
numbering in journal settings.

Supported formats
-----------------
Check on top, check on middle or check on bottom
    """,
    'website': 'http://www.opensourceintegrators.com',
    'depends' : [
        'l10n_us_check_printing',
    ],
    'data': [
        'data/osi_us_check_printing.xml',
        'report/osi_print_check.xml',
        'report/osi_print_check_top.xml',
        'report/osi_print_check_middle.xml',
        'report/osi_print_check_bottom.xml',
        'views/osi_res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
