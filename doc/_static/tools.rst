.. _tools:

Tools
======

.. _synfu-reactor:

SynFU.Reactor
--------------

Reactor provides a flexible approach for mail filtering and preparation. It can be (and for `SynCom`_ is) used as a tool to prepare messages for NNTP integration.

The following features are implemented:

	- removal of mailman or 'complex' signature lines:

		| If enabled this feature will detect and remove mailman signatures (inline and MIME-parts).
		| In 'complex' mode possible signature parts will be matched against a set
		| of regular expressions which enables arbitrary (multi-multi-line) signatures to be removed.

	- removal of list-tags in Subject-header:

		| If the Subject-header contains a matching list-tag then this tag will be removed.

	- fix for broken (aka. outlook style) forward and reply tags in Subject-header:

		| If enabled subjects containing localized versions of 'RE' and 'FWD' will be replaced
		| with RFC compliant versions.

	- fix missing / incorrect Referencing- and In-Reply headers

		| If the message lacks a Referencing-header but provides In-Reply-To,
		| then the missing header will be set accordingly.

Synopsis
..........

:command:`synfu-reactor`

.. program:: synfu-reactor

.. cmdoption:: -c <path/to/synfu.conf>

	Specify path to synfu.conf


Supported configuration
.......................

.. code-block:: yaml

	--- !<tag:news.piratenpartei.de,2009:synfu/reactor>
	settings:
		outlook_hacks  : yes
		complex_footer : yes
		strip_notes    : no
		verbose        : yes
 		verbosity      : 2

.. table::

	================ ================== ============
	parameter        supported values   description 
	================ ================== ============
	outlook_hacks    yes / no           Filter outlook tags for RE:, FWD: etc. and replace them with RFC tags.
	complex_footer   yes / no           Switch between simple mailman and generic mailing list signature filter.
	strip_notes      yes / no           Blaa...             
	verbose          yes / no           Enable logging to syslog.
	verbosity        0 - 999            Set log verbosity (0 = no logging)
	================ ================== ============


SynFu.Postfilter
----------------
.. _synfu-mail2news:

SynFu.Mail2News
................

Mail2News provides a drop-in replacement for mail2news.pl provided by the default `INN`_ installation.
Since the final command (in the example: :command:`mailpost`) is configurable a theoretical setup could feed messages to virtually any NNTP system.

Mail2News was designed to filter it's output through :ref:`synfu-reactor`.
While this step is optional Mail2News will provide special List-Tag hints and other useful information to ease the filtering process.

Synopsis
++++++++++

:command:`synfu-mail2news`

.. program:: synfu-mail2news

.. cmdoption:: -c <path/to/synfu.conf>

	Specify path to synfu.conf


.. _synfu-news2mail:

SynFu.News2Mail
................

News2mail provides a drop-in replacement for news2mail.pl provided by the default `INN`_ installation.

By design messages are expected on :const:`STDIN` and are assumed to have the following format::

	@sm-message-token@ listid[, listid[, listid]]

:const:`STDIN` is processes line by line with an arbitrary number of messages sent per processed line.
:const:`@sm-message-token@` will be used to query :attr:`inn_sm` for the message body, which in turn will be processed.

Processing involves scanning for List-Tags / List-Ids and replacement / expansion of the Sender-header with the default- or list specific sender. 


Synopsis
++++++++++

:command:`synfu-news2mail`

.. program:: synfu-news2mail

.. cmdoption:: -c <path/to/synfu.conf>

	Specify path to synfu.conf


Supported configuration
.......................

.. code-block:: yaml

	--- !<tag:news.piratenpartei.de,2009:synfu/postfilter>
	settings:
		inn_sm         : /usr/lib/news/bin/sm
		inn_host       : news.piratenpartei.de
		verbose        : yes
		verbosity      : 2
		default_sender : mail2news@piratenpartei.de
		mail2news_cmd  : |
			/usr/local/bin/synfu-reactor |
			/usr/lib/news/bin/mailpost -b /tmp -x In-Reply-To:User-Agent -d pirates {0[NNTP_ID]}
		news2mail_cmd  : |
			/usr/sbin/sendmail -oi -oem -ee -odq -f "{0[FROM]}" -p "NNTP:{0[HOST]}" {1}
	
	filters:
	      
		- nntp : pirates.de.region.hh.test
		  smtp : .*test.lists.piratenpartei-hamburg.de
		  from : test@piratenpartei-hamburg.de
		 sender: mail2news@nordpiraten.de
	
		- nntp : pirates.de.test
		  smtp : .*test.lists.piratenpartei.de
		  from : test@lists.piratenpartei.de
	
		- nntp : pirates.de.talk.politik.etc.pflege
		  smtp : .*ag-pflege.lists.piratenpartei.de
		  from : ag-pflege@lists.piratenpartei.de


.. table::

	============== ================== ===========
	parameter      supported values   description
	============== ================== ===========
	inn_sm         filesystem path    Path to INN :command:`sm` binary used by news2mail to fetch messages.
	inn_host       string             Hostname provided as a replacement pattern in news2mail_cmd.
	verbose        yes / no           Enable logging to syslog.
	verbosity      0 - 999            Set log verbosity (0 = no logging)
	default_sender mail address       The default Sender: used by mail2news.
	mail2news_cmd  shell command      Command used by mail2news to deploy messages to NNTP.
	news2mail_cmd  shell commond      Command used by news2mail to deplay messages to mailing lists.
	filters        list of filters    See the following table for details.
	============== ================== ===========


The config parameter **filters** contains a list of filter entries with each entry defining the mapping for one mailing list.
The following parameters are recognized in a filter definition:

.. table::

	============== ================== ===========
	parameter      supported values   description
	============== ================== ===========
	nntp           NNTP group id      Used to map NNTP groups to mailing lists and vice versa.
	smtp           regular expression Used to map mailing lists to NNTP groups and vice versa.
	from           mail address       Used in From:-header and supplied as replacement {0[FROM]} in news2mail_cmd
	sender         mail address       [*optional*] Overwrite default_sender on a per-list basis
	force_tag      string             [*optional*] Force List-Tag for :ref:`synfu-reactor`.
	broken_auth    yes / no           [*optional*] Some lists expect From: and Sender: tags to match..
	============== ================== ===========


.. _`SynCom`: 
	http://wiki.piratenpartei.de/AG_Parteikommunikation#SynCom

.. _`INN`:
	http://www.eyrie.org/~eagle/software/inn/
