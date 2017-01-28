
from flask import Flask, request, abort
from netaddr import IPNetwork, IPAddress
import subprocess
import os

repodir = '/opt/pkgrepo/pkgbuilds/'
buildsdir = '/www/pkgrepo'
repo = '/www/pkgrepo/pkgrepo.db.tar.gz'

application = Flask(__name__)

def get_packages():
    for d in os.listdir(repodir):
        if os.path.isdir(os.path.join(repodir, d)) and not d.startswith('.'):
            yield d

def has_build(package):
    for f in os.listdir(buildsdir):
        if f.startswith(package) and f.endswith('.tar.xz'):
            if os.path.getmtime(os.path.join(buildsdir, f)) > os.path.getmtime(os.path.join(repodir, package, 'PKGBUILD')):
                return True
    return False

def delete_build(package):
    for f in os.listdir(buildsdir):
        if f.startswith(package) and f.endswith('.tar.xz'):
            os.remove(os.path.join(buildsdir, f))

def install_package(package):
    path = os.path.join(repodir, package)
    for f in os.listdir(path):
        if f.startswith(package) and f.endswith('.tar.xz'):
            package = f

    # move build to /www/pkgrepo
    os.rename(os.path.join(path, package), os.path.join(buildsdir, package))

    # add package to repo
    subprocess.check_call(['repo-add', repo, os.path.join(buildsdir, package)])

def update_pkgbuild(package):
    print('attempting update of package %s' % package)

    # delete old builds
    delete_build(package)
    
    # build package
    subprocess.check_call(['makepkg', '-d'], cwd=os.path.join(repodir, package))

    # install new package
    install_package(package)

def update_pkgrepo():
    print('attempting update of package repository')

    # update the pkgbuild repo
    subprocess.check_call(['git', 'pull'], cwd=repodir)
    
    # attempt to produce missing pkgbuilds
    for package in get_packages():
        if not has_build(package):
            update_pkgbuild(package)

@application.route("/", methods=['POST'])
def webhook():
    # check for valid origin (github ips)
    if not IPAddress(request.remote_addr) in IPNetwork('192.30.252.0/22'):
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
