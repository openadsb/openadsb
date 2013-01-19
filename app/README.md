OpenADSB Python App
===================

This app connects to the USB ADS-B receiver, or network data feeds, and decodes received ADS-B packets.  See the screenshot for details.
Run this app with -h option for help:  python main.py -h

It requires python 2.7 and these python modules (sudo apt-get install ... ):

	python-setuptools
	python-usb (1.0 or newer) - you might have to build from source: http://pypi.python.org/packages/source/p/pyusb/pyusb-1.0.0a2.tar.gz
	python-qt4 
	python-qt4-sql
	python-dev
	libqt4-sql-mysql

then install these python modules with sudo easy_install:

	bitstring
	yappi
