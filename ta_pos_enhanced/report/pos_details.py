from openerp import api, models, fields, SUPERUSER_ID
from openerp.osv import osv
from openerp.addons.point_of_sale.report.pos_details import pos_details

class pos_details_custom(pos_details):

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
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('state','in',['done','paid','invoiced']),('company_id','=',company_id)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            #for pol in pos.lines:
            result = {
                #'code': pol.product_id.default_code,
                #'name': pol.product_id.name,
				'id': pos.pos_reference,
                'ref': pos.name,
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
                'amount_paid': pos.amount_paid,
                'amount_total': pos.amount_total,
                #'uom': pol.product_id.uom_id.name,

            }
            self.total_paid_order += result['amount_paid']
            data.append(result)




        if data:
            return data
        else:
            return {}

    def _get_sum_discount(self, form):
        #code for the sum of discount value
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('company_id','=',company_id)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            for pol in pos.lines:
                self.total_discount += (pol.discount * pol.qty)
        return self.total_discount or False

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

    def _get_order_total(self):
        return self.order_total or 0.0

    def _get_credit_sales_total(self):
        return (self.total-self.total_paid_order) or 0.0


    def _get_order_payment(self, pid):
        self.amount_paid = 0.0
        pos_order_obj = self.pool.get("pos.order")
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('name','=',pid['ref'])])
        order = pos_order_obj.browse(self.cr, self.uid, pos_ids)
        return order.amount_paid or 0.0

    def _get_order_total(self):
        return self.order_total or 0.0

    def _paid_total_2(self):
        return self.total_paid or 0.0

    
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
                print tuple(a_l)
                self.cr.execute("select a.id, a.name, sum(sum) from (select aj.id,aj.name, sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj "\
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id and absl.id IN %s and aj.name != 'Discount Journal' "\
                                "group by aj.id, aj.name union all select aj.id , aj.name, sum(amount) from pos_customer_payment as pos, account_journal as aj where payment_date >= %s and payment_date <= %s and aj.name != 'Discount Journal' and aj.id = pos.journal_id group by aj.id, aj.name) a group by a.id, a.name",(tuple(a_l),form['date_start'],form['date_end'],))
                data = self.cr.dictfetchall()
                for a in data:
                    self.total_paid+=a['sum']
                return data
            else:
                return {}
        else:
            return {}


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
        super(pos_details_custom, self).__init__(cr, uid, name, context=context)
        self.order_total = 0.0     #Tahir
        self.total_paid = 0.0
        self.total_paid_order = 0.0
        self.discount = 0.0
        self.localcontext.update({
            'pos_sales_d_details':self._pos_sales_d_details,
            'pos_sales_details':self._pos_sales_details,
            'getamountpaid': self._get_order_payment,
            'getcreditsalestotal': self._get_credit_sales_total,
            'getordertotal': self._get_order_total,
            'getdiscountpayment': self._get_discount_payment,
            'paymentinfo': self._pos_customer_payment,
            'getsumdisc': self._get_sum_discount,
            
        })
            
class report_pos_details(osv.AbstractModel):
    #_name = 'report.point_of_sale.report_detailsofsales'
    _inherit = 'report.point_of_sale.report_detailsofsales'
    #_template = 'point_of_sale.report_detailsofsales'
    _wrapped_report_class = pos_details_custom