import logging
import time
import constants
import numpy

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
    def __init__(self, shard, strategy, onNewShardBlock, beaconChain, mempool, txnBlockLimit, queue, receiptQueue, receiptTxnQueue, collision):
        self.shard = shard
        self.strategy = strategy
        self.onNewShardBlock = onNewShardBlock
        self.beaconChain = beaconChain
        self.mempool = mempool
        self.nextBlock = ShardBlock(0)
        self.lastProcessedBlock = 0
        self.lastBlock = 0
        self.txnBlockLimit = txnBlockLimit
        self.queue = queue
        self.receiptQueue = receiptQueue
        self.receiptTxnQueue = receiptTxnQueue
        self.collision = collision

    def processTransactionFromForeignReceipt(self, foreignReceipt, transaction):
        for i in range(foreignReceipt.sequence, len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                receipt = Receipt(transaction.id, self.shard, i, transactionFragment.shard)
                self.nextBlock.append(receipt)
                self.receiptQueue[transactionFragment.shard].append(receipt)
                self.receiptTxnQueue[transactionFragment.shard].append(transaction)
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(transaction.id, self.shard,  i, None))
                return True

    def processTransaction(self, transaction):
        for i in range(len(transaction)):
            transactionFragment = transaction[i]
            if transactionFragment.shard != self.shard:
                receipt = Receipt(transaction.id, self.shard, i, transactionFragment.shard)
                self.nextBlock.append(receipt)
                self.receiptQueue[transactionFragment.shard].append(receipt)
                self.receiptTxnQueue[transactionFragment.shard].append(transaction)
                return False
            if i == len(transaction) - 1:
                self.nextBlock.append(Receipt(transaction.id, self.shard, i, None))
                return True
    
    def processMempoolTransactions(self):
        for transaction in self.queue[self.shard]:
            if len(self.nextBlock) < self.txnBlockLimit and transaction[0].shard == self.shard:
                if self.isCollision():
                    del self.mempool[transaction.id]
                elif self.processTransaction(transaction):
                    del self.mempool[transaction.id]
                self.queue[self.shard].remove(transaction)

    def isCollision(self):
        choices = [True, False]
        weights = [self.collision, 1 - self.collision]
        return numpy.random.choice(choices, p=weights)

    def processReceiptTransactions(self):
        for r, receipt in enumerate(self.receiptQueue[self.shard]):
            if len(self.nextBlock) < self.txnBlockLimit:
                for t, transaction in enumerate(self.receiptTxnQueue[self.shard]):
                    if transaction.id == receipt.transactionId:
                        if self.isCollision():
                            del self.mempool[transaction.id]
                        elif self.processTransactionFromForeignReceipt(receipt, transaction):
                            del self.mempool[transaction.id]
                        del self.receiptQueue[self.shard][r]
                        del self.receiptTxnQueue[self.shard][t]

    def commitShardBlock(self):
        self.onNewShardBlock(self.shard, self.nextBlock)
        self.nextBlock = ShardBlock(self.nextBlock.index + 1)
        self.lastBlock = self.lastBlock + 1

    def produceShardBlock(self):
        self.processReceiptTransactions()
        self.processMempoolTransactions()
        

