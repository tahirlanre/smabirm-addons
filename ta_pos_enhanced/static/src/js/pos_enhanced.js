/*
    POS Customer payment module for Odoo
    
*/

openerp.ta_pos_enhanced = function(instance){
    var module = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var PosModelSuper = module.PosModel;
    var round_di = instance.web.round_decimals;

//    module.PosModel = module.PosModel.extend({});
     /* Handle Button "Customer Payment" */
    var _saved_renderElement = module.PosWidget.prototype.renderElement;
    module.PosWidget.prototype.renderElement = function() {
        _saved_renderElement.apply(this, arguments);
        var self = this;

        self.el.querySelector('.customer-payment')
            .addEventListener('click', function(){
                
                var ss = self.pos.pos_widget.screen_selector;
                if(ss.get_current_screen() === 'receipt'){
                    console.warn('TODO should not get there...?');
                    return;
                }
                
                if(ss.get_current_screen() === 'customer_receipt'){
                    console.warn('TODO should not get there...?');
                    return;
                }
                    
                self.pos_widget.screen_selector.show_popup('customer-payment-popup');
               //self.pos_widget.screen_selector.set_current_screen('customer_payment');
            });

    },
    module.PosModel = module.PosModel.extend({
        
        load_server_data: function(){
            var self = this;
            var loaded = PosModelSuper.prototype.load_server_data.call(this);
            loaded = loaded.then(function(){
                return self.fetch(
                    'res.partner',
                    ['balance','credit_limit_restriction','credit_limit'],
                    [['customer','=',true]],
                    {}
                );
            }).then(function(partners){
                $.each(partners, function(){
                    $.extend(self.db.get_partner_by_id(this.id) || {}, this)
                });
                return $.when()
            }).then(function(){
                return self.fetch(
                    'product.product',
                    ['qty_available'],
                    [['sale_ok','=',true],['available_in_pos','=',true]],
                    {'location': self.config.stock_location_id[0]}
                );
            }).then(function(products){
                $.each(products, function(){
                    $.extend(self.db.get_product_by_id(this.id) || {}, this)
                });
                return $.when()
            })
            return loaded;
        },
        refresh_qty_available:function(product){
            var $elem = $("[data-product-id='"+product.id+"'] .qty-tag");
            $elem.html(product.qty_available)
            if (product.qty_available <= 0 && !$elem.hasClass('not-available')){
                $elem.addClass('not-available')
            }
        },
        push_order: function(order){
            var self = this;
            var pushed = PosModelSuper.prototype.push_order.call(this, order);
            var client = order && order.get_client();
            var ss = self.pos_widget.screen_selector;
            var currentScreen = ss.get_current_screen();
            var order = self.get('selectedOrder');
            var bal = order.getPaidTotal() - order.getTotalTaxIncluded();
			//console.log('push_order', order.export_as_JSON());
            if (order){
                order.get('orderLines').each(function(line){
                    var product = line.get_product();
                    product.qty_available -= line.get_quantity();
                    self.refresh_qty_available(product);
                })
            }
            if (client){
                if(order.get_balance()){
                    client.balance -= bal;
                    return;
                }
                if(bal && (currentScreen == 'customer_payment')){
                    client.balance -= bal;
                    return;
                }
            }
            return pushed;
        },
        push_and_invoice_order: function(order){
            var self = this;
            var invoiced = new $.Deferred(); 

            if(!order.get_client()){
                invoiced.reject('error-no-client');
                return invoiced;
            }
			//console.log('push_and_invoice_order', order.export_as_JSON());
            var order_id = this.db.add_order(order.export_as_JSON());
           
            this.flush_mutex.exec(function(){
                var done = new $.Deferred(); // holds the mutex

                // send the order to the server
                // we have a 30 seconds timeout on this push.
                // FIXME: if the server takes more than 30 seconds to accept the order,
                // the client will believe it wasn't successfully sent, and very bad
                // things will happen as a duplicate will be sent next time
                // so we must make sure the server detects and ignores duplicated orders

                var transfer = self._flush_orders([self.db.get_order(order_id)], {timeout:30000, to_invoice:false});
                
                transfer.fail(function(){
                    invoiced.reject('error-transfer');
                    done.reject();
                });

                // on success, get the order id generated by the server
                transfer.pipe(function(order_server_id){    

                    // generate the pdf and download it
                    //self.pos_widget.do_action('point_of_sale.pos_lines_report',{additional_context:{ 
                     //   active_ids:order_server_id,
                    //}});
                    //self.pos_widget.screen_selector.set_current_screen('receipt')
                    order.invoice_no = order_server_id[0];
                    invoiced.resolve();
                    done.resolve();
                });
                
                var bal = order.getPaidTotal() - order.getTotalTaxIncluded();
                var client = order && order.get_client();
            
                if(order.get_balance()){
                    client.balance -= bal;
                    //return;
                }
	            if (order){
	                order.get('orderLines').each(function(line){
	                    var product = line.get_product();
	                    product.qty_available -= line.get_quantity();
	                    self.refresh_qty_available(product);
	                })
	            }
                return done;
            });
            return invoiced;
        },
    });
    
    module.PosWidget.include({

        build_widgets: function() {
            this._super();
            var self = this;
            // --------  Screen Selector ---------
            //this.customer_payment_screen = new module.CustomerPaymentScreenWidget(this, {});
            //this.customer_payment_screen.appendTo(this.$('.screens'));
            this.customer_receipt_screen = new module.CustomerReceiptScreenWidget(this, {});
            this.customer_receipt_screen.appendTo(this.$('.screens'));
            this.customer_payment_popup = new module.CustomerPaymentWidget(this, {});
            this.customer_payment_popup.appendTo(this.$el);

            this.screen_selector = new module.ScreenSelector({
                pos: this.pos,
                screen_set:{
                    'products': this.product_screen,
                    'payment' : this.payment_screen,
                    'scale':    this.scale_screen,
                    'receipt' : this.receipt_screen,
                    'clientlist': this.clientlist_screen,
                    //'customer_payment': this.customer_payment_screen,
                    'customer_receipt': this.customer_receipt_screen,
                },
                popup_set:{
                    'error': this.error_popup,
                    'error-barcode': this.error_barcode_popup,
                    'error-traceback': this.error_traceback_popup,
                    'confirm': this.confirm_popup,
                    'unsent-orders': this.unsent_orders_popup,
                    'customer-payment-popup': this.customer_payment_popup,
                },
                default_screen: 'products',
                default_mode: 'cashier',
            });
        },
        
        
    });
  
    module.CustomerReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'CustomerReceiptScreenWidget',

        show_numpad:     false,
        show_leftpane:   false,

        show: function(){
            this._super();
            var self = this;

            var print_button = this.add_action_button({
                    label: _t('Print'),
                    icon: '/point_of_sale/static/src/img/icons/png48/printer.png',
                    click: function(){ self.print(); },
                });

            var finish_button = this.add_action_button({
                    label: _t('Next Order'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-next.png',
                    click: function() { self.finishOrder(); },
                });

            this.refresh();
            var no_of_tickets = this.pos.config.no_of_payment_tickets; //No of tickets to print
            this.print_ticket(no_of_tickets);
            //this.print();

            //
            // The problem is that in chrome the print() is asynchronous and doesn't
            // execute until all rpc are finished. So it conflicts with the rpc used
            // to send the orders to the backend, and the user is able to go to the next
            // screen before the printing dialog is opened. The problem is that what's
            // printed is whatever is in the page when the dialog is opened and not when it's called,
            // and so you end up printing the product list instead of the receipt...
            //
            // Fixing this would need a re-architecturing
            // of the code to postpone sending of orders after printing.
            //
            // But since the print dialog also blocks the other asynchronous calls, the
            // button enabling in the setTimeout() is blocked until the printing dialog is
            // closed. But the timeout has to be big enough or else it doesn't work
            // 2 seconds is the same as the default timeout for sending orders and so the dialog
            // should have appeared before the timeout... so yeah that's not ultra reliable.

            finish_button.set_disabled(true);
            setTimeout(function(){
                finish_button.set_disabled(false);
            }, 2000);
        },
        print: function() {
            window.print();
        },
        print_ticket: function(no){ 
			if(this.pos.config.silent_printing){
            	// Catch error in case addon is not present - Tahir
            	try{
                    //Always use default printer.
                    var listOfPrinters = jsPrintSetup.getPrintersList();
                    var default_printer = listOfPrinters.substr(0,listOfPrinters.indexOf(','));
                    //alert(default_printer);
                    jsPrintSetup.setPrinter(default_printer);
                    
                    //sets no of copies to print
                    jsPrintSetup.setOption('numCopies', no);
                    
                    //set silent printing
                    jsPrintSetup.setOption('printSilent', 1);
                    setTimeout(function() {
                        jsPrintSetup.print();
                    }, 2000);
                    
                    this.pos.get('selectedOrder')._printed = true;
                    jsPrintSetup.clearSilentPrint();
             
            	}catch(err){
                	//Use normal window printing
                	this.pos.get('selectedOrder')._printed = true;
                	setTimeout(function() {
                        window.print();
                    }, 1000);
            	}
			}else{
                //Use normal window printing
                this.pos.get('selectedOrder')._printed = true;
                setTimeout(function() {
                        window.print();
                    }, 1000);
			}
        },
        finishOrder: function() {
            this.pos.get('selectedOrder').destroy();
        },
	    refresh: function() {
	              var order = this.pos.get('selectedOrder');
	              var payment_detail = order.get_payment_detail();
	              var payment_amount = order.get_payment_amount();
	              $('.pos-receipt-container', this.$el).html(QWeb.render('CustomerPosTicket',{
	                      widget:this,
	                      order: order,
	                      orderlines: order.get('orderLines').models,
	                      paymentlines: order.get('paymentLines').models,
                    	  paymentdetail: payment_detail,
                          paymentamount: payment_amount,
	                  }));
	    },
        close: function(){
            this._super();
        }
    });
	module.ReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'ReceiptScreenWidget',

        show_numpad:     false,
        show_leftpane:   false,
		
        show: function(){
            this._super();
            var self = this;

            var print_button = this.add_action_button({
                    label: _t('Print'),
                    icon: '/point_of_sale/static/src/img/icons/png48/printer.png',
                    click: function(){ self.print(); },
                });

            var finish_button = this.add_action_button({
                    label: _t('Next Order'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-next.png',
                    click: function() { self.finishOrder(); },
                });

            this.refresh();

            if (!this.pos.get('selectedOrder')._printed){ 
                var no_of_tickets = this.pos.config.no_of_sale_tickets; //No of tickets to print
				this.print_ticket(no_of_tickets);			
            }

            //
            // The problem is that in chrome the print() is asynchronous and doesn't
            // execute until all rpc are finished. So it conflicts with the rpc used
            // to send the orders to the backend, and the user is able to go to the next 
            // screen before the printing dialog is opened. The problem is that what's 
            // printed is whatever is in the page when the dialog is opened and not when it's called,
            // and so you end up printing the product list instead of the receipt... 
            //
            // Fixing this would need a re-architecturing
            // of the code to postpone sending of orders after printing.
            //
            // But since the print dialog also blocks the other asynchronous calls, the
            // button enabling in the setTimeout() is blocked until the printing dialog is 
            // closed. But the timeout has to be big enough or else it doesn't work
            // 2 seconds is the same as the default timeout for sending orders and so the dialog
            // should have appeared before the timeout... so yeah that's not ultra reliable. 

            finish_button.set_disabled(true);   
            setTimeout(function(){
                finish_button.set_disabled(false);
            }, 2000);
        },
        print_ticket: function(no){ 
			if(this.pos.config.silent_printing){
            	// Catch error in case addon is not present - Tahir
            	try{
                    //Always use default printer.
                    var listOfPrinters = jsPrintSetup.getPrintersList();
                    var default_printer = listOfPrinters.substr(0,listOfPrinters.indexOf(','));
                    //alert(default_printer);
                    jsPrintSetup.setPrinter(default_printer);
                    
                    //sets no of copies to print
                    jsPrintSetup.setOption('numCopies', no);
                    
                    //set silent printing
                    jsPrintSetup.setOption('printSilent', 1);
                    setTimeout(function() {
                        jsPrintSetup.print();
                    }, 2000);
                    
                    this.pos.get('selectedOrder')._printed = true;
                    jsPrintSetup.clearSilentPrint();
             
            	}catch(err){
                	//Use normal window printing
                	this.pos.get('selectedOrder')._printed = true;
                	setTimeout(function() {
                        window.print();
                    }, 1000);
            	}
			}else{
                //Use normal window printing
                this.pos.get('selectedOrder')._printed = true;
                setTimeout(function() {
                        window.print();
                    }, 1000);
			}
        },
	    refresh: function() {
	              var order = this.pos.get('selectedOrder');
	              $('.pos-receipt-container', this.$el).html(QWeb.render('PosTicket',{
	                      widget:this,
	                      order: order,
	                      orderlines: order.get('orderLines').models,
	                      paymentlines: order.get('paymentLines').models,
	                  }));
	    },
        print: function() {
            this.pos.get('selectedOrder')._printed = true;
            window.print();
        },
        finishOrder: function() {
            this.pos.get('selectedOrder').destroy();
        },
        close: function(){
            this._super();
        }
		
	});
	
    module.PaypadButtonWidget = module.PosBaseWidget.extend({
        template: 'PaypadButtonWidget',
        init: function(parent, options){
            this._super(parent, options);
            this.cashregister = options.cashregister;
        },
        renderElement: function() {
            var self = this;
            this._super();

            this.$el.click(function(){
                if (self.pos.get('selectedOrder').get('screen') === 'receipt'){  //TODO Why ?
                    console.warn('TODO should not get there...?');
                    return;
                }
                var ss = self.pos_widget.screen_selector;
                if(ss.get_current_screen() === 'customer_payment'){
                    self.pos.get('selectedOrder').addPaymentline(self.cashregister);
                    self.pos_widget.screen_selector.set_current_screen('customer_payment');
                    //console.log('Customer Payment');
                }else{
                    self.pos.get('selectedOrder').addPaymentline(self.cashregister);
                    self.pos_widget.screen_selector.set_current_screen('payment');
                    //console.log('Payment');  
                }
            });
        },
    });
    
    module.Order = module.Order.extend({
        
       initialize: function(attributes){
           Backbone.Model.prototype.initialize.apply(this, arguments);
            this.pos = attributes.pos;
            this.sequence_number = this.pos.pos_session.sequence_number++;
            this.uid =     this.generateUniqueId();
            this.invoice_no = undefined;
            this.payment_no = undefined;
            this.payment_detail = undefined;
            this.set({
                creationDate:   new Date(),
                orderLines:     new module.OrderlineCollection(),
                paymentLines:   new module.PaymentlineCollection(),
                name:           _t("Order ") + this.uid,
                client:         null,
                laybyorder : null,
            });
            this.payment_amount = 0;
            this.selected_orderline   = undefined;
            this.selected_paymentline = undefined;
            this.screen_data = {};  // see ScreenSelector
            this.receipt_type = 'receipt';  // 'receipt' || 'invoice'
            this.temporary = attributes.temporary || false;
            return this;
        },
        // returns the amount of money on this paymentline
        get_payment_amount: function(){
            return this.payment_amount;
        },
        set_payment_amount: function(value){
            this.payment_amount = round_di(parseFloat(value) || 0, 2);
            //this.trigger('change:amount_layby',this);
        },
        set_payment_detail: function(id){
            var self = this;
            var payment;
            _.each(self.pos.cashregisters, function(cashregister) {
                        if(cashregister.journal_id[0]==id) payment = cashregister.journal_id[1];
           });
           this.payment_detail = payment;
        },
        get_payment_detail: function(){
            return this.payment_detail;
        },
        get_invoice_no: function(){
            return this.invoice_no;
        },
        get_payment_no: function(){
            return this.payment_no;
        },
        getChange: function() {
            var self = this;
            var ss = self.pos.pos_widget.screen_selector;
            var change = this.getPaidTotal() - this.getTotalTaxIncluded();
            if(change > 0 && ss.get_current_screen() !== 'customer_payment')
                return change;
            return 0;
        },
        get_balance: function(){
            var balance = this.getPaidTotal() - this.getTotalTaxIncluded();
            if(balance < 0)
                return balance;
            return 0;
        },
        addProduct: function(product, options){
            
            options = options || {};
            var attr = JSON.parse(JSON.stringify(product));
            attr.pos = this.pos;
            attr.order = this;
            var line = new instance.point_of_sale.Orderline({}, {pos: this.pos, order: this, product: product});
            var currentOrderLines = this.pos.get('selectedOrder').get('orderLines');
            var prod_qty = attr.qty_available;
            
      
            if (prod_qty <= 0 && attr.type != 'service') {
                
                alert ('Not enough stock !');
                return;
            }
            
            if (attr.type == 'service') {
                console.log('service');
                if(options.quantity !== undefined){
                    line.set_quantity(options.quantity);
                }
                if(options.price !== undefined){
                    line.set_unit_price(options.price);
                }
                if(options.discount !== undefined){
                    line.set_discount(options.discount);
                }
    
                var last_orderline = this.getLastOrderline();
                if( last_orderline && last_orderline.can_be_merged_with(line) && options.merge !== false){
                    last_orderline.merge(line);
                }else{
                    this.get('orderLines').add(line);
                }
                this.selectLine(this.getLastOrderline());
            }
            
            if (prod_qty > 0 && attr.type != 'service') {
                //console.log('Product');
                add_prod = true
                if (currentOrderLines.length > 0) {
                    (currentOrderLines).each(_.bind( function(item) {
                        if (attr.id == item.get_product().id && prod_qty < item.get_quantity()+1) {
                            add_prod = false;
                            alert ('Not enough stock !');
                        }
                    }, this));
                } 
                if (add_prod) {
                    if(options.quantity !== undefined){
                        line.set_quantity(options.quantity);
                    }
                    if(options.price !== undefined){
                        line.set_unit_price(options.price);
                    }
                    if(options.discount !== undefined){
                        line.set_discount(options.discount);
                    }
        
                    var last_orderline = this.getLastOrderline();
                    if( last_orderline && last_orderline.can_be_merged_with(line) && options.merge !== false){
                        last_orderline.merge(line);
                    }else{
                        this.get('orderLines').add(line);
                    }
                    this.selectLine(this.getLastOrderline());
                }
            }
        },
        
        
    });
    
    module.PaymentScreenWidget.include({
		partner_balance: function(client){
			var model = new instance.web.Model("res.partner");
			return model.query(['balance'])
								.filter([['id','=',client.id]])
								.first()
								.then(function(result){ 
									return result;
								});
			
		},
        show: function(){
            this._super();
            var self = this;

        },
        update_payment_summary: function() {
            var currentOrder = this.pos.get('selectedOrder');
            var paidTotal = currentOrder.getPaidTotal();
            var dueTotal = currentOrder.getTotalTaxIncluded();
            var remaining = dueTotal > paidTotal ? dueTotal - paidTotal : 0;
            var change = paidTotal > dueTotal ? paidTotal - dueTotal : 0;

            this.$('.payment-due-total').html(this.format_currency(dueTotal));
            this.$('.payment-paid-total').html(this.format_currency(paidTotal));
            this.$('.payment-remaining').html(this.format_currency(remaining));
            this.$('.payment-change').html(this.format_currency(change));
            if(currentOrder.selected_orderline === undefined){
                remaining = 1;  // What is this ? 
            }
                
            if(this.pos_widget.action_bar){
                this.pos_widget.action_bar.set_button_disabled('validation', false);
                this.pos_widget.action_bar.set_button_disabled('invoice', true);
            }
        },
        validate_order: function(options) {
            var self = this;

            options = {invoice: true};

            var currentOrder = self.pos.get('selectedOrder');
            var currentOrderLines = this.pos.get('selectedOrder').get('orderLines');
            var item_count = 0;
			var client = currentOrder.get_client();
			
			
            if (currentOrderLines.length > 0) {
                new instance.web.Model("pos.order").get_func("check_connection")().done(function(connection) {
                    if (connection) {
                        (currentOrderLines).each(_.bind( function(item) {
                            new instance.web.Model("product.product").get_func("search_read")(
                                                    [['id', '=', item.get_product().id]], ['qty_available']).pipe(
                                function(result) {
                                    if (result && result[0]) {
                                        var quantity = 0;
                                            (currentOrderLines).each(_.bind( function(line) {
                                            if (result[0].id == line.get_product().id && line.get_product().type != 'service') {
                                                quantity += line.get_quantity();
                                            }
                                        }, this));
                                        if (quantity > result[0].qty_available && item.get_product().type != 'service'){
                                            alert ('Not enough stock for product "' + item.get_product().display_name + '"');
                                            return;
                                        } else {
                                            item_count = item_count + 1;
                                            if (item_count == currentOrderLines.length) {
                                                if(currentOrder.get('orderLines').models.length === 0){
                                                    self.pos_widget.screen_selector.show_popup('error',{
                                                        'message': _t('Empty Order'),
                                                        'comment': _t('There must be at least one product in your order before it can be validated'),
                                                    });
                                                    return;
                                                }
                                                
                                                if (!currentOrder.get_client() && currentOrder.get_balance()){
                                                        self.pos_widget.screen_selector.show_popup('error',{
                                                        'message': _t('Anonymous order cannot be partially or not paid'),
                                                        'comment': _t('Please select a customer for this order. This can be done by clicking the order tab'),
                                                        });
                                                    return;
                                                }
                                    
                                                var plines = currentOrder.get('paymentLines').models;
                                                for (var i = 0; i < plines.length; i++) {
                                                    if (plines[i].get_type() === 'bank' && plines[i].get_amount() < 0) {
                                                        self.pos_widget.screen_selector.show_popup('error',{
                                                            'message': _t('Negative Bank Payment'),
                                                            'comment': _t('You cannot have a negative amount in a Bank payment. Use a cash payment method to return money to the customer.'),
                                                        });
                                                        return;
                                                    }
                                                }
												//debugger;
												if(client && currentOrder.get_balance()){
													if(client.credit_limit_restriction){
														var total_pay = 0;
														var yo = 0;
														for (var i = 0; i < plines.length; i++) {
                                                    		total_pay = plines[i].get_amount(); 
                                                    	}
														/*console.log(self.partner_balance(client));
														var pb = self.partner_balance(client);
														pb.done(function(customer){
															console.log('Printing balance from server call '+result.balance)
															yo = result.balance;
															console.log('Printing yo inside'+ yo);
														});*/
														var f_balance = client.balance + (currentOrder.getTotalTaxIncluded()-total_pay);
														//console.log('Printing yo '+ yo);
                                                    	if(f_balance>client.credit_limit){
                                                            	self.pos_widget.screen_selector.show_popup('error',{
                                                            		'message': _t('Credit Limit'),
                                                            		'comment': _t('This customer will exceed credit limit by ₦'+ (f_balance-client.credit_limit)+' if invoice is validated'),
                                                        		});
                                                        		return;
                                                    		}
														}
												}
												
                                                if(self.pos.config.discount_restriction){
                                                    var olines = currentOrder.get('orderLines').models;
                                                    for (var i = 0; i < olines.length; i++) {
                                                        console.log(olines[i]);
                                                        if(olines[i].discount > self.pos.config.max_discount){
                                                                self.pos_widget.screen_selector.show_popup('error',{
                                                                'message': _t('Maximum Discount'),
                                                                'comment': _t('Please enter discount lower than maximum discount (' + self.pos.config.max_discount + ') for ' + olines[i].product.display_name),
                                                            });
                                                            return;
                                                        }
                                                    }
                                                }
                                                //if(!self.is_paid()){
                                                    //return;
                                                //}
                                    
                                                // The exact amount must be paid if there is no cash payment method defined.
                                                if (Math.abs(currentOrder.getTotalTaxIncluded() - currentOrder.getPaidTotal()) > 0.00001) {
                                                    var cash = false;
                                                    for (var i = 0; i < self.pos.cashregisters.length; i++) {
                                                        cash = cash || (self.pos.cashregisters[i].journal.type === 'cash');
                                                    }
                                                    if (!cash) {
                                                        self.pos_widget.screen_selector.show_popup('error',{
                                                            message: _t('Cannot return change without a cash payment method'),
                                                            comment: _t('There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'),
                                                        });
                                                        return;
                                                    }
                                                }
                                    
                                                if (self.pos.config.iface_cashdrawer) {
                                                    self.pos.proxy.open_cashbox();
                                                }
                                    
                                                if(options.invoice){
                                                    // deactivate the validation button while we try to send the order
                                                    self.pos_widget.action_bar.set_button_disabled('validation',true);
                                                    self.pos_widget.action_bar.set_button_disabled('invoice',true);
                                    
                                                    var invoiced = self.pos.push_and_invoice_order(currentOrder);
                                                    //console.log(currentOrder)
                                    
                                                    invoiced.fail(function(error){
                                                        if(error === 'error-no-client'){
                                                            self.pos_widget.screen_selector.show_popup('error',{
                                                                message: _t('An anonymous order cannot be invoiced'),
                                                                comment: _t('Please select a client for this order. This can be done by clicking the order tab'),
                                                            });
                                                        }else{
                                                            self.pos_widget.screen_selector.show_popup('error',{
                                                                message: _t('The order could not be sent'),
                                                                comment: _t('Check your internet connection and try again.'),
                                                            });
                                                        }
                                                        self.pos_widget.action_bar.set_button_disabled('validation',false);
                                                        self.pos_widget.action_bar.set_button_disabled('invoice',false);
                                                    });
                                    
                                                    invoiced.done(function(){
                                                        self.pos_widget.action_bar.set_button_disabled('validation',false);
                                                        self.pos_widget.action_bar.set_button_disabled('invoice',false);
														if(currentOrder.invoice_no){
                                                             self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                                                        }else{
                                                            alert("Could not process invoice, please refresh and start again");
                                                        }
                                                    });
                                    
                                                }else{
                                                    //var self = this;
                                                    self.pos.push_order(currentOrder);
                                                    if(self.pos.config.iface_print_via_proxy){
                                                        var receipt = currentOrder.export_for_printing();
                                                        self.pos.proxy.print_receipt(QWeb.render('XmlReceipt',{
                                                            receipt: receipt, widget: self,
                                                        }));
                                                        self.pos.get('selectedOrder').destroy();    //finish order and go back to scan screen
                                                    }else{
                                                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                                                    }
                                                }
                                            }
                                            flag = false;
                                        }
                                    }
                                });
                        }));
                    }
                }).fail(function(result, ev) {
                    ev.preventDefault();
                    connection = false;
                    alert ('Server is not conencted !')
                    return
                });
            }else{
                self.pos_widget.screen_selector.show_popup('error',{
                        'message': _t('Empty Order'),
                        'comment': _t('There must be at least one product in your order before it can be validated'),
                    });
                    return;
            }

            // hide onscreen (iOS) keyboard 
            setTimeout(function(){
                document.activeElement.blur();
                $("input").blur();
            },250);
        },
    });
    
    module.CustomerPaymentWidget = module.PopUpWidget.extend({
        template: 'CustomerPaymentWidget',
        
        init: function(parent, options){
            this._super(parent, options);
			this.cashregisters = this.pos.cashregisters;
        },
        show: function () {
            var self = this;
            this._super();
            this.renderElement();
			//console.log('cash', this.cashregisters);
            this.$('.footer #accept').off('click').click(function () {
                if (confirm("Are you sure you want to pay this?") == true) {
                    self.customer_payment_via_pos();
                }else{
                    
                }
                //$('this').prop("disabled", true);
            });
            this.$('.footer #cancel').off('click').click(function () {
                self.pos_widget.screen_selector.close_popup();
            });
            this.update_input();
        },
        update_input: function(){
            var self = this;
            var fields = {}
            var contents = this.$('.payment-details');
            contents.empty();
			//console.log('pos', this.cashregisters);
            contents.append($(QWeb.render('PaymentDetailsWidget',{widget:this})));
            contents.find('.layby-payment input').on('keyup',function(event){
                    self.pos.get('selectedOrder').set_payment_amount(this.value);
                    //console.log('value', this.value);
                });        
        },
		customer_payment_via_pos: function(){
			var self = this;
            var currentOrder = this.pos.get('selectedOrder');
            var client = currentOrder.get_client();
            var fields = {}
            this.$('.payment-details .detail').each(function(idx,el){
                fields[el.name] = el.value;
                });
			this.pos.get('selectedOrder').set_payment_detail(fields.cash_id);
			var journal_id = parseInt(fields.cash_id);
			var amount = this.$('.layby-payment input').val();
			var ref = this.$('.layby-payment-desc input').val();
			var statement_id;
			var pos_session_id = this.pos.pos_session.id;
			for(var i = 0; i < this.cashregisters.length; i++){
				if (this.cashregisters[i].journal_id[0] == fields.cash_id){
					statement_id = this.cashregisters[i].id;
					break;
				}
			}
			if(client){
                partner_id = client.id;
                if(amount){
                   new instance.web.Model('pos.order').call('pos_customer_payment',[amount, statement_id, journal_id, partner_id, pos_session_id, ref]).then(function(result){
                   if(result){
                   		currentOrder.payment_no = result;
                   	 	client.balance -=amount;
                   	 	//self.pos.load_new_invoices();
                   	 	self.pos_widget.screen_selector.close_popup();
                   	 	self.pos_widget.screen_selector.set_current_screen('customer_receipt');
                   }else{
                   		alert('Could not process payment! Please refresh and try again');
                   }
                });}else{
                    	alert('Please enter valid amount!');
                    //self.pos_widget.screen_selector.close_popup();
                } 
			}else{
                alert('Please choose Customer !');
                self.pos_widget.screen_selector.close_popup();
			}
		},
        payment_via_pos: function(){
			var self = this;
            var currentOrder = this.pos.get('selectedOrder');
            var client = currentOrder.get_client();
            var fields = {}
			var statement_id;
			var pos_session_id = this.pos.pos_session.id;
            this.$('.payment-details .detail').each(function(idx,el){
                //console.log('1 ' + el.name);
                //console.log('2 ' + el.value);
                fields[el.name] = el.value;
                //console.log('fields', fields);
                });
            fields.cash_id = fields.cash_id;
            this.pos.get('selectedOrder').set_payment_detail(fields.cash_id);
			//console.log('pos ', this.pos);
            var amount = this.pos.get('selectedOrder').get_payment_amount();
            if(client) {
                partner = client.id;
                if(amount){
                new instance.web.Model('pos.order').call('customer_payment_via_pos',[partner, fields.cash_id, amount]).then(function(result){
                   if(result){
                       //self.pos.get('selectedOrder').destroy();
                    currentOrder.payment_no = result;
                    client.balance -=amount;
                    //self.pos.load_new_invoices();
                    self.pos_widget.screen_selector.close_popup();
                    self.pos_widget.screen_selector.set_current_screen('customer_receipt');
                   }
                });}else{
                    alert('Please enter valid amount!');
                    //self.pos_widget.screen_selector.close_popup();
                } 
            }
            else{
                alert('Please choose Customer !');
                self.pos_widget.screen_selector.close_popup();
            }
        },
        close:function(){
           this._super();
           this.pos.proxy_queue.clear();
        },
    });
}
