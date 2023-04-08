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



from openerp import models, fields, api


class pos_order(models.Model):
    _inherit = "pos.order"
    
    total_paid = fields.Float(compute='_get_total_paid',store=True, string='Amount paid')
    
    def _get_total_paid(self):
        total_paid = 0.0
        for order in self:
            for payment in order.statement_ids:
                total_paid +=  payment.amount
        return total_paid
        

class pos_order_report(models.Model):
    _inherit = "report.pos.order"
    