from slither import Slither
from slither.core.cfg.node import Node
from slither.core.declarations import FunctionContract
from slither.slithir.operations import Binary


class RepairTarget:
    def __init__(self, source_code: str, slither: Slither, slither_function_node: FunctionContract,
                 slither_statement_node: Node, ir: Binary, ast_root, ast_node):
        self.source_code = source_code
        self.slither = slither
        self.slither_function_node = slither_function_node
        self.slither_statement_node = slither_statement_node
        self.ir = ir
        self.ast_root = ast_root
        self.ast_node = ast_node

    def print_info(self):
        print('[RepairTarget]', end=' ')
        print(self.slither_function_node.contract.name + ':' + self.slither_function_node.name + ':'
              + str(self.ast_node.extract_code(self.source_code, True).split(": ")[0]))
        print('CODE: ' + self.slither_statement_node.source_mapping.content)
        print('OPERATION:', end=' ')
        if self.ast_node.nodeType == 'BinaryOperation':
            print(self.ast_node.leftExpression.extract_code(self.source_code, False), end=' ')
            print('[' + self.ast_node.operator + ']', end=' ')
            print(self.ast_node.rightExpression.extract_code(self.source_code, False))
        elif self.ast_node.nodeType == 'UnaryOperation':
            print('[' + self.ast_node.operator + ']', end=' ')
            print(self.ast_node.subExpression.extract_code(self.source_code, False))
        elif self.ast_node.nodeType == 'Assignment':
            print(self.ast_node.leftHandSide.extract_code(self.source_code, False), end=' ')
            print('[' + self.ast_node.operator + ']', end=' ')
            print(self.ast_node.rightHandSide.extract_code(self.source_code, False))
        print('SSA:', end=' ')
        if self.ast_node.nodeType == 'BinaryOperation':
            print(str(self.ir.variable_left) + ' [' + self.ir.type_str + '] ' + str(self.ir.variable_right), end='')
            print(' --> ' + str(self.ir.lvalue))
        elif self.ast_node.nodeType == 'UnaryOperation':
            print(str(self.ir.variable_left) + ' [' + self.ir.type_str + '] ' + str(self.ir.variable_right), end='')
            print(' --> ' + str(self.ir.lvalue))
        elif self.ast_node.nodeType == 'Assignment':
            print(str(self.ir.variable_left) + ' [' + self.ir.type_str + '] ' + str(self.ir.variable_right), end='')
            print(' --> ' + str(self.ir.lvalue))

    def to_string(self):
        info = '[RepairTarget] '
        info += self.slither_function_node.contract.name + ':' + self.slither_function_node.name + ':'
        info += str(self.ast_node.extract_code(self.source_code, True).split(": ")[0]) + '\n'
        info += 'CODE: ' + self.slither_statement_node.source_mapping.content + '\n'
        info += 'OPERATION: '

        if self.ast_node.nodeType == 'BinaryOperation':
            info += self.ast_node.leftExpression.extract_code(self.source_code, False) + ' '
            info += '[' + self.ast_node.operator + '] '
            info += self.ast_node.rightExpression.extract_code(self.source_code, False) + '\n'
        elif self.ast_node.nodeType == 'UnaryOperation':
            info += '[' + self.ast_node.operator + '] '
            info += self.ast_node.subExpression.extract_code(self.source_code, False) + '\n'
        elif self.ast_node.nodeType == 'Assignment':
            info += self.ast_node.leftHandSide.extract_code(self.source_code, False) + ' '
            info += '[' + self.ast_node.operator + '] '
            info += self.ast_node.rightHandSide.extract_code(self.source_code, False) + '\n'

        info += 'SSA: '
        if self.ast_node.nodeType in ['BinaryOperation', 'UnaryOperation', 'Assignment']:
            info += str(self.ir.variable_left) + ' [' + self.ir.type_str + '] ' + str(self.ir.variable_right)
            info += ' --> ' + str(self.ir.lvalue) + '\n'

        return info

    def get_line_number(self) -> int:
        return int(self.ast_node.extract_code(self.source_code, True).split(": ")[0])
