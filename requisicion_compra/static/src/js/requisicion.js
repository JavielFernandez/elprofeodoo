odoo.define('requisiciones_compra.requisicion', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var core = require('web.core');
    var _t = core._t;

    FormController.include({
        saveRecord: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // Aquí puedes agregar lógica adicional después de guardar el registro
            });
        },
    });
});