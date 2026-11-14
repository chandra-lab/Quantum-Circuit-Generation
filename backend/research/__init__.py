"""Offline PyTorch experimentation harness for circuit specs.

This package is not imported by the web app. It trains a circuit-category
classifier on synthetic, rule-labelled specs; it does not generate circuits.
Only ``research.model``, ``research.train`` and ``research.evaluate`` import torch.
"""
