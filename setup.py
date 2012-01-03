# encoding: utf-8
"""
setup.py

Copyright (c) 2009-2010 René Köcher <shirk@bitspin.org>
All rights reserved.

Redistribution and use in source and binary forms, with or without modifica-
tion, are permitted provided that the following conditions are met:

  1.  Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.

  2.  Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MER-
CHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPE-
CIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTH-
ERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

Created by René Köcher on 2009-12-19.
"""

from setuptools import setup, find_packages
import sys, os

version='0.4.15'

setup(name='SynFU',
      version=version,
      packages=find_packages(exclude=['ez_setup', 'example','tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'PyYAML > 3.08',
        'BeautifulSoup < 3.1.0'
      ],
      entry_points={
        'console_scripts' : [
            'synfu-reactor = synfu.reactor:ReactorRun',
            'synfu-mail2news = synfu.postfilter:FilterMail2News',
            'synfu-news2mail = synfu.postfilter:FilterNews2Mail',
            'synfu-imp       = synfu.imp:ImpRun'
        ],
      },
      test_suite="tests.suite"
)

