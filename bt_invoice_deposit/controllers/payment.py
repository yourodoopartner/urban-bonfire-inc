# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import http, _
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError


class PaymentPortal(http.Controller):

    @route('/invoice/pay_deposit/<int:invoice_id>/form_tx', type='json', auth="public", website=True)
    def invoice_pay_deposit_form(self, acquirer_id, invoice_id, save_token=False, access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button on the payment
        form.

        :return html: form containing all values related to the acquirer to
                      redirect customers to the acquirer website """
        invoice_sudo = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice_sudo:
            return False

        try:
            acquirer_id = int(acquirer_id)
        except:
            return False

        if request.env.user._is_public():
            save_token = False # we avoid to create a token for the public user

        success_url = kwargs.get(
            'success_url', "%s?%s" % (invoice_sudo.access_url, url_encode({'access_token': access_token}) if access_token else '')
        )
        vals = {
            'acquirer_id': acquirer_id,
            'return_url': success_url,
        }

        if save_token:
            vals['type'] = 'form_save'

        transaction = invoice_sudo._create_payment_transaction_deposit(vals)
        PaymentProcessing.add_payment_transaction(transaction)

        render_values = {
                'type': 'form_save' if save_token else 'form',
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
            }
        submit_txt=_('Pay & Confirm')
        values = {
            'partner_id': invoice_sudo.partner_id.id,
        }
        if render_values:
            values.update(render_values)
        return transaction.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            transaction.reference,
            invoice_sudo.deposit_amount,
            invoice_sudo.currency_id.id,
            values=values,
        )

    @http.route('/invoice/pay_deposit/<int:invoice_id>/s2s_token_tx', type='http', auth='public', website=True)
    def invoice_pay_deposit_token(self, invoice_id, pm_id=None, **kwargs):
        """ Use a token to perform a s2s transaction """
        error_url = kwargs.get('error_url', '/my')
        access_token = kwargs.get('access_token')
        params = {}
        if access_token:
            params['access_token'] = access_token

        invoice_sudo = request.env['account.move'].sudo().browse(invoice_id).exists()
        if not invoice_sudo:
            params['error'] = 'pay_invoice_invalid_doc'
            return request.redirect(_build_url_w_params(error_url, params))

        success_url = kwargs.get(
            'success_url', "%s?%s" % (invoice_sudo.access_url, url_encode({'access_token': access_token}) if access_token else '')
        )
        try:
            token = request.env['payment.token'].sudo().browse(int(pm_id))
        except (ValueError, TypeError):
            token = False
        token_owner = invoice_sudo.partner_id if request.env.user._is_public() else request.env.user.partner_id
        if not token or token.partner_id != token_owner:
            params['error'] = 'pay_invoice_invalid_token'
            return request.redirect(_build_url_w_params(error_url, params))

        vals = {
            'payment_token_id': token.id,
            'type': 'server2server',
            'return_url': _build_url_w_params(success_url, params),
        }

        tx = invoice_sudo._create_payment_transaction_deposit(vals)
        PaymentProcessing.add_payment_transaction(tx)

        params['success'] = 'pay_invoice'
        return request.redirect('/payment/process')
    
    
class PortalAccount(CustomerPortal):

    # ------------------------------------------------------------
    # My Draft Invoices
    # ------------------------------------------------------------


    @http.route(['/my/draftinvoices', '/my/draftinvoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_draftinvoices(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = {}
        draftinvoice_count = request.env['account.move'].search_count([
            ('type', 'in', ('out_invoice', 'in_invoice', 'out_refund', 'in_refund', 'out_receipt', 'in_receipt')),
            ('state', '=', 'draft'),
        ])
        values['draftinvoice_count'] = draftinvoice_count
        AccountInvoice = request.env['account.move']

        domain = [('state', '=', 'draft'), ('type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'))]

        searchbar_sortings = {
            'date': {'label': _('Invoice Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('account.move', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        draftinvoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/draftinvoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=draftinvoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'draftinvoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/draftinvoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("bt_invoice_deposit.portal_my_draftinvoices", values)

