# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"
    
    update_invoice = fields.Boolean(string='Update Invoice', default=False)
    
        
###  < ALTER TABLE account_invoice_line ADD COLUMN new_move_line_id integer; >

    def action_update_move_line_vals(self):
        print('Update000000000000000000000000000000000000000000000000000000000000000')
        moves = self.env['account.move'].search([])
        for move in moves:
            print('mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm',move.id)
            self._cr.execute('''
                SELECT id 
                  FROM account_invoice
                 WHERE move_id IN %s
            ''', [tuple([move.id])])
            invoice_id = [r[0] for r in self._cr.fetchall()]
            print ("---------invoice_id",invoice_id,move.id)
            
            if invoice_id:
                self._cr.execute('''
                        SELECT name,sequence,display_type 
                          FROM account_invoice_line
                         WHERE invoice_id IN %s and display_type is not null;
                    ''', [tuple(invoice_id)])
                invoice_line_section_list = self._cr.dictfetchall()
                if invoice_line_section_list:
                    for invc_line_section in invoice_line_section_list:
                        section_name = invc_line_section.get('name', False)
                        section_sequence = invc_line_section.get('sequence', 0)
                        section_display_type = invc_line_section.get('display_type', False)
                        
                        query = '''
                                INSERT INTO account_move_line
                                (name,sequence,display_type,move_id)
                                VALUES (%s, %s, %s, %s)
                            '''
                        query_params = [section_name,section_sequence,section_display_type,move.id]
                        self._cr.execute(query, query_params)
                        
            
            ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
            sequence_list = []
            line_len = len(move.line_ids) or 0
            for line in move.line_ids:
                vals = {'debit': line.debit, 'credit': line.credit, 'amount_currency': line.amount_currency}
                
                invoice_line_vals = {}
                if invoice_id and line.account_id:
                    query = '''
                            SELECT id,discount,is_rounding_line,partner_id,sequence
                              FROM account_invoice_line
                            WHERE invoice_id IN %s AND
                                  account_id = %s AND
                                  quantity = %s  
                        '''
                    query_params = [tuple(invoice_id),line.account_id.id,line.quantity]
                    if line.product_id:
                        query += '''
                            AND product_id = %s 
                        '''
                        query_params.append(line.product_id.id)
                    self._cr.execute(query, query_params)
                    invoice_line_vals_list = self._cr.dictfetchall()
                    sequence_sameline_list = []
                    if len(invoice_line_vals_list) > 1:
                        for invc_line_vals in invoice_line_vals_list:
                            sequence_sameline_list.append(invc_line_vals.get('sequence'))
                            if invc_line_vals.get('sequence', False) == line.sequence:
                                invoice_line_vals = invc_line_vals
                                break
                        if not invoice_line_vals:
                            invoice_line_vals = invoice_line_vals_list and invoice_line_vals_list[0] or {}
                    else:
                        invoice_line_vals = invoice_line_vals_list and invoice_line_vals_list[0] or {}
                    
                    
                    balance = line.currency_id and line.amount_currency or line.debit - line.credit
    #                 if invoice_line_vals.get('discount', False):
    #                     line.discount = invoice_line_vals.get('discount', False)
                    price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
                    to_write = line._get_fields_onchange_balance(
                        quantity=line.quantity,
                        discount = invoice_line_vals.get('discount', False) or 0.0,
                        balance=balance,
                    )
                    p_unit = to_write.get('price_unit', line.price_unit)
                    p_unit = p_unit < 0 and -p_unit or p_unit
                    to_write.update({'price_unit': p_unit})
                    to_write.update(line._get_price_total_and_subtotal(
                        price_unit=p_unit,
                        quantity=to_write.get('quantity', line.quantity),
                        discount=to_write.get('discount', line.discount),
                    ))
                    if invoice_line_vals.get('discount', False):
    #                     line.discount = invoice_line_vals.get('discount', False)
                        to_write.update({'discount': invoice_line_vals.get('discount', False)})
                    line.write(to_write)
                    
                    sequence_update = invoice_line_vals.get('sequence') or line_len+1
                    print('ssssssssssssssssssssssssss',sequence_list,sequence_sameline_list)
                    if sequence_list and sequence_sameline_list:
                        for sequence_sameline in sequence_sameline_list:
                            if sequence_sameline not in sequence_list:
                                sequence_update = sequence_sameline
                    
                    query = """
                        UPDATE account_move_line
                            SET is_rounding_line = %s
                        """
                    query_params = [invoice_line_vals.get('is_rounding_line',False)]
                    if sequence_update:
                        sequence_list.append(sequence_update)
                        query += ",sequence = %s"
                        query_params.append(sequence_update)
                    if invoice_line_vals.get('partner_id',False):
                        query += ",partner_id = %s"
                        query_params.append(invoice_line_vals.get('partner_id',False))
                        
                    query += '''WHERE id in %s
                    '''
                    query_params.append(tuple([line.id],))
                             
                            
    #                 query_params.append(tuple([invoice_res.get('move_id',False)],))
                    self.env.cr.execute(query, query_params)
                    
                    invc_query = '''
                        UPDATE account_invoice_line
                            SET new_move_line_id = %s
                        WHERE invoice_id IN %s AND
                              account_id = %s AND
                              quantity = %s 
                        '''
                    invc_query_params = [line.id,tuple(invoice_id),line.account_id.id,line.quantity]
                    if line.product_id:
                        invc_query += '''
                            AND product_id = %s 
                        '''
                        invc_query_params.append(line.product_id.id)
                    self.env.cr.execute(invc_query, invc_query_params)
                    

    def action_update_account_move_data(self):
        print('Update1111111111111111111111111111111111111111111111')
        self._cr.execute('''
             SELECT move_id,type,
                 reference,partner_bank_id
             FROM account_invoice
             WHERE move_id IS NOT NULL
             ''')
