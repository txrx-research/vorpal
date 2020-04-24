from enum import Enum
import random
import sys, traceback
import numpy
import uuid

import threading
from shard import Shard
import logging
import queue
import constants
import argparse
import csv
import time
import simpy

def main():
	try:
		txn_total = 0
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
		parser.add_argument('--slot', type=float, default=12.0, help="seconds per slot (decimal)")
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
				
				choices = [True, False]
				weights = [1 - 0.25, 0.25]
				if(numpy.random.choice(choices, p=weights)): break
			return transaction

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

		start_time = time.time()

		# create queue
		queue = list()
		receiptQueue = list()
		receiptTxnQueue = list()
		for i in range(args.shards):
			queue.append([])
			receiptQueue.append([])
			receiptTxnQueue.append([])

		def addTxnToMempool(mempool, transactionLog, queue, txns):
			txns = int(txns)
			for i in range(txns):
				randomTransaction = generateRandomTransaction()
				queue[randomTransaction[0].shard].append(randomTransaction)
				mempool[randomTransaction.id] = randomTransaction
				transactionLog.append(randomTransaction)


		mempool = {}
		transactionLog = []

		def new_slot(env, shard, tick):
			while True:
				# before slot
				yield env.timeout(tick)
				shard.produceShardBlock()
				shard.commitShardBlock()

				# after slot
		
		def add_tps(env, mempool, tps):
			while True:
				yield env.timeout(1)
				addTxnToMempool(mempool, transactionLog, queue, tps)
				env.total_generated_transactions += tps

		def calc_slot(time, slot_time):
			return int(time / slot_time)

		def output_data(beacon_chain, time_elapsed, transaction_log):
				print(csv.receipts_per_block(beaconChain))
				print(csv.transactions_per_block(beaconChain))
				print(csv.stats(args, time_elapsed, beaconChain, transactionLog, env.total_generated_transactions))
				print(csv.config_output(args))
				
		env = simpy.Environment()
		env.total_generated_transactions = 0
		env.process(add_tps(env, mempool, args.tps))
		for i in range (args.shards):
			shard = Shard(i, None, onNewShardBlock, beaconChain, mempool, args.blocklimit, queue, receiptQueue, receiptTxnQueue, args.collision)
			env.process(new_slot(env, shard, args.slot))
	
		env.run(until=500)
		output_data(beaconChain, (time.time() - start_time), transactionLog)


	except KeyboardInterrupt:
		print(csv.receipts_per_block(beaconChain))
	except Exception:
		traceback.print_exc(file=sys.stdout)
	sys.exit(0)

if __name__ == "__main__":
    main()
# print(numpy.random.binomial(1, (63/64), 1000))