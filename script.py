from enum import Enum
import random
import yaml

# configuration
SHARD_COUNT = 64;

# transaction types
class TransactionFragmentType(Enum):
	PAYMENT_TO_EOA = 1
	PAYMENT_TO_SHARD = 2
	PAYMENT_TO_CONTRACT = 3
	CONTRACT_CALL = 4
	CONTRACT_DEPLOY = 5
	EE_DEPLOY = 6

class TransactionFragment:	
	def __init__(self, is_foreign_shard, type):
		self.is_foreign_shard = is_foreign_shard
		self.type = type

class ReportFragment:
	gas_cost = None
	#milliseconds
	time = None

def generateRandomTransaction(size):
	transaction = list()
	for i in range(size):
		isForeign = random.choice([True, False])
		txnFragmentType =  random.choice([1, 2, 3, 4])
		txnFragment = TransactionFragment(isForeign, TransactionFragmentType(txnFragmentType))
		transaction.append(txnFragment)
	return transaction

def simulation(transaction, strategy):
	report = list();
	# mempool time
	for txnFragment in transaction:
		orchReportFragment = orchcestrationTiming(txnFragment, ReportFragment());
		reportFragment = strategy(txnFragment, ReportFragment())
		report.append(reportFragment)
	return report

def receipt(transactionFragment, reportFragment):
	# orchestration timing
	if(transactionFragment.is_foreign_shard){

	}
	# execution timing
	if(txnFragment.type == TransactionFragment.PAYMENT_TO_ACCOUNT):

	else if(txnFragment.type == TransactionFragment.PAYMENT_TO_SHARD):

	else if(txnFragment.type == TransactionFragment.PAYMENT_TO_SHARD):

	else if(txnFragment.type == TransactionFragment.PAYMENT_TO_SHARD):

	return reportFragment;
# application

# txnFragment = TransactionFragment(type(False), TransactionFragmentType.PAYMENT_TO_ACCOUNT)

# print(txnFragment.type)

transaction = generateRandomTransaction(5);
print(transaction[2].type)

	
