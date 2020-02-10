import logging
import time

RECEIPT_LIMIT = 30

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

class ShardBlock(list):
    def __init__(self, index):
        self.index = index

class Receipt:
    def __init__(self, transactionId, shard, sequence, nextShard):
        self.transactionId = transactionId
        self.shard = shard
        self.sequence = sequence
        self.nextShard = nextShard
    
    def toString(self):
        return "*** Receipt ***\nTransaction Id: {0}\nShard: {1}\nSequence: {2}\nNextShard: {3}\n".format(self.transactionId, self.shard, self.sequence, self.nextShard)

class Shard:	
    def __init__(self, shard, strategy, onNewShardBlock, beaconChain, mempool):
        self.shard = shard
        self.strategy = strategy
        self.onNewShardBlock = onNewShardBlock
        self.beaconChain = beaconChain
        self.mempool = mempool
        self.nextBlock = ShardBlock(0)
        self.hasProcessedTransaction = list()
        self.hasProcessedReceipt = list()

    def processTransactionFromForeignReceipt(self, foreignReceipt, transaction):
        for i in range(foreignReceipt.sequence, len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                self.nextBlock.append(Receipt(id(transaction), self.shard,  i, transactionFragment.shard))
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(id(transaction), self.shard,  i, None))
                return True

    def processTransaction(self, transaction):
        for i in range(len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                self.nextBlock.append(Receipt(id(transaction), self.shard, i, transactionFragment.shard))
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(id(transaction), self.shard, i, None))
                return True
    
    def processMempoolTransactions(self):
        for transaction in self.mempool:
            if transaction[0].shard == self.shard and transaction not in self.hasProcessedTransaction:
                self.hasProcessedTransaction.append(transaction)
                if self.processTransaction(transaction):
                    self.mempool.remove(transaction)

    def processReceiptTransactions(self):
        for beaconBlock in self.beaconChain:
            for shardBlock in beaconBlock:
                if shardBlock != None:
                    for receipt in shardBlock:
                        if receipt.nextShard == self.shard:
                            for transaction in self.mempool:
                                if id(transaction) == receipt.transactionId and receipt not in self.hasProcessedReceipt:
                                    self.hasProcessedReceipt.append(receipt)
                                    if self.processTransactionFromForeignReceipt(receipt, transaction):
                                        self.mempool.remove(transaction)
                                    break
    def commitShardBlock(self):
        self.onNewShardBlock(self.shard, self.nextBlock)
        self.nextBlock = ShardBlock(self.nextBlock.index + 1)

    def produceShardBlock(self):
        self.processReceiptTransactions()
        self.processMempoolTransactions()
        

