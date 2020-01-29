from enum import Enum

# configuration
SHARD_COUNT = 64;

# data types
class TransactionFragmentType(Enum):
	PAYMENT_TO_ACCOUNT = 1
	PAYMENT_TO_SHARD = 2
	CONTRACT_WRITE = 3
	CONTRACT_READ = 4

class TransactionFragment:	
	def __init__(self, is_foreign_shard, type):
		self.is_foreign_shard = is_foreign_shard
		self.type = type
		
# application
txnFragment = TransactionFragment(type(False), TransactionFragmentType.PAYMENT_TO_ACCOUNT)

print(txnFragment.type)
	
