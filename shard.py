import logging
import time

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

class Block(list):
    def __init__(self, index):
        self.index = index

class Receipt:
    def __init__(self, transactionId, shard, sequence, nextShard):
        self.transactionId = transactionId
        self.shard = shard
        self.sequence = sequence
        self.nextShard = nextShard
    
    def toString(self):
        return "Receipt Transaction Id: {0}\n Shard: {1}\n Sequence: {2}\n NextShard: {3}".format(self.transactionId, self.shard, self.sequence, self.nextShard)

class Shard:	
    def __init__(self, shard, strategy, onNewShardBlock, beaconChain, mempool):
        self.shard = shard
        self.strategy = strategy
        self.onNewShardBlock = onNewShardBlock
        self.beaconChain = beaconChain
        self.mempool = mempool
    nextBlock = Block(0)

    def processTransactionFromForeignReceipt(self, foreignReceipt, transaction):
        for i in range(foreignReceipt.sequence, len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                self.nextBlock.append(Receipt(transaction.id, self.shard,  i, transactionFragment.shard))
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(transaction.id, self.shard,  i, None))
                return True

    def processTransaction(self, transaction):
        for i in range(len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                self.nextBlock.append(Receipt(transaction.id, self.shard, i, transactionFragment.shard))
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(transaction.id, self.shard, i, None))
                return True
    
    def processMempoolTransactions(self):
        for transaction in self.mempool:
            if transaction[0].shard == self.shard:
                if self.processTransaction(transaction):
                    self.mempool.remove(transaction)

    def processReceiptTransactions(self):
        for beaconBlock in self.beaconChain:
            for shardBlock in beaconBlock:
                if shardBlock != None:
                    for receipt in shardBlock:
                        if receipt.nextShard == self.shard:
                            for transaction in self.mempool:
                                if transaction.id == receipt.transactionId:
                                    if self.processTransactionFromForeignReceipt(receipt, transaction):
                                        self.mempool.remove(transaction)
                                    break
    def commitShardBlock(self):
        self.onNewShardBlock(self.shard, self.nextBlock)
        self.nextBlock = Block(self.nextBlock.index + 1)

    def produceShardBlock(self):
        # for block in self.beaconChain:
        #     logging.info("Element: %s", block)
        print(self.mempool.toString())
        self.processMempoolTransactions()
        self.processReceiptTransactions()

