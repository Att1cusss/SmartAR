from typing import Union
from py_solidity_parser.nodes import NodeBase, IterableNodeBase
from slither import Slither
from slither.core.declarations import FunctionContract
from patcher.template import Template

'''
    Currently, in order to be compatible with all versions of smart contracts, 
    the current prototype generates patches based on strings rather than AST. 
    Improvements will be made to the prototype in the future.
'''


class PatchGenerator:
    def __init__(self, contract_source_code: str, contract_compile_version: str, repair_targets: {int: {}},
                 reusable_safemath_functions: {}, slither: Slither, source_node):
        self.slither = slither
        self.contract_source_node = source_node
        self.reusable_safemath_functions = reusable_safemath_functions
        self.repair_targets = repair_targets
        self.contract_compile_version = contract_compile_version
        self.contract_source_code = contract_source_code
        self.contract_type = {}
        self.additional_library_name = 'SmartAR'
        self.additional_library_code = 'contract ' + self.additional_library_name + ' {'
        self.template = Template()
        self.additional_library_function_types = []
        self.additional_inherit_relation_ship = []
        self.additional_using_relation_ship = []
        self.contract_usable_safe_function = {}
        self.replacements = {}
        self.name_of_operator = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div'}
        self.operator_of_operator_type = {'SAFE_ADD': '+', 'SAFE_SUB_1': '-', 'SAFE_MUL': '*', 'SAFE_DIV_1': '/'}
        self.operator_type_of_operator = {'+': 'SAFE_ADD', '-': 'SAFE_SUB_1', '*': 'SAFE_MUL', '/': 'SAFE_DIV_1'}
        for contract in slither.contracts:
            contract_kind = str(contract.contract_kind)
            if contract_kind != 'contract' and contract_kind != 'library':
                continue
            self.contract_type[contract.name] = contract_kind
        self.contract_type[self.additional_library_name] = 'contract'
        for safe_function_type in self.reusable_safemath_functions:
            operator_type = str(safe_function_type).split('@')[0]
            if operator_type == 'SAFE_DIV_2' or operator_type == 'SAFE_SUB_2':
                continue
            operator = self.operator_of_operator_type[operator_type]
            return_data_type = str(safe_function_type).split('@')[1]
            for safe_function in self.reusable_safemath_functions[safe_function_type]:
                safe_function: FunctionContract
                if safe_function.contract.name not in self.contract_usable_safe_function:
                    self.contract_usable_safe_function[safe_function.contract.name] = {}
                if (operator + '@' + return_data_type) not in self.contract_usable_safe_function[
                    safe_function.contract.name]:
                    self.contract_usable_safe_function[safe_function.contract.name][
                        (operator + '@' + return_data_type)] = {}

                self.contract_usable_safe_function[safe_function.contract.name][(operator + '@' + return_data_type)] = \
                    {'safe_function_name': safe_function.name, 'safe_contract_type': 'contract'}

    def patch_line(self, line_number):
        replacement = []
        if line_number not in self.repair_targets:
            return
        repair_target = self.repair_targets[line_number]
        sorted_ast_nodes = sorted(repair_target['ast_nodes'],
                                  key=lambda x: len(x.extract_code(self.contract_source_code, False)))
        repair_target_slither_function_node: FunctionContract = repair_target['function']
        repair_target_function_name = repair_target_slither_function_node.name
        repair_target_contract_name = repair_target_slither_function_node.contract.name
        for ast_node in sorted_ast_nodes:
            ast_node: NodeBase
            bug_code = ast_node.extract_code(self.contract_source_code, False)
            for replace_rule in replacement:
                bug_code = str(bug_code).replace(replace_rule['bug'], replace_rule['fixed'])
            fixed_code = ''
            if ast_node.nodeType == 'BinaryOperation':
                operator = ast_node.operator
                left_expression = ast_node.leftExpression.extract_code(self.contract_source_code, False)
                right_expression = ast_node.rightExpression.extract_code(self.contract_source_code, False)
                for replace_rule in replacement:
                    left_expression = str(left_expression).replace(replace_rule['bug'], replace_rule['fixed'])
                for replace_rule in replacement:
                    right_expression = str(right_expression).replace(replace_rule['bug'], replace_rule['fixed'])
                operand_data_type = ast_node.typeDescriptions['typeString']
                matching_safemath_function = True if (
                        self.operator_type_of_operator[
                            operator] + '@' + operand_data_type in self.reusable_safemath_functions
                        and len(self.reusable_safemath_functions[
                                    self.operator_type_of_operator[operator] + '@' + operand_data_type]) != 0) \
                    else False
                safemath_function_currently_available = True if \
                    (repair_target_contract_name in self.contract_usable_safe_function
                     and (operator + '@' + operand_data_type) in self.contract_usable_safe_function[
                         repair_target_contract_name]) \
                    else False
                if safemath_function_currently_available:
                    safe_function_name = \
                    self.contract_usable_safe_function[repair_target_contract_name][operator + '@' + operand_data_type][
                        'safe_function_name']
                    safe_contract_type = \
                    self.contract_usable_safe_function[repair_target_contract_name][operator + '@' + operand_data_type][
                        'safe_contract_type']
                    if safe_contract_type == 'library':
                        fixed_code = '(' + left_expression + ').' + safe_function_name + '(' + right_expression + ')'
                    if safe_contract_type == 'contract':
                        fixed_code = safe_function_name + '(' + left_expression + ', ' + right_expression + ')'
                elif matching_safemath_function and not safemath_function_currently_available:
                    min_inherit_chain_length = 9999
                    best_safemath_function = None
                    for safe_function_slither_node in self.reusable_safemath_functions[
                        self.operator_type_of_operator[operator] + '@' + operand_data_type]:
                        safe_function_slither_node: FunctionContract
                        if len(safe_function_slither_node.contract.inheritance) < min_inherit_chain_length:
                            min_inherit_chain_length = len(safe_function_slither_node.contract.inheritance)
                            best_safemath_function = safe_function_slither_node
                    assert best_safemath_function is not None
                    if best_safemath_function.contract.contract_kind == 'contract':
                        self.additional_inherit_relation_ship.append(
                            {repair_target_contract_name: best_safemath_function.contract.name})
                        record = {'safe_function_name': best_safemath_function.name, 'safe_contract_type': 'contract'}
                        if repair_target_contract_name not in self.contract_usable_safe_function:
                            self.contract_usable_safe_function[repair_target_contract_name] = {}
                        if operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                            repair_target_contract_name]:
                            self.contract_usable_safe_function[repair_target_contract_name][
                                operator + '@' + operand_data_type] = {}
                        self.contract_usable_safe_function[repair_target_contract_name][
                            operator + '@' + operand_data_type] = record
                        fixed_code = best_safemath_function.name + '(' + left_expression + ', ' + right_expression + ')'
                    elif best_safemath_function.contract.contract_kind == 'library':
                        if {repair_target_contract_name: best_safemath_function.contract.name + '@' + operand_data_type} not in self.additional_using_relation_ship:
                            self.additional_using_relation_ship.append({repair_target_contract_name: best_safemath_function.contract.name + '@' + operand_data_type})
                        record = {'safe_function_name': best_safemath_function.name, 'safe_contract_type': 'library'}
                        if repair_target_contract_name not in self.contract_usable_safe_function:
                            self.contract_usable_safe_function[repair_target_contract_name] = {}
                        if operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                            repair_target_contract_name]:
                            self.contract_usable_safe_function[repair_target_contract_name][
                                operator + '@' + operand_data_type] = {}
                        self.contract_usable_safe_function[repair_target_contract_name][
                            operator + '@' + operand_data_type] = record
                        fixed_code = '(' + left_expression + ').' + best_safemath_function.name + '(' + right_expression + ')'
                else:
                    assert operator + '@' + operand_data_type not in self.additional_library_function_types
                    self.additional_library_function_types.append(operator + '@' + operand_data_type)
                    if {
                        repair_target_contract_name: self.additional_library_name} not in self.additional_inherit_relation_ship:
                        self.additional_inherit_relation_ship.append(
                            {repair_target_contract_name: self.additional_library_name})
                    record = {'safe_function_name': self.name_of_operator[operator] + '_' + operand_data_type,
                              'safe_contract_type': 'contract'}
                    if repair_target_contract_name not in self.contract_usable_safe_function:
                        self.contract_usable_safe_function[repair_target_contract_name] = {}
                    if operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                        repair_target_contract_name]:
                        self.contract_usable_safe_function[repair_target_contract_name][
                            operator + '@' + operand_data_type] = {}
                    self.contract_usable_safe_function[repair_target_contract_name][
                        operator + '@' + operand_data_type] = record
                    fixed_code = self.name_of_operator[
                                     operator] + '_' + operand_data_type + '(' + left_expression + ', ' + right_expression + ')'

            elif ast_node.nodeType == 'UnaryOperation':
                operator = ast_node.operator
                equivalent_operator = ''
                if operator == '++':
                    equivalent_operator = '+'
                if operator == '--':
                    equivalent_operator = '-'
                left_expression = ast_node.subExpression.extract_code(self.contract_source_code, False)
                right_expression = '1'
                for replace_rule in replacement:
                    left_expression = str(left_expression).replace(replace_rule['bug'], replace_rule['fixed'])
                operand_data_type = ast_node.typeDescriptions['typeString']
                matching_safemath_function = True if (
                        self.operator_type_of_operator[
                            equivalent_operator] + '@' + operand_data_type in self.reusable_safemath_functions
                        and len(self.reusable_safemath_functions[self.operator_type_of_operator[
                                                                     equivalent_operator] + '@' + operand_data_type]) != 0) \
                    else False
                safemath_function_currently_available = True if \
                    (repair_target_contract_name in self.contract_usable_safe_function
                     and (equivalent_operator + '@' + operand_data_type) in self.contract_usable_safe_function[
                         repair_target_contract_name]) \
                    else False
                if safemath_function_currently_available:
                    safe_function_name = self.contract_usable_safe_function[repair_target_contract_name][
                        equivalent_operator + '@' + operand_data_type]['safe_function_name']
                    safe_contract_type = self.contract_usable_safe_function[repair_target_contract_name][
                        equivalent_operator + '@' + operand_data_type]['safe_contract_type']
                    if safe_contract_type == 'library':
                        fixed_code = '(' + left_expression + ').' + safe_function_name + '(' + right_expression + ')'
                    if safe_contract_type == 'contract':
                        fixed_code = safe_function_name + '(' + left_expression + ', ' + right_expression + ')'

                elif matching_safemath_function and not safemath_function_currently_available:
                    min_inherit_chain_length = 9999
                    best_safemath_function = None
                    for safe_function_slither_node in self.reusable_safemath_functions[
                        self.operator_type_of_operator[equivalent_operator] + '@' + operand_data_type]:
                        safe_function_slither_node: FunctionContract
                        if len(safe_function_slither_node.contract.inheritance) < min_inherit_chain_length:
                            min_inherit_chain_length = len(safe_function_slither_node.contract.inheritance)
                            best_safemath_function = safe_function_slither_node
                    assert best_safemath_function is not None
                    if best_safemath_function.contract.contract_kind == 'contract':
                        self.additional_inherit_relation_ship.append(
                            {repair_target_contract_name: best_safemath_function.contract.name})
                        record = {'safe_function_name': best_safemath_function.name, 'safe_contract_type': 'contract'}
                        if repair_target_contract_name not in self.contract_usable_safe_function:
                            self.contract_usable_safe_function[repair_target_contract_name] = {}
                        if equivalent_operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                            repair_target_contract_name]:
                            self.contract_usable_safe_function[repair_target_contract_name][
                                equivalent_operator + '@' + operand_data_type] = {}
                        self.contract_usable_safe_function[repair_target_contract_name][
                            equivalent_operator + '@' + operand_data_type] = record
                        fixed_code = best_safemath_function.name + '(' + left_expression + ', ' + right_expression + ')'
                    elif best_safemath_function.contract.contract_kind == 'library':
                        if {repair_target_contract_name: best_safemath_function.contract.name + '@' + operand_data_type} not in self.additional_using_relation_ship:
                            self.additional_using_relation_ship.append({repair_target_contract_name: best_safemath_function.contract.name + '@' + operand_data_type})
                        record = {'safe_function_name': best_safemath_function.name, 'safe_contract_type': 'library'}
                        if repair_target_contract_name not in self.contract_usable_safe_function:
                            self.contract_usable_safe_function[repair_target_contract_name] = {}
                        if equivalent_operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                            repair_target_contract_name]:
                            self.contract_usable_safe_function[repair_target_contract_name][
                                equivalent_operator + '@' + operand_data_type] = {}
                        self.contract_usable_safe_function[repair_target_contract_name][
                            equivalent_operator + '@' + operand_data_type] = record
                        fixed_code = '(' + left_expression + ').' + best_safemath_function.name + '(' + right_expression + ')'

                else:
                    assert equivalent_operator + '@' + operand_data_type not in self.additional_library_function_types
                    self.additional_library_function_types.append(equivalent_operator + '@' + operand_data_type)
                    if {
                        repair_target_contract_name: self.additional_library_name} not in self.additional_inherit_relation_ship:
                        self.additional_inherit_relation_ship.append(
                            {repair_target_contract_name: self.additional_library_name})
                    record = {
                        'safe_function_name': self.name_of_operator[equivalent_operator] + '_' + operand_data_type,
                        'safe_contract_type': 'contract'}
                    if repair_target_contract_name not in self.contract_usable_safe_function:
                        self.contract_usable_safe_function[repair_target_contract_name] = {}
                    if equivalent_operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                        repair_target_contract_name]:
                        self.contract_usable_safe_function[repair_target_contract_name][
                            equivalent_operator + '@' + operand_data_type] = {}
                    self.contract_usable_safe_function[repair_target_contract_name][
                        equivalent_operator + '@' + operand_data_type] = record
                    fixed_code = self.name_of_operator[
                                     equivalent_operator] + '_' + operand_data_type + '(' + left_expression + ', ' + right_expression + ')'

            elif ast_node.nodeType == 'Assignment':
                operator = ast_node.operator
                equivalent_operator = ''
                if operator == '+=':
                    equivalent_operator = '+'
                if operator == '-=':
                    equivalent_operator = '-'
                if operator == '*=':
                    equivalent_operator = '*'
                if operator == '/=':
                    equivalent_operator = '/'
                left_expression = ast_node.leftHandSide.extract_code(self.contract_source_code, False)
                right_expression = ast_node.rightHandSide.extract_code(self.contract_source_code, False)
                for replace_rule in replacement:
                    left_expression = str(left_expression).replace(replace_rule['bug'], replace_rule['fixed'])
                for replace_rule in replacement:
                    right_expression = str(right_expression).replace(replace_rule['bug'], replace_rule['fixed'])
                operand_data_type = ast_node.typeDescriptions['typeString']  # 操作数类型
                matching_safemath_function = True if (
                        self.operator_type_of_operator[
                            equivalent_operator] + '@' + operand_data_type in self.reusable_safemath_functions
                        and len(self.reusable_safemath_functions[self.operator_type_of_operator[
                                                                     equivalent_operator] + '@' + operand_data_type]) != 0) \
                    else False
                safemath_function_currently_available = True if \
                    (repair_target_contract_name in self.contract_usable_safe_function
                     and (equivalent_operator + '@' + operand_data_type) in self.contract_usable_safe_function[
                         repair_target_contract_name]) \
                    else False
                if safemath_function_currently_available:
                    safe_function_name = self.contract_usable_safe_function[repair_target_contract_name][
                        equivalent_operator + '@' + operand_data_type]['safe_function_name']
                    safe_contract_type = self.contract_usable_safe_function[repair_target_contract_name][
                        equivalent_operator + '@' + operand_data_type]['safe_contract_type']
                    if safe_contract_type == 'library':
                        fixed_code = left_expression + ' = ' + '(' + left_expression + ').' + safe_function_name + '(' + right_expression + ')'
                    if safe_contract_type == 'contract':
                        fixed_code = left_expression + ' = ' + safe_function_name + '(' + left_expression + ', ' + right_expression + ')'
                elif matching_safemath_function and not safemath_function_currently_available:
                    min_inherit_chain_length = 9999
                    best_safemath_function = None
                    for safe_function_slither_node in self.reusable_safemath_functions[
                        self.operator_type_of_operator[equivalent_operator] + '@' + operand_data_type]:
                        safe_function_slither_node: FunctionContract
                        if len(safe_function_slither_node.contract.inheritance) < min_inherit_chain_length:
                            min_inherit_chain_length = len(safe_function_slither_node.contract.inheritance)
                            best_safemath_function = safe_function_slither_node
                    assert best_safemath_function is not None
                    if best_safemath_function.contract.contract_kind == 'contract':
                        self.additional_inherit_relation_ship.append(
                            {repair_target_contract_name: best_safemath_function.contract.name})
                        record = {'safe_function_name': best_safemath_function.name, 'safe_contract_type': 'contract'}
                        if repair_target_contract_name not in self.contract_usable_safe_function:
                            self.contract_usable_safe_function[repair_target_contract_name] = {}
                        if equivalent_operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                            repair_target_contract_name]:
                            self.contract_usable_safe_function[repair_target_contract_name][
                                equivalent_operator + '@' + operand_data_type] = {}
                        self.contract_usable_safe_function[repair_target_contract_name][
                            equivalent_operator + '@' + operand_data_type] = record
                        fixed_code = left_expression + ' = ' + best_safemath_function.name + '(' + left_expression + ', ' + right_expression + ')'
                    elif best_safemath_function.contract.contract_kind == 'library':
                        if {repair_target_contract_name: best_safemath_function.contract.name + '@' + operand_data_type} not in self.additional_using_relation_ship:
                            self.additional_using_relation_ship.append({repair_target_contract_name: best_safemath_function.contract.name + '@' + operand_data_type})
                        record = {'safe_function_name': best_safemath_function.name, 'safe_contract_type': 'library'}
                        if repair_target_contract_name not in self.contract_usable_safe_function:
                            self.contract_usable_safe_function[repair_target_contract_name] = {}
                        if equivalent_operator + '@' + operand_data_type not in self.contract_usable_safe_function[
                            repair_target_contract_name]:
                            self.contract_usable_safe_function[repair_target_contract_name][
                                equivalent_operator + '@' + operand_data_type] = {}
                        self.contract_usable_safe_function[repair_target_contract_name][
                            equivalent_operator + '@' + operand_data_type] = record
                        fixed_code = left_expression + ' = ' + '(' + left_expression + ').' + best_safemath_function.name + '(' + right_expression + ')'
                else:
                    self.additional_library_function_types.append(equivalent_operator + '@' + operand_data_type)
                    if {
                        repair_target_contract_name: self.additional_library_name} not in self.additional_inherit_relation_ship:
                        self.additional_inherit_relation_ship.append(
                            {repair_target_contract_name: self.additional_library_name})
                    record = {
                        'safe_function_name': self.name_of_operator[equivalent_operator] + '_' + operand_data_type,
                        'safe_contract_type': 'contract'}
                    if repair_target_contract_name not in self.contract_usable_safe_function:
                        self.contract_usable_safe_function[repair_target_contract_name] = {}
                    if equivalent_operator + '@' + operand_data_type not in self.contract_usable_safe_function[repair_target_contract_name]:
                        self.contract_usable_safe_function[repair_target_contract_name][
                            equivalent_operator + '@' + operand_data_type] = {}
                    self.contract_usable_safe_function[repair_target_contract_name][
                        equivalent_operator + '@' + operand_data_type] = record
                    fixed_code = left_expression + ' = ' + self.name_of_operator[
                        equivalent_operator] + '_' + operand_data_type + '(' + left_expression + ', ' + right_expression + ')'
            if fixed_code != '':
                replacement.append({'bug': bug_code, 'fixed': fixed_code})
        self.replacements[line_number] = replacement

    def get_additional_library_code(self):
        if len(self.additional_library_function_types) == 0:
            return ''
        if self.additional_library_code != 'contract ' + self.additional_library_name + ' {':
            return self.additional_library_code
        for template_type in self.additional_library_function_types:
            operator = str(template_type).split('@')[0]
            operand_type = str(template_type).split('@')[1]
            if operator == '+':
                if 'uint' in operand_type:
                    self.additional_library_code += self.template.get_safe_add_uint_function_code(operand_type)
                elif 'int' in operand_type:
                    self.additional_library_code += self.template.get_safe_add_int_function_code(operand_type)
            elif operator == '-':
                if 'uint' in operand_type:
                    self.additional_library_code += self.template.get_safe_sub_uint_function_code(operand_type)
                elif 'int' in operand_type:
                    self.additional_library_code += self.template.get_safe_sub_int_function_code(operand_type)
            elif operator == '*':
                self.additional_library_code += self.template.get_safe_mul_function_code(operand_type)
            elif operator == '/':
                self.additional_library_code += self.template.get_safe_div_function_code(operand_type)
        self.additional_library_code += '\n}\n'
        return self.additional_library_code

    def get_modified_source_code(self):
        source_code = self.contract_source_code[:]

        def replace_string_in_line(original_string, line_number, old_substring, new_substring):
            lines = original_string.split('\n')
            if 0 < line_number <= len(lines):
                lines[line_number - 1] = lines[line_number - 1].replace(old_substring, new_substring)
                return '\n'.join(lines)
            else:
                return original_string

        for line in self.repair_targets:
            for replace_operation in self.replacements[line]:
                bug_code = replace_operation['bug']
                fixed_code = replace_operation['fixed']
                source_code = replace_string_in_line(source_code, line, bug_code, fixed_code)

        def replace_brace_in_multiline_string(string, start, end, replace_string):
            lines = string.split('\n')
            if start <= 0 or end > len(lines):
                return "Invalid start or end line number"
            for i in range(start - 1, end):
                line_ = lines[i]
                brace_index = line_.find('{')
                if brace_index != -1:
                    lines[i] = line_[:brace_index] + replace_string + line_[brace_index + 1:]
                    break
            return '\n'.join(lines)

        self.contract_source_node: Union[IterableNodeBase, NodeBase]
        for inherit_relation_ship in self.additional_inherit_relation_ship:
            inherit_relation_ship: {}
            for contract_node in self.contract_source_node:
                if contract_node.nodeType == 'ContractDefinition' and contract_node.name in inherit_relation_ship:
                    line_numbers = contract_node.get_line_numbers(self.contract_source_code)
                    father_name = inherit_relation_ship[contract_node.name]
                    base_contracts = contract_node.baseContracts
                    need_replace = True
                    dest = ''
                    if len(base_contracts) != 0:
                        dest = ', ' + father_name + ' {'
                        for base_contract in base_contracts:
                            if str(base_contract.baseName.name) == father_name:
                                need_replace = False
                                break
                    else:
                        dest = 'is ' + father_name + ' {'
                    if need_replace:
                        source_code = replace_brace_in_multiline_string(source_code, line_numbers[0], line_numbers[1], dest)
                    break
        places_to_add_using_statement = []
        for using_relationship in self.additional_using_relation_ship:
            using_relationship: {}
            for son_name, father_name_and_type in using_relationship.items():
                for contract_node in self.contract_source_node:
                    if contract_node.nodeType == 'ContractDefinition' and contract_node.name == son_name:
                        line_numbers = contract_node.get_line_numbers(self.contract_source_code)
                        places_to_add_using_statement.append((line_numbers, father_name_and_type))
                        break

        places_to_add_using_statement = sorted(places_to_add_using_statement, key=lambda x: x[0][0], reverse=True)
        for place_to_add_tuple in places_to_add_using_statement:
            begin_line = place_to_add_tuple[0][0]
            end_line = place_to_add_tuple[0][1]
            father_name_and_type = place_to_add_tuple[1]
            father_name = str(father_name_and_type).split('@')[0]
            for_type = str(father_name_and_type).split('@')[1]
            statement = "{\n\tusing " + father_name + ' for ' + for_type + ';'
            source_code = replace_brace_in_multiline_string(source_code, begin_line, end_line, statement)
        return source_code
