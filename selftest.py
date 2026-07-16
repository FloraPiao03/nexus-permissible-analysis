#!/usr/bin/env python3
"""Offline acceptance tests with hand-computed synthetic expectations."""
import unittest


def main():
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("\nSelf-test passed: manually specified classification, metadata, duplicate, and percentage checks.")


if __name__ == "__main__":
    main()
