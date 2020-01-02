from enum import Enum

class TransactionFragmentType(Enum):
	ACCT_LOOKUP = 1
	PAYMENT_FROM_ACCT = 2
	CONTRACT_CALL = 3

class TransactionFragment:
	isForeignShard = type(False)
	type = TransactionFragmentType(1)

txnFragment = TransactionFragment()

print(txnFragment.type)
	
