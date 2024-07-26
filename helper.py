import pandas as pd
from mplsoccer import Sbopen, Pitch, VerticalPitch, FontManager
from statsbombpy import sb
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as path_effects
import math
import duckdb

def calculate_pass_diff(events, home_team, away_team):
    pitch = Pitch(line_zorder=2)
    df = events.loc[(events['type'] == 'Pass') & (events['play_pattern'] == 'Regular Play')].copy()
    df[['x', 'y']] = df['location'].apply(pd.Series)

    df = df[['team', 'x', 'y']]

    df.rename(columns={'team': 'team'}, inplace=True)

    team_a = df[df['team'] == home_team]
    team_b = df[df['team'] == away_team]
    team_b['x'] = 120-team_b['x']
    team_b['y'] = 80-team_b['y']
    df = pd.concat([team_a, team_b])

    # Define pitch dimensions (length and width)
    pitch_length = 120
    pitch_width = 80

    # Divide pitch into 30 zones (e.g., 5 rows x 6 columns)
    num_vertical_zones = 5
    num_horizontal_zones = 6

    # Calculate zone boundaries
    x_bins = np.linspace(0, pitch_length, num_horizontal_zones + 1)
    y_bins = np.linspace(0, pitch_width, num_vertical_zones + 1)

    # Count passes in each zone for each team
    df['x_bin'] = pd.cut(df['x'], bins=x_bins, labels=False)
    df['y_bin'] = pd.cut(df['y'], bins=y_bins, labels=False)

    pass_counts = df.groupby(['x_bin', 'y_bin', 'team']).size().unstack(fill_value=0)
    
    pass_diff = pass_counts.get(home_team, 0) - pass_counts.get(away_team, 0)
    pass_diff_matrix = np.zeros((num_vertical_zones, num_horizontal_zones))

    for (x_bin, y_bin), value in pass_diff.items():
        pass_diff_matrix[y_bin, x_bin] = value

    # Plot the difference using mplsoccer
    pitch = Pitch(pitch_type='statsbomb', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 7))

    # Prepare data for heatmap plotting
    x_bin_centers = (x_bins[:-1] + x_bins[1:]) / 2
    y_bin_centers = (y_bins[:-1] + y_bins[1:]) / 2

    # Plot the heatmap
    heatmap = ax.pcolormesh(x_bin_centers, y_bin_centers, pass_diff_matrix, cmap='coolwarm', linewidth=0.5)

    # Add a color bar
    
    
    

    # Color the title
    plt.figtext(0.47, 0.96, home_team, fontsize=20, color='darkred', ha ='right', fontdict={'fontweight': 'bold', 'fontfamily': 'monospace'})
    plt.figtext(0.53, 0.96, away_team, fontsize=20, color='darkblue', ha ='left', fontdict={'fontweight': 'bold', 'fontfamily': 'monospace'})
    plt.figtext(0.50, 0.96, ' vs ', fontsize=20, color='k', ha ='center', fontdict={'fontweight': 'bold', 'fontfamily': 'monospace'})

    plt.show()
    return fig 


def calculate_pressures(events, team_name):
    path_eff = [path_effects.Stroke(linewidth=1.5, foreground='black'),
            path_effects.Normal()]

    df_pressure = events.loc[(events['type'] == 'Pressure')].copy()
    
    df_pressure[['x', 'y']] = df_pressure['location'].apply(pd.Series)

    team_a = df_pressure[df_pressure['team'] == team_name]

    pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#f4edf0')
    fig, ax = pitch.draw(figsize=(4.125, 6))
    fig.set_facecolor('#f4edf0')
    bin_x = np.linspace(pitch.dim.left, pitch.dim.right, num=7)
    bin_y = np.sort(np.array([pitch.dim.bottom, pitch.dim.six_yard_bottom,
                            pitch.dim.six_yard_top, pitch.dim.top]))
    bin_statistic = pitch.bin_statistic(team_a.x, team_a.y, statistic='count',
                                        bins=(bin_x, bin_y), normalize=True)
    pitch.heatmap(bin_statistic, ax=ax, cmap='Reds', edgecolor='#f9f9f9')
    labels2 = pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=18,
                                ax=ax, ha='center', va='center',
                                str_format='{:.0%}', path_effects=path_eff)
    return fig
    
