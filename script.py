from enum import Enum
import random
import sys, traceback
import numpy
import uuid
import pickle
from hashlib import sha256
import toml
import os
import math

from shard import Shard
import argparse
import stats
import time
import simpy
from tqdm import tqdm

CONFIG_PATH = "config.toml"
TRANSACTION_SET_PATH = "transaction_set"
config = toml.load(CONFIG_PATH)

class Mempool(list):
	pass

class TransactionSegment:	
	def __init__(self, shard, is_collision, size):
		self.shard = shard
		self.is_collision = is_collision

class Transaction(list):
	def __init__(self, id):
		self.id = id
		pass

def main():
	try:
		parser = argparse.ArgumentParser(description='Ethereum 2.0 Coss-Shard Simulation Commands')

		parser.add_argument('-sh', '--shards', type=int, default=config['simulation']['shards'], help="shards to simulate")
		parser.add_argument('-s', '--slot', type=float, default=config['simulation']['slot'], help="seconds per slot (decimal)")
		parser.add_argument('-b', '--blocksize', type=int, default=config['simulation']['blocksize'], help="size of shard blocks (kb)")
		parser.add_argument('-ws', '--witnesssize', type=int, default=config['simulation']['witnesssize'], help="size of Eth1 stateless witness (kb)")
		parser.add_argument('-css', '--transactionsize', type=int, default=config['simulation']['transactionsize'], help="size of a cross-shard transaction receipt (bytes)")

		parser.add_argument('-t', '--tps', type=int, default=config['transactions']['tps'], help="number of transactions globally per second to added to mempool")
		parser.add_argument('-d', '--duration', type=int, default=config['transactions']['duration'], help="duration of time to simulate (seconds)")
		parser.add_argument('-cs', '--crossshard', type=float, default=config['transactions']['crossshard'], help="probability a cross-shard call will occur within a transaction")
		parser.add_argument('-c', '--collision', type=float, default=config['transactions']['collision'], help="probability a transaction will experience a mutated state and cause a reversion of the transaction")
		parser.add_argument('-sw', '--sweep', action='store_true', default=config['transactions']['sweep'], help="sweeps the probability for the test duration (eg: 0.25, 0 -> 0.25)")

		parser.add_argument('-g', '--generate', action='store_true', default=False, help="application will only generate and stores transactions without simulation")
		parser.add_argument("-o", '--output', type=argparse.FileType('w'), default=None, help="path to file for saving output")
		parser.add_argument("-ot", '--outputtransactions', type=argparse.FileType('wb'), default=None, help="path to file for saving output")
		parser.add_argument("-i", '--input', type=argparse.FileType('rb'), default=None, help="path to file to transaction inputs")

		args = parser.parse_args()
			
		def generate_random_transaction(shards, probability, collision_probability):
			transaction = Transaction(uuid.uuid4())
			while True:
				shard = random.randrange(0, shards, 1)
				if len(transaction) > 1:
					if shard == transaction[len(transaction) - 1] and shard + 1 < shards: shard += 1
					elif shard == transaction[len(transaction) - 1] and shard + 1 >= shards: shard -= 1
				transaction_segment = TransactionSegment(shard, numpy.random.choice([True, False], p=[collision_probability, 1 - collision_probability]))
				transaction.append(transaction_segment)
				
				choices = [True, False]
				weights = [1 - probability, probability]
				if(numpy.random.choice(choices, p=weights)): break
				probability = probability/2
			return transaction

		def on_shard_block(beacon_chain, shard, block):
			if(len(beacon_chain) <= block.index):
				for i in range((block.index + 1) - len(beacon_chain)):
					beacon_chain.append(list([None] * args.shards))
			beacon_chain[block.index][shard] = block

		def calc_crossshard_probability(probability, transaction_total, index, is_sweep):
			if is_sweep: return (index / transaction_total) *  probability
			return probability

		def generate_transaction_set(args):
			transaction_set = []
			transaction_total = args.duration * args.tps
			transaction_progress_bar = tqdm(total=transaction_total)
			transaction_progress_bar.desc = "Generating Transactions"
			for i in range(transaction_total):
				probability = calc_crossshard_probability(args.crossshard, transaction_total, i, args.sweep)
				transaction = generate_random_transaction(args.shards, probability, args.collision)
				transaction_set.append(transaction)
				transaction_progress_bar.update(1)
			transaction_progress_bar.close()
			return transaction_set

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

		def add_tps(env, transaction_set):
			while True:
				yield env.timeout(1/args.tps)
				index = int(env.now / (1/args.tps)) - 1
				transaction = transaction_set[index]
				mempool[transaction[0].shard].append(transaction)
				env.total_generated_transactions += 1

		def create_chart(beacon_chain):
			stats.create_transaction_and_segments_per_slot_chart(beacon_chain).savefig(TRANSACTION_SET_PATH + '/' +  transaction_args_hash() + '.transaction_and_segments_per_slot.png')

		def output_data(beacon_chain, time_elapsed, transaction_log, collision_log, env):
			data = ""
			data += stats.transaction_segments_per_block(beacon_chain)
			data += stats.transactions_per_block(beacon_chain)
			if args.sweep: data += stats.probability_over_duration(args.crossshard, env.now, calc_crossshard_probability)
			data += stats.stats(args, time_elapsed, beacon_chain, transaction_log, env.total_generated_transactions, collision_log)
			data += stats.config(args)
			return data

		def transaction_args():
			# duration, tps, crossshard, sweep, collision
			return {"duration": args.duration, "tps": args.tps, "crossshard": args.crossshard, "sweep": args.sweep, "collision": args.collision}

		def transaction_args_hash():
			return sha256(str(transaction_args()).encode()).hexdigest()

		def has_cached_transactions():
			file_to_open = transaction_args_hash() + ".bin"
			walk = os.walk(os.getcwd() + "/" + TRANSACTION_SET_PATH)
			for files in walk:
				for name in files:
					for file in name:
						if file == file_to_open:
							return True
			return False

		# init
		start_time = time.time()
		beacon_chain = list()
		# create mempool
		mempool = list()
		receipt_queue = list()
		for i in range(args.shards):
			mempool.append([])
			receipt_queue.append([])

		transaction_log = []
		transaction_set = []
		collision_log = []
		gas = []
		bandwidth = []
		has_cached_transactions = has_cached_transactions()

		if args.input == None and not has_cached_transactions:
			transaction_set = generate_transaction_set(args)
		else:
			if(args.input == None):
				args.input = open(TRANSACTION_SET_PATH + "/" + transaction_args_hash() + ".bin", "rb")
				print("Recovering cached file")

			transaction_args_pickle = pickle.load(args.input)
			transaction_set = pickle.load(args.input)
			args.input.close()
			# Override the values or transaction based args
			for arg in vars(args):
				if arg in transaction_args_pickle:
					setattr(args, arg, transaction_args_pickle[arg])

		if  not has_cached_transactions:
			file = args.outputtransactions
			if file == None:
				file = open(TRANSACTION_SET_PATH + "/" + transaction_args_hash() + ".bin", "wb")

			pickle.dump(transaction_args(), file)
			pickle.dump(transaction_set, file)

		if args.generate != True:
			progress_bar = tqdm(total=args.duration)
			progress_bar.desc = "Simulation Running"
					
			env = simpy.Environment()
			env.total_generated_transactions = 0
			env.progress = 0
			env.process(add_tps(env, transaction_set))
			blocklimit = (args.blocksize - args.witnesssize) * 1000 / args.transactionsize
			for i in range (args.shards):
				shard = Shard(i, on_shard_block, beacon_chain, blocklimit, mempool, receipt_queue, args.collision, collision_log, gas, bandwidth)
				env.process(new_slot(env, shard, args.slot))
			env.process(update_progress_bar(progress_bar, env, 1))

			env.run(until=args.duration)
			progress_bar.close()
			data = output_data(beacon_chain, (time.time() - start_time), transaction_log, collision_log, env)
			create_chart(beacon_chain)
			if args.output == None:
				file = open(TRANSACTION_SET_PATH + "/" + transaction_args_hash() + ".csv", "w")
				file.write(data)
			else:
				args.output.write(data)

	except KeyboardInterrupt:
		data = output_data(beacon_chain, (time.time() - start_time), transaction_log, collision_log, env)
		create_chart(beacon_chain)
		if args.output == None:
			print(data)
		else:
			args.output.write(data)
	except Exception:
		traceback.print_exc(file=sys.stdout)
	sys.exit(0)

if __name__ == "__main__":
    main()