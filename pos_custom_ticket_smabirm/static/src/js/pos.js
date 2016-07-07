openerp.pos_custom_ticket_smabirm = function(instance){
    var module = instance.point_of_sale;
    //var QWeb = instance.web.qweb;
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
	
	
}