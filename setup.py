# When possible, use distribute_setup's version of tools
try:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
except ImportError:
    from setuptools import setup, find_packages

setup(
    name='rore',
    version='0.3',
    description='A command line utility for Redmine',
    author='Jesse Keating',
    author_email='jesse.keating@rackspace.com',
    url='https://github.com/rackerlabs/rore',
    license='Apache 2.0',
    packages=find_packages(where='src/'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': ['rore= rore.shell:cmd', ]},
    install_requires=['python-redmine>=0.7.2', ],
)
