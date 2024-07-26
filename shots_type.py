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

def plot_first_moves(events, team):   
    shots_type = get_shot_types(events)
    pitch = VerticalPitch(pitch_type ='statsbomb')

    fig,ax = pitch.draw()
    shots_type[['x', 'y']] = shots_type['location'].apply(pd.Series)

    for x in shots_type.to_dict(orient = 'records'):
        if x['team'] ==  team:
            pitch.scatter(x=x['x'], y=x['y'], ax=ax, s=500*x['shot_statsbomb_xg'],
                        ec='black', c='red' if (x['type_of_pass'] == 'Interception' or x['type_of_pass'] == 'Pressure' or x['type_of_pass'] == 'Ball Recovery' or x['type_of_pass'] == 'Recovery') else 'black')
            
    ax.set_title('Gdzie zaczęły się akcje zakończone strzałem\n - na czerwono odbiór piłki', fontsize = 10, fontfamily = 'monospace')
    
    return fig