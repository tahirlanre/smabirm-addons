import time
from openerp.osv import osv
from openerp.report import report_sxw

class pos_debtors(report_sxw.rml_parse):
    
    def _get_invoice(self, inv_id):
        res={}
        if inv_id:
            self.cr.execute("select number from account_invoice as ac where id = %s", (inv_id,))
            res = self.cr.fetchone()
            return res[0] or 'Draft'
        else:
            return  ''

    def _get_all_users(self):
        user_obj = self.pool.get('res.users')
        return user_obj.search(self.cr, self.uid, [])

    

    def _get_qty_total_2(self):
        return self.qty

    def _get_sales_total_2(self):
        return self.total

    def _get_sum_invoice_2(self, form):
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('company_id','=',company_id),('invoice_id','<>',False)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            for pol in pos.lines:
                self.total_invoiced += (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))
        return self.total_invoiced or False

    

    def _get_sum_dis_2(self):
        return self.discount or 0.0

    def _get_sum_discount(self, form):
        #code for the sum of discount value
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('company_id','=',company_id)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            for pol in pos.lines:
                self.total_discount += ((pol.price_unit * pol.qty) * (pol.discount / 100))
        return self.total_discount or False

    def _pos_sales_d_details(self, pid):
        self.order_total = 0.0
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        
        data = []
        result = {}
        
        pos_orderlines = pos_obj.search(self.cr, self.uid, [('name','=',pid['ref'])])
        for pos in pos_obj.browse(self.cr, self.uid, pos_orderlines):
            for pol in pos.lines:
                result = {
                    'code': pol.product_id.default_code,
                    'name': pol.product_id.name,
					'id': pos.pos_reference,
                    'invoice_id': pos.invoice_id.id, 
                    'price_unit': pol.price_unit, 
                    'qty': pol.qty, 
                    'discount': pol.discount, 
                    'total': (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)), 
                    'date_order': pos.date_order, 
                    'pos_name': pos.name, 
                    'uom': pol.product_id.uom_id.name,
                }
                self.order_total += result['total']
                data.append(result)
                self.total += result['total']
                self.qty += result['qty']
                self.discount += result['discount']
        if data:
            return data
        else:
            return {}
	
	#Tahir
    def _pos_sales_details(self, form):
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        data = []
        result = {}
        #user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['done','paid','invoiced']),('company_id','=',company_id)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            #for pol in pos.lines:
            result = {
                #'code': pol.product_id.default_code,
                #'name': pol.product_id.name,
                'ref': pos.name,
				'id': pos.pos_reference,
				'order_id': pos.name,
                'partner_name': pos.partner_id.name,
                #'invoice_id': pos.invoice_id.id, 
                #'price_unit': pol.price_unit, 
                #'qty': pol.qty, 
                #'discount': pol.discount, 
                #'total': (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)), 
                'date_order': pos.date_order, 
                'pos_name': pos.name, 
				'lines': pos.lines,
                #'uom': pol.product_id.uom_id.name,
				
            }
            data.append(result)
            
        if data:
            return data
        else:
            return {}
                    
    def _get_discount_payment(self, pid):
        #self.discount_paid = 0.0
        statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('name','=',pid['ref'])])
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id:
                    a_l.append(r['id'])
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id and aj.name = 'Discount Journal' and absl.id IN %s " \
                                "group by aj.name ",(tuple(a_l),))

                data = self.cr.dictfetchall()
                for a in data:
					self.discount_paid+=a['sum']
                    #self.total_paid+=a['sum']
                return "Tahir"
        else:
            return "No discount"
    
    def _credit_sales(self, pid):
        self._pos_sales_d_details(pid)
        paid = self._get_order_payment(pid)
        sales = self.order_total
        discount = self._get_order_discount(pid)
        credit_sales = False
        
        if sales > (discount+paid):
            credit_sales = True
            return credit_sales
        return credit_sales

    def _credit_payment(self, pid):
        self._pos_sales_d_details(pid)
        paid = self._get_order_payment(pid)
        sales = self.order_total or 0.0
        discount = self._get_order_discount(pid)
        #credit_sales = discount+paid
        
        if paid > sales:
            #credit_sales = 0
            return True
        return False
    
    def _get_order_payment(self, pid):
        self.amount_paid = 0.0
        statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        #user_ids = form['user_ids'] or self._get_all_users()
        #company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('name','=',pid['ref'])])
        self._get_discount_payment(pid);
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id:
                    a_l.append(r['id'])
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id and aj.name != 'Discount Journal' and absl.id IN %s " \
                                "group by aj.name ",(tuple(a_l),))

                data = self.cr.dictfetchall()
                for a in data:
					self.amount_paid+=a['sum']
                    #self.total_paid+=a['sum']
                return self.amount_paid or 0.0
        else:
            return self.amount_paid or 0.0
    
    def _get_order_discount(self, pid):
        self.discount_amount = 0.0
        
        statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        #user_ids = form['user_ids'] or self._get_all_users()
        #company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('name','=',pid['ref'])])
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id:
                    a_l.append(r['id'])
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id and aj.name = 'Discount Journal' and absl.id IN %s " \
                                "group by aj.name ",(tuple(a_l),))

                data = self.cr.dictfetchall()
                for a in data:
					self.discount_amount+=a['sum']
                #self.discount_paid+=a['sum']
                return self.discount_amount or 0.0
        else:
            return self.discount_amount or 0.0
            
    def _get_order_total(self):
        return self.order_total or 0.0
    
    def _paid_total_2(self):
        return self.total_paid or 0.0
    
    def _discount_total(self):
        return self.discount_paid or 0.0
    
    def _get_payments(self, form):
        statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','in',user_ids), ('company_id', '=', company_id)])
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id:
                    a_l.append(r['id'])
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id  and aj.name != 'Discount Journal' and absl.id IN %s " \
                                "group by aj.name ",(tuple(a_l),))

                data = self.cr.dictfetchall()
                for a in data:
					self.total_paid+=a['sum']
                    #self.total_paid+=a['sum']
                    
               
                
                return data
        else:
            return {}
        statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','in',user_ids), ('company_id', '=', company_id)])
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id:
                    a_l.append(r['id'])
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id IN %s " \
                                "group by aj.name ",(tuple(a_l),))

                data = self.cr.dictfetchall()
                return data
        else:
            return {}

    def _total_of_the_day(self, objects):
        return self.total or 0.00

    def _sum_invoice(self, objects):
        return reduce(lambda acc, obj:
                        acc + obj.invoice_id.amount_total,
                        [o for o in objects if o.invoice_id and o.invoice_id.number],
                        0.0)

    def _ellipsis(self, orig_str, maxlen=100, ellipsis='...'):
        maxlen = maxlen - len(ellipsis)
        if maxlen <= 0:
            maxlen = 1
        new_str = orig_str[:maxlen]
        return new_str

    def _strip_name(self, name, maxlen=50):
        return self._ellipsis(name, maxlen, ' ...')

    def _get_tax_amount(self, form):
        taxes = {}
        account_tax_obj = self.pool.get('account.tax')
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order_obj = self.pool.get('pos.order')
        company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','in',user_ids), ('company_id', '=', company_id)])
        for order in pos_order_obj.browse(self.cr, self.uid, pos_ids):
            for line in order.lines:
                line_taxes = account_tax_obj.compute_all(self.cr, self.uid, line.product_id.taxes_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                for tax in line_taxes['taxes']:
                    taxes.setdefault(tax['id'], {'name': tax['name'], 'amount':0.0})
                    taxes[tax['id']]['amount'] += tax['amount']
        return taxes.values()
    
    def _pos_customer_payment(self, form):
        pos_payment_obj = self.pool.get('pos.customer.payment')
        data = []
        result = {}
        pay_ids = pos_payment_obj.search(self.cr, self.uid, [('payment_date', '>=', form['date_start']), ('payment_date','<=', form['date_end'])])
        for pay in pos_payment_obj.browse(self.cr,self.uid, pay_ids):
            result = {
                'date': pay.payment_date,
                'partner': pay.partner_id.name,
                'amount': pay.amount,
            }
            data.append(result)
        if data:
            return data
        else:
            return {}
    
    def _get_user_names(self, user_ids):
        user_obj = self.pool.get('res.users')
        return ', '.join(map(lambda x: x.name, user_obj.browse(self.cr, self.uid, user_ids)))

    def __init__(self, cr, uid, name, context):
        super(pos_debtors, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.order_total = 0.0     #Tahir
        self.total_paid = 0.0
        self.discount_paid = 0.0
        
        self.qty = 0.0
        self.total_invoiced = 0.0
        self.discount = 0.0
        self.total_discount = 0.0
        self.localcontext.update({
            'time': time,
            'strip_name': self._strip_name,
            'getpayments': self._get_payments,
            'getsumdisc': self._get_sum_discount,
            'gettotaloftheday': self._total_of_the_day,
            'gettaxamount': self._get_tax_amount,
            'pos_sales_details':self._pos_sales_details,
            'getqtytotal2': self._get_qty_total_2,
            'getsalestotal2': self._get_sales_total_2,
            'getsuminvoice2':self._get_sum_invoice_2,
            'getpaidtotal2': self._paid_total_2,
            'getinvoice':self._get_invoice,
            'get_user_names': self._get_user_names,
            'getamountpaid': self._get_order_payment,
            'getordertotal': self._get_order_total,
            'getdiscountpayment': self._get_discount_payment,
            'totaldiscount': self._discount_total,
            'getdiscountamount': self._get_order_discount,
            'pos_sales_d_details':self._pos_sales_d_details,
            'creditsales':self._credit_sales,
            'creditpayment':self._credit_payment,
            'paymentinfo': self._pos_customer_payment,
        })



class report_pos_debtors(osv.AbstractModel):
    _name = 'report.ta_pos_enhanced.report_debtorsreport'
    _inherit = 'report.abstract_report'
    _template = 'ta_pos_enhanced.report_debtorsreport'
    _wrapped_report_class = pos_debtors