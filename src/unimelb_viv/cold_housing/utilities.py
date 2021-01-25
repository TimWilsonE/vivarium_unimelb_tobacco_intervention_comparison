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


def col_to_bins(df, col, binWidth):
    """
    Convert a single column of a multi-index, denoted col, to col_start
    and col_end. The gap between the start and end is set by binWidth.
    """
    
    print(df)
    
def load_csv(name, data_dir):
    data_file = ('{}/' + name).format(data_dir)
    data_path = str(pathlib.Path(data_file).resolve())
    return pd.read_csv(data_path)
