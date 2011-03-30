# encoding: utf-8
#
# reactor.py 
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
# Created by René Köcher on 2009-12-19.
#

"""
.. module:: reactor
    :platform: Unix, MacOS, Windows
    :synopsis: Advanced MIME message filter.

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

import sys, re, quopri
import email, email.message, email.header

from synfu.config import Config
from synfu.fucore import FUCore
    
class Reactor(FUCore):
    """
    SynFU reactor implements basic filtering for mailman and other mailing list
    based messages to suit them better for mail2news purposes.
    """
    
    MAILMAN_SIG = [
    	re.compile('^https?://service.piratenpartei.de/listinfo/[^ ]*$', re.M),
    	re.compile('^(__*$|--*$)'),
    ]
    
    MAILMAN_COMPLEX = [
    	re.compile('^.*https?://.*(/mailman)?/listinfo/[^ ]*$', re.M),
    	re.compile('^(__*$|--*$)'),
    ]
    
    SIGN_NOTICE = [
            re.compile('This is a cryptographically signed message in MIME format.', re.M),
            re.compile('This is an OpenPGP/MIME signed message', re.M),
            re.compile('^$')
    ]
    
    BROKEN_MULTIPART = re.compile('^Content-Type: [^;]*; boundary=')
    
    VERSION = '0.3b (based on mutagenX 0.4g)'
    NOTICE  = '(c) 2009-2010 Rene Koecher <shirk@bitspin.org>'
    
    def __init__(self):
        super(Reactor, self).__init__(Config.get().reactor)
        
        self._conf = Config.get().reactor
        self._mm   = email.message_from_file(sys.stdin)
    
    
    def run(self):
        """
        Process a message from :attr:`sys.stdin` and write the result to
        :attr:`sys.stdout`.
        
        The message will be processed according the the global settings.
        
        .. note::
        
            There is no need to import and call this method directly.
            SynFu provides the wrapper script *synfu-reactor.py* for this job.
        """
        if (self._is_cancel(self._mm)):
            sys.exit(0)
            
        self._mm  = self._apply_blacklist(self._mm, 'reactor', 0)
        if not self._mm:
            # should not happen but who knows?
            self._log('--- Message was dropped by blacklist')
            sys.exit(0)
        
        self._mm = self._process(self._mm)
        self._mm.add_header('X-SynFU-Reactor', 
                            Reactor.NOTICE, version=Reactor.VERSION)
        
        print_out = False
        for p in str(self._mm).split('\n')[1:]:
            if self._conf.strip_notes:
                if Reactor.SIGN_NOTICE[0].match(p) and not print_out:
                    print_out = True
                    continue
                    
                if Reactor.SIGN_NOTICE[1].match(p) and not print_out:
                    # mailman is kinky
                    print ''
                    print_out = True
                    continue
                    
                if Reactor.SIGN_NOTICE[2].match(p) and not print_out:
                    continue
                    
            if Reactor.BROKEN_MULTIPART.match(p):
                # multipart *should be* seperated by a newline
                p = p.replace('; boundary=', ';\n boundary=')
                
            print p.replace('\x0d', '')
    
    
    def _process(self, message, rec=0):
        """
        Recursively scan and filter a MIME message.
        
        _process will scan the passed message part for invalid headers
        as well as mailman signatures and modify them according to
        the global settings.
        
        Generic modifications include:
        
            * fixing of broken **References:** and **In-Reply-To** headers
            
            * generic header filtering (see :meth:`FuCore._filter_headers`)
            
            * removal of Mailman or Mailman-like headers (see :meth:`_mutate_part`)
        
        Args:
            message: a :class:`email.message` object containing a set of MIME parts
            rec:  Recursion level used to prettify log messages.
            
        Returns:
            A (probably) filtered / modified :class:`email.message` object. 
        """
        mm_parts    = 0
        text_parts  = 0
        mailman_sig = Reactor.MAILMAN_SIG
        
        self._log('>>> processing {0}', message.get_content_type(), rec=rec)
        
        if self._conf.complex_footer:
            self._log('--- using complex mailman filter', rec=rec)
            mailman_sig = Reactor.MAILMAN_COMPLEX
            
        if message.is_multipart():
            parts = message._payload
        else:
            parts = [message,]
            
        list_tag  = self._find_list_tag(message, rec)
        reference = message.get('References', None)
        in_reply  = message.get('In-Reply-To', None)
        x_mailman = message.get('X-Mailman-Version', None)
        
        message._headers = self._filter_headers(list_tag, message._headers,
                                                self._conf.outlook_hacks, 
                                                self._conf.fix_dateline, rec)
        
        if in_reply and not reference and rec == 0:
            # set References: to In-Reply-To: if where in toplevel
            # and References was not set properly
            self._log('--- set References: {0}', in_reply, rec=rec)
            try:
                # uncertain this will ever happen..
                message.replace_header('References', in_reply)
            except KeyError:
                message._headers.append(('References', in_reply))
                
        for i in xrange(len(parts) - 1, -1, -1):
            # again, crude since we mutate the list while iterating it..
            # the whole reason is the deeply nested structure of email.message
            p = parts[i]
            
            ct = p.get_content_maintype()
            cs = p.get_content_subtype()
            ce = p.get('Content-Transfer-Encoding', None)
            cb = p.get_boundary()
            
            self._log('-- [ct = {0}, cs = {1}, ce = <{2}>]', ct, cs, ce,
                      rec=rec)
            
            if ct == 'text':
                text_parts += 1
                
                payload = p.get_payload(decode=True)
                self._log('--- scan: """{0}"""', payload, rec=rec, verbosity=3)
                
                if mailman_sig[0].search(payload) and \
                   mailman_sig[1].match(payload.split('\n')[0]):
                    
                    self._log('*** removing this part', rec=rec)
                    self._log('--- """{0}"""', payload, rec=rec, verbosity=2)
                    
                    message._payload.remove(p)
                    text_parts -= 1
                    mm_parts   += 1
                    
                elif mailman_sig[0].search(payload):
                    self._log('--- trying to mutate..', rec=rec)
                    
                    (use, mutation) = self._mutate_part(payload, rec)
                    if use:
                        self._log('*** mutated this part', rec=rec)
                        self._log('--- """{0}"""', payload, rec=rec, verbosity=2)
                        
                        payload   = mutation
                        mm_parts += 1
                        
                    # if it was encoded we need to re-encode it
                    # to keep SMIME happy
                    
                    if ce == 'base64':
                        payload = payload.encode('base64')
                        
                    elif ce == 'quoted-printable':
                        payload = quopri.encodestring(payload)
                        
                    p.set_payload(payload)
                    
                elif ct == 'message' or \
                     (ct == 'multipart' and cs in ['alternative', 'mixed']):
                    p = self._process(p, rec + 1)
                     
                else:
                    self._log('--- what about {0}?', p.get_content_type(), rec=rec)
        
        if rec == 0:
            self._log('--- [mm_parts: {0}, text_parts: {1}, x_mailman: {0}]',
                      mm_parts, text_parts, x_mailman, rec=rec)
            
            if x_mailman and mm_parts and not text_parts:
                # if we have
                # - modified the content
                # - no text parts left in outer message
                # - a valid X-Mailmann-Version:
                # --> remove outer message
                self._log('!!! beheading this one..', rec=rec)
                
                mm = message._payload[0]
                for h in message._headers:
                    if h[0] == 'Content-Type':
                        continue
                        
                    try:
                        mm.replace_header(h[0], h[1])
                    except KeyError:
                        mm._headers.append(h)
                        
                return mm
                
        return message
    
    def _mutate_part(self, body, rec=0):
        """
        Mutate a single message part.
        
        This method will analyze and probably modify the passed message
        part if needed. A modification will only occur if the part contains,
        what looks like a mailman signature.
        
        For this purpose the content will be scanned according to the
        specified configuration (complex_footer: yes|no).
        
        Args:
            body: The (decoded) message part including all subparts.
            rec:  Recursion level used to prettify log messages.
            
        Returns:
            A tuple containing the (modified) message part and a flag
            indicating if it was modified.
            Example:
            
            (true, 'body-of-modified-message-part')
        """
        
        mutation = []
        skip     = 0
        mutated  = False
        parts    = body.split('\n')
        
        for i in range(0, len(parts)):
            parts_orig = parts[i]
            
            if self._conf.complex_footer:
                parts[i] = parts[i].strip()
                
                if skip and not parts[i]:
                    skip = 0
                    self._log('--- stop line-skip at {0}', i, rec=rec)
                    
                elif skip:
                    continue
                    
                if Reactor.MAILMAN_COMPLEX[1].match(parts[i]):
                    try:
                        for j in range(i + 1, i + 10):
                            if Reactor.MAILMAN_COMPLEX[1].match(parts[j].strip()):
                                self._log('--- not a mailman signature, reset at {0}', j, rec=rec)
                                skip    = 0
                                break
                            
                            if Reactor.MAILMAN_COMPLEX[0].match(parts[j].strip()):
                                self._log('--- skip lines starting at {0}', j, rec=rec)
                                skip    = 1
                                mutated = True
                                break
                                
                        if skip:
                            continue
                                
                    except IndexError:
                        pass
                        
            else:
                if skip:
                    skip -= 1
                    continue
                    
                parts[i] = parts[i].strip()
                
                if Reactor.MAILMAN_SIG[1].match(parts[i]):
                    try:
                        if Reactor.MAILMAN_SIG[0].match(parts[i + 3].strip()):
                            print_ign('--- skip line(s) {0}-{1}', i, i + 3, rec=rec)
                            skip    = 3
                            mutated = True
                            continue
                            
                    except IndexError:
                        pass
            
            mutation.append(parts_orig)
        return (mutated, '\n'.join(mutation))
    


def ReactorRun():
    """
    Global wrapper for setup-tools.
    """
    try:
        reactor = Reactor()
    except Exception:
        FUCore.log_traceback(None)

    try:
        reactor.run()
    except Exception:
        FUCore.log_traceback(reactor)

