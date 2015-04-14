'''
Created on 24 févr. 2015

@author: inso
'''
from .node import Node

import logging
import time

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QMutex, QCoreApplication
from ..watching.watcher import Watcher


class Network(Watcher):
    '''
    A network is managing nodes polling and crawling of a
    given community.
    '''
    nodes_changed = pyqtSignal()
    new_block_mined = pyqtSignal(int)
    stopped_perpetual_crawling = pyqtSignal()

    def __init__(self, currency, nodes):
        '''
        Constructor of a network

        :param str currency: The currency name of the community
        :param list nodes: The nodes of the network
        '''
        super().__init__()
        self._nodes = []
        self._mutex = QMutex()
        self.currency = currency
        self.nodes = nodes
        self._must_crawl = False
        self._is_perpetual = False
        self._block_found = 0

    @classmethod
    def create(cls, node):
        '''
        Create a new network with one knew node
        Crawls the nodes from the first node to build the
        community network

        :param node: The first knew node of the network
        '''
        nodes = [node]
        network = cls(node.currency, nodes)
        nodes = network.crawling()
        block_max = max([n.block for n in nodes])
        for node in nodes:
            node.check_sync(block_max)
        network.nodes = nodes
        network._block_found = network.latest_block
        return network

    def merge_with_json(self, json_data):
        '''
        We merge with knew nodes when we
        last stopped cutecoin

        :param dict json_data: Nodes in json format
        '''
        for data in json_data:
            node = Node.from_json(self.currency, data)
            if node.pubkey not in [n.pubkey for n in self.nodes]:
                self.add_node(node)
                logging.debug("Loading : {:}".format(data['pubkey']))
        for n in self.nodes:
            try:
                n.changed.disconnect()
            except TypeError:
                pass
        self.nodes = self.crawling()

    @classmethod
    def from_json(cls, currency, json_data):
        '''
        Load a network from a configured community

        :param str currency: The currency name of a community
        :param dict json_data: A json_data view of a network
        '''
        nodes = []
        for data in json_data:
            node = Node.from_json(currency, data)
            nodes.append(node)
        block_max = max([n.block for n in nodes])
        for node in nodes:
            node.check_sync(block_max)
        network = cls(currency, nodes)
        network._block_found = network.latest_block
        return network

    def jsonify(self):
        '''
        Get the network in json format.

        :return: The network as a dict in json format.
        '''
        data = []
        for node in self.nodes:
            data.append(node.jsonify())
        return data

    def stop_crawling(self):
        '''
        Stop network nodes crawling.
        '''
        self._must_crawl = False

    def continue_crawling(self):
        if self._is_perpetual:
            return self._must_crawl
        else:
            return True

    @property
    def synced_nodes(self):
        '''
        Get nodes which are in the ONLINE state.
        '''
        return [n for n in self.nodes if n.state == Node.ONLINE]

    @property
    def online_nodes(self):
        '''
        Get nodes which are in the ONLINE state.
        '''
        return [n for n in self.nodes if n.state in (Node.ONLINE, Node.DESYNCED)]

    @property
    def nodes(self):
        '''
        Get all knew nodes.
        '''
        return self._nodes

    @nodes.setter
    def nodes(self, new_nodes):
        '''
        Set new nodes
        '''
        self._mutex.lock()
        try:
            for n in self.nodes:
                try:
                    n.disconnect()
                except TypeError:
                    logging.debug("Error disconnecting node {0}".format(n.pubkey[:5]))

            self._nodes = []
            for n in new_nodes:
                self.add_node(n)
        finally:
            self._mutex.unlock()

    @property
    def latest_block(self):
        '''
        Get latest block known
        '''
        return max([n.block for n in self.nodes])

    def add_node(self, node):
        '''
        Add a node to the network.
        '''
        self._nodes.append(node)
        node.changed.connect(self.handle_change)
        logging.debug("{:} connected".format(node.pubkey))

    def moveToThread(self, thread):
        for n in self.nodes:
            n.moveToThread(thread)
        super().moveToThread(thread)

    def watch(self):
        self.stopped_perpetual_crawling.connect(self.watching_stopped)
        self.start_perpetual_crawling()

    def stop(self):
        self.stop_crawling()

    def start_perpetual_crawling(self):
        '''
        Start crawling which never stops.
        To stop this crawling, call "stop_crawling" method.
        '''
        self._must_crawl = True
        while self.continue_crawling():
            nodes = self.crawling(interval=10)

            new_inlines = [n.endpoint.inline() for n in nodes]
            last_inlines = [n.endpoint.inline() for n in self.nodes]

            hash_new_nodes = hash(tuple(frozenset(sorted(new_inlines))))
            hash_last_nodes = hash(tuple(frozenset(sorted(last_inlines))))

            if hash_new_nodes != hash_last_nodes:
                self.nodes = nodes
                self.handle_change()

        self.stopped_perpetual_crawling.emit()

    @pyqtSlot()
    def handle_change(self):
        node = self.sender()
        logging.debug("Handle change")
        if node.state in (Node.ONLINE, Node.DESYNCED):
            node.check_sync(self.latest_block)
        logging.debug("{0} -> {1}".format(self.latest_block, self.latest_block))
        if self._block_found != self.latest_block:
            logging.debug("New block found : {0}".format(self.latest_block))
            self.new_block_mined.emit(self.latest_block)

        if node.last_change + 3600 < time.time() and \
            node.state in (Node.OFFLINE, Node.CORRUPTED):
            try:
                node.changed.disconnect()
            except TypeError:
                logging.debug("Error : {0} not connected".format(node.pubkey))
                pass
            self.nodes.remove(node)

        QCoreApplication.processEvents()
        logging.debug("Syncing : {0} : last changed {1} : unsynced : {2}".format(node.pubkey[:5],
                                                        node.last_change, time.time() - node.last_change))

        self.nodes_changed.emit()

    def crawling(self, interval=0):
        '''
        One network crawling.

        :param int interval: The interval between two nodes request.
        '''
        nodes = []
        traversed_pubkeys = []
        knew_pubkeys = [n.pubkey for n in self.nodes]
        for n in self.nodes:
            logging.debug(traversed_pubkeys)
            logging.debug("Peering : next to read : {0} : {1}".format(n.pubkey,
                          (n.pubkey not in traversed_pubkeys)))
            if self.continue_crawling():
                n.peering_traversal(knew_pubkeys, nodes,
                                    traversed_pubkeys, interval,
                                    self.continue_crawling)
                QCoreApplication.processEvents()
                time.sleep(interval)

        logging.debug("Nodes found : {0}".format(nodes))
        return nodes
