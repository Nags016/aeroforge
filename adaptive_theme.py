#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
AeroForge Universal CLI - Adaptive Drone Theme
- Detects terminal capabilities (truecolor, 256-color, 16-color, basic)
- Auto-selects best theme
- Works on ANY terminal (Linux/macOS/Windows/WSL/SSH)
- Git clone → run immediately
"""

import sys
import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
import platform

# Add project path
sys.path.insert(0, '/home/mr_nags/aeroforge')


class TerminalCapabilities(Enum):
    TRUECOLOR = "truecolor"      # 24-bit RGB (16M colors)
    HIGH_COLOR = "256color"      # 256 colors
    BASIC_COLOR = "16color"      # 16 colors (ANSI)
    MONOCHROME = "monochrome"    # No color support


class DroneTheme:
    """Adaptive drone-themed color schemes for different terminal capabilities."""
    
    # ============================================================
    # TRUECOLOR THEME (24-bit RGB) - Full drone aesthetic
    # ============================================================
    TRUECOLOR = {
        # Drone body colors
        "drone_primary": "#00D4FF",      # Cyan - primary drone accent
        "drone_secondary": "#FF6B00",    # Orange - warning/attention
        "drone_body": "#1A1A2E",         # Dark navy - drone body
        "drone_propeller": "#E8E8E8",    # Light gray - propellers
        "drone_camera": "#FFD700",       # Gold - camera/sensors
        
        # Sky/environment
        "sky_day": "#87CEEB",            # Sky blue
        "sky_dusk": "#FF7F50",           # Coral sunset
        "sky_night": "#0F0F23",          # Deep night
        "cloud": "#F0F0F0",              # White clouds
        "ground": "#2D5A27",             # Forest green
        
        # UI colors
        "success": "#00FF88",            # Bright green - success
        "warning": "#FFAA00",            # Amber - warning
        "error": "#FF3366",              # Red-pink - error
        "info": "#00D4FF",               # Cyan - info
        "highlight": "#FFFF00",          # Yellow - highlight
        "muted": "#666666",              # Gray - muted text
        
        # Panels/borders
        "panel_bg": "#0D1117",           # GitHub dark bg
        "panel_border": "#30363D",       # Subtle border
        "panel_title": "#58A6FF",        # Blue title
        "panel_header": "#161B22",       # Header bg
        
        # Text
        "text_primary": "#E6EDF3",       # Primary text
        "text_secondary": "#8B949E",     # Secondary text
        "text_accent": "#FFD700",        # Gold accent
        
        # Progress/bars
        "bar_filled": "#00D4FF",         # Progress fill
        "bar_empty": "#21262D",          # Progress empty
        
        # Drone status indicators
        "armed": "#FF3366",              # Red when armed
        "disarmed": "#00FF88",           # Green when disarmed
        "offboard": "#00D4FF",           # Cyan for offboard
        "mission": "#FFAA00",            # Amber for mission
        "rtl": "#FF6B00",                # Orange for RTL
        
        # Telemetry
        "altitude": "#00FF88",           # Green altitude
        "velocity": "#00D4FF",           # Cyan velocity
        "battery_high": "#00FF88",       # Green battery
        "battery_med": "#FFAA00",        # Amber battery
        "battery_low": "#FF3366",        # Red battery
        "gps_lock": "#00D4FF",           # Cyan GPS
        "gps_no_lock": "#FF3366",        # Red no GPS
        
        # ASCII art colors
        "ascii_drone": "#00D4FF",
        "ascii_prop": "#E8E8E8",
        "ascii_ground": "#2D5A27",
        "ascii_sky": "#87CEEB",
    }
    
    # ============================================================
    # 256-COLOR THEME - Approximated from truecolor
    # ============================================================
    COLOR256 = {
        "drone_primary": "39",      # Blue-cyan
        "drone_secondary": "208",   # Orange
        "drone_body": "235",        # Very dark gray
        "drone_propeller": "252",   # Light gray
        "drone_camera": "220",      # Gold
        
        "sky_day": "117",           # Light blue
        "sky_dusk": "209",          # Coral
        "sky_night": "233",         # Near black
        "cloud": "255",             # White
        "ground": "28",             # Dark green
        
        "success": "46",            # Bright green
        "warning": "214",           # Orange
        "error": "196",             # Red
        "info": "39",               # Cyan
        "highlight": "226",         # Yellow
        "muted": "242",             # Gray
        
        "panel_bg": "232",          # Near black
        "panel_border": "238",      # Dark gray
        "panel_title": "75",        # Blue
        "panel_header": "234",      # Dark gray
        
        "text_primary": "255",      # White
        "text_secondary": "245",    # Gray
        "text_accent": "220",       # Gold
        
        "bar_filled": "39",         # Cyan
        "bar_empty": "236",         # Dark gray
        
        "armed": "196",             # Red
        "disarmed": "46",           # Green
        "offboard": "39",           # Cyan
        "mission": "214",           # Orange
        "rtl": "208",               # Orange-red
        
        "altitude": "46",           # Green
        "velocity": "39",           # Cyan
        "battery_high": "46",       # Green
        "battery_med": "214",       # Orange
        "battery_low": "196",       # Red
        "gps_lock": "39",           # Cyan
        "gps_no_lock": "196",       # Red
        
        "ascii_drone": "39",
        "ascii_prop": "252",
        "ascii_ground": "28",
        "ascii_sky": "117",
    }
    
    # ============================================================
    # 16-COLOR THEME (ANSI) - Basic terminal support
    # ============================================================
    COLOR16 = {
        "drone_primary": "6",       # Cyan
        "drone_secondary": "3",     # Yellow/Orange
        "drone_body": "0",          # Black
        "drone_propeller": "7",     # White
        "drone_camera": "3",        # Yellow
        
        "sky_day": "6",             # Cyan
        "sky_dusk": "1",            # Red
        "sky_night": "0",           # Black
        "cloud": "7",               # White
        "ground": "2",              # Green
        
        "success": "2",             # Green
        "warning": "3",             # Yellow
        "error": "1",               # Red
        "info": "6",                # Cyan
        "highlight": "3",           # Yellow
        "muted": "8",               # Bright black (gray)
        
        "panel_bg": "0",            # Black
        "panel_border": "8",        # Gray
        "panel_title": "4",         # Blue
        "panel_header": "0",        # Black
        
        "text_primary": "7",        # White
        "text_secondary": "8",      # Gray
        "text_accent": "3",         # Yellow
        
        "bar_filled": "6",          # Cyan
        "bar_empty": "0",           # Black
        
        "armed": "1",               # Red
        "disarmed": "2",            # Green
        "offboard": "6",            # Cyan
        "mission": "3",             # Yellow
        "rtl": "1",                 # Red
        
        "altitude": "2",            # Green
        "velocity": "6",            # Cyan
        "battery_high": "2",        # Green
        "battery_med": "3",         # Yellow
        "battery_low": "1",         # Red
        "gps_lock": "6",            # Cyan
        "gps_no_lock": "1",         # Red
        
        "ascii_drone": "6",         # Cyan
        "ascii_prop": "7",          # White
        "ascii_ground": "2",        # Green
        "ascii_sky": "6",           # Cyan
    }
    
    # ============================================================
    # MONOCHROME THEME - No color support
    # ============================================================
    MONOCHROME = {
        "drone_primary": "",
        "drone_secondary": "",
        "drone_body": "",
        "drone_propeller": "",
        "drone_camera": "",
        
        "sky_day": "",
        "sky_dusk": "",
        "sky_night": "",
        "cloud": "",
        "ground": "",
        
        "success": "[OK]",
        "warning": "[WARN]",
        "error": "[ERROR]",
        "info": "[INFO]",
        "highlight": ">>>",
        "muted": "",
        
        "panel_bg": "",
        "panel_border": "",
        "panel_title": "",
        "panel_header": "",
        
        "text_primary": "",
        "text_secondary": "",
        "text_accent": "",
        
        "bar_filled": "█",
        "bar_empty": "░",
        
        "armed": "[ARMED]",
        "disarmed": "[SAFE]",
        "offboard": "[OFFBOARD]",
        "mission": "[MISSION]",
        "rtl": "[RTL]",
        
        "altitude": "",
        "velocity": "",
        "battery_high": "[BAT:HIGH]",
        "battery_med": "[BAT:MED]",
        "battery_low": "[BAT:LOW]",
        "gps_lock": "[GPS:OK]",
        "gps_no_lock": "[GPS:NO]",
        
        "ascii_drone": "",
        "ascii_prop": "",
        "ascii_ground": "",
        "ascii_sky": "",
    }


class TerminalDetector:
    """Detect terminal capabilities for adaptive theming."""
    
    @staticmethod
    def detect() -> TerminalCapabilities:
        """Detect terminal color support."""
        # Check environment variables
        term = os.environ.get('TERM', '').lower()
        colorterm = os.environ.get('COLORTERM', '').lower()
        
        # Explicit truecolor indicators
        if colorterm in ('truecolor', '24bit', '24-bit'):
            return TerminalCapabilities.TRUECOLOR
        
        # Check TERM for 256-color
        if '256color' in term or '256' in term:
            return TerminalCapabilities.HIGH_COLOR
        
        # Check for common truecolor terminals
        truecolor_terms = [
            'iterm2', 'alacritty', 'kitty', 'wezterm', 'rio', 'contour',
            'tabby', 'terminology', 'xfce4-terminal', 'gnome-terminal',
            'konsole', 'qterminal', 'terminator', 'tilix', 'hyper',
            'vscode', 'jetbrains', 'windows-terminal', 'wt'
        ]
        
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        term_program_version = os.environ.get('TERM_PROGRAM_VERSION', '').lower()
        
        for t in truecolor_terms:
            if t in term or t in term_program or t in term_program_version:
                return TerminalCapabilities.TRUECOLOR
        
        # Check COLORTERM for 256
        if colorterm in ('yes', 'true', '1', '256'):
            return TerminalCapabilities.HIGH_COLOR
        
        # Check for basic color support
        if 'color' in term or 'ansi' in term or 'xterm' in term or 'vt100' in term:
            return TerminalCapabilities.BASIC_COLOR
        
        # Check if we're in a known basic terminal
        if os.environ.get('TERM') in ('dumb', 'linux', 'vt100', 'vt220'):
            return TerminalCapabilities.BASIC_COLOR
        
        # Default: assume basic color
        return TerminalCapabilities.BASIC_COLOR
    
    @staticmethod
    def get_theme(capability: TerminalCapabilities) -> Dict:
        """Get theme for capability level."""
        themes = {
            TerminalCapabilities.TRUECOLOR: DroneTheme.TRUECOLOR,
            TerminalCapabilities.HIGH_COLOR: DroneTheme.COLOR256,
            TerminalCapabilities.BASIC_COLOR: DroneTheme.COLOR16,
            TerminalCapabilities.MONOCHROME: DroneTheme.MONOCHROME,
        }
        return themes.get(capability, DroneTheme.COLOR16)
    
    @staticmethod
    def supports_unicode() -> bool:
        """Check if terminal supports Unicode."""
        encoding = sys.stdout.encoding or 'ascii'
        return 'utf' in encoding.lower() or 'utf' in sys.stderr.encoding.lower()
    
    @staticmethod
    def get_terminal_size() -> Tuple[int, int]:
        """Get terminal width and height."""
        try:
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except:
            return 80, 24
    
    @staticmethod
    def is_ci() -> bool:
        """Check if running in CI environment."""
        return any(k in os.environ for k in ('CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'TRAVIS', 'CIRCLECI'))
    
    @staticmethod
    def is_ssh() -> bool:
        """Check if running over SSH."""
        return 'SSH_CONNECTION' in os.environ or 'SSH_CLIENT' in os.environ


class AdaptiveConsole:
    """Console that adapts to terminal capabilities."""
    
    def __init__(self):
        self.capability = TerminalDetector.detect()
        self.theme = TerminalDetector.get_theme(self.capability)
        self.unicode = TerminalDetector.supports_unicode() and not TerminalDetector.is_ci()
        self.width, self.height = TerminalDetector.get_terminal_size()
        self.is_ssh = TerminalDetector.is_ssh()
        self.is_ci = TerminalDetector.is_ci()
        
        # Try to use Rich if available and terminal supports it
        self.rich_console = None
        self._init_rich()
    
    def _init_rich(self):
        """Initialize Rich console if appropriate."""
        try:
            from rich.console import Console
            from rich.theme import Theme
            
            # Only use Rich for truecolor/256color with decent width
            if self.capability in (TerminalCapabilities.TRUECOLOR, TerminalCapabilities.HIGH_COLOR):
                if self.width >= 60:
                    # Create Rich theme from our drone theme
                    rich_theme = self._create_rich_theme()
                    self.rich_console = Console(
                        theme=rich_theme,
                        width=self.width,
                        force_terminal=True,
                        color_system="truecolor" if self.capability == TerminalCapabilities.TRUECOLOR else "256"
                    )
                    return
        except ImportError:
            pass
        
        self.rich_console = None
    
    def _get_rich_color_system(self) -> str:
        """Get Rich color system for capability."""
        if self.capability == TerminalCapabilities.TRUECOLOR:
            return "truecolor"
        elif self.capability == TerminalCapabilities.HIGH_COLOR:
            return "256"
        else:
            return "standard"
    
    def _create_rich_theme(self):
        """Create Rich theme from drone theme."""
        from rich.theme import Theme
        
        t = self.theme
        rich_theme = Theme({
            # Primary styles
            "drone.primary": t.get("drone_primary", "cyan"),
            "drone.secondary": t.get("drone_secondary", "yellow"),
            "drone.body": t.get("drone_body", "black"),
            "drone.propeller": t.get("drone_propeller", "white"),
            "drone.camera": t.get("drone_camera", "yellow"),
            
            # Status
            "success": t.get("success", "green"),
            "warning": t.get("warning", "yellow"),
            "error": t.get("error", "red"),
            "info": t.get("info", "cyan"),
            "armed": t.get("armed", "red"),
            "disarmed": t.get("disarmed", "green"),
            "offboard": t.get("offboard", "cyan"),
            "mission": t.get("mission", "yellow"),
            "rtl": t.get("rtl", "red"),
            
            # Telemetry
            "altitude": t.get("altitude", "green"),
            "velocity": t.get("velocity", "cyan"),
            "battery_high": t.get("battery_high", "green"),
            "battery_med": t.get("battery_med", "yellow"),
            "battery_low": t.get("battery_low", "red"),
            "gps_lock": t.get("gps_lock", "cyan"),
            "gps_no_lock": t.get("gps_no_lock", "red"),
            
            # UI
            "ui": t.get("panel_border", "gray"),
            "ui_panel": t.get("panel_bg", "black"),
            "ui_border": t.get("panel_border", "gray"),
            "ui_title": t.get("panel_title", "blue"),
            "ui_text": t.get("text_primary", "white"),
            "ui_text_dim": t.get("text_secondary", "gray"),
            "ui_accent": t.get("text_accent", "yellow"),
            "ui_bar_filled": t.get("bar_filled", "cyan"),
            "ui_bar_empty": t.get("bar_empty", "black"),
            
            # Progress
            "progress_bar": t.get("bar_filled", "cyan"),
            "progress_complete": t.get("success", "green"),
        })
        return rich_theme
    
    # ============================================================
    # Output methods
    # ============================================================
    
    def print(self, *args, **kwargs):
        """Print with automatic backend selection."""
        if self.rich_console:
            self.rich_console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)
    
    def print_banner(self):
        """Print adaptive drone banner."""
        banner = self._get_banner()
        if self.rich_console:
            self.rich_console.print(banner, style="drone.primary")
        else:
            self._print_plain(banner)
    
    def _get_banner(self) -> str:
        """Get banner appropriate for terminal width."""
        if self.width >= 80:
            return """
