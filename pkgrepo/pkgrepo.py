'''
actual package handling functions
'''

import subprocess
import logging
import re
import os

from .pkgtools import ccall


PKGBUILDS = '/opt/pkgrepo/pkgbuilds/'
CHROOT = '/opt/pkgrepo/chroot/'
PACKAGES = '/www/pkgrepo/'
PKGREPO = os.path.join(PACKAGES, 'pkgrepo.db.tar.gz')


class Pkgrepo(object):
    '''
    this class represents the package repo
    '''
    def __init__(self):
        '''
        constructor - collect infos about packages
        '''
        self._packages = []
        self._pkgbuilds = []

        self._collect_packages()

    def update(self):
        '''
        update the entire package repo
        '''
        # clean and pull the repository
        logging.info('updating package repository')
        ccall(['git', 'checkout', '--', '.'], cwd=PKGBUILDS)
        ccall(['git', 'clean', '-dfx'], cwd=PKGBUILDS)
        ccall(['git', 'pull'], cwd=PKGBUILDS)
        ccall(['git', 'submodule', 'update', '--init', '--recursive'], cwd=PKGBUILDS)

        # regenerate information on pkgbuilds
        self._collect_pkgbuilds()

        # delete packages removed from pkgrepo
        logging.info('scanning for deleted packages')
        for package in self._packages:
            if package.pkgbuild is None:
                logging.info('package %s has no PKGBUILD - removing...', package)
                package.uninstall()

        # find packages where package is older than PKGBUILD, or does not exist
        logging.info('scanning for updated packages')
        rebuilds = []
        for pkgbuild in self._pkgbuilds:
            if pkgbuild.package is None or pkgbuild.package.version != pkgbuild.version:
                logging.info('%s needs to be rebuilt - queueing...', pkgbuild.name)
                rebuilds.append(pkgbuild)

        # attempt to rebuild these packages
        while rebuilds:
            retries = []
            for pkgbuild in rebuilds:
                try:
                    logging.info('attempting rebuild of %s...', pkgbuild.name)
                    pkgbuild.makepkg()
                    logging.info('finished rebuild of %s...', pkgbuild.name)
                except subprocess.CalledProcessError:
                    logging.warning('rebuild of %s has failed. requeueing...', pkgbuild.name)
                    retries.append(pkgbuild)
            if retries == rebuilds:
                logging.error('unable to resolve this: %s', retries)
                raise Exception('unable to resolve this: %s', retries)
            rebuilds = retries

    def build(self, packagename):
        '''
        rebuild the given package by name
        '''
        # find the queried package
        self._collect_pkgbuilds()
        pkgbuild = next(p for p in self._pkgbuilds if p.name == packagename)
        pkgbuild.makepkg()

    def _collect_packages(self):
        '''
        figure out what built packages there are
        '''
        # clear packages list
        self._packages.clear()

        # collect the installed packages
        for file in os.listdir(PACKAGES):
            if file.endswith('.pkg.tar.xz'):
                package = Package(file)
                logging.debug('found a package: %s', package)
                self._packages.append(package)

    def _collect_pkgbuilds(self):
        '''
        figure out what PKGBUILDs there are
        '''
        # unlink all packages from pkgbuilds
        for package in self._packages:
            package.pkgbuild = None

        # clear pkgbuild list
        self._pkgbuilds.clear()

        # collect pkgbuilds
        for folder in os.listdir(PKGBUILDS):
            if os.path.isdir(os.path.join(PKGBUILDS, folder)) and not folder.startswith('.'):
                pkgbuild = Pkgbuild(folder)
                # figure out which package it belongs to
                try:
                    pkgbuild.package = next(p for p in self._packages if p.name == pkgbuild.name)
                    pkgbuild.package.pkgbuild = pkgbuild
                    logging.debug('%s has package: %s', pkgbuild.name, pkgbuild.package)
                except StopIteration:
                    logging.warning('%s has no package', pkgbuild.name)
                self._pkgbuilds.append(pkgbuild)


