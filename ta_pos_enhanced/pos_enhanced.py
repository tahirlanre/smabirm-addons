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

import logging
from openerp import models, fields, api, exceptions
from openerp.osv import osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
from openerp import netsvc, tools

import openerp.addons.decimal_precision as dp
import openerp.addons.product.product
import time

_logger = logging.getLogger(__name__)
            
            
class account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"        
    #tahir
    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit  - line.discount),
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return tax_grouped            

            
class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    #tahir
    def _compute_price(self):
        price = self.price_unit - self.discount
        taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)
    
    #tahir
    @api.model
    def _default_price_unit(self):
        if not self._context.get('check_total'):
            return 0
        total = self._context['check_total']
        for l in self._context.get('invoice_line', []):
            if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                vals = l[2]
                price = vals.get('price_unit', 0)  - vals.get('discount', 0)
                total = total - (price * vals.get('quantity'))
                taxes = vals.get('invoice_line_tax_id')
                if taxes and len(taxes[0]) >= 3 and taxes[0][2]:
                    taxes = self.env['account.tax'].browse(taxes[0][2])
                    tax_res = taxes.compute_all(price, vals.get('quantity'),
                        product=vals.get('product_id'), partner=self._context.get('partner_id'))
                    for tax in tax_res['taxes']:
                        total = total - tax['amount']
        return total            
    

    #tahir
    @api.model
    def move_line_get(self, invoice_id):
        inv = self.env['account.invoice'].browse(invoice_id)
        currency = inv.currency_id.with_context(date=inv.date_invoice)
        company_currency = inv.company_id.currency_id

        res = []
        for line in inv.invoice_line:
            mres = self.move_line_get_item(line)
            mres['invl_id'] = line.id
            res.append(mres)
            tax_code_found = False
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit - line.discount),
                line.quantity, line.product_id, inv.partner_id)['taxes']
            for tax in taxes:
                if inv.type in ('out_invoice', 'in_invoice'):
                    tax_code_id = tax['base_code_id']
                    tax_amount = line.price_subtotal * tax['base_sign']
                else:
                    tax_code_id = tax['ref_base_code_id']
                    tax_amount = line.price_subtotal * tax['ref_base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(dict(mres))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = currency.compute(tax_amount, company_currency)

        return res
            
class pos_customer_payment(models.Model):
    _name = 'pos.customer.payment'
    _order = 'id desc'
        
    @api.one
    def unlink(self):
        raise exceptions.Warning('Cannot delete customer payment(s)!')
        return True
    
    #def create(self, test, context = context)
    
    journal_id = fields.Many2one('account.journal', 'Payment Mode')
    amount = fields.Float('Amount')
    payment_name = fields.Char('Payment Reference')
    payment_date = fields.Date('Payment Date')
    partner_id = fields.Many2one('res.partner', 'Customer')
    

    
class pos_config(models.Model):
    _inherit = 'pos.config'
    
    default_user = fields.Many2one('res.users', string = 'Default User')
    max_discount = fields.Float('Maximum Discount')
    discount_restriction = fields.Boolean('Discount Restriction')


class pos_session(osv.osv):
    _inherit = 'pos.session'
    
    def wkf_action_close(self, cr, uid, ids, context=None):
        # Close CashBox
        """
        for record in self.browse(cr, uid, ids, context=context):
            for st in record.statement_ids:
                if abs(st.difference) > st.journal_id.amount_authorized_diff:
                    # The pos manager can close statements with maximums.
                    if not self.pool.get('ir.model.access').check_groups(cr, uid, "point_of_sale.group_pos_manager"):
                        raise osv.except_osv( _('Error!'),
                            _("Your ending balance is too different from the theoretical cash closing (%.2f), the maximum allowed is: %.2f. You can contact your manager to force it.") % (st.difference, st.journal_id.amount_authorized_diff))
                if (st.journal_id.type not in ['bank', 'cash']):
                    raise osv.except_osv(_('Error!'), 
                        _("The type of the journal for your payment method should be bank or cash "))
                getattr(st, 'button_confirm_%s' % st.journal_id.type)(context=context)
        self._confirm_orders(cr, uid, ids, context=context)
        """
        self.write(cr, uid, ids, {'state' : 'closed'}, context=context)

        obj = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'point_of_sale', 'menu_point_root')[1]
        return {
            'type' : 'ir.actions.client',
            'name' : 'Point of Sale Menu',
            'tag' : 'reload',
            'params' : {'menu_id': obj},
        }
    
    
      
