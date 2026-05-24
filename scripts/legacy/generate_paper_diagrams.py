"""
Generate workflow diagrams for the IEEE CIFEr paper.
These replace the Draw.io diagrams with matplotlib-generated PNG figures.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def create_task_flow_diagram():
    """Create the benchmark task flow diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis('off')
    
    # Title
    ax.text(6, 4.7, 'Backtest Lie Detector: Benchmark Task Flow', 
            ha='center', va='center', fontsize=14, fontweight='bold')
    
    # Box 1: Research Workflow
    box1 = FancyBboxPatch((0.5, 2.5), 2.5, 1.5, boxstyle="round,pad=0.1",
                          facecolor='#dae8fc', edgecolor='#6c8ebf', linewidth=2)
    ax.add_patch(box1)
    ax.text(1.75, 3.25, 'Research Workflow\nDescription', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Example text below box 1
    ax.text(1.75, 1.8, '"A researcher backtests using\nsix-month lagged Compustat\nfundamentals from datadate..."', 
            ha='center', va='center', fontsize=8, style='italic',
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#999999'))
    
    # Arrow 1
    ax.annotate('', xy=(4, 3.25), xytext=(3.2, 3.25),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333333'))
    
    # Box 2: LLM Auditor
    box2 = FancyBboxPatch((4, 2.5), 2.5, 1.5, boxstyle="round,pad=0.1",
                          facecolor='#fff2cc', edgecolor='#d6b656', linewidth=2)
    ax.add_patch(box2)
    ax.text(5.25, 3.25, 'LLM Auditor', ha='center', va='center', 
            fontsize=12, fontweight='bold')
    
    # Prompt options below box 2
    ax.text(5.25, 1.8, 'System Prompt:\n• Generic (minimal)\n• Specialized (finance auditor)', 
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#999999'))
    
    # Arrow 2
    ax.annotate('', xy=(7.5, 3.25), xytext=(6.7, 3.25),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333333'))
    
    # Box 3: Structured Output
    box3 = FancyBboxPatch((7.5, 2.5), 2.5, 1.5, boxstyle="round,pad=0.1",
                          facecolor='#d5e8d4', edgecolor='#82b366', linewidth=2)
    ax.add_patch(box3)
    ax.text(8.75, 3.25, 'Structured\nAudit Output', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Output fields below box 3
    ax.text(8.75, 1.6, '• validity: valid | invalid | ambiguous\n• violations: [error types]\n• explanation: reasoning\n• repair: corrections', 
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#999999'))
    
    # Arrow 3
    ax.annotate('', xy=(11, 3.25), xytext=(10.2, 3.25),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333333'))
    
    # Box 4: Scoring
    box4 = FancyBboxPatch((10.5, 2.7), 1.3, 1.1, boxstyle="round,pad=0.1",
                          facecolor='#e1d5e7', edgecolor='#9673a6', linewidth=2)
    ax.add_patch(box4)
    ax.text(11.15, 3.25, 'Scoring', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('figures/benchmark_task_flow.png', dpi=150, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    print("Saved figures/benchmark_task_flow.png")


def create_taxonomy_diagram():
    """Create the point-in-time error taxonomy diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    
    # Title
    ax.text(7, 7.7, 'Point-in-Time Error Taxonomy: Four Benchmark Modules', 
            ha='center', va='center', fontsize=16, fontweight='bold')
    
    # Central node
    circle = plt.Circle((7, 5.5), 1, color='#ffe6cc', ec='#d79b00', linewidth=2)
    ax.add_patch(circle)
    ax.text(7, 5.5, 'Point-in-Time\nValidity Errors\n(141 Cases)', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Module 1: Ticker Time Machine (top left)
    box1 = FancyBboxPatch((1, 6.5), 3.5, 0.8, boxstyle="round,pad=0.05",
                          facecolor='#dae8fc', edgecolor='#6c8ebf', linewidth=2)
    ax.add_patch(box1)
    ax.text(2.75, 6.9, 'Ticker Time Machine (48)', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Details for module 1
    ax.text(2.75, 5.9, '• Ticker reassignment (S: Sears→Sprint)\n• FB→META June 2022 transition\n• GOOG vs GOOGL share class\n• Corporate spinoffs', 
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#666666'))
    
    # Line from center to module 1
    ax.plot([6, 4.5], [5.8, 6.5], 'k-', lw=2)
    
    # Module 2: Filing Clock (top right)
    box2 = FancyBboxPatch((9.5, 6.5), 3.5, 0.8, boxstyle="round,pad=0.05",
                          facecolor='#d5e8d4', edgecolor='#82b366', linewidth=2)
    ax.add_patch(box2)
    ax.text(11.25, 6.9, 'Filing Clock (31)', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Details for module 2
    ax.text(11.25, 5.9, '• EDGAR acceptance timestamp\n• Filing date vs acceptance time\n• 5:30 PM same-day rules\n• Timezone errors', 
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#666666'))
    
    # Line from center to module 2
    ax.plot([8, 9.5], [5.8, 6.5], 'k-', lw=2)
    
    # Module 3: Accounting Availability (bottom left)
    box3 = FancyBboxPatch((1, 3.5), 3.5, 0.8, boxstyle="round,pad=0.05",
                          facecolor='#fff2cc', edgecolor='#d6b656', linewidth=2)
    ax.add_patch(box3)
    ax.text(2.75, 3.9, 'Accounting Availability (24)', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Details for module 3
    ax.text(2.75, 2.9, '• Datadate vs filing date\n• Compustat PIT vs current\n• Restatement leakage\n• IBES forecast timing', 
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#666666'))
    
    # Line from center to module 3
    ax.plot([6, 4.5], [5.2, 4.3], 'k-', lw=2)
    
    # Module 4: Survivorship & Delisting (bottom right)
    box4 = FancyBboxPatch((9.5, 3.5), 3.5, 0.8, boxstyle="round,pad=0.05",
                          facecolor='#e1d5e7', edgecolor='#9673a6', linewidth=2)
    ax.add_patch(box4)
    ax.text(11.25, 3.9, 'Survivorship & Delisting (38)', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Details for module 4
    ax.text(11.25, 2.9, '• Universe construction bias\n• DLRET handling\n• Index announce vs effective\n• M&A timing', 
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#666666'))
    
    # Line from center to module 4
    ax.plot([8, 9.5], [5.2, 4.3], 'k-', lw=2)
    
    # Case Tags section
    ax.text(7, 1.8, 'Calibration Case Tags', ha='center', va='center', 
            fontsize=12, fontweight='bold')
    
    # Tag boxes
    tags = [
        ('trap_valid\n(22 cases)', '#d5e8d4', '#82b366', 2),
        ('ambiguous\n(14 cases)', '#fff2cc', '#d6b656', 5),
        ('false_valid_trap\n(16 cases)', '#f8cecc', '#b85450', 8),
        ('near_miss\n(17 cases)', '#e1d5e7', '#9673a6', 11),
    ]
    
    for label, fc, ec, x in tags:
        box = FancyBboxPatch((x, 0.6), 2.5, 0.9, boxstyle="round,pad=0.05",
                              facecolor=fc, edgecolor=ec, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + 1.25, 1.05, label, ha='center', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('figures/point_in_time_taxonomy.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Saved figures/point_in_time_taxonomy.png")


def create_safety_tradeoff_diagram():
    """Create the safety-utility tradeoff diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    
    # Title
    ax.text(6, 6.7, 'Safety-Utility Tradeoff in LLM Workflow Auditing', 
            ha='center', va='center', fontsize=16, fontweight='bold')
    
    # Generic Prompt Box
    box1 = FancyBboxPatch((0.5, 3.5), 5, 2.8, boxstyle="round,pad=0.1",
                          facecolor='#dae8fc', edgecolor='#6c8ebf', linewidth=2)
    ax.add_patch(box1)
    ax.text(3, 6, 'Generic Prompt', ha='center', va='center', 
            fontsize=14, fontweight='bold')
    ax.text(3, 5.4, 'Accuracy: 83.0%', ha='center', va='center', 
            fontsize=12, fontweight='bold', color='#27ae60')
    ax.text(3, 4.9, 'False Valid Rate: 4.7%', ha='center', va='center', 
            fontsize=12, fontweight='bold', color='#e74c3c')
    ax.text(3, 4.4, 'Trap Cases Missed: 3/16', ha='center', va='center', fontsize=11)
    ax.text(3, 3.8, 'Best for: Initial screening\nwhen false alarms are costly', 
            ha='center', va='center', fontsize=10, style='italic')
    
    # VS
    ax.text(6, 4.9, 'vs', ha='center', va='center', fontsize=20, fontweight='bold')
    
    # Specialized Prompt Box
    box2 = FancyBboxPatch((6.5, 3.5), 5, 2.8, boxstyle="round,pad=0.1",
                          facecolor='#d5e8d4', edgecolor='#82b366', linewidth=2)
    ax.add_patch(box2)
    ax.text(9, 6, 'Specialized Finance Auditor', ha='center', va='center', 
            fontsize=14, fontweight='bold')
    ax.text(9, 5.4, 'Accuracy: 80.9%', ha='center', va='center', 
            fontsize=12, fontweight='bold', color='#f39c12')
    ax.text(9, 4.9, 'False Valid Rate: 0.0%', ha='center', va='center', 
            fontsize=12, fontweight='bold', color='#27ae60')
    ax.text(9, 4.4, 'Trap Cases Missed: 0/16', ha='center', va='center', fontsize=11)
    ax.text(9, 3.8, 'Best for: High-stakes auditing\nwhen false approvals are costly', 
            ha='center', va='center', fontsize=10, style='italic')
    
    # Key Insight Box
    box3 = FancyBboxPatch((1.5, 1), 9, 2, boxstyle="round,pad=0.1",
                          facecolor='#fff2cc', edgecolor='#d6b656', linewidth=2)
    ax.add_patch(box3)
    ax.text(6, 2.7, 'Key Insight', ha='center', va='center', 
            fontsize=12, fontweight='bold')
    ax.text(6, 1.9, 'The optimal prompt depends on the loss function:\n'
            '• If false alarms are costly → Use generic prompt\n'
            '• If false approvals are costly → Use specialized prompt\n'
            'Both dramatically outperform rule-based baselines (81-100% false valid rate)', 
            ha='center', va='center', fontsize=10)
    
    # Scale
    ax.annotate('', xy=(10.5, 0.4), xytext=(1.5, 0.4),
                arrowprops=dict(arrowstyle='<->', lw=2, color='#333333'))
    ax.text(1.5, 0.1, 'Higher Utility\n(Accuracy)', ha='center', va='center', 
            fontsize=9, style='italic')
    ax.text(10.5, 0.1, 'Higher Safety\n(Lower FVR)', ha='center', va='center', 
            fontsize=9, style='italic')
    
    plt.tight_layout()
    plt.savefig('figures/safety_utility_tradeoff.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Saved figures/safety_utility_tradeoff.png")


if __name__ == "__main__":
    print("Generating paper diagrams...")
    create_task_flow_diagram()
    create_taxonomy_diagram()
    create_safety_tradeoff_diagram()
    print("\nAll diagrams generated successfully!")
