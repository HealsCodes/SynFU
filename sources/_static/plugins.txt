.. _plugins:

Plugins
=======

.. _GroomNewsgroups:

GroomNewsgroups
----------------------------------

GroomNewsgroups is a reference implementation for :class:`synfu.imp.ImpJob` based plugins and provides an easy way to update a `INN`_ formatted newsgroups list with descriptions provided by mailman.

The following features are implemented:

	- retrieval of group descriptions via mailman listinfo:

		| GroomNewsGroups will fetch and parse all configured listinfo pages
		| and collect the mailing list descriptions.
	
	- static descriptions for groups without listinfo:
	
		| A static description can be used to replace or overwrite the
		| description of a newsgroup

	- partial integration with the filter list used by :ref:`synfu-postfilter`

		| The optional **description** can be used to assign
		| a static description to a filter definition

Synopsis
..........

:command:`GroomNewsGroups`

.. program:: synfu-imp

Supported configuration
.......................

.. code-block:: yaml

	--- !<tag:news.piratenpartei.de,2010:synfu/imp>
	# ...
	jobs:
	    # ...
	    groom_newsgroups:
	      newsgroups : tests/data/misc/newsgroups
	      http_proxy : http://host:port
	      https_proxy: http://host:port

	      listinfo:
	         - host: lists.piratenpartei.de
	           info: https://service.piratenpartei.de/mailman/listinfo
	# ...

.. table::

	================ ================== ============
	parameter        supported values   description 
	================ ================== ============
	newsgroups       string             Path to `INN`_ newsgroups file
	http_proxy       URL                A HTTP-Proxy used while fetching listinfo pages
	https_proxy      URL                A HTTPS-Proxy used while fetching listinfo pages
	listinfo         listinfo mapping   See the following table for details.
	================ ================== ============

The config parameter **listinfo** contains a list of mailman listinfo URLs along with a email host used to map this listinfo page to the newsgroups in the :ref:`synfu-postfilter` filter list.
The following parameters are recognized in a listinfo definition:

.. table::

	============== ==================== ===========
	parameter      supported values     description
	============== ==================== ===========
	host           partial mail address Used to map listinfo pages to mailing lists in the :ref:`synfu-postfilter` settings.
	info           URL                  The URL used to fetch the corresponding mailman listinfo page
	============== ==================== ===========

.. _`SynCom`: 
	http://wiki.piratenpartei.de/AG_Parteikommunikation#SynCom

.. _`INN`:
	http://www.eyrie.org/~eagle/software/inn/
