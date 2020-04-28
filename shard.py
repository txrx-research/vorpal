import numpy

class ShardBlock(list):
    def __init__(self, index):
        self.index = index

class Receipt:
    def __init__(self, transaction_id, shard, sequence, next_shard):
        self.transaction_id = transaction_id
        self.shard = shard
        self.sequence = sequence
        self.next_shard = next_shard
    
    def toString(self):
        return "*** Receipt ***\nTransaction Id: {0}\nShard: {1}\nSequence: {2}\nNextShard: {3}\n".format(self.transaction_id, self.shard, self.sequence, self.next_shard)

class Shard:	
    def __init__(self, shard, on_shard_block, beacon_chain, mempool, blocklimit, queue, receipt_queue, receipt_transaction_queue, collision, collision_log):
        self.shard = shard
        self.on_shard_block = on_shard_block
        self.beacon_chain = beacon_chain
        self.mempool = mempool
        self.next_block = ShardBlock(0)
        self.last_block = 0
        self.blocklimit = blocklimit
        self.queue = queue
        self.receipt_queue = receipt_queue
        self.receipt_transaction_queue = receipt_transaction_queue
        self.collision = collision
        self.collision_log = collision_log

    def process_transaction_from_foreign_receipt(self, foreign_receipt, transaction):
        for i in range(foreign_receipt.sequence, len(transaction)):
            transaction_segment = transaction[i]
            if transaction_segment.shard != self.shard:
                receipt = Receipt(transaction.id, self.shard, i, transaction_segment.shard)
                self.next_block.append(receipt)
                self.receipt_queue[transaction_segment.shard].append(receipt)
                self.receipt_transaction_queue[transaction_segment.shard].append(transaction)
                return False
            if i == len(transaction) - 1:
                self.next_block.append(Receipt(transaction.id, self.shard,  i, None))
                return True

    def process_transaction(self, transaction):
        for i in range(len(transaction)):
            transaction_segment = transaction[i]
            if transaction_segment.shard != self.shard:
                receipt = Receipt(transaction.id, self.shard, i, transaction_segment.shard)
                self.next_block.append(receipt)
                self.receipt_queue[transaction_segment.shard].append(receipt)
                self.receipt_transaction_queue[transaction_segment.shard].append(transaction)
                return False
            if i == len(transaction) - 1:
                self.next_block.append(Receipt(transaction.id, self.shard, i, None))
                return True
    
    def process_mempool_transactions(self):
        for transaction in self.queue[self.shard]:
            if len(self.next_block) < self.blocklimit and transaction[0].shard == self.shard:
                if self.is_collision():
                    self.collision_log.append(self.mempool[transaction.id])
                    del self.mempool[transaction.id]
                elif self.process_transaction(transaction):
                    del self.mempool[transaction.id]
                self.queue[self.shard].remove(transaction)

    def is_collision(self):
        choices = [True, False]
        weights = [self.collision, 1 - self.collision]
        return numpy.random.choice(choices, p=weights)

    def process_receipt_transactions(self):
        for r, receipt in enumerate(self.receipt_queue[self.shard]):
            if len(self.next_block) < self.blocklimit:
                for t, transaction in enumerate(self.receipt_transaction_queue[self.shard]):
                    if transaction.id == receipt.transaction_id:
                        if self.is_collision():
                            self.collision_log.append(self.mempool[transaction.id])
                            del self.mempool[transaction.id]
                        elif self.process_transaction_from_foreign_receipt(receipt, transaction):
                            del self.mempool[transaction.id]
                        del self.receipt_queue[self.shard][r]
                        del self.receipt_transaction_queue[self.shard][t]

    def commitShardBlock(self):
        self.on_shard_block(self.beacon_chain, self.shard, self.next_block)
        self.next_block = ShardBlock(self.next_block.index + 1)
        self.lastBlock = self.last_block + 1

    def produceShardBlock(self):
        self.process_receipt_transactions()
        self.process_mempool_transactions()
        

