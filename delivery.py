from openerp.osv import osv
import datetime
import xmltodict
from openerp.tools.translate import _
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class stock_picking_out(osv.Model):
    _name = "stock.picking.out"
    _inherit = "stock.picking.out"

    def essers_partner_resolver(self, cr, uid, ids, context):
        raise osv.except_osv(_('Warning!'), _("Resolving is not supported for this flow."))

    def send_essers_out(self, cr, uid, items, context=None):
        ''' stock.picking.out:send_essers_out()
         -----------------------------------
         This method will perform the export of a delivery
         order, the Essers version. Only deliveries that
         are in state 'assigned' may be passed to this method,
         otherwise an error will occur.
         ---------------------------------------------------- '''


        edi_db = self.pool.get('clubit.tools.edi.document.outgoing')

        # Get the selected items
        # ----------------------
        pickings = [x['id'] for x in items]
        pickings = self.browse(cr, uid, pickings, context=context)


        # Loop over all pickings to check if their
        # collective states allow for EDI processing
        # ------------------------------------------
        nope = ""
        for pick in pickings:
            if pick.state != 'assigned':
                nope += pick.name + ', '
        if nope:
            raise osv.except_osv(_('Warning!'), _("Not all documents had state 'assigned'. Please exclude the following documents: {!s}").format(nope))


        # Actual processing of all the deliveries
        # ---------------------------------------
        for pick in pickings:
            content = self.edi_export_essers(cr, uid, pick, None, context)
            partner_id = [x['partner_id'] for x in items if x['id'] == pick.id][0]
            result = edi_db.create_from_content(cr, uid, pick.name, content, partner_id, 'stock.picking.out', 'send_essers_out', type='XML')
            if result != True:
                raise osv.except_osv(_('Error!'), _("Something went wrong while trying to create one of the EDI documents. Please contact your system administrator. Error given: {!s}").format(result))


    def edi_export_essers(self, cr, uid, delivery, edi_struct=None, context=None):

        sale_db = self.pool.get('sale.order')
        move_db = self.pool.get('stock.move')
        sale_order = 0
        if delivery.origin:
            sale_order = sale_db.search(cr, uid,[('name', '=', delivery.origin)])
            if sale_order:
                sale_order = sale_db.browse(cr, uid, sale_order[0])


        # Actual EDI conversion of the delivery
        # -------------------------------------
        root = ET.Element("SHP_OBDLV_SAVE_REPLICA02")
        idoc = ET.SubElement(root, "IDOC")
        idoc.set('BEGIN','1')
        header = ET.SubElement(idoc, "EDI_DC40")
        header.set('SEGMENT','1')
        ET.SubElement(header, "MESTYP").text = 'SHP_OBDLV_SAVE_REPLICA'
        header = ET.SubElement(idoc, "E1SHP_OBDLV_SAVE_REPLICA")
        header.set('SEGMENT','1')

        temp = ET.SubElement(header, "E1BPOBDLVHDR")
        temp.set('SEGMENT','1')
        ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
        ET.SubElement(temp, "EXTDELV_NO").text = delivery.order_reference

        if delivery.incoterm:
            if delivery.incoterm.code == 'EXW':
                ET.SubElement(temp, "ROUTE").text = 'PICKUP'
            else:
                ET.SubElement(temp, "ROUTE").text = 'ESSERS'


        # Sold to
        if sale_order:
            temp = ET.SubElement(header, "E1BPDLVPARTNER")
            temp.set('SEGMENT','1')
            ET.SubElement(temp, "ADDRESS_NO").text = '1'
            ET.SubElement(temp, "PARTN_ROLE").text = 'AG'
            ET.SubElement(temp, "PARTNER_NO").text = sale_order.partner_id.reference
            temp = ET.SubElement(header, "E1BPADR1")
            temp.set('SEGMENT','1')
            ET.SubElement(temp, "ADDRESS_NO").text = '1'
            ET.SubElement(temp, "NAME").text = sale_order.partner_id.name
            ET.SubElement(temp, "CITY").text = sale_order.partner_id.city
            ET.SubElement(temp, "POSTL_COD1").text = sale_order.partner_id.zip
            ET.SubElement(temp, "STREET").text = sale_order.partner_id.street
            ET.SubElement(temp, "STR_SUPPL1").text = sale_order.partner_id.street2
            ET.SubElement(temp, "COUNTRY").text = sale_order.partner_id.country_id.code
            ET.SubElement(temp, "LANGU").text = sale_order.partner_id.lang[3:5] or 'NL'

        # Ship to
        temp = ET.SubElement(header, "E1BPDLVPARTNER")
        temp.set('SEGMENT','1')
        ET.SubElement(temp, "ADDRESS_NO").text = '2'
        ET.SubElement(temp, "PARTN_ROLE").text = 'WE'
        ET.SubElement(temp, "PARTNER_NO").text = delivery.partner_id.reference
        temp = ET.SubElement(header, "E1BPADR1")
        temp.set('SEGMENT','1')
        ET.SubElement(temp, "ADDRESS_NO").text = '2'
        ET.SubElement(temp, "NAME").text = delivery.partner_id.name
        ET.SubElement(temp, "CITY").text = delivery.partner_id.city
        ET.SubElement(temp, "POSTL_COD1").text = delivery.partner_id.zip
        ET.SubElement(temp, "STREET").text = delivery.partner_id.street
        ET.SubElement(temp, "STR_SUPPL1").text = delivery.partner_id.street2
        ET.SubElement(temp, "COUNTRY").text = delivery.partner_id.country_id.code
        ET.SubElement(temp, "LANGU").text = delivery.partner_id.lang[3:5] or 'NL'

        # Timing info
        temp = ET.SubElement(header, "E1BPDLVDEADLN")
        temp.set('SEGMENT','1')
        ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
        ET.SubElement(temp, "TIMETYPE").text = 'WSHDRLFDAT'
        ET.SubElement(temp, "TIMESTAMP_UTC").text = datetime.datetime.strptime(delivery.min_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M%S')
        ET.SubElement(temp, "TIMEZONE").text = 'CET'

        # Crossdock
        temp = ET.SubElement(header, "E1BPEXT")
        temp.set('SEGMENT','1')
        ET.SubElement(temp, "PARAM").text = delivery.name + '000000'
        ET.SubElement(temp, "ROW").text = '0'
        ET.SubElement(temp, "FIELD").text = 'SSP'
        if delivery.crossdock_overrule == 'yes':
            ET.SubElement(temp, "VALUE").text = 'Y'
        else:
            ET.SubElement(temp, "VALUE").text = 'N'

        # Groupage
        temp = ET.SubElement(header, "E1BPEXT")
        temp.set('SEGMENT','1')
        ET.SubElement(temp, "PARAM").text = delivery.name + '000000'
        ET.SubElement(temp, "ROW").text = '0'
        ET.SubElement(temp, "FIELD").text = 'SOP'
        if delivery.groupage_overrule == 'yes':
            ET.SubElement(temp, "VALUE").text = 'N'
        else:
            ET.SubElement(temp, "VALUE").text = 'Y'


        # Line items
        i = 0
        for line in delivery.move_lines:

            if line.state != 'assigned':
                continue

            i = i + 100
            temp = ET.SubElement(header, "E1BPOBDLVITEM")
            temp.set('SEGMENT','1')
            ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
            ET.SubElement(temp, "ITM_NUMBER").text = "%06d" % (i,)
            ET.SubElement(temp, "MATERIAL").text = line.product_id.name
            ET.SubElement(temp, "DLV_QTY_STOCK").text = str(int(line.product_qty))

            if not line.product_id.bom_ids:
                ET.SubElement(temp, "BOMEXPL_NO").text = '0'
            else:
                ET.SubElement(temp, "BOMEXPL_NO").text = '5'
                j = i
                for bom in line.product_id.bom_ids[0].bom_lines:
                    j = j + 1
                    temp = ET.SubElement(header, "E1BPOBDLVITEM")
                    temp.set('SEGMENT','1')
                    ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
                    ET.SubElement(temp, "ITM_NUMBER").text = "%06d" % (j,)
                    ET.SubElement(temp, "MATERIAL").text = bom.product_id.ean13
                    ET.SubElement(temp, "DLV_QTY_STOCK").text = str(int(bom.product_qty))
                    ET.SubElement(temp, "BOMEXPL_NO").text = '6'

                    temp = ET.SubElement(header, "E1BPOBDLVITEMORG")
                    temp.set('SEGMENT','1')
                    ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
                    ET.SubElement(temp, "ITM_NUMBER").text = "%06d" % (j,)
                    ET.SubElement(temp, "STGE_LOC").text = '0'


            temp = ET.SubElement(header, "E1BPOBDLVITEMORG")
            temp.set('SEGMENT','1')
            ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
            ET.SubElement(temp, "ITM_NUMBER").text = "%06d" % (i,)
            if not line.storage_location:
                ET.SubElement(temp, "STGE_LOC").text = '0'
            else:
                ET.SubElement(temp, "STGE_LOC").text = line.storage_location


            # Write this EDI sequence to the delivery for referencing the response
            # --------------------------------------------------------------------
            move_db.write(cr, uid, line.id, {'edi_sequence': "%06d" % (i,)}, context=context)

        return root



    def edi_essers_validator(self, cr, uid, ids, context):

        # Read the EDI Document
        # ---------------------
        edi_db = self.pool.get('clubit.tools.edi.document.incoming')
        document = edi_db.browse(cr, uid, ids, context)

        # Convert the document to JSON
        # ----------------------------
        try:
            content = xmltodict.parse(document.content)
            content = content['IDOC']['E1SHP_OBDLV_CONFIRM_DECENTR']
        except Exception:
            edi_db.message_post(cr, uid, document.id, body='Error found: content is not valid XML or the structure deviates from what is expected.')
            return False

        # Check if we can find the delivery
        # ---------------------------------
        delivery = self.search(cr, uid, [('name','=',content['DELIVERY'])], context=context)
        if not delivery:
            edi_db.message_post(cr, uid, document.id, body='Error found: could not find the referenced delivery: {!s}.'.format(content['DELIVERY']))
            return False
        delivery = self.browse(cr, uid, delivery[0], context=context)

        # Check if all the line items match
        # ---------------------------------
        if not content['E1BPOBDLVITEMCON']:
            edi_db.message_post(cr, uid, document.id, body='Error found: no line items provided.')
            return False
        for edi_line in content['E1BPOBDLVITEMCON']:
            if not edi_line['DELIV_ITEM']:
                edi_db.message_post(cr, uid, document.id, body='Error found: line item provided without an identifier.')
                return False
            if not edi_line['MATERIAL']:
                edi_db.message_post(cr, uid, document.id, body='Error found: line item provided without a material identifier.')
                return False
            if not edi_line['DLV_QTY_IMUNIT']:
                edi_db.message_post(cr, uid, document.id, body='Error found: line item provided without a quantity.')
                return False

            move_line = [x for x in delivery.move_lines if x.edi_sequence == edi_line['DELIV_ITEM']]
            if not move_line: # skip BOM explosion lines
                continue
            move_line = move_line[0]
            if move_line.product_id.ean13 <> edi_line['MATERIAL']:
                edi_db.message_post(cr, uid, document.id, body='Error found: line mentioned with EDI sequence {!s} has a different material.'.format(edi_line['DELIV_ITEM']))
                return False

        return True



    def receive_essers_in(self, cr, uid, ids, context):


        # Attempt to validate the file right before processing
        # ----------------------------------------------------
        edi_db = self.pool.get('clubit.tools.edi.document.incoming')
        if not self.edi_essers_validator(cr, uid, ids, context):
            edi_db.message_post(cr, uid, ids, body='Error found: during processing, the document was found invalid.')
            return False

        document = edi_db.browse(cr, uid, ids, context)
        content = xmltodict.parse(document.content)
        content = content['IDOC']['E1SHP_OBDLV_CONFIRM_DECENTR']

        # Process the EDI Document
        # ------------------------
        delivery = self.search(cr, uid, [('name','=', content['DELIVERY'])], context=context)
        delivery = self.browse(cr, uid, delivery[0], context=context)

        vals = {}
        for edi_line in content['E1BPOBDLVITEMCON']:
            move_line = [x for x in delivery.move_lines if x.edi_sequence == edi_line['DELIV_ITEM']]
            if not move_line: #skip BOM explosion lines
                continue
            move_line = move_line[0]

            move = {
                    'prodlot_id': False,
                    'product_id': move_line.product_id.id,
                    'product_uom': move_line.product_uom.id,
                    'product_qty': float(edi_line['DLV_QTY_IMUNIT'])}
            vals["move" + str(move_line.id)] = move


        # Make the call to do_partial() to set the document to 'done'
        # -----------------------------------------------------------
        try:
            self.pool.get('stock.picking').do_partial(cr, uid, [delivery.id], vals, context=context)
        except Exception as e:
            return False
        return True
