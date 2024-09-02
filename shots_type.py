import duckdb
import pandas as pd
from mplsoccer import VerticalPitch



def get_shot_types(events):
    shots = duckdb.sql("select possession, team, shot_statsbomb_xg, shot_outcome, shot_key_pass_id from events where type = 'Shot'")
    events_possession = duckdb.sql("""select distinct events.possession, first_value(play_pattern) over (partition by events.possession, events.team order by timestamp) as play_pattern, events.team, first_value(type) over (partition by events.possession, events.team order by timestamp) as type, first_value(location) over (partition by events.possession, events.team order by timestamp) as location,
                        first_value(pass_type) over (partition by events.possession, events.team order by timestamp) as pass_type
                        from events""")
    shots_type = duckdb.sql("""select * from events_possession join shots on events_possession.possession = shots.possession and events_possession.team = shots.team""")
    shots_type = duckdb.sql("select *, ifnull(pass_type, type) as type_of_pass from shots_type").df()
    
    print(shots_type[shots_type['shot_outcome'] == 'Goal'])
    
    return shots_type

def plot_first_moves(events, home_team, away_team):   
    shots_type = get_shot_types(events)
    pitch = VerticalPitch(pitch_type='statsbomb')

    fig_size = (6, 10)
    # Plot for Home Team
    fig_home, ax_home = pitch.draw(figsize=fig_size)
    home_team_shots = shots_type[shots_type['team'] == home_team]
    home_team_shots[['x', 'y']] = home_team_shots['location'].apply(pd.Series)

    for shot in home_team_shots.to_dict(orient='records'):
        pitch.scatter(x=shot['x'], y=shot['y'], ax=ax_home, s=500*shot['shot_statsbomb_xg'],
                      ec='black', c='red' if shot['type_of_pass'] in ['Interception', 'Pressure', 'Ball Recovery', 'Recovery'] else 'black')

    ax_home.set_title(f'{home_team}: Gdzie zaczęły się akcje zakończone strzałem\n - na czerwono odbiór piłki',
                      fontsize=10, fontfamily='monospace')

    # Plot for Away Team
    fig_away, ax_away = pitch.draw(figsize=fig_size)
    away_team_shots = shots_type[shots_type['team'] == away_team]
    away_team_shots[['x', 'y']] = away_team_shots['location'].apply(pd.Series)

    for shot in away_team_shots.to_dict(orient='records'):
        pitch.scatter(x=shot['x'], y=shot['y'], ax=ax_away, s=500*shot['shot_statsbomb_xg'],
                      ec='black', c='red' if shot['type_of_pass'] in ['Interception', 'Pressure', 'Ball Recovery', 'Recovery'] else 'black')

    ax_away.set_title(f'{away_team}: Gdzie zaczęły się akcje zakończone strzałem\n - na czerwono odbiór piłki',
                      fontsize=10, fontfamily='monospace')

    return fig_home, fig_away