#              ''', [tuple([1120])])
        
        query_res = self._cr.dictfetchall()
        account_move_ids = self.env['account.move'].search([]).ids
        for invoice_res in query_res:
            if invoice_res.get('move_id', False) in account_move_ids:
                query = """
                    UPDATE account_move 
                    SET type = %s,
                    invoice_payment_ref =  %s,
                    invoice_partner_bank_id =  %s
                    """
                query_params = [
                        invoice_res.get('type',False), 
                        invoice_res.get('reference',False), 
                        invoice_res.get('partner_bank_id',False), 
                    ]
                query += """
                    WHERE id in %s
                    """
#                 query_params.append(tuple([1120]))
                query_params.append(tuple([invoice_res.get('move_id',False)],))
                self.env.cr.execute(query, query_params)


    def action_update_move_vals(self):
        print('Update222222222222222222222222222222222222222222222')
#         self._cr.execute('''
#              SELECT id
#              FROM account_invoice
#              WHERE move_id IS NOT NULL
#              ''')
#         
#         query_res = self._cr.dictfetchall()
#         for invoice_res in query_res:
#             if invoice_res.get('id', False):
#                 inv = self.env['account.invoice'].browse(invoice_res.get('id', False))
#                 inv_x_studio_field_jPB6m = inv.x_studio_field_jPB6m
#                 print('iiiiiiiiiiiiiiiiiiiiiiiiiiii',inv,inv_x_studio_field_jPB6m)
#                 inv.move_id.inv_x_studio_field_jPB6m = inv_x_studio_field_jPB6m
#                 print('iiiiiiiiiiiiiiiiiiiiiiiiiiii',inv.move_id,inv.move_id.inv_x_studio_field_jPB6m)
        
        move_objs = self.env['account.move'].search([])
        for move in move_objs:
            print('mmmmmmmmmmmmmm222222222222222222222222222222222222',move.id)
            self._cr.execute('''
                SELECT payment_term_id,date_invoice,date_due,partner_bank_id,
                    name,partner_shipping_id,team_id,
                    incoterm_id,fiscal_position_id
                FROM account_invoice
                WHERE move_id IN %s 
            ''', [tuple([move.id])])
            invoice_vals = self._cr.dictfetchall()
            for vals in invoice_vals:
                query = """
                    UPDATE account_move 
                    SET invoice_date = %s,
                        invoice_payment_term_id = %s,
                        invoice_date_due = %s,
                        invoice_partner_bank_id = %s,
                        ref = %s,
                        partner_shipping_id = %s,
                        team_id = %s,
                        invoice_incoterm_id = %s,
                        fiscal_position_id = %s
                    """
                query_params = [
                        vals.get('date_invoice',False), vals.get('payment_term_id',False), 
                        vals.get('date_due',False),
                        vals.get('partner_bank_id',False),
                        vals.get('name',False),
                        vals.get('partner_shipping_id',False),
                        vals.get('team_id',False),
                        vals.get('incoterm_id',False),
                        vals.get('fiscal_position_id',False)
                    ]
                query += """
                    WHERE id in %s
                    """
                query_params.append(tuple([move.id],))
                self.env.cr.execute(query, query_params)


    def action_update_missing_move_vals(self):
        print('Update3333333333333333333333333333333333333333333333333333333333')
        move_pool = self.env['account.move']
        query = '''
                SELECT id,move_id,user_id,name,sent,origin,refund_invoice_id
                  FROM account_invoice
                WHERE move_id is not NULL
                and move_id in (SELECT id FROM account_move where id=move_id)
            '''
