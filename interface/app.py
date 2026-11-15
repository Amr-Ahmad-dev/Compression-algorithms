"""
Main Application Window for the Compression Laboratory.
Tabbed navigation connecting Dashboard, Analysis, Educational Lab, Tournament, and Generator.
"""

from typing import Any, Dict
import customtkinter as ctk

from interface.dashboard_view import DashboardView
from interface.analysis_view import AnalysisView
from interface.lab_view import LabView
from interface.tournament_view import TournamentView
from interface.generator_view import GeneratorView


class CompressionLabApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Compression Laboratory — Algorithmic Research & Benchmarking")
        self.geometry("1100x740")
        self.minsize(980, 650)

        # Configure appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Shared application state
        self._shared_state: Dict[str, Any] = {
            "active_data": "Welcome to the Compression Laboratory. Analyze, encode, and benchmark from-scratch algorithms.".encode("utf-8"),
            "active_name": "welcome_sample.txt",
            "is_archive": False,
            "active_stats": None,
        }

        self._build_layout()

    def get_shared_state(self, key: str) -> Any:
        return self._shared_state.get(key)

    def set_shared_state(self, key: str, value: Any) -> None:
        self._shared_state[key] = value

    def log_message(self, message: str) -> None:
        print(f"[Lab] {message}")

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Bar
        header = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=("#E5E7EB", "#18181B"))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        title_lbl = ctk.CTkLabel(
            header,
            text="🔬 File Compression Laboratory",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold")
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        theme_switch = ctk.CTkSwitch(
            header,
            text="Light Mode",
            command=self._toggle_theme
        )
        theme_switch.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        # Main Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")

        tab_dash = self.tabview.add("Dashboard")
        tab_analysis = self.tabview.add("Statistical Analysis")
        tab_lab = self.tabview.add("Educational Lab")
        tab_tourney = self.tabview.add("Tournament")
        tab_gen = self.tabview.add("Entropy Generator")

        # Instantiate Views
        self.dash_view = DashboardView(
            tab_dash,
            self.get_shared_state,
            self.set_shared_state,
            self.log_message
        )
        self.dash_view.pack(fill="both", expand=True)

        self.analysis_view = AnalysisView(
            tab_analysis,
            self.get_shared_state,
            self.set_shared_state
        )
        self.analysis_view.pack(fill="both", expand=True)

        self.lab_view = LabView(
            tab_lab,
            self.get_shared_state,
            self.set_shared_state
        )
        self.lab_view.pack(fill="both", expand=True)

        self.tourney_view = TournamentView(
            tab_tourney,
            self.get_shared_state,
            self.set_shared_state,
            self.log_message
        )
        self.tourney_view.pack(fill="both", expand=True)

        self.gen_view = GeneratorView(
            tab_gen,
            self.get_shared_state,
            self.set_shared_state,
            self.log_message
        )
        self.gen_view.pack(fill="both", expand=True)

    def _toggle_theme(self):
        curr = ctk.get_appearance_mode()
        if curr == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")


def run_app():
    app = CompressionLabApp()
    app.mainloop()
