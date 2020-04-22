from enum import Enum
import random
import sys, traceback
import numpy
import uuid

import threading
import shard
import logging
import queue
import constants
import argparse
import csv
import time as Time

def main():
	try:
		format = "%(message)s"
		logging.basicConfig(format=format, level=logging.INFO)

		class DistributionType(Enum):
			UNIFORM = 0
			BINOMIAL = 1
			NORMAL = 2

			def getType(string):
				if(string.lower() == "uniform"): return DistributionType(0)
				if(string.lower() == "binomial"): return DistributionType(1)
				if(string.lower() == "normal"): return DistributionType(2)

		parser = argparse.ArgumentParser(description='Ethereum 2.0 Coss-Shard Simulation Commands')
		parser.add_argument('--shards', type=int, default=64, help="shards to simulate")
		parser.add_argument('--tps', type=int, default=100, help="number of transactions globally per second to added to mempool")
		parser.add_argument('--txns', type=int, default=100, help="total number of transactions to simulate")
		parser.add_argument('--slot', type=int, default=6000, help="milliseconds per slot")
		parser.add_argument('--time', type=int, default=-1, help="length of time for the simulation to run (milliseconds). -1 means indefinite execution")
		parser.add_argument('--blocklimit', type=int, default=30, help="transactions per shard block limit")
		parser.add_argument('--dist', type=DistributionType.getType, default=DistributionType(0), help="distribution of contracts within the shards (uniform, binomial, normal)")
		# parser.add_argument('--crossshard', type=float, default=0.5, help="probability a cross-shard call will occur within a transaction")
		parser.add_argument('--collision', type=float, default=0.01, help="probability a transaction will experience a mutated state and cause a reversion of the transaction")

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

		def generateRandomTransaction():
			transaction = Transaction()
			transaction.id = uuid.uuid4()
			while True:
				txnFragmentType =  random.choice([1, 2, 3, 4, 5, 6])
				while True:
					shard =  random.randrange(0, args.shards, 1)
					if len(transaction) < 1: break
					if shard != transaction[len(transaction) - 1]: break
				txnFragment = TransactionFragment(shard, TransactionFragmentType(txnFragmentType))
				transaction.append(txnFragment)
				if(random.choice([True, False])): break
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

		start_time = Time.time()

		# create queue
		queue = list()
		receiptQueue = list()
		receiptTxnQueue = list()
		for i in range(args.shards):
			queue.append([])
			receiptQueue.append([])
			receiptTxnQueue.append([])

		def addTxnToMempool(mempool, queue, txns):
			txns = int(txns)
			for i in range(txns):
				randomTransaction = generateRandomTransaction()
				queue[randomTransaction[0].shard].append(randomTransaction)
				mempool[randomTransaction.id] = randomTransaction


		mempool = {}
		addTxnToMempool(mempool, queue, (args.slot / 1000)  * args.tps)

		#for transaction in mempool:
		#	queue[transaction[0].shard].append(transaction)

		shards = list()
		for i in range (args.shards):
			_shard = shard.Shard(i, None, onNewShardBlock, beaconChain, mempool, args.blocklimit, queue, receiptQueue, receiptTxnQueue, args.collision)
			shards.append(_shard)

		time = args.time

		txn_time = 0
		txn_total = len(mempool)
		while(len(mempool) > 0 and (args.time == -1 or time - args.slot > 0)):
			for _shard in shards:
				_shard.produceShardBlock()
			for _shard in shards:
				_shard.commitShardBlock()
			# print("Block: ", len(beaconChain) - 1)
			# print("Transactions: ", txn_total)
			# print("Mempool: ", len(mempool))
			time = time - args.slot
			txn_time = txn_time + args.slot
			if txn_total + (args.slot / 1000)  * args.tps < args.txns:
				txn_to_add = int((args.slot / 1000)  * args.tps)
				addTxnToMempool(mempool, queue, (args.slot / 1000)  * args.tps)
				txn_total += txn_to_add
			else:
				txn_to_add = (args.txns - txn_total)
				addTxnToMempool(mempool, queue, txn_to_add)
				txn_total = txn_total + txn_to_add
		print(csv.beacon_chain_to_receipt_per_beacon_block(beaconChain))
		print(csv.config_output(args, Time.time() - start_time))

	except KeyboardInterrupt:
		print(csv.beacon_chain_to_receipt_per_beacon_block(beaconChain))
	except Exception:
		traceback.print_exc(file=sys.stdout)
	sys.exit(0)

if __name__ == "__main__":
    main()
# print(numpy.random.binomial(1, (63/64), 1000))