#         query_params = [tuple([5820],)]
        self._cr.execute(query)
        invoice_vals_list = self._cr.dictfetchall()
        for invoice_vals in invoice_vals_list:
            move_obj = move_pool.browse(invoice_vals['move_id'])
            move_vals = {
                'invoice_payment_ref': invoice_vals.get('name', False),
                'invoice_sent': invoice_vals['sent'],
                'invoice_origin': invoice_vals['origin'],
                }
            if invoice_vals.get('user_id', False):
                move_vals.update({'invoice_user_id': invoice_vals.get('user_id', False)})
            if invoice_vals.get('refund_invoice_id', False):
                self._cr.execute('''
                        SELECT move_id 
                          FROM account_invoice
                        WHERE id = %s
                    ''', [invoice_vals['refund_invoice_id']])
                refund_move_id = [r[0] for r in self._cr.fetchall()]
                if refund_move_id and refund_move_id[0]:
                    move_vals.update({'reversed_entry_id': refund_move_id[0]})
            move_obj.write(move_vals)


                
    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state','update_invoice')
    def _compute_amount(self):
        print('Update44444444444444444444444444441111111111111111111111')
        invoice_ids = [move.id for move in self if move.id and move.is_invoice(include_receipts=True)]
        self.env['account.payment'].flush(['state'])
        if invoice_ids:
            self._cr.execute(
                '''
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                        OR
                        (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                ''', [tuple(invoice_ids)]
            )
            in_payment_set = set(res[0] for res in self._cr.fetchall())
        else:
            in_payment_set = {}
        
        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()
            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===
                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.type == 'entry' else -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
            is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual
            # Compute 'invoice_payment_state'.
            if move.type == 'entry':
                move.invoice_payment_state = False
            elif move.state == 'posted' and is_paid:
                if move.id in in_payment_set:
                    move.invoice_payment_state = 'in_payment'
                else:
                    move.invoice_payment_state = 'paid'
            else:
                move.invoice_payment_state = 'not_paid'
                
                
    def action_check_function(self):
        print('Update44444444444444444444444444444444444444444444444')
        move_objs = self.env['account.move'].search([])
        for move in move_objs:
            for line in move.line_ids:
                if line.account_id.user_type_id.type in ('receivable', 'payable') or line.tax_line_id:
                    line.exclude_from_invoice_tab = True
                else:
                    line.exclude_from_invoice_tab = False
                print('eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',line.exclude_from_invoice_tab)
            move.update_invoice = True


######## Run the below queries before Update5 :-

#    alter table sale_order_line_invoice_rel add old_invoice_line_id integer;
#
#    update sale_order_line_invoice_rel set old_invoice_line_id=invoice_line_id;
# 
#    CREATE TABLE sale_order_line_invoice_rel_old AS TABLE  sale_order_line_invoice_rel WITH NO DATA;
# 
#    INSERT INTO sale_order_line_invoice_rel_old (select * from sale_order_line_invoice_rel);


    def action_update_move_line_sale_links(self):
        print('Update5555555555555555555555555555555555555555555555555555')
