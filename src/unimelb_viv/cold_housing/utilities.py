import pathlib
import pandas as pd

def get_data_dir(population):
    here = pathlib.Path(__file__).resolve()
    return here.parent / population


def get_model_specification_template_file():
    here = pathlib.Path(__file__).resolve()
    return here.parent / 'yaml_template.in'


def get_reduce_acmr_specification_template_file():
    here = pathlib.Path(__file__).resolve()
    return here.parent / 'mslt_reduce_acmr.in'


def get_reduce_chd_specification_template_file():
    here = pathlib.Path(__file__).resolve()
    return here.parent / 'mslt_reduce_chd.in'


def col_to_bin(df, col, binWidth):
    """
    Convert a single column of a multi-index, denoted col, to col_start
    and col_end. The gap between the start and end is set by binWidth.
    """
    df = df.reset_index(level=[col])
    df[col + '_end'] = df[col] + binWidth
    df.rename(columns={col: col + '_start'}, inplace=True)
    df.set_index([col + '_start', col + '_end'], append=True, inplace=True)
    return df
    
def load_csv(name, data_dir):
    data_file = ('{}/' + name).format(data_dir)
    data_path = str(pathlib.Path(data_file).resolve())
    return pd.read_csv(data_path)

def df_cross(df1, df2):
    return (df1
        .assign(_cross_merge_key=1)
        .merge(df2.assign(_cross_merge_key=1), on="_cross_merge_key")
        .drop("_cross_merge_key", axis=1)
    )
