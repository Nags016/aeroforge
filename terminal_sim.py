#!/usr/bin/env python3
"""
AeroForge Terminal Simulation Visualization
ASCII/ANSI-based drone flight visualization for terminal demo
"""

import time
import math
import random
from typing import List, Tuple, Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align

console = Console()


class TerminalSimulator:
    """Terminal-based drone flight simulator with ASCII visualization."""
    
    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self.drone_pos = [width // 4, height // 2]
        self.goal_pos = [width * 3 // 4, height // 2]
        self.obstacles = []
        self.path = []
        self.trail = []
        self.frame = 0
        
    def generate_obstacles(self, num: int = 8):
        """Generate random obstacles."""
        self.obstacles = []
        for _ in range(num):
            x = random.randint(self.width // 5, self.width * 4 // 5)
            y = random.randint(2, self.height - 3)
            r = random.randint(1, 3)
            self.obstacles.append((x, y, r))
            
    def update_drone_position(self, target: Tuple[int, int], obstacles: List[Tuple[int, int, int]], dt: float = 0.1):
        """Update drone position with simple potential field avoidance."""
        dx = target[0] - self.drone_pos[0]
        dy = target[1] - self.drone_pos[1]
        dist = math.hypot(dx, dy)
        
        if dist < 1:
            return
            
        # Attractive force toward goal
        fx = dx / dist * 2.0
        fy = dy / dist * 2.0
        
        # Repulsive forces from obstacles
        for ox, oy, r in obstacles:
            odx = self.drone_pos[0] - ox
            ody = self.drone_pos[1] - oy
            odist = math.hypot(odx, ody)
            
            if odist < r + 5 and odist > 0.1:
                # Repulsion inversely proportional to distance
                repulsion = 10.0 / (odist * odist)
                fx += odx / odist * repulsion
                fy += ody / odist * repulsion
                
        # Update position
        new_x = max(1, min(self.width - 2, int(self.drone_pos[0] + fx * dt * 5)))
        new_y = max(1, min(self.height - 2, int(self.drone_pos[1] + fy * dt * 5)))
        self.drone_pos[0] = new_x
        self.drone_pos[1] = new_y
        
        # Record trail
        self.trail.append((int(self.drone_pos[0]), int(self.drone_pos[1])))
        if len(self.trail) > 100:
            self.trail.pop(0)
            
    def render_frame(self, mission_info: Optional[dict] = None) -> Panel:
        """Render a single frame of the simulation."""
        # Create canvas
        canvas = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        
        # Draw borders
        for x in range(self.width):
            canvas[0][x] = '─'
            canvas[self.height - 1][x] = '─'
        for y in range(self.height):
            canvas[y][0] = '│'
            canvas[y][self.width - 1] = '│'
        canvas[0][0] = '┌'
        canvas[0][self.width - 1] = '┐'
        canvas[self.height - 1][0] = '└'
        canvas[self.height - 1][self.width - 1] = '┘'
        
        # Draw trail
        for i, (tx, ty) in enumerate(self.trail):
            if 0 < tx < self.width - 1 and 0 < ty < self.height - 1:
                alpha = i / len(self.trail)
                if alpha > 0.7:
                    canvas[ty][tx] = '·'
                elif alpha > 0.4:
                    canvas[ty][tx] = '•'
                else:
                    canvas[ty][tx] = '°'
                    
        # Draw obstacles
        for ox, oy, r in self.obstacles:
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx*dx + dy*dy <= r*r:
                        x, y = ox + dx, oy + dy
                        if 0 < x < self.width - 1 and 0 < y < self.height - 1:
                            if dx*dx + dy*dy <= (r-1)*(r-1) and r > 1:
                                canvas[y][x] = '█'
                            else:
                                canvas[y][x] = '▓'
                                
        # Draw goal
        gx, gy = self.goal_pos
        if 0 < gx < self.width - 1 and 0 < gy < self.height - 1:
            canvas[gy][gx] = '🎯'
            # Goal ring
            for r in range(1, 4):
                for angle in range(0, 360, 30):
                    x = int(gx + r * math.cos(math.radians(angle)))
                    y = int(gy + r * math.sin(math.radians(angle)) * 0.5)
                    if 0 < x < self.width - 1 and 0 < y < self.height - 1 and canvas[y][x] == ' ':
                        canvas[y][x] = '○'
                        
        # Draw drone
        dx, dy = int(self.drone_pos[0]), int(self.drone_pos[1])
        if 0 < dx < self.width - 1 and 0 < dy < self.height - 1:
            # Drone body
            canvas[dy][dx] = '🚁'
            # Direction indicator
            if len(self.trail) > 1:
                px, py = self.trail[-2]
                dir_x = dx - px
                dir_y = dy - py
                if abs(dir_x) > abs(dir_y):
                    canvas[dy][dx + (1 if dir_x > 0 else -1)] = '▶' if dir_x > 0 else '◀'
                else:
                    canvas[dy + (1 if dir_y > 0 else -1)][dx] = '▼' if dir_y > 0 else '▲'
                    
        # Convert to strings
        lines = [''.join(row) for row in canvas]
        
        # Add mission info
        if mission_info:
            info_lines = [
                f"Mission: {mission_info.get('name', 'Unknown')}",
                f"Strategy: {mission_info.get('strategy', 'N/A')}",
                f"Step: {mission_info.get('step', 0)}/{mission_info.get('total_steps', 0)}",
                f"Distance to Goal: {math.hypot(self.goal_pos[0]-dx, self.goal_pos[1]-dy):.1f}",
                f"Collisions: {mission_info.get('collisions', 0)}",
                f"Clearance: {self.get_min_clearance():.1f}",
            ]
            # Add info to right side
            for i, line in enumerate(info_lines):
                if i < self.height - 2:
                    lines[i + 1] = lines[i + 1][:-1] + f"  {line}"
                    
        return Panel('\n'.join(lines), title="🎮 Live Simulation", border_style="cyan")
        
    def get_min_clearance(self) -> float:
        """Get minimum clearance from obstacles."""
        min_clear = float('inf')
        for ox, oy, r in self.obstacles:
            dist = math.hypot(self.drone_pos[0] - ox, self.drone_pos[1] - oy) - r
            min_clear = min(min_clear, dist)
        return max(0, min_clear)


def run_visualization_demo():
    """Run a demo visualization."""
    sim = TerminalSimulator(80, 20)
    sim.generate_obstacles(6)
    sim.goal_pos = [70, 10]
    
    mission_info = {
        'name': 'Waypoint Navigation',
        'strategy': 'Classical MPC',
        'step': 0,
        'total_steps': 100,
        'collisions': 0,
    }
    
    with Live(sim.render_frame(mission_info), console=console, refresh_per_second=10) as live:
        for step in range(150):
            sim.update_drone_position(tuple(sim.goal_pos), sim.obstacles)
            mission_info['step'] = step
            mission_info['collisions'] = 0  # Would track actual collisions
            
            live.update(sim.render_frame(mission_info))
            time.sleep(0.05)
            
            # Check if reached goal
            dist = math.hypot(sim.goal_pos[0] - sim.drone_pos[0], sim.goal_pos[1] - sim.drone_pos[1])
            if dist < 2:
                mission_info['step'] = step
                live.update(sim.render_frame(mission_info))
                break
                
    console.print("\n[green]✅ Simulation complete![/green]")


if __name__ == "__main__":
    run_visualization_demo()