def create_passnetwork(events, team_name):
    
    team = events[events['team'] == team_name]
    st.write(team['player'])
    team[['x', 'y']] = team['location'].apply(pd.Series)

    tactics = team[~team['tactics'].isnull()][['tactics', 'team']]

    all_jersey_numbers = []
    for y in tactics.to_dict(orient='records'):
        all_jersey_numbers.append(pd.DataFrame([{'player_id': x['player']['id'], 'jersey_number': x['jersey_number']} for x in y['tactics']['lineup']]))
        
    jersey_numbers = pd.concat(all_jersey_numbers).drop_duplicates()
    
    # Make a new, single column for time and sort the events in chronological order
    team["newsecond"] = 60 * team["minute"] + team["second"]
    
    team.sort_values(by=['newsecond'])
    
    # identify the passer and then the recipient, who'll be the playerId of the next action
    if 'player' in team.columns:
        team['passer'] = team['player']
    else:
        st.error("The column 'player_id' is missing from the data.")
        st.stop()
    
    team['recipient'] = team['passer'].shift(-1)
    
    # filter for only passes and then successful passes
    passes_df = team.loc[(team['type']=="Pass")]
    passes_df['pass_outcome'] = passes_df['pass_outcome'].fillna("Successful")
    
    completions = passes_df.loc[(passes_df['pass_outcome'] == "Successful")]
    
    #find time of the team's first substitution and filter the df to only passes before that
    sub_df = team.loc[(team['type'] == "Substitution")]
    first_sub = sub_df["newsecond"].min()
    
    if first_sub <= (60 * 45):
        first_sub = 60 * 45
    
    completions = completions.loc[completions['newsecond'] < first_sub]
    
    # Find Average Locations
    average_locs_and_count = completions.groupby('passer').agg({'x': ['mean'], 'y': ['mean','count']})
    average_locs_and_count.columns = ['x', 'y', 'count']
    
    # find number of passes along each 'path' of passer to recipient
    passes_between = completions.groupby(['passer', 'recipient']).id.count().reset_index()
    passes_between.rename({'id': 'pass_count'}, axis='columns', inplace=True)
    
    passes_between = passes_between.merge(average_locs_and_count, left_on='passer', right_index=True)
    passes_between = passes_between.merge(
        average_locs_and_count, left_on='recipient', right_index=True, suffixes=['', '_end']
    )
    
    # set minimum threshold for pass arrows to be plotted. So this will only plot combos which occured at least 5 times.
    passes_between = passes_between.loc[(passes_between['pass_count'] >= 4)]
    
    # plot arrows
    def pass_line_template(ax, x, y, end_x, end_y, line_color):
        ax.annotate(
            '',
            xy=(end_y,  end_x),
            xytext=(y, x),
            zorder=1,
            arrowprops=dict(arrowstyle='-|>', linewidth=4, color=line_color, alpha=.85)
        )
        
    def pass_line_template_shrink(ax, x, y, end_x, end_y, line_color, dist_delta=1.2):
        dist = math.hypot(end_x - x, end_y - y)
        angle = math.atan2(end_y-y, end_x-x)
        upd_x = x + (dist - dist_delta) * math.cos(angle)
        upd_y = y + (dist - dist_delta) * math.sin(angle)
        pass_line_template(ax, x, y, upd_x, upd_y, line_color=line_color)
    
    pitch = VerticalPitch(pitch_type='statsbomb')
    fig, ax = pitch.draw()
    
    for index, row in passes_between.iterrows():
        pass_line_template_shrink(ax, row['x'], row['y'], row['x_end'], row['y_end'], 'black')
    
    # plot nodes
    pitch.scatter(
        average_locs_and_count.x, average_locs_and_count.y, s=500,
        color='#f0ece2', edgecolors="#010101", linewidth=2, alpha=1, ax=ax, zorder=2
    )
    
    for index, row in average_locs_and_count.iterrows():
        pitch.annotate(
            jersey_numbers[jersey_numbers['player_id'] == row.name]['jersey_number'].values[0],
            xy=(row.x, row.y),
            c='#132743',
            va='center',
            ha='center',
            size=10,
            fontweight='bold',
            ax=ax
        )
    return fig


def pass_flow(events, team, team2):
    events = events.loc[events['type'] == 'Pass']
    mask_team1 = (events.team == team)
    events[['x', 'y']] = events['location'].apply(pd.Series)
    events[['end_x', 'end_y']] = events['pass_end_location'].apply(pd.Series)
    df_pass = events.loc[mask_team1, ['x', 'y', 'end_x', 'end_y', 'pass_outcome']]
    mask_complete = df_pass.pass_outcome.isnull()
    pitch = VerticalPitch(pitch_type='statsbomb',  line_zorder=2, line_color='#c7d5cc')
    bins = (6, 4)
    fig, ax = pitch.draw(figsize=(16, 11), constrained_layout=True, tight_layout=False)
    # plot the heatmap - darker colors = more passes originating from that square
    bs_heatmap = pitch.bin_statistic(df_pass.x, df_pass.y, statistic='count', bins=bins)
    hm = pitch.heatmap(bs_heatmap, ax=ax, cmap='Reds')
    # plot the pass flow map with a single color and the
    # arrow length equal to the average distance in the cell
    fm = pitch.flow(df_pass.x, df_pass.y, df_pass.end_x, df_pass.end_y, color='black',
                    arrow_type='average', bins=bins, ax=ax)
    return fig