class point_of_sale(models.Model):
    _name ='pos.payment'
    

class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.one
    @api.depends('debit', 'credit')
    def _get_balance(self):
        for partner in self:
            partner.balance = self.credit - self.debit
    
    credit_limit_restriction = fields.Boolean("Credit Limit Restriction?")
    balance = fields.Float(
        compute='_get_balance',
        string='Balance', readonly=True,
        digits=dp.get_precision('Account'))
        

class pos_make_payment(osv.osv_memory):
    _inherit = 'pos.make.payment'

    def check(self, cr, uid, ids, context=None):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        context = context or {}
        order_obj = self.pool.get('pos.order')
        active_id = context and context.get('active_id', False)

        order = order_obj.browse(cr, uid, active_id, context=context)


        amount = order.amount_total - order.amount_paid
        data = self.read(cr, uid, ids, context=context)[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = data['journal_id'][0]
        #o = order_obj.browse(cr,uid, [active_id], context=context)


        if data['amount'] != 0.0:                   #if amount is 0, don't add payment
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            order_obj.signal_workflow(cr, uid, [active_id], 'paid')

            #Tahir
            order_obj._create_account_move_line(cr, uid, active_id)
            for st_line in order.statement_ids:
                vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name
                    }
                self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
            #order_obj.create_picking(cr, uid, [active_id], context=context)
            return {'type' : 'ir.actions.act_window_close' }

        return self.launch_payment(cr, uid, ids, context=context)

        
