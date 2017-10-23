#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
from rdflib import Graph, Namespace, URIRef, Literal
from uuid import uuid4 # Random UUIDs for statement nodes
from hashlib import sha1 # SHA-1 hashes for reference nodes
from sys import exit, argv


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

SHA = sha1()


def setup_logger(level='debug', log_filename='conversion.log'):
    """ Convenience function to setup proper logging """
    levels = {'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}
    logger = logging.getLogger(__name__)
    logger.setLevel(levels[level])
    # Message format
    logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(module)s.%(funcName)s #%(lineno)d - %(message)s")
    # Log to file
    fileHandler = logging.FileHandler(log_filename)
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)
    # Log to console
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    return logger


logger = setup_logger()


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


def convert(fin, fout='out.ttl'):
    """ Convert a QuickStatements dataset into a Wikidata RDF one """
    g = Graph()
    setup_prefixes(g)
    with open(fin) as i:
        for statement in i:
            logger.debug(statement)
            elements = statement.strip().split('\t')
            subject = elements[0]
            main_pid = elements[1]
            value = elements[2]
            # TODO handle value
            value = Literal(value)
            st_node = mint_statement_node(subject)
            g.add((URIRef(WD + subject), URIRef(P + main_pid), st_node))
            g.add((st_node, URIRef(PS + main_pid), value))
            quals_and_refs = zip(*[iter(elements[3:])] * 2)
            for (prop, val) in quals_and_refs:
                # TODO handle value
                val = Literal(val)
                if prop.startswith('S'):
                    ref_node = mint_reference_node(val)
                    g.add((st_node, PROV.wasDerivedFrom, ref_node))
                    g.add((ref_node, PR.prop, val))
                else:
                    g.add((st_node, PQ.prop, val))
    with open(fout, 'w') as o:
        # TODO rdlifb seems to randomly ignore some prefixes
        g.serialize(destination=fout, format='turtle')
    return


def mint_statement_node(statement_subject):
    """ Generate a random UUID and mint a valid statement node """
    return URIRef(WDS + statement_subject + '-' + str(uuid4()))


def mint_reference_node(reference_value):
    """ Generate a SHA-1 and mint a valid reference node """
    SHA.update(reference_value.encode('utf-8'))
    return URIRef(WDREF + SHA.hexdigest())


def main():
    convert(argv[1])
    return 0


if __name__ == '__main__':
    exit(main())