# encoding: utf-8
#
# fucore.py 
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
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY EXPRESS OR IMPLIED
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
# Created by René Köcher on 2009-12-27.
#

"""
.. module:: fucore
    :platform: Unix, MacOS, Windows
    :synopsis: Shared core functionalities.

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

import sys, os, re, quopri
import traceback
import logging
import logging.handlers
import email, email.message, email.header
from logging.handlers import TimedRotatingFileHandler, SysLogHandler

class FUCore(object):
    """
    FUCore contains the generic code and utility methods shared by both
    :class:`synfu.postfilter.PostFilter` and :class:`synfu.reactor.Reactor`.
    
    All of this methods are private and should only be called by subclasses.
    """
    
    HEADER_IGN  = [
    	re.compile('^(X-.*|Cc|To|Received|Delivered.*|Sender.*|Precedence|Reply.*)'),
    	re.compile('^List-(Unsubscribe|Archive|Post|Help|Subscribe)'),
    	re.compile('^(Lines|NNTP-Posting-(Date|Host)|Xref|Path)')
    ]
    
    CANCEL_EXP  = re.compile('(?i)\s*cancel(?# Aren\'t you confused now?)\s*')
    
    OUTLOOK_HACKS = [
            (re.compile(r'\b(AW|R|REPLY|ANTWORT):' , re.I), 'Re:'),
            (re.compile(r'\b(FWD|WG|WTR|Wtr\.):', re.I), 'Fwd:'),
    ]

    @classmethod
    def log_traceback(cls, instance, noreturn=True):
        """
        Log the last traceback

        If instance is provided the traceback will be logged to the
        supplied log_traceback file otherwise syslog will be used.

        :param: instance: a :class:`FUCore` subclass or :const:`None`
        :param: noreturn: if :const:`True` do a sys.exit(1)
        """

        logger = logging.getLogger('exception-trap')

        if instance and instance._conf.log_traceback:
            filename = instance._conf.log_traceback
            format = '%(asctime)s [%(process)d]: %(levelname)s: %(message)s'
            handler = logging.FileHandler(filename)
        else:
            format = 'SYNFU[%(process)d] %(message)s'
            handler = SysLogHandler('/dev/log', SysLogHandler.LOG_NEWS)

        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        for line in traceback.format_exc().splitlines():
            logger.critical(line)

        if noreturn:
            sys.exit(1)

    def __init__(self, conf):
        super(FUCore, self).__init__()

        self._conf = conf
        self._logger = logging.getLogger(self.__class__.__name__)
        if self._conf.log_facility == 'file':
            handler = TimedRotatingFileHandler(self._conf.log_filename,
                                               self._conf.log_when,
                                               self._conf.log_interval,
                                               self._conf.log_keep)
            if os.path.exists(self._conf.log_filename):
                # try to fixup rollover time
                stat = os.stat(self._conf.log_filename)
                ctime = int(stat.st_ctime)
                # work around python 2.6.2 deficiencies.. (not 100% accurate)
                if sys.hexversion < 0x20603f0:
                    handler.rolloverAt = ctime + handler.interval
                else:
                    handler.rolloverAt = handler.computeRollover(ctime)

            format = '%(asctime)s [%(process)d]: %(levelname)s: %(message)s'
        else:
            handler = SysLogHandler('/dev/log', SysLogHandler.LOG_NEWS)
            format = 'SYNFU[%(process)d] %(message)s'

        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(handler)
    
    def _log(self, message, *args, **kwargs):# rec=0, verbosity=1):
        """
        Log a message using :mod:`syslog` as well as :attr:`sys.stdout`.
        
        :param   message: The pre-formatted log message.
        :param       rec: Optional recursion level used to indent messages.
        :param verbosity: Minimal verbosity required to display this message.
        :returns: :const:`None`
        """
        
        verbosity = kwargs.get('verbosity', 1)
        rec       = kwargs.get('rec', 0)
        
        if self._conf.verbose and self._conf.verbosity >= verbosity:
            format_args = []
            
            for a in args:
                if isinstance(a, unicode):
                    format_args.append(a.encode('UTF-8'))
                else:
                    format_args.append(a)
            
            if isinstance(message, unicode):
                message = message.encode('UTF-8')
            
            message = '{0}{1}'.format(' '*rec, message.format(*format_args))
            if verbosity < 2:
                if message.strip().startswith('!!!'):
                    self._logger.error(message)
                else:
                    self._logger.info(message)
            else:
                if message.strip().startswith('!!!'):
                    self._logger.warning(message)
                else:
                    self._logger.debug(message)
    
    def _is_cancel(self, message):
        """
        Check if the passed message is a CANCEL message.
        
        This will try to match :attr:`FUCore.CANCEL_EXP` against all
        **Control:** headers contained in *message*.
        
        :param  message: A :class:`email.message` object.
        :returns: :const:`True` or :const:`False`
        """
        if FUCore.CANCEL_EXP.findall(message.get('Control', '')):
            self._log('--- Message contains *this* header, you know?')
            self._log('--- Therefore I\'m going to delete it.')
            return True
                
        return False
    
    def _find_list_tag(self, message, rec=0, plain=False):
        """
        Filter *message* for a valid list tag.
        
        This method will scan the passed in messages headers looking for a hint
        to the used list-tag.
        
        The following headers will be checked (in order):
        
            * X-SynFU-Tags (explicit List-Tags supplied by synfu-news2mail)
            * [X-]List-Post
            * [X-]List-Id
            * [X-]AF-Envelope-to
            
        If any of these is found it will be converted into a regular expression
        which can be used to remove the List-Tag from arbitrary headers.
        
        :param  message: A :class:`email.message` object.
        :param      rec: Optional recursion level used to indent messages.
        :param    plain: If :const:`True` return the plain List-Tag (no regexp)
        :returns: Either a :class:`re.SRE_PATTERN` or a string
        """
        tag = message.get('X-SynFU-Tags', None)
        lp  = message.get('List-Post', message.get('X-List-Post', None))
        lid = message.get('List-Id'  , message.get('X-List-Id', None))
        evl = message.get('AF-Envelope-to', message.get('X-AF-Envelope-to', None))
        
        tag_base = None
        

        if tag:
            tag = email.header.decode_header(tag)[0][0]
            self._log('--- using supplied SynFU tag hints', rec=rec)
            tag_base = '({0})'.format('|'.join(x.strip() for x in tag.split(',') if x.strip()))
        
        # preffer List-Id if we have it
        elif lid:
            lid = email.header.decode_header(lid)[-1][0]
            tag_base = lid.split('<')[-1].split('.')[0].strip()

        elif lp:
            lp = email.header.decode_header(lp)[0][0]
            try:
                tag_base = lp.split('mailto:')[1].split('@')[0]
            except IndexError:
                tag_base = None
            
        elif evl:
            evl = email.header.decode_header(evl)[0][0]
            try:
                tag_base = evl.split('@')[0]
            except IndexError:
                tag_base = None
        
        if plain:
            return tag_base
        
        if tag_base:
            self._log('--- list tag: "[*{0}*]"', format(tag_base), rec=rec)
            return re.compile('(?i)\[[^[]*{0}[^]]*\]'.format(tag_base))
            
        self._log('--- no list tag found', rec=rec)
        # return 'moab'
        return re.compile('(?i)\s*\[[^]]*(?# This is here to confuse people)\]\s*')
    
    def _filter_headers(self, list_tag, headers, outlook_hacks=False, rec=0):
        """
        Filter a list of headers according to the global settings.
        
        This method will filter the passed in header list by matching a
        series of expressions and filters to it:
        
        - if **list_tag** is specified and matched in the **Subject:** header
          it will be removed
        
        - if **outlook_hacks** is enabled then outlook-style AW:/FWD:/...
          subjects will be converted to RFC compliant versions
        
        - all tags matching :attr:`FUCore.HEADER_IGN` will be discarded
        
        :param      list_tag: A :class:`re.SRE_PATTERN` as returned
                              by :meth:`FUCore._find_list_tag`.
        :param       headers: A list of (key, value) headers
        :param outlook_hacks: If :const:`True` convert AW:/FWD:/... subjects
                              to RFC versions.
        :param           rec: Optional recursion level used to indent messages.
        :returns: The filtered header list.
        """
        removed      = 0
        have_subject = False
        
        for h in headers[:]:
            # another place where we mutate a list while iterating it
            # only this time we iterate a copy of the list
            
            (k, v) = h
            self._log('--- k == \'{0}\'', k, rec=rec, verbosity=4)
            
            if k == 'Subject':
                have_subject = True
                have_first_match = False
                decoded_hdr = email.header.decode_header(v)
                
                for (i, hv) in enumerate(decoded_hdr):
                    (v, enc) = hv

                    if outlook_hacks:
                        self._log('--- applying outlook fixes to Subject', rec=rec, verbosity=2)
                        
                        for (exp, repl) in FUCore.OUTLOOK_HACKS:
                            v = exp.sub(repl, v)
                        
                    l1 = str(v)
                    
                    # try to remove the first occurence of list-tag in l1
                    l1 = list_tag.sub('', l1)
                    if not l1 == v:
                        have_first_match = True
                        v = l1
                    
                    if enc is None:
                        # deal with already decoded headers
                        for new_enc in ['ascii', 'utf-8', 'latin1']:
                            try:
                                v.decode(new_enc)
                                enc = new_enc
                                break
                            except UnicodeDecodeError:
                                continue

                        if enc is None:
                            # probably the hardest choice..
                            v = v.decode('ascii', 'ignore')
                            enc = 'ascii'

                    decoded_hdr[i] = (v, enc)
                v = str(email.header.make_header(decoded_hdr))
                
                if not v == h[1]:
                    # gotcha - we have a list-tag
                    self._log('--- removing list tag..', rec=rec)
                    headers.remove(h)
                    headers.append((k, v))
                    
                if not v:
                    # remove the header if there's nothing left of it
                    # (or there never was anything to start with..)
                    try:
                        headers.remove(h)
                    except:
                        pass
                        
                    try:
                        headers.remove((k, v))
                    except:
                        pass
                        
                    # this will force creation of a dummy subject
                    have_subject = False
                    
            elif k == 'Message-ID':
                # fix multiple @@ in message id
                if v.find('@') != v.rfind('@'):
                    # there's more than one of then
                    self._log('--- copying Message-ID to X-Message-ID', rec=rec)
                    headers.remove(h)
                    headers.append(('X-Message-ID', v))
                    
                    while v.find('@') != v.rfind('@'):
                        v = v.replace('@', '', 1)
                        
                    headers.append(('Message-ID', v))
                    
            # filter headers
            for e in FUCore.HEADER_IGN:
                if e.match(k):
                    self._log('--- remove header "{0}"', k, rec=rec, verbosity=2)
                    
                    headers.remove(h)
                    removed += 1
                    
                    break
                    
        self._log('--- {0} headers removed', removed, rec=rec)
        
        if not have_subject:
            headers.append(('Subject', '<No Subject>'))
            self._log('!!! had to add a dummy subject', rec=rec)
            
        return headers
