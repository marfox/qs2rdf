#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
import re
import click
from rdflib import Graph, Namespace, URIRef, Literal, XSD
from uuid import uuid4 # Random UUIDs for statement nodes
from hashlib import sha1 # SHA-1 hashes for reference nodes
from urllib.parse import urlparse
from sys import exit


SHA = sha1()

# Minimal set of Wikidata namespaces
BASE_URI = 'http://www.wikidata.org/'
WD = Namespace(BASE_URI + 'entity/')
WDS = Namespace(WD + 'statement/')
WDREF = Namespace(BASE_URI + 'reference/')
P = Namespace(BASE_URI + 'prop/')
PS = Namespace(P + 'statement/')
PQ = Namespace(P + 'qualifier/')
PR = Namespace(P + 'reference/')
PROV = Namespace('http://www.w3.org/ns/prov#')
GEO = Namespace('http://www.opengis.net/ont/geosparql#')

# Value data types matchers
ITEM = re.compile(r'^Q\d+$')
PROPERTY = re.compile(r'^P\d+$')
TIME = re.compile(r'^[+-]\d+-\d\d-\d\dT\d\d:\d\d:\d\dZ\/\d+$')
LOCATION = re.compile(r'^@([+\-]?\d+(?:.\d+)?)\/([+\-]?\d+(?:.\d+))?$')
QUANTITY = re.compile(r'^[+-]\d+(\.\d+)?$')
MONOLINGUAL_TEXT = re.compile(r'^(\w+):("[^"\\]*(?:\\.[^"\\]*)*")$')


def setup_logger(level, log_filename):
    """ Convenience function to setup proper logging """
    levels = {'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}
    logger = logging.getLogger(__name__)
    logger.setLevel(levels[level])
    logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(module)s.%(funcName)s #%(lineno)d - %(message)s")
    # Always log to console
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    # Log to file if given
    if log_filename:
        fileHandler = logging.FileHandler(log_filename)
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)
    return logger


def setup_prefixes(graph):
    """ Set up essential Wikidata namespace prefixes """
    graph.bind('wd', WD)
    graph.bind('wds', WDS)
    graph.bind('wdref', WDREF)
    graph.bind('p', P)
    graph.bind('ps', PS)
    graph.bind('pr', PR)
    graph.bind('pq', PQ)
    graph.bind('geo', GEO)
    graph.bind('prov', PROV)
    return


def convert(fin, fout, logger):
    """ Convert a QuickStatements dataset into a Wikidata RDF one """
    g = Graph()
    setup_prefixes(g)
    for statement in fin:
        elements = statement.strip().split('\t')
        logger.debug(elements)
        subject = elements[0]
        main_pid = elements[1]
        value = handle_value(elements[2], logger)
        st_node = mint_statement_node(subject)
        g.add((URIRef(WD + subject), URIRef(P + main_pid), st_node))
        g.add((st_node, URIRef(PS + main_pid), value))
        quals_and_refs = zip(*[iter(elements[3:])] * 2)
        for (prop, val) in quals_and_refs:
            val = handle_value(val, logger)
            if prop.startswith('S'):
                ref_node = mint_reference_node(val)
                g.add((st_node, PROV.wasDerivedFrom, ref_node))
                g.add((ref_node, PR.prop, val))
            else:
                g.add((st_node, PQ.prop, val))
    # TODO rdlifb seems to randomly ignore some prefixes
    g.serialize(destination=fout, format='turtle')
    return


def handle_value(value, logger):
    """
    Handle value data types.
    See https://www.wikidata.org/wiki/Help:QuickStatements#Command_sequence_syntax
    """
    # Item
    if ITEM.match(value):
        item = URIRef(WD + value)
        logger.debug('Item. From [%s] to [%s]' % (value, item.n3()))
        return item
    # Monolingual text
    elif MONOLINGUAL_TEXT.match(value):
        match = MONOLINGUAL_TEXT.match(value)
        literal = Literal(match.group(2).strip('"'), lang=match.group(1))
        logger.debug('Monolingual text. From [%s] to [%s]' % (value, literal.n3()))
        return literal
    # Time YYYY-MM-DDThh:mm:ssZ
    elif TIME.match(value):
        # TODO handle precision via a complex RDF value
        time, precision = value.split('/')
        # Ensure compatibility with the old format, like
        # +00000000931-01-01T00:00:00Z/9
        year, rest = time[1:].split('-', 1)
        # Years have always 4 digits
        year = '%04d' % int(year)
        time = Literal(time[0] + year + '-' + rest, datatype=XSD.dateTime)
        logger.debug('Time. From [%s] to [%s]' % (value, time.n3()))
        return time
    # Location
    elif LOCATION.match(value):
        match = LOCATION.match(value)
        lat = match.group(1)
        lon = match.group(2)
        # Point(12.482777777778 41.893055555556)
        point = Literal('Point(%s %s)' % (lon, lat), datatype=GEO.wktLiteral)
        logger.debug('Location. From [%s] to [%s]' (value, point.n3()))
        return point
    # Quantity
    elif QUANTITY.match(value):
        quantity = Literal(value, datatype=XSD.decimal)
        logger.debug('Quantity. From [%s] to [%s]' % (value, quantity.n3()))
        return quantity
    else:
        no_quotes = value.strip('"')
        parsed = urlparse(no_quotes)
        # URL
        if parsed.scheme.find('http') == 0 and parsed.netloc:
            url = URIRef(no_quotes)
            logger.debug('URL. From [%s] to [%s]' % (value, url.n3()))
            return url
        # Plain string
        else:
            plain_literal = Literal(no_quotes)
            logger.debug('Plain literal. From [%s] to [%s]' % (value, plain_literal.n3()))
            return plain_literal


def mint_statement_node(statement_subject):
    """ Generate a random UUID and mint a valid statement node """
    return URIRef(WDS + statement_subject + '-' + str(uuid4()))


def mint_reference_node(reference_value):
    """ Generate a SHA-1 and mint a valid reference node """
    SHA.update(reference_value.encode('utf-8'))
    return URIRef(WDREF + SHA.hexdigest())


@click.command()
@click.argument('dataset', type=click.File())
@click.option('--output', '-o', type=click.Path(dir_okay=False), default='output.ttl')
@click.option('--debug', '-d', is_flag=True, default=False)
@click.option('--logfile', '-l', type=click.File('w'), default=None)
def main(dataset, output, debug, logfile):
    logger = setup_logger('debug', logfile) if debug else setup_logger('info', logfile)
    convert(dataset, output, logger)
    return 0


if __name__ == '__main__':
    exit(main())