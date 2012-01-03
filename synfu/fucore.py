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
import time
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
    
    TZ_EXP = re.compile(r'(^[^+-]*)(([+-]\d{4})\s*\([^)]*\)).*$')
    
    TZ_OFFSETS = {
        '-1200' : 'IDLW',
        '-1100' : 'BST',
        '-1030' : 'HST',
        '-1000' : 'CAT',
        '-0900' : 'YST',
        '-0800' : 'PST',
        '-0700' : 'MST',
        '-0600' : 'CST',
        '-0500' : 'CDT',
        '-0400' : 'EDT',
        '-0330' : 'NST',
        '-0300' : 'GST',
        '-0200' : 'AT',
        '-0100' : 'WAT',
        '-0000' : 'WET',
        '+0000' : 'GMT',
        '+0100' : 'CET',
        '+0200' : 'EET',
        '+0300' : 'BT',
        '+0330' : 'IT',
        '+0400' : 'ZP4',
        '+0500' : 'ZP5',
        '+0530' : 'IST',
        '+0600' : 'NST',
        '+0700' : 'SST',
        '+0730' : 'JT',
        '+0800' : 'CCT',
        '+0830' : 'MT',
        '+0900' : 'JST',
        '+0930' : 'CAST',
        '+1000' : 'EAST',
        '+1030' : 'CADT',
        '+1100' : 'EADT',
        '+1130' : 'NZT',
        '+1200' : 'IDLE',
        '+1300' : 'NZTD'
    }
    
    BLACKLIST_MODES = [ 'news2mail', 'mail2news', 'reactor' ]
    
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
        
        self._blacklist = {}
        if self._conf.blacklist_filename:
            try:
                blacklist_file = open(self._conf.blacklist_filename)
                for (lno, line) in enumerate(blacklist_file.readlines()):
                    line = line.strip()
                    if line.startswith('#'):
                        continue
                    fields = [x.strip() for x in line.split(';') if x]
                    if len(fields) < 2 or len(fields) > 3:
                        self._log("!!! {0}:{1}: invalid field count {2} expected 2 or 3",
                                  self._conf.blacklist_filename, lno + 1, len(fields))
                        continue
                    elif fields[1].lower() in ['e','ne','en'] and not len(fields) == 3:
                        self._log('!!! {0}:{1}: invalid field count {2} for rule "{3}"',
                                  self._conf.blacklist_filename, lno + 1, len(fields), fields[1])
                        continue
                    elif not fields[1].lower() in ['d', 'n', 'e', 'ne', 'en']:
                        self._log('!!! {0}:{1}: invalid rule "{2}"',
                                  self._conf.blacklist_filename, lno + 1, fields[1])
                        continue
                    
                    if len(fields) == 2:
                        fields.append(None)
                    
                    self._blacklist[fields[0]] = { 'addr' : fields[0],
                                                   'action' : fields[1],
                                                   'param' : fields[2] }
                    self._log('--- blacklist: <addr: {0}>; <action: {1}>; <param: {2}>',
                              fields[0], fields[1], fields[2], verbosity=3)
            except IOError, e:
                self._log('!!! failed to open blacklist file "{0}": {1}',
                          self._conf.blacklist_filename, str(e))
            
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
    
    def _filter_headers(self, list_tag, headers, outlook_hacks=False, fix_dateline=False, rec=0, whitelist=[]):
        """
        Filter a list of headers according to the global settings.
        
        This method will filter the passed in header list by matching a
        series of expressions and filters to it:
        
        - if **list_tag** is specified and matched in the **Subject:** header
          it will be removed
        
        - if **outlook_hacks** is enabled then outlook-style AW:/FWD:/...
          subjects will be converted to RFC compliant versions
        
        - if **fix_dateline** is enabled Date-headers with broken timezone
          (like those sent by Incredymail) will get their timezone fixed.
        
        - all tags matching :attr:`FUCore.HEADER_IGN` will be discarded
          with the exception of X-No-Archive.
        
        :param      list_tag: A :class:`re.SRE_PATTERN` as returned
                              by :meth:`FUCore._find_list_tag`.
        :param       headers: A list of (key, value) headers
        :param outlook_hacks: If :const:`True` convert AW:/FWD:/... subjects
                              to RFC versions.
        :param           rec: Optional recursion level used to indent messages.
        :param     whitelist: Optional list of header names to keep
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
                    
                    try:
                        if not enc is None:
                            v.decode(enc)
                    except UnicodeDecodeError:
                        enc = None
                    
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
                    
            elif k == 'Message-ID' or k == 'Message-Id':
                # fix <message-id
                if v.strip().startswith('<') and not v.strip().endswith('>'):
                    self._log('--- appending missing > to Message-ID')
                    v = v.strip() + '>'
                    headers.remove(h)
                    headers.append((k, v))
                    
                # fix message-id>
                if v.strip().endswith('>') and not v.strip().startswith('<'):
                    self._log('--- prepending missing < to Message-ID')
                    v = '<' + v.strip()
                    headers.remove(h)
                    headers.append((k, v))
                    
                # fix multiple @@ in message id
                if v.find('@') != v.rfind('@'):
                    # there's more than one of then
                    self._log('--- copying Message-Id to X-Message-Id', rec=rec)
                    headers.remove(h)
                    headers.append(('X-Message-Id', v))
                    
                    while v.find('@') != v.rfind('@'):
                        v = v.replace('@', '', 1)
                        
                    headers.append((k, v))
                    
            elif k == 'References':
                # handle References with more than 998 octets
                decoded_header = email.header.decode_header(v)
                
                if len(v) + len(k) > 990:
                    self._log('--- References {0} > 990 octets, shortening', len(v) + len(k), rec=rec)
                    v = v.replace('\n', '').replace('\t', '').replace(' ', '')
                    match = [x.replace('<', '').replace('>', '') for x in v.split('><')]
                    if match and len(match) >= 3:
                        v = [match[0]] + match[-2:]
                        v = ['<{0}>'.format(x) for x in v]
                        v = email.header.make_header([(' '.join(v), 'ascii')])
                        self._log('--- new References: {0}', v, rec=rec, verbosity=2)
                        
                        headers.remove(h)
                        headers.append(('References', v))
                    elif len(match) < 3:
                        self._log('!!! References looks broken (HUGE but only two Message-IDs)!')
                        self._log('match: {0}', match)
                    else:
                        self._log('!!! Could not split References into Message-IDs!', rec=rec, verbosity=0)
                        
            elif k == 'Date' or k == 'X-Date':
                if fix_dateline:
                    try:
                        v.decode('ascii')
                    except UnicodeDecodeError:
                        match = FUCore.TZ_EXP.findall(v)
                        if match:
                            (time_stamp, old_tz, zone_offset) = match[0]
                            
                            if zone_offset in FUCore.TZ_OFFSETS:
                                v = '{0}{1} ({2})'.format(time_stamp, zone_offset,
                                                           FUCore.TZ_OFFSETS[zone_offset])
                                v = email.header.make_header([(v, 'ascii')])
                                self._log('--- fix Date-header: "{0}" -> "{1}"', h[1], v, rec=rec)
                            else:
                                self._log('!!! Unknown timezone {0}, can\t fix it!', rec=rec)
                            
                            headers.remove(h)
                            headers.append(('Date', v))
                        else:
                            self._log('!!! Date-header looks invalid and contains no parseable timezone!', rec=rec)
                        
            # filter headers
            whitelist = [x.lower() for x in whitelist]
            for e in FUCore.HEADER_IGN:
                if e.match(k):
                    if k.lower() == 'x-no-archive':
                        self._log('--- keep X-No-Archive: {0}', v, rec=rec, verbosity=2)
                        continue
                    
                    if k.lower() in whitelist:
                        continue
                    
                    self._log('--- remove header "{0}"', k, rec=rec, verbosity=2)
                    
                    headers.remove(h)
                    removed += 1
                    
                    break
                    
        self._log('--- {0} headers removed', removed, rec=rec)
        
        if not have_subject:
            headers.append(('Subject', '<No Subject>'))
            self._log('!!! had to add a dummy subject', rec=rec)
            
        return headers
    
    def _apply_blacklist(self, message, mode, rec=0):
        """
        Apply the global blacklist to this message.

        This method will modify the headers of the message or decide to
        discard the whole message based on the global blacklist.

        :param messag: A :class:`email.message` object.
        :param mode: One of :attr:`FUCore.BLACKLIST_MODES`
        :returns: The modified message or None if the message should be dropped.
        """
        if not mode.lower() in FUCore.BLACKLIST_MODES:
            self._log('!!! Invalid blacklist mode "{0}", not modifying message.', mode, rec=rec)
            return message
        
        mfrom = message.get('From', '').split('<')[-1].split('>')[0]
        sender = message.get('Sender', '').split('<')[-1].split('>')[0]
        
        if not mfrom and not msender:
            self._log('!!! Message has neiter "From:" nor "Sender:" headers!', rec=rec)
            return message
        
        list_entry = self._blacklist.get(mfrom.lower(), self._blacklist.get(sender.lower(), None))
        if not list_entry:
            return message
        
        self._log('--- applying blacklist rule {0} to message', str(list_entry), rec=rec)
        
        if not list_entry['action'].lower() in ['d', 'n', 'e', 'ne', 'en']:
            # invalid
            self._log('!!! unsupported blacklist rule "{0}"', list_entry['action'], rec=rec)
            return message
        
        add_expires=False
        add_xnay=False
    
        if list_entry['action'].lower() == 'd' and not mode.lower() == 'reactor':
            self._log('--- blacklist rule "drop"', rec=rec, verbosity=2)
            return None
            
        elif mode.lower() == 'news2mail':
            #D=N=E=NE/EN=drop
            self._log('--- blacklist rule D=N=E=NE/EN "drop"', rec=rec, verbosity=2)
            return None

        elif mode.lower() == 'mail2news':
            if list_entry['action'].lower() in ['ne', 'en','n']:
                add_xnay = True
            if list_entry['action'].lower() in ['ne', 'en', 'e']:
                add_expires = True

        elif mode.lower() == 'reactor':
            if list_entry['action'].lower() in ['ne','en','n','d']:
                add_xnay = True
            if list_entry['action'].lower() in ['ne','en','e']:
                add_expires = True

        if add_xnay:
            self._log('--- blacklist rule "xnay"', rec=rec, verbosity=2)
            try:
                message.replace_header('X-No-Archive', 'yes')
            except KeyError:
                message._headers.append(('X-No-Archive', 'yes'))
                
        if add_expires:
            if not list_entry.get('param', None):
                self._log('!!! blacklist rule "expires" missing a parameter', rec=rec)
            else:
                try:
                    delay=long(list_entry['param'])
                    expires=time.strftime(r"%d %b %Y %H:%M:%S %z", time.localtime(time.time() + (86400*delay)))
                    self._log('--- blacklist rule "expires" => {0}', expires, rec=rec, verbosity=2)
                    try:
                        message.replace_header('Expires', expires)
                    except KeyError:
                        message._headers.append(('Expires', expires))
                except ValueError:
                    self.log('!!! blacklist rule "expires" needs a *numeric* parameter.')

        return message
    