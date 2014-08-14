from openerp.osv import osv, fields
import ftplib
import logging
import datetime
from os.path import join

class clubit_essers_communicator(osv.Model):
    _name = 'clubit.essers.communicator'
    _description = 'Class to communicate with Essers.'

    def start(self, cr, uid, ids, context=None):
        self.push(cr, uid)
        return {'type': 'ir.actions.act_window_close'}


    def push(self, cr, uid):

        log = logging.getLogger(None)
        log.info('ESSERS_PUSHER: Starting the FTP pushing process.')


        # Search for deliveries that need pushing
        # ---------------------------------------


        # Find the customizing
        # --------------------
        log.info('ESSERS_PUSHER: Searching for the ESSERS_FTP connection settings.')
        flow_db = self.pool.get('clubit.tools.edi.flow')
        flow_id = flow_db.search(cr, uid, [('model', '=', 'stock.picking.out'),('method', '=', 'send_essers_out')])[0]
        settings = self.pool.get('clubit.tools.settings').get_settings(cr, uid)
        ftp_info = [x for x in settings.connections if x.name == 'ESSERS_FTP' and x.is_active == True]
        if not ftp_info:
            log.warning('ESSERS_PUSHER: Could not find the ESSERS_FTP connection settings, creating CRM helpdesk case.')
            return True
        ftp_info = ftp_info[0]


        # Connect to the FTP server
        # -------------------------
        try:
            log.info('ESSERS_PUSHER: Connecting to the FTP server.')
            ftp = ftplib.FTP(ftp_info.url, ftp_info.user, ftp_info.password)
        except Exception as e:
            log.warning('ESSERS_PUSHER: Could not connect to FTP server at {!s}, error given: {!s}'.format(ftp_info.url, str(e)))
            return True


        # Move to the folder containing the files
        # ---------------------------------------
        #success = ftp.cwd('Artikelgegevens')
        #if not success:
        #    log.warning('ESSERS_PUSHER: Connected to FTP server {!s}, but could not find folder Artikelgegevens'.format(ftp_info.url))
        #    ftp.quit()
        #    return True


        # Download the 2 files we need
        # ----------------------------
        log.info('ESSERS_PUSHER: Searching for files.')
        files = list_files(ftp)
        if not files:
            log.warning('ESSERS_PUSHER: Connected to FTP server {!s}, but folder Artikelgegevens did not contain any files'.format(ftp_info.url))
            ftp.quit()
            return True

        # Look for the latest delta file
        # ------------------------------
        now = datetime.datetime.now()
        delta = [(x[-1],datetime.datetime.strptime('-'.join([str(now.year),x[5],str(x[6])]), '%Y-%b-%d')) for x in files if x[-1].find('delta') != -1]
        if not delta:
            log.warning('ESSERS_PUSHER: Connected to FTP server {!s}, but folder Artikelgegevens did not contain any delta files'.format(ftp_info.url))
            ftp.quit()
            return True

        youngest_delta = max(x for x in delta if x[1] < now)
        log.info('ESSERS_PUSHER: downloading delta masterdata file...')
        try:
            path = join('EDI', cr.dbname, 'THR_product_upload', youngest_delta[0])
            out = open(path, "wb")
            ftp.retrbinary('RETR {!s}'.format(youngest_delta[0]), out.write)
            out.close()
        except Exception as e:
            log.warning('ESSERS_PUSHER: Tried to download file {!s} to {!s}, but got the following error: {!s}'.format(youngest_delta[0], path, str(e)))
            ftp.quit()
            return True

        # Look for the latest stock file
        # ------------------------------
        stock = [x for x in files if x[-1].find('thr_stock_') != -1 and x[-1][-3:] == 'csv']
        if stock:
            log.info('ESSERS_PUSHER: downloading stock file...')
            stock = stock[0]
            try:
                path = join('EDI', cr.dbname, str(ftp_info.partner.id), str(flow_id), '-'.join([stock[5], stock[6], stock[7],stock[-1]]))
                out = open(path, "wb")
                ftp.retrbinary('RETR {!s}'.format(stock[-1]), out.write)
                out.close()
            except Exception as e:
                log.warning('ESSERS_PUSHER: Tried to download file {!s} to {!s}, but got the following error: {!s}'.format(stock, path, str(e)))
                ftp.quit()
                return True


        # Close the connection and leave the program
        # ------------------------------------------
        ftp.quit()
        log.info('ESSERS_PUSHER: Process is complete.')
        return True

