import argparse
import json
import os
from typing import List, Set, Dict
from PathConfig import CONTRACTS_DIR
from patcher.PatchGeneratorFactory import PatchGeneratorFactory
from patcher.safe_math_finder import SafeMathFinderSMT
from recognizer.fp.FalsePositiveRecognizer import FalsePositiveRecognizer
from utils.compile import change_solc_version_to, read_source_code, build_slither, build_ast, compile_contract
from utils.entity.RepairTarget import RepairTarget
from utils.locate import locate_repair_targets


class SmartAR:
    def __init__(self, reuse=True, method='SMT'):
        self.reuse = reuse
        bug_lines_json_path = os.path.join(CONTRACTS_DIR, 'bug_lines.json')
        with open(bug_lines_json_path, 'r', encoding='utf-8') as file:
            bug_lines: List[int] = json.load(file)
        if not bug_lines:
            raise ValueError("bug_lines cannot be empty")
        self.source_code = read_source_code()
        self.source_root = build_ast(compile_output_json=compile_contract())
        self.slither = build_slither()
        self.repair_targets = []
        for bug_line in bug_lines:
            self.repair_targets.extend(
                locate_repair_targets(
                    source_node=self.source_root,
                    source_code=self.source_code,
                    slither=self.slither,
                    line_number=bug_line)
            )
        self.repair_targets: List[RepairTarget]
        self.fp_recognizer = FalsePositiveRecognizer(repair_targets=self.repair_targets)
        self.true_positive_targets, self.false_positive_targets = self.fp_recognizer.recognize_true_positive()
        self.true_positive_targets: Set[RepairTarget]
        self.false_positive_targets: Dict[RepairTarget, str]
        self.final_repair_targets = self.true_positive_targets
        print()
        print(f'[+] False Positives:')
        for target in self.false_positive_targets:
            target.print_info()
        print()
        print(f'[+] True Positives:')
        for target in self.final_repair_targets:
            target.print_info()
        if method == 'SMT':
            self.patch_generator = PatchGeneratorFactory(
                safemath_finder=SafeMathFinderSMT(slither=self.slither),
                repair_targets=list(self.final_repair_targets),
                reuse=self.reuse,
                method='SMT'
            ).create_patch_generator()
        else:
            pass
        self.lines_need_to_patch = set()
        for target in self.final_repair_targets:
            self.lines_need_to_patch.add(target.get_line_number())

    def patch(self):
        if self.patch_generator is None:
            print(f'it seems not bugs')
            return
        for line in self.lines_need_to_patch:
            self.patch_generator.patch_line(line)
        fixed_contract_path = os.path.join(CONTRACTS_DIR, 'fixed.sol')
        with open(fixed_contract_path, 'w', encoding='utf-8') as f:
            f.write(self.patch_generator.get_additional_library_code())
        f.close()
        with open(fixed_contract_path, 'a', encoding='utf-8') as f:
            f.write(self.patch_generator.get_modified_source_code())
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SmartAR Tool")
    parser.add_argument('--version', type=str, required=True, help='Solidity compiler version')
    args = parser.parse_args()
    change_solc_version_to(args.version)
    ar = SmartAR()
    ar.patch()
