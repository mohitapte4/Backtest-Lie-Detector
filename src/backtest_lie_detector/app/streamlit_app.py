"""
Streamlit demo app for the Backtest Lie Detector.

Provides an interactive interface for:
1. Auditing custom finance workflows
2. Viewing benchmark results
3. Exploring example cases
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    ModelResponse,
    EvaluationConfig,
    Module,
    ViolationType,
)
from backtest_lie_detector.evals.prompts import (
    get_system_prompt,
    format_benchmark_prompt,
    get_violation_descriptions,
)
from backtest_lie_detector.evals.model_clients import (
    get_client,
    parse_model_json,
    MockClient,
)
from backtest_lie_detector.benchmark.build_cases import load_benchmark


# Page config
st.set_page_config(
    page_title="Backtest Lie Detector",
    page_icon="🔍",
    layout="wide",
)

# Load benchmark if available
@st.cache_data
def load_benchmark_data():
    benchmark_path = Path(__file__).parent.parent.parent.parent / "data" / "benchmark" / "benchmark_v1.jsonl"
    if benchmark_path.exists():
        return load_benchmark(str(benchmark_path))
    return []


@st.cache_data
def load_results_data():
    results_path = Path(__file__).parent.parent.parent.parent / "outputs" / "results" / "leaderboard.csv"
    if results_path.exists():
        return pd.read_csv(results_path, index_col=0)
    return None


def audit_workflow(workflow_text: str, model: str, provider: str) -> dict:
    """Run audit on a workflow using the selected model."""
    
    # Check for API key
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"error": "OPENAI_API_KEY not set"}
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"error": "ANTHROPIC_API_KEY not set"}
    
    # Create mock case for formatting
    mock_case = BenchmarkCase(
        id="user_input",
        module=Module.TICKER_TIME_MACHINE,
        difficulty="medium",
        prompt=workflow_text,
        expected_validity="invalid",
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes="User-submitted workflow",
    )
    
    # Get prompts
    system_prompt = get_system_prompt("finance_auditor")
    user_prompt = format_benchmark_prompt(mock_case)
    
    try:
        if model == "mock":
            client = MockClient()
        else:
            client = get_client(provider, model)
        
        raw_response, latency = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=2000,
        )
        
        parsed = parse_model_json(raw_response)
        
        return {
            "success": True,
            "raw": raw_response,
            "parsed": parsed,
            "latency_ms": latency,
        }
    except Exception as e:
        return {"error": str(e)}


# Main app
def main():
    st.title("🔍 Backtest Lie Detector")
    st.subheader("Audit Financial Research Workflows for Point-in-Time Validity")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Audit Tool", 
        "📊 Results", 
        "📚 Examples",
        "ℹ️ About"
    ])
    
    # Tab 1: Audit Tool
    with tab1:
        st.markdown("""
        Paste a description of a financial research workflow below. The model will 
        analyze it for point-in-time validity issues including:
        - **Ticker time travel**: Using modern identifiers for historical periods
        - **Filing clock leakage**: Using filing data before it was publicly available
        - **Accounting availability**: Using financial data before it was reported
        - **Survivorship bias**: Using only currently-listed securities for historical backtests
        """)
        
        # Input
        workflow = st.text_area(
            "Describe your financial research workflow:",
            height=150,
            placeholder=(
                "Example: A researcher studies Meta stock returns around the Cambridge "
                "Analytica scandal on March 20, 2018 using ticker META..."
            )
        )
        
        # Model selection
        col1, col2 = st.columns(2)
        with col1:
            provider = st.selectbox(
                "Provider",
                ["openai", "anthropic", "mock"],
                index=2,  # Default to mock for demo
            )
        with col2:
            if provider == "openai":
                model = st.selectbox("Model", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
            elif provider == "anthropic":
                model = st.selectbox("Model", ["claude-sonnet-4-20250514", "claude-3-opus-20240229"])
            else:
                model = "mock"
                st.info("Using mock model for demonstration")
        
        # Audit button
        if st.button("🔍 Audit Workflow", type="primary"):
            if not workflow.strip():
                st.warning("Please enter a workflow description")
            else:
                with st.spinner("Analyzing workflow..."):
                    result = audit_workflow(workflow, model, provider)
                
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                elif result.get("parsed"):
                    parsed = result["parsed"]
                    
                    # Display results
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        validity_color = {
                            "valid": "green",
                            "invalid": "red",
                            "ambiguous": "orange",
                        }
                        st.markdown(f"""
                        ### Validity
                        <h1 style='color: {validity_color.get(parsed.validity.value, "gray")}'>
                        {parsed.validity.value.upper()}
                        </h1>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("### Confidence")
                        st.progress(parsed.confidence)
                        st.write(f"{parsed.confidence:.0%}")
                    
                    with col3:
                        st.markdown("### Latency")
                        st.write(f"{result['latency_ms']:.0f} ms")
                    
                    # Violations
                    if parsed.violations:
                        st.markdown("### 🚨 Violations Detected")
                        violation_descs = get_violation_descriptions()
                        for v in parsed.violations:
                            st.error(f"**{v.value}**: {violation_descs.get(v, '')}")
                    else:
                        st.success("No violations detected")
                    
                    # Explanation
                    st.markdown("### 📝 Explanation")
                    st.write(parsed.explanation)
                    
                    # Repair suggestions
                    if parsed.repair:
                        st.markdown("### 🔧 Suggested Repairs")
                        for i, repair in enumerate(parsed.repair, 1):
                            st.write(f"{i}. {repair}")
                    
                    # Raw response (expandable)
                    with st.expander("View raw response"):
                        st.code(result["raw"], language="json")
                else:
                    st.error("Could not parse model response")
                    with st.expander("View raw response"):
                        st.code(result.get("raw", "No response"), language="text")
    
    # Tab 2: Results
    with tab2:
        st.markdown("### Benchmark Results")
        
        results = load_results_data()
        if results is not None:
            st.dataframe(results.style.format("{:.1%}").background_gradient(cmap='RdYlGn'))
            
            # Show figures if available
            figures_dir = Path(__file__).parent.parent.parent.parent / "outputs" / "figures"
            
            col1, col2 = st.columns(2)
            with col1:
                leaderboard_path = figures_dir / "leaderboard.png"
                if leaderboard_path.exists():
                    st.image(str(leaderboard_path), caption="Model Leaderboard")
            
            with col2:
                module_path = figures_dir / "module_breakdown.png"
                if module_path.exists():
                    st.image(str(module_path), caption="Accuracy by Module")
        else:
            st.info("No results available yet. Run evaluations first using `02_run_evals.ipynb`.")
            
            # Show sample results table
            st.markdown("#### Sample Results (Placeholder)")
            sample = pd.DataFrame({
                "Model": ["GPT-4o (Finance Auditor)", "GPT-4o (Minimal)", "Claude Sonnet"],
                "Validity Accuracy": ["85%", "72%", "83%"],
                "Violation Recall": ["78%", "65%", "80%"],
                "Repair Score": ["71%", "58%", "75%"],
            })
            st.table(sample)
    
    # Tab 3: Examples
    with tab3:
        st.markdown("### Example Benchmark Cases")
        
        cases = load_benchmark_data()
        
        if cases:
            # Filter by module
            module_filter = st.selectbox(
                "Filter by module:",
                ["All"] + [m.value for m in Module]
            )
            
            filtered = cases
            if module_filter != "All":
                filtered = [c for c in cases if c.module.value == module_filter]
            
            st.write(f"Showing {len(filtered)} cases")
            
            for i, case in enumerate(filtered[:10]):  # Show first 10
                with st.expander(f"**{case.id}** ({case.module.value}, {case.difficulty.value})"):
                    st.markdown("**Prompt:**")
                    st.write(case.prompt)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Expected Validity:** `{case.expected_validity.value}`")
                        st.markdown("**Expected Violations:**")
                        for v in case.expected_violations:
                            st.write(f"- {v.value}")
                    
                    with col2:
                        st.markdown("**Expected Repair:**")
                        for r in case.expected_repair:
                            st.write(f"- {r}")
                    
                    st.markdown("**Ground Truth Notes:**")
                    st.info(case.ground_truth_notes)
        else:
            st.info("No benchmark cases found. Generate them using `01_build_benchmark.ipynb`.")
    
    # Tab 4: About
    with tab4:
        st.markdown("""
        ## About Backtest Lie Detector
        
        This project benchmarks whether Large Language Models can reliably detect 
        point-in-time validity errors in financial research workflows.
        
        ### The Problem
        
        Financial backtests and event studies often contain subtle data leakage:
        - Using stock tickers that didn't exist at the historical date
        - Using SEC filing data before it was publicly available
        - Using accounting data before financial statements were filed
        - Testing strategies only on companies that survived to the present
        
        These errors can completely invalidate research results but are easy to miss.
        
        ### Our Approach
        
        We created a benchmark of realistic finance audit tasks testing whether LLMs can:
        1. **Detect** point-in-time validity issues
        2. **Identify** the specific type of violation
        3. **Propose** valid repairs
        
        ### Benchmark Modules
        
        | Module | Description |
        |--------|-------------|
        | Ticker Time Machine | Historical identifier validity |
        | Filing Clock | Information availability timing |
        | Accounting Availability | Fiscal period vs filing date |
        | Survivorship & Delisting | Universe construction bias |
        
        ### Key Findings
        
        [Results will be populated after running evaluations]
        
        ### Team
        
        UChicago Generative AI for Finance, Spring 2026
        
        ### Citation
        
        ```bibtex
        @misc{backtest-lie-detector-2026,
          title={Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors},
          year={2026}
        }
        ```
        """)


if __name__ == "__main__":
    main()
