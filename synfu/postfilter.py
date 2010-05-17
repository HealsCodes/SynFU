# encoding: utf-8
#
# postfilter.py
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
# Created by René Köcher on 2009-12-27.
#

"""
.. module:: postfilter
    :platform: Unix, MacOS, Windows
    :synopsis: Mail2News / News2Mail drop-in replacement

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

import sys, re, subprocess
import email, email.message, email.header

from synfu.config import Config
from synfu.fucore import FUCore

class PostFilter(FUCore):
    """
    PostFilter implements two drop-in-replacements for INN_'s 
    mail2news and news2mail scripts.
    
    .. _INN: http://www.eyrie.org/~eagle/software/inn/
    
    """
    
    VERSION = '0.8a'
    NOTICE  = '(c) 2009-2010 Rene Koecher <shirk@bitspin.org>'
    
    def __init__(self, mode=None):
        if mode == 'news2mail':
            Config.get().postfilter.log_filename = \
                    Config.get().postfilter.log_news2mail
        elif mode == 'mail2news':
            Config.get().postfilter.log_filename = \
                    Config.get().postfilter.log_mail2news

        super(PostFilter, self).__init__(Config.get().postfilter)
        
        self._conf = Config.get().postfilter

    def mail2news(self, fobj=sys.stdin):
        """
        This method provides a drop-in-replacement to news2mail.pl used by INN_.
        It expects the same data on :attr:`sys.stdin` and uses the same
        config entry as news2mail.pl.
        
        .. note::
        
            There is no need to import and call this method directly.
            SynFu provides the wrapper script :command:`synfu-mail2news` (see :ref:`synfu-mail2news`) for this job.
        """
        
        self._data = fobj.read()
        
        mm  = email.message_from_string(self._data)
        if (self._is_cancel(mm)):
            return 0
            
        lid = mm.get('List-ID', mm.get('List-Id', None))
        
        if not lid:
            self._log('!!! Unable to find a valid List-Id')
            return 1
        
        cmd_args = { 
            'NNTP_ID' : []
        }
        
        tag_hints = []
        
        for mapping in self._conf.filters:
            
            if not 'exp' in mapping:
                continue
                
            if not mapping['exp'].findall(lid):
                match = False
                for header in ['To', 'Cc']:
                    for cc in mm.get(header, '').split(','):
                        cc = cc.strip()
                        if not cc:
                            continue
                        
                        if mapping['exp'].findall(cc):
                            match = True
                            self._log('--- cross post to "{0}"', cc)
                            break
                
                if not match:
                    continue
            else:
                self._log('--- post to "{0}"', mapping['nntp'])
            
            cmd_args['NNTP_ID'].append(mapping['nntp'])
            
            if 'force_tag' in mapping:
                self._log('--- appending "{0}" to tag hints', mapping['force_tag'], verbosity=2)
                if isinstance(mapping['force_tag'], unicode):
                    tag_hints.append(mapping['force_tag'].encode('UTF-8'))
                else:
                    tag_hints.append(mapping['force_tag'])
            else:
                tag_base = self._find_list_tag(mm, plain=True)
                if tag_base:
                    self._log('--- using list-tags "{0}" as hints', tag_base, verbosity=2)
                    if isinstance(tag_base, unicode):
                        tag_hints.append(tag_base.encode('UTF-8'))
                    else:
                        tag_hints.append(tag_base)
        
        if tag_hints:
            tag_hints = email.header.make_header([(','.join(tag_hints), 'utf-8')])
            
            try:
                mm.replace_header('X-SynFU-Tags', tag_hints)
            except KeyError:
                mm._headers.append(('X-SynFU-Tags', tag_hints))
                
        if cmd_args['NNTP_ID']:
            cmd_args['NNTP_ID'] = ' '.join(cmd_args['NNTP_ID'])

            proc = subprocess.Popen(self._conf.mail2news_cmd.format(cmd_args),
                                    shell=True,
                                    stdin=subprocess.PIPE,
                                    stdout=sys.stdout,
                                    stderr=sys.stderr)
                                    
            proc.communicate(str(mm))
            proc.wait()
            
            self._log('--- sendmail returned: {0}', proc.returncode)
            return proc.returncode
            
        self._log('!!! No matching List-ID for {0}', lid)
        return 1
    
    def news2mail(self, fobj=sys.stdin):
        """
        This method provides a drop-in-replacement to news2mail.pl used by INN_.
        It expects the same data on :attr:`sys.stdin` and uses the same
        config entry as news2mail.pl.
        
        .. note::
        
            There is no need to import and call this method directly.
            SynFu provides the wrapper script :command:`synfu-news2mail` (see :ref:`synfu-news2mail`) for this job.
        """
        
        """
        This is based on *partial* documentation of news2mail.pl and INN
        
        On entry :attr:`sys.stdin` contains a set of::
        
            @token@ list-ids
        
        pairs for each article that needs to be mailed.
        
        According to INN we need to call '*sm*' to get the actual message.
        (which we mangle and filter and then pipe through to sendmail)
        
        """
        ltok  = re.compile(r'\s+')
        
        self._log('--- begin')
        line = fobj.readline()
        while line:
            line = line.strip()
            if not line:
                self._log('--- received an empty line on STDIN - exiting.');
                break
            
            (token, names) = ltok.split(line.strip(), 1)
            addrs          = {}
            
            self._log('--- processing LTOK = \'{0}\'', line, verbosity=2)
            
            # XXX: this could be done !!FASTER!!
            for name in names.split(','):
                name = name.strip()
                for e in self._conf.filters:
                    if not 'nntp' in e or \
                       not 'from' in e:
                        continue
                    
                    if e['nntp'] == name:
                        sender = self._conf.default_sender
                        
                        if 'sender' in e:
                            sender = e['sender']
                        
                        if not sender in addrs:
                                addrs[sender] = set()
                        
                        if 'broken_auth' in e:
                            sender_is_from = True
                        else:
                            sender_is_from = False
                        
                        addrs[sender].update([(e['from'], sender_is_from),])
                        break
            
            if not addrs:
                self._log('!!! No recipients for LTOK = \'{0}\'', line)
                line = fobj.readline()
                continue
            
            self._log('--- addrs: {0}', addrs)
            # now we have one message-token and the lists we should mail it to
            # let's collect and process the actual messages as well as send them.
            sm = subprocess.Popen('{0} -q {1}'.format(self._conf.inn_sm, token),
                                  shell=True,
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=sys.stderr)

            message = sm.communicate()[0]
            if message.strip():
                mm  = email.email.message_from_string(message)
                tag = self._find_list_tag(mm)
                mm._headers = self._filter_headers(tag, mm._headers)
            
                for sender in addrs:
                    try:
                        mm.replace_header('To', ','.join(x[0] for x in addrs[sender]))
                    except KeyError:
                        mm._headers.append(('To', ','.join(x[0] for x in addrs[sender])))
                    
                    try:
                        mm.replace_header('Sender', sender)
                    except KeyError:
                        mm._headers.append(('Sender', sender))
                    
                    if any(x[1] for x in addrs[sender]):
                        # at least one recipient list requires From == Sender
                        # Sieht spannend aus, funktioniert aber vermutlich.
                        msg_from = ','.join(x for x in [mm.get('From', None), sender] if x)
                        try:
                            mm.replace_header('From', msg_from)
                        except KeyError:
                            mm._headers.append(('From', msg_from))
                            
                        self._log('--- at least one recipient requires From == Sender', verbosity=3)
                        self._log('--- therefore I\'m forcing "From:" to {0}', msg_from, verbosity=3)
                        
                    else:
                        msg_from = mm.get('From', sender)
                        
                        self._log('--- this is a clean list', verbosity=3)
                        self._log('--- therefore I\'m keepfing "From:" set to {0}', msg_from, verbosity=3)
                        
                                        
                    for i in xrange(len(mm._headers) - 1, -1, -1):
                        (k, v) = mm._headers[i]
                        
                        if k == 'Newsgroups':
                            mm._headers.remove((k, v))
                            mm._headers.append(('X-Newsgroups', v))
                    
                    mm.add_header('X-SynFU-PostFilter', 
                                  PostFilter.NOTICE, version=PostFilter.VERSION)
                    
                    sendmail = subprocess.Popen(self._conf.news2mail_cmd.format(
                                                {
                                                 'FROM'   : msg_from,
                                                 'SENDER' : sender,
                                                 'HOST'   : self._conf.inn_host
                                                 },
                                                 ' '.join(x[0] for x in addrs[sender])),
                                                 shell=True,
                                                 stdin=subprocess.PIPE,
                                                 stdout=sys.stdout,
                                                 stderr=sys.stderr)
                    sendmail.communicate(str(mm))
                
                line = fobj.readline()
        self._log('--- end')
        return 0
    

def FilterMail2News():
    """
    Global wrapper for setup-tools.
    """
    try:
        filter = PostFilter(mode='mail2news')
    except Exception:
        FUCore.log_traceback(None)

    try:
        sys.exit(filter.mail2news())
    except Exception:
        FUCore.log_traceback(filter)

def FilterNews2Mail():
    """
    Global wrapper for setup-tools.
    """
    try:
        filter = PostFilter(mode='news2mail')
    except Exception:
        FUCore.log_traceback(None)

    try:
        sys.exit(filter.news2mail())
    except Exception:
        FUCore.log_traceback(filter)


