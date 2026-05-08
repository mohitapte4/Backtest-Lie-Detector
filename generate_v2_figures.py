"""Generate updated figures for v2 benchmark results."""

import sys
sys.path.insert(0, 'src')

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import defaultdict
from backtest_lie_detector.benchmark.build_cases import generate_v2_cases
from backtest_lie_detector.schemas import Module, Difficulty, ViolationType

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11


def load_results():
    """Load and enrich results."""
    results = []
    with open('outputs/results/model_outputs_v2.jsonl') as f:
        for line in f:
            results.append(json.loads(line))
    
    cases = generate_v2_cases()
    case_map = {c.id: c for c in cases}
    
    for r in results:
        case = case_map.get(r['case_id'])
        if case:
            r['module'] = case.module.value
            r['difficulty'] = case.difficulty.value
            r['expected_validity'] = case.expected_validity.value
            r['expected_violations'] = [v.value for v in case.expected_violations]
        if r.get('parsed_response'):
            r['predicted_validity'] = r['parsed_response'].get('validity', 'unknown')
            r['confidence'] = r['parsed_response'].get('confidence', 0.5)
        
        # Determine case type
        if r['case_id'].startswith(('trap_', 'subtle_', 'multi_')):
            r['case_type'] = 'Adversarial'
        elif r['case_id'].startswith('wrds_'):
            r['case_type'] = 'WRDS-backed'
        else:
            r['case_type'] = 'Original'
    
    return results


