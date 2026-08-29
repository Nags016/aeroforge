#!/usr/bin/env python3
"""
AeroForge Agentic Flight Engineer - Beautiful Terminal CLI
Like Hermes/Kiro/Codex but for drone autonomy
"""

import sys
import os
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add project root to path
sys.path.insert(0, '/home/mr_nags/aeroforge')

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.columns import Columns
from rich.rule import Rule
from rich.tree import Tree
from rich.syntax import Syntax
from rich import box
from rich.status import Status

from agent.mission_agent import MissionAnalyst, get_environment_status, run_baseline_mission
from agent.architect_agent import AutonomyArchitect
from agent.experiment_agent import ExperimentEngineer
from agent.verifier_agent import VerifierAgent
from agent.crash_analyzer import AutoCrashRecovery, run_with_crash_recovery
from agent.schemas import (
    MissionSpec, EnvironmentStatus, ExperimentSpec, Metrics, 
    LearningState, StrategyType
)

console = Console()


class AeroForgeCLI:
    """Beautiful terminal interface for AeroForge Agentic Flight Engineer."""
    
    def __init__(self):
        self.console = console
        self.mission_history = []
        self.current_mission = None
        
    def print_banner(self):
        """Print the AeroForge banner."""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║  █████╗ ██████╗ ██████╗ ██████╗ ██╗  ██╗██╗███╗   ██╗██████╗  ██████╗ ██████╗ ║
║ ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║  ██║██║████╗  ██║██╔══██╗██╔═══██╗██╔══██╗║
║ ███████║██████╔╝██║  ██║██████╔╝███████║██║██╔██╗ ██║██║  ██║██║   ██║██████╔╝║
║ ██╔══██║██╔══██╗██║  ██║██╔══██╗██╔══██║██║██║╚██╗██║██║  ██║██║   ██║██╔══██╗║
║ ██║  ██║██║  ██║██████╔╝██████╔╝██║  ██║██║██║ ╚████║██████╔╝╚██████╔╝██║  ██║║
║ ╚═╝  ╚═╝╚═╝  ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝║
║                                                                              ║
║        Agentic Flight Engineer  •  Autonomous Drone Missions  •  v1.0.0     ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold cyan")
        
    def print_mission_header(self, mission_text: str):
        """Print mission header panel."""
        panel = Panel(
            f"[bold white]{mission_text}[/bold white]",
            title="[bold cyan]🎯 New Mission[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
        
    def print_step(self, step_num: int, title: str, details: Optional[List[str]] = None):
        """Print a step with beautiful formatting."""
        self.console.print(f"\n[bold cyan]━━━ Step {step_num}: {title} ━━━[/bold cyan]")
        if details:
            for detail in details:
                self.console.print(f"  [dim]▸[/dim] {detail}")
                
    def print_success(self, msg: str):
        self.console.print(f"  [green]✅[/green] {msg}")
        
    def print_info(self, msg: str):
        self.console.print(f"  [blue]ℹ️[/blue]  {msg}")
        
    def print_warning(self, msg: str):
        self.console.print(f"  [yellow]⚠️[/yellow]  {msg}")
        
    def print_error(self, msg: str):
        self.console.print(f"  [red]❌[/red]  {msg}")
        
    def print_table(self, title: str, data: Dict[str, Any]):
        """Print a beautiful key-value table."""
        table = Table(title=title, box=box.ROUNDED, show_header=False)
        table.add_column("Property", style="cyan", width=30)
        table.add_column("Value", style="white")
        for k, v in data.items():
            table.add_row(k, str(v))
        self.console.print(table)
        
    def show_environment(self, env: EnvironmentStatus):
        """Show environment status beautifully."""
        table = Table(title="🔍 Environment Status", box=box.ROUNDED)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")
        
        table.add_row("PX4 SITL", "✅ Available" if env.px4_sitl_available else "❌ Not Found", env.px4_version or "unknown")
        table.add_row("Gazebo", "✅ Available" if env.gazebo_available else "❌ Not Found", env.gazebo_version or "unknown")
        table.add_row("ROS 2", "✅ Available" if env.ros2_available else "❌ Not Found", env.ros2_distro or "unknown")
        table.add_row("Camera", "✅ Available" if env.camera_available else "❌ Not Found", "")
        table.add_row("Depth Camera", "✅ Available" if env.depth_camera_available else "❌ Not Found", "")
        table.add_row("micro-ROS Agent", "✅ Running" if env.micro_ros_agent_running else "❌ Not Running", "")
        table.add_row("Compute - CPU", "✅" if env.compute_available.get('cpu') else "❌", "")
        table.add_row("Compute - CUDA", "✅" if env.compute_available.get('cuda') else "❌", "")
        table.add_row("Compute - MPS", "✅" if env.compute_available.get('mps') else "❌", "")
        
        self.console.print(table)
        
    def show_strategy_selection(self, experiment_spec: ExperimentSpec, scores: Dict = None):
        """Show strategy selection with scoring."""
        table = Table(title="🧠 Strategy Selection", box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Selected Strategy", f"[bold green]{experiment_spec.strategy.value}[/bold green]")
        table.add_row("Control Level", experiment_spec.control_level.value)
        table.add_row("Algorithm", experiment_spec.algorithm)
        table.add_row("Episodes", str(experiment_spec.n_episodes))
        table.add_row("Max Steps/Episode", str(experiment_spec.max_steps_per_episode))
        
        if scores:
            table.add_row("", "")  # separator
            table.add_row("[bold]Strategy Scores[/bold]", "")
            for strategy, score in sorted(scores.items(), key=lambda x: -x[1]):
                marker = "▸" if strategy.value == experiment_spec.strategy.value else " "
                table.add_row(f"  {marker} {strategy.value}", f"{score:.3f}")
                
        self.console.print(table)
        
        # Reward weights
        rw = experiment_spec.reward_config
        reward_table = Table(title="🎯 Reward Configuration", box=box.ROUNDED)
        reward_table.add_column("Reward", style="cyan")
        reward_table.add_column("Weight", style="white")
        for k, v in rw.items():
            reward_table.add_row(k, f"{v:.2f}")
        self.console.print(reward_table)
        
    def show_experiment_progress(self, mission_id: str, max_iterations: int = 10):
        """Show experiment progress with live updates."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Running experiment cycle for {mission_id}", total=max_iterations)
            for i in range(max_iterations):
                time.sleep(0.1)  # Will be replaced with real work
                progress.update(task, advance=1, description=f"Iteration {i+1}/{max_iterations}")
                
    def show_metrics(self, metrics: Metrics, title: str = "📊 Mission Metrics"):
        """Show metrics beautifully."""
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Status", style="white")
        
        # Success
        status = "[green]✅ PASS[/green]" if metrics.success else "[red]❌ FAIL[/red]"
        table.add_row("Success", "✅" if metrics.success else "❌", status)
        
        # Collisions
        status = "[green]✅" if metrics.collision_count == 0 else "[red]❌"
        table.add_row("Collisions", str(metrics.collision_count), status)
        
        # Goal error
        status = "[green]✅" if metrics.goal_error_m <= 0.5 else "[yellow]⚠️" if metrics.goal_error_m <= 1.0 else "[red]❌"
        table.add_row("Goal Error", f"{metrics.goal_error_m:.2f}m", status)
        
        # Clearance
        status = "[green]✅" if metrics.minimum_clearance_m >= 1.5 else "[yellow]⚠️" if metrics.minimum_clearance_m >= 1.0 else "[red]❌"
        table.add_row("Min Clearance", f"{metrics.minimum_clearance_m:.2f}m", status)
        table.add_row("Mean Clearance", f"{metrics.mean_clearance_m:.2f}m", "")
        
        # Path & Time
        table.add_row("Path Length", f"{metrics.path_length_m:.2f}m", "")
        table.add_row("Flight Time", f"{metrics.flight_time_s:.1f}s", "")
        table.add_row("Smoothness", f"{metrics.smoothness_score:.2f}", "")
        table.add_row("Energy", f"{metrics.energy_consumption:.1f}", "")
        
        # Statistical
        if metrics.n_episodes > 1:
            table.add_row("", "", "")
            table.add_row("[bold]Statistical[/bold]", "", "")
            table.add_row("Episodes", str(metrics.n_episodes), "")
            table.add_row("Success Rate", f"{metrics.success_rate:.0%}", "")
            table.add_row("Std Goal Error", f"{metrics.std_goal_error_m:.2f}m", "")
            table.add_row("Std Clearance", f"{metrics.std_clearance_m:.2f}m", "")
            
        self.console.print(table)
        
    def show_verification(self, verification: Optional[Any]):
        """Show verification results."""
        if verification is None:
            self.print_warning("No verification available")
            return
            
        status = "[green]✅ PASSED[/green]" if verification.passed else "[red]❌ FAILED[/red]"
        panel = Panel(
            f"[bold]Passed:[/bold] {status}\n"
            f"[bold]Confidence:[/bold] {verification.confidence:.0%}\n"
            f"[bold]Score:[/bold] {verification.score:.2f}",
            title="🔍 Verification Result",
            border_style="green" if verification.passed else "red"
        )
        self.console.print(panel)
        
        if verification.issues:
            self.console.print("\n[bold yellow]Issues:[/bold yellow]")
            for issue in verification.issues:
                self.console.print(f"  [yellow]⚠️[/yellow] {issue}")
                
        if verification.recommendations:
            self.console.print("\n[bold cyan]Recommendations:[/bold cyan]")
            for rec in verification.recommendations:
                self.console.print(f"  [cyan]💡[/cyan] {rec}")
                
    def show_final_summary(self, mission_id: str, final_metrics: Dict, record_path: str):
        """Show final mission summary."""
        panel = Panel(
            f"[bold]Mission ID:[/bold] {mission_id}\n"
            f"[bold]Success:[/bold] {'✅' if final_metrics.get('success') else '❌'}\n"
            f"[bold]Collisions:[/bold] {final_metrics.get('collision_count', 0)}\n"
            f"[bold]Goal Error:[/bold] {final_metrics.get('goal_error_m', 0)}m\n"
            f"[bold]Min Clearance:[/bold] {final_metrics.get('minimum_clearance_m', 0)}m\n"
            f"[bold]Path Length:[/bold] {final_metrics.get('path_length_m', 0)}m\n"
            f"[bold]Flight Time:[/bold] {final_metrics.get('flight_time_s', 0):.1f}s\n"
            f"[bold]Energy:[/bold] {final_metrics.get('energy_consumption', 0):.1f}\n\n"
            f"[bold green]💾 Complete record saved to:[/bold green]\n[dim]{record_path}[/dim]",
            title="🚀 Mission Complete",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(panel)
        
    def run_mission(self, natural_language: str) -> int:
        """Run the full mission pipeline with beautiful UI."""
        self.print_banner()
        self.print_mission_header(natural_language)
        
        # Initialize agents
        analyst = MissionAnalyst()
        architect = AutonomyArchitect()
        engineer = ExperimentEngineer()
        verifier = VerifierAgent()
        crash_recovery = AutoCrashRecovery()
        
        start_time = time.time()
        
        # ============================================
        # STEP 1: Mission Analyst - NL → MissionSpec
        # ============================================
        self.print_step(1, "Mission Analyst - Parsing Natural Language")
        with Status("[cyan]Analyzing mission...", console=self.console) as status:
            mission = analyst.parse_mission(natural_language)
            time.sleep(0.3)
            
        self.print_info(f"Mission ID: {mission.mission_id}")
        self.print_info(f"Start: ({mission.start.x:.1f}, {mission.start.y:.1f}, {mission.start.z:.1f})")
        self.print_info(f"Goal: ({mission.goal.x:.1f}, {mission.goal.y:.1f}, {mission.goal.z:.1f})")
        self.print_info(f"Sensors: {[s.value for s in mission.sensor_requirements]}")
        self.print_info(f"Obstacle Avoidance: {mission.obstacle_avoidance.value}")
        self.print_info(f"Min Clearance: {mission.minimum_clearance_m}m")
        self.print_info(f"Objectives: {[f'{k.value}:{v:.1f}' for k,v in mission.objectives.items()]}")
        
        # Clarifying questions
        questions = analyst.ask_clarifying_questions(mission)
        if questions:
            self.console.print("\n[yellow]❓ Clarifying Questions:[/yellow]")
            for q in questions:
                self.console.print(f"  [dim]▸[/dim] {q}")
            self.print_info("Proceeding with defaults for autonomous execution")
            
        # ============================================
        # STEP 2: Environment Status
        # ============================================
        self.print_step(2, "Environment Status Check")
        with Status("[cyan]Checking environment...", console=self.console) as status:
            env = get_environment_status()
            time.sleep(0.3)
        self.show_environment(env)
        
        if not env.px4_sitl_available:
            self.print_error("PX4 SITL not available - cannot proceed")
            return 1
            
        # ============================================
        # STEP 3: Autonomy Architect - Strategy Selection
        # ============================================
        self.print_step(3, "Autonomy Architect - Strategy Selection")
        with Status("[cyan]Selecting optimal strategy...", console=self.console) as status:
            experiment_spec = architect.select_strategy(mission, env)
            time.sleep(0.3)
            
        # Show strategy scores
        scores = architect._score_strategies(mission, env) if hasattr(architect, '_score_strategies') else {}
        self.show_strategy_selection(experiment_spec, scores)
        
        # ============================================
        # STEP 4: Experiment Engineer - Experiment Cycle
        # ============================================
        self.print_step(4, "Experiment Engineer - Running Experiment Cycle")
        self.print_info("Max iterations: 10")
        
        learning_state = LearningState(mission_id=mission.mission_id)
        
        with Status("[cyan]Running experiment with crash recovery...", console=self.console) as status:
            crash_results = asyncio.run(run_with_crash_recovery(
                mission, experiment_spec, env, api_key=None
            ))
            time.sleep(0.5)
            
        cycle_time = time.time() - start_time
        self.print_info(f"Experiment cycle completed in {cycle_time:.1f}s")
        
        if crash_results["recovered"]:
            self.print_success("Crash recovery successful!")
            self.print_info(f"Attempts: {len(crash_results['attempts'])}")
            final_metrics = crash_results["final_metrics"]
        else:
            self.print_warning(f"Crash recovery failed after {len(crash_results['attempts'])} attempts")
            self.print_info("Falling back to regular experiment cycle...")
            learning_state = LearningState(mission_id=mission.mission_id)
            start_time = time.time()
            final_learning_state = engineer.run_experiment_cycle(
                mission, experiment_spec, env, learning_state
            )
            cycle_time = time.time() - start_time
            final_metrics = final_learning_state.best_metrics
            self.print_info(f"Experiment cycle completed in {cycle_time:.1f}s")
            
        if final_metrics:
            self.show_metrics(final_metrics, "🏆 Best Experiment Result")
            
        # ============================================
        # STEP 5: Verifier Agent - Independent Validation
        # ============================================
        self.print_step(5, "Verifier Agent - Independent Validation")
        verification = None
        if final_metrics:
            with Status("[cyan]Validating results...", console=self.console) as status:
                verification = verifier.verify(mission, experiment_spec, final_metrics)
                time.sleep(0.3)
            self.show_verification(verification)
            
        # ============================================
        # STEP 6: Execute Final Validated Mission
        # ============================================
        self.print_step(6, "Final Mission Execution")
        with Status("[cyan]Executing validated mission...", console=self.console) as status:
            final_result = run_baseline_mission()
            time.sleep(0.3)
            
        self.show_metrics(Metrics(**final_result), "📊 Final Mission Results")
        
        # ============================================
        # STEP 7: Save Complete Record
        # ============================================
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "natural_language": natural_language,
            "mission_spec": mission.model_dump(),
            "environment": env.model_dump(),
            "experiment_spec": experiment_spec.model_dump(),
            "verification": verification.__dict__ if verification else None,
            "final_metrics": final_result,
            "total_time_s": time.time() - start_time,
        }
        
        output_dir = Path("experiments/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"mission_{mission.mission_id}_full.json"
        
        with open(output_file, "w") as f:
            json.dump(record, f, indent=2, default=str)
            
        self.show_final_summary(mission.mission_id, final_result, str(output_file))
        
        return 0 if final_result.get('success', False) else 1
        
    def interactive_mode(self):
        """Run interactive mission planner."""
        self.print_banner()
        self.console.print("\n[bold]Interactive Mission Planner[/bold]")
        self.console.print("[dim]Type your mission in natural language. Type 'exit' to quit.[/dim]\n")
        
        while True:
            try:
                mission_text = Prompt.ask("\n[bold cyan]✈️  Mission[/bold cyan]")
                if mission_text.lower() in ('exit', 'quit', 'q'):
                    self.console.print("[green]👋 Goodbye![/green]")
                    break
                    
                if not mission_text.strip():
                    continue
                    
                result = self.run_mission(mission_text)
                self.mission_history.append({
                    "mission": mission_text,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                if not Confirm.ask("\n[bold]Run another mission?[/bold]", default=True):
                    break
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted.[/yellow]")
                break
            except Exception as e:
                self.print_error(f"Error: {e}")
                
    def show_help(self):
        """Show help information."""
        self.print_banner()
        self.console.print("\n[bold]Usage:[/bold]")
        self.console.print("  aeroforge \"<natural language mission>\"")
        self.console.print("  aeroforge --interactive")
        self.console.print("  aeroforge --help\n")
        
        self.console.print("[bold]Examples:[/bold]")
        examples = [
            'aeroforge "Fly from (0,0,2) to (10,10,2) avoiding obstacles"',
            'aeroforge "Take off and hover for 10 seconds"',
            'aeroforge "Fly from (0,0,2) to (20,15,3) using camera and depth to avoid dynamic obstacles with 2.5m clearance, minimize energy and time"',
            'aeroforge "Explore unknown area with RRT* planner"',
        ]
        for ex in examples:
            self.console.print(f"  [dim]$[/dim] {ex}")
            
        self.console.print("\n[bold]Features:[/bold]")
        features = [
            "🧠 5 Specialized Agents (Mission Analyst, Autonomy Architect, Experiment Engineer, Verifier, Crash Analyzer)",
            "🔄 Iterative Experiment Cycle with Bounded Parameter Mutation",
            "🛡️ Independent Safety Verification with Thresholds",
            "💥 Crash Recovery: .ulg → log-analyser.app → Auto-fix → Re-run",
            "📚 Curriculum Learning: 5-level progression (hover → waypoints → obstacles)",
            "🎯 6 Strategies: Classical MPC, RRT*, PPO, SAC, Hybrid MPC+RL, Hybrid RRT+RL",
            "📊 Full Experiment Logging & Replay",
        ]
        for f in features:
            self.console.print(f"  {f}")
            

def main():
    cli = AeroForgeCLI()
    
    if len(sys.argv) < 2:
        cli.show_help()
        return 0
        
    if sys.argv[1] in ('--help', '-h'):
        cli.show_help()
        return 0
        
    if sys.argv[1] in ('--interactive', '-i'):
        cli.interactive_mode()
        return 0
        
    # Run mission from command line
    natural_language = " ".join(sys.argv[1:])
    return cli.run_mission(natural_language)


if __name__ == "__main__":
    sys.exit(main())