class point_of_sale(models.Model):
    _inherit = 'pos.order'

    def check_connection(self, cr, uid, context=None):
        return True
    
    def get_default_warehouse(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', company_id)], context=context)
        if not warehouse_ids:
            return False
        return warehouse_ids[0]

    def get_payment_term(self, cr, uid, context=None):
        payment_term_id = self.pool.get('account.payment.term').search(cr, uid, [('name', '=', 'Layby')], context=context)
        if payment_term_id:
            return payment_term_id[0]
        return False

    def get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user\'s company!'))
        return company_id
    
    def get_account_id(self, cr, uid, journal, partner_id, context=None):
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')

        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            if not journal.default_credit_account_id or not journal.default_debit_account_id:
                raise osv.except_osv(_('Error!'), _('Please define default credit/debit accounts on the journal "%s".') % (journal.name))
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
        return account_id
    
    def _account_voucher_fields(self, cr, uid, payment_info, journal_id, amount, context=None):
        journal_pool = self.pool.get('account.journal')
        invoice_obj = self.pool.get('account.invoice')
        voucher_obj = self.pool.get('account.voucher')
        journal = journal_pool.browse(cr, uid, int(journal_id), context=context)
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        company_id = self.get_default_company(cr, uid, context=context)
        partner_id = payment_info['partner_id']
        date = time.strftime('%Y-%m-%d')
        inv = invoice_obj.browse(cr, uid, payment_info['id'], context=context)
        ttype = inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
        vals = voucher_obj.onchange_amount(cr, uid, [], amount, 1.0, partner_id, journal.id, currency_id, ttype, date, currency_id, company_id, context=context)
        res = voucher_obj.onchange_journal(cr, uid, [], journal.id, None, None, partner_id, date, amount, ttype, company_id, context=context)
        for key in res.keys():
                vals[key].update(res[key])
        vals['value']['journal_id'] = journal_id
        return vals

    def payment_invoice_via_pos(self, cr, uid, payment_info, journal_id, amount, context=None):
        if context is None:
            ctx = {}
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')

        inv = self.pool.get('account.invoice').browse(cr, uid, payment_info['id'], context=context)
        ctx= {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                'default_amount': amount,
                'default_reference': inv.name,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        if amount != 0:
            vals = self._account_voucher_fields(cr, uid, payment_info, journal_id, amount, context=ctx)
            del vals['value']['line_cr_ids']
            del vals['value']['line_dr_ids']

            voucher_id = voucher_obj.create(cr, uid, vals['value'], context=ctx)
            res = self._account_voucher_fields(cr, uid, payment_info, journal_id, amount, context=ctx)
            print res
            if res['value']['line_cr_ids']:
                for line in res['value']['line_cr_ids']:
                    line['voucher_id'] = voucher_id
                    voucher_line_obj.create(cr, uid, line, context=ctx)
            if res['value']['line_dr_ids']:
                for line in res['value']['line_dr_ids']:
                    line['voucher_id'] = voucher_id
                    voucher_line_obj.create(cr, uid, line, context=ctx)

            voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher')
            return True
        else:
            return False   

    def create_from_ui(self, cr, uid, orders, context=None):

        #TODO if payment is 0, then no need to add payment
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        existing_order_ids = self.search(cr, uid, [('pos_reference', 'in', submitted_references)], context=context)
        existing_orders = self.read(cr, uid, existing_order_ids, ['pos_reference'], context=context)
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]

        order_ids = []

        for tmp_order in orders_to_save:
            to_invoice = tmp_order['to_invoice']
            order = tmp_order['data']
            order_id = self._process_order(cr, uid, order, context=context)
            order_ids.append(order_id)

            try:
                self.signal_workflow(cr, uid, [order_id], 'paid')
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
                return []

            order_obj = self.browse(cr, uid, order_id, context)

            #Tahir
            try:
                self._create_account_move_line(cr, uid, order_id)
                for st_line in order_obj.statement_ids:
                    vals = {
                            'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                            'credit': st_line.amount > 0 and st_line.amount or 0.0,
                            'account_id': st_line.account_id.id,
                            'name': st_line.name
                        }
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
            except Exception as e:
                _logger.error('Smabirm Error: %s', tools.ustr(e))
                return []

            if to_invoice:
                self.action_invoice(cr, uid, [order_id], context)
                #order_obj = self.browse(cr, uid, order_id, context)
                self.pool['account.invoice'].signal_workflow(cr, uid, [order_obj.invoice_id.id], 'invoice_open')

        return order_ids
    
    def _process_order(self, cr, uid, order, context=None):

        order_id = self.create(cr, uid, self._order_fields(cr, uid, order, context=context),context)

        for payments in order['statement_ids']:
            amount = payments[2]['amount']
            if amount != 0:
                self.add_payment(cr, uid, order_id, self._payment_fields(cr, uid, payments[2], context=context), context=context)

        session = self.pool.get('pos.session').browse(cr, uid, order['pos_session_id'], context=context)
        if session.sequence_number <= order['sequence_number']:
            session.write({'sequence_number': order['sequence_number'] + 1})
            session.refresh()

        if not float_is_zero(order['amount_return'], self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')):
            cash_journal = session.cash_journal_id
            if not cash_journal:
                cash_journal_ids = filter(lambda st: st.journal_id.name=='Cash', session.statement_ids)
                if not len(cash_journal_ids):
                    raise osv.except_osv( _('error!'),
                        _("No cash statement found for this session. Unable to record returned cash."))
                
                cash_journal = cash_journal_ids[0].journal_id
            self.add_payment(cr, uid, order_id, {
                'amount': -order['amount_return'],
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_name': _('return'),
                'journal': cash_journal.id,
            }, context=context)
        return order_id
    
    
    def customer_payment_via_pos(self, cr, uid, partner_id, journal_id, amount, context=None):
        if context is None:
            ctx = {}
        journal_pool = self.pool.get('account.journal')
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')
        journal = journal_pool.browse(cr, uid, int(journal_id), context=context)
        pos_payment = self.pool.get('pos.customer.payment')
        
        #inv = self.pool.get('account.invoice').browse(cr, uid, payment_info['id'], context=context)
        res_partner = self.pool.get('res.partner').browse(cr,uid,partner_id,context=context)
        
        try:
            ctx= {
                    #'payment_expected_currency': inv.currency_id.id,
                    'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(res_partner).id,
                    'default_amount': amount,
                    #'default_reference': inv.name,
                    #'close_after_process': True,
                    #'invoice_type': inv.type,
                    #'invoice_id': inv.id,
                    #'default_type': 'receipt',
                    'type': 'receipt',
                }
        except Exception as e:
                _logger.error('Wahala dey small: %s', tools.ustr(e)) 
                
        
        if amount != 0:
            try:
                vals = self._account_voucher_fields_1(cr, uid, partner_id, journal_id, amount, context=ctx)
                del vals['value']['line_cr_ids']
                del vals['value']['line_dr_ids']
            except Exception as e:
                _logger.error('which kind wahala sef 1: %s', tools.ustr(e))
            
            try:
                voucher_id = voucher_obj.create(cr, uid, vals['value'], context=ctx)
                res = self._account_voucher_fields_1(cr, uid, partner_id, journal_id, amount, context=context)
    
                voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher')
                 
                test= {
                        'amount': amount,
                        'journal_id' : journal_id,
                        #'payment_name' : 'CP: ',
                        'payment_date': time.strftime('%Y-%m-%d'),
                        'partner_id': self.pool.get('res.partner')._find_accounting_partner(res_partner).id,
                    }
                  
                payment = pos_payment.create(cr, uid, test, context = context)
                pos_p = pos_payment.browse(cr, uid, payment, context=context)
                
                return pos_p.id
            except Exception as e:
                _logger.error('which kind wahala sef 2: %s', tools.ustr(e))
        else:
            return    
    
    
    def customer_payment_return(self, cr, uid, partner_id, journal_id, amount, context=None):
        if context is None:
            ctx = {}
        journal_pool = self.pool.get('account.journal')
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')
        journal = journal_pool.browse(cr, uid, int(journal_id), context=context)
        pos_payment = self.pool.get('pos.customer.payment')
        
        #inv = self.pool.get('account.invoice').browse(cr, uid, payment_info['id'], context=context)
        res_partner = self.pool.get('res.partner').browse(cr,uid,partner_id,context=context)
        
        try:
            ctx= {
                    #'payment_expected_currency': inv.currency_id.id,
                    'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(res_partner).id,
                    'default_amount': amount,
                    #'default_reference': inv.name,
                    #'close_after_process': True,
                    #'invoice_type': inv.type,
                    #'invoice_id': inv.id,
                    #'default_type': 'receipt',
                    'type': 'receipt',
                }
        except Exception as e:
                _logger.error('Wahala dey small: %s', tools.ustr(e)) 
                
        
        if amount != 0:
            try:
                vals = self._account_voucher_fields_1(cr, uid, partner_id, journal_id, amount, context=ctx)
                del vals['value']['line_cr_ids']
                del vals['value']['line_dr_ids']
            except Exception as e:
                _logger.error('which kind wahala sef 1: %s', tools.ustr(e))
            
            try:
                voucher_id = voucher_obj.create(cr, uid, vals['value'], context=ctx)
                res = self._account_voucher_fields_1(cr, uid, partner_id, journal_id, amount, context=context)
                print res
                if res['value']['line_cr_ids']:
                    for line in res['value']['line_cr_ids']:
                        line['voucher_id'] = voucher_id
                        voucher_line_obj.create(cr, uid, line, context=ctx)
                if res['value']['line_dr_ids']:
                    for line in res['value']['line_dr_ids']:
                        line['voucher_id'] = voucher_id
                        voucher_line_obj.create(cr, uid, line, context=ctx)

                voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher')
                
                test= {
                        'amount': amount,
                        'journal_id' : journal_id,
                        #'payment_name' : 'CP: ',
                        'payment_date': time.strftime('%Y-%m-%d'),
                        'partner_id': self.pool.get('res.partner')._find_accounting_partner(res_partner).id,
                    }
                   
                payment = pos_payment.create(cr, uid, test, context = context)

                return True
            except Exception as e:
                _logger.error('which kind wahala sef 2: %s', tools.ustr(e))
        else:
            return False
    
    
    def _account_voucher_fields_1(self, cr, uid, customer_id, journal_id, amount, context=None):
        try:
            journal_pool = self.pool.get('account.journal')
            invoice_obj = self.pool.get('account.invoice')
            voucher_obj = self.pool.get('account.voucher')

            journal = journal_pool.browse(cr, uid, int(journal_id), context=context)
            periods = self.pool.get('account.period').find(cr, uid, context=context)
            account_id = self.get_account_id(cr,uid,journal,customer_id,context=context)
            currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
            company_id = self.get_default_company(cr, uid, context=context)
            print customer_id
            partner_id = customer_id
            date = time.strftime('%Y-%m-%d')
            #inv = invoice_obj.browse(cr, uid, payment_info['id'], context=context)
            ttype = 'receipt'
            vals = voucher_obj.onchange_amount(cr, uid, [], amount, 1.0, partner_id, journal.id, currency_id, ttype, date, currency_id, company_id, context=context)
            res = voucher_obj.onchange_journal(cr, uid, [], journal.id, None, None, partner_id, date, amount, ttype, company_id, context=context)
            for key in res.keys():
                    vals[key].update(res[key])
            vals['value']['journal_id'] = journal_id
            vals['value']['account_id'] = account_id
            #vals['value']['partner_id']= partner_id
        except Exception as e:
                _logger.error('wahala dey for this side: %s', tools.ustr(e))
        return vals
    
    def test_paid(self, cr, uid, ids, context=None):
        return True

    def _create_account_move_line(self, cr, uid, ids, session=None, move_id=None, context=None):
        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        account_move_obj = self.pool.get('account.move')
        account_period_obj = self.pool.get('account.period')
        account_tax_obj = self.pool.get('account.tax')
        property_obj = self.pool.get('ir.property')
        cur_obj = self.pool.get('res.currency')

        #session_ids = set(order.session_id for order in self.browse(cr, uid, ids, context=context))

        if session and not all(session.id == order.session_id.id for order in self.browse(cr, uid, ids, context=context)):
            raise osv.except_osv(_('Error!'), _('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False

        def compute_tax(amount, tax, line):
            if amount > 0:
                tax_code_id = tax['base_code_id']
                tax_amount = line.price_subtotal * tax['base_sign']
            else:
                tax_code_id = tax['ref_base_code_id']
                tax_amount = -line.price_subtotal * tax['ref_base_sign']

            return (tax_code_id, tax_amount,)

        for order in self.browse(cr, uid, ids, context=context):
            if order.account_move:
                continue
            if order.state != 'paid':
                continue

            current_company = order.sale_journal.company_id

            group_tax = {}
            account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context)

            order_account = order.partner_id and \
                            order.partner_id.property_account_receivable and \
                            order.partner_id.property_account_receivable.id or \
                            account_def and account_def.id

            if move_id is None:
                # Create an entry for the sale
                move_id = self._create_account_move(cr, uid, order.session_id.start_at, order.name, order.sale_journal.id, order.company_id.id, context=context)

            move = account_move_obj.browse(cr, uid, move_id, context=context)

            def insert_data(data_type, values):
                # if have_to_group_by:

                sale_journal_id = order.sale_journal.id

                # 'quantity': line.qty,
                # 'product_id': line.product_id.id,
                values.update({
                    'date': order.date_order[:10],
                    'ref': order.name,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False,
                    'journal_id' : sale_journal_id,
                    'period_id': move.period_id.id,
                    'move_id' : move_id,
                    'company_id': current_company.id,
                })

                if data_type == 'product':
                    key = ('product', values['partner_id'], values['product_id'], values['analytic_account_id'], values['debit'] > 0)
                elif data_type == 'tax':
                    key = ('tax', values['partner_id'], values['tax_code_id'], values['debit'] > 0)
                elif data_type == 'counter_part':
                    key = ('counter_part', values['partner_id'], values['account_id'], values['debit'] > 0)
                else:
                    return

                grouped_data.setdefault(key, [])

                # if not have_to_group_by or (not grouped_data[key]):
                #     grouped_data[key].append(values)
                # else:
                #     pass

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        for line in grouped_data[key]:
                            if line.get('tax_code_id') == values.get('tax_code_id'):
                                current_value = line
                                current_value['quantity'] = current_value.get('quantity', 0.0) +  values.get('quantity', 0.0)
                                current_value['credit'] = current_value.get('credit', 0.0) + values.get('credit', 0.0)
                                current_value['debit'] = current_value.get('debit', 0.0) + values.get('debit', 0.0)
                                current_value['tax_amount'] = current_value.get('tax_amount', 0.0) + values.get('tax_amount', 0.0)
                                break
                        else:
                            grouped_data[key].append(values)
                else:
                    grouped_data[key].append(values)

            #because of the weird way the pos order is written, we need to make sure there is at least one line,
            #because just after the 'for' loop there are references to 'line' and 'income_account' variables (that
            #are set inside the for loop)
            #TOFIX: a deep refactoring of this method (and class!) is needed in order to get rid of this stupid hack
            assert order.lines, _('The POS order must have lines when calling this method')
            # Create an move for each order line

            cur = order.pricelist_id.currency_id
            for line in order.lines:
                tax_amount = 0
                taxes = []
                for t in line.product_id.taxes_id:
                    if t.company_id.id == current_company.id:
                        taxes.append(t)
                computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, line.price_unit * (100.0-line.discount) / 100.0, line.qty)['taxes']

                for tax in computed_taxes:
                    tax_amount += cur_obj.round(cr, uid, cur, tax['amount'])
                    if tax_amount < 0:
                        group_key = (tax['ref_tax_code_id'], tax['base_code_id'], tax['account_collected_id'], tax['id'])
                    else:
                        group_key = (tax['tax_code_id'], tax['base_code_id'], tax['account_collected_id'], tax['id'])

                    group_tax.setdefault(group_key, 0)
                    group_tax[group_key] += cur_obj.round(cr, uid, cur, tax['amount'])

                amount = line.price_subtotal

                # Search for the income account
                if  line.product_id.property_account_income.id:
                    income_account = line.product_id.property_account_income.id
                elif line.product_id.categ_id.property_account_income_categ.id:
                    income_account = line.product_id.categ_id.property_account_income_categ.id
                else:
                    raise osv.except_osv(_('Error!'), _('Please define income '\
                        'account for this product: "%s" (id:%d).') \
                        % (line.product_id.name, line.product_id.id, ))

                # Empty the tax list as long as there is no tax code:
                tax_code_id = False
                tax_amount = 0
                while computed_taxes:
                    tax = computed_taxes.pop(0)
                    tax_code_id, tax_amount = compute_tax(amount, tax, line)

                    # If there is one we stop
                    if tax_code_id:
                        break

                # Create a move for the line
                insert_data('product', {
                    'name': line.product_id.name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(cr, uid, line, context=context),
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'tax_code_id': tax_code_id,
                    'tax_amount': tax_amount,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                })

                # For each remaining tax with a code, whe create a move line
                for tax in computed_taxes:
                    tax_code_id, tax_amount = compute_tax(amount, tax, line)
                    if not tax_code_id:
                        continue

                    insert_data('tax', {
                        'name': _('Tax'),
                        'product_id':line.product_id.id,
                        'quantity': line.qty,
                        'account_id': income_account,
                        'credit': 0.0,
                        'debit': 0.0,
                        'tax_code_id': tax_code_id,
                        'tax_amount': tax_amount,
                        'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                    })

            # Create a move for each tax group
            (tax_code_pos, base_code_pos, account_pos, tax_id)= (0, 1, 2, 3)

            for key, tax_amount in group_tax.items():
                tax = self.pool.get('account.tax').browse(cr, uid, key[tax_id], context=context)
                insert_data('tax', {
                    'name': _('Tax') + ' ' + tax.name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': key[account_pos] or income_account,
                    'credit': ((tax_amount>0) and tax_amount) or 0.0,
                    'debit': ((tax_amount<0) and -tax_amount) or 0.0,
                    'tax_code_id': key[tax_code_pos],
                    'tax_amount': abs(tax_amount),
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                })

            # counterpart
            insert_data('counter_part', {
                'name': _("Trade Receivables"), #order.name,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total) or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total) or 0.0,
                'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
            })

            order.write({'state':'done', 'account_move': move_id})

        all_lines = []
        for group_key, group_data in grouped_data.iteritems():
            for value in group_data:
                all_lines.append((0, 0, value),)
        if move_id: #In case no order was changed
            self.pool.get("account.move").write(cr, uid, [move_id], {'line_id':all_lines}, context=context)
            self.pool.get('account.move').post(cr, uid, [move_id], context=context) #Tahir

        return True