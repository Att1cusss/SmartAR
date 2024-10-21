import os
from slither import Slither
from slither.core.declarations import FunctionContract
from PathConfig import CONTRACTS_DIR
from graphviz import Digraph


def print_function_cfg(contract_name: str,
                       function_name: str,
                       contract_path: str = os.path.join(CONTRACTS_DIR, 'sample.sol')):
    command = 'slither ' + contract_path + ' --print cfg'
    os.system(command)
    for root, dirs, files in os.walk(CONTRACTS_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            if '-' + contract_name + '-' in file and function_name in file:
                output_path = os.path.join(CONTRACTS_DIR, contract_name + '.' + function_name + '.png')
                command = 'dot ' + str(file_path) + ' -Tpng -o ' + output_path
                os.system(command)
            if '.dot' in file:
                os.remove(file_path)


def print_function_ssa(slither_function_node: FunctionContract):
    print(f'[+] printing ssa of function: {slither_function_node.contract.name}::{slither_function_node.name}')
    for node in slither_function_node.nodes:
        print(f'---------------node_id: {node.node_id} ---------------------')
        for ssa in node.irs_ssa:
            print(ssa)
    print()


def print_function_ssa_use_name(slither: Slither, contract_name, function_name):
    for contract in slither.contracts:
        if contract.name == contract_name:
            for function in contract.functions:
                if function.name == function_name:
                    print_function_ssa(function)
                    return


def print_expression_tree(root):
    dot = visualize_tree(root)
    dot.render('tree', format='png', view=True)


def add_nodes_edges(tree, dot=None):
    if dot is None:
        dot = Digraph()
    node_label = f"{str(tree.variable)}\n{tree.op}" if tree.op else str(tree.variable)
    dot.node(str(id(tree)), node_label)
    if tree.left:
        dot.edge(str(id(tree)), str(id(tree.left)), "L")
        add_nodes_edges(tree.left, dot)
    if tree.right:
        dot.edge(str(id(tree)), str(id(tree.right)), "R")
        add_nodes_edges(tree.right, dot)
    return dot


def visualize_tree(tree):
    dot = add_nodes_edges(tree)
    return dot
