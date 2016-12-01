/**
 * Miscellaneous utility functions.
 */

/**
 * Show an alert dialog with a single button.
 * @param [text] The text to display.
 * @param [buttonText] The text for the button.
 * @param [buttonClass] Class string to apply to the button.
 * @param [escapedHtml] If you want to render the text as HTML rather than
 *        plain text, set this to true to acknowledge that you have escaped any
 *        user-created data within the text to prevent XSS exploits.
 * @param callback Callback function called when the user clicks the button.
 */
isic.showAlertDialog = function (params) {
    params = _.extend({
        text: '',
        buttonText: 'OK',
        buttonClass: 'btn-primary',
        escapedHtml: false
    }, params);

    var container = $('#g-dialog-container');
    container.html(isic.templates.alertDialog({
        params: params
    })).girderModal(false).on('hidden.bs.modal', function () {
        if (params.callback) {
            params.callback();
        }
    });

    var el = container.find('.modal-body>p');
    if (params.escapedHtml) {
        el.html(params.text);
    } else {
        el.text(params.text);
    }

    $('#isic-alert-dialog-button').unbind('click').click(function () {
        container.modal('hide');
    });
};