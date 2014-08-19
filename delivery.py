from openerp.osv import osv
import datetime
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
        ET.SubElement(temp, "ROUTE").text = 'ESS'
        ET.SubElement(temp, "EXTDELV_NO").text = delivery.order_reference

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
        ET.SubElement(temp, "TIMETYPE").text = 'WSHDRWADAT'
        ET.SubElement(temp, "TIMESTAMP_UTC").text = datetime.datetime.strptime(delivery.min_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M%S')
        ET.SubElement(temp, "TIMEZONE").text = 'CET'

        # Line items
        for i, line in enumerate(delivery.move_lines):
            temp = ET.SubElement(header, "E1BPOBDLVITEM")
            temp.set('SEGMENT','1')
            ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
            ET.SubElement(temp, "ITM_NUMBER").text = str(i+1)
            ET.SubElement(temp, "MATERIAL").text = line.product_id.ean13
            ET.SubElement(temp, "DLV_QTY_STOCK").text = str(int(line.product_qty))
            ET.SubElement(temp, "BOMEXPL_NO").text = '5'

            temp = ET.SubElement(header, "E1BPOBDLVITEMORG")
            temp.set('SEGMENT','1')
            ET.SubElement(temp, "DELIV_NUMB").text = delivery.name
            ET.SubElement(temp, "ITM_NUMBER").text = str(i+1)
            ET.SubElement(temp, "STGE_LOC").text = '0'          #????????????????????????

        return root


        #ET.SubElement(root, "Incoterm").text = delivery.incoterm.name or ''
        #ET.SubElement(root, "Instruction1").text = delivery.instruction1
        #ET.SubElement(root, "Instruction2").text = delivery.instruction2
        #ET.SubElement(root, "CrossdockOverrule").text = delivery.crossdock_overrule
        #ET.SubElement(root, "GroupageOverrule").text = delivery.groupage_overrule





    def edi_essers_validator(self, cr, uid, ids, context):
        return True



    def edi_import_thr(self, cr, uid, ids, context):
        return True



