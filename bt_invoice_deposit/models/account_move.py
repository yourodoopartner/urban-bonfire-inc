# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date, get_lang
import base64

from werkzeug import urls
from odoo.addons.http_routing.models.ir_http import slug


class AccountMove(models.Model):
    _inherit = "account.move"


    deposit_exist = fields.Boolean('Deposit Exists', copy=False)
    deposit_amount = fields.Float('Deposit Amount (Expected)', copy=False)
    deposit_amount_collected = fields.Float('Deposit Amount (Collected)', copy=False)
    inv_balance_owed = fields.Float('Invoice Balance Owed', copy=False,
                                    help='This is the difference  between the invoice amount and deposit amount. Company is supposed to collect this amount from customer after the invoice is posted.'
                                    )
    portal_url = fields.Char('Draft Portal URL')
    
    
#     def write(self, values):
#         if not self.deposit_amount:
#             print('wwwwwwwwwwwwwwwwwwwwwwww',self.deposit_amount,self.amount_total)
#             values['deposit_amount'] = self.amount_total
#         return super(AccountMove, self).write(values)
    
    def deduct_deposit(self):
        for invoice_obj in self:
            deposit = self.env['bt.payment.deposit'].search([('invoice_id', '=', invoice_obj.id)])
            if deposit:
                (deposit.move_id + invoice_obj).line_ids \
                    .filtered(lambda line: not line.reconciled and line.account_id == deposit.payment_id.destination_account_id) \
                    .reconcile()
            invoice_obj.deposit_exist = False
            return True
        
    def action_draft_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('bt_invoice_deposit.email_template_edi_draft_invoice', raise_if_not_found=False)
        lang = get_lang(self.env)
        if template and template.lang:
            lang = template._render_template(template.lang, 'account.move', self.id)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        
        portal_url = self.get_portal_url()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = urls.url_join(base_url, portal_url)
        self.portal_url = url
        
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )
        return {
            'name': _('Send Draft Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _create_payment_transaction_deposit(self, vals):
        '''Similar to self.env['payment.transaction'].create(vals) but the values are filled with the
        current invoices fields (e.g. the partner or the currency).
        :param vals: The values to create a new payment.transaction.
        :return: The newly created payment.transaction record.
        '''
        # Ensure the currencies are the same.
        currency = self[0].currency_id
        if any([inv.currency_id != currency for inv in self]):
            raise ValidationError(_('A transaction can\'t be linked to invoices having different currencies.'))

        # Ensure the partner are the same.
        partner = self[0].partner_id
        if any([inv.partner_id != partner for inv in self]):
            raise ValidationError(_('A transaction can\'t be linked to invoices having different partners.'))

        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = vals.get('acquirer_id')
        acquirer = None
        payment_token_id = vals.get('payment_token_id')

        if payment_token_id:
            payment_token = self.env['payment.token'].sudo().browse(payment_token_id)

            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(acquirer_id)
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise ValidationError(_('Invalid token found! Token acquirer %s != %s') % (
                    payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise ValidationError(_('Invalid token found! Token partner %s != %s') % (
                    payment_token.partner.name, partner.name))
            else:
                acquirer = payment_token.acquirer_id

        # Check an acquirer is there.
        if not acquirer_id and not acquirer:
            raise ValidationError(_('A payment acquirer is required to create a transaction.'))

        if not acquirer:
            acquirer = self.env['payment.acquirer'].browse(acquirer_id)

        # Check a journal is set on acquirer.
        if not acquirer.journal_id:
            raise ValidationError(_('A journal must be specified of the acquirer %s.' % acquirer.name))

        if not acquirer_id and acquirer:
            vals['acquirer_id'] = acquirer.id

        vals.update({
            'amount': self[0].deposit_amount,
            'currency_id': currency.id,
            'partner_id': partner.id,
            'invoice_ids': [(6, 0, self.ids)],
            'invoice_deposit': True
        })

        transaction = self.env['payment.transaction'].create(vals)

        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()

        return transaction
  