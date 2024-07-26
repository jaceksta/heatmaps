import pandas as pd
from mplsoccer import Sbopen, Pitch, VerticalPitch
from statsbombpy import sb
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as path_effects
import math
from helper import calculate_pass_diff, calculate_pressures, create_passnetwork, pass_flow, passes_to_shots, passes_to_penalty
from match_prob import simulate_game, plot_heatmap, plot_bar_chart
import duckdb
from shots_type import plot_first_moves
from table_maker import make_table



def get_poland_games():
    games = sb.matches(competition_id=55, season_id=282)

    games = games[(games['home_team'] == 'Poland') | (games['away_team'] == 'Poland')]
    
    games['match_name'] = games['home_team'] + ' vs ' + games['away_team']
    
    return games[['match_id', 'home_team', 'away_team', 'match_name']]


games = get_poland_games()

game_to_analyse = st.selectbox('Select a game', games['match_name'])
game_id = games[games['match_name'] == game_to_analyse]['match_id'].values[0]
home_team = games[games['match_name'] == game_to_analyse]['home_team'].values[0]
away_team = games[games['match_name'] == game_to_analyse]['away_team'].values[0]



events = sb.events(game_id)
shots = duckdb.sql("select possession, team, max(shot_statsbomb_xg) as shot_xg, pass_type from events where type = 'Shot' group by possession, team, pass_type").df()

home_xg = shots[shots['team'] == home_team]['shot_xg'].sum()
away_xg = shots[shots['team'] == away_team]['shot_xg'].sum()
result_probabilities = simulate_game(home_xg, away_xg, num_simulations=1000)


tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(['Tabelka', 'Prawdopodobieństwo', 'Podania', 'Pressing', 'Sieć podań', 'Strzały'])

with tab0:
    st.write(make_table(events))
    st.write(events['player'])

with tab1:
    st.plotly_chart(plot_heatmap(result_probabilities, home_team, away_team))

    col5, col6 = st.columns(2)

    # Calculate marginal probabilities for each team
    team1_probabilities = result_probabilities.sum(axis=1)
    team2_probabilities = result_probabilities.sum(axis=0)

    # Plot bar charts for each team
    col5.plotly_chart(plot_bar_chart(team1_probabilities, home_team), use_container_width=True)
    col6.plotly_chart(plot_bar_chart(team2_probabilities, away_team), use_container_width=True)


with tab2:    
    st.write('Podania przed pole bramkowe')
    st.pyplot(passes_to_penalty(events, home_team, away_team))
    st.write('Róznica w liczbie podań w róznych strefach')
    st.pyplot(calculate_pass_diff(events, home_team, away_team))
    st.write('Flow podań')
    col9, col10 = st.columns(2)
    col9.pyplot(pass_flow(events, home_team, away_team))
    col10.pyplot(pass_flow(events, away_team, home_team))
    
    
with tab3: 

    col1, col2 = st.columns(2)
    col1.write(f'Pressing {home_team}')
    col1.pyplot(calculate_pressures(events, home_team))
    col2.write(f'Pressing {away_team}')
    col2.pyplot(calculate_pressures(events, away_team))
    
with tab4:    

    col3, col4 = st.columns(2)
    col3.write(f"Sieć podań {home_team}")
    col3.pyplot(create_passnetwork(events, home_team))
    col4.write(f"Sieć podań {away_team}")
    col4.pyplot(create_passnetwork(events, away_team))
    
with tab5:
    col7, col8 = tab5.columns(2)
    col7.caption(f"Rozpoczęcie akcji zakończonej strzałem {home_team}")
    col7.pyplot(plot_first_moves(events, home_team))
    col7.caption(f"Kluczowe podania {home_team}")
    col7.pyplot(passes_to_shots(events, home_team, away_team))
    col8.caption(f"Rozpoczęcie akcji zakończonej strzałem {away_team}")
    col8.pyplot(plot_first_moves(events, away_team))
    col8.caption(f"Kluczowe podania {away_team}")
    col8.pyplot(passes_to_shots(events, away_team, home_team))