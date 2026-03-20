odoo.define('copy_clipboard', function (require) {
    const InputField = require("web.basic_fields").InputField;
    const setClipboard = require("copy_clipboard.set_clipboard");
    const field_registry = require('web.field_registry');
    const core = require('web.core');
    const _t = core._t;

    InputField.include({
        events: Object.assign({}, InputField.prototype.events, {
            'click .copy-to-clipboard': '_onCopyToClipboardClick',
        }),
        init() {
            this._super.apply(this, arguments);
            this.nodeOptions.isCopyable = 'copyable' in this.attrs;
        },
        _renderEdit: function () {
            this._super.apply(this, arguments);
            if (this.nodeOptions.isCopyable) {
                this.$el.append('<a class="btn btn-default copy-to-clipboard" href="#"><i class="fa fa-copy"/></a>');
            }
        },
        _renderReadonly() {
            this._super.apply(this, arguments);
            if (this.nodeOptions.isCopyable) {
                this.$el.append('<a class="btn btn-default copy-to-clipboard" href="#"><i class="fa fa-copy"/></a>');
            }
        },
        _onCopyToClipboardClick(event) {
            event.preventDefault();
            event.stopPropagation();
            const value = this.$input ? this.$input.attr("value") : this.value;
            setClipboard(value);
            window.alert("Copied to clipboard");
        }
    });
    const CopyableInput = InputField.extend({
        init() {
            this._super.apply(this, arguments);
            this.nodeOptions.isCopyable = true;
        },
    });
    field_registry.add("copyable", CopyableInput);
    return CopyableInput;
});

odoo.define('copy_clipboard.set_clipboard', function () {
    return function (value) {
        const tempInput = document.createElement("input");
        tempInput.style = "position: absolute; left: -1000px; top: -1000px";
        tempInput.value = value;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand("copy");
        document.body.removeChild(tempInput);
    };

});