# encoding: utf-8
#
#  fucore.py 
#
# Copyright (c) 2010 René Köcher <shirk@bitspin.org>
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
# Created by René Köcher on 2010-04-03.
#

import sys, os, re, unittest
import email, email.message, json
import synfu.config, synfu.fucore

from contextlib import nested

class FUCoreBase(synfu.fucore.FUCore):
    def __init__ (self, conf):
        super(FUCoreBase, self).__init__()
        self._conf = conf.reactor

    def __del__(self):
        # supress syslog.closelog() message
        pass

class FUCoreSuite(unittest.TestCase):
    def setUp(self):
        self._data_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
        
        self._cfg = synfu.config.Config.get(os.path.join(self._data_path, 'synfu.conf'))
        
        #
        # prepare sample messages for _is_cancel()
        #
        with nested(open(os.path.join(self._data_path, 'fucore_00_detect_cancel_00.msg'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_00_detect_cancel_01.msg'), 'r')) \
             as (msg_is_cancel, msg_no_cancel):
             
            self._detect_cancel = [
                email.message_from_file(msg_is_cancel),
                email.message_from_file(msg_no_cancel)
            ]
        
        #
        # prepare sample messages for _find_list_tag()
        #
        with nested(open(os.path.join(self._data_path, 'fucore_01_find_list_tag_00.msg'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_01_find_list_tag_01.msg'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_01_find_list_tag_02.msg'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_01_find_list_tag_03.msg'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_01_find_list_tag_04.msg'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_01_find_list_tag_05.msg'), 'r')) \
             \
             as (list_tag_listid      , list_tag_xlistid,
                 list_tag_listpost    , list_tag_xlistpost,
                 list_tag_synfu_simple, list_tag_synfu_multi):
        
            self._list_tags = [
                ('List-Id'     , 'test'      , email.message_from_file(list_tag_listid)),
                ('List-Post'   , 'test'      , email.message_from_file(list_tag_listpost)),
                ('X-List-Id'   , 'test'      , email.message_from_file(list_tag_xlistid)),
                ('X-List-Post' , 'test'      , email.message_from_file(list_tag_xlistpost)),
                ('X-SynFU-Tags', '(test)'    , email.message_from_file(list_tag_synfu_simple)),
                ('X-SynFU-Tags', '(test|neu)', email.message_from_file(list_tag_synfu_multi))
            ]
        
        #
        # prepare sample messages for _filter_headers()
        #
        with nested(open(os.path.join(self._data_path, 'fucore_02_filter_headers_00.msg') , 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_00.json'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_01.msg') , 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_01.json'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_02.msg') , 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_02.json'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_03.msg') , 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_03.json'), 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_04.msg') , 'r'),
                    open(os.path.join(self._data_path, 'fucore_02_filter_headers_04.json'), 'r')) \
             \
             as (headers_ignored , headers_ignored_exp,
                 headers_unicode , headers_unicode_exp,
                 headers_outlook , headers_outlook_exp,
                 headers_mid     , headers_mid_exp,
                 headers_unicode2, headers_unicode2_exp):
             
             self._headers = [
                ('ignored headers' , email.message_from_file(headers_ignored) , False, json.load(headers_ignored_exp)),
                ('Unicode subject' , email.message_from_file(headers_unicode) , False, json.load(headers_unicode_exp)),
                ('Outlook fixes'   , email.message_from_file(headers_outlook) , True , json.load(headers_outlook_exp)),
                ('Message-Id fixes', email.message_from_file(headers_mid)     , False, json.load(headers_mid_exp)),
                ('Unicode List-Tag', email.message_from_file(headers_unicode2), True , json.load(headers_unicode2_exp))
             ]
        
        self._fucore = FUCoreBase(self._cfg)
    
    def test_00_detect_cancel(self):
        self.assertTrue(self._fucore._is_cancel(self._detect_cancel[0]) , "Control: cancel was'nt detected!")
        self.assertFalse(self._fucore._is_cancel(self._detect_cancel[1]), "Control: cancel was detected!")
    
    def test_01_find_listtag(self):
        for (header, tag, msg) in self._list_tags:
            sys.stderr.write('\n    {0}..'.format(header))
            
            self.assertEqual(tag, self._fucore._find_list_tag(msg, plain=True),
                            'Match against {0}: header failed.'.format(header))
        
        sys.stderr.write('\n -- ')
    
    def test_02_filter_headers(self):
        tag = re.compile('(?i)\s*\[\s*(test|ÄÖÜ)[^]]*\]')
        
        for (what, msg, outlook_hacks, exp) in self._headers:
            sys.stderr.write('\n    {0}.. '.format(what))
            
            res = self._fucore._filter_headers(tag, msg._headers, outlook_hacks)
            res = [[k, v] for k,v in res]
            res.sort()
            exp.sort()
            
            self.assertEqual(exp, res)
    
        sys.stderr.write('\n -- ')

