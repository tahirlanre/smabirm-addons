import time
from openerp.osv import osv
from openerp.report import report_sxw

class pos_debtors(report_sxw.rml_parse):
    
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
                    'total': (pol.price_unit - pol.discount) * pol.qty, 
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
                    
    def _credit_sales(self, pid):
        self._pos_sales_d_details(pid)
        paid = self._get_order_payment(pid)
        sales = self.order_total
        #discount = self._get_order_discount(pid)
        credit_sales = False
        
        if sales > paid:
            credit_sales = True
            return credit_sales
        return credit_sales
    
    def _get_order_payment(self, pid):
        self.amount_paid = 0.0
        #statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        #user_ids = form['user_ids'] or self._get_all_users()
        #company_id = self.pool['res.users'].browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('name','=',pid['ref'])])
        order = pos_order_obj.browse(self.cr, self.uid, pos_ids)
        return order.amount_paid or 0.0
    
    def _get_order_total(self):
        return self.order_total or 0.0
    
    def _ellipsis(self, orig_str, maxlen=100, ellipsis='...'):
        maxlen = maxlen - len(ellipsis)
        if maxlen <= 0:
            maxlen = 1
        new_str = orig_str[:maxlen]
        return new_str

    def _strip_name(self, name, maxlen=50):
        return self._ellipsis(name, maxlen, ' ...')

    
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
            'pos_sales_details':self._pos_sales_details,
            'getamountpaid': self._get_order_payment,
            'getordertotal': self._get_order_total,
            'pos_sales_d_details':self._pos_sales_d_details,
            'creditsales':self._credit_sales,
            'paymentinfo': self._pos_customer_payment,
        })



class report_pos_debtors(osv.AbstractModel):
    _name = 'report.ta_pos_enhanced.report_debtorsreport'
    _inherit = 'report.abstract_report'
    _template = 'ta_pos_enhanced.report_debtorsreport'
    _wrapped_report_class = pos_debtors