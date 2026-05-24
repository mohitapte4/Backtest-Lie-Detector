"""Generate figures for v3 benchmark results."""

import sys
sys.path.insert(0, 'src')

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from backtest_lie_detector.benchmark.build_cases import generate_v3_cases

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11


def load_results():
    """Load and enrich results."""
    results = []
    with open('outputs/results/model_outputs_v3.jsonl') as f:
        for line in f:
            results.append(json.loads(line))
    
    cases = generate_v3_cases()
    case_map = {c.id: c for c in cases}
    
    for r in results:
        case = case_map.get(r['case_id'])
        if case:
            r['module'] = case.module.value
            r['difficulty'] = case.difficulty.value
            r['expected_validity'] = case.expected_validity.value
        if r.get('parsed_response'):
            r['confidence'] = r['parsed_response'].get('confidence', 0.5)
        
        if r['case_id'].startswith('hard_'):
            r['case_type'] = 'Hard (v3)'
        elif r['case_id'].startswith(('trap_', 'subtle_', 'multi_')):
            r['case_type'] = 'Adversarial (v2)'
        elif r['case_id'].startswith('wrds_'):
            r['case_type'] = 'WRDS-backed (v2)'
        else:
            r['case_type'] = 'Original (v1)'
    
    return results


def plot_version_comparison():
    """Plot accuracy across benchmark versions."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    versions = ['v1\n(42 cases)', 'v2\n(69 cases)', 'v3\n(105 cases)']
    accuracies = [97.6, 95.7, 84.8]
    colors = ['#3498db', '#9b59b6', '#e74c3c']
    
    bars = ax.bar(versions, accuracies, color=colors, edgecolor='black', linewidth=1.5)
    
    ax.set_ylabel('Accuracy (%)', fontweight='bold', fontsize=12)
    ax.set_title('Benchmark Evolution: Increasing Difficulty', fontweight='bold', fontsize=14)
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    ax.axhline(y=85, color='red', linestyle='--', alpha=0.3, label='Target difficulty')
    
    for bar, acc in zip(bars, accuracies):
        ax.annotate(f'{acc:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1),
                    ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    # Add annotations
    ax.annotate('Original\nbenchmark', xy=(0, 60), ha='center', fontsize=10)
    ax.annotate('+17 adversarial\n+10 WRDS', xy=(1, 60), ha='center', fontsize=10)
    ax.annotate('+36 hard\nsource-backed', xy=(2, 60), ha='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v3_version_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v3_version_comparison.png")


def plot_case_type_breakdown(results):
    """Plot accuracy by case type."""
    by_type = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        by_type[r['case_type']]['total'] += 1
        if r['validity_correct']:
            by_type[r['case_type']]['correct'] += 1
    
    order = ['Original (v1)', 'Adversarial (v2)', 'WRDS-backed (v2)', 'Hard (v3)']
    types = [t for t in order if t in by_type]
    accuracies = [by_type[t]['correct'] / by_type[t]['total'] * 100 for t in types]
    totals = [by_type[t]['total'] for t in types]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#3498db', '#9b59b6', '#2ecc71', '#e74c3c']
    bars = ax.bar(types, accuracies, color=colors, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Case Type', fontweight='bold', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontweight='bold', fontsize=12)
    ax.set_title('GPT-4o Accuracy by Case Type (v3 Benchmark)', fontweight='bold', fontsize=14)
    ax.set_ylim(0, 110)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    
    for bar, acc, total in zip(bars, accuracies, totals):
        ax.annotate(f'{acc:.1f}%\n(n={total})',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1),
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v3_case_type_breakdown.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v3_case_type_breakdown.png")


def plot_hard_family_breakdown(results):
    """Plot accuracy by hard case family."""
    hard_results = [r for r in results if r['case_type'] == 'Hard (v3)']
    families = defaultdict(lambda: {"correct": 0, "total": 0})
    
    for r in hard_results:
        case_id = r['case_id']
        if 'ticker_s' in case_id or 'ticker_c' in case_id:
            family = "Ticker Reassignment"
        elif 'manville' in case_id or 'gm_old' in case_id:
            family = "Security Reorg"
        elif 'meta' in case_id:
            family = "FB-META Timing"
        elif 'goog' in case_id:
            family = "GOOG/GOOGL"
        elif 'ibm' in case_id or 'kyndryl' in case_id:
            family = "IBM/Kyndryl"
        elif 'filing' in case_id or 'acceptance' in case_id:
            family = "Filing Clock"
        elif 'sp500' in case_id:
            family = "S&P Timing"
        elif 'erroneous' in case_id:
            family = "Erroneous Ann."
        elif 'compustat' in case_id:
            family = "Compustat PIT"
        elif 'xbrl' in case_id or 'factset' in case_id:
            family = "Standardization"
        elif 'adjusted' in case_id:
            family = "Adj. Price"
        elif 'delisting' in case_id:
            family = "Delisting"
        elif 'earnings' in case_id:
            family = "Earnings"
        else:
            family = "Other"
        
        families[family]['total'] += 1
        if r['validity_correct']:
            families[family]['correct'] += 1
    
    # Sort by accuracy
    sorted_families = sorted(families.items(), key=lambda x: x[1]['correct']/x[1]['total'] if x[1]['total'] > 0 else 0)
    
    names = [f[0] for f in sorted_families]
    accuracies = [f[1]['correct'] / f[1]['total'] * 100 if f[1]['total'] > 0 else 0 for f in sorted_families]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = plt.cm.RdYlGn([a/100 for a in accuracies])
    bars = ax.barh(names, accuracies, color=colors, edgecolor='black', linewidth=0.5)
    
    ax.set_xlabel('Accuracy (%)', fontweight='bold', fontsize=12)
    ax.set_title('Hard Case Family Performance (36 cases)', fontweight='bold', fontsize=14)
    ax.set_xlim(0, 110)
    ax.axvline(x=50, color='red', linestyle='--', alpha=0.5, label='Random baseline')
    
    for bar, acc in zip(bars, accuracies):
        ax.annotate(f'{acc:.0f}%',
                    xy=(bar.get_width() + 2, bar.get_y() + bar.get_height()/2),
                    va='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v3_hard_family_breakdown.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v3_hard_family_breakdown.png")


def plot_failure_types(results):
    """Plot failure type distribution."""
    failures = [r for r in results if not r['validity_correct']]
    
    false_invalids = sum(1 for r in failures if r.get('expected_validity') == 'valid')
    false_valids = sum(1 for r in failures if r.get('expected_validity') == 'invalid')
    ambiguous_errors = sum(1 for r in failures if r.get('expected_validity') == 'ambiguous')
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Pie chart
    sizes = [false_invalids, false_valids, ambiguous_errors]
    labels = [f'False Invalids\n(n={false_invalids})', f'False Valids\n(n={false_valids})', f'Ambiguous Errors\n(n={ambiguous_errors})']
    colors = ['#e74c3c', '#27ae60', '#f1c40f']
    explode = (0.05, 0, 0)
    
    ax1.pie(sizes, labels=labels, colors=colors, explode=explode, autopct='%1.0f%%', startangle=90)
    ax1.set_title('Failure Type Distribution (16 failures)', fontweight='bold', fontsize=12)
    
    # Stacked bar by case type
    case_types = ['Original', 'Adversarial', 'WRDS', 'Hard']
    false_inv_by_type = [
        sum(1 for r in failures if r['case_type'] == 'Original (v1)' and r.get('expected_validity') == 'valid'),
        sum(1 for r in failures if r['case_type'] == 'Adversarial (v2)' and r.get('expected_validity') == 'valid'),
        sum(1 for r in failures if r['case_type'] == 'WRDS-backed (v2)' and r.get('expected_validity') == 'valid'),
        sum(1 for r in failures if r['case_type'] == 'Hard (v3)' and r.get('expected_validity') == 'valid'),
    ]
    ambig_by_type = [
        sum(1 for r in failures if r['case_type'] == 'Original (v1)' and r.get('expected_validity') == 'ambiguous'),
        sum(1 for r in failures if r['case_type'] == 'Adversarial (v2)' and r.get('expected_validity') == 'ambiguous'),
        sum(1 for r in failures if r['case_type'] == 'WRDS-backed (v2)' and r.get('expected_validity') == 'ambiguous'),
        sum(1 for r in failures if r['case_type'] == 'Hard (v3)' and r.get('expected_validity') == 'ambiguous'),
    ]
    
    x = np.arange(len(case_types))
    ax2.bar(x, false_inv_by_type, label='False Invalid', color='#e74c3c')
    ax2.bar(x, ambig_by_type, bottom=false_inv_by_type, label='Ambiguous Error', color='#f1c40f')
    
    ax2.set_xlabel('Case Type', fontweight='bold')
    ax2.set_ylabel('Number of Failures', fontweight='bold')
    ax2.set_title('Failures by Case Type', fontweight='bold', fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(case_types)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v3_failure_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v3_failure_analysis.png")


def plot_difficulty_and_module(results):
    """Combined plot for difficulty and module."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # By difficulty
    by_diff = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        by_diff[r['difficulty']]['total'] += 1
        if r['validity_correct']:
            by_diff[r['difficulty']]['correct'] += 1
    
    diffs = ['easy', 'medium', 'hard']
    diff_acc = [by_diff[d]['correct'] / by_diff[d]['total'] * 100 for d in diffs]
    diff_n = [by_diff[d]['total'] for d in diffs]
    
    colors_diff = ['#27ae60', '#f1c40f', '#c0392b']
    bars1 = ax1.bar(diffs, diff_acc, color=colors_diff, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Accuracy (%)', fontweight='bold')
    ax1.set_title('Accuracy by Difficulty', fontweight='bold', fontsize=12)
    ax1.set_ylim(0, 105)
    for bar, acc, n in zip(bars1, diff_acc, diff_n):
        ax1.annotate(f'{acc:.1f}%\n(n={n})', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()+1),
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # By module
    by_mod = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        by_mod[r['module']]['total'] += 1
        if r['validity_correct']:
            by_mod[r['module']]['correct'] += 1
    
    mods = sorted(by_mod.keys())
    mod_acc = [by_mod[m]['correct'] / by_mod[m]['total'] * 100 for m in mods]
    mod_n = [by_mod[m]['total'] for m in mods]
    
    colors_mod = ['#3498db', '#e74c3c', '#9b59b6', '#2ecc71']
    bars2 = ax2.bar([m.replace('_', '\n') for m in mods], mod_acc, color=colors_mod, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Accuracy (%)', fontweight='bold')
    ax2.set_title('Accuracy by Module', fontweight='bold', fontsize=12)
    ax2.set_ylim(0, 105)
    for bar, acc, n in zip(bars2, mod_acc, mod_n):
        ax2.annotate(f'{acc:.1f}%\n(n={n})', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()+1),
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v3_difficulty_module.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v3_difficulty_module.png")


def main():
    print("Generating v3 benchmark figures...")
    results = load_results()
    
    plot_version_comparison()
    plot_case_type_breakdown(results)
    plot_hard_family_breakdown(results)
    plot_failure_types(results)
    plot_difficulty_and_module(results)
    
    print("\nAll figures generated!")


if __name__ == "__main__":
    main()
