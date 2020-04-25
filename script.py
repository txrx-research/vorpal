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
from tqdm import tqdm

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
		parser.add_argument('-sh', '--shards', type=int, default=64, help="shards to simulate")
		parser.add_argument('-t', '--tps', type=int, default=100, help="number of transactions globally per second to added to mempool")
		parser.add_argument('-s', '--slot', type=float, default=12.0, help="seconds per slot (decimal)")
		parser.add_argument('-d', '--duration', type=int, default=60, help="duration of time to simulate (seconds)")
		parser.add_argument('-b', '--blocklimit', type=int, default=30, help="transactions per shard block limit")
		parser.add_argument('-ds', '--dist', type=DistributionType.getType, default=DistributionType(0), help="distribution of contracts within the shards (uniform, binomial, normal)")
		parser.add_argument('-cs', '--crossshard', type=float, default=0.01, help="probability a cross-shard call will occur within a transaction")
		parser.add_argument('-c', '--collision', type=float, default=0.01, help="probability a transaction will experience a mutated state and cause a reversion of the transaction")
		parser.add_argument('-sw', '--sweep', action='store_true', help="sweeps the probability for the test duration (eg: 0.25, 0 -> 0.25)")
		parser.add_argument("-o", '--output', type=argparse.FileType('w'), help="path to file for saving output")

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

		def generateRandomTransaction(probability):
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
				weights = [1 - probability, probability]
				if(numpy.random.choice(choices, p=weights)): break
			return transaction

		class TransactionLog(list):
			def __init__(self, transaction):
				self.transaction = transaction

		def logTransaction(transaction, beaconChain, transaction_logs):
			log = transaction_logs.get(id(transaction))
			if log == None:
				log = TransactionLog(transaction)
			for i in range(transaction_logs.get("lastBlock"), len(beaconChain)):
				beaconBlock = beaconChain[i]
				for shardBlock in beaconBlock:
					if shardBlock != None:
						for receipt in shardBlock:
							if receipt.transactionId == id(transaction):
								log.append(receipt)
			transaction_logs[id(transaction)] = log
			transaction_logs["lastBlock"] = len(beaconChain)
				

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

		def add_transactions_to_mempool(mempool, transactionLog, queue, transactions_size, probability):
			for i in range(transactions_size):
				randomTransaction = generateRandomTransaction(probability)
				queue[randomTransaction[0].shard].append(randomTransaction)
				mempool[randomTransaction.id] = randomTransaction
				transactionLog.append(randomTransaction)


		mempool = {}
		transaction_log = []
		progress_bar = tqdm(total=args.duration)
		progress_bar.desc = "Simulation Running"

		def update_progress_bar(progress_bar, env, tick):
			while True:
				progress_bar.update(tick)
				yield env.timeout(tick)

		def new_slot(env, shard, tick):
			while True:
				# before slot
				yield env.timeout(tick)
				# after slot
				shard.produceShardBlock()
				shard.commitShardBlock()
		
		def add_tps(crossshard, is_sweep, duration, env, mempool, tps):
			while True:
				yield env.timeout(1)
				probability = calc_crossshard_probability(crossshard, duration, env.now, is_sweep)
				add_transactions_to_mempool(mempool, transaction_log, queue, tps, probability)
				env.total_generated_transactions += tps

		def calc_slot(time, slot_time):
			return int(time / slot_time)

		def output_data(file, beacon_chain, time_elapsed, transaction_log):
			file.write(csv.transaction_segments_per_block(beaconChain))
			file.write(csv.transactions_per_block(beaconChain))
			file.write(csv.stats(args, time_elapsed, beaconChain, transaction_log, env.total_generated_transactions))
			file.write(csv.config(args))
		
		def calc_crossshard_probability(probability, duration, now, is_sweep):
			if is_sweep: return (now / duration) *  probability
			return probability
				
		env = simpy.Environment()
		env.total_generated_transactions = 0
		env.progress = 0
		env.process(add_tps(args.crossshard, args.sweep, args.duration, env, mempool, args.tps))
		for i in range (args.shards):
			shard = Shard(i, None, onNewShardBlock, beaconChain, mempool, args.blocklimit, queue, receiptQueue, receiptTxnQueue, args.collision)
			env.process(new_slot(env, shard, args.slot))
		env.process(update_progress_bar(progress_bar, env, 1))
	
		env.run(until=args.duration)
		progress_bar.close()
		output_data(args.output, beaconChain, (time.time() - start_time), transaction_log)


	except KeyboardInterrupt:
		output_data(args.output, beaconChain, (time.time() - start_time), transaction_log)
	except Exception:
		traceback.print_exc(file=sys.stdout)
	sys.exit(0)

if __name__ == "__main__":
    main()
# print(numpy.random.binomial(1, (63/64), 1000))