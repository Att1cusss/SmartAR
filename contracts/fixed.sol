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