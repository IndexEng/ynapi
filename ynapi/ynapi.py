import requests
import json
import logging
import sys
import datetime

class BudgetSession():
    """Is a temporary representation of your YNAB account. It is initially configured
       with the API key and can incrementally be populated with account transaction and
       other info, minimising the total number of times the API is accessed"""

    def __init__(self, API_token):
        """Configures the budget session with the API token / API Key"""

        logging.info("Configuring API request")
        if len(API_token) != 64:
            logging.error("API Key is too short, check config file is correct")
            sys.exit(1)
        bearer = "Bearer " + API_token
        self.header = {"Authorization" : bearer}
        self.params = {'access_token': API_token}

    def retrieve_account_list(self, budget_id):
        """Copies the account list from YNAB server into budget session"""

        try:
            url = "https://api.youneedabudget.com/v1/budgets/{}/accounts".format(budget_id)
        except:
            logging.error("Something went wrong accessing the YNAB API")
            sys.exit(1)
        r = requests.get(url, headers=self.header)
        if r.status_code is not 200:
            #TODO : Make error match the actual status code description
            logging.error("Something went wrong accessing YNAB account list, status code {}".format(r.status_code))
            sys.exit(1)
        ynab_account_dict_list = json.loads(r.text)['data']['accounts']
        return ynab_account_dict_list

    def find_account_id(self, account_list, account_number):
        '''Given an account list and full account number, retreives YNAB account id'''
        account_id = ''
        for account in account_list:
            if account['note'] is not None:
                if account_number in account['note']:
                    account_id = account['id']    

        return account_id

    def retrieve_txn_list(self, budget_id, acct_id):

        try:
            url = "https://api.youneedabudget.com/v1/budgets/{}/accounts/{}/transactions".format(budget_id, acct_id)
        except:
            logging.error("Something went wrong while accessing YNAB transaction list")
            sys.exit(1)
        r = requests.get(url, headers=self.header)
        if r.status_code is not 200:
            #TODO : Make error match the actual status code description
            logging.error("Something went wrong accessing the YNAB API, coded")
            sys.exit(1)
        ynab_txn_dict_list = json.loads(r.text)['data']['transactions']
        logging.debug(ynab_txn_dict_list)
        return ynab_txn_dict_list

    def retrieve_budget_activity(self,  month, budget_id, category_id):
        url = "https://api.youneedabudget.com/v1/budgets/{}/months/{}/categories/{}".format(budget_id, month, category_id)
        r = requests.get(url, headers=self.header)
        r_dict = json.loads(r.text)

        return r_dict['data']['category']

    def construct_value_update_txn(self, account_id, corrective_amount, payee_id):
        """Assembles a JSON transaction suitable to be uploaded to YNAB via API"""
        child = {}
        child["account_id"] = account_id
        child["date"] = datetime.date.today().strftime('%Y-%m-%d')
        child["amount"] = int(corrective_amount * 1000)
        child["memo"] = '''#BalanceUpdate #AutoGenerated #ynabi'''
        child["cleared"] = "cleared"
        child["approved"] = False
        child["payee_id"] = payee_id
        parent_json = {}
        parent_json["transaction"] = child
        return json.loads(json.dumps(parent_json))

    def construct_ofx_child_transaction(self, account_id, ofx_txn):
        """Assembles a JSON transaction using an ofx txn object """
        def construct_import_id(txn_date, txn_amount):
            return "{}:{}:{}:1".format("YNAB", txn_amount, txn_date)

        txn_date = ofx_txn.date.strftime('%Y-%m-%d')
        txn_amount = int(ofx_txn.amount * 1000)

        import_id = construct_import_id(txn_date, txn_amount)

        child = {}
        child["account_id"] = account_id
        child["date"] = txn_date
        child["amount"] = txn_amount
        child["memo"] = ofx_txn.memo
        child["cleared"] = "cleared"
        child["approved"] = False
        child["import_id"] = import_id

        return json.loads(json.dumps(child))

    def construct_transaction_list_json(self, transaction_list):
        parent_json = {}
        parent_json["transactions"] = transaction_list

        return json.loads(json.dumps(parent_json))

    def send_transaction_to_YNAB(self, budget_id, account_id, txn_json):
        """Sends an assembled JSON transaction to the an account and budget on YNAB API"""
        url = 'https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(budget_id)
        r = requests.post(url, params=self.params, json=txn_json)
        if r.status_code == 201:
            logging.info("Upload of transaction succeded to account id {}".format(account_id))
            pass
        else:
            logging.error("Upload to YNAB failed, status code {}".format(r.status_code))
            logging.debug(txn_json)
            logging.debug(r.json())
