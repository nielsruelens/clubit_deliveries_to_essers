from openerp.osv import osv
from openerp.tools.translate import _


##############################################################################
#
#    clubit.tools.edi.wizard.delivery.essers
#
#    Action handler class for delivery order outgoing (essers)
#
##############################################################################
class clubit_tools_edi_wizard_delivery_essers(osv.TransientModel):
    _inherit = ['clubit.tools.edi.wizard.outgoing']
    _name = 'clubit.tools.edi.wizard.delivery.essers'
    _description = 'Send Deliveries'