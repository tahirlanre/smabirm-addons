openerp.pos_discount_amount = function(instance){
    var module   = instance.point_of_sale;
    var QWeb = instance.web.qweb;
	_t = instance.web._t;
    var round_pr = instance.web.round_precision
	

    module.Order = module.Order.extend({
       getSubtotal : function(){
            return round_pr((this.get('orderLines')).reduce((function(sum, orderLine){
                return sum + orderLine.get_product().list_price;
            }), 0), this.pos.currency.rounding);
       },
       getDiscountTotal: function() {
            return round_pr((this.get('orderLines')).reduce((function(sum, orderLine) {
                return sum + ( (orderLine.get_discount()) * orderLine.get_quantity());
            }), 0), this.pos.currency.rounding);
        },
    });

    module.Orderline = module.Orderline.extend({
        get_base_price:    function(){
            var rounding = this.pos.currency.rounding;
            return round_pr((this.get_unit_price() - this.get_discount()) * this.get_quantity(), rounding);
        },
        set_discount: function(discount){
            var disc = Math.max(parseFloat(discount) || 0, 0);
            this.discount = disc;
            this.discountStr = '' + disc;
            this.trigger('change',this);
        },
        get_all_prices: function(){
            var base = round_pr(this.get_quantity() * (this.get_unit_price() - this.get_discount()), this.pos.currency.rounding);
            var totalTax = base;
            var totalNoTax = base;
            var taxtotal = 0;

            var product =  this.get_product();
            var taxes_ids = product.taxes_id;
            var taxes =  this.pos.taxes;
            var taxdetail = {};
            var product_taxes = [];

            _(taxes_ids).each(function(el){
                product_taxes.push(_.detect(taxes, function(t){
                    return t.id === el;
                }));
            });

            var all_taxes = _(this.compute_all(product_taxes, base)).flatten();

            _(all_taxes).each(function(tax) {
                if (tax.price_include) {
                    totalNoTax -= tax.amount;
                } else {
                    totalTax += tax.amount;
                }
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
            });

            return {
                "priceWithTax": totalTax,
                "priceWithoutTax": totalNoTax,
                "tax": taxtotal,
                "taxDetails": taxdetail,
            };
        },

    });

};

