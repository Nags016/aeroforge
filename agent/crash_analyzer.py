"""Crash Log Analysis Pipeline - Automatic .ulg analysis via log-analyser.app"""

import asyncio
import aiohttp
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.schemas import ExperimentSpec, MissionSpec, EnvironmentStatus

logger = logging.getLogger(__name__)


@dataclass
class CrashAnalysis:
    """Result of crash log analysis."""
    crash_type: str
    root_cause: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    affected_parameters: List[str]
    recommended_fixes: List[Dict[str, Any]]
    raw_report: Dict[str, Any]
    analysis_timestamp: str


@dataclass
class CrashEvent:
    """Detected crash event."""
    timestamp: str
    log_path: Path
    crash_type: str
    description: str


class LogAnalyserClient:
    """Client for log-analyser.app API."""
    
    BASE_URL = "https://log-analyser.app/api"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def upload_log(self, log_path: Path) -> Dict[str, Any]:
        """Upload .ulg log for analysis."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        with open(log_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=log_path.name, content_type='application/octet-stream')
            
            async with self.session.post(f"{self.BASE_URL}/analyze", data=data) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    raise RuntimeError(f"Analysis failed: {resp.status} - {error_text}")
    
    async def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Get analysis results by ID."""
        if not self.session:
            raise RuntimeError("Client not initialized.")
        
        async with self.session.get(f"{self.BASE_URL}/analysis/{analysis_id}") as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error_text = await resp.text()
                raise RuntimeError(f"Failed to get analysis: {resp.status} - {error_text}")


