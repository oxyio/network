# oxy.io
# File: setup.py
# Desc: oxy.io Network package config

from setuptools import setup


install_requires = (
    'paramiko==1.15.2',
    'netaddr==0.7.18'
)

# oxy.io Network Python, see MANIFEST.in for HTML/etc
packages = (
    'oxyio.network',
    'oxyio.network.models',
    'oxyio.network.tasks',
    'oxyio.network.web',
    'oxyio.network.web.views',
    'oxyio.network.websockets'
)


if __name__ == '__main__':
    setup(
        name='oxy.io-Network',
        version=0,
        author='Oxygem',
        author_email='hello@oxygem.com',
        url='',
        description='',
        packages=packages,
        package_dir={'oxyio.network': 'network'},
        install_requires=install_requires,
        license='MIT',
        include_package_data=True
    )
