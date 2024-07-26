import pandas as pd
import duckdb


def make_table(events):
    events[['x', 'y']] = events['location'].apply(pd.Series)
    events[['end_x', 'end_y']] = events['pass_end_location'].apply(pd.Series)
    
    shots = duckdb.sql("select a.possession, a.team, a.shot_statsbomb_xg, b.pass_type from (select possession, team, shot_statsbomb_xg, shot_outcome, shot_key_pass_id from events where type = 'Shot') a left join (select id, ifnull(pass_type, 'Open Play') as pass_type from events where type = 'Pass') b on a.shot_key_pass_id = b.id")

    xg_table = duckdb.sql("select team, sum(sum_xg) as overall_xg, sum(case when pass_type = 'Set Piece' then sum_xg end) as set_piece_xg from (select team, case when pass_type = 'Corner' or pass_type = 'Free Kick' then 'Set Piece' else 'Open Play' end as pass_type, sum(shot_xg) as sum_xg from (select possession, team, max(shot_statsbomb_xg) as shot_xg, pass_type from shots group by possession, team, pass_type) group by 1,2) group by 1")
    
    passes = duckdb.sql("select player, team, x,y, end_x, end_y, ifnull(pass_outcome, 'Complete') as pass_outcome, ifnull(pass_type, 'Regular Play') as pass_type from events where type = 'Pass'")
    
    
    passes_to_penalty = duckdb.sql("""select player, team, x, y, end_x, end_y from passes
                    where end_x > 100 and end_y > 20 and end_y < 60 and pass_type = 'Regular Play' and pass_outcome = 'Complete'""")
    

    penalty_pass = duckdb.sql("select team, count(*) as passes_to_penalty_area from passes_to_penalty group by 1")
    

    
    pressures = duckdb.sql("""select team, count(*) as pressures_in_opp_half from (select team, possession, timestamp, x, y from events where type = 'Pressure' and x > 60) group by 1""")

    table = duckdb.sql("select xg_table.team, xg_table.overall_xg, xg_table.set_piece_xg, penalty_pass.passes_to_penalty_area, pressures.pressures_in_opp_half from xg_table join penalty_pass on xg_table.team = penalty_pass.team join pressures on xg_table.team = pressures.team").df()

    table = table.set_index('team')
    return table.transpose()