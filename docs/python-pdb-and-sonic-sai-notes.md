# Python PDB Debugging and SONiC/SAI Architecture Notes

## 1. Python PDB debugging

Practised Python's built-in debugger (`pdb`) using the existing
`TCPCollector` in `src/infra_monitor/checks/network.py`.

Activities:
- Set a breakpoint in the mocked TCP connection callback.
- Used `where`, `up`, and `down` to navigate the call stack.
- Used `list` to inspect the source around the current line.
- Inspected the collector's host, port, timeout, threshold, and timestamp.
- Used `next` and `continue` to control execution.

Observed values:
- Host: `localhost`
- Port: `443`
- Timeout: `2.0` seconds
- Warning threshold: `250 ms`
- Critical threshold: `1000 ms`

Debugging lesson:
Pausing between performance-counter readings includes debugger time in the
measured interval. A breakpoint during timing-sensitive code can therefore
distort response-time measurements. Use controlled clocks in automated tests
when validating timing thresholds.

## 2. SONiC architecture study

SONiC (Software for Open Networking in the Cloud) is a Linux-based network
operating system used on supported network switches.

Key components and concepts:

- **CONFIG_DB:** Stores configuration intended for network services.
- **APPL_DB:** Carries application-level state and intent between components.
- **STATE_DB:** Stores operational state reported by services.
- **COUNTERS_DB:** Stores interface and hardware counter information.
- **orchagent:** Coordinates application-level configuration with lower-level
  forwarding components.
- **syncd:** Coordinates communication between SONiC and the switch ASIC.
- **SAI:** Switch Abstraction Interface, a standardized API between network
  operating-system components and vendor-specific switch ASIC implementations.

Conceptual flow:

Configuration -> SONiC application components -> orchagent -> SAI ->
vendor ASIC implementation -> switch hardware

This is an architecture study only. A SONiC image, switch ASIC, and running
SONiC services were not available in this WSL environment.

## 3. How this project could monitor a SONiC switch

The existing Python monitoring project could monitor a supported SONiC
deployment through approved management interfaces or operational commands.

Potential monitoring areas:
- Interface administrative and operational state.
- Interface traffic counters and packet drops.
- Link errors and interface status changes.
- Routing-service health, including BGP and OSPF.
- Service availability and monitoring alerts.

Python integration would depend on the deployment's supported management
interfaces, permissions, and data access methods. This project does not
currently implement direct SAI access or a live SONiC integration.

## 4. SAI learning scope

SAI provides a hardware-independent interface for switch capabilities such
as ports, queues, routing, and forwarding objects.

For this Python-focused project, SAI is studied at the architecture and
monitoring-integration level. No C/C++ SAI implementation or ASIC driver
development was performed.

## 5. Environment limitations

- SONiC was not installed or run in this WSL environment.
- No physical switch or switch ASIC was available.
- MPLS kernel support was unavailable in the WSL kernel during the earlier
  lab attempt.
- BGP and OSPF were separately practised in the documented FRR routing lab.

## 6. Verification

The TCP-specific tests were run with:

    PYTHONPATH=src python3 -m pytest -q tests/test_optional_collectors.py -k tcp

Result: 14 tests passed.
