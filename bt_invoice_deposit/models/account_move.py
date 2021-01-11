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
    
    
    @api.model
    def create(self, values):
        if 'deposit_amount' not in values:
            values['deposit_amount'] = self.amount_total/2
        return super(AccountMove, self).create(values)
    
    def write(self, values):
        if self.state == 'draft' and not self.deposit_amount and 'deposit_amount' not in values:
            values['deposit_amount'] = self.amount_total/2
        return super(AccountMove, self).write(values)
    
    def deduct_deposit(self):
        for invoice_obj in self:
            deposit = self.env['bt.payment.deposit'].search([('invoice_id', '=', invoice_obj.id)])
            
            deposit_journal = self.env['bt.deposit.journal'].search([])
            if deposit and deposit_journal and deposit_journal[0].journal_id.default_debit_account_id and invoice_obj.partner_id and invoice_obj.partner_id.property_account_receivable_id:
#                 payment_vals = {
#                     'company_id': invoice_obj.company_id and invoice_obj.company_id.id or False,
#                     'partner_id': invoice_obj.partner_id and invoice_obj.partner_id.id or False,
#                     'amount': deposit.payment_amount,
#                     'currency_id': invoice_obj.currency_id.id,
#                     'journal_id': deposit_journal[0].journal_id.id,
#                     'communication': 'Deposit: ' + invoice_obj.name,
#                     'payment_date': fields.Date.today(),
#                     'payment_type': 'inbound',
#                     'partner_type': 'customer',
#                     'payment_method_id': deposit_journal[0].journal_id.inbound_payment_method_ids and deposit_journal[0].journal_id.inbound_payment_method_ids[0].id or False
#                     }
#                 payment = self.env['account.payment']\
#                         .with_context(active_ids=[deposit.id], active_model='bt.payment.deposit', active_id=deposit.id)\
#                         .create(payment_vals)
#                         
#                 if not payment.name:
#                     sequence_code = 'account.payment.customer.invoice'
#                     payment.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=payment.payment_date)

                move_vals = {
                    'date': fields.Date.today(),
                    'ref': 'Deposit: ' + invoice_obj.name,
                    'journal_id': deposit_journal[0].journal_id.id,
                    'currency_id': invoice_obj.currency_id and invoice_obj.currency_id.id or False,
                    'partner_id': invoice_obj.partner_id and invoice_obj.partner_id.id or False,
                    'type': 'entry',
                    'line_ids': [
                        (0, 0, {
                            'name': invoice_obj.name,
    #                         'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
#                             'currency_id': invoice_obj.currency_id and invoice_obj.currency_id.id or False,
                            'debit': 0.0,
                            'credit': deposit.payment_amount,
                            'date_maturity': fields.Date.today(),
                            'partner_id': invoice_obj.partner_id and invoice_obj.partner_id.id or False,
                            'account_id': invoice_obj.partner_id.property_account_receivable_id.id, #### customer account receivable
                        
                        }),
                        (0, 0, {
                            'name': 'Deposit',
    #                         'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
#                             'currency_id': invoice_obj.currency_id and invoice_obj.currency_id.id or False,
                            'debit': deposit.payment_amount,
                            'credit': 0.0,
                            'date_maturity': fields.Date.today(),
                            'partner_id': invoice_obj.partner_id and invoice_obj.partner_id.id or False,
                            'account_id': deposit_journal[0].journal_id.default_debit_account_id.id,  #### customer deposit
                        }),
                    ],
                }
                
                moves = self.env['account.move'].create(move_vals)
                moves.post()
                deposit.deduct_move_id = moves.id
                
                (deposit.move_id + moves).line_ids \
                        .filtered(lambda line: not line.reconciled and line.account_id == deposit_journal[0].journal_id.default_debit_account_id) \
                        .reconcile()
                (invoice_obj + moves).line_ids \
                        .filtered(lambda line: not line.reconciled and line.account_id == invoice_obj.partner_id.property_account_receivable_id) \
                        .reconcile()
                invoice_obj.deposit_exist = False
                invoice_obj.message_post(body=_("Customer Advance Deducted"))
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
    
    
    ### For inv pdf
    def _get_payment_ref(self, account_payment_id):
        self.ensure_one()
        if account_payment_id:
            name = account_payment_id and self.env['account.payment'].browse(account_payment_id).name or ''
            return name or ''
        
        deposit = self.env['bt.payment.deposit'].search([('invoice_id', '=', self.id)])
        if deposit:
            return deposit.payment_id and deposit.payment_id.name or ''
    
  