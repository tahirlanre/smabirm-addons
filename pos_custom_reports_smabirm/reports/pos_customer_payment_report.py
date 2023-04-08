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
from openerp import tools
from openerp import models, fields


class report_pos_customer_payment(models.Model):
    _name = "report.pos.customer.payment"
    _auto = False
    
    date = fields.Date(string='Payment Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", readonly=True)
    amount = fields.Float(string="Payment Amount")
    journal_id = fields.Many2one('account.journal',string="Payment Method")
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute(
            """CREATE or REPLACE VIEW %s as (
                (select a.id,
                       a.date as date,
                       a.partner_id as partner_id,
                       a.amount as amount,
                       a.journal_id as journal_id
                from account_bank_statement_line as a 
                join pos_order s on s.id = a.pos_statement_id) 
                union all
                (select pos.id,
                        pos.payment_date as date,
                        pos.partner_id as partner_id,
                        pos.amount as amount,
                        pos.journal_id as journal_id
                from pos_customer_payment as pos       
                )
            )"""
            % (self._table)
        )