class Package(object):
    '''
    a built package
    '''
    def __init__(self, file):
        '''
        constructor - parse the filename and extract name and version
        '''
        self._file = file
        match = re.match(r'^(.*)-([^-]*-[0-9]*)-[^-]*\.pkg\.tar\.xz$', file).groups()

        self._name = match[0]
        self._version = match[1]
        logging.debug('tokenized %s to name: %s version: %s', file, self._name, self._version)

        self.pkgbuild = None

    @property
    def name(self):
        '''
        the package name
        '''
        return self._name

    @property
    def version(self):
        '''
        the package version
        '''
        return self._version

    def install(self, pkgbuilddir):
        '''
        install the package from the pkgbuild directory
        '''
        logging.info('adding %s to pkgrepo', self)
        os.rename(os.path.join(pkgbuilddir, self._file), os.path.join(PACKAGES, self._file))
        ccall(['repo-add', PKGREPO, os.path.join(PACKAGES, self._file)])

    def uninstall(self):
        '''
        uninstall the package
        '''
        logging.info('removing %s from pkgrepo', self)
        ccall(['repo-remove', PKGREPO, self._name])
        try:
            os.unlink(os.path.join(PACKAGES, self._file))
        except FileNotFoundError:
            pass

    @classmethod
    def make(cls, pkgbuild):
        '''
        produce a new package from the given pkgbuild
        '''
        # build the package in the chroot
        ccall(['sudo', 'makechrootpkg', '-c', '-r', CHROOT], cwd=pkgbuild.cwd)

        # produce the package object
        for file in os.listdir(pkgbuild.cwd):
            if file.endswith('.pkg.tar.xz'):
                package = Package(file)
                package.pkgbuild = pkgbuild
                return package

        # there was no package? how peculiar.
        logging.error('found no package in %s', pkgbuild.cwd)
        raise Exception('found no package in %s' % pkgbuild.cwd)

    def __repr__(self):
        '''
        a string representation of the package
        '''
        return '%s-%s' % (self.name, self.version)


class Pkgbuild(object):
    '''
    a PKGBUILD
    '''
    def __init__(self, folder):
        '''
        constructor - parse package name and version from the PKGBUILD
        '''
        self._cwd = os.path.join(PKGBUILDS, folder)

        # parse the PKGBUILD
        with open(os.path.join(self.cwd, 'PKGBUILD')) as file:
            data = file.read()
            pkgname = re.search(r'pkgname *=(.*)', data).groups()[0].strip()
            logging.debug(data)
            logging.debug('PKGBUILD tokenized into pkgname: %s', pkgname)

        self._name = pkgname
        self._version = None
        self.package = None


    @property
    def name(self):
        '''
        the name of the package
        '''
        return self._name

    @property
    def version(self):
        '''
        the version of the package
        '''
        if self._version is None:
            self._get_version()
        return self._version

    def _get_version(self):
        '''
        update the PKGBUILD and extract the version number
        '''
        # clean the pkgbuild
        ccall(['rm', '-rf', 'src'], cwd=self.cwd)
        ccall(['git', 'clean', '-fdx'], cwd=self.cwd)
        ccall(['git', 'checkout', '--', '.'], cwd=self.cwd)

        # update the pkgver
        ccall(['makepkg', '-do'], cwd=self.cwd)

        # parse the PKGBUILD
        with open(os.path.join(self.cwd, 'PKGBUILD')) as file:
            data = file.read()
            pkgver = re.search(r'pkgver *=(.*)', data).groups()[0].strip()
            pkgrel = re.search(r'pkgrel *=(.*)', data).groups()[0].strip()
            logging.debug(data)
            logging.debug('PKGBUILD tokenized into pkgver: %s pkgrel: %s', pkgver, pkgrel)

        self._version = '%s-%s' % (pkgver, pkgrel)

        # clean the pkgbuild again
        ccall(['rm', '-rf', 'src'], cwd=self.cwd)
        ccall(['git', 'clean', '-fdx'], cwd=self.cwd)
        ccall(['git', 'checkout', '--', '.'], cwd=self.cwd)

    @property
    def cwd(self):
        '''
        the directory containing the pkgbuild
        '''
        return self._cwd

    def makepkg(self):
        '''
        rebuild the given package
        '''
        oldpackage = self.package

        # update the chroot
        ccall(['sudo', 'arch-nspawn', os.path.join(CHROOT, 'root'),
            'pacman', '-Syu', '--noconfirm'])
        # clean the package directory
        ccall(['git', 'clean', '-fdx'], cwd=self.cwd)

        # buildfind the new package
        logging.info('starting build of %s', self.name)
        self.package = Package.make(self)
        logging.info('new package has been built as %s', self.package)

        # install it
        if oldpackage is not None:
            oldpackage.uninstall()
        self.package.install(self.cwd)

    def __repr__(self):
        '''
        a string representation of the pkgbuild
        '''
        return '%s-%s' % (self.name, self.version)
