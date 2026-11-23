# Network and Python Debugging Practice

These scripts are manual learning utilities for practising Python debugging and TCP connectivity troubleshooting. They are separate from the production monitoring components.

## 1. Python PDB Debugging

Run:

```powershell
python scripts/practice/pdb_practice.py
```

The script pauses at `pdb.set_trace()` to allow interactive debugging.

Useful PDB commands:

- `n` - Execute the next line.
- `s` - Step into a function.
- `p variable_name` - Print a variable.
- `c` - Continue execution.
- `q` - Quit debugging.

## 2. TCP Connection Debugging

Run:

```powershell
python scripts/practice/tcp_debug_practice.py
```

This script attempts a TCP connection to `127.0.0.1` on port `1`.

The connection may fail with a timeout or connection-refused error, depending on the local system and network behavior. In the observed run, the collector returned a CRITICAL result with a connection timeout.

This exercise demonstrates basic TCP connection troubleshooting and error handling. It is a local learning exercise, not a production monitoring check.

## 3. Technologies

- Python
- Python PDB debugger
- TCP/IP
- Socket programming
- PowerShell

## 4. Learning Outcomes

- Practised stepping through Python code using PDB.
- Inspected variable values during execution.
- Practised identifying TCP connection failures.
- Understood the difference between a local debugging exercise and production monitoring.
