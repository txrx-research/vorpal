from enum import Enum
import random
import sys, traceback
import numpy
import uuid

from shard import Shard
import argparse
import csv
import time
import simpy
from tqdm import tqdm

def main():
	try:

		parser = argparse.ArgumentParser(description='Ethereum 2.0 Coss-Shard Simulation Commands')
		parser.add_argument('-sh', '--shards', type=int, default=64, help="shards to simulate")
		parser.add_argument('-t', '--tps', type=int, default=100, help="number of transactions globally per second to added to mempool")
		parser.add_argument('-s', '--slot', type=float, default=12.0, help="seconds per slot (decimal)")
		parser.add_argument('-d', '--duration', type=int, default=60, help="duration of time to simulate (seconds)")
		parser.add_argument('-b', '--blocklimit', type=int, default=30, help="transactions per shard block limit")
		# parser.add_argument('-ds', '--dist', type=DistributionType.getType, default=DistributionType(0), help="distribution of contracts within the shards (uniform, binomial, normal)")
		parser.add_argument('-cs', '--crossshard', type=float, default=0.01, help="probability a cross-shard call will occur within a transaction")
		parser.add_argument('-c', '--collision', type=float, default=0.01, help="probability a transaction will experience a mutated state and cause a reversion of the transaction")
		parser.add_argument('-sw', '--sweep', action='store_true', help="sweeps the probability for the test duration (eg: 0.25, 0 -> 0.25)")
		parser.add_argument("-o", '--output', type=argparse.FileType('w'), help="path to file for saving output")
		args = parser.parse_args()

		class Mempool(list):
			pass

		class TransactionSegment:	
			def __init__(self, shard):
				self.shard = shard

		class Transaction(list):
			def __init__(self):
				pass

		def generate_random_transaction(shards, probability):
			transaction = Transaction()
			transaction.id = uuid.uuid4()
			while True:
				shard = random.randrange(0, shards, 1)
				if len(transaction) > 1:
					if shard == transaction[len(transaction) - 1] and shard + 1 < shards: shard += 1
					elif shard == transaction[len(transaction) - 1] and shard + 1 >= shards: shard -= 1
				transaction_segment = TransactionSegment(shard)
				transaction.append(transaction_segment)
				
				choices = [True, False]
				weights = [1 - probability, probability]
				if(numpy.random.choice(choices, p=weights)): break
			return transaction

		def on_shard_block(beacon_chain, shard, block):
			if(len(beacon_chain) <= block.index):
				for i in range((block.index + 1) - len(beacon_chain)):
					beacon_chain.append(list([None] * args.shards))
			beacon_chain[block.index][shard] = block
		# init
		start_time = time.time()
		beacon_chain = list()
		# create queue
		queue = list()
		receipt_queue = list()
		receipt_transaction_queue = list()
		for i in range(args.shards):
			queue.append([])
			receipt_queue.append([])
			receipt_transaction_queue.append([])

		def add_transactions_to_mempool(mempool, transactionLog, queue, transactions_size, probability):
			for i in range(transactions_size):
				transaction = generate_random_transaction(args.shards, probability)
				queue[transaction[0].shard].append(transaction)
				mempool[transaction.id] = transaction
				transactionLog.append(transaction)


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

		def output_data(file, beacon_chain, time_elapsed, transaction_log, env):
			file.write(csv.transaction_segments_per_block(beacon_chain))
			file.write(csv.transactions_per_block(beacon_chain))
			if args.sweep: file.write(csv.probability_over_duration(args.crossshard, env.now, calc_crossshard_probability))
			file.write(csv.stats(args, time_elapsed, beacon_chain, transaction_log, env.total_generated_transactions))
			file.write(csv.config(args))
		
		def calc_crossshard_probability(probability, duration, now, is_sweep):
			if is_sweep: return (now / duration) *  probability
			return probability
				
		env = simpy.Environment()
		env.total_generated_transactions = 0
		env.progress = 0
		env.process(add_tps(args.crossshard, args.sweep, args.duration, env, mempool, args.tps))
		for i in range (args.shards):
			shard = Shard(i, on_shard_block, beacon_chain, mempool, args.blocklimit, queue, receipt_queue, receipt_transaction_queue, args.collision)
			env.process(new_slot(env, shard, args.slot))
		env.process(update_progress_bar(progress_bar, env, 1))
	
		env.run(until=args.duration)
		progress_bar.close()
		output_data(args.output, beacon_chain, (time.time() - start_time), transaction_log, env)


	except KeyboardInterrupt:
		output_data(args.output, beacon_chain, (time.time() - start_time), transaction_log, env)
	except Exception:
		traceback.print_exc(file=sys.stdout)
	sys.exit(0)

if __name__ == "__main__":
    main()
# print(numpy.random.binomial(1, (63/64), 1000))