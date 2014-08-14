from openerp.osv import osv
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

        # Actual EDI conversion of the delivery
        # -------------------------------------
        root = ET.Element("XXX_Delivery")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

        sale_order = sale_db.search(cr, uid,[('name', '=', delivery.origin)])
        if sale_order:
            sale_order = sale_db.browse(cr, uid, sale_order[0])
            ET.SubElement(root, "SoldTo").text = sale_order.partner_id.reference
            ET.SubElement(root, "SoldToAddress").text = sale_order.partner_id.street

        ET.SubElement(root, "ShipTo").text = delivery.partner_id.reference
        ET.SubElement(root, "ShipToAddress").text = delivery.partner_id.street
        ET.SubElement(root, "ExpectedDeliveryDate").text = delivery.min_date
        ET.SubElement(root, "Name").text = delivery.name
        ET.SubElement(root, "Reference").text = delivery.order_reference
        ET.SubElement(root, "Incoterm").text = delivery.incoterm.name or ''
        ET.SubElement(root, "Instruction1").text = delivery.instruction1
        ET.SubElement(root, "Instruction2").text = delivery.instruction2
        ET.SubElement(root, "CrossdockOverrule").text = delivery.crossdock_overrule
        ET.SubElement(root, "GroupageOverrule").text = delivery.groupage_overrule


        lines = ET.SubElement(root, "lines")
        for i, line in enumerate(delivery.move_lines):
            detail = ET.SubElement(lines, "line")
            ET.SubElement(detail, "Line").text = str(i+1)
            ET.SubElement(detail, "BOM").text = line.product_id.name
            ET.SubElement(detail, "Product").text = line.product_id.name
            ET.SubElement(detail, "Quantity").text = str(line.product_qty)
            ET.SubElement(detail, "Status").text = line.status_code


        return root





