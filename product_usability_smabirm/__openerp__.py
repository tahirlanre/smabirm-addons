# -*- encoding: utf-8 -*-
##############################################################################
#
#    Product Usability module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
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
    'name': 'Product Usability for SNL',
    'version': '1.0',
    'category': 'Product',
    'license': 'AGPL-3',
    'summary': 'Small usability enhancements to the product module',
    'description': """
Product Usability
=================

The usability enhancements include:
* sets the default Inventory Valuation to Real Time(automated)
* sets the default Product Type to Stockable Product
    """,
    'author': 'Tahir Aduragba',
    'depends': ['product'],
    'data': [
        ],
    'installable': True,
}
