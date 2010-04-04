# encoding: utf-8
#
# config.py 
# 
# Copyright (c) 2009-2010 René Köcher <shirk@bitspin.org>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modifica-
# tion, are permitted provided that the following conditions are met:
# 
#   1.  Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
# 
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MER-
# CHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPE-
# CIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTH-
# ERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# Created by René Köcher on 2009-12-19.
#

"""
.. module:: config
    :platform: Unix, MacOS, Windows
    :synopsis: Shared settings manager.

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

try:
    import re
except:
    import sre as re

import sys, os, optparse, yaml

class _ReactorConfig(yaml.YAMLObject):
    yaml_tag = u'tag:news.piratenpartei.de,2009:synfu/reactor'
    
    def __init__(self, **kwargs):
        super(_ReactorConfig, self).__init__()
        
    def __repr__(self):
        return '{0}{{ outlook_hacks: {1}, complex_footer: {2}, verbose: {3} }}'.format(
                self.__class__.__name__,
                self.outlook_hacks,
                self.complex_footer,
                self.verbose)

    def configure(self):
        self.outlook_hacks  = self.settings.get('outlook_hacks', False)
        self.complex_footer = self.settings.get('complex_footer', False)
        self.strip_notes    = self.settings.get('strip_notes', False)
        self.verbose        = self.settings.get('verbose', False)
        self.verbosity      = self.settings.get('verbosity', 0)
        
        return self

class _PostfilterConfig(yaml.YAMLObject):
    yaml_tag = u'tag:news.piratenpartei.de,2009:synfu/postfilter'
    
    def __init__(self, **kwargs):
        super(_PostfilterConfig, self).__init__()
    
    def __repr__(self):
        return '{0}{{ mail2news_cmd: "{1}", filters[{2}] }}'.format(
                self.__class__.__name__,
                self.mail2news_cmd,
                len(self.filters))
    
    def configure(self):
        self.mail2news_cmd  = self.settings.get('mail2news_cmd', '/bin/false').strip()
        self.news2mail_cmd  = self.settings.get('news2mail_cmd', '/bin/false').strip()
        self.inn_sm         = self.settings.get('inn_sm'       , '/bin/false').strip()
        self.inn_host       = self.settings.get('inn_host'     , '/bin/false').strip()
        self.verbose        = self.settings.get('verbose', False)
        self.verbosity      = self.settings.get('verbosity', 0)
        self.default_sender = self.settings.get('default_sender', None)
        
        for e in self.filters:
            try:
                e['exp'] = re.compile(e['smtp'])
            except Exception,err:
                sys.stderr.write('Could not compile expression "{0[smtp]}": {1}\n'.format(e, err))
                pass
        
        return self
    
    
class Config(object):
    """SynFU global config"""
    
    _sharedConfig = None
    
    @classmethod
    def get(cls, *args):
        """
        Return the shared Config instance (initalizing it as needed).
        For the config syntax in use see `_synfu-config-syntax`.
        
        :param \*args: optional paths to search for synfu.conf
        :type \*args:  list of strings or None
        :rtype:        :class:`synfu.config.Config`
        :returns:      an initialezed :class:`synfu.config.Config` instance
        """
        
        if Config._sharedConfig:
            return Config._sharedConfig
        
        paths = ['.', '/etc', '/usr/local/etc']
        paths.insert(0, os.path.join(os.getenv('HOME','/'),'.config'))
        
        if args:
            paths = list(args) + paths
        
        parser = optparse.OptionParser()
        parser.add_option('-c', '--config',
                          dest    = 'config_path',
                          action  = 'store',
                          default = None,
                          help    = 'Path to config file')
                          
        (opts, args) = parser.parse_args(sys.argv[1:])
        if opts.config_path:
            paths.append(opts.config_path)
        
        for path in paths:
            try:
                if not path.endswith('synfu.conf'):
                    conf_path = os.path.join(path, 'synfu.conf')
                else:
                    conf_path = path
                
                Config._sharedConfig = Config(conf_path)
                
                return Config._sharedConfig
                
            except IOError,e:
                pass
        
        raise RuntimeError('Failed to load synfu.conf')
    
    def __init__(self, path):
        super(Config, self).__init__()

        self.postfilter = None
        self.reactor    = None
        
        with open(path, 'r') as data:
            for k in yaml.load_all(data.read()):
                if type(k) == _PostfilterConfig:
                    self.postfilter = k.configure()
                    
                elif type(k) == _ReactorConfig:
                    self.reactor = k.configure()
                    
                else:
                    print('What is type(k) == {0} ?'.format(type(k)))
                    
        if not self.postfilter:
            raise RuntimeError('Mandatory postfilter config missing.')
            
        if not self.reactor:
            raise RuntimeError('Mandatory reactor config missing.')

    
    