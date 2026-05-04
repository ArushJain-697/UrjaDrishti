import pandas as pd

def load_data(path):
    df = pd.read_csv(path, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def temporal_split(df, val_months=2, test_months=2):
    t_max = df['timestamp'].max()

    test_start  = t_max - pd.DateOffset(months=test_months)
    val_start   = test_start - pd.DateOffset(months=val_months)

    train_df = df[df['timestamp'] <  val_start].copy()
    val_df   = df[(df['timestamp'] >= val_start) & (df['timestamp'] < test_start)].copy()
    test_df  = df[df['timestamp'] >= test_start].copy()

    print(f"Split sizes  ->  train: {len(train_df):,}  val: {len(val_df):,}  test: {len(test_df):,}")
    print(f"  Train  :  {train_df['timestamp'].min()}  ->  {train_df['timestamp'].max()}")
    print(f"  Val    :  {val_df['timestamp'].min()}  ->  {val_df['timestamp'].max()}")
    print(f"  Test   :  {test_df['timestamp'].min()}  ->  {test_df['timestamp'].max()}")

    return train_df, val_df, test_df