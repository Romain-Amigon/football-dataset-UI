# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.stats import norm
from datetime import datetime, timedelta
import kagglehub

# Authentification si nécessaire
kagglehub.login()

# Télécharger tous les fichiers du dataset
local_path = kagglehub.dataset_download(
    "davidcariboo/player-scores",
    force_download=False
)

print("Jeu de données téléchargé dans :", local_path)

class FootballComparisonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Comparaison des Clubs de Football")
        self.root.geometry("800x600")

        # ----- 1. Zone défilante -----
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        scrollbar_x.pack(side="bottom", fill="x")

        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.main_frame = ttk.Frame(self.canvas, padding="10")
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

        # ----- 2. Chargement des données -----
        try:
            self.clubs_df = pd.read_csv(f'{local_path}/clubs.csv')
            self.games_df = pd.read_csv(f'{local_path}/games.csv')
            self.players_df = pd.read_csv(f'{local_path}/players.csv')
            
            # Convertir la colonne 'date' en datetime
            self.games_df['date'] = pd.to_datetime(self.games_df['date'])
            current_date = datetime.now()
            cutoff_date = current_date - timedelta(days=5*365)  # Approximativement 5 ans
            self.games_df_recent = self.games_df[self.games_df['date'] >= cutoff_date]
            
            print(f"Date actuelle : {current_date.strftime('%Y-%m-%d')}")
            print(f"Date de coupure (5 ans avant) : {cutoff_date.strftime('%Y-%m-%d')}")
            print(f"Matchs totaux : {len(self.games_df)}")
            print(f"Matchs filtrés (5 dernières années) : {len(self.games_df_recent)}")
            
        except FileNotFoundError:
            messagebox.showerror("Erreur", "Fichiers CSV manquants !")
            return
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des données : {str(e)}")
            return

        self.club_names = self.clubs_df['name'].tolist()
        self.acronyms = {n: self.generate_acronym(n) for n in self.club_names}

        # ----- 3. Widgets -----
        ttk.Label(self.main_frame, text="Club 1:").grid(row=0, column=0, pady=5, sticky=tk.W)
        self.club1_search_var = tk.StringVar()
        entry1 = ttk.Entry(self.main_frame, textvariable=self.club1_search_var)
        entry1.grid(row=0, column=1, pady=5)
        entry1.bind('<KeyRelease>', lambda e: self.filter_clubs(self.club1_search_var, self.club1_combo))

        self.club1_var = tk.StringVar()
        self.club1_combo = ttk.Combobox(self.main_frame, textvariable=self.club1_var, values=self.club_names)
        self.club1_combo.grid(row=1, column=1, pady=5)

        ttk.Label(self.main_frame, text="Club 2:").grid(row=2, column=0, pady=5, sticky=tk.W)
        self.club2_search_var = tk.StringVar()
        entry2 = ttk.Entry(self.main_frame, textvariable=self.club2_search_var)
        entry2.grid(row=2, column=1, pady=5)
        entry2.bind('<KeyRelease>', lambda e: self.filter_clubs(self.club2_search_var, self.club2_combo))

        self.club2_var = tk.StringVar()
        self.club2_combo = ttk.Combobox(self.main_frame, textvariable=self.club2_var, values=self.club_names)
        self.club2_combo.grid(row=3, column=1, pady=5)

        ttk.Button(self.main_frame, text="Comparer", command=self.compare_clubs)\
            .grid(row=4, column=0, columnspan=2, pady=10)

        self.result_text = tk.Text(self.main_frame, height=25, width=80)
        self.result_text.grid(row=5, column=0, columnspan=2, pady=10)

    # ----- Scroll molette verticale -----
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ----- Scroll molette horizontale -----
    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def generate_acronym(self, name):
        words = name.split()
        acronym = ''.join(word[0].upper() for word in words if word)
        return acronym

    def filter_clubs(self, search_var, combo):
        search_text = search_var.get().lower()
        filtered_clubs = [
            name for name in self.club_names
            if search_text in name.lower() or search_text in self.acronyms[name].lower()
        ]
        combo['values'] = filtered_clubs
        if filtered_clubs:
            combo.current(0)

    def calculate_wins(self, club_id, matches):
        wins = 0
        for _, match in matches.iterrows():
            if match['home_club_id'] == club_id and match['home_club_goals'] > match['away_club_goals']:
                wins += 1
            elif match['away_club_id'] == club_id and match['away_club_goals'] > match['home_club_goals']:
                wins += 1
        return wins

    def calculate_goals(self, club_id, matches):
        total_goals = 0
        for _, match in matches.iterrows():
            if match['home_club_id'] == club_id:
                total_goals += match['home_club_goals']
            elif match['away_club_id'] == club_id:
                total_goals += match['away_club_goals']
        return total_goals

    def compare_clubs(self):
        club1_name = self.club1_var.get()
        club2_name = self.club2_var.get()

        if not club1_name or not club2_name:
            messagebox.showwarning("Attention", "Veuillez sélectionner deux clubs !")
            return

        if club1_name == club2_name:
            messagebox.showwarning("Attention", "Veuillez sélectionner deux clubs différents !")
            return

        # Effacer le texte précédent
        self.result_text.delete(1.0, tk.END)

        # Récupérer les IDs des clubs
        club1_id = self.clubs_df[self.clubs_df['name'] == club1_name]['club_id'].iloc[0]
        club2_id = self.clubs_df[self.clubs_df['name'] == club2_name]['club_id'].iloc[0]

        # Statistiques des clubs (globales)
        club1_info = self.clubs_df[self.clubs_df['club_id'] == club1_id]
        club2_info = self.clubs_df[self.clubs_df['club_id'] == club2_id]

        # Statistiques des joueurs (globales, car actuelles)
        club1_players = self.players_df[self.players_df['current_club_id'] == club1_id]
        club2_players = self.players_df[self.players_df['current_club_id'] == club2_id]

        # ----- Statistiques générales -----
        club1_matches = self.games_df[(self.games_df['home_club_id'] == club1_id) | (self.games_df['away_club_id'] == club1_id)]
        club2_matches = self.games_df[(self.games_df['home_club_id'] == club2_id) | (self.games_df['away_club_id'] == club2_id)]

        club1_wins = self.calculate_wins(club1_id, club1_matches)
        club2_wins = self.calculate_wins(club2_id, club2_matches)
        club1_goals = self.calculate_goals(club1_id, club1_matches)
        club2_goals = self.calculate_goals(club2_id, club2_matches)

        club1_total_matches = len(club1_matches)
        club2_total_matches = len(club2_matches)
        winrate1 = (club1_wins / club1_total_matches * 100) if club1_total_matches > 0 else 0
        winrate2 = (club2_wins / club2_total_matches * 100) if club2_total_matches > 0 else 0
        avg_goals1 = club1_goals / club1_total_matches if club1_total_matches > 0 else 0
        avg_goals2 = club2_goals / club2_total_matches if club2_total_matches > 0 else 0

        # Face à face général
        head_to_head = self.games_df[
            ((self.games_df['home_club_id'] == club1_id) & (self.games_df['away_club_id'] == club2_id)) |
            ((self.games_df['home_club_id'] == club2_id) & (self.games_df['away_club_id'] == club1_id))
        ]
        club1_head_wins = 0
        club2_head_wins = 0
        club1_head_goals = 0
        club2_head_goals = 0
        for _, match in head_to_head.iterrows():
            if match['home_club_goals'] > match['away_club_goals']:
                if match['home_club_id'] == club1_id:
                    club1_head_wins += 1
                    club1_head_goals += match['home_club_goals']
                    club2_head_goals += match['away_club_goals']
                else:
                    club2_head_wins += 1
                    club1_head_goals += match['away_club_goals']
                    club2_head_goals += match['home_club_goals']
            elif match['home_club_goals'] < match['away_club_goals']:
                if match['away_club_id'] == club1_id:
                    club1_head_wins += 1
                    club1_head_goals += match['away_club_goals']
                    club2_head_goals += match['home_club_goals']
                else:
                    club2_head_wins += 1
                    club1_head_goals += match['home_club_goals']
                    club2_head_goals += match['away_club_goals']
            else:  # Match nul
                club1_head_goals += match['away_club_goals'] if match['away_club_id'] == club1_id else match['home_club_goals']
                club2_head_goals += match['away_club_goals'] if match['away_club_id'] == club2_id else match['home_club_goals']

        total_h2h = len(head_to_head)
        proba1 = (club1_head_wins + 1) / (total_h2h + 2) if total_h2h > 0 else 0.5
        proba2 = (club2_head_wins + 1) / (total_h2h + 2) if total_h2h > 0 else 0.5
        avg_head_goals1 = club1_head_goals / total_h2h if total_h2h > 0 else 0
        avg_head_goals2 = club2_head_goals / total_h2h if total_h2h > 0 else 0

        # ----- Statistiques récentes (5 dernières années) -----
        club1_matches_recent = self.games_df_recent[(self.games_df_recent['home_club_id'] == club1_id) | (self.games_df_recent['away_club_id'] == club1_id)]
        club2_matches_recent = self.games_df_recent[(self.games_df_recent['home_club_id'] == club2_id) | (self.games_df_recent['away_club_id'] == club2_id)]

        club1_wins_recent = self.calculate_wins(club1_id, club1_matches_recent)
        club2_wins_recent = self.calculate_wins(club2_id, club2_matches_recent)
        club1_goals_recent = self.calculate_goals(club1_id, club1_matches_recent)
        club2_goals_recent = self.calculate_goals(club2_id, club2_matches_recent)

        club1_total_matches_recent = len(club1_matches_recent)
        club2_total_matches_recent = len(club2_matches_recent)
        winrate1_recent = (club1_wins_recent / club1_total_matches_recent * 100) if club1_total_matches_recent > 0 else 0
        winrate2_recent = (club2_wins_recent / club2_total_matches_recent * 100) if club2_total_matches_recent > 0 else 0
        avg_goals1_recent = club1_goals_recent / club1_total_matches_recent if club1_total_matches_recent > 0 else 0
        avg_goals2_recent = club2_goals_recent / club2_total_matches_recent if club2_total_matches_recent > 0 else 0

        # Face à face récent
        head_to_head_recent = self.games_df_recent[
            ((self.games_df_recent['home_club_id'] == club1_id) & (self.games_df_recent['away_club_id'] == club2_id)) |
            ((self.games_df_recent['home_club_id'] == club2_id) & (self.games_df_recent['away_club_id'] == club1_id))
        ]
        club1_head_wins_recent = 0
        club2_head_wins_recent = 0
        club1_head_goals_recent = 0
        club2_head_goals_recent = 0
        draws_recent = 0
        for _, match in head_to_head_recent.iterrows():
            if match['home_club_goals'] > match['away_club_goals']:
                if match['home_club_id'] == club1_id:
                    club1_head_wins_recent += 1
                    club1_head_goals_recent += match['home_club_goals']
                    club2_head_goals_recent += match['away_club_goals']
                else:
                    club2_head_wins_recent += 1
                    club1_head_goals_recent += match['away_club_goals']
                    club2_head_goals_recent += match['home_club_goals']
            elif match['home_club_goals'] < match['away_club_goals']:
                if match['away_club_id'] == club1_id:
                    club1_head_wins_recent += 1
                    club1_head_goals_recent += match['away_club_goals']
                    club2_head_goals_recent += match['home_club_goals']
                else:
                    club2_head_wins_recent += 1
                    club1_head_goals_recent += match['home_club_goals']
                    club2_head_goals_recent += match['away_club_goals']
            else:  # Match nul
                draws_recent += 1
                club1_head_goals_recent += match['away_club_goals'] if match['away_club_id'] == club1_id else match['home_club_goals']
                club2_head_goals_recent += match['away_club_goals'] if match['away_club_id'] == club2_id else match['home_club_goals']

        total_h2h_recent = len(head_to_head_recent)
        proba1_recent = (club1_head_wins_recent + 1) / (total_h2h_recent + 2) if total_h2h_recent > 0 else 0.5
        proba2_recent = (club2_head_wins_recent + 1) / (total_h2h_recent + 2) if total_h2h_recent > 0 else 0.5
        proba_draw_recent = (draws_recent + 1) / (total_h2h_recent + 2) if total_h2h_recent > 0 else 0.5
        avg_head_goals1_recent = club1_head_goals_recent / total_h2h_recent if total_h2h_recent > 0 else 0
        avg_head_goals2_recent = club2_head_goals_recent / total_h2h_recent if total_h2h_recent > 0 else 0

        # ----- Affichage des résultats -----
        cutoff_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        result = f"Comparaison entre {club1_name} et {club2_name}\n\n"
        
        # Statistiques générales
        result += f"===== Statistiques générales =====\n"
        result += f"--- {club1_name} ---\n"
        result += f"Nombre de joueurs: {len(club1_players)}\n"
        result += f"Matchs joués: {club1_total_matches}\n"
        result += f"Matchs gagnés: {club1_wins}\n"
        result += f"Win%: {winrate1:.2f}%\n"
        result += f"Buts marqués: {club1_goals}\n"
        result += f"Moyenne de buts par match: {avg_goals1:.2f}\n"
        result += f"Valeur totale du marché (M€): {club1_info['total_market_value'].iloc[0] if not pd.isna(club1_info['total_market_value'].iloc[0]) else 'N/A'}\n"
        result += f"Taille moyenne de l'effectif: {club1_info['squad_size'].iloc[0]}\n\n"

        result += f"--- {club2_name} ---\n"
        result += f"Nombre de joueurs: {len(club2_players)}\n"
        result += f"Matchs joués: {club2_total_matches}\n"
        result += f"Matchs gagnés: {club2_wins}\n"
        result += f"Win%: {winrate2:.2f}%\n"
        result += f"Buts marqués: {club2_goals}\n"
        result += f"Moyenne de buts par match: {avg_goals2:.2f}\n"
        result += f"Valeur totale du marché (M€): {club2_info['total_market_value'].iloc[0] if not pd.isna(club2_info['total_market_value'].iloc[0]) else 'N/A'}\n"
        result += f"Taille moyenne de l'effectif: {club2_info['squad_size'].iloc[0]}\n\n"

        result += f"--- Face à face général ---\n"
        result += f"Nombre de confrontations: {total_h2h}\n"
        result += f"Victoires {club1_name}: {club1_head_wins}\n"
        result += f"Victoires {club2_name}: {club2_head_wins}\n"
        result += f"Buts marqués {club1_name}: {club1_head_goals}\n"
        result += f"Buts marqués {club2_name}: {club2_head_goals}\n"
        result += f"Moyenne de buts par match {club1_name}: {avg_head_goals1:.2f}\n"
        result += f"Moyenne de buts par match {club2_name}: {avg_head_goals2:.2f}\n"
        result += f"{club1_name} gagne (proba Laplace): {proba1:.2f}\n"
        result += f"{club2_name} gagne (proba Laplace): {proba2:.2f}\n\n"

        # Statistiques récentes
        result += f"===== Statistiques des 5 dernières années (depuis {cutoff_date}) =====\n"
        result += f"--- {club1_name} ---\n"
        result += f"Matchs joués: {club1_total_matches_recent}\n"
        result += f"Matchs gagnés: {club1_wins_recent}\n"
        result += f"Win%: {winrate1_recent:.2f}%\n"
        result += f"Buts marqués: {club1_goals_recent}\n"
        result += f"Moyenne de buts par match: {avg_goals1_recent:.2f}\n\n"

        result += f"--- {club2_name} ---\n"
        result += f"Matchs joués: {club2_total_matches_recent}\n"
        result += f"Matchs gagnés: {club2_wins_recent}\n"
        result += f"Win%: {winrate2_recent:.2f}%\n"
        result += f"Buts marqués: {club2_goals_recent}\n"
        result += f"Moyenne de buts par match: {avg_goals2_recent:.2f}\n\n"

        result += f"--- Face à face (5 dernières années) ---\n"
        result += f"Nombre de confrontations: {total_h2h_recent}\n"
        result += f"Victoires {club1_name}: {club1_head_wins_recent}\n"
        result += f"Victoires {club2_name}: {club2_head_wins_recent}\n"
        result += f"Matchs nuls: {draws_recent}\n"
        result += f"Buts marqués {club1_name}: {club1_head_goals_recent}\n"
        result += f"Buts marqués {club2_name}: {club2_head_goals_recent}\n"
        result += f"Moyenne de buts par match {club1_name}: {avg_head_goals1_recent:.2f}\n"
        result += f"Moyenne de buts par match {club2_name}: {avg_head_goals2_recent:.2f}\n"
        result += f"{club1_name} gagne (proba Laplace): {proba1_recent:.2f}\n"
        result += f"{club2_name} gagne (proba Laplace): {proba2_recent:.2f}\n"
        result += f"Match nul (proba Laplace): {proba_draw_recent:.2f}\n"

        # ----- Graphique pour face-à-face récent -----
        if total_h2h_recent > 0:
            mu = club1_head_wins_recent / total_h2h_recent
            mu2 = club2_head_wins_recent / total_h2h_recent
            mu3 =proba_draw_recent 

            # Variance corrigée pour la distribution binomiale
            variance1 = (mu * (1 - mu)) / total_h2h_recent if total_h2h_recent > 0 else 0.1
            sigma1 = np.sqrt(max(variance1, 0.01))  # Minimum pour éviter une courbe trop étroite
            variance2 = (mu2 * (1 - mu2)) / total_h2h_recent if total_h2h_recent > 0 else 0.1
            sigma2 = np.sqrt(max(variance2, 0.01))
            variance3 = (mu3 * (1 - mu3)) / total_h2h_recent if total_h2h_recent > 0 else 0.1
            sigma3 = np.sqrt(max(variance3, 0.01))

            x = np.linspace(0, 1, 100)
            y = norm.pdf(x, mu, sigma1)
            y2 = norm.pdf(x, mu2, sigma2)
            y3 = norm.pdf(x, mu3, sigma3)

            # Supprimer un éventuel graphique précédent
            for widget in self.main_frame.grid_slaves():
                if isinstance(widget, FigureCanvasTkAgg):
                    widget.destroy()
            
            r = np.random.rand(1)[0]
            
            # Créer une figure matplotlib
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(x, y, label=f'Taux de victoire {club1_name}: {mu:.2f}', color='blue')
            ax.axvline(mu, color='blue', linestyle='--')
            ax.plot(x, y2, label=f'Taux de victoire {club2_name}: {mu2:.2f}', color='red')
            ax.axvline(mu2, color='red', linestyle='--')
            ax.plot(x, y3, label=f'Match nul: {mu3:.2f}', color='green')
            ax.axvline(mu3, color='green', linestyle='--')
            ax.axvline(r, color='black', linestyle=':', label='Tirage aléatoire')
            
            ax.set_title(f"Densité de probabilité (5 dernières années, depuis {cutoff_date})")
            ax.set_xlabel("Taux")
            ax.set_ylabel("Densité")
            ax.legend()
            
            # Intégrer la figure dans Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.main_frame)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.grid(row=6, column=0, columnspan=2, pady=10)
            
            # Forcer la mise à jour de la région de défilement
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.result_text.insert(tk.END, result)


if __name__ == "__main__":
    root = tk.Tk()
    app = FootballComparisonApp(root)
    root.mainloop()