#         self._cr.execute('''
#                     SELECT * 
#                       FROM sale_order_line_invoice_rel
#                 ''')
#         sale_invoice_links = self._cr.dictfetchall()
        ###########################Below Sale Orders have multiple invoices but these are not getting updated properly
#         Multi_invoice_sales = (388, 233, 191, 183, 174, 115, 107, 106, 105, 100, 29, 23, 22, 10, 2, 160)
#         sale_orders = self.env['sale.order'].search([('id','not in',[206,7,8,10,14,17,22,39,167,224,247,117,160])])
        sale_orders = self.env['sale.order'].search([])
#         sale_orders = self.env['sale.order'].search([('id','=',97)])
#         sale_orders = self.env['sale.order'].search([('id','=',97)])
        sale_order_line_dict = {}
        invc_line_without_line_dict = {}
        old_invc_line_id_dict = {}
        uom_not_same = []
        for sale_order in sale_orders:
            invoice_line_count = 0
            for sale_order_line in sale_order.order_line:
                new_move_line_ids = []
                without_ids = []
                old_invc_line_ids = []
                if sale_order_line.product_uom.category_id != sale_order_line.product_id.uom_id.category_id:
                        uom_not_same.append(sale_order_line.id)
                invoice_lines = sale_order_line.invoice_lines and sale_order_line.invoice_lines.ids or []
                if not invoice_lines:
                    self._cr.execute('''
                                SELECT invoice_line_id 
                                  FROM sale_order_line_invoice_rel
                                WHERE order_line_id = %s ORDER BY invoice_line_id
                            ''', [sale_order_line.id])
                    invoice_lines = [r[0] for r in self._cr.fetchall()]
                for invc_line_id in invoice_lines:
                    self._cr.execute('''
                        SELECT new_move_line_id 
                          FROM account_invoice_line
                         WHERE id = %s AND new_move_line_id is not NULL
                    ''', [invc_line_id])
                    move_line_id = [r[0] for r in self._cr.fetchall()]
                    if move_line_id and move_line_id[0]:
                        new_move_line_ids.extend(move_line_id)
                        old_invc_line_ids.append(invc_line_id) 
                        old_invc_line_id_dict.update({sale_order_line.id: {move_line_id[0]: invc_line_id}})
#                         old_invc_line_id_dict.update({sale_order_line.id: invc_line.id})
                    else:
                        without_ids.append(invc_line_id)
                        query = '''
                                SELECT id,invoice_id,account_id,price_subtotal,quantity,product_id
                                  FROM account_invoice_line
                                WHERE id = %s AND invoice_id is not NULL
                            '''
                        query_params = [invc_line_id]
                        self._cr.execute(query, query_params)
                        invoice_line_vals_list = self._cr.dictfetchall()
                        for invoice_line_vals in invoice_line_vals_list:
                            if invoice_line_vals.get('invoice_id', False):
                                self._cr.execute('''
                                    SELECT move_id 
                                      FROM account_invoice
                                    WHERE id = %s AND move_id is not NULL AND partner_id = %s
                                ''', [invoice_line_vals.get('invoice_id', False),sale_order.partner_id.id])
                                move_id = [r[0] for r in self._cr.fetchall()]
                                if move_id and move_id[0]:
                                    query = '''
                                            SELECT id
                                              FROM account_move_line
                                            WHERE move_id IN %s AND
                                                  account_id = %s AND
                                                  quantity = %s  
                                        '''
                                    query_params = [tuple(move_id),invoice_line_vals.get('account_id',False),invoice_line_vals.get('quantity',False)]
                                    if invoice_line_vals.get('product_id',False):
                                        query += '''
                                            AND product_id = %s 
                                        '''
                                        query_params.append(invoice_line_vals.get('product_id',False))
                                    self._cr.execute(query, query_params)
                                    move_line_id = [r[0] for r in self._cr.fetchall()]
                                    if not move_line_id or move_line_id == [None]:
                                        query = '''
                                                SELECT id
                                                  FROM account_move_line
                                                WHERE move_id IN %s AND
                                                      price_subtotal = %s AND
                                                      quantity = %s  
                                            '''
                                        query_params = [tuple(move_id),round(invoice_line_vals.get('price_subtotal',False),2),invoice_line_vals.get('quantity',False)]
                                        if invoice_line_vals.get('product_id',False):
                                            query += '''
                                                AND product_id = %s 
                                            '''
                                            query_params.append(invoice_line_vals.get('product_id',False))
                                        self._cr.execute(query, query_params)
                                        move_line_id = [r[0] for r in self._cr.fetchall()]
                                        if not move_line_id or move_line_id == [None] and invoice_line_vals.get('price_subtotal',False) == 0:
                                            query = '''
                                                SELECT id
                                                  FROM account_move_line
                                                WHERE move_id IN %s AND
                                                      price_subtotal is NULL AND
                                                      quantity = %s  
                                            '''
                                            query_params = [tuple(move_id),invoice_line_vals.get('quantity',False)]
                                            if invoice_line_vals.get('product_id',False):
                                                query += '''
                                                    AND product_id = %s 
                                                '''
                                                query_params.append(invoice_line_vals.get('product_id',False))
                                            query += '''
                                                    ORDER BY id
                                                '''
                                            self._cr.execute(query, query_params)
                                            move_line_id = [r[0] for r in self._cr.fetchall()]
                                            if len(move_line_id) > 1:
                                                move_line_id = [move_line_id[invoice_line_count]]
                                                invoice_line_count += 1 
                                    if move_line_id and move_line_id[0]:
                                        new_move_line_ids.append(move_line_id[0])
                                        old_invc_line_ids.append(invc_line_id) 
                                        old_invc_line_id_dict.update({sale_order_line.id: {move_line_id[0]: invc_line_id}})
                        
                invc_line_without_line_dict.update({sale_order_line.id: {sale_order.id: without_ids}})
