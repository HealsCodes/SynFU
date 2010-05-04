# encoding: utf-8
#
# imp.py
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
# Created by René Köcher on 2010-04-07.
#

"""
.. module:: imp
    :platform: Unix, MacOS, Windows
    :synopsis: Periodic Imp - background tasks.

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

import sys, os, re, urllib2, pkgutil
from BeautifulSoup import BeautifulSoup, StopParsing

from synfu.config import Config
from synfu.fucore import FUCore

class Imp(FUCore):
    """
    Imp - the periodic Imp
    
    | SynFU Imp is a background helper designed to run periodic maintenance jobs.
    | At the time of this writing the following jobs are built-in:
    
        - :ref:`GroomNewsgroups` -- update newsgroup descriptions via mailman
    
    | Each job is provided as a separate python file containing arbitrary
    | job definitions in the form of :class:`synfu.imp.ImpJob` subclasses.
    """
    
    VERSION = '0.3'
    
    def __init__(self):
        super(Imp, self).__init__()
        
        Config.add_option('-j', '--jobs',
                          dest='jobs',
                          help='comma separated list of jobs to execute',
                          action='store',
                          default='',
                          metavar='JOBS')
                          
        Config.add_option('', '--help-jobs',
                          dest='show_help',
                          help='print help for installed jobs',
                          action='store_true',
                          default=False)
        
        self._conf = Config.get().imp
        
        self._show_help = Config.get().options.show_help
        if Config.get().options.jobs:
            self._jobs = Config.get().options.jobs.split(',')
        else:
            self._jobs = []
        
        if self._show_help:
            self._conf.verbose = False
        
    def run(self):
        if self._show_help:
            # extra printout, --help-plugins disables _log()
            print('Installed jobs:')
        
        self._log('--- begin')
        self._log('--- loading plugins:')
        plugin_path = [os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'plugins'),
                       self._conf.plugin_dir]
        
        for p in plugin_path:
            if not os.path.exists(p):
                self._log('!!! skipping  "{0}" - no such file or directory'.format(p))
                continue
            
            sys.path.append(p)
            
            for (importer, name, ispkg) in pkgutil.walk_packages([p]):
                if name.startswith('ImpJob'):
                    try:
                        __import__(name)
                    except Exception, e:
                        self._log('!!! unable to import "{0}": {1}: {2}'.format(
                                  name, e.__class__.__name__, e))
        
        if 'LOADED_JOBS' in dir(Imp):
            for plugin in Imp.LOADED_JOBS:
                self._log('--- loaded plugin "{0}"'.format(plugin.__name__),
                          verbosity=2)
        
        
            for plugin in Imp.LOADED_JOBS:
                if self._jobs and (not plugin.__name__ in self._jobs):
                    continue
                
                try:
                    inst = plugin()
                    
                    if self._show_help:
                        print '-- {0}:'.format(plugin.__name__)
                        inst.show_help(Config.get().optargs)
                        del inst
                        continue
                    
                    do_run = inst.needs_run(Config.get().optargs)
                    self._log('--- {0}.needs_run() ='.format(plugin.__name__, do_run))
                    
                    if do_run:
                        self._log('--- executing job "{0}"'.format(plugin.__name__))
                        res = inst.run()
                        self._log('--- job result: {0}'.format(res))
                    del inst
                except Exception, e:
                        self._log('!!! uncaught exception {0}: {1}'.format(
                                  e.__class__.__name__, e))
        self._log('--- end')
        return 0

class _ImpJobMeta(type):
    """
    Metaclass featuring automatic registration for ImpJob subclasses.
    """
    def __init__(cls, name, bases, dict):
        if not 'LOADED_JOBS' in Imp.__dict__:
            setattr(Imp, 'LOADED_JOBS', [])

        if (not name == 'ImpJob') and (not cls in Imp.LOADED_JOBS):
            Imp.LOADED_JOBS.append(cls)

        super(type, _ImpJobMeta).__init__(name, bases, dict)

class ImpJob(FUCore):
    """
    An abstract job.

    | ImpJob provides the base for custom SynFU oriented jobs.
    | Any derived subclass will be registered as a new job upon import.
    """
    __metaclass__ = _ImpJobMeta

    def _log(self, message, *args, **kwargs):
        """
        | Log a message using :mod:`syslog` as well as :attr:`sys.stdout`.
        | Messages will be prefixed using the current *__class__.__name__*.
        
        :param   message: The pre-formatted log-message.
        :param       rec: Optional recursion level used to indent messages.
        :param verbosity: Minimal verbosity required to display this message.
        :returns: :const:`None`
        """
        if len(message) >= 4 and message[0] == message[1] == message[2]:
            tags    = message[:4]
            message = message[4:]
        else:
            tags    = '--- '
            
        if isinstance(message, unicode):
            message = '{0}{1}: {2}'.format(tags, self.__class__.__name__, message.encode('UTF-8'))
        else:
            message = '{0}{1}: {2}'.format(tags, self.__class__.__name__, message)
        
        super(ImpJob, self)._log(message, *args, **kwargs)

    def job_config(self, name, defaults={}):
        """
        Load job specific config object.
        
        | This method will try to load a subsection of the Imp-configuration.
        | The optional dictionary *defaults* contains a list of default key,value pairs.
        
        :param: name: The name of the config subsection beneath Imp.jobs
        :param: defaults: A :const:`dict` with key,value pairs for default parameters
        :return: A JobConf instance with all top-level settings converted to attributes.
        """
        class JobConf(object):
            pass
            
        conf = JobConf()
        imp  = Config.get().imp
        
        defaults.update(getattr(imp, 'jobs', {}).get(name, {}))
        
        for k,v in defaults.items():
            setattr(conf, k, v)
        
        setattr(conf, 'verbose'  , imp.verbose)
        setattr(conf, 'verbosity', imp.verbosity)
        
        return conf
        
    def show_help(self, *args):
        """
        Print the available command line options for this job.
        
        :params: \*args: the list of command line arguments (suitable for use by :mod:`optparse`)
        :returns: :const:`None`
        
        .. note::
        
            You should really overwrite this one ;)
        """
        print('\tThe author of this job was to lazy to provide a real help.')
    
    def needs_run(self, *args):
        """
        Check run status.

        | This method will be called by :class:`Imp` to check if this job needs to be run.
        | The final decision is up to the job and determined by the return code.

        :params: \*args: the list of command line arguments (suitable for use by :mod:`optparse`)
        :returns: :const:`True` if the job needs to be run
        """
        return False

    def run(self):
        """
        Execute the job

        | This method will be called on a successful call to :meth:`needs_run`.
        | On success the job should return :const:`True`, :const:`False` otherwise.

        :returns: :const:`True` on success
        :returns: :const:`False` on failure

        .. note::

            Imp will wrap job execution in a catch-all try-block.
            However it is considered good practice to care for possible exceptions.
        """
        return False



def ImpRun():
    """
    Global wrapper for setup-tools.
    """
    imp = Imp()
    sys.exit(imp.run())
