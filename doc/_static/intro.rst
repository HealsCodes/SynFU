Introduction
=============

So what is SynFU all about?
----------------------------

| SynFU (short for *SynCom Filter Utilities*) is a comprehensive set of easy-to-setup,
| easy-to-use tools for NNTP<-->Mail two way sync.

The development takes part as a component of the so called SynCom_ concept developed by the `AG Parteikommunikation`_, a working group of the `Piratenpartei Deutschland`_.

At the current state SynFU provides three components:

	- :ref:`synfu-reactor`: a handsome filter for mailing list messages
	- :ref:`synfu-news2mail`: a drop-in replacement for INN_'s news2mail.pl
	- :ref:`synfu-mail2news`: a drop-in replacement for INN_'s mail2news.pl

:ref:`synfu-reactor` started out as a simple filter to remove mailman signatures from messages before passing them to the INN_ import scripts.
Soon more features where added and the result is a flexible mail filter able to correct many malformed message headers *as well* as removing mailman and generic mailing list signatures.

:ref:`synfu-news2mail` and :ref:`synfu-mail2news` where created in to supersede the original INN_ scripts.
They have the benefit of being more configurable and more flexible than their counterparts.

Why should I use it?
---------------------

SynFU is open source, which means you can download, modify and redistribute the source according to the terms of the `Simplified BSD License`_.

It provides benefits in performance and configurability while keeping the exposed interface compatible to INN_.

***Because, you have the choice to!***

.. _SynCom:
	http://wiki.piratenpartei.de/AG_Parteikommunikation#SynCom

.. _`AG Parteikommunikation`:
	http://wiki.piratenpartei.de/AG_Parteikommunikation

.. _`Piratenpartei Deutschland`:
	http://www.piratenpartei.de/

.. _INN:
	http://www.eyrie.org/~eagle/software/inn/

.. _`Simplified BSD License`:
	http://opensource.org/licenses/bsd-license.php