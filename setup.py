# When possible, use distribute_setup's version of tools
try:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
except ImportError:
    from setuptools import setup, find_packages

setup(
    name='rmshell',
    version='0.0',
    description='A command line shell for redmine',
    author='Jesse Keating',
    author_email='jesse.keating@rackspace.com',
    url='https://github.com/rackerlabs/rmshell',
    license='Apache 2.0',
    packages=find_packages(where='src/'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': ['rmshell= rmshell.shell:cmd', ]},
    requires=['pyredmine', ],
)