def plot_module_breakdown(results):
    """Plot accuracy by module."""
    by_module = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        by_module[r['module']]['total'] += 1
        if r['validity_correct']:
            by_module[r['module']]['correct'] += 1
    
    modules = list(by_module.keys())
    accuracies = [by_module[m]['correct'] / by_module[m]['total'] * 100 for m in modules]
    totals = [by_module[m]['total'] for m in modules]
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    colors = ['#2ecc71', '#e74c3c', '#3498db', '#9b59b6']
    bars = ax.bar(range(len(modules)), accuracies, color=colors)
    
    ax.set_xlabel('Module', fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_title('GPT-4o Accuracy by Benchmark Module (v2)', fontweight='bold', fontsize=14)
    ax.set_xticks(range(len(modules)))
    ax.set_xticklabels([m.replace('_', ' ').title() for m in modules], rotation=15, ha='right')
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    
    # Add counts
    for bar, acc, total in zip(bars, accuracies, totals):
        ax.annotate(f'{acc:.1f}%\n(n={total})',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v2_module_breakdown.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v2_module_breakdown.png")


def plot_difficulty_breakdown(results):
    """Plot accuracy by difficulty."""
    by_diff = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        by_diff[r['difficulty']]['total'] += 1
        if r['validity_correct']:
            by_diff[r['difficulty']]['correct'] += 1
    
    order = ['easy', 'medium', 'hard']
    diffs = [d for d in order if d in by_diff]
    accuracies = [by_diff[d]['correct'] / by_diff[d]['total'] * 100 for d in diffs]
    totals = [by_diff[d]['total'] for d in diffs]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    colors = ['#27ae60', '#f1c40f', '#c0392b']
    bars = ax.bar(diffs, accuracies, color=colors)
    
    ax.set_xlabel('Difficulty', fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_title('GPT-4o Accuracy by Case Difficulty (v2)', fontweight='bold', fontsize=14)
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    
    for bar, acc, total in zip(bars, accuracies, totals):
        ax.annotate(f'{acc:.1f}%\n(n={total})',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v2_difficulty_breakdown.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v2_difficulty_breakdown.png")


def plot_case_type_breakdown(results):
    """Plot accuracy by case type (Original vs Adversarial vs WRDS)."""
    by_type = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        by_type[r['case_type']]['total'] += 1
        if r['validity_correct']:
            by_type[r['case_type']]['correct'] += 1
    
    order = ['Original', 'Adversarial', 'WRDS-backed']
    types = [t for t in order if t in by_type]
    accuracies = [by_type[t]['correct'] / by_type[t]['total'] * 100 for t in types]
    totals = [by_type[t]['total'] for t in types]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    colors = ['#3498db', '#e74c3c', '#2ecc71']
    bars = ax.bar(types, accuracies, color=colors)
    
    ax.set_xlabel('Case Type', fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_title('GPT-4o Accuracy by Case Type', fontweight='bold', fontsize=14)
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    
    for bar, acc, total in zip(bars, accuracies, totals):
        ax.annotate(f'{acc:.1f}%\n(n={total})',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v2_case_type_breakdown.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v2_case_type_breakdown.png")


def plot_confusion_matrix(results):
    """Plot confusion matrix for validity classification."""
    confusion = {
        ('valid', 'valid'): 0,
        ('valid', 'invalid'): 0,
        ('valid', 'ambiguous'): 0,
        ('invalid', 'valid'): 0,
        ('invalid', 'invalid'): 0,
        ('invalid', 'ambiguous'): 0,
    }
    
    for r in results:
        expected = r.get('expected_validity', 'unknown')
        predicted = r.get('predicted_validity', 'unknown')
        if (expected, predicted) in confusion:
            confusion[(expected, predicted)] += 1
    
    matrix = np.array([
        [confusion[('valid', 'valid')], confusion[('valid', 'invalid')], confusion[('valid', 'ambiguous')]],
        [confusion[('invalid', 'valid')], confusion[('invalid', 'invalid')], confusion[('invalid', 'ambiguous')]],
    ])
    
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(matrix, cmap='Blues')
    
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(['Valid', 'Invalid', 'Ambiguous'])
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['Valid', 'Invalid'])
    ax.set_xlabel('Predicted', fontweight='bold')
    ax.set_ylabel('Expected', fontweight='bold')
    ax.set_title('Validity Classification Confusion Matrix', fontweight='bold', fontsize=14)
    
    for i in range(2):
        for j in range(3):
            text = ax.text(j, i, matrix[i, j], ha='center', va='center', 
                          color='white' if matrix[i, j] > matrix.max()/2 else 'black', fontsize=14)
    
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig('outputs/figures/v2_confusion_matrix.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v2_confusion_matrix.png")


def plot_confidence_distribution(results):
    """Plot confidence distribution for correct vs incorrect predictions."""
    correct_conf = [r.get('confidence', 0.5) for r in results if r['validity_correct']]
    incorrect_conf = [r.get('confidence', 0.5) for r in results if not r['validity_correct']]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    ax.hist(correct_conf, bins=10, alpha=0.7, label=f'Correct (n={len(correct_conf)})', color='#27ae60')
    ax.hist(incorrect_conf, bins=10, alpha=0.7, label=f'Incorrect (n={len(incorrect_conf)})', color='#c0392b')
    
    ax.set_xlabel('Model Confidence', fontweight='bold')
    ax.set_ylabel('Count', fontweight='bold')
    ax.set_title('Confidence Distribution by Correctness', fontweight='bold', fontsize=14)
    ax.legend()
    ax.axvline(x=np.mean(correct_conf), color='#27ae60', linestyle='--', label=f'Mean (correct): {np.mean(correct_conf):.2f}')
    if incorrect_conf:
        ax.axvline(x=np.mean(incorrect_conf), color='#c0392b', linestyle='--', label=f'Mean (incorrect): {np.mean(incorrect_conf):.2f}')
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v2_confidence_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v2_confidence_distribution.png")


def plot_v1_vs_v2_comparison():
    """Compare v1 and v2 benchmark results."""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    versions = ['v1 (42 cases)', 'v2 (69 cases)']
    accuracies = [97.6, 95.7]
    colors = ['#3498db', '#9b59b6']
    
    bars = ax.bar(versions, accuracies, color=colors)
    
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_title('Benchmark Evolution: v1 vs v2', fontweight='bold', fontsize=14)
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)
    
    for bar, acc in zip(bars, accuracies):
        ax.annotate(f'{acc:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax.text(0.5, 0.85, '+27 harder cases\n+17 adversarial\n+10 WRDS-backed',
            transform=ax.transAxes, ha='center', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('outputs/figures/v2_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: outputs/figures/v2_comparison.png")


def main():
    print("Generating v2 benchmark figures...")
    results = load_results()
    
    plot_module_breakdown(results)
    plot_difficulty_breakdown(results)
    plot_case_type_breakdown(results)
    plot_confusion_matrix(results)
    plot_confidence_distribution(results)
    plot_v1_vs_v2_comparison()
    
    print("\nAll figures generated!")


if __name__ == "__main__":
    main()
