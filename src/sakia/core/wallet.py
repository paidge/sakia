"""
Created on 1 févr. 2014

@author: inso
"""

from ucoinpy.documents.transaction import InputSource, OutputSource, Transaction
from ucoinpy.key import SigningKey

from ucoinpy.api import bma
from ucoinpy.api.bma import PROTOCOL_VERSION
from ..tools.exceptions import NotEnoughMoneyError, NoPeerAvailable, LookupFailureError
from .transfer import Transfer
from .txhistory import TxHistory
from .registry import IdentitiesRegistry, Identity

from PyQt5.QtCore import QObject, pyqtSignal, QCoreApplication

import logging
import asyncio


class Wallet(QObject):
    """
    A wallet is used to manage money with a unique key.
    """
    refresh_progressed = pyqtSignal(int, int, str)
    refresh_finished = pyqtSignal(list)

    def __init__(self, walletid, pubkey, name, identities_registry):
        """
        Constructor of a wallet object

        :param int walletid: The wallet number, unique between all wallets
        :param str pubkey: The wallet pubkey
        :param str name: The wallet name
        """
        super().__init__()
        self.coins = []
        self.walletid = walletid
        self.pubkey = pubkey
        self.name = name
        self._identities_registry = identities_registry
        self.caches = {}

    @classmethod
    def create(cls, walletid, salt, password, name, identities_registry):
        """
        Factory method to create a new wallet

        :param int walletid: The wallet number, unique between all wallets
        :param str salt: The account salt
        :param str password: The account password
        :param str name: The account name
        """
        if walletid == 0:
            key = SigningKey(salt, password)
        else:
            key = SigningKey(b"{0}{1}".format(salt, walletid), password)
        return cls(walletid, key.pubkey, name, identities_registry)

    @classmethod
    def load(cls, json_data, identities_registry):
        """
        Factory method to load a saved wallet.

        :param dict json_data: The wallet as a dict in json format
        """
        walletid = json_data['walletid']
        pubkey = json_data['pubkey']
        name = json_data['name']
        return cls(walletid, pubkey, name, identities_registry)

    def load_caches(self, app, json_data):
        """
        Load this wallet caches.
        Each cache correspond to one different community.

        :param dict json_data: The caches as a dict in json format
        """
        for currency in json_data:
            if currency != 'version':
                self.caches[currency] = TxHistory(app, self)
                self.caches[currency].load_from_json(json_data[currency])

    def jsonify_caches(self):
        """
        Get this wallet caches as json.

        :return: The wallet caches as a dict in json format
        """
        data = {}
        for currency in self.caches:
            data[currency] = self.caches[currency].jsonify()
        return data

    def init_cache(self, app, community):
        """
        Init the cache of this wallet for the specified community.

        :param community: The community to refresh its cache
        """
        if community.currency not in self.caches:
            self.caches[community.currency] = TxHistory(app, self)

    def refresh_transactions(self, community, received_list):
        """
        Refresh the cache of this wallet for the specified community.

        :param community: The community to refresh its cache
        """
        logging.debug("Refresh transactions for {0}".format(self.pubkey))
        asyncio.ensure_future(self.caches[community.currency].refresh(community, received_list))

    def rollback_transactions(self, community, received_list):
        """
        Rollback the transactions of this wallet for the specified community.

        :param community: The community to refresh its cache
        """
        logging.debug("Refresh transactions for {0}".format(self.pubkey))
        asyncio.ensure_future(self.caches[community.currency].rollback(community, received_list))

    def check_password(self, salt, password):
        """
        Check if wallet password is ok.

        :param salt: The account salt
        :param password: The given password
        :return: True if (salt, password) generates the good public key
        .. warning:: Generates a new temporary SigningKey from salt and password
        """
        key = None
        if self.walletid == 0:
            key = SigningKey(salt, password)
        else:
            key = SigningKey("{0}{1}".format(salt, self.walletid), password)
        return (key.pubkey == self.pubkey)

    async def relative_value(self, community):
        """
        Get wallet value relative to last generated UD

        :param community: The community to get value
        :return: The wallet relative value
        """
        value = await self.value(community)
        ud = community.dividend
        relative_value = value / float(ud)
        return relative_value

    async def value(self, community):
        """
        Get wallet absolute value

        :param community: The community to get value
        :return: The wallet absolute value
        """
        value = 0
        sources = await self.sources(community)
        for s in sources:
            value += s.amount
        return value

    def tx_inputs(self, amount, community):
        """
        Get inputs to generate a transaction with a given amount of money

        :param int amount: The amount target value
        :param community: The community target of the transaction

        :return: The list of inputs to use in the transaction document
        """
        value = 0
        inputs = []
        cache = self.caches[community.currency]

        buf_inputs = list(cache.available_sources)
        for s in cache.available_sources:
            value += s.amount
            s.index = 0
            inputs.append(s)
            buf_inputs.remove(s)
            if value >= amount:
                return (inputs, buf_inputs)

        raise NotEnoughMoneyError(value, community.currency,
                                  len(inputs), amount)

    def tx_outputs(self, pubkey, amount, inputs):
        """
        Get outputs to generate a transaction with a given amount of money

        :param str pubkey: The target pubkey of the transaction
        :param int amount: The amount to send
        :param list inputs: The inputs used to send the given amount of money

        :return: The list of outputs to use in the transaction document
        """
        outputs = []
        inputs_value = 0
        for i in inputs:
            logging.debug(i)
            inputs_value += i.amount

        overhead = inputs_value - int(amount)
        outputs.append(OutputSource(pubkey, int(amount)))
        if overhead != 0:
            outputs.append(OutputSource(self.pubkey, overhead))
        return outputs

    async def send_money(self, salt, password, community,
                   recipient, amount, message):
        """
        Send money to a given recipient in a specified community

        :param str salt: The account salt
        :param str password: The account password
        :param community: The community target of the transfer
        :param str recipient: The pubkey of the recipient
        :param int amount: The amount of money to transfer
        :param str message: The message to send with the transfer
        """
        try:
            blockid = await community.blockid()
            block = await community.bma_access.future_request(bma.blockchain.Block,
                                      req_args={'number': blockid.number})
        except ValueError as e:
            if '404' in str(e):
                return False, "Could not send transfer with null blockchain"

        time = block['medianTime']
        txid = len(block['transactions'])
        if self.walletid == 0:
            key = SigningKey(salt, password)
        else:
            key = SigningKey("{0}{1}".format(salt, self.walletid), password)
        logging.debug("Sender pubkey:{0}".format(key.pubkey))

        try:
            issuer = await self._identities_registry.future_find(key.pubkey, community)
            issuer_uid = issuer.uid
        except LookupFailureError as e:
            issuer_uid = ""

        try:
            receiver = await self._identities_registry.future_find(recipient, community)
            receiver_uid = receiver.uid
        except LookupFailureError as e:
            receiver_uid = ""

        metadata = {'block': None,
                    'time': time,
                    'amount': amount,
                    'issuer': key.pubkey,
                    'issuer_uid': issuer_uid,
                    'receiver': recipient,
                    'receiver_uid': receiver_uid,
                    'comment': message,
                    'txid': txid
                    }
        transfer = Transfer.initiate(metadata)

        self.caches[community.currency]._transfers.append(transfer)

        try:
            result = self.tx_inputs(int(amount), community)
            inputs = result[0]
            self.caches[community.currency].available_sources = result[1][1:]
        except NotEnoughMoneyError as e:
            return False, str(e)
        logging.debug("Inputs : {0}".format(inputs))

        outputs = self.tx_outputs(recipient, amount, inputs)
        logging.debug("Outputs : {0}".format(outputs))
        tx = Transaction(PROTOCOL_VERSION, community.currency,
                         [self.pubkey], inputs,
                         outputs, message, None)
        logging.debug("TX : {0}".format(tx.raw()))

        tx.sign([key])
        logging.debug("Transaction : {0}".format(tx.signed_raw()))
        return (await transfer.send(tx, community))

    async def sources(self, community):
        """
        Get available sources in a given community

        :param sakia.core.community.Community community: The community where we want available sources
        :return: List of InputSource ucoinpy objects
        """
        tx = []
        try:
            data = await community.bma_access.future_request(bma.tx.Sources,
                                     req_args={'pubkey': self.pubkey})
            for s in data['sources']:
                tx.append(InputSource.from_bma(s))
        except NoPeerAvailable as e:
            logging.debug(str(e))
        return tx

    def transfers(self, community):
        """
        Get all transfers objects of this wallet

        :param community: The community we want to get the executed transfers
        :return: A list of Transfer objects
        """
        if community.currency in self.caches:
            return self.caches[community.currency].transfers
        else:
            return []

    def dividends(self, community):
        """
        Get all the dividends received by this wallet

        :param community:  The community we want to get received dividends
        :return: Result of udhistory request
        """
        if community.currency in self.caches:
            return self.caches[community.currency].dividends
        else:
            return []

    def stop_coroutines(self):
        for c in self.caches.values():
            c.stop_coroutines()

    def jsonify(self):
        """
        Get the wallet as json format.

        :return: The wallet as a dict in json format.
        """
        return {'walletid': self.walletid,
                'pubkey': self.pubkey,
                'name': self.name}
