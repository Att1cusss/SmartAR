# SmartAR

SmartAR is an automated repair tool for integer overflow vulnerabilities in smart contracts. The name stands for "Smart Contract Arithmetic Bugs Repair."

## Installation of Dependencies

Python Version: 3.9.18

```shell
pip install -r requirements.txt
```

## Usage

usage: SmartAR.py [-h] --version VERSION

for example:

```shell
python SmartAR.py --version 0.4.26
```

The target contract to be repaired is `sample.sol` located in the `contracts` folder. The vulnerability report is recorded in an array format in `bug_lines.json`, also located in the `contracts` folder. The output of the repair will be saved as `fixed.sol` in the same `contracts` folder.


## Example

sample.sol

```
pragma solidity^0.4.26;

contract sGuard{
  function add_uint256(uint256 a, uint256 b) internal pure returns (uint256) {
    uint256 c = a + b;
    assert(c >= a);
    return c;
  }
}
contract Fund is sGuard {
  mapping(address => uint) balances;
  uint counter = 0;
  uint dontFixMe = 0;

   function main(uint x) public {
    if (counter < 100) {
      msg.sender.send(x + 1);
      counter = counter + 1;
      dontFixMe ++;
    }
  }
}
```

bug_lines.json

```json
[17, 18, 19]
```

fixed.sol
```
pragma solidity^0.4.26;

contract sGuard{
  function add_uint256(uint256 a, uint256 b) internal pure returns (uint256) {
    uint256 c = a + b;
    assert(c >= a);
    return c;
  }
}
contract Fund is sGuard {
  mapping(address => uint) balances;
  uint counter = 0;
  uint dontFixMe = 0;

   function main(uint x) public {
    if (counter < 100) {
      msg.sender.send(add_uint256(x, 1));
      counter = counter + 1;
      add_uint256(dontFixMe, 1);
    }
  }
}
```

output of tool:

```
Switched global version to 0.4.26
[#] [Targets Located] Elapsed time: 0.001 seconds, 1 targets located in line:17
[#] [Targets Located] Elapsed time: 0.000 seconds, 1 targets located in line:18
[#] [Targets Located] Elapsed time: 0.001 seconds, 1 targets located in line:19

[+] False Positives:
[RepairTarget] Fund:main:18
CODE: counter = counter + 1
OPERATION: counter [+] 1
SSA: counter_1 [+] 1 --> TMP_9

[+] True Positives:
[RepairTarget] Fund:main:19
CODE: dontFixMe ++
OPERATION: [++] dontFixMe
SSA: dontFixMe_1 [+] 1 --> dontFixMe_2
[RepairTarget] Fund:main:17
CODE: msg.sender.send(x + 1)
OPERATION: x [+] 1
SSA: x_1 [+] 1 --> TMP_7
```

---
## Note

#### 1. This tool is a prototype of our method, and the current implementation is not stable. If you encounter any issues, please submit an issue, and we will address it in future updates.
#### 2. Our tool is for reference only. We are not responsible for any financial losses caused by the use of this tool.