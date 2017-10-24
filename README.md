# QuickStatements to Wikidata RDF converter
Translate [Wikidata statements](https://www.wikidata.org/wiki/Help:Statements) serialized in the [QuickStatements](https://www.wikidata.org/wiki/Help:QuickStatements) tabular format into [Wikidata RDF](https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format) triples.

# Get ready
Don't have [Python 3](https://www.python.org/downloads/)? Install it! And why don't you [upgrade pip](https://pip.pypa.io/en/stable/installing/#upgrading-pip), too?
```
$ git clone https://github.com/marfox/qs2rdf.git
$ pip install -r requirements.txt
```

# Usage
```
$ python qs2rdf.py --help

Usage: qs2rdf.py [OPTIONS] DATASET

Options:
  -o, --output PATH
  -d, --debug
  -l, --logfile FILENAME
  --help                  Show this message and exit.
```

# License
The source code is under the terms of the [GNU General Public License, version 3](http://www.gnu.org/licenses/gpl.html).