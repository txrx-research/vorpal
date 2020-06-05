import numpy


class Gas():
    def __init__(self, type, details, amount):
        self.type = type
        self.details = details
        self.amount = amount

class Bandwidth():
    def __init__(self, type, details, size):
        self.type = type
        self.details = details
        self.size = size

class ShardBlock(list):
    def __init__(self, index):
        self.index = index

class Receipt:
    def __init__(self, transaction_id, shard, sequence, next_shard):
        self.transaction_id = transaction_id
        self.shard = shard
        self.sequence = sequence
        self.next_shard = next_shard

class Shard:	
    def __init__(self, shard, on_shard_block, beacon_chain, blocklimit, mempool, receipt_queue, collision, collision_log, gas, bandwidth):
        self.shard = shard
        self.on_shard_block = on_shard_block
        self.beacon_chain = beacon_chain
        self.next_block = ShardBlock(0)
        self.last_block = 0
        self.blocklimit = blocklimit
        self.mempool = mempool
        self.receipt_queue = receipt_queue
        self.collision = collision
        self.collision_log = collision_log
        self.gas = gas
        self.bandwidth = bandwidth

    def process_transaction_from_foreign_receipt(self, foreign_receipt, transaction):
        index = len(transaction) <= foreign_receipt.sequence + 1 if foreign_receipt.sequence else foreign_receipt.sequence + 1
        return self.process_transaction(transaction, index)

    def process_transaction(self, transaction, index):
        transaction_segment = transaction[index]
        if transaction_segment.is_collision:
            self.collision_log.append(transaction)
        else:
            if index == len(transaction) - 1:
                self.next_block.append(Receipt(transaction.id, self.shard, index, None))
                return True
            else:
                receipt = Receipt(transaction.id, self.shard, index, transaction_segment.shard)
                self.next_block.append(receipt)
                receipt.transaction = transaction
                self.receipt_queue[transaction_segment.shard].append(receipt)
                return False
    
    def process_mempool_transactions(self):
        for transaction in self.mempool[self.shard]:
            if len(self.next_block) < self.blocklimit and transaction[0].shard == self.shard:
                self.process_transaction(transaction, 0)
                self.mempool[self.shard].remove(transaction)

    def process_receipt_transactions(self):
        for r, receipt in enumerate(self.receipt_queue[self.shard]):
            transaction = receipt.transaction
            self.process_transaction_from_foreign_receipt(receipt, transaction)
            del self.receipt_queue[self.shard][r]

    def commitShardBlock(self):
        self.on_shard_block(self.beacon_chain, self.shard, self.next_block)
        self.next_block = ShardBlock(self.next_block.index + 1)
        self.lastBlock = self.last_block + 1

    def produceShardBlock(self):
        self.process_receipt_transactions()
        self.process_mempool_transactions()
        

