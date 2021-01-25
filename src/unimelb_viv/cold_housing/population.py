"""Build population data tables."""

import pandas as pd
import numpy as np
import pathlib

from .uncertainty import sample_fixed_rate_from
from unimelb_viv.cold_housing.utilities import load_csv, col_to_bins

SUB_POPS = 5

class Population:

    def load_base_pop(self, data_dir, year_start):
        df = load_csv('base_population.csv', data_dir)
        df = df.rename(columns={'mortality per 1 rate': 'mortality_rate',
                                'pYLD rate': 'disability_rate',
                                'APC in all-cause mortality': 'mortality_apc',
                                '5-year': 'population'})

        # Use identical populations in the BAU and intervention scenarios.
        df['bau_population'] = df['population'].values

        # Retain only the necessary columns.
        df['year'] = year_start
        df = df[['year', 'age', 'sex', 'population', 'bau_population',
                 'disability_rate', 'mortality_rate', 'mortality_apc']]

        # Remove strata that have already reached the terminal age.
        df = df[~ (df.age == df['age'].max())]

        # Sort the rows.
        df = df.sort_values(by=['year', 'age', 'sex']).reset_index(drop=True)

        self.year_start = year_start
        self.year_end = year_start + df['age'].max() - df['age'].min()
        self._num_apc_years = 15

        return df


    def __init__(self, data_dir, year_start):
        self.df_base = self.load_base_pop(data_dir, year_start)
        self.df_cohort = load_csv('maori_cohort_population_data.csv', data_dir)
        
        df = self.df_cohort.rename(columns = {'N' : 'population'})
        
        # Retain only the necessary columns.
        df.set_index(['age', 'sex', 'year'], inplace=True)
        df = df[['prop{}'.format(k) for k in range(SUB_POPS)] + 
                ['mort_RR{}'.format(k) for k in range(SUB_POPS)] +
                ['yld_RR{}'.format(k) for k in range(SUB_POPS)] +
                ['population', 'yld', 'mortality']]
        
        self.agg_mort = df[['mortality']].rename(columns = {'mortality': 'value'})
        self.agg_yld = df[['yld']].rename(columns = {'yld': 'value'})
        self.agg_pop = (df[df.index.get_level_values('year') == 2011]
            )[['population']].rename(columns = {'population': 'value'})
        
        self.prop_pop = ((df[df.index.get_level_values('year') == 2011]).
            rename(columns = dict([('prop{}'.format(k), k) for k in range(SUB_POPS)])).
            melt(id_vars = [], value_vars=range(SUB_POPS), ignore_index=False).
            rename(columns = {'variable': 'strata'}).
            set_index(['strata'], append=True))
        
        self.prop_mort = (df.
            rename(columns=dict([('mort_RR{}'.format(k), k) for k in range(SUB_POPS)])).
            melt(id_vars = [], value_vars=range(SUB_POPS), ignore_index=False).
            rename(columns = {'variable': 'strata'}).
            set_index(['strata'], append=True))
        
        self.prop_yld = (df.
            rename(columns=dict([('yld_RR{}'.format(k), k) for k in range(SUB_POPS)])).
            melt(id_vars = [], value_vars=range(SUB_POPS), ignore_index=False).
            rename(columns = {'variable': 'strata'}).
            set_index(['strata'], append=True))
        
        col_to_bins(self.prop_mort, 'age', 1)



    def years(self):
        """Return an iterator over the simulation period."""
        return range(self.year_start, self.year_end + 1)
    

    def get_agg_population(self):
        return self.agg_pop


    def get_agg_mort(self):
        return self.agg_mort


    def get_agg_yld(self):
        return self.agg_yld
        
    def get_prop_population(self):
        return self.prop_pop


    def get_prop_mort(self):
        return self.prop_mort


    def get_prop_yld(self):
        return self.prop_yld
    
    def get_acmr_apc(self):
        """Return the annual percent change (APC) in mortality rate."""
        df = self.df_base[['year', 'age', 'sex', 'mortality_apc']]
        df = df.rename(columns={'mortality_apc': 'value'})

        tables = []
        for year in self.years():
            df['year'] = year
            tables.append(df.copy())

        df = pd.concat(tables).sort_values(['year', 'age', 'sex'])
        df = df.reset_index(drop=True)

        return df

    def get_mortality_rate(self):
        # - ACMR = BASE_ACMR * e^(APC * (year - 2011))
        df_apc = self.get_acmr_apc()
        df_acmr = self.df_base[['age', 'sex', 'mortality_rate']]
        df_acmr = df_acmr.rename(columns={'mortality_rate': 'value'})
        base_acmr = df_acmr['value'].copy()

        # Replace 'age' with age groups.
        df_acmr = df_acmr.rename(columns={'age': 'age_start'})
        df_acmr.insert(df_acmr.columns.get_loc('age_start') + 1,
                       'age_end',
                       df_acmr['age_start'] + 1)

        # These values apply at each year of the simulation, so we only need
        # to define a single bin.
        df_acmr.insert(0, 'year_start', self.year_start -1)
        df_acmr.insert(1, 'year_end', self.year_start)

        tables = []
        tables.append(df_acmr.copy())
        for counter, year in enumerate(self.years()):
            if counter <= self._num_apc_years:
                year_apc = df_apc[df_apc.year == year]
                apc = year_apc['value'].values
                scale = np.exp(apc * (year - self.year_start))
                df_acmr.loc[:, 'value'] = base_acmr * scale
            else:
                # NOTE: use the same scale for this cohort as per the previous
                # year; shift by 2 because there are male and female cohorts.
                scale[2:] = scale[:-2]
                df_acmr.loc[:, 'value'] = base_acmr * scale
            df_acmr['year_start'] = year
            df_acmr['year_end'] = year + 1
            tables.append(df_acmr.copy())

        df = pd.concat(tables).sort_values(['year_start', 'age_start',
                                            'sex'])
        df = df.reset_index(drop=True)

        return df
    
    
    