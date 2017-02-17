'''
The Flask app
'''

from flask import Flask, request, abort
from netaddr import IPNetwork, IPAddress

from .pkgrepo import update_pkgrepo, update_pkgbuild


def _create_app():
    '''
    when you create the app, also update the pkgrepo
    '''
    update_pkgrepo()
    return Flask(__name__)


app = _create_app()


@app.route("/", methods=['POST'])
def webhook():
    '''
    respond to github webhooks
    '''
    # check for valid origin (github ips)
    if IPAddress(request.remote_addr) not in IPNetwork('192.30.252.0/22'):
        abort(403)

    # log the request
    print('received a request!')
    print(request.json)

    # dispatch request
    if request.json['repository']['name'] == 'pkgbuilds':
        update_pkgrepo()
    else:
        update_pkgbuild(request.json['repository']['name'])

    # say ok and leave
    return ('', 204)
