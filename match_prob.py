import numpy as np
import plotly.graph_objects as go
import streamlit as st

@st.cache_data
def simulate_game(xg_team1, xg_team2, num_simulations=1000):
    max_goals = 5
    result_matrix = np.zeros((max_goals + 1, max_goals + 1))

    for _ in range(num_simulations):
        # Simulate goals for team 1
        goals_team1 = np.random.poisson(xg_team1)
        goals_team1 = min(goals_team1, max_goals)

        # Simulate goals for team 2
        goals_team2 = np.random.poisson(xg_team2)
        goals_team2 = min(goals_team2, max_goals)

        # Increment the corresponding cell in the result matrix
        result_matrix[goals_team1, goals_team2] += 1

    # Convert counts to probabilities
    result_matrix /= num_simulations

    return result_matrix

def plot_heatmap(matrix, home_team, away_team):
    # Create text labels for the heatmap cells
    text = [[f'{prob:.2%}' for prob in row] for row in matrix]
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[0, 1, 2, 3, 4, 5],
        y=[0, 1, 2, 3, 4, 5],
        colorscale='reds',
        text=text,
        hoverinfo='text'
    ))

    fig.update_layout(
        title=f'Probability Matrix ({home_team} goals vs {away_team} goals)',
        xaxis_title=f'{away_team} Goals',
        yaxis_title=f'{home_team} Goals',
    )

    return fig

def plot_bar_chart(probabilities, team_name):
    max_goals = 5
    goals = list(range(max_goals + 1))
    max_prob_index = np.argmax(probabilities)

    colors = ['blue'] * (max_goals + 1)
    colors[max_prob_index] = 'red'

    fig = go.Figure(data=[go.Bar(
        x=goals,
        y=probabilities,
        marker_color=colors,
        text=[f'{prob:.2%}' for prob in probabilities],
        textposition='auto'
    )])

    fig.update_layout(
        title=f'Probability of Goals for {team_name}',
        xaxis_title='Number of Goals',
        yaxis_title='Probability'
    )

    return fig

