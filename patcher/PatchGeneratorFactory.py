from typing import List, Optional, Union
from patcher.PatchGenerator import PatchGenerator
from patcher.safe_math_finder import SafeMathFinderSMT
from utils.entity.RepairTarget import RepairTarget


class PatchGeneratorFactory:
    def __init__(self, safemath_finder: Union[SafeMathFinderSMT], repair_targets: List[RepairTarget], reuse=True, method='SMT'):
        self.reusable_safemath_functions = {}
        assert method in ['SMT']
        self.method = method
        self.safemath_finder = safemath_finder
        self.repair_targets = repair_targets
        self.slither = safemath_finder.slither
        self.reusable_safemath_functions = {}
        self.targets = {}
        self.reuse = reuse

    def find_reusable_safemath(self):
        if not self.reuse:
            return
        if self.method == 'SMT':
            self.safemath_finder: SafeMathFinderSMT
            candidates = self.safemath_finder.structural_judgement()
            for function in candidates:
                res, function_type = self.safemath_finder.functional_judgement(function)
                if res is True:
                    if function_type not in self.reusable_safemath_functions:
                        self.reusable_safemath_functions[function_type] = [function]
                    else:
                        self.reusable_safemath_functions[function_type].append(function)

    def repair_target_convert(self):
        for repair_target in self.repair_targets:
            line_number = int(repair_target.ast_node.extract_code(repair_target.source_code, True).split(": ")[0])
            if line_number not in self.targets:
                self.targets[line_number] = {'ast_nodes': [], 'cfg_node': None, 'function': None}
            self.targets[line_number]['ast_nodes'].append(repair_target.ast_node)
            self.targets[line_number]['cfg_node'] = repair_target.slither_statement_node
            self.targets[line_number]['function'] = repair_target.slither_function_node
        for line_number in self.targets:
            self.targets[line_number]['ast_nodes'] = sorted(self.targets[line_number]['ast_nodes'], key=lambda obj: len(obj.extract_code(repair_target.source_code, False)))

    def create_patch_generator(self) -> Optional[PatchGenerator]:
        if len(self.repair_targets) == 0:
            return None
        self.find_reusable_safemath()
        self.repair_target_convert()
        return PatchGenerator(
            contract_source_code=self.repair_targets[0].source_code,
            contract_compile_version='',
            repair_targets=self.targets,
            reusable_safemath_functions=self.reusable_safemath_functions,
            slither=self.slither,
            source_node=self.repair_targets[0].ast_root
        )
