
from os.path import join, dirname
from setuptools import setup


setup(
    name='pkgrepo',
    version='0.1.0',
    maintainer='Andreas Grapentin',
    maintainer_email='andreas@grapentin.org',
    url='https://github.com/oaken-source/pkgrepo',
    description='Pkgrepo.',

    keywords='arch pkgbuild pkgrepo',
    packages=['pkgrepo'],

    install_requires=[
        'flask',
        'netaddr'
    ],

    license='GPL3',
)
