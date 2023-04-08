from openerp.report import report_sxw
from openerp.osv import osv
from openerp.report.report_sxw import rml_parse
import random
import time
import re
import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from openerp.tools.float_utils import float_round
from openerp import models, fields

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'expense_line': self._hr_expense_line,
            'expense_line_sum': self._hr_expense_line_sum,
            'expense_summary': self._hr_expense_summary
        })
        self.context = context
        
    def _hr_expense_line(self, form):
        data = []
        result = {}
        line_obj = self.pool.get('hr.expense.line')
        line_obj_details = line_obj.search(self.cr, self.uid, [('date_value','>=',form['date_from']),('date_value','<=',form['date_to']),('expense_id.state','in',('confirm','accepted','done','paid'))])
        
        for line in line_obj.browse(self.cr, self.uid, line_obj_details).sorted(key=lambda r:r.date_value):
            result = {
                'line_date': line.date_value,
                'name': line.name,
                'ref': line.ref,
                'unit_amount': line.unit_amount
            }
            data.append(result)
        return data
        
    def _hr_expense_line_sum(self, form):
        total = 0.0
        
        self.cr.execute("SELECT SUM(unit_amount) FROM hr_expense_line h left join hr_expense_expense hr on hr.id = h.expense_id WHERE hr.state in ('confirm','accepted','done','paid') AND h.date_value >= %s AND h.date_value <= %s", (form['date_from'],form['date_to']))
        res = self.cr.fetchone()
        
        total = res and res[0] or 0.0
        
        return total
        
    def _hr_expense_summary(self, form):  
        data = []      
        self.cr.execute("SELECT p.name_template, sum(unit_amount), h.product_id FROM hr_expense_line h left join product_product p on p.id = h.product_id left join hr_expense_expense hr on hr.id = h.expense_id WHERE hr.state in ('confirm','accepted','done','paid') AND h.date_value >= %s AND h.date_value <= %s GROUP BY h.product_id, p.name_template", (form['date_from'],form['date_to']))
        res = self.cr.fetchall()
        
        data = res or []
        
        return data

class report_hr_expense_report(osv.AbstractModel):
    _name = 'report.hr_expense_usability_smabirm.expense_report'
    _inherit = 'report.abstract_report'
    _template = 'hr_expense_usability_smabirm.expense_report'
    _wrapped_report_class = Parser