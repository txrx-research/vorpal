from enum import Enum
import random

import threading
import time
import shard
import logging
import queue
import constants
import argparse

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

class DistributionType(Enum):
	UNIFORM = 0
	BINOMIAL = 1
	NORMAL = 2
	CHAOS = 3

	def getType(string):
		if(string.lower() == "uniform"): return DistributionType(0)
		if(string.lower() == "binomial"): return DistributionType(1)
		if(string.lower() == "normal"): return DistributionType(2)
		if(string.lower() == "chaos"): return DistributionType(3)

parser = argparse.ArgumentParser(description='Ethereum 2.0 Coss-Shard Simulation Commands')
parser.add_argument('--shards', type=int, default=64, help="shards to simulate")
parser.add_argument('--txns', type=int, default=100, help="number of transactions to simulate")
parser.add_argument('--slot', type=int, default=6000, help="milliseconds per slot")
parser.add_argument('--time', type=int, default=-1, help="length of time for the simulation to run (milliseconds). -1 means indefinite execution")
parser.add_argument('--receipts', type=int, default=30, help="receipt limit per shard block")
parser.add_argument('--dist', type=DistributionType.getType, default=DistributionType(0), help="distribution of contracts within the shards (uniform, binomial, normal, chaos)")
parser.add_argument('--crossshard', type=float, default=0.5, help="probability a cross-shard call will occur within a transaction")
parser.add_argument('--collision', type=float, default=0.5, help="probability a transaction will experience a mutated state and cause a reversion of the transaction")

args = parser.parse_args()

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
		shard =  random.randrange(0, args.shards, 1)
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
			beaconChain.append(list([None] * args.shards))
	beaconChain[block.index][shard] = block

mempool = Mempool()
randomTransaction = generateRandomTransaction(6)
mempool.append(randomTransaction)
transactionsToLog = list()
transactionsToLog.append(randomTransaction)

transactionLogs = {}
transactionLogs["lastBlock"] = 0

shards = list()
for i in range (args.shards):
	_shard = shard.Shard(i, None, onNewShardBlock, beaconChain, mempool)
	shards.append(_shard)

while(len(mempool) > 0):
	for _shard in shards:
		_shard.produceShardBlock()
	for _shard in shards:
		_shard.commitShardBlock()
	for transaction in transactionsToLog:
		logTransaction(transaction, beaconChain, transactionLogs)
logging.info(outputTransactionLog(transactionLogs, transactionsToLog))