#                 if new_move_line_ids:
                sale_order_line_dict.update({sale_order_line.id: new_move_line_ids})
                if new_move_line_ids:
                    sale_order_line.invoice_lines = [(6, 0, new_move_line_ids)]


        for old_sale_line in old_invc_line_id_dict:
            for move_line_id in old_invc_line_id_dict[old_sale_line]:
                if old_invc_line_id_dict[old_sale_line][move_line_id]:
                    query = '''
                            SELECT *
                              FROM sale_order_line_invoice_rel
                            WHERE order_line_id = %s AND
                            invoice_line_id = %s
                        '''
                    query_params = [old_sale_line,old_invc_line_id_dict[old_sale_line][move_line_id]]
                    self._cr.execute(query, query_params)
                    delete_vals = self._cr.dictfetchall()
                    
                    invc_query = '''
                        DELETE FROM sale_order_line_invoice_rel
                        WHERE order_line_id = %s AND
                            invoice_line_id = %s
                        '''
                    invc_query_params = [old_sale_line,old_invc_line_id_dict[old_sale_line][move_line_id]]
                    self.env.cr.execute(invc_query, invc_query_params)
                    
                    invc_query = '''
                        UPDATE sale_order_line_invoice_rel
                            SET old_invoice_line_id = %s
                        WHERE order_line_id = %s AND
                            invoice_line_id = %s
                        '''
                    invc_query_params = [old_invc_line_id_dict[old_sale_line][move_line_id],old_sale_line,move_line_id]
                    self.env.cr.execute(invc_query, invc_query_params)
        print ("-----------OK afterrrrrr.......>>>>")
        

    def action_update_move_line_purchase_line_links(self):
        print('Update66666666666666666666666666666666666666666666666666666')
        move_pool = self.env['account.move.line']
        query = '''
                SELECT id,new_move_line_id,purchase_line_id,invoice_id,account_id,quantity,price_subtotal,product_id
                  FROM account_invoice_line
                WHERE purchase_line_id is not NULL
            '''
