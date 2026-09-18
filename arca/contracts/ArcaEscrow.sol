// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ArcaEscrow — open-bounty USDC escrow for the agent economy on Arc
/// @notice A client posts and funds an OPEN bounty (no provider named up front).
///         Any agent can claim it, submit a deliverable, and the job's evaluator
///         releases the USDC on verified delivery. For code bounties the evaluator
///         is an automated service that runs the test suite and releases on green.
///         Solves the "how does the client know the provider up front" problem in
///         the ERC-8183 reference flow: discovery + claim instead of pre-naming.
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract ArcaEscrow {
    enum Status { Open, Claimed, Submitted, Released, Refunded }

    struct Job {
        address client;
        address provider;        // address(0) until an agent claims
        address evaluator;       // releases funds on verified delivery
        uint256 amount;          // USDC (6 decimals), locked at post time
        uint64  deadline;        // unix; after this an unfinished job is refundable
        Status  status;
        bytes32 acceptanceHash;  // hash of the machine-checkable acceptance criteria
        bytes32 deliverableHash; // hash of the submitted work (e.g. commit SHA)
    }

    IERC20 public immutable usdc;
    uint256 public jobCount;
    mapping(uint256 => Job) public jobs;

    event JobPosted(uint256 indexed id, address indexed client, address evaluator, uint256 amount, uint64 deadline, bytes32 acceptanceHash, string description);
    event JobClaimed(uint256 indexed id, address indexed provider);
    event Delivered(uint256 indexed id, bytes32 deliverableHash);
    event Released(uint256 indexed id, address indexed provider, uint256 amount);
    event Refunded(uint256 indexed id, uint256 amount);

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }

    /// @notice Client posts an OPEN bounty and funds the escrow up front.
    /// @dev Requires the client to have approved this contract for `amount` USDC.
    function postJob(address evaluator, uint256 amount, uint64 deadline, bytes32 acceptanceHash, string calldata description)
        external
        returns (uint256 id)
    {
        require(amount > 0, "amount=0");
        require(evaluator != address(0), "evaluator=0");
        id = ++jobCount;
        jobs[id] = Job({
            client: msg.sender,
            provider: address(0),
            evaluator: evaluator,
            amount: amount,
            deadline: deadline,
            status: Status.Open,
            acceptanceHash: acceptanceHash,
            deliverableHash: bytes32(0)
        });
        require(usdc.transferFrom(msg.sender, address(this), amount), "fund failed");
        emit JobPosted(id, msg.sender, evaluator, amount, deadline, acceptanceHash, description);
    }

    /// @notice Any agent (except the client) claims an open bounty.
    function claimJob(uint256 id) external {
        Job storage j = jobs[id];
        require(j.status == Status.Open, "not open");
        require(msg.sender != j.client, "client cannot claim");
        j.provider = msg.sender;
        j.status = Status.Claimed;
        emit JobClaimed(id, msg.sender);
    }

    /// @notice Provider submits the deliverable hash.
    function submit(uint256 id, bytes32 deliverableHash) external {
        Job storage j = jobs[id];
        require(j.status == Status.Claimed, "not claimed");
        require(msg.sender == j.provider, "not provider");
        j.deliverableHash = deliverableHash;
        j.status = Status.Submitted;
        emit Delivered(id, deliverableHash);
    }

    /// @notice Evaluator releases the escrow to the provider (tests passed).
    function release(uint256 id) external {
        Job storage j = jobs[id];
        require(j.status == Status.Submitted, "not submitted");
        require(msg.sender == j.evaluator, "not evaluator");
        j.status = Status.Released;                       // effects before interaction
        require(usdc.transfer(j.provider, j.amount), "payout failed");
        emit Released(id, j.provider, j.amount);
    }

    /// @notice Client reclaims funds if the deadline passes without delivery.
    function refund(uint256 id) external {
        Job storage j = jobs[id];
        require(msg.sender == j.client, "not client");
        require(j.status == Status.Open || j.status == Status.Claimed, "not refundable");
        require(block.timestamp > j.deadline, "before deadline");
        j.status = Status.Refunded;
        require(usdc.transfer(j.client, j.amount), "refund failed");
        emit Refunded(id, j.amount);
    }

    function getJob(uint256 id) external view returns (Job memory) {
        return jobs[id];
    }
}
