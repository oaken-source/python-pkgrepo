'''
The Flask app
'''

import logging
import netaddr
from flask import Flask, request, abort

from .pkgrepo import Pkgrepo


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


GITHUB = netaddr.IPNetwork('192.30.252.0/22')
APPLICATION = Flask(__name__)


@APPLICATION.route("/", methods=['POST'])
def webhook_push():
    '''
    respond to github webhooks
    '''
    logging.info('received a push notification!')
    logging.debug(request.json)

    # check for valid origin (github ips)
    if netaddr.IPAddress(request.remote_addr) not in GITHUB:
        logging.warning('request from unauthorized IP: %s', request.remote_address)
        logging.warning('aborting...')
        abort(403)

    # dispatch request
    target = request.json['repository']['name']
    logging.info('requested rebuild of %s', target)

    pkgrepo = Pkgrepo()

    if target == 'pkgbuilds':
        pkgrepo.update()
    else:
        pkgrepo.build('%s-git' % target)

    # say ok and leave
    logging.info('request finished!')
    return ('', 204)


@APPLICATION.route("/rebuild/")
def webhook_rebuild():
    '''
    trigger a full rebuild
    '''
    logging.info('received a rebuild request!')
    logging.debug(request)

    pkgrepo = Pkgrepo()
    pkgrepo.update()

    # say ok and leave
    logging.info('request finished!')
    return ('', 204)
