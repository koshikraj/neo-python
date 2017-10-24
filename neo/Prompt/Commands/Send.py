from prompt_toolkit import prompt
import traceback

from neo.Core.Blockchain import Blockchain
from neo.Fixed8 import Fixed8
from neo.Core.TX.Transaction import TransactionOutput,ContractTransaction
from neo.Core.TX.InvocationTransaction import InvocationTransaction
from neo.SmartContract.ContractParameterContext import ContractParametersContext
from neo.Network.NodeLeader import NodeLeader
from neo.Prompt.Utils import parse_param,get_arg,get_from_addr
import json
from neo.Core.TX.TransactionAttribute import TransactionAttribute,TransactionAttributeUsage
import pdb

def construct_and_send(prompter, wallet, arguments):
    try:
        if not wallet:
            print("please open a wallet")
            return
        if len(arguments) < 3:
            print("Not enough arguments")
            return


        arguments, from_address = get_from_addr(arguments)

        to_send = get_arg(arguments)
        address_to = get_arg(arguments, 1)
        amount = get_arg(arguments, 2)


        assetId = None

        if to_send.lower() == 'neo':
            assetId = Blockchain.Default().SystemShare().Hash
        elif to_send.lower() == 'gas':
            assetId = Blockchain.Default().SystemCoin().Hash
        elif Blockchain.Default().GetAssetState(to_send):
            assetId = Blockchain.Default().GetAssetState(to_send).AssetId

        scripthash_to = wallet.ToScriptHash(address_to)
        if scripthash_to is None:
            print("invalid address")
            return

        scripthash_from = None

        if from_address is not None:
            scripthash_from = wallet.ToScriptHash(from_address)

        f8amount = Fixed8.TryParse(amount)
        if f8amount is None:
            print("invalid amount format")
            return

        if f8amount.value % pow(10, 8 - Blockchain.Default().GetAssetState(assetId.ToBytes()).Precision) != 0:
            print("incorrect amount precision")
            return

        fee = Fixed8.Zero()
        if get_arg(arguments, 3):
            fee = Fixed8.TryParse(get_arg(arguments, 3))

        output = TransactionOutput(AssetId=assetId, Value=f8amount, script_hash=scripthash_to)
        tx = ContractTransaction(outputs=[output])
        ttx = wallet.MakeTransaction(tx=tx, change_address=None, fee=fee,from_addr=scripthash_from)

        if ttx is None:
            print("insufficient funds")
            return

        passwd = prompt("[Password]> ", is_password=True)

        if not wallet.ValidatePassword(passwd):
            print("incorrect password")
            return

        standard_contract = wallet.GetStandardAddress()
        data = standard_contract.Data
        tx.Attributes = [TransactionAttribute(usage=TransactionAttributeUsage.Script,
                                              data=data)]


        context = ContractParametersContext(tx)
        wallet.Sign(context)

        if context.Completed:

            tx.scripts = context.GetScripts()


            wallet.SaveTransaction(tx)

#            print("will send tx: %s " % json.dumps(tx.ToJson(),indent=4))

            relayed = NodeLeader.Instance().Relay(tx)

            if relayed:
                print("Relayed Tx: %s " % tx.Hash.ToString())
            else:
                print("Could not relay tx %s " % tx.Hash.ToString())

        else:
            print("Could not sign transaction")
            return




    except Exception as e:
        print("could not send: %s " % e)
        traceback.print_stack()
        traceback.print_exc()


def construct_contract_withdrawal(prompter, wallet, arguments):

    if len(arguments) < 4:
        print("not enough arguments")
        return False

    #AG5xbb6QqHSUgDw8cHdyU73R1xy4qD7WEE neo AdMDZGto3xWozB1HSjjVv27RL3zUM8LzpV 20
    from_address = get_arg(arguments,0)
    to_send = get_arg(arguments,1)
    to_address = get_arg(arguments, 2)
    amount = get_arg(arguments, 3)

    assetId = None

    if to_send.lower() == 'neo':
        assetId = Blockchain.Default().SystemShare().Hash
    elif to_send.lower() == 'gas':
        assetId = Blockchain.Default().SystemCoin().Hash
    elif Blockchain.Default().GetAssetState(to_send):
        assetId = Blockchain.Default().GetAssetState(to_send).AssetId

    scripthash_to = wallet.ToScriptHash(to_address)
    if scripthash_to is None:
        print("invalid address")
        return False

    scripthash_from = wallet.ToScriptHash(from_address)

    f8amount = Fixed8.TryParse(amount)
    if f8amount is None:
        print("invalid amount format")
        return False

    if f8amount.value % pow(10, 8 - Blockchain.Default().GetAssetState(assetId.ToBytes()).Precision) != 0:
        print("incorrect amount precision")
        return False


    wallet_contract = wallet.GetContract(scripthash_from)

    if wallet_contract is None:
        print("please import this contract into your wallet before withdrawing from it")
        print("Example: import contract_addr {SCRIPT_HASH} {YOUR_PUB_KEY}")
        print("Alternatively, you can use add watch_addr {ADDR}")
        return False

    output = TransactionOutput(AssetId=assetId, Value=f8amount, script_hash=scripthash_to)
    withdraw_tx = InvocationTransaction(outputs=[output])
    withdraw_constructed_tx = wallet.MakeTransaction(tx=withdraw_tx,
                                                     change_address=None,
                                                     fee=Fixed8.Zero(),
                                                     from_addr=scripthash_from)