#         query_params = [tuple([174,173,143,144,145,146,133,134,131,132],)]
        self._cr.execute(query)
        invoice_line_vals_list = self._cr.dictfetchall()
        print ("------countttttt",len(invoice_line_vals_list))
        for invoice_line in invoice_line_vals_list:
            if invoice_line.get('new_move_line_id',False):
                move_line_obj = move_pool.browse(invoice_line['new_move_line_id'])
                move_line_obj.purchase_line_id = invoice_line.get('purchase_line_id',False)
            elif invoice_line.get('invoice_id',False):
                move_line_id = False
                self._cr.execute('''
                        SELECT move_id 
                          FROM account_invoice
                        WHERE id = %s
                ''', [invoice_line.get('invoice_id',False)])
                move_id = [r[0] for r in self._cr.fetchall()]
                if move_id and move_id[0]:
                    query = '''
                            SELECT id
                              FROM account_move_line
                            WHERE move_id IN %s AND
                                  account_id = %s AND
                                  quantity = %s  
                        '''
                    query_params = [tuple(move_id),invoice_line.get('account_id',False),invoice_line.get('quantity',False)]
                    if invoice_line.get('product_id',False):
                        query += '''
                            AND product_id = %s 
                        '''
                        query_params.append(invoice_line.get('product_id',False))
                    self._cr.execute(query, query_params)
                    move_line_id = [r[0] for r in self._cr.fetchall()]
                    if not move_line_id or move_line_id == [None]:
                        query = '''
                                SELECT id
                                  FROM account_move_line
                                WHERE move_id IN %s AND
                                      price_subtotal = %s AND
                                      quantity = %s  
                            '''
                        query_params = [tuple(move_id),round(invoice_line.get('price_subtotal',False),2),invoice_line.get('quantity',False)]
                        if invoice_line.get('product_id',False):
                            query += '''
                                AND product_id = %s 
                            '''
                            query_params.append(invoice_line.get('product_id',False))
                        self._cr.execute(query, query_params)
                        move_line_id = [r[0] for r in self._cr.fetchall()]
                        if not move_line_id or move_line_id == [None] and invoice_line.get('price_subtotal',False) == 0:
                            query = '''
                                SELECT id
                                  FROM account_move_line
                                WHERE move_id IN %s AND
                                      price_subtotal is NULL AND
                                      quantity = %s  
                            '''
                            query_params = [tuple(move_id),invoice_line.get('quantity',False)]
                            if invoice_line.get('product_id',False):
                                query += '''
                                    AND product_id = %s 
                                '''
                                query_params.append(invoice_line.get('product_id',False))
                            self._cr.execute(query, query_params)
                            move_line_id = [r[0] for r in self._cr.fetchall()]
                if move_line_id:
                    move_line_obj = move_pool.browse(move_line_id)
                    move_line_obj.purchase_line_id = invoice_line.get('purchase_line_id',False)
                    
                    
    def action_update_attachments_data(self):
        print('Update77777777777777777777777777777777777777777777777')
        self._cr.execute('''select id,res_id from ir_attachment where res_model='account.invoice' ''')
        query_res = self._cr.dictfetchall()
        for attachment_res in query_res:
            self._cr.execute('''select move_id from account_invoice where id= %s''',(tuple([attachment_res.get('res_id')])))
            query_move_id = self._cr.dictfetchall()
            for move_id in query_move_id:
                self._cr.execute('''update ir_attachment set res_id=%s , res_model='account.move' where id=%s''',(tuple([move_id.get('move_id')]),tuple([attachment_res.get('id')])))
                
                
                
                
    def action_update_sale_invoice_links(self):
        print('Update88888888888888888888888888888888888888888888888888')
        sale_orders = self.env['sale.order'].search([('state', 'not in', ('draft', 'sent'))])
        for sale_order in sale_orders:
            for sale_order_line in sale_order.order_line:
                invoice_lines = []
                if sale_order_line.display_type:
                    print('sssssssssssssssssssssssssssssssssssss',sale_order_line.name,sale_order.id)
                    self._cr.execute('''
                        select id from account_move_line 
                            where name=%s and move_id in (select id from account_move 
                            where invoice_origin=(select name from sale_order where id=%s));
                            ''', [sale_order_line.name, sale_order.id])
                    invoice_lines = self._cr.fetchall()
                for invc_line_id in invoice_lines:
                    print('iiiiiiiiiiiiinnnnnnnnnnnnnnnnnnnvvvv',invc_line_id)
                    self._cr.execute('''update sale_order_line_invoice_rel set invoice_line_id=%s where old_invoice_line_id is not null and order_line_id=%s''', [invc_line_id,sale_order_line.id])

                    
                    

