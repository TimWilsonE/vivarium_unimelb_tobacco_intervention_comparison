import datetime
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from vivarium.framework.artifact import hdf
from vivarium.framework.artifact import Artifact

from unimelb_viv.cold_housing.population import Population
from unimelb_viv.cold_housing.utilities import get_data_dir

YEAR_START = 2011
RANDOM_SEED = 49430

def output_csv_mkdir(data, path):
    """
    Wrapper for pandas .to_csv() method to create directory for path if it
    doesn't already exist.
    """
    output_path = Path('.').resolve() / 'artifacts' / (path + '.csv')
    out_folder = os.path.dirname(output_path)

    if not os.path.exists(out_folder):
        os.mkdir(out_folder)

    print(output_path)
    data.to_csv(output_path)


def check_for_bin_edges(df):
    """
    Check that lower (inclusive) and upper (exclusive) bounds for year and age
    are defined as table columns.
    """

    if 'age_start' in df.columns and 'year_start' in df.columns:
        return df
    else:
        raise ValueError('Table does not have bins')


def write_table(artifact, path, data):
    """
    Write a data table to an artifact, after ensuring that it doesn't contain
    any NA values.

    :param artifact: The artifact object.
    :param path: The table path.
    :param data: The table data.
    """
    if np.any(data.isna()):
        msg = 'NA values in table {} for {}'.format(path, artifact.path)
        raise ValueError(msg)

    logger = logging.getLogger(__name__)
    logger.info('{} Writing table {} to {}'.format(
        datetime.datetime.now().strftime("%H:%M:%S"), path, artifact.path))

    output_csv_mkdir(data, path)
    artifact.write(path, data)


def assemble_artifacts(num_draws, output_path: Path, seed: int = RANDOM_SEED):
    """
    Assemble the data artifacts required to simulate the various tobacco
    interventions.

    Parameters
    ----------
    num_draws
        The number of random draws to sample for each rate and quantity,
        for the uncertainty analysis.
    output_path
        The path to the artifact being assembled.
    seed
        The seed for the pseudo-random number generator used to generate the
        random samples.

    """
    data_dir = get_data_dir('input')
    prng = np.random.RandomState(seed=seed)
    logger = logging.getLogger(__name__)
    
    # Initialise each artifact file.
    artifact_file = output_path / 'cold_house.hdf'
    if artifact_file.exists():
        artifact_file.unlink()
    artifact = Artifact(str(artifact_file))
    
    pop = Population(data_dir, YEAR_START)

    logger.info('{} Writing population tables'.format(
                datetime.datetime.now().strftime("%H:%M:%S")))
    
    write_table(artifact, 'population.agg', pop.get_population())
    write_table(artifact, 'population.prop', pop.get_prop_population())
    write_table(artifact, 'mortality.agg', pop.get_mortality_rate())
    write_table(artifact, 'mortality.prop', pop.get_prop_mort())
    write_table(artifact, 'yld.agg', pop.get_disability_rate())
    write_table(artifact, 'yld.prop', pop.get_prop_yld())


def test_artifacts():
    output_path = Path('.').resolve() / 'artifacts'
    output_path.mkdir(exist_ok=True)
    
    print(output_path)
    assemble_artifacts(0, output_path)