╔══════════════════════════════════════════════════════════════════════════════╗
║  █████╗ ██████╗ ██████╗ ██████╗ ██╗  ██╗██╗███╗   ██╗██████╗  ██████╗ ██████╗ ║
║ ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║  ██║██║████╗  ██║██╔══██╗██╔═══██╗██╔══██╗║
║ ███████║██████╔╝██║  ██║██████╔╝███████║██║██╔██╗ ██║██║  ██║██║   ██║██████╔╝║
║ ██╔══██║██╔══██╗██║  ██║██╔══██╗██╔══██║██║██║╚██╗██║██║  ██║██║   ██║██╔══██╗║
║ ██║  ██║██║  ██║██████╔╝██████╔╝██║  ██║██║██║ ╚████║██████╔╝╚██████╔╝██║  ██║║
║ ╚═════╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝║
║                                                                              ║
║    Autonomous Flight Engineer  •  NL → SITL → Hardware  •  v2.0             ║
╚══════════════════════════════════════════════════════════════════════════════╝"""
        elif self.width >= 60:
            return """
╔══════════════════════════════════════════════════════════╗
║  █████╗ ██████╗ ██████╗  Autonomous Flight Engineer  v2.0 ║
║ ██╔══██╗██╔══██╗██╔══██╗  NL → SITL → Hardware Deploy     ║
║ ███████║██████╔╝██║  ██║  5 Agents • 6 Strategies • RL    ║
║ ╚═════╝ ╚═════╝ ╚═════╝                                   ║
╚═════════════════════════════════════════════════════════╝"""
        else:
            return "🚁 AeroForge v2.0 - Autonomous Flight Engineer"
    
    def _print_plain(self, text: str):
        """Print without Rich, using ANSI codes if available."""
        if self.capability == TerminalCapabilities.MONOCHROME:
            print(text)
        else:
            # Simple ANSI color for banner
            color_code = self._get_ansi_color(self.theme.get("drone_primary", "6"))
            reset = "\033[0m" if self.capability != TerminalCapabilities.MONOCHROME else ""
            print(f"{color_code}{text}{reset}")
    
    def _get_ansi_color(self, color: str) -> str:
        """Convert theme color to ANSI escape code."""
        if self.capability == TerminalCapabilities.TRUECOLOR:
            # Convert hex to RGB ANSI
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                return f"\033[38;2;{r};{g};{b}m"
        elif self.capability == TerminalCapabilities.HIGH_COLOR:
            return f"\033[38;5;{color}m"
        elif self.capability == TerminalCapabilities.BASIC_COLOR:
            # Map basic ANSI colors
            ansi_map = {
                '0': '30', '1': '31', '2': '32', '3': '33',
                '4': '34', '5': '35', '6': '36', '7': '37',
                '8': '90', '9': '91', '10': '92', '11': '93',
                '12': '94', '13': '95', '14': '96', '15': '97',
            }
            return f"\033[{ansi_map.get(color, '37')}m"
        return ""
    
    def panel(self, content: str, title: str = "", style: str = "ui"):
        """Print a panel."""
        if self.rich_console:
            from rich.panel import Panel
            panel = Panel(content, title=title, border_style=style, expand=False)
            self.rich_console.print(panel)
        else:
            self._print_panel_plain(content, title)
    
    def _print_panel_plain(self, content: str, title: str):
        """Print panel without Rich."""
        width = min(self.width - 4, 76)
        border = self.theme.get("panel_border", "")
        title_color = self._get_ansi_color(self.theme.get("panel_title", "4"))
        reset = "\033[0m" if self.capability != TerminalCapabilities.MONOCHROME else ""
        
        if title:
            print(f"{title_color}┌─ {title} {'─' * (width - len(title) - 4)}┐{reset}")
        else:
            print(f"{title_color}┌{'─' * width}┐{reset}")
        
        for line in content.split('\n'):
            padding = width - len(line)
            print(f"{title_color}│{reset} {line}{' ' * padding} {title_color}│{reset}")
        
        print(f"{title_color}└{'─' * width}┘{reset}")
    
    def table(self, title: str, data: Dict, style: str = "ui"):
        """Print a key-value table."""
        if self.rich_console:
            from rich.table import Table
            table = Table(title=title, show_header=False, border_style="ui_border")
            table.add_column("Key", style="ui_text_dim")
            table.add_column("Value", style="ui_text")
            for k, v in data.items():
                table.add_row(k, str(v))
            self.rich_console.print(table)
        else:
            self._print_table_plain(title, data)
    
    def _print_table_plain(self, title: str, data: Dict):
        """Print table without Rich."""
        title_color = self._get_ansi_color(self.theme.get("panel_title", "4"))
        key_color = self._get_ansi_color(self.theme.get("text_secondary", "8"))
        val_color = self._get_ansi_color(self.theme.get("text_primary", "7"))
        reset = "\033[0m" if self.capability != TerminalCapabilities.MONOCHROME else ""
        
        if title:
            print(f"{title_color}{title}{reset}")
        
        max_key = max(len(k) for k in data.keys()) if data else 0
        for k, v in data.items():
            print(f"  {key_color}{k.ljust(max_key)}{reset} : {val_color}{v}{reset}")
    
    def progress_bar(self, current: int, total: int, label: str = "", width: int = 40):
        """Print a progress bar."""
        if total == 0:
            return
        
        pct = current / total
        filled = int(width * pct)
        empty = width - filled
        
        if self.capability == TerminalCapabilities.MONOCHROME:
            bar = "█" * filled + "░" * empty
            print(f"\r{label} [{bar}] {pct:.0%}", end="", flush=True)
        else:
            fill_color = self._get_ansi_color(self.theme.get("bar_filled", "6"))
            empty_color = self._get_ansi_color(self.theme.get("bar_empty", "0"))
            reset = "\033[0m"
            bar = f"{fill_color}{'█' * filled}{reset}{empty_color}{'░' * empty}{reset}"
            print(f"\r{label} [{bar}] {pct:.0%}", end="", flush=True)
        
        if current >= total:
            print()
    
    def drone_status(self, armed: bool, mode: str, battery: float, gps: bool, altitude: float, velocity: float):
        """Print drone status panel."""
        t = self.theme
        
        if self.rich_console:
            from rich.columns import Columns
            from rich.panel import Panel
            
            # Status indicator
            armed_status = ("[armed]● ARMED[/]", "[disarmed]○ SAFE[/]")[not armed]
            mode_styles = {
                "OFFBOARD": "offboard",
                "MISSION": "mission",
                "RTL": "rtl",
                "POSITION": "info",
                "ALTITUDE": "info",
            }
            mode_style = mode_styles.get(mode.upper(), "ui_text")
            
            # Battery
            if battery > 50:
                bat_style = "battery_high"
            elif battery > 20:
                bat_style = "battery_med"
            else:
                bat_style = "battery_low"
            
            # GPS
            gps_style = "gps_lock" if gps else "gps_no_lock"
            gps_text = "● GPS" if gps else "○ NO GPS"
            
            panels = [
                Panel(f"{armed_status}\n[{mode_style}]{mode}[/]", title="Status", border_style="ui_border"),
                Panel(f"[{bat_style}]{battery:.0f}%[/]", title="Battery", border_style="ui_border"),
                Panel(f"[{gps_style}]{gps_text}[/]", title="GPS", border_style="ui_border"),
                Panel(f"[altitude]{altitude:.1f}m[/]\n[velocity]{velocity:.1f}m/s[/]", 
                      title="Telemetry", border_style="ui_border"),
            ]
            self.rich_console.print(Columns(panels))
        else:
            # Plain text status
            armed_str = f"{t['armed']}ARMED" if armed else f"{t['disarmed']}SAFE"
            bat_str = f"{battery:.0f}%"
            gps_str = "GPS:OK" if gps else "GPS:NO"
            
            self._print_panel_plain(
                f"Status: {armed_str} | Mode: {mode}\n"
                f"Battery: {bat_str} | {gps_str}\n"
                f"Alt: {altitude:.1f}m | Vel: {velocity:.1f}m/s",
                "🚁 DRONE STATUS"
            )
    
    def drone_ascii(self, flying: bool = True):
        """Print drone ASCII art with theme colors."""
        if not self.unicode:
            return
        
        color = self._get_ansi_color(self.theme.get("ascii_drone", "6"))
        prop_color = self._get_ansi_color(self.theme.get("ascii_prop", "7"))
        ground_color = self._get_ansi_color(self.theme.get("ascii_ground", "2"))
        sky_color = self._get_ansi_color(self.theme.get("ascii_sky", "6"))
        reset = "\033[0m" if self.capability != TerminalCapabilities.MONOCHROME else ""
        
        if flying:
            drone = f"""{sky_color}
        \\   |   /
         \\  |  /
          \\ | /
{prop_color}     \\|/
{color}    ┌─────┐
    │  ●  │  ← Camera
    │ ███ │
    └─────┘
{prop_color}     /|\\
         / | \\
        /  |  \\
       /   |   \\
{ground_color}────────────────────
{reset}"""
        else:
            drone = f"""{color}
    ┌─────┐
    │  ●  │
    │ ███ │
    └─────┘
{ground_color}────────────────────
{reset}"""
        
        if self.rich_console:
            from rich.align import Align
            self.rich_console.print(Align.center(drone))
        else:
            print(drone)
    
    def success(self, msg: str):
        self._print_styled(msg, "success", "✅")
    
    def warning(self, msg: str):
        self._print_styled(msg, "warning", "⚠️")
    
    def error(self, msg: str):
        self._print_styled(msg, "error", "❌")
    
    def info(self, msg: str):
        self._print_styled(msg, "info", "ℹ️")
    
    def _print_styled(self, msg: str, style_key: str, icon: str = ""):
        """Print with style."""
        if self.rich_console:
            style = style_key  # Use direct style names
            self.rich_console.print(f"{icon} {msg}", style=style)
        else:
            color = self._get_ansi_color(self.theme.get(style_key, ""))
            reset = "\033[0m" if self.capability != TerminalCapabilities.MONOCHROME else ""
            prefix = self.theme.get(style_key, "") if self.capability == TerminalCapabilities.MONOCHROME else icon
            print(f"{color}{prefix} {msg}{reset}")
    
    def status_line(self, msg: str):
        """Print a status line (overwrites previous)."""
        if self.rich_console:
            self.rich_console.print(f"[ui_text_dim]{msg}[/]")
        else:
            color = self._get_ansi_color(self.theme.get("muted", "8"))
            reset = "\033[0m" if self.capability != TerminalCapabilities.MONOCHROME else ""
            print(f"\r{color}{msg}{reset}", end="", flush=True)


# Global adaptive console instance
console = AdaptiveConsole()


def get_console() -> AdaptiveConsole:
    """Get the global adaptive console."""
    return console


# Convenience functions
def print_banner():
    console.print_banner()

def success(msg): console.success(msg)
def warning(msg): console.warning(msg)
def error(msg): console.error(msg)
def info(msg): console.info(msg)

def panel(content, title="", style="ui"):
    console.panel(content, title, style)

def table(title, data, style="ui"):
    console.table(title, data, style)

def progress(current, total, label="", width=40):
    console.progress_bar(current, total, label, width)

def drone_status(armed, mode, battery, gps, altitude, velocity):
    console.drone_status(armed, mode, battery, gps, altitude, velocity)

def drone_ascii(flying=True):
    console.drone_ascii(flying)

def status(msg):
    console.status_line(msg)


if __name__ == "__main__":
    # Demo
    print(f"Detected: {console.capability.value}")
    print(f"Unicode: {console.unicode}")
    print(f"Width: {console.width}")
    print(f"SSH: {console.is_ssh}")
    print(f"CI: {console.is_ci}")
    print()
    
    console.print_banner()
    print()
    
    console.drone_ascii(flying=True)
    print()
    
    console.drone_status(
        armed=True, mode="OFFBOARD", battery=78.5, 
        gps=True, altitude=12.3, velocity=4.2
    )
    print()
    
    console.panel(
        "Mission: Fly from (0,0,2) to (10,10,2)\n"
        "Strategy: classical_mpc\n"
        "Clearance: 2.0m\n"
        "Status: ✅ VERIFIED",
        "🎯 MISSION PLAN"
    )
    print()
    
    console.table("📊 METRICS", {
        "Success Rate": "100%",
        "Collisions": "0",
        "Goal Error": "0.32m",
        "Min Clearance": "2.85m",
        "Flight Time": "10.4s",
        "Energy": "64.6",
    })
    print()
    
    for i in range(101):
        console.progress_bar(i, 100, "Training", 30)
        time.sleep(0.01)
    
    console.success("All systems nominal")
    console.warning("Wind gust detected")
    console.error("Obstacle proximity alert")
    console.info("Mission uploaded successfully")