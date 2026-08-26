"""Verifier Agent - independently validates experiment results"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from agent.schemas import Metrics, ExperimentSpec, MissionSpec


@dataclass
class VerificationResult:
    """Result of verification."""
    passed: bool
    confidence: float  # 0.0 to 1.0
    issues: List[str]
    recommendations: List[str]
    score: float  # 0.0 to 1.0


class VerifierAgent:
    """Independently validates experiment results against mission requirements."""
    
    def __init__(self):
        self.verification_thresholds = {
            "min_confidence": 0.8,
            "min_safety_score": 0.7,
            "max_acceptable_collision_rate": 0.0,
        }
    
    def verify(self, mission: "MissionSpec", experiment_spec: "ExperimentSpec", 
               metrics: "Metrics") -> "VerificationResult":
        """Verify experiment results against mission requirements."""
        
        issues = []
        recommendations = []
        scores = {}
        
        # 1. Safety verification
        safety_score, safety_issues = self._verify_safety(metrics)
        scores["safety"] = safety_score
        issues.extend(safety_issues)
        
        # 2. Performance verification
        perf_score, perf_issues = self._verify_performance(metrics)
        scores["performance"] = perf_score
        
        # 3. Mission compliance
        compliance_score, compliance_issues = self._verify_mission_compliance(metrics)
        scores["compliance"] = compliance_score
        
        # 3. Robustness check
        robustness_score, robustness_issues = self._verify_robustness(metrics)
        scores["robustness"] = robustness_score
        
        # 4. Statistical significance
        stats_score, stats_issues = self._verify_statistics(metrics)
        scores["statistics"] = stats_score
        
        # Aggregate
        all_issues = []
        for issue_list in [safety_issues, compliance_issues, robustness_issues]:
            issues.extend(issue_list)
        
        # Weighted overall score
        weights = {
            "safety": 0.35,
            "performance": 0.25,
            "compliance": 0.20,
            "robustness": 0.10,
            "statistics": 0.10,
        }
        
        overall_score = sum(weights[k] * v for k, v in {
            "safety": scores.get("safety", 0),
            "performance": scores.get("performance", 0),
            "compliance": scores.get("compliance", 0),
            "robustness": scores.get("robustness", 0),
            "statistics": scores.get("statistics", 0),
        }.items())
        
        # Confidence based on issue severity
        critical_issues = sum(1 for issue in issues if "CRITICAL" in issue)
        high_issues = sum(1 for issue in issues if "HIGH" in issue)
        confidence = max(0.0, 1.0 - critical_issues * 0.3 - high_issues * 0.1)
        
        # Recommendations
        recommendations = self._generate_recommendations(metrics, issues)
        
        passed = overall_score >= 0.7 and len([i for i in issues if "CRITICAL" in i]) == 0
        
        return VerificationResult(
            passed=passed,
            confidence=confidence,
            issues=issues,
            recommendations=recommendations,
            score=overall_score
        )
    
    def _verify_safety(self, metrics) -> tuple[float, List[str]]:
        """Verify safety constraints."""
        issues = []
        score = 1.0
        
        # Zero collisions required
        if metrics.collision_count > 0:
            issues.append(f"CRITICAL: {metrics.collision_count} collision(s) detected")
            score = 0.0
        
        # Minimum clearance
        if metrics.minimum_clearance_m < 1.0:
            issues.append(f"HIGH: Minimum clearance {metrics.minimum_clearance_m:.2f}m < 1.0m")
            score = min(score, 0.3)
        elif metrics.minimum_clearance_m < 1.5:
            issues.append(f"MEDIUM: Minimum clearance {metrics.minimum_clearance_m:.2f}m < 1.5m")
            score = min(score, 0.7)
        
        # Mean clearance
        if metrics.mean_clearance_m < 1.5:
            issues.append(f"MEDIUM: Mean clearance {metrics.mean_clearance_m:.2f}m below 1.5m")
            score = min(score, 0.7)
        
        return max(0.0, score), issues
    
    def _verify_performance(self, metrics) -> tuple[float, List[str]]:
        """Verify performance metrics."""
        issues = []
        score = 1.0
        
        # Goal accuracy
        if metrics.goal_error_m > 1.0:
            issues.append(f"HIGH: Goal error {metrics.goal_error_m:.2f}m > 1.0m")
            score = min(score, 0.5)
        elif metrics.goal_error_m > 0.5:
            issues.append(f"MEDIUM: Goal error {metrics.goal_error_m:.2f}m > 0.5m")
            score = min(score, 0.8)
        
        # Flight time
        if metrics.flight_time_s > 120:
            issues.append(f"MEDIUM: Flight time {metrics.flight_time_s:.1f}s > 120s")
            score = min(score, 0.7)
        elif metrics.flight_time_s > 60:
            issues.append(f"LOW: Flight time {metrics.flight_time_s:.1f}s > 60s")
            score = min(score, 0.9)
        
        # Smoothness
        if metrics.smoothness_score < 0.7:
            issues.append(f"LOW: Smoothness {metrics.smoothness_score:.2f} < 0.7")
            score = min(score, 0.8)
        
        return max(0.0, score), []
    
    def _verify_mission_compliance(self, metrics) -> tuple[float, List[str]]:
        """Verify mission compliance."""
        issues = []
        score = 1.0
        
        # Success required
        if not metrics.success:
            return 0.0, ["CRITICAL: Mission not successful"]
        
        # Collisions
        if metrics.collision_count > 0:
            return 0.0, ["CRITICAL: Collisions detected"]
        
        return 1.0, []
    
    def _verify_robustness(self, metrics) -> tuple[float, List[str]]:
        """Verify robustness indicators."""
        issues = []
        score = 1.0
        
        # Variance checks
        if metrics.std_goal_error_m > 0.3:
            issues.append(f"HIGH: High goal error variance ({metrics.std_goal_error_m:.2f}m)")
            score = min(score, 0.5)
        
        if metrics.std_clearance_m > 0.5:
            issues.append(f"MEDIUM: High clearance variance ({metrics.std_clearance_m:.2f}m)")
            score = min(score, 0.7)
        
        if metrics.smoothness_score < 0.5:
            issues.append(f"HIGH: Low smoothness ({metrics.smoothness_score:.2f})")
            score = min(score, 0.4)
        
        return max(0.0, score), issues
    
    def _verify_statistics(self, metrics) -> tuple[float, List[str]]:
        """Verify statistical validity."""
        issues = []
        score = 1.0
        
        if metrics.n_episodes < 5:
            issues.append(f"LOW: Only {metrics.n_episodes} episodes (need >=5 for statistics)")
            score = min(score, 0.7)
        
        if metrics.success_rate < 0.8:
            issues.append(f"HIGH: Success rate {metrics.success_rate:.1%} < 80%")
            score = min(score, 0.5)
        
        return score, []
    
    def _generate_recommendations(self, metrics, issues: List[str]) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        
        if any("collision" in i.lower() for i in issues):
            recs.append("Increase collision penalty in reward function")
            recs.append("Reduce maximum velocity")
            recs.append("Add safety layer / shield")
        
        if any("clearance" in i.lower() for i in issues):
            recs.append("Increase clearance reward weight")
            recs.append("Increase minimum clearance threshold")
            recs.append("Add potential field repulsion")
        
        if any("goal error" in i.lower() for i in issues):
            recs.append("Increase goal reward weight")
            recs.append("Improve goal reaching reward shaping")
        
        if any("flight time" in i.lower() for i in issues):
            recs.append("Increase time penalty weight")
            recs.append("Optimize trajectory for speed")
        
        if any("smoothness" in i.lower() for i in issues):
            recs.append("Increase action smoothness penalty")
            recs.append("Add jerk minimization to reward")
        
        if any("variance" in i.lower() or "std" in i.lower() for i in issues):
            recs.append("Increase training episodes")
            recs.append("Add entropy regularization")
            recs.append("Reduce learning rate")
        
        return recs


def verify_experiment(mission, experiment_spec, metrics) -> dict:
    """Convenience function for verification."""
    verifier = VerifierAgent()
    result = verifier.verify(None, None, metrics)
    return {
        "passed": result.passed,
        "confidence": result.confidence,
        "score": result.score,
        "issues": result.issues,
        "recommendations": result.recommendations,
    }