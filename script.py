from enum import Enum
import random

import threading
import time
import shard
import logging
import queue

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

# configuration timing
SHARD_COUNT = 64
SLOT_TIME = 6.000 # seconds 
global_time_offset = 3000 # milliseconds
MEMPOOL_PROP_MIN = 10 # milliseconds
MEMPOOL_PROP_MAX = 5000 # milliseconds

# configuration gas costs
RECEIPT_GAS_COST = 5000

class Mempool(list):

	def toString(self):
		string = "+++++ Begin Mempool +++++\n"
		for transaction in self:
			string = string + transaction.toString() + "\n"
		string = string + "+++++  End Mempool  +++++\n"
		return string

# transaction types
class TransactionFragmentType(Enum):
	PAYMENT_TO_EOA = 1
	PAYMENT_TO_SHARD = 2
	PAYMENT_TO_CONTRACT = 3
	CONTRACT_CALL = 4
	CONTRACT_DEPLOY = 5
	EE_DEPLOY = 6

class TransactionFragment:	
	def __init__(self, shard, type):
		self.shard = shard
		self.type = type

class Transaction(list):
	def __init__(self):
		pass

	def toString(self):
		string = ""
		string = string + "Transaction Id: {0}\n".format(id(self))
		for i in range(len(self)):
			transactionFragment = self[i]
			string = string + "Shard: {0} Action: {1}".format(transactionFragment.shard, transactionFragment.type)
			if i != len(self) - 1:
				string = string + "\n"
		return string


def generateRandomTransaction(size):
	transaction = Transaction()
	for i in range(size):
		txnFragmentType =  random.choice([1, 2, 3, 4, 5, 6])
		shard =  random.randrange(0, SHARD_COUNT, 1)
		txnFragment = TransactionFragment(shard, TransactionFragmentType(txnFragmentType))
		transaction.append(txnFragment)
	return transaction

def isTransactionComplete(transaction, receipts):
	return receipts[len(receipts) - 1].nextShard == None

class TransactionLog(list):
	def __init__(self, transaction):
		self.transaction = transaction

def logTransaction(transaction, beaconChain, transactionLogs):
	log = transactionLogs.get(id(transaction))
	if log == None:
		log = TransactionLog(transaction)
	for i in range(transactionLogs.get("lastBlock"), len(beaconChain)):
		beaconBlock = beaconChain[i]
		for shardBlock in beaconBlock:
			if shardBlock != None:
				for receipt in shardBlock:
					if receipt.transactionId == id(transaction):
						log.append(receipt)
	transactionLogs[id(transaction)] = log
	transactionLogs["lastBlock"] = len(beaconChain)
		

beaconChain = list()

def outputTransactionLog(transactionLogs, transactionsToLog):
	string = ""
	for transaction in transactionsToLog:
		log = transactionLogs[(id(transaction))]
		if log != None:
			for receipt in log:
				string = string + receipt.toString()
	return string


def onNewShardBlock(shard, block):
	if(len(beaconChain) <= block.index):
		for i in range((block.index + 1) - len(beaconChain)):
			beaconChain.append(list([None] * SHARD_COUNT))
	beaconChain[block.index][shard] = block

mempool = Mempool()
randomTransaction = generateRandomTransaction(6)
mempool.append(randomTransaction)
transactionsToLog = list()
transactionsToLog.append(randomTransaction)

transactionLogs = {}
transactionLogs["lastBlock"] = 0

shards = list()
for i in range (SHARD_COUNT):
	_shard = shard.Shard(i, None, onNewShardBlock, beaconChain, mempool)
	shards.append(_shard)

while(len(mempool) > 0):
	# logging.info(mempool.toString())
	for _shard in shards:
		_shard.produceShardBlock()
	for _shard in shards:
		_shard.commitShardBlock()
	# logging.info("Beacon Block: %s", len(beaconChain) - 1)
	for transaction in transactionsToLog:
		logTransaction(transaction, beaconChain, transactionLogs)
logging.info(outputTransactionLog(transactionLogs, transactionsToLog))
	