class ULogCrashDetector:
    """Detect crashes from PX4 .ulg logs."""
    
    CRASH_INDICATORS = {
        "crash": ["crash", "emergency", "failsafe", "terminated"],
        "gps_loss": ["gps_lost", "gps_failed", "no_gps"],
        "ekf_failure": ["ekf_failed", "ekf_reset", "estimator_failed"],
        "motor_failure": ["motor_failed", "esc_error", "actuator_fault"],
        "battery_critical": ["battery_critical", "low_battery", "voltage_low"],
        "rc_loss": ["rc_lost", "link_lost", "failsafe_triggered"],
        "collision": ["collision", "impact", "obstacle_hit"],
        "ekf_divergence": ["ekf_diverged", "innovation_fault", "covariance_exploded"],
    }
    
    def __init__(self, log_directory: Path = Path("/home/mr_nags/PX4-Autopilot/log")):
        self.log_directory = log_directory
        self.last_check_time = 0
    
    def find_latest_log(self) -> Optional[Path]:
        """Find the most recent .ulg log file."""
        logs = list(self.log_directory.glob("*.ulg"))
        if not logs:
            return None
        return max(logs, key=lambda p: p.stat().st_mtime)
    
    def detect_crash(self, log_path: Path) -> Optional[CrashEvent]:
        """Detect if log contains a crash using pyulog or log parsing."""
        try:
            import pyulog
            ulog = pyulog.ULog(str(log_path))
            
            # Check messages for crash indicators
            for msg in ulog.data_list:
                if msg.name in ["system_status", "vehicle_status", "estimator_status"]:
                    data = msg.data
                    # Check for crash indicators in status messages
                    
        except ImportError:
            # Fallback: parse text representation
            return self._parse_text_log(log_path)
        
        return None
    
    def _parse_text_log(self, log_path: Path) -> Optional[CrashEvent]:
        """Parse log using ulog2csv or text extraction."""
        try:
            result = subprocess.run(
                ["ulog2csv", str(log_path)], 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                csv_output = result.stdout
                return self._analyze_csv(csv_output, log_path)
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None
    
    def _analyze_csv(self, csv_data: str, log_path: Path) -> Optional[CrashEvent]:
        """Analyze CSV data for crash indicators."""
        lines = csv_data.strip().split('\n')
        if len(lines) < 2:
            return None
        
        headers = lines[0].split(',')
        data_rows = [line.split(',') for line in lines[1:]]
        
        for row in data_rows:
            row_dict = dict(zip(headers, row))
            # Check various status fields for crash indicators
            for crash_type, indicators in self.CRASH_INDICATORS.items():
                for key, value in row_dict.items():
                    if any(ind in str(value).lower() for ind in indicators):
                        return CrashEvent(
                            timestamp=datetime.now().isoformat(),
                            log_path=log_path,
                            crash_type=crash_type,
                            description=f"Detected {crash_type} in {key}: {value}"
                        )
        
        return None


class CrashAnalyzer:
    """Analyzes crash logs and generates fix recommendations."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.detector = ULogCrashDetector()
        self.fix_templates = self._load_fix_templates()
    
    def _load_fix_templates(self) -> Dict[str, List[Dict]]:
        """Load fix templates for different crash types."""
        return {
            "crash": [
                {"parameter": "reward_config.collision_penalty", "action": "multiply", "factor": 2.0},
                {"parameter": "algorithm_config.max_velocity", "action": "multiply", "factor": 0.7},
                {"parameter": "reward_config.clearance_reward_weight", "action": "multiply", "factor": 1.5},
            ],
            "gps_loss": [
                {"parameter": "reward_config.gps_loss_penalty", "action": "set", "value": -100.0},
                {"parameter": "algorithm_config.use_vision_fallback", "action": "set", "value": True},
            ],
            "ekf_failure": [
                {"parameter": "reward_config.ekf_health_weight", "action": "multiply", "factor": 2.0},
                {"parameter": "algorithm_config.ekf_check_frequency", "action": "set", "value": 10},
            ],
            "motor_failure": [
                {"parameter": "reward_config.motor_health_weight", "action": "multiply", "factor": 2.0},
                {"parameter": "algorithm_config.motor_check_frequency", "action": "set", "value": 5},
            ],
            "battery_critical": [
                {"parameter": "reward_config.battery_weight", "action": "multiply", "factor": 2.0},
                {"parameter": "algorithm_config.rtl_battery_threshold", "action": "multiply", "factor": 1.2},
            ],
            "rc_loss": [
                {"parameter": "algorithm_config.failsafe_action", "action": "set", "value": "rtl"},
                {"parameter": "reward_config.rc_loss_penalty", "action": "multiply", "factor": 2.0},
            ],
            "collision": [
                {"parameter": "reward_config.collision_penalty", "action": "multiply", "factor": 3.0},
                {"parameter": "algorithm_config.max_velocity", "action": "multiply", "factor": 0.5},
                {"parameter": "reward_config.clearance_reward_weight", "action": "multiply", "factor": 2.0},
                {"parameter": "algorithm_config.clearance_threshold", "action": "multiply", "factor": 1.5},
            ],
            "ekf_divergence": [
                {"parameter": "reward_config.ekf_innovation_weight", "action": "multiply", "factor": 2.0},
                {"parameter": "algorithm_config.ekf_reset_threshold", "action": "multiply", "factor": 0.5},
            ],
        }
    
    async def analyze_crash(self, log_path: Path) -> CrashAnalysis:
        """Analyze crash log and generate fix recommendations."""
        
        # First try local detection
        local_crash = self.detector.detect_crash(log_path)
        
        # Then try cloud analysis if API key available
        cloud_analysis = None
        if self.api_key:
            try:
                async with LogAnalyserClient(self.api_key) as client:
                    cloud_analysis = await client.upload_log(log_path)
            except Exception as e:
                logger.warning(f"Cloud analysis failed: {e}")
        
        # Combine local and cloud analysis
        return self._generate_analysis(log_path, local_crash, cloud_analysis)
    
    def _generate_analysis(
        self, 
        log_path: Path, 
        local_crash: Optional[CrashEvent],
        cloud_analysis: Optional[Dict]
    ) -> CrashAnalysis:
        """Generate comprehensive crash analysis."""
        
        crash_type = "unknown"
        severity = "MEDIUM"
        root_cause = "Unknown crash"
        affected_params = []
        
        # From cloud analysis
        if cloud_analysis:
            crash_type = cloud_analysis.get("crash_type", "unknown")
            severity = cloud_analysis.get("severity", "MEDIUM")
            root_cause = cloud_analysis.get("root_cause", "See analysis report")
        
        # From local detection
        if local_crash:
            crash_type = local_crash.crash_type
        
        # Determine affected parameters from fix templates
        affected_params = []
        recommended_fixes = []
        
        if crash_type in self.fix_templates:
            for fix in self.fix_templates[crash_type]:
                affected_params.append(fix["parameter"])
                recommended_fixes.append({
                    "parameter": fix["parameter"],
                    "action": fix["action"],
                    "value": fix.get("value"),
                    "factor": fix.get("factor"),
                    "reason": f"Fix for {crash_type} crash"
                })
        
        return CrashAnalysis(
            crash_type=crash_type,
            root_cause=root_cause,
            severity=severity,
            affected_parameters=affected_params,
            recommended_fixes=recommended_fixes,
            raw_report=cloud_analysis or {},
            analysis_timestamp=datetime.now().isoformat()
        )
    
    def apply_fixes(self, experiment_spec: "ExperimentSpec", analysis: CrashAnalysis) -> "ExperimentSpec":
        """Apply crash fixes to experiment specification."""
        import copy
        new_spec = copy.deepcopy(experiment_spec)
        
        for fix in analysis.recommended_fixes:
            param_path = fix["parameter"]
            action = fix["action"]
            
            # Navigate to parameter
            parts = param_path.split(".")
            obj = experiment_spec
            for part in parts[:-1]:
                obj = getattr(obj, part)
            
            param_name = parts[-1]
            current_value = getattr(obj, param_name, None)
            
            if fix["action"] == "multiply":
                factor = fix.get("factor", 1.0)
                setattr(obj, param_name, current_value * factor)
            elif fix["action"] == "set":
                setattr(obj, param_name, fix.get("value"))
            elif fix["action"] == "add":
                setattr(obj, param_name, current_value + fix.get("value", 0))
            
            logger.info(f"Applied fix: {fix['parameter']} {action} -> {getattr(obj, param_name)}")
        
        return experiment_spec


class AutoCrashRecovery:
    """Automatic crash recovery pipeline."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.analyzer = CrashAnalyzer(api_key)
        self.detector = ULogCrashDetector()
        self.max_recovery_attempts = 3
    
    async def monitor_and_recover(
        self, 
        experiment_runner, 
        experiment_spec: "ExperimentSpec",
        mission: "MissionSpec",
        env: "EnvironmentStatus",
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """Monitor for crashes and automatically recover."""
        
        results = {
            "original_spec": experiment_spec,
            "attempts": [],
            "final_metrics": None,
            "recovered": False,
        }
        
        current_spec = experiment_spec
        
        for attempt in range(max_attempts):
            print(f"\n🔄 Attempt {attempt + 1}/{max_attempts}")
            
            try:
                # Run experiment
                from agent.experiment_agent import ExperimentEngineer
                from agent.verifier_agent import VerifierAgent
                
                engineer = ExperimentEngineer()
                verifier = VerifierAgent()
                
                learning_state = engineer.run_experiment_cycle(
                    mission, current_spec, env
                )
                
                best_metrics = learning_state.best_metrics
                
                if not best_metrics:
                    raise RuntimeError("No metrics returned")
                
                # Verify
                verifier_agent = VerifierAgent()
                verification = verifier_agent.verify(mission, current_spec, best_metrics)
                
                if verification.passed:
                    print(f"✅ Experiment passed on attempt {attempt + 1}")
                    results["final_metrics"] = best_metrics
                    results["recovered"] = True
                    break
                else:
                    print(f"❌ Verification failed: {verification.issues}")
                    
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} crashed: {e}")
                
                # Check for crash log
                latest_log = self.detector.find_latest_log()
                if latest_log:
                    print(f"📋 Found log: {latest_log}")
                    
                    # Analyze crash
                    analysis = await self.analyzer.analyze_crash(latest_log)
                    print(f"🔍 Crash Analysis: {analysis.crash_type} - {analysis.root_cause}")
                    print(f"   Severity: {analysis.severity}")
                    
                    # Apply fixes
                    current_spec = self.analyzer.apply_fixes(current_spec, analysis)
                    print(f"🔧 Applied {len(analysis.recommended_fixes)} fixes")
                    
                    results["attempts"].append({
                        "attempt": attempt + 1,
                        "crashed": True,
                        "analysis": analysis.__dict__,
                        "fixes_applied": [f["parameter"] for f in analysis.recommended_fixes],
                    })
                else:
                    results["attempts"].append({
                        "attempt": attempt + 1,
                        "crashed": True,
                        "error": str(e),
                    })
        
        return results


# Integration with main pipeline
async def run_with_crash_recovery(
    mission,
    experiment_spec,
    env,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Run experiment with automatic crash recovery."""
    
    recovery = AutoCrashRecovery(api_key)
    return await recovery.monitor_and_recover(
        None, experiment_spec, mission, env
    )