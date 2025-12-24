#!/bin/bash
#
# Comprehensive validation script for hybrid autofill system
#
# Tests:
# 1. All unit tests
# 2. Integration tests
# 3. CLI with all algorithms
# 4. Performance comparison
# 5. Acceptance test (≥90% completion)
#

set -e  # Exit on error

echo "======================================================================"
echo "HYBRID AUTOFILL SYSTEM VALIDATION"
echo "======================================================================"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

echo "======================================================================"
echo "PHASE 1: Unit Tests"
echo "======================================================================"
echo ""

# Test BeamSearchAutofill
echo "Testing BeamSearchAutofill..."
if python -m pytest cli/tests/unit/test_beam_search.py -v --tb=no > /tmp/beam_test.log 2>&1; then
    print_status 0 "BeamSearchAutofill (26 tests)"
else
    print_status 1 "BeamSearchAutofill"
    tail -20 /tmp/beam_test.log
fi
echo ""

# Test IterativeRepair
echo "Testing IterativeRepair..."
if python -m pytest cli/tests/unit/test_iterative_repair.py -v --tb=no > /tmp/repair_test.log 2>&1; then
    print_status 0 "IterativeRepair (22 tests)"
else
    print_status 1 "IterativeRepair"
    tail -20 /tmp/repair_test.log
fi
echo ""

# Test HybridAutofill
echo "Testing HybridAutofill integration..."
if python -m pytest cli/tests/unit/test_hybrid_integration.py -v --tb=no > /tmp/hybrid_test.log 2>&1; then
    print_status 0 "HybridAutofill (11 tests)"
else
    print_status 1 "HybridAutofill"
    tail -20 /tmp/hybrid_test.log
fi
echo ""

echo "======================================================================"
echo "PHASE 2: Coverage Report"
echo "======================================================================"
echo ""

echo "Generating coverage report..."
if python -m pytest cli/tests/unit/test_beam_search.py cli/tests/unit/test_iterative_repair.py cli/tests/unit/test_hybrid_integration.py \
    --cov=cli/src/fill/beam_search_autofill \
    --cov=cli/src/fill/iterative_repair \
    --cov=cli/src/fill/hybrid_autofill \
    --cov-report=term-missing \
    --tb=no > /tmp/coverage.log 2>&1; then
    print_status 0 "Coverage report generated"
    grep "^TOTAL" /tmp/coverage.log
else
    print_status 1 "Coverage report"
fi
echo ""

echo "======================================================================"
echo "PHASE 3: CLI Integration Tests"
echo "======================================================================"
echo ""

# Test each algorithm
for algo in trie beam repair hybrid; do
    echo "Testing CLI with algorithm: $algo"
    if timeout 120 python3 -m cli.src.cli fill simple_fillable_11x11.json \
        --algorithm $algo \
        --wordlists data/wordlists/top_50k.txt \
        --timeout 90 \
        --min-score 0 \
        --output "test_result_${algo}.json" > /tmp/cli_${algo}.log 2>&1; then
        print_status 0 "CLI with $algo algorithm"
    else
        print_status 1 "CLI with $algo algorithm"
        tail -10 /tmp/cli_${algo}.log
    fi
done
echo ""

echo "======================================================================"
echo "PHASE 4: Performance Comparison"
echo "======================================================================"
echo ""

echo "Algorithm Performance Summary:"
echo "----------------------------------------------------------------------"
printf "%-15s %-15s %-10s %-10s\n" "Algorithm" "Slots Filled" "Success" "Time (s)"
echo "----------------------------------------------------------------------"

for algo in trie beam repair hybrid; do
    if [ -f "test_result_${algo}.json" ]; then
        python3 <<EOF
import json
try:
    with open('test_result_${algo}.json') as f:
        data = json.load(f)
        filled = data.get('slots_filled', 0)
        total = data.get('total_slots', 0)
        success = data.get('success', False)
        time_elapsed = data.get('time_elapsed', 0)
        print(f"{'$algo':<15s} {filled}/{total:<11s} {'✓' if success else '✗':<10s} {time_elapsed:.2f}")
except Exception as e:
    print(f"{'$algo':<15s} ERROR: {str(e)}")
EOF
    fi
done

echo "----------------------------------------------------------------------"
echo ""

echo "======================================================================"
echo "PHASE 5: Acceptance Test (≥90% completion requirement)"
echo "======================================================================"
echo ""

echo "Testing hybrid algorithm on standard_11x11.json..."
if timeout 150 python3 -m cli.src.cli fill standard_11x11.json \
    --algorithm hybrid \
    --wordlists data/wordlists/top_50k.txt \
    --timeout 120 \
    --min-score 0 \
    --output acceptance_test_result.json > /tmp/acceptance.log 2>&1; then

    # Check completion rate
    python3 <<'EOF'
import json
import sys

try:
    with open('acceptance_test_result.json') as f:
        result = json.load(f)
        completion = result['slots_filled'] / result['total_slots']

        print(f"Completion: {result['slots_filled']}/{result['total_slots']} ({completion:.1%})")
        print(f"Time: {result['time_elapsed']:.2f}s")
        print(f"Success: {result['success']}")

        if completion >= 0.90:
            print(f"\n✓ ACCEPTANCE TEST PASSED (≥90% completion)")
            sys.exit(0)
        else:
            print(f"\n✗ ACCEPTANCE TEST FAILED (<90% completion)")
            sys.exit(1)
except Exception as e:
    print(f"Error reading result: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_status 0 "Acceptance test (≥90% completion)"
    else
        print_status 1 "Acceptance test (≥90% completion)"
    fi
else
    print_status 1 "Acceptance test (command failed)"
    tail -20 /tmp/acceptance.log
fi
echo ""

echo "======================================================================"
echo "FINAL SUMMARY"
echo "======================================================================"
echo ""
echo "Total Tests Run: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
else
    echo "Failed: 0"
fi
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ ALL VALIDATION TESTS PASSED${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ VALIDATION FAILED - $FAILED_TESTS test(s) failed${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    exit 1
fi
