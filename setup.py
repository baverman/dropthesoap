from setuptools import setup, find_packages

setup(
    name     = 'dropthesoap',
    version  = '0.1dev',
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'SOAP server and XSD/WSDL modeling framework',
    long_description = open('README.rst').read(),
    zip_safe   = False,
    packages = find_packages(exclude=['tests']),
    install_requires = ['WebOb'],
    include_package_data = True,
    url = 'http://github.com/baverman/dropthesoap',
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
    ],
)
