# Rating Engine PoC – Project Summary

## Objective
Build a modern, deterministic rating engine for P&C insurance (starting with motor),
with tariff logic defined declaratively and usable both in production and actuarial Python workflows.

## Core Principles
- Tariff logic defined as data (YAML + tables)
- Deterministic execution (Decimal arithmetic)
- Full explainability (price breakdown)
- Python-first actuarial workflow
- Versioned, auditable tariffs

## Scope (PoC)
- One product: Motor
- One version
- Multiplicative technical premium + additive fees
- Batch pricing in Python
- No UI, no policy lifecycle

## Tariff Representation
- YAML-defined DAG
- Supported operators: CONSTANT, LOOKUP, ADD, MULTIPLY, IF
- Lookup tables as CSV

## Architecture
- Tariff loader + validator
- DAG-based evaluation engine
- Pandas-based sandbox
- Optional Torch backend for optimization

## Success Criteria
- Python and engine produce identical results
- Actuaries can simulate and optimize tariffs
- Tariff deployable by copying files
