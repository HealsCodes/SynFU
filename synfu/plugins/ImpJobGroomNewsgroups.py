# encoding: utf-8
#
# ImpJobGroomNewsgroups.py
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
# Created by René Köcher on 2010-04-28.
#

"""
.. module:: ImpJobGroomNevsgroups
    :platform: Unix, MacOS, Windows
    :synopsis: Periodic Imp - automated newsgroups updating

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

import sys, os, re, urllib2, pkgutil
from BeautifulSoup import BeautifulSoup, StopParsing

from synfu.config import Config
from synfu.imp import ImpJob

class GroomNewsgroups(ImpJob):
    """
    GroomNewsgroups - update newsgroup descriptions via mailman
    
    This Imp-Job will fetch a list of mailman listinfo pages and
    update the configured newsgroups-file using the listdescriptions.
    """
    
    VERSION = '0.3'
    
    def __init__(self):
        super(GroomNewsgroups, self).__init__()
        
        empty_conf = {
            'http_proxy'  : None,
            'https_proxy' : None,
            'listinfo'    : {},
            'newsgroups'  : None
        }
            
        self._conf = self.job_config('groom_newsgroups', empty_conf)
        
        proxy_list = []
        
        if self._conf.http_proxy:
            proxy_list.append(urllib2.ProxyHandler({ 'http' : self._conf.http_proxy }))
            
        if self._conf.https_proxy:
            proxy_list.append(urllib2.ProxyHandler({ 'https': self._conf.https_proxy }))
            
        opener = urllib2.build_opener(*proxy_list)        
        urllib2.install_opener(opener)
        
        # plug in filter settings from postfilter
        self._conf.__setattr__('filters', Config.get().postfilter.filters)
    
    def _required_lists(self):
        """
        Collect required lists.
        
        This method will scan the configured filters and host definitions
        and create a nested tree mapping lists to hosts.
        
        Args:
            --
        
        Returns:
            A dict containing a tree style representation of all lists:
            
            {
                'list.host1.tld' : {
                    'nntp.group.1' : [ 'list-name-1' : None ],
                    'nntp.group.2' : [ 'list-name-2' : None ],
                }
            }
        """

        lists = {}
        
        for f in self._conf.filters:
            if not 'from' in f or \
               not 'nntp' in f:
                continue
        
            filter_list = f['from'].split('@')[0]
            filter_host = f['from'].split('@')[-1]
            filter_desc = f.get('desc', None)
            
            match = False
            for listinfo in self._conf.listinfo:
                if not 'host' in listinfo or \
                   not 'info' in listinfo:
                    continue
             
                if filter_host == listinfo['host']:
                
                    if not listinfo['host'] in lists:
                        lists[listinfo['host']] = {}
                    
                    lists[listinfo['host']][f['nntp']] = [ filter_list,
                                                           filter_desc ]
                    match = True
                    break
            
            if not match:
                if not 'unassigned' in lists:
                    lists['unassigned'] = {}
                
                lists['unassigned'][f['nntp']] = [ filter_list,
                                                   filter_desc ]
        return lists
    
    def _fetch_listinfo(self, url):
        """
        Fetch a listinfo page as a BeautifulSoup tree.

        This method will try to fetch the supplied URL and on success
        return a BeautifulSoup tree ready for processing.

        Args:
            url: A URL containig a mailman listinfo page

        Returns:
            A parse tree as returned by BeautifulSoup() or None on error.
        """
        try:
            data = urllib2.urlopen(url)
            return BeautifulSoup(data)

        except urllib2.HTTPError, eh:
            self._log('!!! failed to fetch "{0}": {1}', url, str(eh))
            return None
            
        except urllib2.URLError, eu:
            self._log('!!! failed to fetch "{0}": {1}', url, str(eu))
            return None
        
        except StopParsing, sp:
            self._log('!!! even BeautifulSoup can\'t parse "{0}": {1}',
                      url, str(sp))
        
        # never reached.
        return None
    
    def _collect_descriptions(self):
        """
        Update list descriptions from mailman listinfo pages.
        
        This method will:
            
            - fetch and parse all configured mailman lists,
            - parse the contained list names and descriptions,
            - complete the tree returned by :meth:_required_lists() as needed
            
        Args:
            --
            
        Returns:
            A tree like :meth:_required_lists() but with additional
            descriptions for each list.
        """
        lists = self._required_lists()
        for host in lists:
            if host == 'unassigned':
                continue
            
            self._log('--- attempting to fetch listinfo for "{0}"...',
                      host)
            
            for li in self._conf.listinfo:
                if not 'host' in li or \
                   not 'info' in li:
                    continue
                
                if li['host'] == host:
                    url = li['info']
                    break
            
            if not url:
                self._log('!!! no url for host "{0}"', host)
                continue
            
            soup = self._fetch_listinfo(url)
            
            if not soup:
                continue
            
            for newsgroup in lists[host]:
                (name, desc) = lists[host][newsgroup]
                
                if desc:
                    self._log('--- using supplied description for newsgroup "{0}"',
                              newsgroup)
                    continue
                    
                service_url = '{0}/{1}'.format(url, name)
                self._log('--- looking for listinfo containing "{0}"', 
                          service_url, verbosity=3)
                
                tag = soup.find('a', href=service_url)
                
                if not tag:
                    self._log('!!! no entry for newsgroup "{0}"', newsgroup)
                    continue
                
                tag = tag.findNext('td')
                
                if not tag:
                    self._log('!!! malformed entry for newsgroup "{0}"', newsgroup)
                    continue
                
                self._log('--- group: "{0}", descr: "{1}"',
                          newsgroup, tag.text, verbosity=2)
                          
                lists[host][newsgroup] = [name, tag.text]
            
        return lists
    
    def needs_run(self, *args):
        return True
        
    def run(self):
        
        self._log('--- using http_proxy : {0}', self._conf.http_proxy)
        self._log('--- using https_proxy: {0}', self._conf.https_proxy)
        
        self._log('--- begin')
        lists = self._collect_descriptions()
        
        self._log('--- updating "{0}"', self._conf.newsgroups)
        try:
            newsgroups = open(self._conf.newsgroups, 'r')
            lines = newsgroups.readlines()
            newsgroups.close()
            
            newsgroups = open(self._conf.newsgroups, 'w')
            for line in lines:
                line = line.strip()
                
                group = line.split(' ', 1)[0].split('\t')[0].strip()
                match = False
                for host in lists:
                    if group in lists[host]:
                        
                        if not lists[host][group][1]:
                            del lists[host][group]
                            break
                        
                        if isinstance(lists[host][group][1], unicode):
                            lists[host][group][1] = lists[host][group][1].encode('UTF-8')
                        
                        self._log('--- updt: {0}\t\t{1}', 
                                  group, lists[host][group][1], verbosity=3)
                        
                        newsgroups.write('{0}\t\t{1}\n'.format(
                                         group, lists[host][group][1]))
                        
                        del lists[host][group]
                        
                        match = True
                        break
                        
                if not match:
                    self._log('--- keep: {0}', line, verbosity=3)
                    newsgroups.write(line + '\n')
            
            # aftermath
            for host in lists:
                for group in lists[host]:
                    if isinstance(lists[host][group][1], unicode):
                        lists[host][group][1] = lists[host][group][1].encode('UTF-8')
                    
                    self._log('--- +new: {0}\t\t{1}',
                              group, lists[host][group][1] or '<None>', verbosity=3)
                    
                    if lists[host][group][1]:
                        newsgroups.write('{0}\t\t{1}\n'.format(
                                        group, lists[host][group][1]))
                    else:
                        # don't record {groupname}\t\tNone
                        newsgroups.write('{0}\t\t\n'.format(group))
            
            newsgroups.close()
            self._log('--- update done.')
            self._log('--- end')
            return True
        
        except IOError, e:
            self._log('!!! failed to update "{0}": {1}'.format(
                      self._conf.newsgroups,
                      str(e)))
            self._log('--- end')
            return False

