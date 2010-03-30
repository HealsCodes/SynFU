.. _appendix-a:

Appendix A: Synfu example config
=================================

The following synfu.conf was taken from a test system
and represents a working sample.

.. code-block:: yaml

        --- !<tag:news.piratenpartei.de,2009:synfu/reactor>
        settings:
              outlook_hacks  : yes
              complex_footer : yes
              strip_notes    : no
              verbose        : yes
              verbosity      : 2

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

            - nntp : pirates.de.region.hh.misc
              smtp : .*list.hh.aktive
              from : aktive@piratenpartei-hamburg.de
              sender: mail2news@nordpiraten.de
              force_tag: PPD-HH
              
            - nntp : pirates.de.region.hh.test
              smtp : .*test.lists.piratenpartei-hamburg.de
              from : test@piratenpartei-hamburg.de
              sender: mail2news@nordpiraten.de

            - nntp : pirates.de.test
              smtp : .*test.lists.piratenpartei.de
              from : test@lists.piratenpartei.de
              force_tag: PPD-HH

            - nntp : pirates.de.talk.politik.etc.pflege
              smtp : .*ag-pflege.lists.piratenpartei.de
              from : ag-pflege@lists.piratenpartei.de

            - nntp : pirates.de.region.nw.ak.gesundheit
              smtp : .*nrw-ak-gesundheit.lists.piratenpartei.de
              from : nrw-ak-gesundheit@lists.piratenpartei.de

            - nntp : pirates.de.talk.politik.etc.pflege
              smtp : .*ag-pflege.lists.piratenpartei.de
              from : ag-pflege@lists.piratenpartei.de

            - nntp : pirates.de.talk.politik.etc.gesundheit
              smtp : .*ag-gesundheitswesen.lists.piratenpartei.de
              from : ag-gesundheitswesen@lists.piratenpartei.de

            - nntp : pirates.de.region.sn
              smtp : .*sachsen.lists.piratenpartei.de
              from : sachsen@lists.piratenpartei.de

            - nntp : pirates.de.region.he.darmstadt
              smtp : .*darmstadt.piratenpartei-hessen.de
              from : darmstadt@piratenpartei-hessen.de

            - nntp : pirates.de.region.ni.misc
              smtp : .*aktive-nds.lists.piraten-nds.de
              from : aktive-nds@lists.piraten-nds.de

            - nntp : pirates.de.region.ni.braunschweig
              smtp : .*braunschweig.lists.piratenpartei-niedersachsen.de
              from : bs-piraten@gomex.de

            - nntp : pirates.de.region.rp.neustadt
              smtp : .*rlp-neustadt@lists.piratenpartei.de
              from : rlp-neustadt@lists.piratenpartei.dee

            - nntp : pirates.de.region.sh.misc
              smtp : .*diskurs.lists.piratenpartei-sh.de
              from : diskurs@lists.piratenpartei-sh.de
              sender: mail2news@nordpiraten.de

            - nntp : pirates.de.region.sh.announce
              smtp : .*ankuendigungen.lists.piratenpartei-sh.de
              from : ankuendigungen@lists.piratenpartei-sh.de
              sender: mail2news@nordpiraten.de

        ...