def passes_to_shots(df, TEAM1, TEAM2):
    df[['x', 'y']] = df['location'].apply(pd.Series)
    df[['end_x', 'end_y']] = df['pass_end_location'].apply(pd.Series)
    df_pass = df.loc[(df.pass_assisted_shot_id.notnull()) & (df.team     == TEAM1),
                 ['x', 'y', 'end_x', 'end_y', 'pass_assisted_shot_id']]

    df_shot = (df.loc[(df.type == 'Shot') & (df.team == TEAM1),
                    ['id', 'shot_outcome', 'shot_statsbomb_xg']]
            .rename({'id': 'pass_assisted_shot_id'}, axis=1))

    df_pass = df_pass.merge(df_shot, how='left').drop('pass_assisted_shot_id', axis=1)

    mask_goal = df_pass.shot_outcome == 'Goal'
    
        # Setup the pitch
    pitch = VerticalPitch(pitch_type='statsbomb',
                        half=True, pad_top=2)
    fig, axs = pitch.grid(endnote_height=0.03, endnote_space=0, figheight=12,
                        title_height=0.08, title_space=0, axis=False,
                        grid_height=0.82)

    # Plot the completed passes
    pitch.lines(df_pass.x, df_pass.y, df_pass.end_x, df_pass.end_y,
                lw=10, transparent=True,
                label='pass leading to shot', ax=axs['pitch'])

    # Plot the goals
    pitch.scatter(df_pass[mask_goal].end_x, df_pass[mask_goal].end_y, s=700,
                marker='football', edgecolors='black', c='white', zorder=2,
                label='goal', ax=axs['pitch'])
    pitch.scatter(df_pass[~mask_goal].end_x, df_pass[~mask_goal].end_y,
                edgecolors='white', c='#22312b', s=700, zorder=2,
                label='shot', ax=axs['pitch'])



    return fig


def passes_to_penalty(events, team1, team2):
    events[['x', 'y']] = events['location'].apply(pd.Series)
    events[['end_x', 'end_y']] = events['pass_end_location'].apply(pd.Series)


    passes = events[events['type'] == 'Pass']

    passes['pass_type'] = passes['pass_type'].fillna('Regular Play')
    passes['pass_outcome'] = passes['pass_outcome'].fillna('Complete')

    passes = duckdb.sql("""select player, team, x, y, end_x, end_y,  ifnull(pass_outcome, 'Complete') as pass_outcome, ifnull(pass_type, 'Regular Play') as pass_type from passes
                    where end_x > 100 and end_y > 30 and end_y < 50 and end_x < 115 and pass_type = 'Regular Play'""").df()
    
    
    pitch = Pitch(pitch_type='statsbomb')

    fig, ax = pitch.draw()

    for x in passes.to_dict(orient = 'records'):
        if x['team'] == team1:
            if x['pass_outcome'] =='Complete':
                pitch.lines(x['x'], x['y'], x['end_x'], x['end_y'], lw = 5,
                            transparent = True, comet = True, ax = ax, color = 'g')
            else:
                pitch.lines(x['x'], x['y'], x['end_x'], x['end_y'], lw=5,
                            transparent=True, comet=True, ax=ax, color='r')
        else:
            x['x'] = 120 - x['x']
            x['y'] = 80 - x['y']
            x['end_x'] = 120 - x['end_x']
            x['end_y'] = 80 - x['end_y']
            if x['pass_outcome'] =='Complete':
                pitch.lines(x['x'], x['y'], x['end_x'], x['end_y'], lw = 5,
                            transparent = True, comet = True, ax = ax, color = 'g')
            else:
                pitch.lines(x['x'], x['y'], x['end_x'], x['end_y'], lw=5,
                            transparent=True, comet=True, ax=ax, color='r')
            
    ax.set_title('Podania przed pole bramkowe', fontsize = 12, fontfamily = 'monospace')

    from matplotlib.lines import Line2D

    legend_elements = [
            Line2D([0], [0], color = 'g', lw = 4, label = 'Complete Pass'),
            Line2D([0], [0], color='r', lw=4, label='Incomplete Pass'),

        ]
    
    ax.text(30,86, team2, ha='center', fontsize = 16, fontfamily = 'monospace')
    ax.text(90, 86, team1, ha='center', fontsize=16, fontfamily='monospace')

    ax.legend(handles = legend_elements, loc = 'lower left')
    return fig