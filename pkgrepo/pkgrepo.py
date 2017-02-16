'''
actual package handling functions
'''

import subprocess
import os


PKGDIR = '/opt/pkgrepo/pkgbuilds/'
BUILDDIR = '/www/pkgrepo'
REPO = '/www/pkgrepo/pkgrepo.db.tar.gz'


def packages():
    '''
    yield packages
    '''
    for pkg in os.listdir(PKGDIR):
        if os.path.isdir(os.path.join(PKGDIR, pkg)) and not pkg.startswith('.'):
            yield pkg


def builds():
    '''
    yield built packages
    '''
    for pkg in os.listdir(BUILDDIR):
        if pkg.endswith('.tar.xz'):
            yield pkg


def needs_rebuild(package):
    '''
    figure out if a package is out of date
    '''
    for pkg in builds():
        if pkg.startswith(package):
            mtime_pkgbuild = os.path.getmtime(os.path.join(PKGDIR, package, 'PKGBUILD'))
            mtime_package = os.path.getmtime(os.path.join(BUILDDIR, pkg))
            return mtime_package < mtime_pkgbuild
    return True


def delete_build(package):
    '''
    remove builds of a package
    '''
    for pkg in builds():
        if pkg.startswith(package):
            os.remove(os.path.join(BUILDDIR, pkg))


def install_package(package):
    '''
    build and install a package
    '''
    path = os.path.join(PKGDIR, package)
    for pkg in os.listdir(path):
        if pkg.startswith(package) and pkg.endswith('.tar.xz'):
            package = pkg

    # move build to /www/pkgrepo
    os.rename(os.path.join(path, package), os.path.join(BUILDDIR, package))
    # add package to repo
    subprocess.check_call(['repo-add', REPO, os.path.join(BUILDDIR, package)])


def update_pkgbuild(package):
    '''
    update a single package
    '''
    print('attempting update of package %s' % package)

    # delete old builds
    delete_build(package)
    # build package
    subprocess.check_call(['makepkg', '-d'], cwd=os.path.join(PKGDIR, package))
    # install new package
    install_package(package)


def update_pkgrepo():
    '''
    update the entire package repo
    '''
    print('attempting update of package repository')

    # update the pkgbuild repo
    subprocess.check_call(['git', 'reset', '--hard'], cwd=PKGDIR)
    subprocess.check_call(['git', 'pull'], cwd=PKGDIR)
    # rebuild updated pkgbuilds
    for package in packages():
        if needs_rebuild(package):
            update_pkgbuild(package)
