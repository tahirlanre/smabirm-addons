openerp.pos_custom_ticket_smabirm = function(instance){
    var module = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    //var _t = instance.web._t;
    var PosModelSuper = module.PosModel;
    //var round_di = instance.web.round_decimals;
	
	
    module.PosModel = module.PosModel.extend({
        
        load_server_data: function(){
            var self = this;
            var loaded = PosModelSuper.prototype.load_server_data.call(this);
			console.log('pos custom ticket for SNL')
            loaded = loaded.then(function(){
                return self.fetch(
                    'res.company',
                    ['currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id' , 'country_id', 'tax_calculation_rounding_method','logo'],
                    []
                );
            }).then(function(companies){
				self.company = companies[0];
                return $.when()
            })
            return loaded;
        },
	});
	
	
    module.ReceiptScreenWidget.include({    
        refresh: function() {
            var order = this.pos.get('selectedOrder');
			var customer = order.get_client();
            var invoice_no = order.get_invoice_no();
			var partner = '';
			if(customer){
				partner = customer;
			}
            $('.pos-receipt-container', this.$el).html(QWeb.render('PosTicket',{
                    widget:this,
                    order: order,
					partner : partner,
                    invoice : invoice_no,
                    orderlines: order.get('orderLines').models,
                    paymentlines: order.get('paymentLines').models,
                }));
        },
    });
	
    module.CustomerReceiptScreenWidget.include({    
        refresh: function() {
            var order = this.pos.get('selectedOrder');
			var customer = order.get_client();
			var partner = '';
            var payment_detail = order.get_payment_detail();
            var payment_amount = order.get_payment_amount();
            var payment_no = order.get_payment_no();
			if(customer){
				partner = customer;
			}
            $('.pos-receipt-container', this.$el).html(QWeb.render('CustomerPosTicket',{
                    widget:this,
                    order: order,
					partner : partner,
                    orderlines: order.get('orderLines').models,
                    paymentlines: order.get('paymentLines').models,
                    paymentdetail: payment_detail,
                    paymentamount: payment_amount,
                    paymentno: payment_no,
                }));
        },
    });
	
	
}