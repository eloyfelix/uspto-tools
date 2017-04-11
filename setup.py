#!/use/bin/env python

from distutils.core import setup


def readme():
    with open('README.rst') as f:
        contents = f.read()
    return contents

setup(
    name='uspto_tools',
    version='1.0',
    author='Rickard Sjögren',
    author_email='r.sjogren89@gmail.com',
    license='MIT',
    url='https://github.com/clicumu/uspto-tools',
    description=('A simple Python package for fetching and '
                 'retrieval of USPTO patents'),
    long_description=readme(),
    package_dir = {
        'uspto_tools': 'uspto_tools',
        'uspto_tools.fetch': 'uspto_tools/fetch',
        'uspto_tools.parse': 'uspto_tools/parse'
    },
    packages=['uspto_tools', 'uspto_tools.parse', 'uspto_tools.fetch'],
    scripts=['scripts/bulk_download.py'],
    keywords='python uspto patents textanalysis',
    install_requires=[
        'beautifulsoup4',
        'requests',
    ]
)
