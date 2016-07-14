# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Enhanced POS for Smabirm',
    'version': '1.1',
    'category': 'Point Of Sale',
    'sequence': 6,
    'summary': '',
    'description': """
        - Silent receipt printing
        - POS credit sales
        - Immediate POS sales posting
        - Custom POS Details of Sales Report
        - Debtors Report
        - Credit limit in POS sales
        
    """,
    'author': 'Tahir Aduragba',
   
    'depends': ['point_of_sale'],
    
    'installable': True,
    
    'data': ['views.xml',
    'template.xml',
    'view/report_detailsofsales.xml',
    'wizard/debtors_report.xml',
    'view/report_debtorsreport.xml',
    'pos_order_sequence.xml'],
    
    'qweb': ['static/src/xml/pos.xml'],
 
    'auto_install': False,
}